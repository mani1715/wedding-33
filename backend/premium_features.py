"""
Maharani.studio — PREMIUM FEATURES MODULE (rebranded to MAJA Creations)
==========================================
Implements priority Phase 38 features:
- Live Photo Wall (real-time gallery, desktop uploader API, guest upload, QR)
- Extended AI Suite (multi-language story, greeting personalization, translation, image enhancement)
- Smart RSVP (extended fields, exports)
- WhatsApp System (Twilio, mock fallback)
- Digital Shagun (UPI deep links, Razorpay)
- Personalized Itinerary
- Travel & Navigation deep links
- Wall of Love, Blessing Counter
- Analytics enrichments
"""
import os
import io
import csv
import uuid
import json
import base64
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Literal
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, Query, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from PIL import Image as PILImage

# ============================================================================
# Storage helpers
# ============================================================================
LIVE_GALLERY_DIR = Path("/app/uploads/live_gallery")
LIVE_GALLERY_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_doc(doc: dict) -> dict:
    """Remove Mongo _id from doc for safe JSON response."""
    if doc and "_id" in doc:
        del doc["_id"]
    return doc


# ============================================================================
# Pydantic models
# ============================================================================
class LiveGallerySettings(BaseModel):
    enabled: bool = True
    guest_upload_enabled: bool = True
    auto_approve: bool = True
    moderation_required: bool = False
    watermark_enabled: bool = False
    max_photos_per_guest: int = 20


class GuestPhotoUpload(BaseModel):
    guest_name: str = Field(..., min_length=1, max_length=80)
    caption: Optional[str] = Field(None, max_length=240)
    image_base64: str  # data URL or raw base64
    event_type: Optional[str] = None  # haldi / mehendi / sangeet / marriage / reception


class LivePhotoResponse(BaseModel):
    id: str
    profile_id: str
    url: str
    thumb_url: str
    caption: Optional[str]
    uploader_type: str  # photographer | guest | desktop
    uploader_name: Optional[str]
    event_type: Optional[str]
    favorite_count: int = 0
    approved: bool = True
    created_at: str


class UploaderTokenResponse(BaseModel):
    token: str
    profile_id: str
    profile_slug: str
    upload_url: str
    expires_at: str


class FavoriteRequest(BaseModel):
    photo_id: str
    device_id: str


# AI models
class AIStoryV2Request(BaseModel):
    bride: str
    groom: str
    how_we_met: Optional[str] = None
    proposal_story: Optional[str] = None
    wedding_journey: Optional[str] = None
    tone: Literal["royal", "emotional", "poetic", "cinematic", "traditional", "modern"] = "cinematic"
    language: Literal["en", "te", "hi", "ta", "kn", "mr", "bn"] = "en"
    cultural_region: Optional[str] = None


class GreetingPersonalizeRequest(BaseModel):
    guest_name: str
    relation: Optional[str] = None  # family / friend / colleague / elder
    tone: Literal["formal", "warm", "playful", "royal"] = "warm"
    language: Literal["en", "te", "hi", "ta", "kn", "mr", "bn"] = "en"
    couple: Optional[str] = None  # "Riya & Aarav"


class TranslateBulkRequest(BaseModel):
    items: Dict[str, str]  # {key: text}
    target_language: Literal["en", "te", "hi", "ta", "kn", "mr", "bn"]


class ImageEnhanceRequest(BaseModel):
    image_base64: str  # data URL
    enhancements: List[str] = ["lighting", "color", "skin_tone", "upscale"]


# WhatsApp
class WhatsAppInvitationRequest(BaseModel):
    profile_id: str
    recipients: List[Dict[str, str]]  # [{name, phone}]
    custom_message: Optional[str] = None


class WhatsAppReminderRequest(BaseModel):
    profile_id: str
    reminder_type: Literal["7_days", "3_days", "1_day", "custom"] = "3_days"
    target: Literal["all", "confirmed", "pending"] = "all"
    custom_message: Optional[str] = None


# Digital Shagun
class ShagunSettings(BaseModel):
    enabled: bool = True
    upi_id: Optional[str] = None
    payee_name: Optional[str] = None
    suggested_amounts: List[int] = [101, 501, 1001, 2001, 5001, 11000]
    blessing_message: Optional[str] = "Your blessings mean more than any gift. — Riya & Aarav"
    gpay_handle: Optional[str] = None
    phonepe_handle: Optional[str] = None
    paytm_handle: Optional[str] = None
    # Prompt 12: Razorpay support (per-photographer)
    razorpay_enabled: bool = False
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None
    platform_fee_percent: float = 5.0


# Itinerary
class ItineraryAccess(BaseModel):
    audience: Literal["all", "family", "close", "general"] = "all"


