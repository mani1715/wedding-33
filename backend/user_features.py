"""
USER FEATURES — Normal-user (wedding-couple / guest) backend:

  • Design pricing (super-admin sets credits-per-design)
  • Public design pricing list
  • User-side Razorpay credit purchase (create-order + verify)
  • User-side invitation create + list (deducts credits from user wallet)

Mirrors the photographer flow at `/api/admin/*` but writes/reads from the
`users` collection and prefixes profile `admin_id` with `user:<user_id>` so
existing admin data-isolation queries never see user-created profiles.
"""
from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel, Field

logger = logging.getLogger("user_features")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _razorpay_configured() -> bool:
    """True if real Razorpay keys are present (not the placeholder defaults)."""
    key_id = os.environ.get("RAZORPAY_KEY_ID", "")
    key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not key_id or not key_secret:
        return False
    if "PLACEHOLDER" in key_id.upper() or "PLACEHOLDER" in key_secret.upper():
        return False
    return True


# ─────────────────────────────────────────────────────────────────────
# Defaults seeded at app startup (see seed_user_purchase_catalog below).
# Kept at module level so they're trivially overridable in tests.
# ─────────────────────────────────────────────────────────────────────
DEFAULT_EXPIRY_TIERS = [
    {"id": "1_month",  "label": "1 Month",  "days": 30,  "credits": 1, "order": 1},
    {"id": "3_months", "label": "3 Months", "days": 90,  "credits": 2, "order": 2},
    {"id": "6_months", "label": "6 Months", "days": 180, "credits": 3, "order": 3},
    {"id": "1_year",   "label": "1 Year",   "days": 365, "credits": 5, "order": 4},
]

DEFAULT_USER_ADDONS = [
    {"id": "music",          "label": "Background Music",       "description": "Curated royalty-free score plays on the invitation.",     "credits": 1, "order": 1},
    {"id": "live_gallery",   "label": "Live Photo Gallery",     "description": "Guests upload photos live during the wedding.",           "credits": 3, "order": 2},
    {"id": "ai_story",       "label": "AI Story Composer",      "description": "Gemini writes a cinematic 'how we met' narrative.",        "credits": 2, "order": 3},
    {"id": "rsvp",           "label": "Smart RSVP",             "description": "Guest list, +1 tracking and dietary preferences.",        "credits": 1, "order": 4},
    {"id": "whatsapp",       "label": "WhatsApp Invites",       "description": "One-click WhatsApp share with personalised greetings.",   "credits": 1, "order": 5},
    {"id": "parking",        "label": "Parking & Travel",       "description": "Parking map, drop-off zones and travel deep links.",       "credits": 1, "order": 6},
    {"id": "gift_registry",  "label": "Gift Registry",          "description": "Optional gift list or 'no gifts please' note.",           "credits": 1, "order": 7},
    {"id": "digital_shagun", "label": "Digital Shagun (UPI)",   "description": "Live UPI blessing counter shown on the invitation.",       "credits": 1, "order": 8},
    {"id": "ai_face_match",  "label": "AI Face-Match Photos",   "description": "Guests find their photos via a single selfie.",           "credits": 3, "order": 9},
    {"id": "save_the_date",  "label": "Save the Date teaser",   "description": "A teaser page that goes live before the main invitation.", "credits": 1, "order": 10},
]


async def seed_user_purchase_catalog(db) -> None:
    """Idempotent startup seeder for the public user-purchase catalogue.

    Runs once at app boot (called from server.py startup) so the lazy
    seed inside the request handlers can never race two concurrent
    first-time visitors.  Safe to re-call — uses count-then-insert.
    """
    try:
        if await db.expiry_tiers.count_documents({}) == 0:
            await db.expiry_tiers.insert_many(DEFAULT_EXPIRY_TIERS)
            logger.info("seed_user_purchase_catalog: inserted %d expiry tiers", len(DEFAULT_EXPIRY_TIERS))
        if await db.user_addons.count_documents({}) == 0:
            await db.user_addons.insert_many(DEFAULT_USER_ADDONS)
            logger.info("seed_user_purchase_catalog: inserted %d user addons", len(DEFAULT_USER_ADDONS))
    except Exception as e:
        # Log but don't crash boot on a seeding hiccup.
        logger.exception("seed_user_purchase_catalog failed: %s", e)


def _strip(d: Optional[dict]) -> Optional[dict]:
    if d is None:
        return d
    d.pop("_id", None)
    return d


# ─────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────
class DesignPricingUpsert(BaseModel):
    credits: int = Field(ge=0, le=100_000)
    inr_price: int = Field(default=0, ge=0)  # Rupee price for normal users
    is_active: bool = True
    label: Optional[str] = None  # Human-readable design name (cache)
    theme_id: Optional[str] = None  # e.g. "royal_mughal"
    event_type: Optional[str] = None  # e.g. "marriage"


class UserPurchaseOrderRequest(BaseModel):
    pack_id: str


class BuyAddonRequest(BaseModel):
    """Body for POST /api/users/profiles/{id}/buy-addon."""
    addon_id: str = Field(min_length=1, max_length=64)


class UserPurchaseVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


class UserProfileCreate(BaseModel):
    """Minimum payload to create an invitation as a normal user.
    Mirrors the admin form's required fields. Free-form `extras` carries
    everything the photographer form supports (sections_enabled, custom_text,
    background_music, events, link_expiry_*, etc.) so the same React form
    can post here unchanged."""
    design_id: str
    groom_name: str = Field(min_length=1, max_length=80)
    bride_name: str = Field(min_length=1, max_length=80)
    event_type: str
    event_date: str
    venue: Optional[str] = ""
    city: Optional[str] = ""
    invitation_message: Optional[str] = ""
    language: Optional[List[str]] = None
    deity_id: Optional[str] = None
    whatsapp_groom: Optional[str] = None
    whatsapp_bride: Optional[str] = None
    enabled_languages: Optional[List[str]] = None
    custom_text: Optional[Dict[str, Any]] = None
    about_couple: Optional[str] = None
    family_details: Optional[str] = None
    love_story: Optional[str] = None
    bride_about: Optional[str] = None
    groom_about: Optional[str] = None
    bride_photo_url: Optional[str] = None
    groom_photo_url: Optional[str] = None
    couple_photo_url: Optional[str] = None
    cover_photo_id: Optional[str] = None
    sections_enabled: Optional[Dict[str, Any]] = None
    background_music: Optional[Dict[str, Any]] = None
    map_settings: Optional[Dict[str, Any]] = None
    events: Optional[List[Dict[str, Any]]] = None
    link_expiry_type: Optional[str] = None
    link_expiry_value: Optional[int] = None
    expires_at: Optional[str] = None
    # Find My Room (guest accommodation lookup) & Pre-wedding shoot links
    guest_rooms: Optional[List[Dict[str, Any]]] = None
    pre_wedding_links: Optional[List[Dict[str, Any]]] = None
    # Photo Privacy (access code + flags). Server hashes the code.
    gallery_privacy: Optional[Dict[str, Any]] = None
    # Per-slot photo enable/disable toggles
    show_bride_photo: Optional[bool] = True
    show_groom_photo: Optional[bool] = True
    show_couple_photo: Optional[bool] = True
    # Couple deep-dive fields surfaced in the rich preview
    couple_about: Optional[str] = None
    nakshatram: Optional[str] = None
    muhurtam: Optional[str] = None
    # Opening (link-open) animation background — couple / bride / groom / custom / none
    use_couple_photo_as_opening_bg: Optional[bool] = True
    opening_bg_source: Optional[str] = 'couple'
    opening_photo_url: Optional[str] = None
    # 2026 — Universal Invitation Categories
    invitation_category: Optional[str] = "wedding"
    celebrant_info: Optional[Dict[str, Any]] = None
    design_selections: Optional[Dict[str, str]] = None
    selected_features: Optional[List[str]] = None


class GrantUserCredits(BaseModel):
    """Request body for granting credits to a normal user."""
    amount: int = Field(gt=0, le=10_000)
    reason: Optional[str] = Field(default="Granted by super-admin", max_length=240)


class SetUserStatus(BaseModel):
    """Request body for setting user account status."""
    status: str  # "active" | "suspended" | "blocked"
    reason: Optional[str] = Field(default=None, max_length=240)


