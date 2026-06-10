from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import os
from typing import Optional


# Security configurations
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
security = HTTPBearer()


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
    """Get current admin from token (works for both Super Admin and Admin)"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    admin_id: str = payload.get('sub')
    if admin_id is None:
        raise credentials_exception
    
    return admin_id


async def get_current_admin_with_role(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """PHASE 35: Get current admin with role information"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    
    token = credentials.credentials
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
