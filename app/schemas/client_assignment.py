"""
Client Assignment Schemas
Pydantic models for client assignment request/response validation
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ClientAssignmentCreate(BaseModel):
    """Schema for assigning a client to a user"""
    client_id: UUID
    user_id: Optional[UUID] = None  # None = unassign


class ClientAssignmentBulk(BaseModel):
    """Schema for bulk assigning clients"""
    client_ids: list[UUID]
    user_id: Optional[UUID] = None  # None = unassign all


class ClientAssignmentResponse(BaseModel):
    """Schema for assignment response"""
    id: UUID
    organization_id: UUID
    client_id: UUID
    user_id: Optional[UUID]
    assigned_at: datetime
    assigned_by: Optional[UUID]
    unassigned_at: Optional[datetime]
    
    # Related data
    client_name: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    
    is_assigned: bool

    class Config:
        from_attributes = True
