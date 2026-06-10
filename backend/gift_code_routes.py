"""
Gift Code (Redemption Code) system — sits on top of `/credits/gift`.

Super Admin generates short alphanumeric codes (e.g. `LOVE26`) that grant
N credits when redeemed by any signed-in account holder. Useful for early-
access marketing, conference giveaways, partnership perks.

Collection: `gift_codes`
Schema:
    code:             str   (primary, uppercased, 4–16 chars)
    credits:          int   > 0
    description:      str   short marketing note ("Conference 2026")
    max_redemptions:  int|None  None = unlimited
    redeemed_count:   int   default 0
    per_account_limit:int   how many times one admin_id can redeem (default 1)
    expires_at:       isoformat str | None
    is_active:        bool  default True
    created_by:       super_admin id
    created_at:       iso str
    metadata:         dict  optional

Collection: `gift_code_redemptions` (append-only audit log)
Schema:
    code, admin_id, credits, redeemed_at, ledger_id

Endpoints
    Super Admin:
      POST   /api/super-admin/gift-codes              — create
      GET    /api/super-admin/gift-codes              — list (newest first)
      PATCH  /api/super-admin/gift-codes/{code}       — toggle active, edit credits/expiry
      DELETE /api/super-admin/gift-codes/{code}       — soft-delete (is_active=False)
      GET    /api/super-admin/gift-codes/{code}/redemptions

    Self-service:
      POST   /api/account/redeem-code  { code: "LOVE26" }
"""
from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from motor.motor_asyncio import AsyncIOMotorDatabase

from credit_service import CreditService


_CODE_ALPHABET = string.ascii_uppercase + string.digits  # no lowercase / no I,O,0,1 ambiguity? keep simple
_CODE_DEFAULT_LEN = 6


def _generate_code(length: int = _CODE_DEFAULT_LEN) -> str:
    """Generate a random uppercased alphanumeric code."""
    return "".join(random.choices(_CODE_ALPHABET, k=length))


# ───── request models ─────────────────────────────────────────────────────
class _CreateGiftCodeReq(BaseModel):
    code: Optional[str] = Field(None, min_length=4, max_length=16,
                                description="Optional custom code; auto-generated if omitted")
    credits: int = Field(..., gt=0, description="Credits granted per redemption")
    description: str = Field("", max_length=200)
    max_redemptions: Optional[int] = Field(None, ge=1,
                                           description="None = unlimited")
    per_account_limit: int = Field(1, ge=1, le=10,
                                   description="How many times one account can redeem")
    expires_at: Optional[str] = Field(None,
                                      description="ISO-8601 UTC; None = no expiry")
    metadata: Optional[Dict[str, Any]] = None

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, v):
        if v is None:
            return v
        v = v.strip().upper()
        if not v.isalnum():
            raise ValueError("Code must be alphanumeric (A–Z, 0–9)")
        return v


class _UpdateGiftCodeReq(BaseModel):
    credits: Optional[int] = Field(None, gt=0)
    description: Optional[str] = Field(None, max_length=200)
    max_redemptions: Optional[int] = Field(None, ge=1)
    per_account_limit: Optional[int] = Field(None, ge=1, le=10)
    expires_at: Optional[str] = None
    is_active: Optional[bool] = None


class _RedeemReq(BaseModel):
    code: str = Field(..., min_length=4, max_length=16)

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, v):
        return v.strip().upper()


