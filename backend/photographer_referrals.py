"""
Photographer Referral Codes — viral growth on top of gift-code infra.

Every photographer (admin role) automatically gets a personal referral code
of the form `MAJA-XXXXXX`. When any user/photographer redeems it:
  • The redeemer's credit balance is credited with `redeemer_reward` credits.
  • The photographer (code owner) earns `owner_reward` credits.
Both grants go through `CreditService.add_credits()` so the immutable ledger
records both sides with reasons that include the code and the counterparty.

Collection: `photographer_referrals`
Schema:
    code:              str  unique, "MAJA-XXXXXX"
    owner_admin_id:    str  the photographer who owns this code
    redeemer_reward:   int  credits granted to person redeeming   (default 50)
    owner_reward:      int  credits awarded to owner per redeem   (default 50)
    per_account_limit: int  same-account cap (default 1)
    redeemed_count:    int  total redemptions
    is_active:         bool
    created_at:        iso str
    last_redeemed_at:  iso str | None

Endpoints:
  Self-service (any signed-in account):
    GET    /api/account/referral-code             → get / auto-create my code
    POST   /api/account/referral-code/regenerate  → rotate to a new code
    POST   /api/account/redeem-referral { code }  → redeem someone else's code

  Super-Admin:
    GET    /api/super-admin/referrals/{admin_id}   → view a photographer's code + stats
    GET    /api/super-admin/referrals              → leaderboard (top owners by redemptions)
    PATCH  /api/super-admin/referrals/{admin_id}   → change reward amounts / active flag
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


_PREFIX = "MAJA-"
_LEN    = 6
_ALPHABET = string.ascii_uppercase + string.digits

DEFAULT_REDEEMER_REWARD = 50   # credits to the person who pastes the code
DEFAULT_OWNER_REWARD    = 50   # credits to the photographer per redemption
DEFAULT_PER_ACCOUNT_LIMIT = 1


def _generate_code() -> str:
    body = "".join(random.choices(_ALPHABET, k=_LEN))
    return f"{_PREFIX}{body}"


class _RedeemReferral(BaseModel):
    code: str = Field(..., min_length=4, max_length=20)

    @field_validator("code")
    @classmethod
    def _norm(cls, v):
        return v.strip().upper()


class _PatchReferral(BaseModel):
    redeemer_reward: Optional[int] = Field(None, ge=0)
    owner_reward:    Optional[int] = Field(None, ge=0)
    per_account_limit: Optional[int] = Field(None, ge=1, le=10)
    is_active: Optional[bool] = None


def _doc_to_response(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    return {k: v for k, v in doc.items() if k != "_id"}


async def _ensure_referral_for(
    db: AsyncIOMotorDatabase, admin_id: str
) -> Dict[str, Any]:
    """Idempotent fetch-or-create for the caller's referral code."""
    existing = await db.photographer_referrals.find_one({"owner_admin_id": admin_id})
    if existing:
        return existing
    # Allocate a unique code
    code = None
    for _ in range(10):
        cand = _generate_code()
        if not await db.photographer_referrals.find_one({"code": cand}):
            code = cand
            break
    if not code:
        raise HTTPException(status_code=500, detail="Could not allocate a referral code")
    doc = {
        "code": code,
        "owner_admin_id": admin_id,
        "redeemer_reward": DEFAULT_REDEEMER_REWARD,
        "owner_reward":    DEFAULT_OWNER_REWARD,
        "per_account_limit": DEFAULT_PER_ACCOUNT_LIMIT,
        "redeemed_count":  0,
        "is_active":       True,
        "created_at":      datetime.now(timezone.utc).isoformat(),
        "last_redeemed_at": None,
    }
    await db.photographer_referrals.insert_one(doc)
    return doc


