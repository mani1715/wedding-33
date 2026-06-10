"""
PROMPT 05 + 13 — Live Photo Gallery (WebSocket-powered) + Guest Photo Upload

Real-time photo gallery for the public invitation page:
- Photographer uploads from /admin/profile/{id}/live-gallery
- Guests upload from the floating "Share your photo" button on the invitation page
- All clients connected to /ws/gallery/{wedding_id} get instant push updates
- Photos stored on disk under /app/uploads/weddings/{wedding_id}/{folder}/
- Pillow generates 800px WebP "thumb" + 200px WebP "micro" preview
"""
from __future__ import annotations

import io
import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Set, List, Optional, Any

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, Request,
    WebSocket, WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel

from PIL import Image as PILImage  # already in requirements


logger = logging.getLogger(__name__)

UPLOAD_ROOT = Path("/app/uploads/weddings")
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic", "image/heif"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB safety cap per photo


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------
# WebSocket connection manager
# ----------------------------------------------------------------------------
class GalleryConnectionManager:
    """Keeps track of active websocket subscribers per wedding_id."""

    def __init__(self) -> None:
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, wedding_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(wedding_id, set()).add(ws)
        logger.info("[gallery-ws] connect wedding=%s total=%d", wedding_id, len(self._connections.get(wedding_id, [])))

    async def disconnect(self, wedding_id: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(wedding_id)
            if conns and ws in conns:
                conns.discard(ws)
                if not conns:
                    self._connections.pop(wedding_id, None)
        logger.info("[gallery-ws] disconnect wedding=%s", wedding_id)

    async def broadcast(self, wedding_id: str, payload: dict) -> None:
        async with self._lock:
            conns = list(self._connections.get(wedding_id, []))
        if not conns:
            return
        dead: List[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                live = self._connections.get(wedding_id, set())
                for d in dead:
                    live.discard(d)


manager = GalleryConnectionManager()


# ----------------------------------------------------------------------------
# Image processing
# ----------------------------------------------------------------------------
def _save_image_with_thumbs(raw: bytes, dest_dir: Path, base_name: str) -> dict:
    """Saves original + 800px thumb + 200px micro thumb. Returns metadata."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"  # we always save originals as jpg-compatible for browser support

    img = PILImage.open(io.BytesIO(raw))
    # Strip EXIF orientation
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    width, height = img.size

    # Save original (re-encode as high-quality JPEG)
    orig_path = dest_dir / f"{base_name}{ext}"
    rgb_img = img.convert("RGB")
    rgb_img.save(orig_path, format="JPEG", quality=88, optimize=True)

    # 800px WebP thumb (preserve aspect ratio)
    thumb_img = rgb_img.copy()
    thumb_img.thumbnail((800, 800), PILImage.LANCZOS)
    thumb_path = dest_dir / f"thumb_{base_name}.webp"
    thumb_img.save(thumb_path, format="WEBP", quality=82, method=6)

    # 200px micro thumb
    micro_img = rgb_img.copy()
    micro_img.thumbnail((200, 200), PILImage.LANCZOS)
    micro_path = dest_dir / f"micro_{base_name}.webp"
    micro_img.save(micro_path, format="WEBP", quality=70, method=6)

    return {
        "width": width,
        "height": height,
        "file_size": len(raw),
        "orig_filename": orig_path.name,
        "thumb_filename": thumb_path.name,
        "micro_filename": micro_path.name,
    }


def _build_urls(wedding_id: str, folder: str, meta: dict) -> dict:
    base = f"/api/uploads/weddings/{wedding_id}/{folder}"
    return {
        "url": f"{base}/{meta['orig_filename']}",
        "thumb_url": f"{base}/{meta['thumb_filename']}",
        "micro_url": f"{base}/{meta['micro_filename']}",
    }


# ----------------------------------------------------------------------------
# Router builder
# ----------------------------------------------------------------------------
def build_live_gallery_router(db, require_admin) -> APIRouter:
    router = APIRouter(tags=["live-gallery"])

    # ---- Helpers -----------------------------------------------------------
    async def _get_profile_owned(profile_id: str, admin_data: dict) -> dict:
        p = await db.profiles.find_one({"$or": [{"id": profile_id}, {"slug": profile_id}]}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Profile not found")
        admin_id = admin_data.get("admin_id") or admin_data.get("id")
        if admin_data.get("role") not in ("super_admin", "superadmin") and p.get("admin_id") and p.get("admin_id") != admin_id:
            raise HTTPException(403, "Not your wedding")
        return p

    async def _get_profile_by_slug(slug: str) -> dict:
        p = await db.profiles.find_one({"$or": [{"id": slug}, {"slug": slug}]}, {"_id": 0})
        if not p:
            raise HTTPException(404, "Wedding not found")
        return p

    def _strip(d: dict) -> dict:
        d.pop("_id", None)
        return d

    # ---- WebSocket endpoint ------------------------------------------------
    @router.websocket("/api/ws/gallery/{wedding_id}")
    async def gallery_ws(websocket: WebSocket, wedding_id: str):
        # Resolve slug → real profile_id
        profile = await db.profiles.find_one({"$or": [{"id": wedding_id}, {"slug": wedding_id}]}, {"_id": 0})
        resolved_id = profile["id"] if profile else wedding_id
        await manager.connect(resolved_id, websocket)
        try:
            # Send initial "connected" ping
            await websocket.send_json({"type": "connected", "wedding_id": resolved_id})
            while True:
                # We don't expect inbound messages, but keep the socket alive
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send heartbeat
                    try:
                        await websocket.send_json({"type": "ping", "ts": _now_iso()})
                    except Exception:
                        break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.warning("[gallery-ws] error: %s", e)
        finally:
            await manager.disconnect(resolved_id, websocket)

    # ---- ADMIN: photographer upload ---------------------------------------
    @router.post("/api/admin/profiles/{profile_id}/live-gallery/upload")
    async def photographer_upload(
        profile_id: str,
        files: List[UploadFile] = File(...),
        admin_data: dict = Depends(require_admin),
    ):
        profile = await _get_profile_owned(profile_id, admin_data)
        wedding_id = profile["id"]
        folder = "gallery"
        dest_dir = UPLOAD_ROOT / wedding_id / folder

        results = []
        for upload in files:
            try:
                raw = await upload.read()
                if not raw:
                    continue
                if len(raw) > MAX_FILE_SIZE:
                    continue
                base = uuid.uuid4().hex
                meta = _save_image_with_thumbs(raw, dest_dir, base)
                urls = _build_urls(wedding_id, folder, meta)
                doc = {
                    "id": uuid.uuid4().hex,
                    "profile_id": wedding_id,
                    "wedding_id": wedding_id,
                    "source": "photographer",
                    "guest_name": None,
                    "caption": None,
                    "width": meta["width"],
                    "height": meta["height"],
                    "file_size": meta["file_size"],
                    "created_at": _now_iso(),
                    **urls,
                }
                await db.live_gallery_photos.insert_one(doc)
                _strip(doc)
                results.append(doc)
                await manager.broadcast(wedding_id, {"type": "photo_added", "photo": doc})
            except Exception as e:
                logger.exception("[gallery] upload failed: %s", e)
                continue

        return {"uploaded": len(results), "photos": results}

    # ---- PUBLIC: guest upload (auto-publish) ------------------------------
    @router.post("/api/invite/{slug}/gallery/guest-upload")
    async def guest_upload(
        slug: str,
        file: UploadFile = File(...),
        guest_name: str = Form(...),
        caption: Optional[str] = Form(None),
    ):
        profile = await _get_profile_by_slug(slug)
        wedding_id = profile["id"]

        guest_name = (guest_name or "Guest").strip()[:60]
        caption_clean = (caption or "").strip()[:200] if caption else None

        raw = await file.read()
        if not raw:
            raise HTTPException(400, "Empty file")
        if len(raw) > MAX_FILE_SIZE:
            raise HTTPException(413, "File too large")

        folder = "guest_uploads"
        dest_dir = UPLOAD_ROOT / wedding_id / folder
        base = uuid.uuid4().hex
        try:
            meta = _save_image_with_thumbs(raw, dest_dir, base)
        except Exception as e:
            logger.exception("[gallery] guest upload failed: %s", e)
            raise HTTPException(400, "Could not process image")

        urls = _build_urls(wedding_id, folder, meta)
        doc = {
            "id": uuid.uuid4().hex,
            "profile_id": wedding_id,
            "wedding_id": wedding_id,
            "source": "guest",
            "guest_name": guest_name,
            "caption": caption_clean,
            "width": meta["width"],
            "height": meta["height"],
            "file_size": meta["file_size"],
            "created_at": _now_iso(),
            **urls,
        }
        await db.live_gallery_photos.insert_one(doc)
        _strip(doc)
        await manager.broadcast(wedding_id, {"type": "photo_added", "photo": doc})
        return {"success": True, "photo": doc}

    # ---- PUBLIC: list photos ----------------------------------------------
    @router.get("/api/public/gallery/{slug}/photos")
    async def list_photos(slug: str, limit: int = 200, since: Optional[str] = None):
        profile = await _get_profile_by_slug(slug)
        wedding_id = profile["id"]
        query: dict = {"wedding_id": wedding_id}
        if since:
            query["created_at"] = {"$gt": since}
        cursor = db.live_gallery_photos.find(query, {"_id": 0}).sort("created_at", -1).limit(min(limit, 500))
        photos = await cursor.to_list(limit)
        # Total count + storage
        total = await db.live_gallery_photos.count_documents({"wedding_id": wedding_id})
        return {"photos": photos, "total": total}

    # ---- ADMIN: list photos for management page ---------------------------
    @router.get("/api/admin/profiles/{profile_id}/live-gallery/photos")
    async def admin_list_photos(profile_id: str, admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_owned(profile_id, admin_data)
        wedding_id = profile["id"]
        cursor = db.live_gallery_photos.find({"wedding_id": wedding_id}, {"_id": 0}).sort("created_at", -1).limit(1000)
        photos = await cursor.to_list(1000)
        total_bytes = sum((p.get("file_size") or 0) for p in photos)
        return {
            "photos": photos,
            "total": len(photos),
            "storage_bytes": total_bytes,
            "photographer_count": sum(1 for p in photos if p.get("source") == "photographer"),
            "guest_count": sum(1 for p in photos if p.get("source") == "guest"),
        }

    # ---- ADMIN: delete a photo --------------------------------------------
    @router.delete("/api/admin/profiles/{profile_id}/live-gallery/{photo_id}")
    async def delete_photo(profile_id: str, photo_id: str, admin_data: dict = Depends(require_admin)):
        profile = await _get_profile_owned(profile_id, admin_data)
        wedding_id = profile["id"]
        photo = await db.live_gallery_photos.find_one({"id": photo_id, "wedding_id": wedding_id}, {"_id": 0})
        if not photo:
            raise HTTPException(404, "Photo not found")
        # Remove files
        for url_key in ("url", "thumb_url", "micro_url"):
            try:
                rel = (photo.get(url_key) or "").split("/api/uploads/", 1)[-1]
                full = Path("/app/uploads") / rel
                if full.exists():
                    full.unlink()
            except Exception:
                pass
        await db.live_gallery_photos.delete_one({"id": photo_id})
        await manager.broadcast(wedding_id, {"type": "photo_deleted", "photo_id": photo_id})
        return {"success": True}

    # ---- PUBLIC: file serving (StaticFiles equivalent) --------------------
    @router.get("/api/uploads/weddings/{wedding_id}/{folder}/{filename}")
    async def serve_upload(wedding_id: str, folder: str, filename: str):
        if folder not in ("gallery", "guest_uploads"):
            raise HTTPException(404, "Not found")
        # Prevent path traversal
        if "/" in filename or ".." in filename:
            raise HTTPException(400, "Invalid filename")
        path = UPLOAD_ROOT / wedding_id / folder / filename
        if not path.exists():
            raise HTTPException(404, "File not found")
        media_type = "image/webp" if filename.endswith(".webp") else "image/jpeg"
        return FileResponse(path, media_type=media_type)

    return router
