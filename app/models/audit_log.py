"""
Audit Log Model
Comprehensive logging for compliance (Xero, AML, MTD, GDPR)
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    """
    Audit Logs
    Immutable logs for compliance and security tracking
    Required for: Xero certification, AML/MLR 2017, MTD, GDPR
    """
    __tablename__ = "audit_logs"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Key
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # User Who Performed Action
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Action Details
    action = Column(String(100), nullable=False, index=True)  # login, logout, create, update, delete, view, etc.
    resource_type = Column(String(50), nullable=True, index=True)  # user, client, document, transaction, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Context
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    module = Column(String(50), nullable=True, index=True)  # receptionist, dashboard, settings, etc.
    access_type = Column(String(50), nullable=True)  # readonly, readwrite, admin
    
    # Severity (for alerts)
    severity = Column(String(50), default='info', nullable=False, index=True)  # info, warning, critical
    
    # Technical Details
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    
    # Additional Context (flexible JSON field)
    details = Column(JSON, default={}, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs", foreign_keys=[user_id])
    client = relationship("Client", back_populates="audit_logs")

    def __repr__(self):
        user_email = self.user.email if self.user else "SYSTEM"
        return f"<AuditLog {self.action} by {user_email} at {self.timestamp}>"

    @property
    def is_critical(self) -> bool:
        """Check if this is a critical event"""
        return self.severity == 'critical'

    @property
    def is_permission_failure(self) -> bool:
        """Check if this is a permission failure"""
        return self.action in ['permission_denied', 'access_denied', 'unauthorized']

    @classmethod
    def log_action(
        cls,
        db,
        organization_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID = None,
        resource_type: str = None,
        resource_id: uuid.UUID = None,
        client_id: uuid.UUID = None,
        module: str = None,
        access_type: str = None,
        severity: str = 'info',
        ip_address: str = None,
        user_agent: str = None,
        details: dict = None
    ):
        """
        Helper method to create audit log entry
        
        Usage:
            AuditLog.log_action(
                db=db,
                organization_id=org_id,
                action='login',
                user_id=user_id,
                severity='info',
                ip_address=request.client.host
            )
        """
        log_entry = cls(
            organization_id=organization_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            client_id=client_id,
            module=module,
            access_type=access_type,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {}
        )
        db.add(log_entry)
        db.commit()
        return log_entry
