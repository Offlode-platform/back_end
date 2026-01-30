"""
Document Model
Represents receipts, invoices, and other documents uploaded by clients
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    """
    Documents (Receipts/Invoices)
    Each document belongs to one organization and one client
    Can be linked to a transaction
    """
    __tablename__ = "documents"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Keys
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File Information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)  # Size in bytes
    mime_type = Column(String(100), nullable=True)
    
    # S3 Storage
    s3_key = Column(String(500), nullable=False, unique=True, index=True)
    s3_bucket = Column(String(255), default='sentinel-documents-prod', nullable=False)
    
    # OCR Data (AWS Textract)
    ocr_status = Column(String(50), default='pending', nullable=False)  # pending, processing, completed, failed
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Numeric(5, 2), nullable=True)  # 0.00 to 100.00
    
    # Extracted Information
    extracted_amount = Column(Numeric(12, 2), nullable=True)
    extracted_date = Column(Date, nullable=True)
    extracted_supplier = Column(String(255), nullable=True)
    
    # Xero Integration
    xero_file_id = Column(String(255), nullable=True)
    forwarded_to_xero = Column(Boolean, default=False, nullable=False)
    forwarded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit Trail
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="documents")
    transaction = relationship("Transaction", back_populates="documents")
    client = relationship("Client", back_populates="documents")
    uploaded_by_user = relationship("User", back_populates="uploaded_documents", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<Document {self.filename} ({self.ocr_status})>"

    @property
    def s3_url(self) -> str:
        """Get S3 URL (not pre-signed)"""
        return f"s3://{self.s3_bucket}/{self.s3_key}"

    @property
    def is_processed(self) -> bool:
        """Check if OCR processing is complete"""
        return self.ocr_status == 'completed'

    @property
    def needs_ocr(self) -> bool:
        """Check if document needs OCR processing"""
        return self.ocr_status == 'pending'
