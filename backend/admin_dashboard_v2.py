"""
admin_dashboard_v2.py — Bucket 1 extras for the Photographer/Studio dashboard.

Adds (all under /api/admin):
  • GET    /admin/profiles/paginated      — page / page_size / status / sort / q / tag
  • POST   /admin/profiles/bulk-action    — delete / archive / unarchive / publish / unpublish / restore
  • GET    /admin/profiles/trash          — list soft-deleted (deleted_at within 30d)
  • POST   /admin/profiles/{id}/restore-trash
  • DELETE /admin/profiles/{id}/purge     — hard delete from trash
  • PATCH  /admin/profiles/{id}/quick     — quick edit (couple names, date, status, tags)
  • PATCH  /admin/profiles/{id}/tags      — replace tags array
  • GET    /admin/profiles/{id}/quick-stats — views/RSVPs/wishes/gallery counters in 1 call
  • GET    /admin/profiles/export.csv     — CSV export of profiles + counters
  • GET    /admin/notifications           — recent activity (rsvps/wishes/payment alerts)
  • GET    /admin/notifications/unread-count

Soft-delete semantics:
  • DELETE /admin/profiles/{id} sets is_active=False (existing).
  • This module sets `deleted_at` on bulk-action delete + on PATCH quick action.
  • Items where deleted_at >= now()-30d show up in /trash, else they are hard-purged
    by the daily sweep (or by /admin/profiles/{id}/purge).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
import csv
import io


def build_admin_dashboard_v2_router(db, require_admin, log_audit_action):
    router = APIRouter(prefix="/api/admin", tags=["admin-dashboard-v2"])

    # ---------- helpers ----------
    def _is_super(admin_data):
        return admin_data.get("role") == "super_admin"

    async def _check_ownership(profile_id: str, admin_data: dict):
        profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        if not _is_super(admin_data) and profile.get("admin_id") != admin_data["admin_id"]:
            raise HTTPException(status_code=403, detail="Not authorized for this profile")
        return profile

    def _normalize_dt(p: dict):
        for k in ("event_date", "created_at", "updated_at", "link_expiry_date",
                  "expires_at", "deleted_at", "archived_at", "published_at",
                  "publish_at"):
            v = p.get(k)
            if v and isinstance(v, datetime):
                p[k] = v.isoformat()
        return p

    # ---------- listing ----------
    class PaginatedProfilesResponse(BaseModel):
        items: List[Dict[str, Any]]
        total: int
        page: int
        page_size: int
        total_pages: int

    @router.get("/profiles/paginated", response_model=PaginatedProfilesResponse)
    async def get_profiles_paginated(
        page: int = Query(1, ge=1),
        page_size: int = Query(12, ge=1, le=100),
        status: Optional[str] = Query(None,
            description="all|draft|published|expiring|archived|trash"),
        sort: str = Query("newest",
            description="newest|oldest|date_asc|date_desc|most_viewed|name_asc"),
        q: Optional[str] = Query(None,
            description="Search across bride, groom, slug, phone, email, tags, city"),
        tag: Optional[str] = Query(None, description="Single tag filter"),
        admin_data: dict = Depends(require_admin),
    ):
        query: Dict[str, Any] = {"is_template": {"$ne": True}}
        if not _is_super(admin_data):
            query["admin_id"] = admin_data["admin_id"]

        status_norm = (status or "all").lower()
        if status_norm == "trash":
            query["deleted_at"] = {"$exists": True, "$ne": None}
        else:
            # Non-trash: only show non-deleted
            query["$and"] = [{"$or": [{"deleted_at": None}, {"deleted_at": {"$exists": False}}]}]
            if status_norm == "draft":
                query["status"] = "DRAFT"
            elif status_norm == "published":
                query["status"] = "PUBLISHED"
            elif status_norm == "archived":
                query["archived_at"] = {"$exists": True, "$ne": None}
            elif status_norm == "expiring":
                soon = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                query["expires_at"] = {"$lte": soon, "$ne": None}
            # "all" → no extra filter

        if q:
            qre = {"$regex": q.strip(), "$options": "i"}
            query["$or"] = [
                {"bride_name": qre}, {"groom_name": qre}, {"slug": qre},
                {"city": qre}, {"venue": qre},
                {"contact_info.bride_phone": qre},
                {"contact_info.groom_phone": qre},
                {"contact_info.bride_email": qre},
                {"contact_info.groom_email": qre},
                {"tags": qre},
            ]

        if tag:
            query["tags"] = tag

        sort_map = {
            "newest":      [("created_at", -1)],
            "oldest":      [("created_at", 1)],
            "date_asc":    [("event_date", 1)],
            "date_desc":   [("event_date", -1)],
            "most_viewed": [("view_count", -1)],
            "name_asc":    [("bride_name", 1), ("groom_name", 1)],
        }
        sort_spec = sort_map.get(sort, sort_map["newest"])

        total = await db.profiles.count_documents(query)
        skip = (page - 1) * page_size
        cursor = (db.profiles.find(query, {"_id": 0})
                  .sort(sort_spec).skip(skip).limit(page_size))
        items = [_normalize_dt(p) async for p in cursor]
        return PaginatedProfilesResponse(
            items=items, total=total, page=page, page_size=page_size,
            total_pages=max(1, (total + page_size - 1) // page_size),
        )

    # ---------- bulk action ----------
    class BulkActionRequest(BaseModel):
        ids: List[str] = Field(..., min_length=1, max_length=200)
        action: str  # delete|archive|unarchive|publish|unpublish|restore|purge|tag

    class BulkActionResponse(BaseModel):
        matched: int
        modified: int
        action: str

    @router.post("/profiles/bulk-action", response_model=BulkActionResponse)
    async def bulk_action(req: BulkActionRequest, admin_data: dict = Depends(require_admin)):
        # Scope to ownership
        scope: Dict[str, Any] = {"id": {"$in": req.ids}}
        if not _is_super(admin_data):
            scope["admin_id"] = admin_data["admin_id"]

        now_iso = datetime.now(timezone.utc).isoformat()
        action = req.action.lower()

        if action == "delete":
            update = {"$set": {"deleted_at": now_iso, "is_active": False, "updated_at": now_iso}}
        elif action == "restore":
            update = {"$unset": {"deleted_at": ""}, "$set": {"is_active": True, "updated_at": now_iso}}
        elif action == "archive":
            update = {"$set": {"archived_at": now_iso, "updated_at": now_iso}}
        elif action == "unarchive":
            update = {"$unset": {"archived_at": ""}, "$set": {"updated_at": now_iso}}
        elif action == "publish":
            update = {"$set": {"status": "PUBLISHED", "is_published": True,
                               "published_at": now_iso, "updated_at": now_iso}}
        elif action == "unpublish":
            update = {"$set": {"status": "DRAFT", "is_published": False, "updated_at": now_iso}}
        elif action == "purge":
            # Hard delete — only if currently in trash
            scope_purge = dict(scope)
            scope_purge["deleted_at"] = {"$exists": True, "$ne": None}
            res = await db.profiles.delete_many(scope_purge)
            try:
                await log_audit_action(
                    action="profile_bulk_purge",
                    admin_id=admin_data["admin_id"],
                    profile_id=",".join(req.ids[:10]),
                    profile_slug="bulk",
                    details={"count": res.deleted_count, "ids": req.ids},
                )
            except Exception:
                pass
            return BulkActionResponse(matched=res.deleted_count, modified=res.deleted_count, action=action)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

        res = await db.profiles.update_many(scope, update)
        try:
            await log_audit_action(
                action=f"profile_bulk_{action}",
                admin_id=admin_data["admin_id"],
                profile_id=",".join(req.ids[:10]),
                profile_slug="bulk",
                details={"matched": res.matched_count, "modified": res.modified_count, "ids": req.ids},
            )
        except Exception:
            pass
        return BulkActionResponse(
            matched=res.matched_count, modified=res.modified_count, action=action
        )

    # ---------- trash ----------
    @router.get("/profiles/trash")
    async def list_trash(admin_data: dict = Depends(require_admin)):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        query: Dict[str, Any] = {
            "deleted_at": {"$gte": cutoff, "$ne": None, "$exists": True},
            "is_template": {"$ne": True},
        }
        if not _is_super(admin_data):
            query["admin_id"] = admin_data["admin_id"]
        raw = await db.profiles.find(query, {"_id": 0}).sort("deleted_at", -1).to_list(500)
        items = [_normalize_dt(p) for p in raw]
        return {"items": items, "total": len(items), "retention_days": 30}

    @router.post("/profiles/{profile_id}/restore-trash")
    async def restore_from_trash(profile_id: str, admin_data: dict = Depends(require_admin)):
        await _check_ownership(profile_id, admin_data)
        now_iso = datetime.now(timezone.utc).isoformat()
        res = await db.profiles.update_one(
            {"id": profile_id},
            {"$unset": {"deleted_at": ""}, "$set": {"is_active": True, "updated_at": now_iso}},
        )
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Profile not found")
        return {"message": "Profile restored", "profile_id": profile_id}

    @router.delete("/profiles/{profile_id}/purge")
    async def purge_profile(profile_id: str, admin_data: dict = Depends(require_admin)):
        await _check_ownership(profile_id, admin_data)
        res = await db.profiles.delete_one(
            {"id": profile_id, "deleted_at": {"$exists": True, "$ne": None}}
        )
        if res.deleted_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Profile must be in trash before it can be purged",
            )
        try:
            await log_audit_action(
                action="profile_purge",
                admin_id=admin_data["admin_id"],
                profile_id=profile_id,
                profile_slug="purged",
                details={"hard_deleted": True},
            )
        except Exception:
            pass
        return {"message": "Profile permanently deleted"}

    # ---------- quick edit ----------
    class QuickEditRequest(BaseModel):
        bride_name: Optional[str] = None
        groom_name: Optional[str] = None
        event_date: Optional[str] = None  # ISO
        status: Optional[str] = None      # DRAFT|PUBLISHED
        tags: Optional[List[str]] = None
        publish_at: Optional[str] = None  # ISO future
        notes: Optional[str] = None

    @router.patch("/profiles/{profile_id}/quick")
    async def quick_edit(
        profile_id: str, req: QuickEditRequest,
        admin_data: dict = Depends(require_admin),
    ):
        await _check_ownership(profile_id, admin_data)
        upd = {k: v for k, v in req.model_dump(exclude_none=True).items()}
        if not upd:
            raise HTTPException(status_code=400, detail="No fields to update")
        if "tags" in upd and len(upd["tags"]) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 tags allowed")
        upd["updated_at"] = datetime.now(timezone.utc).isoformat()
        if upd.get("status") == "PUBLISHED":
            upd["is_published"] = True
            upd.setdefault("published_at", upd["updated_at"])
        elif upd.get("status") == "DRAFT":
            upd["is_published"] = False
        await db.profiles.update_one({"id": profile_id}, {"$set": upd})
        try:
            await log_audit_action(
                action="profile_quick_edit",
                admin_id=admin_data["admin_id"],
                profile_id=profile_id,
                profile_slug=(await db.profiles.find_one({"id": profile_id}, {"slug": 1})).get("slug", ""),
                details=upd,
            )
        except Exception:
            pass
        return {"message": "Profile updated", "updated_fields": list(upd.keys())}

    # ---------- tags ----------
    class TagsRequest(BaseModel):
        tags: List[str] = Field(default_factory=list, max_length=20)

    @router.patch("/profiles/{profile_id}/tags")
    async def update_tags(
        profile_id: str, req: TagsRequest,
        admin_data: dict = Depends(require_admin),
    ):
        await _check_ownership(profile_id, admin_data)
        clean = sorted({t.strip() for t in req.tags if t and t.strip()})[:20]
        await db.profiles.update_one(
            {"id": profile_id},
            {"$set": {"tags": clean, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        return {"tags": clean}

    @router.get("/tags")
    async def list_all_tags(admin_data: dict = Depends(require_admin)):
        match: Dict[str, Any] = {"tags": {"$exists": True, "$ne": []}}
        if not _is_super(admin_data):
            match["admin_id"] = admin_data["admin_id"]
        pipeline = [
            {"$match": match},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": 100},
        ]
        items = [{"tag": r["_id"], "count": r["count"]}
                 async for r in db.profiles.aggregate(pipeline)]
        return {"items": items}

    # ---------- quick stats per card ----------
    @router.get("/profiles/{profile_id}/quick-stats")
    async def quick_stats(profile_id: str, admin_data: dict = Depends(require_admin)):
        await _check_ownership(profile_id, admin_data)
        profile = await db.profiles.find_one({"id": profile_id}, {"_id": 0, "view_count": 1, "unique_visitors": 1})
        rsvp_count = await db.rsvps.count_documents({"profile_id": profile_id})
        wish_count = await db.wishes.count_documents({"profile_id": profile_id}) \
            if "wishes" in await db.list_collection_names() else 0
        try:
            gallery_views = await db.gallery_events.count_documents({
                "profile_id": profile_id, "type": "view",
            })
        except Exception:
            gallery_views = 0
        # Credit consumption from ledger
        credit_spent = 0
        try:
            agg = db.credit_ledger.aggregate([
                {"$match": {"profile_id": profile_id, "type": "DEBIT"}},
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
            ])
            async for r in agg:
                credit_spent = abs(int(r.get("total", 0)))
        except Exception:
            pass
        return {
            "views": int((profile or {}).get("view_count", 0)),
            "unique_visitors": int((profile or {}).get("unique_visitors", 0)),
            "rsvps": rsvp_count,
            "wishes": wish_count,
            "gallery_views": gallery_views,
            "credits_spent": credit_spent,
        }

    # ---------- CSV export ----------
    @router.get("/profiles/export.csv")
    async def export_csv(
        status: Optional[str] = None,
        admin_data: dict = Depends(require_admin),
    ):
        query: Dict[str, Any] = {"is_template": {"$ne": True}}
        if not _is_super(admin_data):
            query["admin_id"] = admin_data["admin_id"]
        if status and status != "all":
            if status == "trash":
                query["deleted_at"] = {"$exists": True, "$ne": None}
            else:
                query["status"] = status.upper()

        cursor = db.profiles.find(query, {"_id": 0}).sort("created_at", -1)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "slug", "bride_name", "groom_name", "event_type", "event_date",
            "city", "venue", "status", "is_published", "view_count",
            "unique_visitors", "tags", "created_at", "updated_at",
        ])
        async for p in cursor:
            writer.writerow([
                p.get("id", ""), p.get("slug", ""),
                p.get("bride_name", ""), p.get("groom_name", ""),
                p.get("event_type", ""), str(p.get("event_date", "")),
                p.get("city", ""), p.get("venue", ""),
                p.get("status", ""), p.get("is_published", False),
                p.get("view_count", 0), p.get("unique_visitors", 0),
                ",".join(p.get("tags", []) or []),
                str(p.get("created_at", "")), str(p.get("updated_at", "")),
            ])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="weddings.csv"'},
        )

    # ---------- notifications ----------
    @router.get("/notifications")
    async def list_notifications(
        limit: int = Query(20, ge=1, le=100),
        admin_data: dict = Depends(require_admin),
    ):
        """Lightweight notification feed by aggregating recent activity:
           - New RSVPs in last 7 days
           - New wishes in last 7 days
           - Recent credit purchases / debits
           - Expiring invitations within 7 days
        """
        admin_id = admin_data["admin_id"]
        is_super = _is_super(admin_data)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # Owner's profiles set
        owner_q: Dict[str, Any] = {"is_template": {"$ne": True}}
        if not is_super:
            owner_q["admin_id"] = admin_id
        owner_profiles = list(await db.profiles.find(
            owner_q, {"_id": 0, "id": 1, "slug": 1, "bride_name": 1, "groom_name": 1,
                      "expires_at": 1, "admin_id": 1}
        ).to_list(1000))
        owner_ids = [p["id"] for p in owner_profiles]
        profile_by_id = {p["id"]: p for p in owner_profiles}

        feed: List[Dict[str, Any]] = []

        # RSVPs
        try:
            async for r in db.rsvps.find(
                {"profile_id": {"$in": owner_ids}, "created_at": {"$gte": cutoff}},
                {"_id": 0, "profile_id": 1, "guest_name": 1, "created_at": 1, "attendees": 1},
            ).sort("created_at", -1).limit(limit):
                pr = profile_by_id.get(r.get("profile_id"), {})
                feed.append({
                    "type": "rsvp",
                    "icon": "MessageCircle",
                    "title": f"{r.get('guest_name', 'Guest')} replied",
                    "subtitle": f"{pr.get('bride_name','')} & {pr.get('groom_name','')}",
                    "profile_id": r.get("profile_id"),
                    "at": r.get("created_at"),
                })
        except Exception:
            pass

        # Wishes
        try:
            if "wishes" in await db.list_collection_names():
                async for w in db.wishes.find(
                    {"profile_id": {"$in": owner_ids}, "created_at": {"$gte": cutoff}},
                    {"_id": 0, "profile_id": 1, "author_name": 1, "created_at": 1},
                ).sort("created_at", -1).limit(limit):
                    pr = profile_by_id.get(w.get("profile_id"), {})
                    feed.append({
                        "type": "wish",
                        "icon": "Heart",
                        "title": f"{w.get('author_name', 'Guest')} left a wish",
                        "subtitle": f"{pr.get('bride_name','')} & {pr.get('groom_name','')}",
                        "profile_id": w.get("profile_id"),
                        "at": w.get("created_at"),
                    })
        except Exception:
            pass

        # Expiring soon
        try:
            soon = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            for p in owner_profiles:
                exp = p.get("expires_at")
                if exp and isinstance(exp, str) and exp <= soon:
                    feed.append({
                        "type": "expiring",
                        "icon": "Clock",
                        "title": f"{p.get('bride_name','')} & {p.get('groom_name','')} expires soon",
                        "subtitle": f"Link expires {exp[:10]}",
                        "profile_id": p["id"],
                        "at": exp,
                    })
        except Exception:
            pass

        # Sort + slice
        feed.sort(key=lambda x: str(x.get("at") or ""), reverse=True)
        feed = feed[:limit]
        return {"items": feed, "total": len(feed)}

    @router.get("/notifications/unread-count")
    async def unread_count(admin_data: dict = Depends(require_admin)):
        # Simple heuristic: count items in last 24h
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        admin_id = admin_data["admin_id"]
        is_super = _is_super(admin_data)
        owner_q: Dict[str, Any] = {"is_template": {"$ne": True}}
        if not is_super:
            owner_q["admin_id"] = admin_id
        owner_ids = [p["id"] for p in await db.profiles.find(owner_q, {"_id": 0, "id": 1}).to_list(1000)]
        rsvp_c = await db.rsvps.count_documents({"profile_id": {"$in": owner_ids}, "created_at": {"$gte": cutoff}})
        wish_c = 0
        try:
            if "wishes" in await db.list_collection_names():
                wish_c = await db.wishes.count_documents({"profile_id": {"$in": owner_ids}, "created_at": {"$gte": cutoff}})
        except Exception:
            pass
        return {"count": rsvp_c + wish_c, "rsvps": rsvp_c, "wishes": wish_c}

    return router
