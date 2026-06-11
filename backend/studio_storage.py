"""
MAJA Creations — Studio Backup Storage (NEW FEATURE — June 2026)
===============================================================
Lets photographers store their studio photos/videos as a backup even
after their physical drives/cards are lost.

Flow (per the product owner brief)
----------------------------------
1. Super admin defines storage plans from the admin panel:
       { name, gb_limit, duration_days, grace_days, price_inr, is_active }
   Example plans:
       • 10 GB / 1 month  → ₹ X
       • 100 GB / 3 months → ₹ Y
       • 1 TB / 6 months  → ₹ Z
2. Photographer logs in → Dashboard → "Store my photos"
3. Photographer picks a plan → Razorpay payment → on success a
   StudioStorageSubscription document is created with:
       • starts_at = now
       • expires_at = starts_at + duration_days
       • purge_at  = expires_at + grace_days
       • status    = "active"
4. During [starts_at, expires_at] photographer can upload/download/delete files.
5. During [expires_at, purge_at] (the grace window):
       • Status flips to "grace" automatically (computed on read).
       • Uploads are rejected with 402 — pay to extend.
       • Downloads/listing still work so the photographer can grab their
         files before purge.
       • Renewing extends expires_at by another duration_days.
6. After purge_at: status = "expired", all S3 files purged, used_bytes = 0.

API surface
-----------
Super admin (require `super_admin` role):
    GET    /api/super-admin/studio-storage/plans
    POST   /api/super-admin/studio-storage/plans
    PUT    /api/super-admin/studio-storage/plans/{plan_id}
    DELETE /api/super-admin/studio-storage/plans/{plan_id}
    GET    /api/super-admin/studio-storage/subscriptions       (overview)

Photographer (require legacy admin JWT):
    GET    /api/admin/studio-storage/plans                     (active plans only)
    GET    /api/admin/studio-storage/my-plan                   (subscription + usage)
    POST   /api/admin/studio-storage/subscribe                 (create Razorpay order)
    POST   /api/admin/studio-storage/verify-payment            (verify + activate / renew)
    POST   /api/admin/studio-storage/upload                    (multipart upload)
    GET    /api/admin/studio-storage/files                     (list)
    DELETE /api/admin/studio-storage/files/{file_id}

Storage layout in S3:
    studio/{admin_id}/{file_id}{ext}

NOTE
----
- This module is self-contained: it exposes a `router` that server.py
  mounts. It does NOT depend on any helper that isn't already imported
  elsewhere in the codebase (uses `aws_service.s3 / bucket / upload_bytes
  / delete_prefix / generate_signed_url`).
- Subscription state derivation (active / grace / expired) is computed
  on every read so we don't need a cron job to flip flags. Actual S3
  purge of expired subscriptions is handled by the `purge_expired()`
  helper which can be called from any existing scheduled-task entry
  point (or on first access after purge_at).
"""

from __future__ import annotations

import os
import io
import time
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

import razorpay
from aws_service import s3, bucket, upload_bytes, delete_prefix, generate_signed_url
from auth import get_current_admin_with_role, require_super_admin

logger = logging.getLogger("studio_storage")
router = APIRouter()


# ============================================================
# Defaults — used to seed a brand-new install with sensible plans
# the super admin can later edit/delete from the UI.
# ============================================================
DEFAULT_PLANS: List[Dict[str, Any]] = [
    {"name": "10 GB / 1 month",  "gb_limit": 10,   "duration_days": 30,
     "grace_days": 30, "price_inr": 299},
    {"name": "100 GB / 3 months","gb_limit": 100,  "duration_days": 90,
     "grace_days": 30, "price_inr": 1499},
    {"name": "1 TB / 6 months",  "gb_limit": 1024, "duration_days": 180,
     "grace_days": 30, "price_inr": 4999},
]


