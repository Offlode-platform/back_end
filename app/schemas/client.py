"""
Client Schemas
Pydantic models for client request/response validation
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ClientBase(BaseModel):
    """Base schema for Client"""
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)


class ClientCreate(ClientBase):
    """Schema for creating a client"""
    organization_id: UUID
    xero_contact_id: Optional[str] = Field(None, max_length=255)
    chase_enabled: bool = True
    chase_frequency_days: int = Field(7, ge=1, le=90)
    escalation_days: int = Field(14, ge=1, le=90)


class ClientUpdate(BaseModel):
    """Schema for updating a client"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    chase_enabled: Optional[bool] = None
    chase_frequency_days: Optional[int] = Field(None, ge=1, le=90)
    escalation_days: Optional[int] = Field(None, ge=1, le=90)


class ClientResponse(ClientBase):
    """Schema for client response"""
    id: UUID
    organization_id: UUID
    xero_contact_id: Optional[str]
    chase_enabled: bool
    chase_frequency_days: int
    escalation_days: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class ClientWithAssignment(ClientResponse):
    """Schema for client with assignment info"""
    assigned_user_id: Optional[UUID] = None
    assigned_user_name: Optional[str] = None
    assigned_at: Optional[datetime] = None
