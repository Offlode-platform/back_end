"""
Transaction Model
Represents bank transactions synced from Xero
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Transaction(Base):
    """
    Transactions (From Xero)
    Each transaction belongs to one organization and one client
    """
    __tablename__ = "transactions"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Xero Data
    xero_transaction_id = Column(String(255), unique=True, nullable=False, index=True)
    xero_type = Column(String(50), nullable=True)  # SPEND, RECEIVE, etc.
    
    # Transaction Details
    date = Column(Date, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)  # 12 digits, 2 decimal places
    description = Column(Text, nullable=True)
    supplier_name = Column(String(255), nullable=True, index=True)
    
    # Document Status
    document_required = Column(Boolean, default=True, nullable=False, index=True)
    document_received = Column(Boolean, default=False, nullable=False, index=True)
    document_uploaded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Auto-Exclusion
    excluded = Column(Boolean, default=False, nullable=False, index=True)
    exclusion_reason = Column(String(255), nullable=True)
    
    # Audit Trail
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="transactions")
    client = relationship("Client", back_populates="transactions")
    documents = relationship("Document", back_populates="transaction", cascade="all, delete-orphan")
    chases = relationship("Chase", back_populates="transaction", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transaction {self.xero_transaction_id} - £{self.amount}>"

    @property
    def needs_document(self) -> bool:
        """Check if transaction needs a document"""
        return self.document_required and not self.document_received and not self.excluded

    @property
    def is_overdue(self) -> bool:
        """Check if transaction is overdue (more than 30 days old and no document)"""
        if not self.needs_document:
            return False
        
        from datetime import timedelta
        days_old = (date.today() - self.date).days
        return days_old > 30