def build_photographer_referral_router(
    db: AsyncIOMotorDatabase,
    require_super_admin,
    get_current_admin,
) -> APIRouter:
    router = APIRouter(tags=["photographer-referrals"])
    svc = CreditService(db)

    async def _actor_id(actor) -> str:
        if isinstance(actor, dict):
            return actor.get("id") or actor.get("admin_id") or ""
        return actor or ""

    # ─── Self-service: my code ───────────────────────────────────────────
    @router.get("/api/account/referral-code")
    async def my_referral(actor=Depends(get_current_admin)):
        admin_id = await _actor_id(actor)
        if not admin_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        doc = await _ensure_referral_for(db, admin_id)
        return _doc_to_response(doc)

    @router.post("/api/account/referral-code/regenerate")
    async def regenerate_my_referral(actor=Depends(get_current_admin)):
        admin_id = await _actor_id(actor)
        if not admin_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        # Allocate a new unique code and replace
        new_code = None
        for _ in range(10):
            cand = _generate_code()
            if not await db.photographer_referrals.find_one({"code": cand}):
                new_code = cand
                break
        if not new_code:
            raise HTTPException(status_code=500, detail="Could not allocate a code")
        await db.photographer_referrals.update_one(
            {"owner_admin_id": admin_id},
            {"$set": {"code": new_code, "regenerated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )
        # If no existing row, ensure full doc exists
        doc = await _ensure_referral_for(db, admin_id)
        return _doc_to_response(doc)

    # ─── Self-service: redeem someone else's ─────────────────────────────
    @router.post("/api/account/redeem-referral")
    async def redeem_referral(req: _RedeemReferral, actor=Depends(get_current_admin)):
        redeemer_id = await _actor_id(actor)
        if not redeemer_id:
            raise HTTPException(status_code=401, detail="Not authenticated")

        ref = await db.photographer_referrals.find_one({"code": req.code})
        if not ref:
            raise HTTPException(status_code=404, detail="Invalid referral code")
        if not ref.get("is_active", True):
            raise HTTPException(status_code=400, detail="This referral code has been disabled")
        if ref["owner_admin_id"] == redeemer_id:
            raise HTTPException(status_code=400, detail="You cannot redeem your own code")

        # Per-account cap on this code
        per = int(ref.get("per_account_limit") or 1)
        already = await db.referral_redemptions.count_documents(
            {"code": ref["code"], "redeemer_id": redeemer_id}
        )
        if already >= per:
            raise HTTPException(status_code=400, detail="You have already redeemed this code")

        redeemer_reward = int(ref.get("redeemer_reward") or 0)
        owner_reward    = int(ref.get("owner_reward") or 0)

        # Credit the redeemer (only if reward > 0)
        redeemer_balance = None
        redeemer_ledger_id = None
        if redeemer_reward > 0:
            res = await svc.add_credits(
                admin_id=redeemer_id, amount=redeemer_reward,
                reason=f"Referral redemption ({ref['code']})",
                performed_by="system",
                metadata={"referral_code": ref["code"], "side": "redeemer",
                          "owner_admin_id": ref["owner_admin_id"]},
            )
            redeemer_balance = {
                "total_credits": res["total_credits"],
                "used_credits":  res["used_credits"],
                "available_credits": res["available_credits"],
            }
            redeemer_ledger_id = res["ledger_id"]

        # Credit the owner (photographer) — guarded so a missing admin row
        # doesn't break the redemption; we just skip the owner-side credit.
        owner_ledger_id = None
        if owner_reward > 0:
            try:
                res = await svc.add_credits(
                    admin_id=ref["owner_admin_id"], amount=owner_reward,
                    reason=f"Referral earnings ({ref['code']})",
                    performed_by="system",
                    metadata={"referral_code": ref["code"], "side": "owner",
                              "redeemer_admin_id": redeemer_id},
                )
                owner_ledger_id = res["ledger_id"]
            except ValueError:
                # Owner account no longer exists or invalid; ignore — the
                # redeemer's side has already been credited.
                pass

        # Increment counter + append audit row
        await db.photographer_referrals.update_one(
            {"code": ref["code"]},
            {"$inc": {"redeemed_count": 1},
             "$set": {"last_redeemed_at": datetime.now(timezone.utc).isoformat()}},
        )
        await db.referral_redemptions.insert_one({
            "id": str(uuid.uuid4()),
            "code": ref["code"],
            "owner_admin_id": ref["owner_admin_id"],
            "redeemer_id": redeemer_id,
            "redeemer_reward": redeemer_reward,
            "owner_reward":    owner_reward,
            "redeemed_at": datetime.now(timezone.utc).isoformat(),
            "redeemer_ledger_id": redeemer_ledger_id,
            "owner_ledger_id":    owner_ledger_id,
        })

        return {
            "success": True,
            "code": ref["code"],
            "credits_added": redeemer_reward,
            "owner_earned":  owner_reward,
            "balance": redeemer_balance,
        }

    # ─── Super-Admin: leaderboard ────────────────────────────────────────
    @router.get("/api/super-admin/referrals")
    async def referral_leaderboard(_: str = Depends(require_super_admin)):
        items: List[Dict[str, Any]] = []
        async for doc in (db.photographer_referrals
                          .find({})
                          .sort("redeemed_count", -1).limit(100)):
            items.append(_doc_to_response(doc))
        return {"items": items, "total": len(items)}

    # ─── Super-Admin: per-photographer detail ────────────────────────────
    @router.get("/api/super-admin/referrals/{admin_id}")
    async def referral_for_admin(admin_id: str, _: str = Depends(require_super_admin)):
        doc = await db.photographer_referrals.find_one({"owner_admin_id": admin_id})
        if not doc:
            raise HTTPException(status_code=404, detail="No referral row")
        out = _doc_to_response(doc)
        # Include recent redemption history
        recent: List[Dict[str, Any]] = []
        async for r in (db.referral_redemptions
                        .find({"code": doc["code"]})
                        .sort("redeemed_at", -1).limit(50)):
            recent.append(_doc_to_response(r))
        out["recent_redemptions"] = recent
        return out

    # ─── Super-Admin: patch rewards / active ─────────────────────────────
    @router.patch("/api/super-admin/referrals/{admin_id}")
    async def patch_referral(admin_id: str, req: _PatchReferral,
                             _: str = Depends(require_super_admin)):
        target = await db.photographer_referrals.find_one({"owner_admin_id": admin_id})
        if not target:
            raise HTTPException(status_code=404, detail="No referral row")
        patch = {k: v for k, v in req.model_dump(exclude_none=True).items()}
        if not patch:
            raise HTTPException(status_code=400, detail="Nothing to update")
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.photographer_referrals.update_one(
            {"owner_admin_id": admin_id}, {"$set": patch}
        )
        updated = await db.photographer_referrals.find_one({"owner_admin_id": admin_id})
        return _doc_to_response(updated)

    return router