# ============================================================================
# Helper: get profile by id or slug
# ============================================================================
async def _get_profile_by_id_or_slug(db, identifier: str) -> dict:
    profile = await db.profiles.find_one(
        {"$or": [{"id": identifier}, {"slug": identifier}]},
        {"_id": 0}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def _verify_admin_owns(profile: dict, admin_data: dict):
    if admin_data.get('role') == 'super_admin':
        return
    if profile.get('admin_id') != admin_data.get('admin_id'):
        raise HTTPException(status_code=403, detail="Not authorized")


# ============================================================================
# Build router (caller injects db, ai client, admin dep)
# ============================================================================
def build_premium_router(db, get_current_admin, require_admin, ai_chat_factory):
    """
    Build the premium-features APIRouter.
    
    - db: motor AsyncIOMotorDatabase
    - get_current_admin: FastAPI dep returning admin_id (str)
    - require_admin: FastAPI dep returning {admin_id, role}
    - ai_chat_factory: async fn(system_msg, session_id) -> sends a single prompt, returns text
    """
    router = APIRouter(prefix="/api", tags=["premium"])

    # ========================================================================
    # AI: Greeting personalization
    # ========================================================================
    @router.post("/admin/ai/greeting-personalize")
    async def ai_greeting_personalize(req: GreetingPersonalizeRequest,
                                       admin_id: str = Depends(get_current_admin)):
        lang_map = {"en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil",
                    "kn": "Kannada", "mr": "Marathi", "bn": "Bengali"}
        tone_brief = {
            "formal": "respectful and dignified",
            "warm": "warm and affectionate",
            "playful": "playful, witty, light-hearted",
            "royal": "regal, cinematic, slow and dignified",
        }[req.tone]
        system = (
            "You are an elite Indian wedding stationery copywriter. "
            "You write personalized one-line greetings for invitations. "
            "Tone is " + tone_brief + ". Output ONLY the greeting line (max 14 words). "
            "Never use emojis or quotation marks."
        )
        user = (
            f"Write a personalized greeting in {lang_map[req.language]} "
            f"for guest '{req.guest_name}'"
            + (f" (relation: {req.relation})" if req.relation else "")
            + (f" from the couple {req.couple}." if req.couple else ".")
        )
        try:
            text = await ai_chat_factory(system, f"greet-{admin_id}-{uuid.uuid4()}", user)
            return {"greeting": text.strip().strip('"').strip("'")}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"AI muse is resting. ({str(e)[:80]})")

    @router.post("/admin/ai/translate-bulk")
    async def ai_translate_bulk(req: TranslateBulkRequest,
                                 admin_id: str = Depends(get_current_admin)):
        lang_map = {"en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil",
                    "kn": "Kannada", "mr": "Marathi", "bn": "Bengali"}
        if req.target_language not in lang_map:
            raise HTTPException(status_code=400, detail="Unsupported language")

        items_payload = json.dumps(req.items, ensure_ascii=False)
        system = (
            "You are a professional Indian-wedding translator. "
            "Translate the given JSON object's VALUES to " + lang_map[req.target_language] + ". "
            "Preserve keys, JSON shape, names, dates, and cultural meaning. "
            "Output ONLY a valid JSON object. No prose, no markdown fences."
        )
        try:
            text = await ai_chat_factory(system, f"tx-{admin_id}-{uuid.uuid4()}", items_payload)
            text = text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.rsplit("```", 1)[0].strip()
            return {"translations": json.loads(text), "target_language": req.target_language}
        except json.JSONDecodeError:
            raise HTTPException(status_code=502, detail="Translation came back malformed.")
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"AI muse is resting. ({str(e)[:80]})")

    @router.post("/admin/ai/story-v2")
    async def ai_story_v2(req: AIStoryV2Request,
                           admin_id: str = Depends(get_current_admin)):
        lang_map = {"en": "English", "te": "Telugu", "hi": "Hindi", "ta": "Tamil",
                    "kn": "Kannada", "mr": "Marathi", "bn": "Bengali"}
        tone_briefs = {
            "royal": "regal, cinematic, slow, opulent — never tacky",
            "emotional": "tender, heartfelt, gently emotional — restraint over melodrama",
            "poetic": "lyrical, metaphor-rich, evocative — occasional Sanskrit/Urdu phrase if natural (with English meaning)",
            "cinematic": "Sanjay-Leela-Bhansali film — sweeping, restrained, luxurious",
            "traditional": "rooted in Indian tradition, dignified, ritual-aware",
            "modern": "minimal, dignified, contemporary — short sentences",
        }
        system = (
            "You are MAJA — an elite Indian wedding copywriter. "
            "You write the couple's love-journey story in cinematic prose. "
            "Never cheesy, never generic, never AI-tells. Output ONLY the prose."
        )
        sections = []
        if req.how_we_met:
            sections.append(f"How we met: {req.how_we_met}")
        if req.proposal_story:
            sections.append(f"The proposal: {req.proposal_story}")
        if req.wedding_journey:
            sections.append(f"The journey: {req.wedding_journey}")

        user = (
            f"Write a 3-paragraph love-journey story for {req.bride} (bride) and {req.groom} (groom).\n"
            f"Tone: {tone_briefs[req.tone]}.\n"
            f"Language: {lang_map[req.language]}.\n"
            f"Cultural region: {req.cultural_region or 'general Indian'}.\n\n"
            f"Source material from the couple:\n" + "\n".join(sections) + "\n\n"
            "Rules: no emojis, no headings, no quotes around the prose, "
            "keep cinematic restraint, do NOT mention you are an AI."
        )
        try:
            text = await ai_chat_factory(system, f"story2-{admin_id}-{uuid.uuid4()}", user)
            try:
                await db.ai_story_logs.insert_one({
                    "id": str(uuid.uuid4()),
                    "admin_id": admin_id,
                    "kind": "story_v2",
                    "bride": req.bride,
                    "groom": req.groom,
                    "tone": req.tone,
                    "language": req.language,
                    "created_at": _now_iso(),
                })
            except Exception:
                pass
            return {"story": text.strip()}
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("budget", "quota", "exceeded", "rate")):
                raise HTTPException(status_code=503,
                    detail="The AI muse is resting briefly. Please try again, or top up your Universal Key in Profile → Universal Key.")
            raise HTTPException(status_code=502, detail=f"AI temporarily unavailable. ({str(e)[:80]})")

    @router.post("/admin/ai/enhance-image")
    async def ai_enhance_image(req: ImageEnhanceRequest,
                                admin_id: str = Depends(get_current_admin)):
        """
        Auto-enhance an image using Pillow (no external API):
        - lighting: contrast + auto-brightness
        - color: saturation boost
        - skin_tone: subtle warm balance
        - upscale: 2x with high-quality resampler
        Returns enhanced image as base64 data URL.
        """
        from PIL import ImageEnhance, ImageOps
        try:
            data = req.image_base64
            if data.startswith("data:"):
                data = data.split(",", 1)[1]
            raw = base64.b64decode(data)
            img = PILImage.open(io.BytesIO(raw)).convert("RGB")

            if "lighting" in req.enhancements:
                img = ImageOps.autocontrast(img, cutoff=2)
                img = ImageEnhance.Brightness(img).enhance(1.05)
                img = ImageEnhance.Contrast(img).enhance(1.10)
            if "color" in req.enhancements:
                img = ImageEnhance.Color(img).enhance(1.15)
            if "skin_tone" in req.enhancements:
                # subtle warm balance
                r, g, b = img.split()
                r = r.point(lambda v: min(255, int(v * 1.04)))
                g = g.point(lambda v: min(255, int(v * 1.01)))
                img = PILImage.merge("RGB", (r, g, b))
            if "upscale" in req.enhancements and img.width < 2400:
                new_w = min(img.width * 2, 2880)
                new_h = int(img.height * (new_w / img.width))
                img = img.resize((new_w, new_h), PILImage.Resampling.LANCZOS)
            # mild sharpen
            img = ImageEnhance.Sharpness(img).enhance(1.2)

            out = io.BytesIO()
            img.save(out, format="JPEG", quality=92, optimize=True)
            b64 = base64.b64encode(out.getvalue()).decode("ascii")
            return {
                "enhanced_image": f"data:image/jpeg;base64,{b64}",
                "size_bytes": len(out.getvalue()),
                "dimensions": {"width": img.width, "height": img.height},
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image enhancement failed: {str(e)[:100]}")

    # ========================================================================
    # LIVE PHOTO WALL
    # ========================================================================
    @router.get("/admin/profiles/{profile_id}/live-gallery/settings")
    async def get_live_gallery_settings(profile_id: str,
                                         admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        settings = profile.get("live_gallery_settings") or LiveGallerySettings().model_dump()
        return settings

    @router.put("/admin/profiles/{profile_id}/live-gallery/settings")
    async def update_live_gallery_settings(profile_id: str,
                                            settings: LiveGallerySettings,
                                            admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        await db.profiles.update_one(
            {"id": profile["id"]},
            {"$set": {"live_gallery_settings": settings.model_dump(),
                      "updated_at": _now_iso()}}
        )
        return {"success": True, "settings": settings.model_dump()}

    @router.post("/admin/profiles/{profile_id}/live-gallery/uploader-token",
                 response_model=UploaderTokenResponse)
    async def create_uploader_token(profile_id: str,
                                     ttl_hours: int = 72,
                                     admin_data: dict = Depends(require_admin)):
        """Generate a short-lived token for desktop uploader app."""
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)

        token = uuid.uuid4().hex + uuid.uuid4().hex
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
        await db.uploader_tokens.insert_one({
            "token": token,
            "profile_id": profile["id"],
            "admin_id": profile["admin_id"],
            "expires_at": expires_at.isoformat(),
            "created_at": _now_iso(),
            "revoked": False,
        })
        backend_url = os.environ.get("PUBLIC_BACKEND_URL", "")
        return UploaderTokenResponse(
            token=token,
            profile_id=profile["id"],
            profile_slug=profile["slug"],
            upload_url=f"{backend_url}/api/live-gallery/desktop-upload",
            expires_at=expires_at.isoformat(),
        )

    @router.post("/admin/profiles/{profile_id}/live-gallery/uploader-token/revoke")
    async def revoke_uploader_token(profile_id: str, token: str,
                                     admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        await db.uploader_tokens.update_one({"token": token},
                                             {"$set": {"revoked": True}})
        return {"success": True}

    @router.post("/live-gallery/desktop-upload")
    async def desktop_upload(
        request: Request,
        file: UploadFile = File(...),
        caption: Optional[str] = Form(None),
        event_type: Optional[str] = Form(None),
    ):
        """
        Endpoint hit by the desktop uploader app.
        Auth via 'X-Uploader-Token' header (no JWT needed).
        """
        token = request.headers.get("X-Uploader-Token") or request.headers.get("x-uploader-token")
        if not token:
            raise HTTPException(status_code=401, detail="Uploader token required")
        token_doc = await db.uploader_tokens.find_one({"token": token, "revoked": False},
                                                       {"_id": 0})
        if not token_doc:
            raise HTTPException(status_code=401, detail="Invalid or revoked token")

        expires_at = token_doc["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=401, detail="Token expired")

        # Save file
        profile_id = token_doc["profile_id"]
        ext = (file.filename or "photo.jpg").split(".")[-1].lower()
        if ext not in ("jpg", "jpeg", "png", "webp", "heic"):
            ext = "jpg"
        photo_id = uuid.uuid4().hex
        target_dir = LIVE_GALLERY_DIR / profile_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{photo_id}.{ext}"

        raw = await file.read()
        # Compress + thumbnail
        try:
            img = PILImage.open(io.BytesIO(raw)).convert("RGB")
            # main (compressed)
            if img.width > 1920:
                ratio = 1920 / img.width
                img = img.resize((1920, int(img.height * ratio)),
                                   PILImage.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=86, optimize=True)
            target_path.write_bytes(buf.getvalue())
            # thumb
            thumb = img.copy()
            thumb.thumbnail((480, 480), PILImage.Resampling.LANCZOS)
            thumb_buf = io.BytesIO()
            thumb.save(thumb_buf, format="JPEG", quality=78, optimize=True)
            thumb_path = target_dir / f"{photo_id}_thumb.jpg"
            thumb_path.write_bytes(thumb_buf.getvalue())
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)[:80]}")

        profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
        settings = profile.get("live_gallery_settings") or LiveGallerySettings().model_dump()
        approved = bool(settings.get("auto_approve", True))

        doc = {
            "id": photo_id,
            "profile_id": profile_id,
            "url": f"/uploads/live_gallery/{profile_id}/{photo_id}.{ext}",
            "thumb_url": f"/uploads/live_gallery/{profile_id}/{photo_id}_thumb.jpg",
            "caption": caption,
            "uploader_type": "desktop",
            "uploader_name": "Photographer",
            "event_type": event_type,
            "favorite_count": 0,
            "favorited_by": [],
            "approved": approved,
            "created_at": _now_iso(),
        }
        await db.live_photos.insert_one(doc)
        _serialize_doc(doc)
        return doc

    @router.post("/invite/{slug}/live-gallery/guest-upload")
    async def guest_upload(slug: str, payload: GuestPhotoUpload):
        profile = await _get_profile_by_id_or_slug(db, slug)
        settings = profile.get("live_gallery_settings") or LiveGallerySettings().model_dump()
        if not settings.get("guest_upload_enabled", True):
            raise HTTPException(status_code=403, detail="Guest uploads disabled")

        data = payload.image_base64
        if data.startswith("data:"):
            data = data.split(",", 1)[1]
        try:
            raw = base64.b64decode(data)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image")
        if len(raw) > 8 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Image too large (max 8MB)")

        photo_id = uuid.uuid4().hex
        target_dir = LIVE_GALLERY_DIR / profile["id"]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{photo_id}.jpg"
        thumb_path = target_dir / f"{photo_id}_thumb.jpg"

        try:
            img = PILImage.open(io.BytesIO(raw)).convert("RGB")
            if img.width > 1600:
                ratio = 1600 / img.width
                img = img.resize((1600, int(img.height * ratio)),
                                   PILImage.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            target_path.write_bytes(buf.getvalue())
            thumb = img.copy()
            thumb.thumbnail((480, 480), PILImage.Resampling.LANCZOS)
            tbuf = io.BytesIO()
            thumb.save(tbuf, format="JPEG", quality=78, optimize=True)
            thumb_path.write_bytes(tbuf.getvalue())
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image: {str(e)[:60]}")

        approved = bool(settings.get("auto_approve", True)) and not settings.get("moderation_required", False)
        doc = {
            "id": photo_id,
            "profile_id": profile["id"],
            "url": f"/uploads/live_gallery/{profile['id']}/{photo_id}.jpg",
            "thumb_url": f"/uploads/live_gallery/{profile['id']}/{photo_id}_thumb.jpg",
            "caption": payload.caption,
            "uploader_type": "guest",
            "uploader_name": payload.guest_name,
            "event_type": payload.event_type,
            "favorite_count": 0,
            "favorited_by": [],
            "approved": approved,
            "created_at": _now_iso(),
        }
        await db.live_photos.insert_one(doc)
        _serialize_doc(doc)
        return doc

    @router.get("/invite/{slug}/live-gallery")
    async def get_live_gallery(slug: str, since: Optional[str] = None,
                                limit: int = 60, skip: int = 0):
        profile = await _get_profile_by_id_or_slug(db, slug)
        query = {"profile_id": profile["id"], "approved": True}
        if since:
            query["created_at"] = {"$gt": since}
        cursor = db.live_photos.find(query, {"_id": 0, "favorited_by": 0}).sort("created_at", -1).skip(skip).limit(limit)
        photos = await cursor.to_list(limit)
        total = await db.live_photos.count_documents({"profile_id": profile["id"], "approved": True})
        return {"photos": photos, "total": total, "fetched_at": _now_iso()}

    @router.get("/admin/profiles/{profile_id}/live-gallery")
    async def admin_get_live_gallery(profile_id: str,
                                      include_pending: bool = True,
                                      admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        query = {"profile_id": profile["id"]}
        if not include_pending:
            query["approved"] = True
        cursor = db.live_photos.find(query, {"_id": 0}).sort("created_at", -1)
        photos = await cursor.to_list(2000)
        return {"photos": photos, "total": len(photos)}

    @router.put("/admin/live-gallery/{photo_id}/moderate")
    async def moderate_photo(photo_id: str, approved: bool,
                              admin_data: dict = Depends(require_admin)):
        photo = await db.live_photos.find_one({"id": photo_id}, {"_id": 0})
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        profile = await db.profiles.find_one({"id": photo["profile_id"]}, {"_id": 0})
        if profile:
            _verify_admin_owns(profile, admin_data)
        await db.live_photos.update_one({"id": photo_id},
                                         {"$set": {"approved": approved}})
        return {"success": True, "approved": approved}

    @router.delete("/admin/live-gallery/{photo_id}")
    async def delete_photo(photo_id: str,
                            admin_data: dict = Depends(require_admin)):
        photo = await db.live_photos.find_one({"id": photo_id}, {"_id": 0})
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        profile = await db.profiles.find_one({"id": photo["profile_id"]}, {"_id": 0})
        if profile:
            _verify_admin_owns(profile, admin_data)
        # delete files (best effort)
        try:
            for url in (photo.get("url"), photo.get("thumb_url")):
                if url:
                    p = Path("/app" + url) if url.startswith("/uploads") else None
                    if p and p.exists():
                        p.unlink()
        except Exception:
            pass
        await db.live_photos.delete_one({"id": photo_id})
        return {"success": True}

    @router.post("/invite/{slug}/live-gallery/favorite")
    async def favorite_photo(slug: str, req: FavoriteRequest):
        photo = await db.live_photos.find_one({"id": req.photo_id}, {"_id": 0})
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        favorited = req.device_id in (photo.get("favorited_by") or [])
        if favorited:
            await db.live_photos.update_one({"id": req.photo_id},
                {"$pull": {"favorited_by": req.device_id},
                 "$inc": {"favorite_count": -1}})
            return {"favorited": False}
        else:
            await db.live_photos.update_one({"id": req.photo_id},
                {"$addToSet": {"favorited_by": req.device_id},
                 "$inc": {"favorite_count": 1}})
            return {"favorited": True}

    # ========================================================================
    # WHATSAPP (Twilio)
    # ========================================================================
    def _twilio_client():
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        tok = os.environ.get("TWILIO_AUTH_TOKEN")
        if not sid or not tok:
            return None
        try:
            from twilio.rest import Client
            return Client(sid, tok)
        except Exception:
            return None

    def _twilio_from():
        return os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    @router.get("/admin/whatsapp/status")
    async def whatsapp_status(admin_id: str = Depends(get_current_admin)):
        client = _twilio_client()
        return {
            "configured": client is not None,
            "from_number": _twilio_from() if client else None,
            "mode": "live" if client else "mock",
        }

    @router.post("/admin/whatsapp/send-invitation")
    async def whatsapp_send_invitation(req: WhatsAppInvitationRequest,
                                        admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, req.profile_id)
        _verify_admin_owns(profile, admin_data)
        backend_url = os.environ.get("PUBLIC_BACKEND_URL", "")
        invite_link = f"{backend_url.replace('/api','')}/invite/{profile['slug']}" if backend_url else f"/invite/{profile['slug']}"

        couple = f"{profile.get('groom_name','')} & {profile.get('bride_name','')}"
        date = profile.get("event_date", "")
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date).strftime("%d %B %Y")
            except Exception:
                pass

        client = _twilio_client()
        from_num = _twilio_from()
        results = []
        for r in req.recipients:
            name = r.get("name", "Dear Guest")
            phone = r.get("phone", "").strip()
            if not phone:
                continue
            if not phone.startswith("+"):
                phone = "+91" + phone.lstrip("0")  # default India
            body = req.custom_message or (
                f"Dear {name},\n\n"
                f"With joyful hearts, {couple} request the honour of your presence "
                f"at their wedding on {date}.\n\n"
                f"View the invitation: {invite_link}\n\n"
                f"— Maharani.studio"
            )
            body = body.replace("{name}", name).replace("{link}", invite_link)
            if client:
                try:
                    msg = client.messages.create(
                        from_=from_num,
                        to=f"whatsapp:{phone}",
                        body=body,
                    )
                    results.append({"phone": phone, "name": name,
                                    "status": "sent", "sid": msg.sid})
                except Exception as e:
                    results.append({"phone": phone, "name": name,
                                    "status": "failed", "error": str(e)[:120]})
            else:
                results.append({"phone": phone, "name": name,
                                "status": "mock", "sid": "mock_" + uuid.uuid4().hex[:10]})

        await db.whatsapp_logs.insert_one({
            "id": uuid.uuid4().hex,
            "profile_id": profile["id"],
            "admin_id": admin_data["admin_id"],
            "kind": "invitation",
            "count": len(results),
            "mode": "live" if client else "mock",
            "results": results,
            "created_at": _now_iso(),
        })
        return {"sent": len(results), "mode": "live" if client else "mock", "results": results}

    @router.post("/admin/whatsapp/send-reminder")
    async def whatsapp_send_reminder(req: WhatsAppReminderRequest,
                                      admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, req.profile_id)
        _verify_admin_owns(profile, admin_data)
        rsvp_query = {"profile_id": profile["id"]}
        if req.target == "confirmed":
            rsvp_query["attending"] = True
        elif req.target == "pending":
            rsvp_query["attending"] = None
        rsvps = await db.rsvps.find(rsvp_query, {"_id": 0}).to_list(2000)
        recipients = []
        for r in rsvps:
            phone = r.get("guest_phone") or r.get("phone")
            name = r.get("guest_name") or r.get("name") or "Dear Guest"
            if phone:
                recipients.append({"phone": phone, "name": name})

        # Build dummy req for invitation send
        couple = f"{profile.get('groom_name','')} & {profile.get('bride_name','')}"
        date = profile.get("event_date", "")
        if isinstance(date, str):
            try:
                date = datetime.fromisoformat(date).strftime("%d %B %Y")
            except Exception:
                pass
        rem_text = {
            "7_days": f"7 days to go! {couple} can't wait to celebrate with you on {date}.",
            "3_days": f"Just 3 days left for {couple}'s big day on {date}!",
            "1_day": f"Tomorrow is the day — see you at {couple}'s wedding!",
            "custom": req.custom_message or "Looking forward to seeing you.",
        }[req.reminder_type]

        client = _twilio_client()
        from_num = _twilio_from()
        results = []
        for rec in recipients:
            phone = rec["phone"].strip()
            if not phone.startswith("+"):
                phone = "+91" + phone.lstrip("0")
            body = f"Dear {rec['name']},\n\n{rem_text}\n\n— MAJA Creations"
            if client:
                try:
                    msg = client.messages.create(from_=from_num,
                                                  to=f"whatsapp:{phone}", body=body)
                    results.append({"phone": phone, "name": rec["name"],
                                    "status": "sent", "sid": msg.sid})
                except Exception as e:
                    results.append({"phone": phone, "name": rec["name"],
                                    "status": "failed", "error": str(e)[:120]})
            else:
                results.append({"phone": phone, "name": rec["name"],
                                "status": "mock"})

        await db.whatsapp_logs.insert_one({
            "id": uuid.uuid4().hex,
            "profile_id": profile["id"],
            "admin_id": admin_data["admin_id"],
            "kind": "reminder",
            "reminder_type": req.reminder_type,
            "count": len(results),
            "mode": "live" if client else "mock",
            "results": results,
            "created_at": _now_iso(),
        })
        return {"sent": len(results), "mode": "live" if client else "mock", "results": results}

    @router.get("/admin/profiles/{profile_id}/whatsapp/logs")
    async def whatsapp_logs(profile_id: str,
                             admin_data: dict = Depends(require_admin), limit: int = 50):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        cursor = db.whatsapp_logs.find({"profile_id": profile["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit)
        logs = await cursor.to_list(limit)
        return {"logs": logs}

    # ========================================================================
    # DIGITAL SHAGUN
    # ========================================================================
    @router.get("/admin/profiles/{profile_id}/shagun")
    async def get_shagun(profile_id: str,
                          admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        return profile.get("shagun_settings") or ShagunSettings().model_dump()

    @router.put("/admin/profiles/{profile_id}/shagun")
    async def set_shagun(profile_id: str, settings: ShagunSettings,
                          admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        await db.profiles.update_one({"id": profile["id"]},
            {"$set": {"shagun_settings": settings.model_dump(),
                      "updated_at": _now_iso()}})
        return {"success": True, "settings": settings.model_dump()}

    @router.get("/invite/{slug}/shagun")
    async def public_shagun(slug: str):
        profile = await _get_profile_by_id_or_slug(db, slug)
        s = profile.get("shagun_settings") or {}
        if not s.get("enabled", False) or not s.get("upi_id"):
            return {"enabled": False}
        couple = f"{profile.get('groom_name','')} & {profile.get('bride_name','')}"
        # Construct UPI deep links per Indian UPI spec
        def upi_link(amount: int):
            params = {
                "pa": s["upi_id"],
                "pn": s.get("payee_name") or couple,
                "am": str(amount),
                "cu": "INR",
                "tn": f"Shagun for {couple}",
            }
            return "upi://pay?" + urllib.parse.urlencode(params)
        suggested = [{"amount": a, "link": upi_link(a)} for a in s.get("suggested_amounts", [101, 501, 1001])]
        return {
            "enabled": True,
            "couple": couple,
            "payee_name": s.get("payee_name") or couple,
            "blessing_message": s.get("blessing_message"),
            "upi_id": s["upi_id"],
            "gpay_handle": s.get("gpay_handle"),
            "phonepe_handle": s.get("phonepe_handle"),
            "paytm_handle": s.get("paytm_handle"),
            "suggested": suggested,
            "razorpay_enabled": bool(s.get("razorpay_enabled") and s.get("razorpay_key_id") and s.get("razorpay_key_secret")),
            "platform_fee_percent": float(s.get("platform_fee_percent", 5.0)),
        }

    @router.post("/invite/{slug}/shagun/record")
    async def record_shagun(slug: str, payload: Dict[str, Any]):
        """Record a blessing/shagun event for the blessing-counter."""
        profile = await _get_profile_by_id_or_slug(db, slug)
        amount = int(payload.get("amount", 0) or 0)
        guest = (payload.get("guest_name") or "An anonymous well-wisher")[:80]
        message = (payload.get("message") or "")[:240]
        doc = {
            "id": uuid.uuid4().hex,
            "profile_id": profile["id"],
            "guest_name": guest,
            "amount": amount,
            "message": message,
            "created_at": _now_iso(),
        }
        await db.shagun_records.insert_one(doc)
        _serialize_doc(doc)
        return doc

    @router.get("/invite/{slug}/blessings")
    async def get_blessings(slug: str, limit: int = 30):
        """Returns blessing counter + recent wall-of-love."""
        profile = await _get_profile_by_id_or_slug(db, slug)
        cursor = db.shagun_records.find({"profile_id": profile["id"]},
                                          {"_id": 0}).sort("created_at", -1).limit(limit)
        recent = await cursor.to_list(limit)
        total_count = await db.shagun_records.count_documents({"profile_id": profile["id"]})
        agg = await db.shagun_records.aggregate([
            {"$match": {"profile_id": profile["id"]}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]).to_list(1)
        total_amount = (agg[0]["total"] if agg else 0)
        # Wall of love also pulls from guest wishes
        wishes_count = await db.guest_wishes.count_documents({
            "profile_id": profile["id"], "is_approved": True
        }) if "guest_wishes" in await db.list_collection_names() else 0
        return {
            "blessing_count": total_count,
            "blessing_total_amount": total_amount,
            "wishes_count": wishes_count,
            "recent_blessings": recent,
        }

    # ========================================================================
    # PROMPT 12 — Razorpay Shagun (per-photographer keys, 5% platform fee)
    # ========================================================================
    @router.post("/invite/{slug}/shagun/razorpay/order")
    async def create_razorpay_shagun_order(slug: str, payload: Dict[str, Any]):
        """Create a Razorpay order for a Shagun payment using the photographer's own keys."""
        import razorpay as _rzp
        profile = await _get_profile_by_id_or_slug(db, slug)
        s = profile.get("shagun_settings") or {}
        if not s.get("razorpay_enabled"):
            raise HTTPException(status_code=400, detail="Razorpay is not enabled for this wedding")
        key_id = s.get("razorpay_key_id") or os.environ.get("RAZORPAY_KEY_ID", "rzp_test_PLACEHOLDER")
        key_secret = s.get("razorpay_key_secret") or os.environ.get("RAZORPAY_KEY_SECRET", "PLACEHOLDER_SECRET")
        if not key_id or "PLACEHOLDER" in (key_secret or ""):
            raise HTTPException(status_code=400, detail="Photographer hasn't added Razorpay keys yet")
        amount = int(payload.get("amount", 0) or 0)
        if amount < 1:
            raise HTTPException(status_code=400, detail="Amount must be at least ₹1")
        try:
            client = _rzp.Client(auth=(key_id, key_secret))
            receipt = f"shagun_{uuid.uuid4().hex[:10]}"
            order = client.order.create({
                "amount": amount * 100,  # paise
                "currency": "INR",
                "receipt": receipt,
                "payment_capture": 1,
                "notes": {
                    "wedding_slug": slug,
                    "profile_id": profile["id"],
                    "guest_name": (payload.get("guest_name") or "")[:80],
                    "message": (payload.get("message") or "")[:200],
                },
            })
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Razorpay error: {str(e)[:200]}")
        return {
            "order_id": order["id"],
            "amount": amount,
            "currency": "INR",
            "key_id": key_id,
            "payee_name": s.get("payee_name") or f"{profile.get('groom_name','')} & {profile.get('bride_name','')}",
        }

    @router.post("/invite/{slug}/shagun/razorpay/verify")
    async def verify_razorpay_shagun(slug: str, payload: Dict[str, Any]):
        """Verify a Razorpay payment signature and record the Shagun with 5% platform fee."""
        import hmac, hashlib as _hashlib
        profile = await _get_profile_by_id_or_slug(db, slug)
        s = profile.get("shagun_settings") or {}
        key_secret = s.get("razorpay_key_secret") or os.environ.get("RAZORPAY_KEY_SECRET", "PLACEHOLDER_SECRET")
        order_id = payload.get("razorpay_order_id")
        payment_id = payload.get("razorpay_payment_id")
        signature = payload.get("razorpay_signature")
        if not (order_id and payment_id and signature):
            raise HTTPException(status_code=400, detail="Missing payment fields")
        # Server-side signature verification
        expected = hmac.new(
            (key_secret or "").encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            _hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=400, detail="Signature mismatch")
        amount = int(payload.get("amount", 0) or 0)
        platform_fee_pct = float(s.get("platform_fee_percent", 5.0))
        platform_fee = round(amount * platform_fee_pct / 100.0, 2)
        photographer_amount = round(amount - platform_fee, 2)
        doc = {
            "id": uuid.uuid4().hex,
            "profile_id": profile["id"],
            "guest_name": (payload.get("guest_name") or "An anonymous well-wisher")[:80],
            "amount": amount,
            "message": (payload.get("message") or "")[:240],
            "method": "razorpay",
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "platform_fee_percent": platform_fee_pct,
            "platform_fee": platform_fee,
            "photographer_amount": photographer_amount,
            "status": "paid",
            "created_at": _now_iso(),
        }
        await db.shagun_records.insert_one(doc)
        _serialize_doc(doc)
        return {"success": True, "record": doc}

    @router.get("/admin/profiles/{profile_id}/shagun/dashboard")
    async def shagun_dashboard(profile_id: str, admin_data: dict = Depends(require_admin)):
        """Photographer's Shagun earnings dashboard (totals + per-Shagun breakdown)."""
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        cursor = db.shagun_records.find({"profile_id": profile["id"]}, {"_id": 0}).sort("created_at", -1).limit(200)
        records = await cursor.to_list(200)
        total_received = sum(int(r.get("amount", 0) or 0) for r in records)
        platform_fees = sum(float(r.get("platform_fee", 0) or 0) for r in records)
        photographer_earnings = sum(float(r.get("photographer_amount", r.get("amount", 0)) or 0) for r in records)
        paid_count = sum(1 for r in records if r.get("status") == "paid")
        return {
            "total_received": total_received,
            "platform_fees": platform_fees,
            "photographer_earnings": photographer_earnings,
            "paid_count": paid_count,
            "total_count": len(records),
            "records": records,
        }

    # ========================================================================
    # TRAVEL & NAVIGATION
    # ========================================================================
    @router.get("/invite/{slug}/travel")
    async def travel_links(slug: str,
                            lat: Optional[float] = None,
                            lng: Optional[float] = None):
        profile = await _get_profile_by_id_or_slug(db, slug)
        venue = profile.get("venue") or "Wedding Venue"
        ms = profile.get("map_settings") or {}
        dest_lat = lat or ms.get("latitude")
        dest_lng = lng or ms.get("longitude")
        venue_q = urllib.parse.quote(venue)
        google_maps = (
            f"https://www.google.com/maps/search/?api=1&query={dest_lat},{dest_lng}"
            if dest_lat and dest_lng
            else f"https://www.google.com/maps/search/?api=1&query={venue_q}"
        )
        ola = (f"https://book.olacabs.com/?lat={dest_lat}&lng={dest_lng}&drop_name={venue_q}"
               if dest_lat and dest_lng
               else f"https://book.olacabs.com/?drop_name={venue_q}")
        uber = (f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[latitude]={dest_lat}&dropoff[longitude]={dest_lng}&dropoff[nickname]={venue_q}"
                if dest_lat and dest_lng
                else f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[nickname]={venue_q}")
        rapido = f"https://rapido.bike/Booknow?dropLat={dest_lat}&dropLng={dest_lng}" if dest_lat and dest_lng else "https://rapido.bike"
        return {
            "venue": venue,
            "destination": {"lat": dest_lat, "lng": dest_lng} if dest_lat and dest_lng else None,
            "links": {
                "google_maps": google_maps,
                "ola": ola,
                "uber": uber,
                "rapido": rapido,
            },
            "hotels_nearby_query": f"https://www.google.com/maps/search/hotels+near+{venue_q}",
        }

    # ========================================================================
    # PERSONALIZED ITINERARY
    # ========================================================================
    @router.get("/invite/{slug}/itinerary")
    async def itinerary(slug: str,
                         audience: Literal["all", "family", "close", "general"] = "general"):
        profile = await _get_profile_by_id_or_slug(db, slug)
        events = profile.get("events") or []
        # Filter by audience: events have optional `audience` field
        filtered = []
        for e in events:
            ev_aud = (e.get("audience") or "all").lower()
            # If the event's audience is "all", everyone sees it.
            # If it's "family", only family/close see it.
            # If it's "close", only close+family.
            audience_rank = {"general": 1, "close": 2, "family": 3, "all": 4}
            user_rank = audience_rank.get(audience, 1)
            event_rank = audience_rank.get(ev_aud, 4)
            if user_rank >= event_rank or ev_aud == "all":
                filtered.append(e)
        return {"audience": audience, "events": filtered, "total": len(filtered)}

    # ========================================================================
    # SMART RSVP — extended export
    # ========================================================================
    @router.get("/admin/profiles/{profile_id}/rsvps/export-smart")
    async def export_rsvps_smart(profile_id: str,
                                  fmt: Literal["csv", "xlsx", "json"] = "csv",
                                  admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)
        rsvps = await db.rsvps.find({"profile_id": profile["id"]}, {"_id": 0}).to_list(5000)

        if fmt == "json":
            return JSONResponse(content={"rsvps": rsvps})

        if fmt == "csv":
            buf = io.StringIO()
            cols = ["guest_name", "guest_phone", "guest_email", "attending",
                    "attendee_count", "meal_preference", "dietary_restrictions",
                    "transport_needed", "accommodation_needed",
                    "event_rsvps", "message", "created_at"]
            writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            for r in rsvps:
                # Inflate nested fields to text
                row = dict(r)
                if isinstance(row.get("event_rsvps"), list):
                    row["event_rsvps"] = "; ".join([
                        f"{e.get('event_type','event')}={'yes' if e.get('attending') else 'no'}"
                        for e in row["event_rsvps"]
                    ])
                if isinstance(row.get("dietary_restrictions"), list):
                    row["dietary_restrictions"] = ", ".join(row["dietary_restrictions"])
                writer.writerow({k: row.get(k, "") for k in cols})
            return StreamingResponse(io.BytesIO(buf.getvalue().encode("utf-8")),
                                      media_type="text/csv",
                                      headers={"Content-Disposition":
                                               f"attachment; filename=rsvps-{profile['slug']}.csv"})

        if fmt == "xlsx":
            try:
                import openpyxl  # noqa
            except Exception:
                # fallback: send CSV with xlsx-like name
                return await export_rsvps_smart.__wrapped__(profile_id=profile_id, fmt="csv",
                                                            admin_data=admin_data)
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "RSVPs"
            cols = ["guest_name", "guest_phone", "guest_email", "attending",
                    "attendee_count", "meal_preference", "dietary_restrictions",
                    "transport_needed", "accommodation_needed",
                    "event_rsvps", "message", "created_at"]
            ws.append(cols)
            for r in rsvps:
                row = []
                for c in cols:
                    v = r.get(c, "")
                    if isinstance(v, list):
                        if c == "event_rsvps":
                            v = "; ".join([f"{e.get('event_type','event')}={'yes' if e.get('attending') else 'no'}" for e in v])
                        else:
                            v = ", ".join([str(x) for x in v])
                    row.append(v)
                ws.append(row)
            buf = io.BytesIO()
            wb.save(buf)
            buf.seek(0)
            return StreamingResponse(buf,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=rsvps-{profile['slug']}.xlsx"})

    @router.post("/invite/{slug}/rsvp-smart")
    async def submit_smart_rsvp(slug: str, payload: Dict[str, Any]):
        """Extended RSVP that supports new fields."""
        profile = await _get_profile_by_id_or_slug(db, slug)
        if not profile.get("is_active", True):
            raise HTTPException(status_code=410, detail="Invitation no longer active")
        doc = {
            "id": uuid.uuid4().hex,
            "profile_id": profile["id"],
            "guest_name": payload.get("guest_name", "")[:80],
            "guest_phone": payload.get("guest_phone", "")[:20],
            "guest_email": payload.get("guest_email", "")[:120],
            "attending": payload.get("attending"),
            "attendee_count": int(payload.get("attendee_count", 1) or 1),
            "meal_preference": payload.get("meal_preference"),   # veg / non-veg / jain / vegan
            "dietary_restrictions": payload.get("dietary_restrictions") or [],
            "transport_needed": bool(payload.get("transport_needed", False)),
            "accommodation_needed": bool(payload.get("accommodation_needed", False)),
            "event_rsvps": payload.get("event_rsvps") or [],
            "message": (payload.get("message") or "")[:500],
            "smart": True,
            "created_at": _now_iso(),
        }
        await db.rsvps.insert_one(doc)
        _serialize_doc(doc)
        return doc

    # ========================================================================
    # ANALYTICS — light extras (heatmap-friendly aggregates)
    # ========================================================================
    @router.get("/admin/profiles/{profile_id}/analytics/v2")
    async def analytics_v2(profile_id: str,
                            admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_by_id_or_slug(db, profile_id)
        _verify_admin_owns(profile, admin_data)

        sessions = await db.view_sessions.find({"profile_id": profile["id"]}, {"_id": 0}).to_list(10000) \
            if "view_sessions" in await db.list_collection_names() else []
        by_city = {}
        by_device = {}
        by_lang = {}
        by_hour = [0]*24
        for s in sessions:
            by_city[s.get("city") or "Unknown"] = by_city.get(s.get("city") or "Unknown", 0) + 1
            by_device[s.get("device_type") or "Unknown"] = by_device.get(s.get("device_type") or "Unknown", 0) + 1
            by_lang[s.get("language") or "en"] = by_lang.get(s.get("language") or "en", 0) + 1
            try:
                hour = datetime.fromisoformat(s.get("created_at")).hour
                by_hour[hour] += 1
            except Exception:
                pass

        rsvp_total = await db.rsvps.count_documents({"profile_id": profile["id"]})
        rsvp_yes = await db.rsvps.count_documents({"profile_id": profile["id"], "attending": True})
        rsvp_no = await db.rsvps.count_documents({"profile_id": profile["id"], "attending": False})
        photos = await db.live_photos.count_documents({"profile_id": profile["id"]})
        favorites = 0
        agg = await db.live_photos.aggregate([
            {"$match": {"profile_id": profile["id"]}},
            {"$group": {"_id": None, "favs": {"$sum": "$favorite_count"}}}
        ]).to_list(1)
        if agg:
            favorites = agg[0]["favs"]

        return {
            "by_city": [{"name": k, "value": v} for k, v in sorted(by_city.items(), key=lambda x: -x[1])[:15]],
            "by_device": [{"name": k, "value": v} for k, v in by_device.items()],
            "by_language": [{"name": k, "value": v} for k, v in by_lang.items()],
            "hourly_heatmap": [{"hour": i, "value": v} for i, v in enumerate(by_hour)],
            "rsvp_funnel": {
                "total_views": len(sessions),
                "rsvp_started": rsvp_total + rsvp_yes + rsvp_no,
                "rsvp_yes": rsvp_yes,
                "rsvp_no": rsvp_no,
                "rsvp_pending": max(0, rsvp_total - rsvp_yes - rsvp_no),
            },
            "engagement": {
                "live_photos": photos,
                "photo_favorites": favorites,
            },
            "generated_at": _now_iso(),
        }

    # ========================================================================
    # PUBLIC REFERRAL — slug-based (for public invitation viral CTA)
    # ========================================================================
    @router.get("/public/referral-code-by-slug/{slug}")
    async def referral_code_by_slug(slug: str):
        profile = await _get_profile_by_id_or_slug(db, slug)
        # Find or create referral code
        existing = await db.referrals.find_one({"referrer_profile_id": profile["id"]}, {"_id": 0})
        if existing and existing.get("referral_code"):
            return {"referral_code": existing["referral_code"], "profile_id": profile["id"]}
        # Lazy-create
        import random
        import string
        code = (profile["id"][:5] + ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))).upper()
        await db.referrals.insert_one({
            "referral_id": "ref_" + uuid.uuid4().hex[:16],
            "referrer_profile_id": profile["id"],
            "referrer_admin_id": profile.get("admin_id", "unknown"),
            "referred_profile_id": None,
            "referral_code": code,
            "status": "pending",
            "reward_credits": 0,
            "created_at": _now_iso(),
        })
        return {"referral_code": code, "profile_id": profile["id"]}

    return router
