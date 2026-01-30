"""
Client Model
Represents end customers of accounting firms
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Client(Base):
    """
    Clients (End Customers)
    Each client belongs to one organization (accounting firm)
    """
    __tablename__ = "clients"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Key
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Client Information
    name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    
    # Xero Integration
    xero_contact_id = Column(String(255), nullable=True, index=True)
    
    # Chase Settings (Configurable per client)
    chase_enabled = Column(Boolean, default=True, nullable=False)
    chase_frequency_days = Column(Integer, default=7, nullable=False)  # How often to chase
    escalation_days = Column(Integer, default=14, nullable=False)      # When to escalate (SMS/WhatsApp)
    
    # Audit Trail
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete
    
    # Relationships
    organization = relationship("Organization", back_populates="clients")
    transactions = relationship("Transaction", back_populates="client", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="client", cascade="all, delete-orphan")
    chases = relationship("Chase", back_populates="client", cascade="all, delete-orphan")
    assignments = relationship("ClientAssignment", back_populates="client", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client {self.name} ({self.email})>"

    @property
    def is_active(self) -> bool:
        """Check if client is active (not soft-deleted)"""
        return self.deleted_at is None

    @property
    def has_contact_info(self) -> bool:
        """Check if client has any contact information"""
        return bool(self.email or self.phone)
