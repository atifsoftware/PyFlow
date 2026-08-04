"""
app/api/routes/users.py
========================
Users REST API Routes:
- GET    /api/users          → সকল ব্যবহারকারী (JWT প্রয়োজন)
- GET    /api/users/{id}     → একজন ব্যবহারকারীর তথ্য
- POST   /api/users          → নতুন ব্যবহারকারী তৈরি
- PUT    /api/users/{id}     → ব্যবহারকারী আপডেট
- DELETE /api/users/{id}     → ব্যবহারকারী মুছে দেওয়া
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.api.routes.auth import get_current_user, get_app_config
from app.models.user_model import User

router = APIRouter()


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str

class UserCreateRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None

class PaginatedUsers(BaseModel):
    data: List[UserOut]
    total: int
    page: int
    per_page: int


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedUsers, summary="সকল ব্যবহারকারী দেখুন")
async def list_users(
    page: int = Query(1, ge=1, description="পেজ নম্বর"),
    per_page: int = Query(10, ge=1, le=100, description="প্রতি পেজে কতজন"),
    search: Optional[str] = Query(None, description="নাম বা ইমেইল দিয়ে খুঁজুন"),
    _: dict = Depends(get_app_config),
    current_user=Depends(get_current_user),
):
    """
    JWT Authentication প্রয়োজন।
    সকল ব্যবহারকারীর তালিকা pagination সহ দেখুন।
    """
    query = User.query()

    if search:
        # নাম বা ইমেইলে search
        all_users = User.all()
        s = search.lower()
        filtered = [
            u for u in all_users
            if s in u._attributes.get("name", "").lower()
            or s in u._attributes.get("email", "").lower()
        ]
        total = len(filtered)
        start = (page - 1) * per_page
        users_page = filtered[start: start + per_page]
    else:
        all_users = User.all()
        total = len(all_users)
        start = (page - 1) * per_page
        users_page = all_users[start: start + per_page]

    return PaginatedUsers(
        data=[
            UserOut(
                id=u.id,
                name=u._attributes.get("name", ""),
                email=u._attributes.get("email", ""),
                role=u._attributes.get("role", "user"),
            )
            for u in users_page
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{user_id}", response_model=UserOut, summary="একজন ব্যবহারকারীর তথ্য")
async def get_user(
    user_id: int,
    _: dict = Depends(get_app_config),
    current_user=Depends(get_current_user),
):
    """JWT Authentication প্রয়োজন।"""
    user = User.find(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"ID {user_id} ব্যবহারকারী পাওয়া যায়নি")

    return UserOut(
        id=user.id,
        name=user._attributes.get("name", ""),
        email=user._attributes.get("email", ""),
        role=user._attributes.get("role", "user"),
    )


@router.post("", response_model=UserOut, status_code=201, summary="নতুন ব্যবহারকারী তৈরি করুন")
async def create_user(
    data: UserCreateRequest,
    _: dict = Depends(get_app_config),
    current_user=Depends(get_current_user),
):
    """
    JWT Authentication প্রয়োজন।
    নতুন ব্যবহারকারী তৈরি করুন। ইমেইল অবশ্যই অনন্য হতে হবে।
    """
    # Email uniqueness check
    existing = User.find_by("email", data.email)
    if existing:
        raise HTTPException(status_code=422, detail="এই ইমেইল ইতোমধ্যে নিবন্ধিত")

    user = User.create_with_password(
        name=data.name,
        email=data.email,
        plain_password=data.password,
        role=data.role,
    )

    if user is None:
        raise HTTPException(status_code=500, detail="ব্যবহারকারী তৈরি করতে সমস্যা হয়েছে")

    return UserOut(
        id=user.id,
        name=user._attributes.get("name", ""),
        email=user._attributes.get("email", ""),
        role=user._attributes.get("role", "user"),
    )


@router.put("/{user_id}", response_model=UserOut, summary="ব্যবহারকারী আপডেট করুন")
async def update_user(
    user_id: int,
    data: UserUpdateRequest,
    _: dict = Depends(get_app_config),
    current_user=Depends(get_current_user),
):
    """JWT Authentication প্রয়োজন।"""
    user = User.find(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"ID {user_id} ব্যবহারকারী পাওয়া যায়নি")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="কোনো আপডেট ডেটা দেওয়া হয়নি")

    # Email uniqueness check
    if "email" in updates:
        existing = User.find_by("email", updates["email"])
        if existing and existing.id != user_id:
            raise HTTPException(status_code=422, detail="এই ইমেইল ইতোমধ্যে ব্যবহৃত হচ্ছে")

    user.update(updates)

    return UserOut(
        id=user.id,
        name=user._attributes.get("name", ""),
        email=user._attributes.get("email", ""),
        role=user._attributes.get("role", "user"),
    )


@router.delete("/{user_id}", summary="ব্যবহারকারী মুছে দিন")
async def delete_user(
    user_id: int,
    _: dict = Depends(get_app_config),
    current_user=Depends(get_current_user),
):
    """JWT Authentication প্রয়োজন। নিজেকে মুছে দেওয়া যাবে না।"""
    if current_user.id == user_id:
        raise HTTPException(status_code=403, detail="নিজের অ্যাকাউন্ট মুছে দেওয়া যাবে না")

    user = User.find(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"ID {user_id} ব্যবহারকারী পাওয়া যায়নি")

    user.delete()
    return {"message": f"ID {user_id} ব্যবহারকারী সফলভাবে মুছে দেওয়া হয়েছে"}
