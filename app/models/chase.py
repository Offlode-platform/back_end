"""
Chase Model
Represents communication attempts (email, SMS, WhatsApp, voice) to clients
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Chase(Base):
    """
    Chases (Communication Log)
    Tracks all communication attempts with clients
    """
    __tablename__ = "chases"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Chase Details
    chase_type = Column(String(50), nullable=False, index=True)  # email, sms, whatsapp, voice
    status = Column(String(50), default='pending', nullable=False, index=True)  # pending, sent, delivered, failed
    
    # Message Content
    message_template = Column(String(255), nullable=True)
    message_content = Column(Text, nullable=True)
    
    # Magic Link (For Email/SMS)
    magic_link_token = Column(String(255), unique=True, nullable=True, index=True)
    magic_link_expires_at = Column(DateTime(timezone=True), nullable=True)
    magic_link_clicked = Column(Boolean, default=False, nullable=False)
    magic_link_clicked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Delivery Status
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    
    # Escalation
    is_escalation = Column(Boolean, default=False, nullable=False)
    escalation_level = Column(Integer, default=0, nullable=False)  # 0=first attempt, 1=first escalation, etc.
    
    # Audit Trail
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="chases")
    client = relationship("Client", back_populates="chases")
    transaction = relationship("Transaction", back_populates="chases")
    created_by_user = relationship("User", back_populates="created_chases", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Chase {self.chase_type} - {self.status}>"

    @property
    def is_successful(self) -> bool:
        """Check if chase was delivered successfully"""
        return self.status in ['sent', 'delivered']

    @property
    def is_pending(self) -> bool:
        """Check if chase is still pending"""
        return self.status == 'pending'

    @property
    def magic_link_is_valid(self) -> bool:
        """Check if magic link is still valid"""
        if not self.magic_link_token or not self.magic_link_expires_at:
            return False
        return datetime.utcnow() < self.magic_link_expires_at
