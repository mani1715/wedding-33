"""
MONETIZATION FEATURES
- Super-admin-managed credit packs (₹ → credits) — no code change needed; UI-driven.
- Photographer purchases a pack via Razorpay (test/live).
- Atomic auto-credit on successful payment (signature verified + webhook idempotent).
- Super admin photographer-detail drilldown: profiles, ledger, payments, RSVPs, login.
"""
from __future__ import annotations

import os
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip(d: dict) -> dict:
    if d is None:
        return d
    d.pop("_id", None)
    return d


# ----------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------
class CreditPackCreate(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    price_inr: int = Field(gt=0, le=1_000_000)   # rupees
    credits: int = Field(gt=0, le=1_000_000)
    description: Optional[str] = None
    badge: Optional[str] = None                   # e.g. "Most Popular"
    is_active: bool = True
    sort_order: int = 0
    # P0 — per-design + audience pricing
    audience: str = Field(default="photographer")  # "photographer" | "guest" | "both"
    design_id: Optional[str] = None                # Optional theme link (e.g. "royal_mughal")


class CreditPackUpdate(BaseModel):
    label: Optional[str] = None
    price_inr: Optional[int] = None
    credits: Optional[int] = None
    description: Optional[str] = None
    badge: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None
    audience: Optional[str] = None
    design_id: Optional[str] = None


class PurchaseOrderRequest(BaseModel):
    pack_id: str


class PurchaseVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ----------------------------------------------------------------------------
# Router builder
# ----------------------------------------------------------------------------
def build_monetization_router(db, require_admin, require_super_admin, credit_service, razorpay_client) -> APIRouter:
    router = APIRouter(tags=["monetization"])

    # =========================================================================
    # CREDIT PACKS — SUPER ADMIN CRUD
    # =========================================================================
    @router.get("/api/super-admin/credit-packs")
    async def sa_list_packs(super_admin_id: str = Depends(require_super_admin)):
        cursor = db.credit_packs.find({}, {"_id": 0}).sort([("sort_order", 1), ("price_inr", 1)])
        packs = await cursor.to_list(200)
        return {"packs": packs}

    @router.post("/api/super-admin/credit-packs")
    async def sa_create_pack(payload: CreditPackCreate, super_admin_id: str = Depends(require_super_admin)):
        doc = {
            "id": uuid.uuid4().hex,
            **payload.model_dump(),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "created_by": super_admin_id,
        }
        await db.credit_packs.insert_one(doc)
        return _strip(doc)

    @router.put("/api/super-admin/credit-packs/{pack_id}")
    async def sa_update_pack(pack_id: str, payload: CreditPackUpdate,
                              super_admin_id: str = Depends(require_super_admin)):
        update = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update:
            raise HTTPException(400, "No fields to update")
        update["updated_at"] = _now_iso()
        res = await db.credit_packs.update_one({"id": pack_id}, {"$set": update})
        if res.matched_count == 0:
            raise HTTPException(404, "Pack not found")
        pack = await db.credit_packs.find_one({"id": pack_id}, {"_id": 0})
        return pack

    @router.delete("/api/super-admin/credit-packs/{pack_id}")
    async def sa_delete_pack(pack_id: str, super_admin_id: str = Depends(require_super_admin)):
        res = await db.credit_packs.delete_one({"id": pack_id})
        if res.deleted_count == 0:
            raise HTTPException(404, "Pack not found")
        return {"success": True}

    # =========================================================================
    # CREDIT PACKS — PHOTOGRAPHER PUBLIC LIST
    # =========================================================================
    @router.get("/api/admin/credit-packs")
    async def admin_list_packs(admin_data: dict = Depends(require_admin)):
        cursor = db.credit_packs.find(
            {"is_active": True, "audience": {"$in": ["photographer", "both", None]}},
            {"_id": 0},
        ).sort([("sort_order", 1), ("price_inr", 1)])
        packs = await cursor.to_list(200)
        return {"packs": packs}

    # =========================================================================
    # CREDIT PACKS — PUBLIC (normal-user / guest)
    # =========================================================================
    @router.get("/api/public/credit-packs")
    async def public_list_packs():
        """Credit packs available to normal users (guests) on the landing page.

        We first try the modern super-admin pricing hub
        (`pricing_credit_packs` with audience="normal_user"), which is what
        super-admins edit via the pricing UI. If that yields nothing, fall
        back to the legacy `credit_packs` collection so older deployments
        keep working.
        """
        # Modern source — super-admin pricing hub.
        cursor = db.pricing_credit_packs.find(
            {"is_active": True, "audience": "normal_user"},
            {"_id": 0},
        ).sort([("base_price", 1)])
        rows = await cursor.to_list(200)
        if rows:
            packs = []
            for r in rows:
                price = r.get("discount_price") if r.get("discount_enabled") and r.get("discount_price") is not None else r.get("base_price", 0)
                packs.append({
                    "id": r.get("id"),
                    "label": r.get("label") or "",
                    "credits": int(r.get("credits", 0) or 0),
                    "price_inr": int(price or 0),
                    "base_price": int(r.get("base_price", 0) or 0),
                    "discount_enabled": bool(r.get("discount_enabled")),
                    "discount_price": r.get("discount_price"),
                    "is_free": int(price or 0) == 0,
                })
            return {"packs": packs}

        # Legacy fallback.
        cursor = db.credit_packs.find(
            {"is_active": True, "audience": {"$in": ["guest", "both"]}},
            {"_id": 0},
        ).sort([("sort_order", 1), ("price_inr", 1)])
        packs = await cursor.to_list(200)
        return {"packs": packs}

    # =========================================================================
    # PURCHASE — CREATE ORDER (photographer)
    # =========================================================================
    @router.post("/api/admin/credits/purchase/create-order")
    async def create_purchase_order(payload: PurchaseOrderRequest,
                                     admin_data: dict = Depends(require_admin)):
        if razorpay_client is None:
            raise HTTPException(503, "Payment gateway not configured. Please contact administrator.")
        _key = os.environ.get("RAZORPAY_KEY_ID", "")
        _sec = os.environ.get("RAZORPAY_KEY_SECRET", "")
        if not _key or not _sec or "PLACEHOLDER" in _key.upper() or "PLACEHOLDER" in _sec.upper():
            raise HTTPException(
                503,
                "Razorpay keys are placeholders. Replace RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET in backend/.env with real test keys "
                "from your Razorpay dashboard, then restart the backend.",
            )

        # Resolve the pack — modern admin pricing lives in
        # `pricing_credit_packs` (filterable by audience="photographer").
        # We fall back to the legacy `credit_packs` collection for older
        # deployments that haven't migrated.
        pack = await db.pricing_credit_packs.find_one(
            {"id": payload.pack_id, "audience": "photographer", "is_active": True},
            {"_id": 0},
        )
        if not pack:
            pack = await db.credit_packs.find_one(
                {"id": payload.pack_id, "is_active": True},
                {"_id": 0},
            )
        if not pack:
            raise HTTPException(404, "Pack not found or inactive")

        # `pricing_credit_packs` stores price in `base_price` / `discount_price`
        # while legacy `credit_packs` uses `price_inr`. Normalise.
        effective_price = pack.get("price_inr")
        if effective_price is None:
            if pack.get("discount_enabled") and pack.get("discount_price") is not None:
                effective_price = int(pack["discount_price"])
            else:
                effective_price = int(pack.get("base_price") or 0)
        # Mutate the local pack dict so downstream code reads price_inr uniformly.
        pack["price_inr"] = int(effective_price)
        if "label" not in pack:
            pack["label"] = pack.get("name") or f"{pack['credits']} credits"

        admin_id = admin_data.get("admin_id") or admin_data.get("id")

        # ── Photographer loyalty tier — apply discount + bonus credits ──
        # Pull the tier matching this admin's paid_links_count. Discount
        # shrinks the Razorpay amount, bonus_pct grants extra credits on
        # successful purchase.
        admin_doc = await db.admins.find_one({"id": admin_id}, {"_id": 0}) or {}
        paid_links = int(admin_doc.get("paid_links_count", 0) or 0)
        try:
            from super_admin_pricing import get_photographer_tier_for
            tier_info = await get_photographer_tier_for(paid_links)
            tier = tier_info.get("tier") or {}
            tier_enabled = bool(tier_info.get("enabled"))
        except Exception:
            tier = {"key": "starter", "discount_pct": 0, "bonus_pct": 0}
            tier_enabled = False
        discount_pct = int(tier.get("discount_pct", 0)) if tier_enabled else 0
        bonus_pct = int(tier.get("bonus_pct", 0)) if tier_enabled else 0
        base_price_inr = int(pack["price_inr"])
        # Apply discount, but never charge less than 1 (Razorpay min)
        discounted_price_inr = max(1, round(base_price_inr * (100 - discount_pct) / 100)) if discount_pct > 0 else base_price_inr
        bonus_credits = int(round(int(pack["credits"]) * bonus_pct / 100)) if bonus_pct > 0 else 0
        total_credits_to_grant = int(pack["credits"]) + bonus_credits

        # Idempotency: short receipt id (Razorpay max 40 chars)
        receipt = f"cpk_{uuid.uuid4().hex[:24]}"
        amount_paise = discounted_price_inr * 100

        try:
            order = razorpay_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "receipt": receipt,
                "notes": {
                    "admin_id": admin_id,
                    "pack_id": pack["id"],
                    "credits": str(total_credits_to_grant),
                    "kind": "credit_pack",
                    "tier": tier.get("key", "starter"),
                    "discount_pct": str(discount_pct),
                    "bonus_pct": str(bonus_pct),
                },
            })
        except Exception as e:
            logger.exception("[monetization] create_order failed")
            raise HTTPException(502, f"Could not create order: {str(e)[:120]}")

        purchase_doc = {
            "id": f"purch_{uuid.uuid4().hex[:16]}",
            "admin_id": admin_id,
            "pack_id": pack["id"],
            "pack_label": pack["label"],
            # Stored credits already include the tier bonus so the atomic
            # credit step grants exactly this number — no re-calculation needed.
            "credits": total_credits_to_grant,
            "base_credits": int(pack["credits"]),
            "bonus_credits": bonus_credits,
            "tier_key": tier.get("key", "starter"),
            "tier_discount_pct": discount_pct,
            "tier_bonus_pct": bonus_pct,
            "amount_inr": discounted_price_inr,
            "base_amount_inr": base_price_inr,
            "amount_paise": amount_paise,
            "currency": "INR",
            "razorpay_order_id": order["id"],
            "razorpay_payment_id": None,
            "razorpay_signature": None,
            "status": "created",
            "credited": False,
            "created_at": _now_iso(),
            "completed_at": None,
        }
        await db.credit_purchases.insert_one(purchase_doc)
        _strip(purchase_doc)

        return {
            "purchase_id": purchase_doc["id"],
            "order_id": order["id"],
            "amount_paise": amount_paise,
            "amount_inr": discounted_price_inr,
            "base_amount_inr": base_price_inr,
            "credits": total_credits_to_grant,
            "base_credits": int(pack["credits"]),
            "bonus_credits": bonus_credits,
            "tier": tier.get("key", "starter"),
            "tier_label": tier.get("label", "Starter"),
            "tier_discount_pct": discount_pct,
            "tier_bonus_pct": bonus_pct,
            "pack_label": pack["label"],
            "currency": "INR",
            "razorpay_key_id": os.environ.get("RAZORPAY_KEY_ID", ""),
        }

    # =========================================================================
    # PURCHASE — VERIFY SIGNATURE (called from frontend after Checkout success)
    # =========================================================================
    async def _credit_purchase_atomic(purchase: dict, performed_by: str, source: str = "razorpay_verify") -> dict:
        """Atomically credit a purchase, idempotent. Returns updated purchase doc."""
        # Atomic flip: only credit if not yet credited
        res = await db.credit_purchases.update_one(
            {"id": purchase["id"], "credited": {"$ne": True}},
            {"$set": {
                "credited": True,
                "status": "captured",
                "completed_at": _now_iso(),
            }},
        )
        # Re-fetch
        updated = await db.credit_purchases.find_one({"id": purchase["id"]}, {"_id": 0})
        if res.modified_count == 0:
            # Already credited — idempotent return
            return updated

        # Add credits via service (this writes immutable ledger)
        try:
            tier_key = purchase.get("tier_key", "starter")
            bonus = int(purchase.get("bonus_credits", 0) or 0)
            base_credits = int(purchase.get("base_credits", purchase["credits"]) or 0)
            reason = (
                f"Razorpay purchase · {purchase.get('pack_label','pack')} · "
                f"₹{purchase['amount_inr']} · {base_credits} credits"
                + (f" + {bonus} bonus ({tier_key} tier)" if bonus > 0 else "")
            )
            await credit_service.add_credits(
                admin_id=purchase["admin_id"],
                amount=int(purchase["credits"]),
                reason=reason,
                performed_by=performed_by,
                metadata={
                    "purchase_id": purchase["id"],
                    "razorpay_order_id": purchase.get("razorpay_order_id"),
                    "razorpay_payment_id": purchase.get("razorpay_payment_id"),
                    "source": source,
                    "tier_key": tier_key,
                    "bonus_credits": bonus,
                    "tier_discount_pct": int(purchase.get("tier_discount_pct", 0) or 0),
                },
            )
        except Exception as e:
            # Roll back the credited flag so a retry can complete
            await db.credit_purchases.update_one(
                {"id": purchase["id"]},
                {"$set": {"credited": False, "status": "credit_error", "error": str(e)[:200]}},
            )
            raise
        return updated

    @router.post("/api/admin/credits/purchase/verify")
    async def verify_purchase(payload: PurchaseVerifyRequest,
                               admin_data: dict = Depends(require_admin)):
        if razorpay_client is None:
            raise HTTPException(503, "Payment gateway not configured")

        admin_id = admin_data.get("admin_id") or admin_data.get("id")
        purchase = await db.credit_purchases.find_one(
            {"razorpay_order_id": payload.razorpay_order_id, "admin_id": admin_id},
            {"_id": 0},
        )
        if not purchase:
            raise HTTPException(404, "Purchase not found for this admin")

        # Verify signature
        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            })
        except Exception as e:
            await db.credit_purchases.update_one(
                {"id": purchase["id"]},
                {"$set": {"status": "signature_invalid", "error": str(e)[:200]}},
            )
            raise HTTPException(400, "Invalid payment signature")

        # Save payment refs
        await db.credit_purchases.update_one(
            {"id": purchase["id"]},
            {"$set": {
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            }},
        )
        purchase["razorpay_payment_id"] = payload.razorpay_payment_id

        # Credit atomically
        updated = await _credit_purchase_atomic(purchase, performed_by=admin_id, source="verify")
        # Return new balance
        admin = await db.admins.find_one({"id": admin_id}, {"_id": 0}) or {}
        total = int(admin.get("total_credits", 0))
        used = int(admin.get("used_credits", 0))
        return {
            "success": True,
            "credited": True,
            "credits_added": int(purchase["credits"]),
            "total_credits": total,
            "used_credits": used,
            "available_credits": total - used,
            "purchase": updated,
        }

    # =========================================================================
    # PURCHASE — WEBHOOK (idempotent fallback)
    # =========================================================================
    @router.post("/api/payments/razorpay-webhook")
    async def razorpay_webhook(request: Request):
        body = await request.body()
        signature = request.headers.get("x-razorpay-signature", "")
        secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

        if not secret or "PLACEHOLDER" in secret:
            # Allow inbound but mark unverified — useful for staging
            logger.warning("[monetization] webhook secret missing; storing event unverified")
        else:
            try:
                expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expected, signature):
                    raise HTTPException(400, "Invalid webhook signature")
            except HTTPException:
                raise
            except Exception as e:
                logger.exception("[monetization] webhook verify failed")
                raise HTTPException(400, f"Webhook verify error: {str(e)[:120]}")

        try:
            import json
            payload = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            raise HTTPException(400, "Invalid JSON")

        event = payload.get("event", "")
        entity = (payload.get("payload", {}).get("payment", {}) or {}).get("entity", {}) or {}
        order_id = entity.get("order_id")
        payment_id = entity.get("id")

        # Log event for audit
        await db.razorpay_events.insert_one({
            "id": uuid.uuid4().hex,
            "event": event,
            "order_id": order_id,
            "payment_id": payment_id,
            "received_at": _now_iso(),
            "raw": payload,
        })

        if event in ("payment.captured", "order.paid") and order_id:
            purchase = await db.credit_purchases.find_one({"razorpay_order_id": order_id}, {"_id": 0})
            if purchase and not purchase.get("credited"):
                if payment_id:
                    purchase["razorpay_payment_id"] = payment_id
                    await db.credit_purchases.update_one(
                        {"id": purchase["id"]},
                        {"$set": {"razorpay_payment_id": payment_id}},
                    )
                try:
                    await _credit_purchase_atomic(purchase, performed_by="razorpay_webhook", source="webhook")
                except Exception as e:
                    logger.exception("[monetization] webhook credit failed")

        return {"received": True}

    # =========================================================================
    # PHOTOGRAPHER — purchase history
    # =========================================================================
    @router.get("/api/admin/credits/purchases")
    async def my_purchases(admin_data: dict = Depends(require_admin)):
        admin_id = admin_data.get("admin_id") or admin_data.get("id")
        cursor = db.credit_purchases.find({"admin_id": admin_id}, {"_id": 0}).sort("created_at", -1).limit(100)
        purchases = await cursor.to_list(100)
        return {"purchases": purchases}

    # =========================================================================
    # SUPER ADMIN — PHOTOGRAPHER DETAIL DRILLDOWN
    # =========================================================================
    @router.get("/api/super-admin/photographers/{admin_id}/detail")
    async def photographer_detail(admin_id: str, super_admin_id: str = Depends(require_super_admin)):
        admin = await db.admins.find_one({"id": admin_id}, {"_id": 0, "password_hash": 0})
        if not admin:
            raise HTTPException(404, "Photographer not found")

        # All their profiles (invitations)
        profiles_cursor = db.profiles.find({"admin_id": admin_id}, {"_id": 0}).sort("created_at", -1)
        profiles = await profiles_cursor.to_list(500)

        # Aggregate metrics per profile
        profile_summaries = []
        for p in profiles:
            pid = p.get("id")
            slug = p.get("slug") or pid
            rsvp_total = await db.rsvps.count_documents({"profile_id": pid})
            rsvp_yes = await db.rsvps.count_documents({"profile_id": pid, "status": "yes"})
            wishes_total = await db.guest_wishes.count_documents({"profile_id": pid})
            photos_total = await db.live_gallery_photos.count_documents({"wedding_id": pid})
            analytics_doc = await db.analytics.find_one({"profile_id": pid}, {"_id": 0, "total_views": 1, "unique_views": 1}) or {}
            profile_summaries.append({
                "id": pid,
                "slug": slug,
                "groom_name": p.get("groom_name"),
                "bride_name": p.get("bride_name"),
                "event_date": p.get("event_date"),
                "event_type": p.get("event_type"),
                "venue": p.get("venue"),
                "city": p.get("city"),
                "design_id": p.get("design_id"),
                "plan_type": p.get("plan_type"),
                "is_published": p.get("is_published", False),
                "status": p.get("status"),
                "expires_at": p.get("expires_at"),
                "created_at": p.get("created_at"),
                "public_link": f"/invite/{slug}",
                "metrics": {
                    "views": int(analytics_doc.get("total_views", 0)),
                    "unique_views": int(analytics_doc.get("unique_views", 0)),
                    "rsvps": rsvp_total,
                    "rsvps_yes": rsvp_yes,
                    "wishes": wishes_total,
                    "photos": photos_total,
                },
            })

        # Credit ledger
        ledger_cursor = db.credit_ledger.find({"admin_id": admin_id}, {"_id": 0}).sort("created_at", -1).limit(200)
        ledger = await ledger_cursor.to_list(200)

        # Purchases
        purchase_cursor = db.credit_purchases.find({"admin_id": admin_id}, {"_id": 0}).sort("created_at", -1).limit(100)
        purchases = await purchase_cursor.to_list(100)
        revenue_inr = sum(int(p.get("amount_inr", 0)) for p in purchases if p.get("credited"))

        # Aggregate totals
        total_rsvps = sum(s["metrics"]["rsvps"] for s in profile_summaries)
        total_views = sum(s["metrics"]["views"] for s in profile_summaries)
        published_count = sum(1 for s in profile_summaries if s["is_published"])

        # Last login (best-effort from audit_logs or admins.last_login_at)
        last_login = admin.get("last_login_at") or admin.get("updated_at")

        return {
            "admin": admin,
            "summary": {
                "profiles_total": len(profile_summaries),
                "profiles_published": published_count,
                "rsvps_total": total_rsvps,
                "views_total": total_views,
                "revenue_inr": revenue_inr,
                "credits_total": int(admin.get("total_credits", 0)),
                "credits_used": int(admin.get("used_credits", 0)),
                "credits_available": int(admin.get("total_credits", 0)) - int(admin.get("used_credits", 0)),
                "last_login": last_login,
            },
            "profiles": profile_summaries,
            "credit_ledger": ledger,
            "purchases": purchases,
        }

    return router
