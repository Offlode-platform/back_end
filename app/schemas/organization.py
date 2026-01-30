"""
Organization Schemas
Pydantic models for request/response validation
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationBase(BaseModel):
    """Base schema for Organization"""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)


class OrganizationCreate(OrganizationBase):
    """Schema for creating an organization"""
    subscription_tier: Optional[str] = "basic"


class OrganizationUpdate(BaseModel):
    """Schema for updating an organization"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subscription_status: Optional[str] = None
    subscription_tier: Optional[str] = None
    xero_connected: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    """Schema for organization response"""
    id: UUID
    subscription_status: str
    subscription_tier: str
    xero_connected: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)
