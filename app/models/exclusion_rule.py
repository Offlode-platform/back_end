"""
Exclusion Rule Model
Defines patterns for automatically excluding transactions from requiring documents
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class ExclusionRule(Base):
    """
    Exclusion Rules (Auto-Exclude Patterns)
    Defines rules for automatically excluding transactions
    """
    __tablename__ = "exclusion_rules"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Multi-tenant Foreign Key
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Rule Details
    rule_type = Column(String(50), nullable=False, index=True)  # supplier_name, description, amount_range, category
    pattern = Column(String(255), nullable=False)
    match_type = Column(String(50), default='contains', nullable=False)  # contains, equals, starts_with, ends_with, regex
    
    # Settings
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    reason = Column(String(255), nullable=True)  # Why this rule exists (e.g., "Internal transfers")
    
    # Audit Trail
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="exclusion_rules")
    created_by_user = relationship("User", back_populates="created_rules", foreign_keys=[created_by])

    def __repr__(self):
        return f"<ExclusionRule {self.rule_type}: {self.pattern}>"

    @property
    def is_active(self) -> bool:
        """Check if rule is enabled"""
        return self.enabled

    def matches(self, value: str) -> bool:
        """
        Check if a value matches this rule
        
        Args:
            value: The value to check (e.g., supplier name, description)
            
        Returns:
            bool: True if matches, False otherwise
        """
        if not value or not self.enabled:
            return False
        
        value_lower = value.lower()
        pattern_lower = self.pattern.lower()
        
        if self.match_type == 'contains':
            return pattern_lower in value_lower
        elif self.match_type == 'equals':
            return value_lower == pattern_lower
        elif self.match_type == 'starts_with':
            return value_lower.startswith(pattern_lower)
        elif self.match_type == 'ends_with':
            return value_lower.endswith(pattern_lower)
        elif self.match_type == 'regex':
            import re
            try:
                return bool(re.search(self.pattern, value, re.IGNORECASE))
            except re.error:
                return False
        
        return False
