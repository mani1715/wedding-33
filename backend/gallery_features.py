"""
MAJA Creations — LIVE AI PHOTO GALLERY (Sprint 10)
==================================================
* Photographer enables gallery on a profile → creates Rekognition collection
* Photographer uploads photos via bulk OR phone-live mode (short token, no login)
* Each upload: validated → thumb → S3 (with expire-at tag) → Rekognition index
* Guests on /invite/{slug} click "Find My Photos", upload selfie → matches
* Selfies auto-deleted in 24h; entire wedding gallery deleted 1 day after link_expiry_date

Endpoints (mounted under /api):
  Admin (JWT):
    POST   /api/admin/profiles/{id}/gallery/enable
    PATCH  /api/admin/profiles/{id}/gallery/upload-methods
    POST   /api/admin/profiles/{id}/gallery/regenerate-token
    GET    /api/admin/profiles/{id}/gallery/credentials
    GET    /api/admin/profiles/{id}/gallery/photos
    POST   /api/admin/profiles/{id}/gallery/bulk-upload      (multipart)
    DELETE /api/admin/profiles/{id}/gallery/photos/{photo_id}
    GET    /api/admin/profiles/{id}/gallery/stats
    GET    /api/admin/gallery/aws/health

  Live photographer upload (token, no login):
    POST   /api/live-upload/{profile_id}                     (multipart, ?token=)
    GET    /api/live-upload/{profile_id}/status              (?token=)

  Public (no auth):
    POST   /api/public/gallery/{slug}/face-search            (multipart selfie)
    GET    /api/public/gallery/{slug}/photos                 (?session_id=)
    GET    /api/public/gallery/{slug}/download-zip           (?session_id=)
    GET    /api/public/gallery/{slug}/info                   (gallery enabled? count?)
"""
import os
import io
import re
import uuid
import secrets
import logging
import zipfile
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import jwt as _jwt
import zipstream
from fastapi import (APIRouter, HTTPException, Depends, UploadFile, File,
                      Query, Form, Request, Response)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aws_service import (s3, rekognition, bucket, upload_bytes, delete_prefix,
                          generate_signed_url, make_thumbnail, is_valid_image,
                          image_dimensions, create_face_collection,
                          delete_face_collection, index_photo_faces,
                          search_faces_by_selfie, is_configured, healthcheck)

logger = logging.getLogger("gallery")

# Pull JWT secret from same env var server.py uses
JWT_SECRET = os.environ.get("JWT_SECRET_KEY", "change-me")
LIVE_TOKEN_EXPIRY_HOURS = int(os.environ.get("LIVE_UPLOAD_TOKEN_EXPIRY_HOURS", "24"))
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB per file
ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/heic", "image/heif", "image/webp"}


# ============================================================
#  Pydantic models
# ============================================================
class UploadMethods(BaseModel):
    dslr_ftp_enabled: bool = False           # skipped this build (k8s port limit)
    phone_tether_enabled: bool = True
    wifi_sd_card_enabled: bool = False
    phone_live_enabled: bool = True
    bulk_upload_enabled: bool = True
    guest_contributions_enabled: bool = False


class GalleryConfigPublic(BaseModel):
    enabled: bool
    total_photos: int = 0
    face_search_enabled: bool = True
    expires_at: Optional[str] = None
    auto_delete_at: Optional[str] = None


class EnableGalleryPayload(BaseModel):
    enabled: bool = True
    upload_methods: Optional[UploadMethods] = None
    confidence_threshold: float = 90.0


class UpdateMethodsPayload(BaseModel):
    upload_methods: UploadMethods


# ============================================================
#  Helpers
# ============================================================
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _profile_collection_id(profile_id: str) -> str:
    # AWS Rekognition collection IDs: a-z A-Z 0-9 _ . - (no UUID dashes? dashes are ok)
    safe = re.sub(r"[^a-zA-Z0-9_.\-]", "_", profile_id)
    return f"maja_wedding_{safe}"


def _s3_prefix(profile_id: str) -> str:
    return f"weddings/{profile_id}/"


def _photo_keys(profile_id: str, photo_id: str) -> Dict[str, str]:
    pref = _s3_prefix(profile_id)
    return {
        "original": f"{pref}photos/{photo_id}/orig.jpg",
        "thumb":    f"{pref}photos/{photo_id}/thumb.jpg",
    }


