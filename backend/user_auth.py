"""
Public-user authentication module.

Adds a *separate* identity layer for end-users (wedding guests) who want to
sign up to buy credits / track their AI-matched photos. This is INDEPENDENT
from the photographer / super-admin `admins` collection — they live in
different collections, have different roles, and never share tokens.

Two routes:
  1) Classic email + password (bcrypt) — POST /api/users/register, /login
  2) Emergent-managed Google OAuth — GET /api/users/auth/session (called
     by the frontend AuthCallback after `?session_id=...` lands)

Cookie name: `user_session_token` — cookie path "/", httpOnly, secure, samesite=none.
"""

from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends, Response, Request, Header
from pydantic import BaseModel, EmailStr, Field

logger = logging.getLogger("user_auth")


# ----------------------------------------------------------------------------
# Models
# ----------------------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=8, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=20)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    credits: int = 0
    auth_provider: str  # "password" | "google"
    created_at: datetime


# ----------------------------------------------------------------------------
# Router builder — wires into the main FastAPI app
# ----------------------------------------------------------------------------
def build_user_auth_router(db, password_hasher, password_verifier) -> APIRouter:
    """Build the public-user auth router.

    `password_hasher(plain) -> str` and `password_verifier(plain, hash) -> bool`
    are injected so we reuse the same bcrypt setup as the admins module.
    """
    router = APIRouter(tags=["public-user-auth"])

    SESSION_TTL_DAYS = 7
    EMERGENT_SESSION_DATA_URL = (
        "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
    )

    async def _create_session(user_id: str, response: Response) -> str:
        session_token = f"usr_{uuid.uuid4().hex}{uuid.uuid4().hex}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
        await db.user_sessions.insert_one(
            {
                "user_id": user_id,
                "session_token": session_token,
                "expires_at": expires_at,
                "created_at": datetime.now(timezone.utc),
            }
        )
        # Cross-site cookie (frontend may live on a different subdomain in prod)
        response.set_cookie(
            key="user_session_token",
            value=session_token,
            max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
            path="/",
            httponly=True,
            secure=True,
            samesite="none",
        )
        return session_token

    async def _resolve_session_token(
        request: Request, authorization: Optional[str] = Header(default=None)
    ) -> Optional[str]:
        token = request.cookies.get("user_session_token")
        if token:
            return token
        if authorization and authorization.lower().startswith("bearer "):
            return authorization.split(" ", 1)[1].strip()
        return None

    async def get_current_user(
        request: Request,
        authorization: Optional[str] = Header(default=None),
    ) -> dict:
        token = await _resolve_session_token(request, authorization)
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")
        exp = session.get("expires_at")
        if isinstance(exp, str):
            try:
                exp = datetime.fromisoformat(exp)
            except Exception:
                exp = None
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        # July 2025 — account-status enforcement. Suspended users see a
        # friendly 403; blocked users have their sessions deleted by the
        # super-admin endpoint so we should never even reach here, but we
        # defend in depth.
        u_status = (user.get("status") or "active").lower()
        if u_status == "blocked":
            try:
                await db.user_sessions.delete_one({"session_token": token})
            except Exception:
                pass
            raise HTTPException(status_code=403, detail="This account has been blocked. Please contact support.")
        if u_status == "suspended":
            raise HTTPException(status_code=403, detail="This account is temporarily suspended. Please contact support.")
        return user

    # ============================================================
    # Classic email + password signup / login
    # ============================================================
    @router.post("/api/users/register")
    async def register(payload: UserRegister, response: Response):
        email_l = payload.email.lower().strip()
        existing = await db.users.find_one({"email": email_l}, {"_id": 0})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        user_doc = {
            "user_id": user_id,
            "email": email_l,
            "name": payload.name.strip(),
            "phone": (payload.phone or "").strip() or None,
            "picture": None,
            "password_hash": password_hasher(payload.password),
            "credits": 0,
            "auth_provider": "password",
            "created_at": datetime.now(timezone.utc),
        }
        await db.users.insert_one(user_doc)
        await _create_session(user_id, response)
        user_doc.pop("password_hash", None)
        user_doc.pop("_id", None)
        return user_doc

    @router.post("/api/users/login")
    async def login(payload: UserLogin, response: Response):
        email_l = payload.email.lower().strip()
        user = await db.users.find_one({"email": email_l}, {"_id": 0})
        if not user or not user.get("password_hash"):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not password_verifier(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Account-status gate (July 2025) — refuse login for non-active users
        u_status = (user.get("status") or "active").lower()
        if u_status == "blocked":
            raise HTTPException(status_code=403, detail="This account has been blocked. Please contact support.")
        if u_status == "suspended":
            raise HTTPException(status_code=403, detail="This account is temporarily suspended. Please contact support.")
        await _create_session(user["user_id"], response)
        user.pop("password_hash", None)
        return user

    # ============================================================
    # Emergent Google OAuth — exchanged from session_id fragment
    # ============================================================
    @router.post("/api/users/auth/session")
    async def auth_session(payload: dict, response: Response):
        """Frontend AuthCallback POSTs { session_id } here after Google login."""
        session_id = (payload or {}).get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id required")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    EMERGENT_SESSION_DATA_URL,
                    headers={"X-Session-ID": session_id},
                )
        except Exception as e:
            logger.warning(f"Emergent session-data call failed: {e}")
            raise HTTPException(status_code=502, detail="Auth provider unreachable")
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid session_id")
        data = resp.json()
        email_l = (data.get("email") or "").lower().strip()
        if not email_l:
            raise HTTPException(status_code=400, detail="Google session missing email")

        existing = await db.users.find_one({"email": email_l}, {"_id": 0})
        if existing:
            user_id = existing["user_id"]
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "name": data.get("name") or existing.get("name"),
                    "picture": data.get("picture") or existing.get("picture"),
                    "last_login_at": datetime.now(timezone.utc),
                }},
            )
        else:
            user_id = f"user_{uuid.uuid4().hex[:12]}"
            await db.users.insert_one({
                "user_id": user_id,
                "email": email_l,
                "name": data.get("name") or email_l.split("@")[0],
                "picture": data.get("picture"),
                "credits": 0,
                "auth_provider": "google",
                "created_at": datetime.now(timezone.utc),
            })

        await _create_session(user_id, response)
        return await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})

    # ============================================================
    # Authenticated routes
    # ============================================================
    @router.get("/api/users/me")
    async def me(current=Depends(get_current_user)):
        current.pop("password_hash", None)
        return current

    @router.post("/api/users/logout")
    async def logout(request: Request, response: Response):
        token = request.cookies.get("user_session_token")
        if token:
            await db.user_sessions.delete_one({"session_token": token})
        response.delete_cookie("user_session_token", path="/")
        return {"success": True}

    return router, get_current_user
