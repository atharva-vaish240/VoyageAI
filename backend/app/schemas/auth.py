from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ── Request schemas ──────────────────────────────────────────────


class SignupRequest(BaseModel):
    """Public signup — name, email, password only. Role is never accepted."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str
    

# ── Response schemas ─────────────────────────────────────────────


class UserResponse(BaseModel):
    """Safe user representation — never includes password_hash."""
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    auth_provider: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
