"""
app/api/routes/auth.py
=======================
Authentication API Routes:
- POST /api/auth/login   → JWT token পাওয়া
- GET  /api/auth/me      → নিজের তথ্য দেখা (JWT প্রয়োজন)
- POST /api/auth/logout  → (stateless — client টোকেন মুছে দেবে)
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional

from core.database import Database
from core.security import Hash, JWT
from config.config import get_config
from app.models.user_model import User

from fastapi.security.api_key import APIKeyHeader
from fastapi import Security

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_config = None

def get_app_config():
    global _config
    if _config is None:
        _config = get_config()
        Database.init(_config)
    return _config


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str


# ─── JWT / API Key Dependency ────────────────────────────────────────────────

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_api_key: Optional[str] = Security(api_key_header),
    config: dict = Depends(get_app_config),
):
    # API Key Authentication
    if x_api_key:
        from app.models.api_key_model import ApiKey
        user = ApiKey.authenticate(x_api_key)
        if user:
            return user
        raise HTTPException(status_code=401, detail="API Key অবৈধ বা নিষ্ক্রিয়")

    # JWT Authentication (Fallback)
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header অথবা X-API-Key প্রয়োজন")

    token = credentials.credentials
    payload = JWT.decode(token, config.get("SECRET_KEY", ""))
    if payload is None:
        raise HTTPException(status_code=401, detail="JWT টোকেন অবৈধ বা মেয়াদ শেষ")

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="টোকেনে user_id নেই")

    user = User.find(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="ব্যবহারকারী পাওয়া যায়নি")

    return user


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse, summary="লগইন করুন ও JWT টোকেন পান")
async def login(data: LoginRequest, config: dict = Depends(get_app_config)):
    """
    ইমেইল ও পাসওয়ার্ড দিয়ে লগইন করুন।
    সফল হলে **Bearer JWT টোকেন** পাবেন।
    """
    user = User.find_by("email", data.email)
    if user is None or not user.check_password(data.password):
        raise HTTPException(status_code=401, detail="ইমেইল বা পাসওয়ার্ড ভুল")

    payload = {
        "user_id": user.id,
        "email": user._attributes.get("email"),
        "role": user._attributes.get("role", "user"),
    }
    token = JWT.encode(payload, config.get("SECRET_KEY", ""), expires_in=86400)

    return LoginResponse(
        token=token,
        user={
            "id": user.id,
            "name": user._attributes.get("name"),
            "email": user._attributes.get("email"),
            "role": user._attributes.get("role", "user"),
        },
    )


@router.get("/me", response_model=UserResponse, summary="নিজের প্রোফাইল দেখুন")
async def me(current_user=Depends(get_current_user)):
    """
    JWT টোকেন দিয়ে নিজের অ্যাকাউন্টের তথ্য দেখুন।
    """
    return UserResponse(
        id=current_user.id,
        name=current_user._attributes.get("name", ""),
        email=current_user._attributes.get("email", ""),
        role=current_user._attributes.get("role", "user"),
    )


@router.post("/logout", summary="লগআউট (client-side)")
async def logout():
    """
    Stateless JWT logout — client কে অবশ্যই local storage থেকে token মুছে দিতে হবে।
    """
    return {"message": "সফলভাবে লগআউট হয়েছে। টোকেন মুছে দিন।"}
