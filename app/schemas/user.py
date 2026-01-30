"""
User Schemas
Pydantic models for user request/response validation
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base schema for User"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    """Schema for creating a user"""
    role: str = Field(..., pattern="^(practice_manager|team_member)$")
    organization_id: UUID


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[str] = Field(None, pattern="^(practice_manager|team_member)$")
    two_factor_enabled: Optional[bool] = None
    notification_preferences: Optional[dict] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    organization_id: UUID
    role: str
    email_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    deactivated_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class UserDeactivate(BaseModel):
    """Schema for deactivating a user"""
    reason: Optional[str] = Field(None, max_length=500)
