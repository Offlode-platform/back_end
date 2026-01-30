"""
Organization Model
Represents accounting firms using the Sentinel platform
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Organization(Base):
    """
    Organizations (Accounting Firms)
    Each organization is a tenant in the multi-tenant system
    """
    __tablename__ = "organizations"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Subscription & Billing
    subscription_status = Column(String(50), default='trial', nullable=False)  # trial, active, cancelled, suspended
    subscription_tier = Column(String(50), default='basic', nullable=False)    # basic, professional, enterprise
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    
    # Settings (JSON field for flexible configuration)
    settings = Column(JSON, default={}, nullable=False)
    
    # Xero Integration
    xero_tenant_id = Column(String(255), unique=True, nullable=True, index=True)
    xero_connected = Column(Boolean, default=False, nullable=False)
    
    # Audit Trail
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="organization", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="organization", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="organization", cascade="all, delete-orphan")
    chases = relationship("Chase", back_populates="organization", cascade="all, delete-orphan")
    xero_connections = relationship("XeroConnection", back_populates="organization", cascade="all, delete-orphan")
    exclusion_rules = relationship("ExclusionRule", back_populates="organization", cascade="all, delete-orphan")
    client_assignments = relationship("ClientAssignment", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization {self.name} ({self.slug})>"

    @property
    def is_active(self) -> bool:
        """Check if organization subscription is active"""
        return self.subscription_status in ['trial', 'active']

    @property
    def is_deleted(self) -> bool:
        """Check if organization is soft-deleted"""
        return self.deleted_at is not None
