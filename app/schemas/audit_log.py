"""
Audit Log Schemas
Pydantic models for audit log response validation
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Schema for audit log response"""
    id: UUID
    organization_id: UUID
    user_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    client_id: Optional[UUID]
    module: Optional[str]
    access_type: Optional[str]
    severity: str
    timestamp: datetime
    ip_address: Optional[str]
    details: dict
    
    # Related data
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    client_name: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs"""
    user_id: Optional[UUID] = None
    action: Optional[str] = None
    resource_type: Optional[str] = None
    client_id: Optional[UUID] = None
    module: Optional[str] = None
    severity: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