def _selfie_key(profile_id: str, session_id: str) -> str:
    return f"{_s3_prefix(profile_id)}selfies/{session_id}.jpg"


async def _get_profile(db, profile_id_or_slug: str) -> Optional[dict]:
    return await db.profiles.find_one(
        {"$or": [{"id": profile_id_or_slug}, {"slug": profile_id_or_slug}]},
        {"_id": 0},
    )


def _compute_auto_delete_at(profile: dict) -> datetime:
    """1 DAY after profile.link_expiry_date (or event_date + 7 days)."""
    expiry = profile.get("link_expiry_date") or profile.get("expires_at")
    if expiry:
        if isinstance(expiry, str):
            try:
                expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
            except Exception:
                expiry = None
    if not expiry:
        ev = profile.get("event_date")
        if isinstance(ev, str):
            try:
                ev = datetime.fromisoformat(ev.replace("Z", "+00:00"))
            except Exception:
                ev = None
        expiry = (ev or _now()) + timedelta(days=7)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry + timedelta(days=1)


def _issue_live_token(profile_id: str) -> str:
    payload = {
        "sub": profile_id,
        "type": "live_upload",
        "iat": int(_now().timestamp()),
        "exp": int((_now() + timedelta(hours=LIVE_TOKEN_EXPIRY_HOURS)).timestamp()),
    }
    return _jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _verify_live_token(token: str, profile_id: str) -> bool:
    try:
        payload = _jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return (payload.get("sub") == profile_id
                and payload.get("type") == "live_upload")
    except Exception:
        return False