# ───── helpers ────────────────────────────────────────────────────────────
def _doc_to_response(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Strip mongo `_id` and convert internals."""
    if not doc:
        return doc
    out = {k: v for k, v in doc.items() if k != "_id"}
    return out


async def _validate_code_for_redemption(
    db: AsyncIOMotorDatabase, code: str, admin_id: str
) -> Dict[str, Any]:
    """
    Return the gift-code document if redeemable for this account; raise
    HTTPException otherwise.
    """
    doc = await db.gift_codes.find_one({"code": code})
    if not doc:
        raise HTTPException(status_code=404, detail="Invalid code")
    if not doc.get("is_active", True):
        raise HTTPException(status_code=400, detail="This code has been disabled")
    # Expiry
    expires_at = doc.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp < datetime.now(timezone.utc):
                raise HTTPException(status_code=400, detail="This code has expired")
        except ValueError:
            # malformed expiry — treat as no-expiry rather than failing the user
            pass
    # Global cap
    max_red = doc.get("max_redemptions")
    if max_red is not None and doc.get("redeemed_count", 0) >= max_red:
        raise HTTPException(status_code=400, detail="This code has reached its redemption limit")
    # Per-account cap
    per = int(doc.get("per_account_limit") or 1)
    used = await db.gift_code_redemptions.count_documents(
        {"code": code, "admin_id": admin_id}
    )
    if used >= per:
        raise HTTPException(status_code=400, detail="You have already redeemed this code")
    return doc


# ───── router builder ─────────────────────────────────────────────────────
def build_gift_code_router(
    db: AsyncIOMotorDatabase,
    require_super_admin,         # FastAPI dep
    get_current_admin,           # FastAPI dep — string admin_id or dict
) -> APIRouter:
    router = APIRouter(tags=["gift-codes"])
    svc = CreditService(db)

    async def _actor_id(actor) -> str:
        if isinstance(actor, dict):
            return actor.get("id") or actor.get("admin_id") or ""
        return actor or ""

    # ─── Super-Admin: create ─────────────────────────────────────────────
    @router.post("/api/super-admin/gift-codes")
    async def create_gift_code(req: _CreateGiftCodeReq,
                               super_admin_id: str = Depends(require_super_admin)):
        # Allocate a unique code (auto-generate if not provided)
        code = req.code
        if not code:
            for _ in range(8):
                cand = _generate_code()
                if not await db.gift_codes.find_one({"code": cand}):
                    code = cand
                    break
            if not code:
                raise HTTPException(status_code=500, detail="Could not allocate a unique code; retry")
        else:
            if await db.gift_codes.find_one({"code": code}):
                raise HTTPException(status_code=409, detail="A code with this value already exists")

        doc = {
            "code": code,
            "credits": req.credits,
            "description": req.description,
            "max_redemptions": req.max_redemptions,
            "per_account_limit": req.per_account_limit,
            "expires_at": req.expires_at,
            "is_active": True,
            "redeemed_count": 0,
            "created_by": super_admin_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": req.metadata or {},
        }
        await db.gift_codes.insert_one(doc)
        return _doc_to_response(doc)

    # ─── Super-Admin: list ───────────────────────────────────────────────
    @router.get("/api/super-admin/gift-codes")
    async def list_gift_codes(_: str = Depends(require_super_admin)):
        items: List[Dict[str, Any]] = []
        async for doc in db.gift_codes.find({}).sort("created_at", -1).limit(500):
            items.append(_doc_to_response(doc))
        return {"items": items, "total": len(items)}

    # ─── Super-Admin: update ─────────────────────────────────────────────
    @router.patch("/api/super-admin/gift-codes/{code}")
    async def update_gift_code(code: str, req: _UpdateGiftCodeReq,
                               _: str = Depends(require_super_admin)):
        code = code.strip().upper()
        target = await db.gift_codes.find_one({"code": code})
        if not target:
            raise HTTPException(status_code=404, detail="Code not found")
        patch = {k: v for k, v in req.model_dump(exclude_none=True).items()}
        if not patch:
            raise HTTPException(status_code=400, detail="Nothing to update")
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.gift_codes.update_one({"code": code}, {"$set": patch})
        updated = await db.gift_codes.find_one({"code": code})
        return _doc_to_response(updated)

    # ─── Super-Admin: deactivate (soft delete) ───────────────────────────
    @router.delete("/api/super-admin/gift-codes/{code}")
    async def deactivate_gift_code(code: str,
                                   _: str = Depends(require_super_admin)):
        code = code.strip().upper()
        res = await db.gift_codes.update_one(
            {"code": code},
            {"$set": {"is_active": False,
                      "deactivated_at": datetime.now(timezone.utc).isoformat()}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Code not found")
        return {"deactivated": True, "code": code}

    # ─── Super-Admin: list per-code redemptions ──────────────────────────
    @router.get("/api/super-admin/gift-codes/{code}/redemptions")
    async def list_redemptions(code: str,
                               _: str = Depends(require_super_admin)):
        code = code.strip().upper()
        items: List[Dict[str, Any]] = []
        async for doc in (db.gift_code_redemptions
                          .find({"code": code})
                          .sort("redeemed_at", -1).limit(500)):
            items.append(_doc_to_response(doc))
        return {"items": items, "total": len(items)}

    # ─── Self-service: redeem ────────────────────────────────────────────
    @router.post("/api/account/redeem-code")
    async def redeem_code(req: _RedeemReq, actor=Depends(get_current_admin)):
        admin_id = await _actor_id(actor)
        if not admin_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        gift = await _validate_code_for_redemption(db, req.code, admin_id)

        # Grant credits through CreditService — single source of truth for the
        # ledger. Reason includes the code itself for auditability.
        try:
            credit_result = await svc.add_credits(
                admin_id=admin_id,
                amount=int(gift["credits"]),
                reason=f"Redeemed code {gift['code']}: {gift.get('description') or 'gift code'}",
                performed_by="system",
                metadata={
                    "gift_code": gift["code"],
                    "gift_description": gift.get("description") or "",
                    **(gift.get("metadata") or {}),
                },
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Increment counter + append redemption audit row.
        await db.gift_codes.update_one(
            {"code": gift["code"]},
            {"$inc": {"redeemed_count": 1}},
        )
        await db.gift_code_redemptions.insert_one({
            "id": str(uuid.uuid4()),
            "code": gift["code"],
            "admin_id": admin_id,
            "credits": int(gift["credits"]),
            "redeemed_at": datetime.now(timezone.utc).isoformat(),
            "ledger_id": credit_result.get("ledger_id"),
        })

        return {
            "success": True,
            "code": gift["code"],
            "credits_added": int(gift["credits"]),
            "balance": {
                "total_credits": credit_result["total_credits"],
                "used_credits": credit_result["used_credits"],
                "available_credits": credit_result["available_credits"],
            },
        }

    return router
