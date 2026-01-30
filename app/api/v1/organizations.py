"""
Organizations API Endpoints
CRUD operations for organizations
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.organization import Organization
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)

router = APIRouter()


@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    organization: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create a new organization"""
    
    # Check if slug already exists
    existing = db.query(Organization).filter(Organization.slug == organization.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{organization.slug}' already exists"
        )
    
    # Create organization
    db_org = Organization(**organization.model_dump())
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    
    return db_org


@router.get("/", response_model=List[OrganizationResponse])
def list_organizations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all organizations"""
    organizations = db.query(Organization)\
        .filter(Organization.deleted_at.is_(None))\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return organizations


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific organization by ID"""
    organization = db.query(Organization)\
        .filter(Organization.id == organization_id)\
        .filter(Organization.deleted_at.is_(None))\
        .first()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {organization_id} not found"
        )
    
    return organization


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: UUID,
    organization_update: OrganizationUpdate,
    db: Session = Depends(get_db)
):
    """Update an organization"""
    
    # Get organization
    db_org = db.query(Organization)\
        .filter(Organization.id == organization_id)\
        .filter(Organization.deleted_at.is_(None))\
        .first()
    
    if not db_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {organization_id} not found"
        )
    
    # Update fields
    update_data = organization_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_org, field, value)
    
    db.commit()
    db.refresh(db_org)
    
    return db_org


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    organization_id: UUID,
    db: Session = Depends(get_db)
):
    """Soft delete an organization"""
    from datetime import datetime
    
    db_org = db.query(Organization)\
        .filter(Organization.id == organization_id)\
        .filter(Organization.deleted_at.is_(None))\
        .first()
    
    if not db_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {organization_id} not found"
        )
    
    # Soft delete
    db_org.deleted_at = datetime.utcnow()
    db.commit()
    
    return None