# ============================================================
#  Router builder
# ============================================================
def build_gallery_router(db, get_current_admin):
    router = APIRouter(prefix="/api", tags=["gallery"])

    # --------------------------------------------------------
    #  Admin — health + enable + methods
    # --------------------------------------------------------
    @router.get("/admin/gallery/aws/health")
    async def aws_health(admin_id: str = Depends(get_current_admin)):
        return healthcheck()

    @router.post("/admin/profiles/{profile_id}/gallery/enable")
    async def enable_gallery(profile_id: str, payload: EnableGalleryPayload,
                              admin_id: str = Depends(get_current_admin)):
        if not is_configured():
            raise HTTPException(status_code=503,
                detail="AWS not configured. Set AWS_* env vars and restart backend.")
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        collection_id = _profile_collection_id(profile["id"])
        if payload.enabled:
            create_face_collection(collection_id)

        gc = profile.get("gallery_config") or {}
        gc.update({
            "enabled": payload.enabled,
            "face_search_enabled": True,
            "confidence_threshold": payload.confidence_threshold or 90.0,
            "aws_collection_id": collection_id,
            "upload_methods": (payload.upload_methods.model_dump()
                                if payload.upload_methods else UploadMethods().model_dump()),
            "live_upload_token": _issue_live_token(profile["id"]),
            "live_upload_expires_at": (_now() + timedelta(hours=LIVE_TOKEN_EXPIRY_HOURS)).isoformat(),
            "auto_delete_at": _compute_auto_delete_at(profile).isoformat(),
            "total_photos": int(gc.get("total_photos") or 0),
            "updated_at": _now().isoformat(),
        })
        await db.profiles.update_one({"id": profile["id"]}, {"$set": {"gallery_config": gc}})
        return {"success": True, "gallery_config": _redact(gc)}

    @router.patch("/admin/profiles/{profile_id}/gallery/upload-methods")
    async def update_methods(profile_id: str, payload: UpdateMethodsPayload,
                              admin_id: str = Depends(get_current_admin)):
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        gc = profile.get("gallery_config") or {}
        gc["upload_methods"] = payload.upload_methods.model_dump()
        gc["updated_at"] = _now().isoformat()
        await db.profiles.update_one({"id": profile["id"]}, {"$set": {"gallery_config": gc}})
        return {"success": True, "upload_methods": gc["upload_methods"]}

    @router.post("/admin/profiles/{profile_id}/gallery/regenerate-token")
    async def regen_token(profile_id: str,
                           admin_id: str = Depends(get_current_admin)):
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        gc = profile.get("gallery_config") or {}
        token = _issue_live_token(profile["id"])
        gc["live_upload_token"] = token
        gc["live_upload_expires_at"] = (_now() + timedelta(hours=LIVE_TOKEN_EXPIRY_HOURS)).isoformat()
        await db.profiles.update_one({"id": profile["id"]}, {"$set": {"gallery_config": gc}})
        return {"success": True, "token": token,
                "expires_at": gc["live_upload_expires_at"]}

    @router.get("/admin/profiles/{profile_id}/gallery/credentials")
    async def get_credentials(profile_id: str, request: Request,
                               admin_id: str = Depends(get_current_admin)):
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        gc = profile.get("gallery_config") or {}
        if not gc.get("enabled"):
            raise HTTPException(status_code=400, detail="Gallery not enabled")
        # Build public live URL based on the frontend origin
        frontend = os.environ.get("FRONTEND_URL", "")
        token = gc.get("live_upload_token") or _issue_live_token(profile["id"])
        live_url = f"{frontend}/live/{profile['id']}?token={token}"
        # SD-card mode endpoint
        backend = os.environ.get("REACT_APP_BACKEND_URL", "")
        sd_url = f"{backend}/api/live-upload/{profile['id']}?token={token}"
        return {
            "live_upload_url": live_url,
            "sd_card_post_url": sd_url,
            "live_token": token,
            "live_token_expires_at": gc.get("live_upload_expires_at"),
            "upload_methods": gc.get("upload_methods") or UploadMethods().model_dump(),
            "auto_delete_at": gc.get("auto_delete_at"),
            "aws_collection_id": gc.get("aws_collection_id"),
        }

    @router.get("/admin/profiles/{profile_id}/gallery/stats")
    async def stats(profile_id: str,
                     admin_id: str = Depends(get_current_admin)):
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        gc = profile.get("gallery_config") or {}
        total = await db.gallery_photos.count_documents({"profile_id": profile["id"]})
        with_faces = await db.gallery_photos.count_documents({"profile_id": profile["id"], "face_count": {"$gt": 0}})
        by_method = {}
        async for d in db.gallery_photos.aggregate([
            {"$match": {"profile_id": profile["id"]}},
            {"$group": {"_id": "$upload_method", "n": {"$sum": 1}}},
        ]):
            by_method[d["_id"] or "unknown"] = d["n"]
        last = await db.gallery_photos.find_one(
            {"profile_id": profile["id"]}, sort=[("created_at", -1)], projection={"_id": 0})
        return {
            "enabled": bool(gc.get("enabled")),
            "total_photos": total,
            "photos_with_faces": with_faces,
            "by_method": by_method,
            "last_upload_at": last.get("created_at") if last else None,
            "auto_delete_at": gc.get("auto_delete_at"),
        }

    @router.get("/admin/profiles/{profile_id}/gallery/photos")
    async def list_photos(profile_id: str, limit: int = 200, offset: int = 0,
                           event_invitation_id: Optional[str] = Query(None),
                           admin_id: str = Depends(get_current_admin)):
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        query: Dict[str, Any] = {"profile_id": profile["id"]}
        if event_invitation_id:
            query["event_invitation_id"] = event_invitation_id
        cursor = db.gallery_photos.find(
            query, {"_id": 0}
        ).sort("created_at", -1).skip(offset).limit(min(limit, 500))
        out: List[dict] = []
        async for p in cursor:
            out.append({
                "id": p["id"],
                "upload_method": p.get("upload_method"),
                "event_invitation_id": p.get("event_invitation_id"),
                "face_count": p.get("face_count", 0),
                "width": p.get("width"),
                "height": p.get("height"),
                "file_size": p.get("file_size"),
                "created_at": p.get("created_at"),
                "thumb_url": generate_signed_url(p["thumb_s3_key"], 3600),
                "original_url": generate_signed_url(p["s3_key"], 3600),
            })
        return {"photos": out, "total": len(out)}

    @router.delete("/admin/profiles/{profile_id}/gallery/photos/{photo_id}")
    async def delete_photo(profile_id: str, photo_id: str,
                            admin_id: str = Depends(get_current_admin)):
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        p = await db.gallery_photos.find_one(
            {"profile_id": profile["id"], "id": photo_id}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="Photo not found")
        # Delete S3 objects
        try:
            s3().delete_objects(Bucket=bucket(), Delete={"Objects": [
                {"Key": p["s3_key"]}, {"Key": p["thumb_s3_key"]}]})
        except Exception as e:
            logger.warning("S3 delete failed: %s", e)
        # Delete faces from Rekognition collection
        face_ids = p.get("aws_face_ids") or []
        if face_ids:
            try:
                gc = profile.get("gallery_config") or {}
                if gc.get("aws_collection_id"):
                    rekognition().delete_faces(
                        CollectionId=gc["aws_collection_id"], FaceIds=face_ids)
            except Exception as e:
                logger.warning("Rekognition delete_faces failed: %s", e)
        await db.gallery_photos.delete_one({"id": photo_id})
        return {"success": True}

    @router.post("/admin/profiles/{profile_id}/gallery/bulk-upload")
    async def bulk_upload(profile_id: str, files: List[UploadFile] = File(...),
                           event_invitation_id: Optional[str] = Form(None),
                           admin_id: str = Depends(get_current_admin)):
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        gc = profile.get("gallery_config") or {}
        if not gc.get("enabled"):
            raise HTTPException(status_code=400, detail="Gallery not enabled")
        # If tagging by event, validate the event belongs to this profile
        if event_invitation_id:
            ei = await db.event_invitations.find_one(
                {"id": event_invitation_id, "profile_id": profile["id"]}, {"_id": 0, "id": 1})
            if not ei:
                raise HTTPException(status_code=404,
                    detail="Event invitation not found for this profile")
        results = []
        for f in files:
            res = await _ingest_photo(db, profile, gc, f, method="bulk",
                                       uploader="photographer",
                                       event_invitation_id=event_invitation_id)
            results.append(res)
        return {"success": True, "uploaded": sum(1 for r in results if r.get("ok")),
                "failed": sum(1 for r in results if not r.get("ok")),
                "results": results}

    # --------------------------------------------------------
    #  Live upload (token-gated, no login)
    # --------------------------------------------------------
    @router.post("/live-upload/{profile_id}")
    async def live_upload(profile_id: str, token: str = Query(...),
                           files: List[UploadFile] = File(...)):
        if not _verify_live_token(token, profile_id):
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        gc = profile.get("gallery_config") or {}
        if not gc.get("enabled"):
            raise HTTPException(status_code=400, detail="Gallery not enabled")
        results = []
        for f in files:
            r = await _ingest_photo(db, profile, gc, f, method="phone_live", uploader="photographer")
            results.append(r)
        return {"success": True,
                "uploaded": sum(1 for r in results if r.get("ok")),
                "failed": sum(1 for r in results if not r.get("ok")),
                "results": results}

    @router.get("/live-upload/{profile_id}/status")
    async def live_upload_status(profile_id: str, token: str = Query(...)):
        if not _verify_live_token(token, profile_id):
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        profile = await _get_profile(db, profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        total = await db.gallery_photos.count_documents({"profile_id": profile["id"]})
        last = await db.gallery_photos.find_one(
            {"profile_id": profile["id"]}, sort=[("created_at", -1)], projection={"_id": 0})
        recent = []
        cursor = db.gallery_photos.find(
            {"profile_id": profile["id"]}, {"_id": 0}
        ).sort("created_at", -1).limit(10)
        async for p in cursor:
            recent.append({
                "id": p["id"], "created_at": p.get("created_at"),
                "thumb_url": generate_signed_url(p["thumb_s3_key"], 3600),
            })
        return {
            "total_photos": total,
            "last_upload_at": last.get("created_at") if last else None,
            "recent": recent,
            "couple": f'{profile.get("bride_name", "")} & {profile.get("groom_name", "")}',
        }

    # --------------------------------------------------------
    #  Public — face search / photo grid / ZIP
    # --------------------------------------------------------
    @router.get("/public/gallery/{slug}/info")
    async def public_info(slug: str):
        profile = await _get_profile(db, slug)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        gc = profile.get("gallery_config") or {}
        return GalleryConfigPublic(
            enabled=bool(gc.get("enabled")),
            total_photos=int(gc.get("total_photos") or 0),
            face_search_enabled=bool(gc.get("face_search_enabled", True)),
            expires_at=(profile.get("link_expiry_date") or profile.get("expires_at")
                        and str(profile.get("link_expiry_date") or profile.get("expires_at"))),
            auto_delete_at=gc.get("auto_delete_at"),
        )

    @router.post("/public/gallery/{slug}/face-search")
    async def public_face_search(slug: str, request: Request,
                                   selfie: UploadFile = File(...)):
        profile = await _get_profile(db, slug)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        # Gallery privacy gate (no-op if not protected)
        try:
            from gallery_privacy import enforce_gallery_access
            await enforce_gallery_access(profile, request)
            privacy = profile.get("gallery_privacy") or {}
            if privacy.get("enabled") and not privacy.get("ai_face_match_enabled", True):
                raise HTTPException(status_code=403, detail="AI face match is disabled for this gallery")
        except HTTPException:
            raise
        gc = profile.get("gallery_config") or {}
        if not gc.get("enabled") or not gc.get("face_search_enabled", True):
            raise HTTPException(status_code=400, detail="Face search not available")
        data = await selfie.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Selfie too large (max 20 MB)")
        if not is_valid_image(data):
            raise HTTPException(status_code=400, detail="Invalid image")

        # Compress selfie to keep Rekognition payload small
        try:
            data_for_search = make_thumbnail(data, target_w=800, jpeg_quality=88)
        except Exception:
            data_for_search = data

        # Store selfie (auto-deleted in 24h)
        session_id = str(uuid.uuid4())
        selfie_key = _selfie_key(profile["id"], session_id)
        expire_at = (_now() + timedelta(hours=24)).strftime("%Y-%m-%d")
        try:
            upload_bytes(selfie_key, data_for_search, "image/jpeg",
                         tags={"expire-at": expire_at, "kind": "selfie",
                               "wedding": profile["id"]})
        except Exception as e:
            logger.warning("selfie upload failed: %s", e)
            # continue search anyway (in-memory bytes)

        # Search
        threshold = float(gc.get("confidence_threshold") or 90.0)
        result = search_faces_by_selfie(gc["aws_collection_id"], data_for_search,
                                         threshold=threshold, max_faces=200)
        if not result.get("ok"):
            raise HTTPException(status_code=422,
                detail=result.get("message") or "Face search failed")

        photo_ids = [m["photo_id"] for m in result["matches"]]
        # Persist session
        guest_ip = request.client.host if request.client else "unknown"
        session_doc = {
            "id": session_id,
            "profile_id": profile["id"],
            "guest_ip": guest_ip,
            "selfie_s3_key": selfie_key,
            "matched_photo_ids": photo_ids,
            "similarity_map": {m["photo_id"]: m["similarity"] for m in result["matches"]},
            "created_at": _now().isoformat(),
            "expires_at": (_now() + timedelta(hours=24)).isoformat(),
        }
        await db.face_search_sessions.insert_one(session_doc)

        # Bump privacy analytics (best-effort, no-op if not protected)
        try:
            await db.profiles.update_one(
                {"id": profile["id"]},
                {"$inc": {
                    "gallery_privacy.stats.ai_uploads": 1,
                    "gallery_privacy.stats.matched_results": len(photo_ids),
                }},
            )
        except Exception:
            pass

        # Build photo response with signed URLs
        photos = []
        if photo_ids:
            cursor = db.gallery_photos.find(
                {"profile_id": profile["id"], "id": {"$in": photo_ids}}, {"_id": 0})
            async for p in cursor:
                photos.append({
                    "id": p["id"],
                    "thumb_url": generate_signed_url(p["thumb_s3_key"], 3600),
                    "original_url": generate_signed_url(p["s3_key"], 3600),
                    "similarity": round(session_doc["similarity_map"].get(p["id"], 0.0), 1),
                    "created_at": p.get("created_at"),
                })
            photos.sort(key=lambda x: -x["similarity"])
        return {
            "session_id": session_id,
            "match_count": len(photos),
            "photos": photos,
        }

    @router.get("/public/gallery/{slug}/photos")
    async def public_photos_by_session(slug: str, session_id: str = Query(...),
                                         request: Request = None):
        profile = await _get_profile(db, slug)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        try:
            from gallery_privacy import enforce_gallery_access
            await enforce_gallery_access(profile, request)
        except HTTPException:
            raise
        session = await db.face_search_sessions.find_one(
            {"id": session_id, "profile_id": profile["id"]}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        photos = []
        ids = session.get("matched_photo_ids") or []
        if ids:
            cursor = db.gallery_photos.find(
                {"profile_id": profile["id"], "id": {"$in": ids}}, {"_id": 0})
            async for p in cursor:
                photos.append({
                    "id": p["id"],
                    "thumb_url": generate_signed_url(p["thumb_s3_key"], 3600),
                    "original_url": generate_signed_url(p["s3_key"], 3600),
                    "similarity": round((session.get("similarity_map") or {}).get(p["id"], 0.0), 1),
                })
        photos.sort(key=lambda x: -x.get("similarity", 0))
        return {"photos": photos, "session_id": session_id}

    @router.get("/public/gallery/{slug}/download-zip")
    async def public_zip(slug: str, session_id: str = Query(...), request: Request = None):
        profile = await _get_profile(db, slug)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        # Gallery privacy gate + downloads-allowed check
        try:
            from gallery_privacy import enforce_gallery_access
            await enforce_gallery_access(profile, request)
            privacy = profile.get("gallery_privacy") or {}
            if privacy.get("enabled") and not privacy.get("allow_downloads", True):
                raise HTTPException(status_code=403, detail="Downloads are disabled for this gallery")
        except HTTPException:
            raise
        session = await db.face_search_sessions.find_one(
            {"id": session_id, "profile_id": profile["id"]}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        ids = session.get("matched_photo_ids") or []
        if not ids:
            raise HTTPException(status_code=404, detail="No photos in session")
        photos = []
        async for p in db.gallery_photos.find(
            {"profile_id": profile["id"], "id": {"$in": ids}}, {"_id": 0}):
            photos.append(p)

        zs = zipstream.ZipStream(compress_type=zipfile.ZIP_STORED)
        for i, p in enumerate(photos):
            try:
                resp = s3().get_object(Bucket=bucket(), Key=p["s3_key"])
                body = resp["Body"].read()
                fname = f"photo_{i+1:03d}.jpg"
                zs.add(body, arcname=fname)
            except Exception as e:
                logger.warning("zip stream skipping %s: %s", p.get("id"), e)
        couple = f'{profile.get("bride_name", "")}-{profile.get("groom_name", "")}'.replace(" ", "")
        fname = f"{couple or 'wedding'}-photos.zip"

        def _iter():
            for chunk in zs:
                yield chunk

        return StreamingResponse(_iter(), media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'})

    return router


# ============================================================
#  Internal — ingest a single uploaded photo
# ============================================================
async def _ingest_photo(db, profile: dict, gc: dict, upload_file: UploadFile,
                         method: str, uploader: str,
                         event_invitation_id: Optional[str] = None) -> Dict[str, Any]:
    try:
        ct = (upload_file.content_type or "").lower()
        if ct not in ALLOWED_MIME and not any(ct.startswith(a) for a in ("image/",)):
            return {"ok": False, "filename": upload_file.filename, "error": "unsupported_type"}
        data = await upload_file.read()
        if not data:
            return {"ok": False, "filename": upload_file.filename, "error": "empty_file"}
        if len(data) > MAX_UPLOAD_BYTES:
            return {"ok": False, "filename": upload_file.filename,
                    "error": "too_large", "max_bytes": MAX_UPLOAD_BYTES}
        if not is_valid_image(data):
            return {"ok": False, "filename": upload_file.filename, "error": "invalid_image"}

        # Normalize to JPEG for storage + Rekognition (handles HEIC->JPEG via Pillow if pillow-heif installed)
        try:
            orig_jpeg = make_thumbnail(data, target_w=2000, jpeg_quality=92)
        except Exception:
            orig_jpeg = data
        try:
            thumb_jpeg = make_thumbnail(data, target_w=400, jpeg_quality=85)
        except Exception:
            thumb_jpeg = orig_jpeg

        photo_id = str(uuid.uuid4())
        keys = _photo_keys(profile["id"], photo_id)
        auto_del = gc.get("auto_delete_at") or _compute_auto_delete_at(profile).isoformat()
        expire_tag = auto_del[:10]  # YYYY-MM-DD
        tags = {"expire-at": expire_tag, "wedding": profile["id"], "method": method}

        upload_bytes(keys["original"], orig_jpeg, "image/jpeg", tags=tags)
        upload_bytes(keys["thumb"], thumb_jpeg, "image/jpeg", tags=tags)

        # Index faces
        index_res = index_photo_faces(gc["aws_collection_id"], keys["original"],
                                       external_image_id=photo_id, max_faces=15)
        dims = image_dimensions(orig_jpeg)

        doc = {
            "id": photo_id,
            "profile_id": profile["id"],
            "event_invitation_id": event_invitation_id,
            "s3_key": keys["original"],
            "thumb_s3_key": keys["thumb"],
            "upload_method": method,
            "uploaded_by": uploader,
            "file_size": len(orig_jpeg),
            "width": dims["width"],
            "height": dims["height"],
            "face_count": int(index_res.get("face_count") or 0),
            "aws_face_ids": index_res.get("face_ids") or [],
            "indexed": bool(index_res.get("ok")),
            "created_at": _now().isoformat(),
            "expires_at": auto_del,
        }
        await db.gallery_photos.insert_one(doc)
        # Bump counter
        await db.profiles.update_one(
            {"id": profile["id"]},
            {"$inc": {"gallery_config.total_photos": 1},
             "$set": {"gallery_config.last_upload_at": _now().isoformat()}}
        )
        return {"ok": True, "id": photo_id, "filename": upload_file.filename,
                "face_count": doc["face_count"],
                "thumb_url": generate_signed_url(keys["thumb"], 3600)}
    except Exception as e:
        logger.exception("ingest_photo failed")
        return {"ok": False, "filename": upload_file.filename, "error": str(e)[:200]}


def _redact(gc: dict) -> dict:
    """Hide raw token from API response (we keep it in DB)."""
    out = {**gc}
    if "live_upload_token" in out:
        tok = out["live_upload_token"] or ""
        out["live_upload_token_preview"] = (tok[:8] + "..." + tok[-4:]) if tok else None
        out.pop("live_upload_token", None)
    return out


# ============================================================
#  Cleanup scheduler (called from server.py startup)
# ============================================================
async def cleanup_expired_galleries(db):
    """Daily 3am job — deletes everything for weddings past auto_delete_at."""
    now_iso = _now().isoformat()
    cursor = db.profiles.find({
        "gallery_config.enabled": True,
        "gallery_config.auto_delete_at": {"$lt": now_iso},
    }, {"_id": 0, "id": 1, "gallery_config": 1, "slug": 1})
    deleted_weddings = 0
    async for p in cursor:
        try:
            gc = p.get("gallery_config") or {}
            # S3 prefix
            try:
                delete_prefix(_s3_prefix(p["id"]))
            except Exception as e:
                logger.warning("cleanup S3 delete failed %s: %s", p["id"], e)
            # Rekognition collection
            if gc.get("aws_collection_id"):
                try:
                    delete_face_collection(gc["aws_collection_id"])
                except Exception as e:
                    logger.warning("cleanup rek collection failed %s: %s", p["id"], e)
            # Mongo records
            await db.gallery_photos.delete_many({"profile_id": p["id"]})
            await db.face_search_sessions.delete_many({"profile_id": p["id"]})
            await db.profiles.update_one({"id": p["id"]},
                {"$set": {"gallery_config.enabled": False,
                          "gallery_config.cleaned_at": _now().isoformat(),
                          "gallery_config.total_photos": 0}})
            deleted_weddings += 1
        except Exception as e:
            logger.exception("gallery cleanup loop failed for %s: %s", p.get("id"), e)
    if deleted_weddings:
        logger.info("[cleanup] purged %d expired wedding galleries", deleted_weddings)
    return deleted_weddings


async def cleanup_expired_selfies(db):
    """Hourly job — purge selfies > 24h old."""
    cutoff = _now() - timedelta(hours=24)
    cutoff_iso = cutoff.isoformat()
    cursor = db.face_search_sessions.find(
        {"created_at": {"$lt": cutoff_iso}}, {"_id": 0, "selfie_s3_key": 1, "id": 1})
    purged = 0
    async for s in cursor:
        if s.get("selfie_s3_key"):
            try:
                s3().delete_object(Bucket=bucket(), Key=s["selfie_s3_key"])
            except Exception:
                pass
        purged += 1
    if purged:
        await db.face_search_sessions.delete_many({"created_at": {"$lt": cutoff_iso}})
        logger.info("[cleanup] purged %d expired selfies", purged)
    return purged