# ============================================================
# Pydantic schemas
# ============================================================
class StoragePlanIn(BaseModel):
    name: str
    gb_limit: int = Field(..., gt=0, le=1024 * 100)        # max 100 TB
    duration_days: int = Field(..., gt=0, le=3650)         # max 10 years
    grace_days: int = Field(0, ge=0, le=365)
    price_inr: int = Field(..., ge=0, le=10_000_000)       # rupees
    is_active: bool = True


class StoragePlanOut(StoragePlanIn):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SubscribeRequest(BaseModel):
    plan_id: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan_id: str


# ============================================================
# Internal helpers
# ============================================================
def _now() -> datetime:
    return datetime.utcnow()


def _strip_id(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not doc:
        return None
    doc.pop("_id", None)
    return doc


def _file_key(admin_id: str, file_id: str, ext: str) -> str:
    safe_ext = (ext or "").lstrip(".").lower()
    if safe_ext:
        return f"studio/{admin_id}/{file_id}.{safe_ext}"
    return f"studio/{admin_id}/{file_id}"


async def _ensure_default_plans(db) -> None:
    """Idempotent: insert default plans only if the collection is empty."""
    count = await db.studio_storage_plans.count_documents({})
    if count > 0:
        return
    now = _now()
    docs = []
    for p in DEFAULT_PLANS:
        docs.append({
            "id": f"plan_{uuid.uuid4().hex[:10]}",
            **p,
            "created_at": now,
            "updated_at": now,
        })
    if docs:
        await db.studio_storage_plans.insert_many(docs)


def _derive_status(sub: Dict[str, Any], now: datetime) -> str:
    """Compute the live status based on timestamps."""
    if not sub:
        return "none"
    if sub.get("status") == "expired":
        return "expired"
    expires_at = sub.get("expires_at")
    purge_at = sub.get("purge_at")
    if expires_at and now < expires_at:
        return "active"
    if purge_at and now < purge_at:
        return "grace"
    return "expired"


async def _get_admin_sub(db, admin_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recently created subscription for this admin."""
    sub = await db.studio_storage_subscriptions.find_one(
        {"admin_id": admin_id},
        sort=[("created_at", -1)],
    )
    return _strip_id(sub)


# ============================================================
# Auth dependencies
# ============================================================
# `get_current_admin_with_role` returns {'admin_id', 'role'} which is exactly
# the dict shape every route in this file consumes. `require_super_admin`
# already enforces the role check at the framework boundary and returns an
# admin_id string — we wrap it so the downstream code can keep using
# admin["admin_id"] uniformly.
async def current_admin_dep(
    admin_data: Dict[str, Any] = Depends(get_current_admin_with_role),
) -> Dict[str, Any]:
    return admin_data


async def current_super_admin_dep(
    admin_id: str = Depends(require_super_admin),
) -> Dict[str, Any]:
    return {"admin_id": admin_id, "role": "super_admin"}


def init(database, razorpay_client):
    """Bind shared dependencies. Called once from server.py during startup."""
    global _db, _razorpay_client
    _db = database
    _razorpay_client = razorpay_client


# Injected by server.py at startup
_db = None
_razorpay_client: Optional[razorpay.Client] = None


# ============================================================
# Super admin — plan CRUD
# ============================================================
@router.get("/super-admin/studio-storage/plans")
async def list_plans_admin(_admin: Dict[str, Any] = Depends(current_super_admin_dep)):
    await _ensure_default_plans(_db)
    cursor = _db.studio_storage_plans.find({}).sort("price_inr", 1)
    out = []
    async for doc in cursor:
        out.append(_strip_id(doc))
    return {"items": out}


@router.post("/super-admin/studio-storage/plans", response_model=StoragePlanOut)
async def create_plan(plan: StoragePlanIn,
                      _admin: Dict[str, Any] = Depends(current_super_admin_dep)):
    doc = plan.dict()
    doc["id"] = f"plan_{uuid.uuid4().hex[:10]}"
    doc["created_at"] = _now()
    doc["updated_at"] = doc["created_at"]
    await _db.studio_storage_plans.insert_one(doc)
    return _strip_id(doc)


@router.put("/super-admin/studio-storage/plans/{plan_id}", response_model=StoragePlanOut)
async def update_plan(plan_id: str, plan: StoragePlanIn,
                      _admin: Dict[str, Any] = Depends(current_super_admin_dep)):
    doc = plan.dict()
    doc["updated_at"] = _now()
    res = await _db.studio_storage_plans.find_one_and_update(
        {"id": plan_id},
        {"$set": doc},
        return_document=True,
    )
    if not res:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _strip_id(res)


@router.delete("/super-admin/studio-storage/plans/{plan_id}")
async def delete_plan(plan_id: str,
                      _admin: Dict[str, Any] = Depends(current_super_admin_dep)):
    res = await _db.studio_storage_plans.delete_one({"id": plan_id})
    if not res.deleted_count:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"deleted": True}


@router.get("/super-admin/studio-storage/subscriptions")
async def list_subscriptions_admin(
    _admin: Dict[str, Any] = Depends(current_super_admin_dep)
):
    """Quick overview of every photographer's subscription + storage usage."""
    now = _now()
    cursor = _db.studio_storage_subscriptions.find({}).sort("created_at", -1)
    items = []
    async for sub in cursor:
        sub = _strip_id(sub)
        sub["status"] = _derive_status(sub, now)
        items.append(sub)
    return {"items": items}


# ============================================================
# Photographer — plans + subscription
# ============================================================
@router.get("/admin/studio-storage/plans")
async def list_plans_photographer(_admin: Dict[str, Any] = Depends(current_admin_dep)):
    await _ensure_default_plans(_db)
    cursor = _db.studio_storage_plans.find({"is_active": True}).sort("price_inr", 1)
    out = []
    async for doc in cursor:
        out.append(_strip_id(doc))
    return {"items": out}


@router.get("/admin/studio-storage/my-plan")
async def get_my_plan(admin: Dict[str, Any] = Depends(current_admin_dep)):
    admin_id = admin.get("admin_id") or admin.get("id")
    sub = await _get_admin_sub(_db, admin_id)
    if not sub:
        return {"subscription": None, "plan": None, "usage": None}

    now = _now()
    status = _derive_status(sub, now)
    sub["status"] = status

    # Auto-purge if past purge_at
    if status == "expired" and sub.get("used_bytes", 0) > 0:
        try:
            delete_prefix(f"studio/{admin_id}/")
        except Exception as e:
            logger.warning("S3 purge failed for %s: %s", admin_id, e)
        await _db.studio_storage_files.delete_many({"admin_id": admin_id})
        await _db.studio_storage_subscriptions.update_one(
            {"id": sub["id"]},
            {"$set": {"status": "expired", "used_bytes": 0,
                      "purged_at": now}},
        )
        sub["used_bytes"] = 0

    plan = await _db.studio_storage_plans.find_one({"id": sub.get("plan_id")})
    plan = _strip_id(plan)
    used = sub.get("used_bytes", 0) or 0
    cap = (plan or {}).get("gb_limit", 0) * 1024 * 1024 * 1024
    return {
        "subscription": sub,
        "plan": plan,
        "usage": {
            "used_bytes": used,
            "cap_bytes": cap,
            "percent": round((used / cap) * 100, 1) if cap else 0,
        },
    }


@router.post("/admin/studio-storage/subscribe")
async def subscribe(req: SubscribeRequest,
                    admin: Dict[str, Any] = Depends(current_admin_dep)):
    """Create a Razorpay order for the chosen plan. Activation happens on verify."""
    if _razorpay_client is None:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    plan = await _db.studio_storage_plans.find_one({"id": req.plan_id, "is_active": True})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")

    amount_paise = int(plan["price_inr"]) * 100
    try:
        order = _razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "plan_id": plan["id"],
                "admin_id": admin.get("admin_id") or admin.get("id") or "",
                "type": "studio_storage",
            },
        })
    except Exception as e:
        logger.exception("Razorpay order create failed: %s", e)
        raise HTTPException(status_code=502, detail="Could not create payment order")

    return {
        "order_id": order["id"],
        "amount": amount_paise,
        "currency": "INR",
        "key_id": os.environ.get("RAZORPAY_KEY_ID", ""),
        "plan": _strip_id(plan),
    }


