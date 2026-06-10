"""
Canonical Credit System API Router — implements the credit spec exactly:

  Super-Admin only (RBAC enforced):
    POST   /api/super-admin/credits/add
    POST   /api/super-admin/credits/deduct
    POST   /api/super-admin/credits/adjust
    POST   /api/super-admin/credits/gift     (alias of add)
    POST   /api/super-admin/credits/refund
    GET    /api/super-admin/admins/{admin_id}/ledger?limit=&skip=
    GET    /api/super-admin/admins/{admin_id}/balance

  Self-service:
    GET    /api/account/credits
    GET    /api/account/ledger

All mutations go through CreditService so the immutable ledger is the single
source of truth. `reason` is mandatory on every mutation.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorDatabase

from credit_service import CreditService


# ---------- Request models ----------
class _AmountReason(BaseModel):
    admin_id: str = Field(..., min_length=1)
    amount: int = Field(..., gt=0, description="Positive integer")
    reason: str = Field(..., min_length=1, max_length=500)
    metadata: Optional[Dict[str, Any]] = None


class _SignedAmountReason(BaseModel):
    admin_id: str = Field(..., min_length=1)
    amount: int = Field(..., description="Signed integer (cannot be 0)")
    reason: str = Field(..., min_length=1, max_length=500)
    metadata: Optional[Dict[str, Any]] = None


class _GiftRequest(BaseModel):
    target_user_id: str = Field(..., min_length=1)
    credits: int = Field(..., gt=0)
    reason: str = Field(..., min_length=1, max_length=500)
    metadata: Optional[Dict[str, Any]] = None


class _RefundRequest(BaseModel):
    admin_id: str = Field(..., min_length=1)
    amount: int = Field(..., gt=0)
    reason: str = Field(..., min_length=1, max_length=500)
    related_wedding_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


def build_credit_system_router(
    db: AsyncIOMotorDatabase,
    require_super_admin,                 # FastAPI dep — returns admin_id (str)
    get_current_admin,                   # FastAPI dep — returns admin_id (str) for the caller
) -> APIRouter:
    """
    Wire the canonical credit-system endpoints onto the FastAPI app.
    """
    router = APIRouter(tags=["credit-system"])
    svc = CreditService(db)

    async def _resolve_actor_id(actor) -> str:
        """get_current_admin sometimes returns a string id, sometimes a dict."""
        if isinstance(actor, dict):
            return actor.get("id") or actor.get("admin_id") or ""
        return actor or ""

    # ------------------------------------------------------------------
    # SUPER-ADMIN endpoints (RBAC: require_super_admin enforces role)
    # ------------------------------------------------------------------
    @router.post("/api/super-admin/credits/add")
    async def sa_add_credits(req: _AmountReason, super_admin_id: str = Depends(require_super_admin)):
        try:
            return await svc.add_credits(
                admin_id=req.admin_id, amount=req.amount, reason=req.reason,
                performed_by=super_admin_id, metadata=req.metadata,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/api/super-admin/credits/deduct")
    async def sa_deduct_credits(req: _AmountReason, super_admin_id: str = Depends(require_super_admin)):
        try:
            return await svc.deduct_credits(
                admin_id=req.admin_id, amount=req.amount, reason=req.reason,
                performed_by=super_admin_id, metadata=req.metadata,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/api/super-admin/credits/adjust")
    async def sa_adjust_credits(req: _SignedAmountReason, super_admin_id: str = Depends(require_super_admin)):
        if req.amount == 0:
            raise HTTPException(status_code=400, detail="Adjustment amount must be non-zero")
        try:
            return await svc.adjust_credits(
                admin_id=req.admin_id, amount=req.amount, reason=req.reason,
                performed_by=super_admin_id, metadata=req.metadata,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/api/super-admin/credits/gift")
    async def sa_gift_credits(req: _GiftRequest, super_admin_id: str = Depends(require_super_admin)):
        """Gift credits to a user or photographer (wrapper around add_credits)."""
        # Target may live in either `admins` or `users` — try admins first since
        # CreditService is admins-collection-backed today.
        target = await db.admins.find_one({"id": req.target_user_id}, {"_id": 0})
        if not target:
            raise HTTPException(status_code=404, detail="Target user not found")
        try:
            res = await svc.add_credits(
                admin_id=req.target_user_id, amount=req.credits,
                reason=f"Gift: {req.reason}", performed_by=super_admin_id,
                metadata={**(req.metadata or {}), "gift": True},
            )
            res["gifted"] = req.credits
            return res
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/api/super-admin/credits/refund")
    async def sa_refund_credits(req: _RefundRequest, super_admin_id: str = Depends(require_super_admin)):
        try:
            return await svc.refund_credits(
                admin_id=req.admin_id, amount=req.amount, reason=req.reason,
                performed_by=super_admin_id,
                related_wedding_id=req.related_wedding_id,
                metadata=req.metadata,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/api/super-admin/admins/{admin_id}/ledger")
    async def sa_get_ledger(
        admin_id: str,
        limit: int = Query(100, ge=1, le=500),
        skip: int = Query(0, ge=0),
        _: str = Depends(require_super_admin),
    ):
        try:
            return await svc.get_credit_ledger(admin_id=admin_id, limit=limit, skip=skip)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.get("/api/super-admin/admins/{admin_id}/balance")
    async def sa_get_balance(admin_id: str, _: str = Depends(require_super_admin)):
        try:
            return await svc.get_credit_balance(admin_id=admin_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # ------------------------------------------------------------------
    # SELF-SERVICE endpoints (callers see only their own credits/ledger)
    # ------------------------------------------------------------------
    @router.get("/api/account/credits")
    async def my_balance(actor=Depends(get_current_admin)):
        actor_id = await _resolve_actor_id(actor)
        if not actor_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            return await svc.get_credit_balance(admin_id=actor_id)
        except ValueError:
            # Account exists but has no credit profile yet → return zeros.
            return {"total_credits": 0, "used_credits": 0, "available_credits": 0}

    @router.get("/api/account/ledger")
    async def my_ledger(
        limit: int = Query(100, ge=1, le=500),
        skip: int = Query(0, ge=0),
        actor=Depends(get_current_admin),
    ):
        actor_id = await _resolve_actor_id(actor)
        if not actor_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            return await svc.get_credit_ledger(admin_id=actor_id, limit=limit, skip=skip)
        except ValueError:
            return {"entries": [], "total": 0, "limit": limit, "skip": skip}

    return router
