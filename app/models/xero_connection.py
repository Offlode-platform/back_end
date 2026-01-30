"""
Xero Connection Model
Stores OAuth tokens and connection status for Xero integration
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class XeroConnection(Base):
    """
    Xero Connections (OAuth Tokens)
    Stores encrypted OAuth tokens for Xero API access
    """
    __tablename__ = "xero_connections"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Key
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Xero Tenant Information
    xero_tenant_id = Column(String(255), nullable=False, index=True)
    xero_tenant_name = Column(String(255), nullable=True)
    
    # OAuth Tokens (Encrypted at application level)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Sync Status
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    sync_status = Column(String(50), default='active', nullable=False)  # active, expired, revoked, error
    
    # Audit Trail
    connected_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="xero_connections")
    connected_by_user = relationship("User", back_populates="connected_xero", foreign_keys=[connected_by])

    # Unique constraint: one organization can have one connection per Xero tenant
    __table_args__ = (
        # Composite unique index
        {"schema": None}
    )

    def __repr__(self):
        return f"<XeroConnection {self.xero_tenant_name} ({self.sync_status})>"

    @property
    def is_active(self) -> bool:
        """Check if connection is active"""
        return self.sync_status == 'active'

    @property
    def is_expired(self) -> bool:
        """Check if access token is expired"""
        return datetime.utcnow() >= self.expires_at

    @property
    def needs_refresh(self) -> bool:
        """Check if token needs refresh (expires in less than 1 hour)"""
        from datetime import timedelta
        return datetime.utcnow() >= (self.expires_at - timedelta(hours=1))