@router.post("/admin/studio-storage/verify-payment")
async def verify_payment(req: VerifyPaymentRequest,
                         admin: Dict[str, Any] = Depends(current_admin_dep)):
    """Verify Razorpay signature → create or renew subscription."""
    if _razorpay_client is None:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")
    secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Payment gateway not configured")

    # Verify the HMAC signature against (order_id|payment_id).
    generated = hmac.new(
        secret.encode(),
        f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(generated, req.razorpay_signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    plan = await _db.studio_storage_plans.find_one({"id": req.plan_id})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    admin_id = admin.get("admin_id") or admin.get("id")
    now = _now()
    existing = await _get_admin_sub(_db, admin_id)
    duration = timedelta(days=int(plan["duration_days"]))
    grace = timedelta(days=int(plan.get("grace_days", 0)))

    if existing and _derive_status(existing, now) in ("active", "grace"):
        # Renewal: extend from current expires_at (or now if grace)
        base = existing["expires_at"] if existing.get("expires_at", now) > now else now
        new_expires = base + duration
        new_purge = new_expires + grace
        await _db.studio_storage_subscriptions.update_one(
            {"id": existing["id"]},
            {"$set": {
                "plan_id": plan["id"],
                "expires_at": new_expires,
                "purge_at": new_purge,
                "status": "active",
                "updated_at": now,
                "last_razorpay_order_id": req.razorpay_order_id,
                "last_razorpay_payment_id": req.razorpay_payment_id,
            }},
        )
        sub = await _db.studio_storage_subscriptions.find_one({"id": existing["id"]})
        return {"renewed": True, "subscription": _strip_id(sub)}

    # Fresh subscription
    starts_at = now
    expires_at = starts_at + duration
    purge_at = expires_at + grace
    doc = {
        "id": f"sub_{uuid.uuid4().hex[:10]}",
        "admin_id": admin_id,
        "plan_id": plan["id"],
        "starts_at": starts_at,
        "expires_at": expires_at,
        "purge_at": purge_at,
        "status": "active",
        "used_bytes": 0,
        "created_at": now,
        "updated_at": now,
        "razorpay_order_id": req.razorpay_order_id,
        "razorpay_payment_id": req.razorpay_payment_id,
    }
    await _db.studio_storage_subscriptions.insert_one(doc)
    return {"renewed": False, "subscription": _strip_id(doc)}


# ============================================================
# Photographer — file ops
# ============================================================
ALLOWED_TYPES = {
    "image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif",
    "video/mp4", "video/quicktime", "video/x-msvideo",
    "application/zip", "application/x-zip-compressed",
}
MAX_SINGLE_UPLOAD = 500 * 1024 * 1024     # 500 MB per file


@router.post("/admin/studio-storage/upload")
async def upload_file(
    file: UploadFile = File(...),
    admin: Dict[str, Any] = Depends(current_admin_dep),
):
    admin_id = admin.get("admin_id") or admin.get("id")
    sub = await _get_admin_sub(_db, admin_id)
    if not sub:
        raise HTTPException(status_code=402, detail="No active studio storage subscription")
    now = _now()
    status = _derive_status(sub, now)
    if status != "active":
        # Uploads are blocked during grace and once expired.
        raise HTTPException(
            status_code=402,
            detail=f"Subscription is {status}. Renew to upload more files.",
        )

    plan = await _db.studio_storage_plans.find_one({"id": sub["plan_id"]})
    cap_bytes = int(plan["gb_limit"]) * 1024 * 1024 * 1024

    if file.content_type not in ALLOWED_TYPES and not (file.filename or "").lower().endswith(
        (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".mp4", ".mov", ".avi", ".zip")
    ):
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {file.content_type}")

    # Read file (streamed) and enforce per-file + cumulative cap
    data = await file.read()
    size = len(data)
    if size > MAX_SINGLE_UPLOAD:
        raise HTTPException(status_code=413, detail="File too large (max 500 MB per upload)")
    used_after = (sub.get("used_bytes", 0) or 0) + size
    if used_after > cap_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Storage cap reached. {used_after / 1e9:.1f} GB requested, {cap_bytes / 1e9:.0f} GB cap.",
        )

    file_id = f"sf_{uuid.uuid4().hex[:14]}"
    name = file.filename or "upload"
    ext = os.path.splitext(name)[1]
    key = _file_key(admin_id, file_id, ext)

    try:
        upload_bytes(key, data, file.content_type or "application/octet-stream",
                     tags={"kind": "studio-backup", "admin_id": admin_id})
    except Exception as e:
        logger.exception("S3 upload failed: %s", e)
        raise HTTPException(status_code=502, detail="Storage upload failed")

    file_doc = {
        "id": file_id,
        "admin_id": admin_id,
        "subscription_id": sub["id"],
        "name": name,
        "size_bytes": size,
        "content_type": file.content_type or "application/octet-stream",
        "s3_key": key,
        "uploaded_at": now,
    }
    await _db.studio_storage_files.insert_one(file_doc)
    await _db.studio_storage_subscriptions.update_one(
        {"id": sub["id"]},
        {"$inc": {"used_bytes": size}, "$set": {"updated_at": now}},
    )
    return {"file": _strip_id(file_doc), "new_used_bytes": used_after}


@router.get("/admin/studio-storage/files")
async def list_files(
    limit: int = 100,
    offset: int = 0,
    admin: Dict[str, Any] = Depends(current_admin_dep),
):
    admin_id = admin.get("admin_id") or admin.get("id")
    sub = await _get_admin_sub(_db, admin_id)
    if not sub:
        return {"items": [], "total": 0}

    cursor = (
        _db.studio_storage_files
        .find({"admin_id": admin_id})
        .sort("uploaded_at", -1)
        .skip(max(0, offset))
        .limit(min(max(1, limit), 500))
    )
    items: List[Dict[str, Any]] = []
    async for doc in cursor:
        doc = _strip_id(doc)
        try:
            doc["download_url"] = generate_signed_url(doc["s3_key"], expiry_seconds=3600)
        except Exception as e:
            logger.warning("signed url failed: %s", e)
            doc["download_url"] = None
        items.append(doc)
    total = await _db.studio_storage_files.count_documents({"admin_id": admin_id})
    return {"items": items, "total": total}


@router.delete("/admin/studio-storage/files/{file_id}")
async def delete_file(file_id: str,
                      admin: Dict[str, Any] = Depends(current_admin_dep)):
    admin_id = admin.get("admin_id") or admin.get("id")
    doc = await _db.studio_storage_files.find_one({"id": file_id, "admin_id": admin_id})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        s3().delete_object(Bucket=bucket(), Key=doc["s3_key"])
    except Exception as e:
        logger.warning("S3 delete failed (continuing): %s", e)
    await _db.studio_storage_files.delete_one({"id": file_id})

    # Decrement usage (clamp to zero)
    sub = await _get_admin_sub(_db, admin_id)
    if sub:
        new_used = max(0, (sub.get("used_bytes", 0) or 0) - int(doc.get("size_bytes", 0)))
        await _db.studio_storage_subscriptions.update_one(
            {"id": sub["id"]},
            {"$set": {"used_bytes": new_used, "updated_at": _now()}},
        )
    return {"deleted": True}
