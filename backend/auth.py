from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import os
import logging
from typing import Optional, Tuple, Dict, Any

# Supabase JWT verification (asymmetric ES256/RS256 via JWKS, or legacy HS256).
try:
    from auth_supabase import verify_supabase_jwt, SupabaseAuthError
    _SUPABASE_AVAILABLE = True
except Exception as _exc:  # pragma: no cover - import failure shouldn't break legacy
    _SUPABASE_AVAILABLE = False
    _SUPABASE_IMPORT_ERROR = _exc

logger = logging.getLogger("auth")


# Security configurations
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
security = HTTPBearer()


# ---------------------------------------------------------------------------
# MongoDB admins lookup (lazy-imported to avoid circular imports at module
# load-time — server.py wires `db` into globals after FastAPI app boot).
# ---------------------------------------------------------------------------
def _get_db():
    """Best-effort retrieval of the Motor db handle bound by server.py."""
    import sys
    server_mod = sys.modules.get("server")
    if server_mod is not None:
        return getattr(server_mod, "db", None)
    return None


async def _admin_id_from_supabase_claims(claims: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Map a Supabase JWT to (admin_id, role) using MongoDB `admins`.

    Lookup order:
      1. admins.supabase_user_id == claims.sub
      2. admins.email == claims.email (and stamp supabase_user_id for next time)
    """
    db = _get_db()
    if db is None:
        return None

    sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()

    admin_doc = None
    if sub:
        admin_doc = await db.admins.find_one({"supabase_user_id": sub})

    if admin_doc is None and email:
        admin_doc = await db.admins.find_one({"email": email})
        if admin_doc and sub and not admin_doc.get("supabase_user_id"):
            # First time this Supabase user has hit the backend — link them.
            try:
                await db.admins.update_one(
                    {"id": admin_doc["id"]},
                    {"$set": {"supabase_user_id": sub}},
                )
            except Exception as exc:
                logger.warning("Failed to link supabase_user_id for %s: %s", email, exc)

    if not admin_doc:
        return None

    return admin_doc.get("id"), admin_doc.get("role", "admin")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({'exp': expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Hybrid: validate Supabase JWT first, fall back to legacy JWT.

    Returns the MongoDB `admins.id` (str). Existing routes that depend on this
    keep working unchanged.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    token = credentials.credentials

    # 1) Supabase JWT (asymmetric via JWKS).
    if _SUPABASE_AVAILABLE:
        try:
            claims = verify_supabase_jwt(token)
            mapped = await _admin_id_from_supabase_claims(claims)
            if mapped:
                return mapped[0]
            # Token is valid but the user isn't in our admins collection.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Authenticated but no admin profile found',
            )
        except SupabaseAuthError:
            # Not a Supabase token — fall through to legacy verification.
            pass

    # 2) Legacy custom JWT (HS256 with our SECRET_KEY).
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    admin_id: str = payload.get('sub')
    if admin_id is None:
        raise credentials_exception

    return admin_id


async def get_current_admin_with_role(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Hybrid: returns {'admin_id', 'role'} for legacy callers."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )

    token = credentials.credentials

    # 1) Supabase JWT first.
    if _SUPABASE_AVAILABLE:
        try:
            claims = verify_supabase_jwt(token)
            mapped = await _admin_id_from_supabase_claims(claims)
            if mapped:
                return {'admin_id': mapped[0], 'role': mapped[1]}
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Authenticated but no admin profile found',
            )
        except SupabaseAuthError:
            pass

    # 2) Legacy JWT.
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    admin_id: str = payload.get('sub')
    role: str = payload.get('role')

    if admin_id is None or role is None:
        raise credentials_exception

    return {'admin_id': admin_id, 'role': role}


async def require_super_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """PHASE 35: Middleware to ensure only Super Admin can access"""
    admin_data = await get_current_admin_with_role(credentials)
    
    if admin_data['role'] != 'super_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Super Admin access required'
        )
    
    return admin_data['admin_id']


async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """PHASE 35: Middleware to ensure authenticated admin (Super Admin or Admin)"""
    admin_data = await get_current_admin_with_role(credentials)
    return admin_data
