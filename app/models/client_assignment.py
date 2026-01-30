"""
Client Assignment Model
Tracks which team members are assigned to which clients
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ClientAssignment(Base):
    """
    Client Assignments
    Tracks team member assignments to clients
    NULL user_id = unassigned client
    """
    __tablename__ = "client_assignments"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)  # NULL = unassigned
    
    # Assignment Details
    assigned_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    unassigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="client_assignments")
    client = relationship("Client", back_populates="assignments")
    user = relationship("User", back_populates="client_assignments", foreign_keys=[user_id])
    assigned_by_user = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self):
        user_email = self.user.email if self.user else "UNASSIGNED"
        return f"<ClientAssignment {self.client.name} → {user_email}>"

    @property
    def is_assigned(self) -> bool:
        """Check if client is currently assigned to a user"""
        return self.user_id is not None and self.unassigned_at is None

    @property
    def is_unassigned(self) -> bool:
        """Check if client is unassigned"""
        return self.user_id is None or self.unassigned_at is not None
