"""
Client Assignments API Endpoints
Manage team member assignments to clients
"""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.client_assignment import ClientAssignment
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.client_assignment import (
    ClientAssignmentBulk,
    ClientAssignmentCreate,
    ClientAssignmentResponse,
)

router = APIRouter()


@router.post("/", response_model=ClientAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_client(
    assignment: ClientAssignmentCreate,
    db: Session = Depends(get_db)
):
    """
    Assign a client to a team member (or unassign if user_id is None)
    
    TODO: Add authentication and check that requester is a practice manager
    """
    
    # Get client
    client = db.query(Client).filter(Client.id == assignment.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {assignment.client_id} not found"
        )
    
    # Verify user exists and is a team member (if assigning)
    if assignment.user_id:
        user = db.query(User).filter(User.id == assignment.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {assignment.user_id} not found"
            )
        
        # Check user belongs to same organization
        if user.organization_id != client.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User and client must belong to the same organization"
            )
    
    # Check if client already has an active assignment
    existing = db.query(ClientAssignment)\
        .filter(ClientAssignment.client_id == assignment.client_id)\
        .filter(ClientAssignment.unassigned_at.is_(None))\
        .first()
    
    if existing:
        # Unassign the old assignment
        existing.unassigned_at = datetime.utcnow()
        db.commit()
        
        # Log reassignment
        AuditLog.log_action(
            db=db,
            organization_id=client.organization_id,
            action='client_reassigned',
            resource_type='client_assignment',
            resource_id=existing.id,
            client_id=client.id,
            severity='info',
            details={
                'old_user_id': str(existing.user_id) if existing.user_id else None,
                'new_user_id': str(assignment.user_id) if assignment.user_id else None
            }
        )
    
    # Create new assignment
    db_assignment = ClientAssignment(
        organization_id=client.organization_id,
        client_id=assignment.client_id,
        user_id=assignment.user_id,
        # assigned_by=current_user_id  # TODO: Set from JWT
    )
    db.add(db_assignment)
    db.commit()
    db.refresh(db_assignment)
    
    # Build response
    response = ClientAssignmentResponse.model_validate(db_assignment)
    response.client_name = client.name
    
    if assignment.user_id:
        user = db.query(User).filter(User.id == assignment.user_id).first()
        if user:
            response.user_name = user.name
            response.user_email = user.email
    
    return response


@router.post("/bulk", response_model=List[ClientAssignmentResponse])
def bulk_assign_clients(
    bulk_assignment: ClientAssignmentBulk,
    db: Session = Depends(get_db)
):
    """
    Bulk assign multiple clients to a team member
    
    TODO: Add authentication and check that requester is a practice manager
    """
    
    # Verify user exists (if assigning)
    if bulk_assignment.user_id:
        user = db.query(User).filter(User.id == bulk_assignment.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {bulk_assignment.user_id} not found"
            )
    
    results = []
    
    for client_id in bulk_assignment.client_ids:
        # Get client
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            continue  # Skip if client not found
        
        # Unassign existing
        existing = db.query(ClientAssignment)\
            .filter(ClientAssignment.client_id == client_id)\
            .filter(ClientAssignment.unassigned_at.is_(None))\
            .first()
        
        if existing:
            existing.unassigned_at = datetime.utcnow()
        
        # Create new assignment
        db_assignment = ClientAssignment(
            organization_id=client.organization_id,
            client_id=client_id,
            user_id=bulk_assignment.user_id,
        )
        db.add(db_assignment)
        db.commit()
        db.refresh(db_assignment)
        
        # Build response
        response = ClientAssignmentResponse.model_validate(db_assignment)
        response.client_name = client.name
        
        if bulk_assignment.user_id:
            user = db.query(User).filter(User.id == bulk_assignment.user_id).first()
            if user:
                response.user_name = user.name
                response.user_email = user.email
        
        results.append(response)
        
        # Log action
        AuditLog.log_action(
            db=db,
            organization_id=client.organization_id,
            action='client_assigned' if bulk_assignment.user_id else 'client_unassigned',
            resource_type='client_assignment',
            resource_id=db_assignment.id,
            client_id=client.id,
            severity='info'
        )
    
    return results


@router.get("/", response_model=List[ClientAssignmentResponse])
def list_assignments(
    organization_id: UUID = None,
    user_id: UUID = None,
    client_id: UUID = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all client assignments
    
    TODO: Add authentication and filter by organization
    """
    
    query = db.query(ClientAssignment)\
        .filter(ClientAssignment.unassigned_at.is_(None))
    
    if organization_id:
        query = query.filter(ClientAssignment.organization_id == organization_id)
    
    if user_id:
        query = query.filter(ClientAssignment.user_id == user_id)
    
    if client_id:
        query = query.filter(ClientAssignment.client_id == client_id)
    
    if unassigned_only:
        query = query.filter(ClientAssignment.user_id.is_(None))
    
    assignments = query.offset(skip).limit(limit).all()
    
    # Build responses with related data
    results = []
    for assignment in assignments:
        response = ClientAssignmentResponse.model_validate(assignment)
        
        # Get client name
        client = db.query(Client).filter(Client.id == assignment.client_id).first()
        if client:
            response.client_name = client.name
        
        # Get user info
        if assignment.user_id:
            user = db.query(User).filter(User.id == assignment.user_id).first()
            if user:
                response.user_name = user.name
                response.user_email = user.email
        
        results.append(response)
    
    return results


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_client(
    assignment_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Unassign a client (set to unassigned)
    
    TODO: Add authentication and check that requester is a practice manager
    """
    
    assignment = db.query(ClientAssignment)\
        .filter(ClientAssignment.id == assignment_id)\
        .filter(ClientAssignment.unassigned_at.is_(None))\
        .first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment {assignment_id} not found"
        )
    
    # Unassign
    assignment.unassigned_at = datetime.utcnow()
    db.commit()
    
    # Log action
    AuditLog.log_action(
        db=db,
        organization_id=assignment.organization_id,
        action='client_unassigned',
        resource_type='client_assignment',
        resource_id=assignment.id,
        client_id=assignment.client_id,
        severity='info'
    )
    
    return None