# ─────────────────────────────────────────────────────────────────────
# Router builder
# ─────────────────────────────────────────────────────────────────────
def build_user_features_router(
    db,
    require_super_admin,
    get_current_public_user,
    razorpay_client,
    sanitize_html,
    generate_slug,
    calculate_expiry_date,
    calculate_invitation_expires_at,
) -> APIRouter:
    router = APIRouter(tags=["user-features"])

    # ════════════════════════════════════════════════════════════════════
    # DESIGN PRICING — super-admin CRUD
    # ════════════════════════════════════════════════════════════════════
    @router.get("/api/super-admin/design-pricing")
    async def sa_list_design_pricing(super_admin_id: str = Depends(require_super_admin)):
        cursor = db.design_pricing.find({}, {"_id": 0}).sort("design_id", 1)
        rows = await cursor.to_list(5000)
        return {"pricing": rows}

    @router.put("/api/super-admin/design-pricing/{design_id}")
    async def sa_upsert_design_pricing(
        design_id: str,
        payload: DesignPricingUpsert,
        super_admin_id: str = Depends(require_super_admin),
    ):
        update = {
            **payload.model_dump(exclude_none=True),
            "design_id": design_id,
            "updated_at": _now_iso(),
            "updated_by": super_admin_id,
        }
        await db.design_pricing.update_one(
            {"design_id": design_id},
            {"$set": update, "$setOnInsert": {"created_at": _now_iso()}},
            upsert=True,
        )
        row = await db.design_pricing.find_one({"design_id": design_id}, {"_id": 0})
        return row

    @router.delete("/api/super-admin/design-pricing/{design_id}")
    async def sa_delete_design_pricing(
        design_id: str, super_admin_id: str = Depends(require_super_admin)
    ):
        await db.design_pricing.delete_one({"design_id": design_id})
        return {"success": True}

    # ════════════════════════════════════════════════════════════════════
    # NORMAL-USER MANAGEMENT — super-admin CRUD (July 2025 spec)
    #
    # The super-admin console previously only listed photographers. These
    # endpoints surface every normal user (sign-up via /api/users/register
    # or Google OAuth) so the super-admin can:
    #   - See every user account & when they signed up
    #   - View any user's profile with their invitations
    #   - Grant FREE credits (with a reason — audited)
    #   - Suspend / unsuspend / block the account
    # ════════════════════════════════════════════════════════════════════

    async def _user_stats(user_id: str):
        """Compute per-user invite + credit counts. Cheap aggregations."""
        invites = await db.profiles.count_documents({"user_id": user_id})
        return {"profiles_count": invites}

    @router.get("/api/super-admin/users")
    async def sa_list_users(
        super_admin_id: str = Depends(require_super_admin),
        q: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 200,
    ):
        """List every normal user. Optional `q` searches name/email/phone,
        optional `status` filters by account status."""
        filt: Dict[str, Any] = {}
        if status and status.lower() in ("active", "suspended", "blocked"):
            filt["status"] = status.lower()
        if q and q.strip():
            term = q.strip()
            filt["$or"] = [
                {"email":  {"$regex": term, "$options": "i"}},
                {"name":   {"$regex": term, "$options": "i"}},
                {"phone":  {"$regex": term, "$options": "i"}},
                {"user_id": term},
            ]
        cursor = (
            db.users.find(filt, {"_id": 0, "password_hash": 0})
            .sort("created_at", -1)
            .limit(max(1, min(limit, 1000)))
        )
        users = await cursor.to_list(1000)
        # Enrich with profiles_count
        out = []
        for u in users:
            stats = await _user_stats(u["user_id"])
            out.append({
                **u,
                **stats,
                "status": u.get("status") or "active",
                "credits": int(u.get("credits") or 0),
            })
        return {"users": out, "count": len(out)}

    @router.get("/api/super-admin/users/{user_id}")
    async def sa_get_user(
        user_id: str, super_admin_id: str = Depends(require_super_admin)
    ):
        """Full user detail: account + all their invitations + recent credit
        ledger entries — everything the super-admin needs to make a call."""
        user = await db.users.find_one(
            {"user_id": user_id}, {"_id": 0, "password_hash": 0}
        )
        if not user:
            raise HTTPException(404, "User not found")
        user["status"]  = user.get("status") or "active"
        user["credits"] = int(user.get("credits") or 0)

        # Their invitations (no _id, newest first)
        profiles_cur = db.profiles.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(200)
        profiles = await profiles_cur.to_list(200)

        # Recent credit ledger (newest first, last 100)
        ledger_cur = db.user_credit_ledger.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(100)
        ledger = await ledger_cur.to_list(100)

        return {
            "user": user,
            "profiles": profiles,
            "profiles_count": len(profiles),
            "credit_ledger": ledger,
        }

    @router.post("/api/super-admin/users/{user_id}/credits")
    async def sa_grant_user_credits(
        user_id: str,
        payload: GrantUserCredits,
        super_admin_id: str = Depends(require_super_admin),
    ):
        """Grant FREE credits to a normal user. Logged in user_credit_ledger
        with type='admin_grant' so the user sees it as 'Gifted by MAJA'."""
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(404, "User not found")

        amount = int(payload.amount)
        new_balance = int(user.get("credits") or 0) + amount
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"credits": new_balance, "updated_at": _now_iso()}},
        )

        # Audit-trail entry in the same ledger users read on their dashboard
        await db.user_credit_ledger.insert_one({
            "id": uuid.uuid4().hex,
            "user_id": user_id,
            "amount": amount,                  # positive = credit
            "type": "admin_grant",
            "reason": (payload.reason or "Gifted by MAJA").strip(),
            "granted_by": super_admin_id,
            "balance_after": new_balance,
            "created_at": _now_iso(),
        })

        # Mirror to the super-admin audit log so it shows up on /audit
        try:
            await db.audit_logs.insert_one({
                "id": uuid.uuid4().hex,
                "admin_id": super_admin_id,         # canonical field expected by AuditLogResponse
                "actor_id": super_admin_id,         # kept for back-compat with the user-mgmt UI
                "actor_role": "super_admin",
                "action": "user_credits_granted",
                "target_id": user_id,
                "target_type": "user",
                "details": {                        # Dict — matches AuditLogResponse schema
                    "user_id": user_id,
                    "amount": amount,
                    "reason": payload.reason or "gifted by super-admin",
                },
                "created_at": _now_iso(),
                "timestamp": _now_iso(),
            })
        except Exception:
            pass

        return {"success": True, "credits": new_balance, "granted": amount}

    @router.put("/api/super-admin/users/{user_id}/status")
    async def sa_set_user_status(
        user_id: str,
        payload: SetUserStatus,
        super_admin_id: str = Depends(require_super_admin),
    ):
        """Suspend / block / re-activate a normal user.
          - active     → user can log in normally
          - suspended  → existing sessions stay valid until expiry, but new
                         login attempts are refused
          - blocked    → user is locked out immediately; sessions invalidated
        """
        wanted = (payload.status or "").lower().strip()
        if wanted not in ("active", "suspended", "blocked"):
            raise HTTPException(400, "status must be active|suspended|blocked")

        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(404, "User not found")

        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "status": wanted,
                "status_reason": (payload.reason or "").strip() or None,
                "status_changed_by": super_admin_id,
                "status_changed_at": _now_iso(),
                "updated_at": _now_iso(),
            }},
        )

        # If blocking, kill all active sessions for this user
        if wanted == "blocked":
            try:
                await db.user_sessions.delete_many({"user_id": user_id})
            except Exception:
                pass

        try:
            await db.audit_logs.insert_one({
                "id": uuid.uuid4().hex,
                "admin_id": super_admin_id,         # canonical field expected by AuditLogResponse
                "actor_id": super_admin_id,
                "actor_role": "super_admin",
                "action": f"user_status_{wanted}",
                "target_id": user_id,
                "target_type": "user",
                "details": {                        # Dict — matches AuditLogResponse schema
                    "user_id": user_id,
                    "status": wanted,
                    "reason": payload.reason or f"status set to {wanted}",
                },
                "created_at": _now_iso(),
                "timestamp": _now_iso(),
            })
        except Exception:
            pass

        return {"success": True, "status": wanted}

    @router.get("/api/super-admin/users/{user_id}/credits/ledger")
    async def sa_user_credit_ledger(
        user_id: str,
        super_admin_id: str = Depends(require_super_admin),
        limit: int = 200,
    ):
        cur = db.user_credit_ledger.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(max(1, min(limit, 1000)))
        rows = await cur.to_list(1000)
        return {"ledger": rows, "count": len(rows)}

    @router.get("/api/public/design-pricing")
    async def public_design_pricing():
        """Returns {design_id: {credits, label, ...}} for active designs.
        Used by the user-facing design picker."""
        cursor = db.design_pricing.find({"is_active": {"$ne": False}}, {"_id": 0})
        rows = await cursor.to_list(5000)
        return {"pricing": {r["design_id"]: r for r in rows}}

    # ── PUBLIC EXPIRY TIERS — used by user-facing PurchaseOptionsWizard ───
    @router.get("/api/public/expiry-tiers")
    async def public_expiry_tiers():
        """Returns the list of link-expiry tiers (days + credits) shown
        in the user-facing PurchaseOptionsWizard. No auth required.
        Catalogue is seeded at app startup via seed_user_purchase_catalog().
        """
        docs = await db.expiry_tiers.find({}, {"_id": 0}).sort("order", 1).to_list(50)
        return {"tiers": docs}

    # ── PUBLIC ADD-ON CATALOGUE — curated feature add-ons shown in the
    # PurchaseOptionsWizard.  Seeded at app startup; this endpoint just reads.
    @router.get("/api/public/addons")
    async def public_addons():
        docs = await db.user_addons.find({}, {"_id": 0}).sort("order", 1).to_list(100)
        return {"addons": docs}

    # ════════════════════════════════════════════════════════════════════
    # POST-PURCHASE ADD-ONS — buy extra features on an existing invite
    # ════════════════════════════════════════════════════════════════════
    @router.post("/api/users/profiles/{profile_id}/buy-addon")
    async def user_buy_addon(
        profile_id: str,
        payload: BuyAddonRequest,
        current=Depends(get_current_public_user),
    ):
        """Deduct credits and append the add-on to profile.add_ons."""
        addon_id = payload.addon_id

        profile = await db.profiles.find_one(
            {"id": profile_id, "user_id": current["user_id"]}, {"_id": 0}
        )
        if not profile:
            raise HTTPException(404, "Invitation not found")

        addon = await db.user_addons.find_one({"id": addon_id}, {"_id": 0})
        if not addon:
            raise HTTPException(404, "Add-on not found")

        # Idempotency — if already purchased, return success without re-charging
        existing_ids = {a.get("id") for a in (profile.get("add_ons") or [])}
        if addon_id in existing_ids:
            user_doc = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0, "password_hash": 0})
            return {
                "success": True,
                "already_purchased": True,
                "addon": addon,
                "credits_charged": 0,
                "balance": int(user_doc.get("credits", 0)) if user_doc else 0,
            }

        cost = int(addon.get("credits", 0) or 0)
        user_doc = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0})
        balance = int(user_doc.get("credits", 0)) if user_doc else 0
        if balance < cost:
            raise HTTPException(
                402,
                {"error": "Insufficient credits", "required": cost, "balance": balance, "addon_id": addon_id},
            )

        now_iso = _now_iso()
        addon_entry = {
            "id": addon["id"],
            "label": addon["label"],
            "credits": cost,
            "purchased_at": now_iso,
        }
        await db.profiles.update_one(
            {"id": profile_id, "user_id": current["user_id"]},
            {
                "$push": {"add_ons": addon_entry},
                "$set":  {"updated_at": now_iso},
            },
        )
        if cost > 0:
            await db.users.update_one(
                {"user_id": current["user_id"]},
                {"$inc": {"credits": -cost}},
            )
            await db.user_credit_ledger.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": current["user_id"],
                "action": "spend",
                "amount": -cost,
                "reason": f"Add-on · {addon['label']} · {profile.get('slug','')}",
                "profile_id": profile_id,
                "addon_id": addon_id,
                "created_at": now_iso,
            })

        updated_user = await db.users.find_one(
            {"user_id": current["user_id"]}, {"_id": 0, "password_hash": 0}
        )
        updated_profile = await db.profiles.find_one(
            {"id": profile_id}, {"_id": 0, "admin_id": 0}
        )
        if updated_profile:
            updated_profile["invitation_link"] = f"/invite/{updated_profile['slug']}"
        return {
            "success": True,
            "already_purchased": False,
            "addon": addon_entry,
            "credits_charged": cost,
            "balance": int(updated_user.get("credits", 0)) if updated_user else 0,
            "profile": updated_profile,
        }

    # ════════════════════════════════════════════════════════════════════
    # USER CREDIT PURCHASE — Razorpay
    # ════════════════════════════════════════════════════════════════════
    @router.post("/api/users/credits/purchase/create-order")
    async def user_create_order(
        payload: UserPurchaseOrderRequest, current=Depends(get_current_public_user)
    ):
        if razorpay_client is None:
            raise HTTPException(503, "Payment gateway not configured")
        if not _razorpay_configured():
            raise HTTPException(
                503,
                "Razorpay keys are placeholders. Replace RAZORPAY_KEY_ID and "
                "RAZORPAY_KEY_SECRET in backend/.env with real test keys "
                "from your Razorpay dashboard, then restart the backend.",
            )

        pack = await db.credit_packs.find_one(
            {
                "id": payload.pack_id,
                "is_active": True,
                "audience": {"$in": ["guest", "both"]},
            },
            {"_id": 0},
        )
        if not pack:
            raise HTTPException(404, "Pack not found or unavailable to users")

        amount_paise = int(pack["price_inr"]) * 100
        receipt = f"ucpk_{uuid.uuid4().hex[:24]}"

        try:
            order = razorpay_client.order.create({
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "receipt": receipt,
                "notes": {
                    "user_id": current["user_id"],
                    "pack_id": pack["id"],
                    "credits": str(pack["credits"]),
                    "kind": "user_credit_pack",
                },
            })
        except Exception as e:
            logger.exception("[user_features] create_order failed")
            raise HTTPException(502, f"Could not create order: {str(e)[:120]}")

        purchase_doc = {
            "id": f"upurch_{uuid.uuid4().hex[:16]}",
            "user_id": current["user_id"],
            "pack_id": pack["id"],
            "pack_label": pack["label"],
            "credits": int(pack["credits"]),
            "amount_inr": int(pack["price_inr"]),
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
        await db.user_credit_purchases.insert_one(purchase_doc)
        _strip(purchase_doc)
        return {
            "purchase_id": purchase_doc["id"],
            "order_id": order["id"],
            "amount_paise": amount_paise,
            "amount_inr": pack["price_inr"],
            "credits": pack["credits"],
            "pack_label": pack["label"],
            "currency": "INR",
            "razorpay_key_id": os.environ.get("RAZORPAY_KEY_ID", ""),
            "user_name": current.get("name"),
            "user_email": current.get("email"),
            "user_phone": current.get("phone"),
        }

    async def _credit_user_atomic(purchase: dict) -> dict:
        res = await db.user_credit_purchases.update_one(
            {"id": purchase["id"], "credited": {"$ne": True}},
            {"$set": {"credited": True, "status": "captured", "completed_at": _now_iso()}},
        )
        if res.modified_count == 1:
            await db.users.update_one(
                {"user_id": purchase["user_id"]},
                {"$inc": {"credits": int(purchase["credits"])}},
            )
            await db.user_credit_ledger.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": purchase["user_id"],
                "action": "purchase",
                "amount": int(purchase["credits"]),
                "reason": f"Razorpay {purchase.get('pack_label','pack')} (₹{purchase['amount_inr']})",
                "purchase_id": purchase["id"],
                "razorpay_order_id": purchase.get("razorpay_order_id"),
                "razorpay_payment_id": purchase.get("razorpay_payment_id"),
                "created_at": _now_iso(),
            })
        return await db.user_credit_purchases.find_one({"id": purchase["id"]}, {"_id": 0})

    @router.post("/api/users/credits/purchase/verify")
    async def user_verify_purchase(
        payload: UserPurchaseVerifyRequest, current=Depends(get_current_public_user)
    ):
        if razorpay_client is None:
            raise HTTPException(503, "Payment gateway not configured")

        purchase = await db.user_credit_purchases.find_one(
            {"razorpay_order_id": payload.razorpay_order_id, "user_id": current["user_id"]},
            {"_id": 0},
        )
        if not purchase:
            raise HTTPException(404, "Purchase not found")

        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            })
        except Exception as e:
            await db.user_credit_purchases.update_one(
                {"id": purchase["id"]},
                {"$set": {"status": "signature_invalid", "error": str(e)[:200]}},
            )
            raise HTTPException(400, "Invalid payment signature")

        await db.user_credit_purchases.update_one(
            {"id": purchase["id"]},
            {"$set": {
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            }},
        )
        purchase["razorpay_payment_id"] = payload.razorpay_payment_id
        updated = await _credit_user_atomic(purchase)
        user_doc = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0, "password_hash": 0})
        return {
            "success": True,
            "credited": True,
            "credits_added": int(purchase["credits"]),
            "new_balance": int(user_doc.get("credits", 0)),
            "purchase": updated,
        }

    @router.get("/api/users/credits/purchases")
    async def user_purchases(current=Depends(get_current_public_user)):
        cursor = (
            db.user_credit_purchases.find({"user_id": current["user_id"]}, {"_id": 0})
            .sort("created_at", -1)
            .limit(100)
        )
        purchases = await cursor.to_list(100)
        return {"purchases": purchases}

    # ════════════════════════════════════════════════════════════════════
    # USER PROFILES — create / list / read
    # ════════════════════════════════════════════════════════════════════
    @router.post("/api/users/profiles")
    async def user_create_profile(
        payload: UserProfileCreate, current=Depends(get_current_public_user)
    ):
        # ── 1. Fetch design price (default = 1)
        # For non-wedding categories use the event_category_pricing collection
        cost = 1
        if (payload.invitation_category or "wedding") != "wedding":
            cat_price = await db.event_category_pricing.find_one(
                {"category_id": payload.invitation_category, "user_type": "normal_user"},
                {"_id": 0},
            )
            if cat_price and "design_credits" in cat_price:
                cost = int(cat_price["design_credits"])
            else:
                # fall back to in-memory defaults
                try:
                    from invitation_categories import get_category_pricing
                    cost = int(get_category_pricing(payload.invitation_category, "normal_user").get("design_credits", 1))
                except Exception:
                    cost = 1
            # add feature credits — fall back to in-memory defaults when
            # the super-admin hasn't created an override in the DB yet.
            feat_credits = (cat_price or {}).get("feature_credits") or {}
            if not feat_credits:
                try:
                    from invitation_categories import get_category_pricing
                    feat_credits = (
                        get_category_pricing(payload.invitation_category, "normal_user")
                        .get("feature_credits") or {}
                    )
                except Exception:
                    feat_credits = {}
            for fk in (payload.selected_features or []):
                cost += int(feat_credits.get(fk, 0) or 0)
        else:
            pricing = await db.design_pricing.find_one(
                {"design_id": payload.design_id, "is_active": {"$ne": False}}, {"_id": 0}
            )
            cost = int(pricing["credits"]) if pricing else 1

        # ── 2. Check user balance
        user = await db.users.find_one({"user_id": current["user_id"]}, {"_id": 0})
        balance = int(user.get("credits", 0)) if user else 0
        if balance < cost:
            raise HTTPException(
                402,
                {
                    "error": "Insufficient credits",
                    "required": cost,
                    "balance": balance,
                    "design_id": payload.design_id,
                },
            )

        # ── 3. Generate unique slug
        slug = generate_slug(payload.groom_name, payload.bride_name)
        while await db.profiles.find_one({"slug": slug}):
            slug = generate_slug(payload.groom_name, payload.bride_name)

        # ── 4. Compute expiry windows
        expiry_date = None
        try:
            expiry_date = calculate_expiry_date(
                payload.link_expiry_type, payload.link_expiry_value
            )
        except Exception:
            pass

        try:
            event_dt = datetime.fromisoformat(payload.event_date)
        except Exception:
            event_dt = datetime.now(timezone.utc)

        invitation_expires_at = calculate_invitation_expires_at(event_dt, payload.expires_at)

        # ── 5. Build profile document
        about = sanitize_html(payload.about_couple) if payload.about_couple else None
        family = sanitize_html(payload.family_details) if payload.family_details else None
        love = sanitize_html(payload.love_story) if payload.love_story else None
        msg = sanitize_html(payload.invitation_message) if payload.invitation_message else ""
        venue = sanitize_html(payload.venue) if payload.venue else ""
        city = sanitize_html(payload.city) if payload.city else ""

        now_iso = _now_iso()
        profile_id = uuid.uuid4().hex
        profile_doc = {
            "id": profile_id,
            "admin_id": f"user:{current['user_id']}",  # Sentinel — keeps user invites out of admin queries
            "user_id": current["user_id"],
            "created_by_role": "user",
            "slug": slug,
            "groom_name": payload.groom_name,
            "bride_name": payload.bride_name,
            "event_type": payload.event_type,
            "event_date": event_dt.isoformat(),
            "venue": venue,
            "city": city,
            "invitation_message": msg,
            "language": payload.language or ["english"],
            "design_id": payload.design_id,
            "deity_id": payload.deity_id,
            "whatsapp_groom": payload.whatsapp_groom,
            "whatsapp_bride": payload.whatsapp_bride,
            "enabled_languages": payload.enabled_languages or [],
            "custom_text": payload.custom_text or {},
            "about_couple": about,
            "family_details": family,
            "love_story": love,
            "bride_about": sanitize_html(payload.bride_about) if payload.bride_about else None,
            "groom_about": sanitize_html(payload.groom_about) if payload.groom_about else None,
            "bride_photo_url": payload.bride_photo_url,
            "groom_photo_url": payload.groom_photo_url,
            "couple_photo_url": payload.couple_photo_url,
            "cover_photo_id": payload.cover_photo_id,
            "sections_enabled": payload.sections_enabled or {},
            "background_music": payload.background_music or {},
            "map_settings": payload.map_settings or {},
            "events": payload.events or [],
            "link_expiry_type": payload.link_expiry_type,
            "link_expiry_value": payload.link_expiry_value,
            "link_expiry_date": expiry_date.isoformat() if expiry_date else None,
            "expires_at": invitation_expires_at.isoformat() if invitation_expires_at else None,
            "guest_rooms": payload.guest_rooms or [],
            "pre_wedding_links": payload.pre_wedding_links or [],
            "gallery_privacy": None,  # populated below if provided
            # Per-slot photo toggles (Feb 2026)
            "show_bride_photo": payload.show_bride_photo if payload.show_bride_photo is not None else True,
            "show_groom_photo": payload.show_groom_photo if payload.show_groom_photo is not None else True,
            "show_couple_photo": payload.show_couple_photo if payload.show_couple_photo is not None else True,
            # Couple deep-dive
            "couple_about": sanitize_html(payload.couple_about) if payload.couple_about else None,
            "nakshatram": payload.nakshatram,
            "muhurtam": payload.muhurtam,
            # Opening (link-open) animation background
            "use_couple_photo_as_opening_bg": payload.use_couple_photo_as_opening_bg if payload.use_couple_photo_as_opening_bg is not None else (payload.opening_bg_source != 'custom' if payload.opening_bg_source else True),
            "opening_bg_source": payload.opening_bg_source or 'couple',
            "opening_photo_url": payload.opening_photo_url,
            # 2026 — Universal Invitation Categories
            "invitation_category": payload.invitation_category or "wedding",
            "celebrant_info": payload.celebrant_info,
            "design_selections": payload.design_selections or {},
            "selected_features": payload.selected_features or [],
            "is_published": True,  # Users publish straight away (they paid)
            "created_at": now_iso,
            "updated_at": now_iso,
            "credits_charged": cost,
        }

        # Photo Privacy — hash code if provided and validate
        if payload.gallery_privacy and payload.gallery_privacy.get("enabled"):
            from gallery_privacy import _get_default_privacy, PASSWORD_RE
            from auth import get_password_hash
            import secrets as _secrets
            pv_in = payload.gallery_privacy or {}
            code = (pv_in.get("code") or "").strip()
            if not code or not PASSWORD_RE.match(code):
                raise HTTPException(
                    status_code=400,
                    detail="Access code must be 4–20 chars with at least 1 letter and 1 digit",
                )
            if (pv_in.get("confirm_code") or "") != code:
                raise HTTPException(status_code=400, detail="Access code and confirmation must match")
            pv = _get_default_privacy()
            pv["enabled"] = True
            pv["password_hash"] = get_password_hash(code)
            pv["remember_days"] = int(pv_in.get("remember_days") or 30)
            for f in ("public_highlights_enabled", "private_full_gallery_enabled",
                      "ai_face_match_enabled", "allow_downloads", "allow_share"):
                if f in pv_in:
                    pv[f] = bool(pv_in[f])
            pv["expires_at"] = pv_in.get("expires_at") or None
            profile_doc["gallery_privacy"] = pv

        await db.profiles.insert_one(profile_doc)
        _strip(profile_doc)

        # ── 6. Atomic credit deduction (safe — we already checked balance)
        await db.users.update_one(
            {"user_id": current["user_id"]},
            {"$inc": {"credits": -cost}},
        )
        await db.user_credit_ledger.insert_one({
            "id": uuid.uuid4().hex,
            "user_id": current["user_id"],
            "action": "spend",
            "amount": -cost,
            "reason": f"Invitation · {payload.design_id} · {slug}",
            "profile_id": profile_id,
            "created_at": now_iso,
        })

        updated_user = await db.users.find_one(
            {"user_id": current["user_id"]}, {"_id": 0, "password_hash": 0}
        )
        public_profile = {k: v for k, v in profile_doc.items() if k != "admin_id"}
        return {
            "success": True,
            "profile": {
                **public_profile,
                "invitation_link": f"/invite/{slug}",
            },
            "credits_charged": cost,
            "balance": int(updated_user.get("credits", 0)) if updated_user else 0,
        }

    @router.get("/api/users/profiles")
    async def user_list_profiles(current=Depends(get_current_public_user)):
        cursor = (
            db.profiles.find({"user_id": current["user_id"]}, {"_id": 0, "admin_id": 0})
            .sort("created_at", -1)
            .limit(100)
        )
        profiles = await cursor.to_list(100)
        for p in profiles:
            p["invitation_link"] = f"/invite/{p['slug']}"
        return {"profiles": profiles}

    @router.get("/api/users/profiles/{profile_id}")
    async def user_get_profile(profile_id: str, current=Depends(get_current_public_user)):
        profile = await db.profiles.find_one(
            {"id": profile_id, "user_id": current["user_id"]}, {"_id": 0, "admin_id": 0}
        )
        if not profile:
            raise HTTPException(404, "Profile not found")
        profile["invitation_link"] = f"/invite/{profile['slug']}"
        return profile

    # ── PATCH: edit a user-owned invitation (limited fields) ────────────
    @router.patch("/api/users/profiles/{profile_id}")
    async def user_update_profile(
        profile_id: str,
        payload: dict,
        current=Depends(get_current_public_user),
    ):
        existing = await db.profiles.find_one(
            {"id": profile_id, "user_id": current["user_id"]}, {"_id": 0}
        )
        if not existing:
            raise HTTPException(404, "Invitation not found")

        # Whitelist editable fields — anything else is silently ignored.
        ALLOWED = {
            "groom_name", "bride_name", "venue", "city",
            "invitation_message", "event_date", "about_couple",
            "love_story", "whatsapp_groom", "whatsapp_bride",
            "bride_photo_url", "groom_photo_url", "couple_photo_url",
        }
        update_doc: Dict[str, Any] = {}
        for k, v in (payload or {}).items():
            if k not in ALLOWED:
                continue
            if isinstance(v, str):
                v = v.strip()
                if k in {"about_couple", "love_story", "invitation_message"} and v:
                    v = sanitize_html(v)
            update_doc[k] = v

        if not update_doc:
            raise HTTPException(400, "No editable fields supplied")

        # Coerce event_date if provided
        if "event_date" in update_doc and update_doc["event_date"]:
            try:
                dt = datetime.fromisoformat(update_doc["event_date"].replace("Z", "+00:00"))
                update_doc["event_date"] = dt.isoformat()
            except Exception:
                raise HTTPException(400, "Invalid event_date format")

        update_doc["updated_at"] = _now_iso()
        await db.profiles.update_one(
            {"id": profile_id, "user_id": current["user_id"]},
            {"$set": update_doc},
        )
        updated = await db.profiles.find_one(
            {"id": profile_id}, {"_id": 0, "admin_id": 0}
        )
        if updated:
            updated["invitation_link"] = f"/invite/{updated['slug']}"
        return {"success": True, "profile": updated}

    # ── DELETE: remove a user-owned invitation ─────────────────────────
    @router.delete("/api/users/profiles/{profile_id}")
    async def user_delete_profile(
        profile_id: str, current=Depends(get_current_public_user)
    ):
        existing = await db.profiles.find_one(
            {"id": profile_id, "user_id": current["user_id"]}, {"_id": 0}
        )
        if not existing:
            raise HTTPException(404, "Invitation not found")
        await db.profiles.delete_one(
            {"id": profile_id, "user_id": current["user_id"]}
        )
        # Best-effort cleanup of associated profile media
        try:
            await db.profile_media.delete_many({"profile_id": profile_id})
        except Exception:
            pass
        return {"success": True, "deleted_id": profile_id}

    @router.get("/api/users/credits/ledger")
    async def user_ledger(current=Depends(get_current_public_user)):
        cursor = (
            db.user_credit_ledger.find({"user_id": current["user_id"]}, {"_id": 0})
            .sort("created_at", -1)
            .limit(200)
        )
        entries = await cursor.to_list(200)
        return {"entries": entries}

    # ════════════════════════════════════════════════════════════════════
    # USER IMAGE UPLOAD — for bride/groom/couple thumbnails on the
    # invitation form (used before a profile exists, so we don't bind to
    # any profile_id).  Reuses the same WebP-conversion pipeline.
    # ════════════════════════════════════════════════════════════════════
    @router.post("/api/users/upload-image")
    async def user_upload_image(
        file: UploadFile = File(...),
        slot: str = Form("misc"),
        current=Depends(get_current_public_user),
    ):
        """Upload an image; returns a public URL.  `slot` is a UX hint
        (bride / groom / couple) — stored on the media doc for audit."""
        from server import validate_image_file, convert_to_webp, UPLOADS_DIR
        import random
        import string
        is_valid, error_msg = validate_image_file(file)
        if not is_valid:
            raise HTTPException(400, error_msg)
        webp_data, file_size = await convert_to_webp(file, quality=85)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        slot_safe = "".join(c for c in (slot or "misc") if c.isalnum() or c in "-_")[:20] or "misc"
        filename = f"user-{current['user_id']}-{slot_safe}-{ts}-{suffix}.webp"
        out_path = UPLOADS_DIR / filename
        with open(out_path, "wb") as f:
            f.write(webp_data)
        url = f"/uploads/photos/{filename}"
        # Audit record (best-effort)
        try:
            await db.user_uploads.insert_one({
                "id": uuid.uuid4().hex,
                "user_id": current["user_id"],
                "slot": slot_safe,
                "url": url,
                "file_size": file_size,
                "original_filename": file.filename,
                "created_at": _now_iso(),
            })
        except Exception as e:
            logger.warning("user_uploads insert failed: %s", e)
        return {"url": url, "file_size": file_size}

    return router
