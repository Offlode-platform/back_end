"""
Users API Endpoints
CRUD operations for users (practice managers and team members)
"""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.user import (
    UserCreate,
    UserDeactivate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user (practice manager or team member)
    
    TODO: Add authentication and check that requester is a practice manager
    """
    
    # Check if email already exists
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user.email}' already exists"
        )
    
    # Create user
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log action
    AuditLog.log_action(
        db=db,
        organization_id=db_user.organization_id,
        action='user_created',
        resource_type='user',
        resource_id=db_user.id,
        severity='info',
        details={'email': db_user.email, 'role': db_user.role}
    )
    
    return db_user


@router.get("/", response_model=List[UserResponse])
def list_users(
    organization_id: UUID = None,
    role: str = None,
    include_deactivated: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all users
    
    TODO: Add authentication and filter by requester's organization
    """
    query = db.query(User)
    
    if organization_id:
        query = query.filter(User.organization_id == organization_id)
    
    if role:
        query = query.filter(User.role == role)
    
    if not include_deactivated:
        query = query.filter(User.deactivated_at.is_(None))
    
    users = query.offset(skip).limit(limit).all()
    
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific user by ID
    
    TODO: Add authentication and check permissions
    """
    user = db.query(User)\
        .filter(User.id == user_id)\
        .first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    return user


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a user
    
    TODO: Add authentication and check that requester is a practice manager
    """
    
    # Get user
    db_user = db.query(User)\
        .filter(User.id == user_id)\
        .filter(User.deactivated_at.is_(None))\
        .first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Update fields
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    
    # Log action
    AuditLog.log_action(
        db=db,
        organization_id=db_user.organization_id,
        action='user_updated',
        resource_type='user',
        resource_id=db_user.id,
        severity='info',
        details=update_data
    )
    
    return db_user


@router.post("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    deactivate_data: UserDeactivate,
    db: Session = Depends(get_db)
):
    """
    Deactivate a user (soft delete)
    
    TODO: Add authentication and implement security controls:
    - Only practice managers can deactivate
    - Cannot deactivate last practice manager
    - Two-step confirmation for practice managers
    - Email notifications
    """
    
    db_user = db.query(User)\
        .filter(User.id == user_id)\
        .filter(User.deactivated_at.is_(None))\
        .first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )
    
    # Check if this is the last practice manager
    if db_user.is_practice_manager:
        active_pms = db.query(User)\
            .filter(User.organization_id == db_user.organization_id)\
            .filter(User.role == 'practice_manager')\
            .filter(User.deactivated_at.is_(None))\
            .count()
        
        if active_pms <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last practice manager"
            )
    
    # Deactivate user
    db_user.deactivated_at = datetime.utcnow()
    # db_user.deactivated_by = current_user_id  # TODO: Set from JWT
    
    db.commit()
    db.refresh(db_user)
    
    # Log action
    severity = 'critical' if db_user.is_practice_manager else 'warning'
    AuditLog.log_action(
        db=db,
        organization_id=db_user.organization_id,
        action='user_deactivated',
        resource_type='user',
        resource_id=db_user.id,
        severity=severity,
        details={
            'email': db_user.email,
            'role': db_user.role,
            'reason': deactivate_data.reason
        }
    )
    
    # TODO: Send email notifications
    # TODO: Handle orphaned clients if team member
    
    return db_user


@router.post("/{user_id}/reactivate", response_model=UserResponse)
def reactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Reactivate a deactivated user
    
    TODO: Add authentication and check that requester is a practice manager
    """
    
    db_user = db.query(User)\
        .filter(User.id == user_id)\
        .filter(User.deactivated_at.is_not(None))\
        .first()
    
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deactivated user {user_id} not found"
        )
    
    # Reactivate user
    db_user.deactivated_at = None
    db_user.deactivated_by = None
    
    db.commit()
    db.refresh(db_user)
    
    # Log action
    AuditLog.log_action(
        db=db,
        organization_id=db_user.organization_id,
        action='user_reactivated',
        resource_type='user',
        resource_id=db_user.id,
        severity='info',
        details={'email': db_user.email, 'role': db_user.role}
    )
    
    return db_user
