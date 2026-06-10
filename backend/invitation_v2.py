"""
Invitation Viewer V2 — long-scroll wedding invitation builder & viewer.

Routes are all prefixed with /api/v2 so they live alongside the existing
v1 routes without conflict.

Sections (in scroll order):
  1.  cover         — couple names + groom photo
  2.  groom         — groom photo + bio
  3.  bride         — bride photo + bio
  4.  couple        — couple photo + caption
  5.  details       — parents + main event date/time/venue + sub-events
  6.  comments      — wishes wall (reuses existing greetings collection)
  7.  qr            — QR code for the gallery (enable/disable + teaser text)
  8.  ai_match      — AI face match (enable/disable + teaser text)
  9.  directions    — Google Maps link
  10. parking       — free-text parking info
  11. stay          — name → hotel/room lookup (enable/disable)
  12. rsvp          — reuses existing rsvp endpoints
  13. closing       — animation + thank-you text

The whole config lives as `viewer_v2` on the existing Profile document so we
piggyback on auth, slugs, media, gallery_config, etc. that already exist.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger("invitation_v2")


# ───────────────────────────────────────────────────────────────────────
# Pydantic models
# ───────────────────────────────────────────────────────────────────────

class SubEvent(BaseModel):
    """Mini-events under a main wedding (haldi, mehandi, sangeeth, ...)"""
    id: str = ""
    name: str = ""               # e.g. "Haldi"
    enabled: bool = True
    date: str = ""               # ISO date or free-text
    time: str = ""
    venue: str = ""
    description: str = ""
    # Per-sub-event toggles for "comments / qr / ai_match / etc." since the
    # user said these are not mandatory for mini events.
    section_toggles: Dict[str, bool] = Field(default_factory=dict)


class StayGuest(BaseModel):
    """One row in the accommodation lookup table."""
    id: str = ""
    name: str = ""               # name we match against (case-insensitive)
    hotel: str = ""
    room: str = ""
    notes: str = ""              # check-in time, transport etc.


class ViewerV2Config(BaseModel):
    """Full invitation viewer config — every section + its enable flag."""
    # Theme + design
    theme_id: str = "mughal"
    design_id: str = ""
    accent_color: str = ""

    # 1 — Cover
    cover_enabled: bool = True
    cover_bride_name: str = ""
    cover_groom_name: str = ""
    cover_groom_photo_url: str = ""    # initial hero photo
    cover_background_url: str = ""

    # 2 — Groom solo
    groom_enabled: bool = True
    groom_photo_url: str = ""
    groom_info: str = ""

    # 3 — Bride solo
    bride_enabled: bool = True
    bride_photo_url: str = ""
    bride_info: str = ""

    # 4 — Couple
    couple_enabled: bool = True
    couple_photo_url: str = ""
    couple_caption: str = ""

    # 5 — Details (parents + date + time + sub-events)
    details_enabled: bool = True
    groom_parents: str = ""
    bride_parents: str = ""
    main_event_name: str = "Wedding"
    main_event_date: str = ""
    main_event_time: str = ""
    main_event_venue: str = ""
    main_event_address: str = ""
    sub_events: List[SubEvent] = Field(default_factory=list)

    # 6 — Comments / wishes wall
    comments_enabled: bool = True
    comments_background_url: str = ""   # blank → use couple_photo_url

    # 7 — QR code (for the gallery)
    qr_enabled: bool = False
    qr_target_url: str = ""             # what the QR encodes
    qr_pre_event_text: str = ("After the wedding, scan this QR to see and "
                              "download every photo from the celebration.")

    # 8 — AI face match
    ai_match_enabled: bool = False
    ai_match_pre_event_text: str = ("After the wedding, upload your selfie "
                                    "and our AI will instantly find every "
                                    "photo of you from the event — yours to "
                                    "download.")

    # 9 — Directions
    directions_enabled: bool = True
    directions_url: str = ""            # google maps URL
    directions_label: str = "Open directions in Google Maps"

    # 10 — Parking
    parking_enabled: bool = True
    parking_text: str = ""

    # 11 — Stay
    stay_enabled: bool = False
    stay_intro: str = ("Type your name below to see where you're staying "
                       "and your room number.")
    stay_background_url: str = ""       # blank → use couple_photo_url
    stay_guests: List[StayGuest] = Field(default_factory=list)

    # 12 — RSVP
    rsvp_enabled: bool = True

    # 13 — Closing
    closing_enabled: bool = True
    closing_text: str = "Your presence is the greatest gift of all."
    closing_animation_id: str = "petals"
    closing_signature: str = ""         # e.g. "— Anaya & Vihaan"


class ViewerConfigUpdate(BaseModel):
    """PUT payload — any subset of the fields."""
    config: Dict[str, Any]


class StayLookupResponse(BaseModel):
    matches: List[StayGuest]


class V2CommentCreate(BaseModel):
    name: str
    message: str


class V2Comment(BaseModel):
    id: str
    profile_id: str
    name: str
    message: str
    created_at: str
    deleted: bool = False


# ───────────────────────────────────────────────────────────────────────
# Defaults helper
# ───────────────────────────────────────────────────────────────────────

def default_viewer_v2() -> Dict[str, Any]:
    return ViewerV2Config().model_dump()


# ───────────────────────────────────────────────────────────────────────
# Router builder — wired into server.py
# ───────────────────────────────────────────────────────────────────────

def build_invitation_v2_router(db, get_current_admin):
    router = APIRouter(prefix="/api/v2", tags=["invitation-v2"])

    # ───── helpers ─────
    async def _profile_by_id_or_slug(ident: str) -> Optional[dict]:
        prof = await db.profiles.find_one({"id": ident}, {"_id": 0})
        if not prof:
            prof = await db.profiles.find_one({"slug_url": ident}, {"_id": 0})
        return prof

    # ───── ADMIN — viewer config CRUD ─────
    @router.get("/admin/profiles/{profile_id}/viewer-config")
    async def get_viewer_config(profile_id: str,
                                admin_id: str = Depends(get_current_admin)):
        prof = await _profile_by_id_or_slug(profile_id)
        if not prof:
            raise HTTPException(404, "Profile not found")
        cfg = prof.get("viewer_v2") or default_viewer_v2()
        # Pre-fill from existing profile fields so first-time builders get a
        # sensible starting state.
        if not cfg.get("cover_bride_name"):
            cfg["cover_bride_name"] = prof.get("bride_name") or ""
        if not cfg.get("cover_groom_name"):
            cfg["cover_groom_name"] = prof.get("groom_name") or ""
        return {
            "profile_id": prof["id"],
            "slug_url": prof.get("slug_url"),
            "config": cfg,
        }

    @router.put("/admin/profiles/{profile_id}/viewer-config")
    async def put_viewer_config(profile_id: str,
                                payload: ViewerConfigUpdate,
                                admin_id: str = Depends(get_current_admin)):
        prof = await _profile_by_id_or_slug(profile_id)
        if not prof:
            raise HTTPException(404, "Profile not found")
        cfg = {**default_viewer_v2(), **(prof.get("viewer_v2") or {}), **payload.config}
        await db.profiles.update_one(
            {"id": prof["id"]},
            {"$set": {
                "viewer_v2": cfg,
                "viewer_v2_updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return {"profile_id": prof["id"], "config": cfg}

    @router.post("/admin/profiles/{profile_id}/viewer-config/section-toggle")
    async def toggle_section(profile_id: str,
                             section: str = Query(..., min_length=1),
                             enabled: bool = Query(True),
                             admin_id: str = Depends(get_current_admin)):
        """Quick atomic toggle for a single section flag."""
        ALLOWED = {
            "cover", "groom", "bride", "couple", "details", "comments",
            "qr", "ai_match", "directions", "parking", "stay", "rsvp",
            "closing",
        }
        if section not in ALLOWED:
            raise HTTPException(400, f"Unknown section '{section}'")
        prof = await _profile_by_id_or_slug(profile_id)
        if not prof:
            raise HTTPException(404, "Profile not found")
        flag = f"{section}_enabled"
        cfg = {**default_viewer_v2(), **(prof.get("viewer_v2") or {})}
        cfg[flag] = bool(enabled)
        await db.profiles.update_one({"id": prof["id"]}, {"$set": {"viewer_v2": cfg}})
        return {"profile_id": prof["id"], "section": section, "enabled": cfg[flag]}

    # ───── PUBLIC — viewer payload ─────
    @router.get("/invitations/{slug}")
    async def public_viewer_payload(slug: str):
        """Single endpoint that returns everything the viewer needs to render
        a slug — config + sanitized profile bits + comments + media list."""
        prof = await _profile_by_id_or_slug(slug)
        if not prof:
            raise HTTPException(404, "Invitation not found")
        cfg = {**default_viewer_v2(), **(prof.get("viewer_v2") or {})}

        # Pull up to 50 most-recent approved/visible comments
        comments_cursor = db.invitation_v2_comments.find(
            {"profile_id": prof["id"], "deleted": {"$ne": True}},
            {"_id": 0},
        ).sort("created_at", -1).limit(50)
        comments = [c async for c in comments_cursor]

        # Public-safe profile fields
        safe = {
            "id": prof["id"],
            "slug_url": prof.get("slug_url"),
            "bride_name": prof.get("bride_name") or cfg.get("cover_bride_name"),
            "groom_name": prof.get("groom_name") or cfg.get("cover_groom_name"),
            "wedding_date": prof.get("wedding_date") or cfg.get("main_event_date"),
            "venue": prof.get("venue") or cfg.get("main_event_venue"),
        }

        # Strip stay_guests from public payload (they're queried via lookup)
        public_cfg = {k: v for k, v in cfg.items() if k != "stay_guests"}
        # Indicate whether stay lookup is available so the frontend can show
        # the search box without leaking the guest list.
        public_cfg["_stay_lookup_available"] = bool(
            cfg.get("stay_enabled") and cfg.get("stay_guests")
        )

        # Surface gallery + face-match availability so the viewer knows
        # whether to show the QR / AI-match cards.
        gc = prof.get("gallery_config") or {}
        gallery_meta = {
            "enabled": bool(gc.get("enabled")),
            "face_search_enabled": bool(gc.get("face_search_enabled")),
            "total_photos": int(gc.get("total_photos") or 0),
        }

        return {
            "profile": safe,
            "config": public_cfg,
            "comments": comments,
            "gallery": gallery_meta,
        }

    # ───── PUBLIC — comments ─────
    @router.post("/invitations/{slug}/comments")
    async def post_comment(slug: str, payload: V2CommentCreate):
        prof = await _profile_by_id_or_slug(slug)
        if not prof:
            raise HTTPException(404, "Invitation not found")
        cfg = prof.get("viewer_v2") or {}
        if not cfg.get("comments_enabled", True):
            raise HTTPException(403, "Comments are disabled for this invitation")
        name = (payload.name or "").strip()
        msg = (payload.message or "").strip()
        if not name or not msg:
            raise HTTPException(400, "Both name and message are required")
        if len(name) > 80 or len(msg) > 800:
            raise HTTPException(400, "Name max 80 chars, message max 800 chars")
        import uuid
        doc = {
            "id": str(uuid.uuid4()),
            "profile_id": prof["id"],
            "name": name,
            "message": msg,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "deleted": False,
        }
        await db.invitation_v2_comments.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @router.get("/invitations/{slug}/comments")
    async def list_comments(slug: str, limit: int = 50):
        prof = await _profile_by_id_or_slug(slug)
        if not prof:
            raise HTTPException(404, "Invitation not found")
        limit = max(1, min(200, int(limit)))
        cursor = db.invitation_v2_comments.find(
            {"profile_id": prof["id"], "deleted": {"$ne": True}},
            {"_id": 0},
        ).sort("created_at", -1).limit(limit)
        return {"comments": [c async for c in cursor]}

    @router.delete("/admin/comments/{comment_id}")
    async def delete_comment(comment_id: str,
                             admin_id: str = Depends(get_current_admin)):
        res = await db.invitation_v2_comments.update_one(
            {"id": comment_id},
            {"$set": {"deleted": True,
                      "deleted_at": datetime.now(timezone.utc).isoformat(),
                      "deleted_by": admin_id}},
        )
        if res.matched_count == 0:
            raise HTTPException(404, "Comment not found")
        return {"id": comment_id, "deleted": True}

    @router.get("/admin/profiles/{profile_id}/comments")
    async def admin_list_comments(profile_id: str,
                                  include_deleted: bool = False,
                                  admin_id: str = Depends(get_current_admin)):
        prof = await _profile_by_id_or_slug(profile_id)
        if not prof:
            raise HTTPException(404, "Profile not found")
        q = {"profile_id": prof["id"]}
        if not include_deleted:
            q["deleted"] = {"$ne": True}
        cursor = db.invitation_v2_comments.find(q, {"_id": 0}).sort("created_at", -1).limit(500)
        return {"comments": [c async for c in cursor]}

    # ───── PUBLIC — stay lookup ─────
    @router.get("/invitations/{slug}/stay-lookup")
    async def stay_lookup(slug: str, name: str = Query(..., min_length=1, max_length=120)):
        prof = await _profile_by_id_or_slug(slug)
        if not prof:
            raise HTTPException(404, "Invitation not found")
        cfg = prof.get("viewer_v2") or {}
        if not cfg.get("stay_enabled"):
            raise HTTPException(403, "Stay lookup is not enabled for this invitation")
        guests = cfg.get("stay_guests") or []
        q = name.strip().lower()
        matches = []
        for g in guests:
            full_name = (g.get("name") or "").strip().lower()
            if not full_name:
                continue
            # case-insensitive substring match in either direction
            if q in full_name or full_name in q:
                matches.append({
                    "id": g.get("id") or "",
                    "name": g.get("name", ""),
                    "hotel": g.get("hotel", ""),
                    "room": g.get("room", ""),
                    "notes": g.get("notes", ""),
                })
        return {"query": name, "matches": matches}

    return router
