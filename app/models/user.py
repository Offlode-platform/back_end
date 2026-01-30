"""
User Model
Represents accountants and staff members within an organization
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    Users (Accountants/Staff)
    Each user belongs to one organization (tenant)
    Roles: practice_manager, team_member
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Key
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Basic Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default='team_member', nullable=False, index=True)  # practice_manager, team_member
    
    # Authentication
    email_verified = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)  # Account lockout
    
    # 2FA (Two-Factor Authentication)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(255), nullable=True)  # TOTP secret (encrypted)
    
    # Settings (JSON field for user preferences)
    notification_preferences = Column(JSON, default={}, nullable=False)
    
    # Audit Trail
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Deactivation (Soft Delete)
    deactivated_at = Column(DateTime(timezone=True), nullable=True, index=True)
    deactivated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    deactivated_by_user = relationship("User", remote_side=[id], foreign_keys=[deactivated_by])
    
    # Client Assignments (for team members)
    client_assignments = relationship("ClientAssignment", back_populates="user", foreign_keys="ClientAssignment.user_id")
    
    # Activity Tracking
    created_chases = relationship("Chase", back_populates="created_by_user", foreign_keys="Chase.created_by")
    uploaded_documents = relationship("Document", back_populates="uploaded_by_user", foreign_keys="Document.uploaded_by")
    created_rules = relationship("ExclusionRule", back_populates="created_by_user", foreign_keys="ExclusionRule.created_by")
    connected_xero = relationship("XeroConnection", back_populates="connected_by_user", foreign_keys="XeroConnection.connected_by")
    
    # Audit Logs
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

    @property
    def is_practice_manager(self) -> bool:
        """Check if user is a practice manager"""
        return self.role == 'practice_manager'

    @property
    def is_team_member(self) -> bool:
        """Check if user is a team member"""
        return self.role == 'team_member'

    @property
    def is_active(self) -> bool:
        """Check if user is active (not deactivated)"""
        return self.deactivated_at is None

    @property
    def is_locked(self) -> bool:
        """Check if account is currently locked"""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until

    @property
    def requires_2fa(self) -> bool:
        """Check if 2FA is required (mandatory for practice managers)"""
        return self.is_practice_manager or self.two_factor_enabled
