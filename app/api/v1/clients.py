"""
Clients API Endpoints
CRUD operations for clients (end customers)
"""
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.client_assignment import ClientAssignment
from app.models.audit_log import AuditLog
from app.schemas.client import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    ClientWithAssignment,
)

router = APIRouter()


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new client
    
    TODO: Add authentication and set organization_id from JWT
    """
    
    # Create client
    db_client = Client(**client.model_dump())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    
    # Create initial assignment (unassigned)
    assignment = ClientAssignment(
        organization_id=db_client.organization_id,
        client_id=db_client.id,
        user_id=None  # Unassigned
    )
    db.add(assignment)
    db.commit()
    
    # Log action
    AuditLog.log_action(
        db=db,
        organization_id=db_client.organization_id,
        action='client_created',
        resource_type='client',
        resource_id=db_client.id,
        client_id=db_client.id,
        severity='info',
        details={'name': db_client.name, 'email': db_client.email}
    )
    
    return db_client


@router.get("/", response_model=List[ClientWithAssignment])
def list_clients(
    organization_id: UUID = None,
    assigned_to: UUID = None,
    unassigned_only: bool = False,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all clients with assignment information
    
    TODO: Add authentication and filter by:
    - Organization
    - Team member's assigned clients only (if not practice manager)
    """
    
    # Join with assignments
    query = db.query(
        Client,
        ClientAssignment.user_id,
        ClientAssignment.assigned_at
    ).outerjoin(
        ClientAssignment,
        (ClientAssignment.client_id == Client.id) & 
        (ClientAssignment.unassigned_at.is_(None))
    )
    
    if organization_id:
        query = query.filter(Client.organization_id == organization_id)
    
    if assigned_to:
        query = query.filter(ClientAssignment.user_id == assigned_to)
    
    if unassigned_only:
        query = query.filter(ClientAssignment.user_id.is_(None))
    
    query = query.filter(Client.deleted_at.is_(None))
    
    results = query.offset(skip).limit(limit).all()
    
    # Build response with assignment info
    clients_with_assignments = []
    for client, user_id, assigned_at in results:
        client_dict = ClientWithAssignment.model_validate(client).model_dump()
        client_dict['assigned_user_id'] = user_id
        client_dict['assigned_at'] = assigned_at
        
        # Get user name if assigned
        if user_id:
            from app.models.user import User
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                client_dict['assigned_user_name'] = user.name
        
        clients_with_assignments.append(ClientWithAssignment(**client_dict))
    
    return clients_with_assignments


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific client by ID
    
    TODO: Add authentication and check permissions (assigned or practice manager)
    """
    client = db.query(Client)\
        .filter(Client.id == client_id)\
        .filter(Client.deleted_at.is_(None))\
        .first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found"
        )
    
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    client_update: ClientUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a client
    
    TODO: Add authentication and check permissions
    """
    
    # Get client
    db_client = db.query(Client)\
        .filter(Client.id == client_id)\
        .filter(Client.deleted_at.is_(None))\
        .first()
    
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found"
        )
    
    # Update fields
    update_data = client_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_client, field, value)
    
    db.commit()
    db.refresh(db_client)
    
    # Log action
    AuditLog.log_action(
        db=db,
        organization_id=db_client.organization_id,
        action='client_updated',
        resource_type='client',
        resource_id=db_client.id,
        client_id=db_client.id,
        severity='info',
        details=update_data
    )
    
    return db_client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Soft delete a client
    
    TODO: Add authentication and check that requester is a practice manager
    """
    
    db_client = db.query(Client)\
        .filter(Client.id == client_id)\
        .filter(Client.deleted_at.is_(None))\
        .first()
    
    if not db_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} not found"
        )
    
    # Soft delete
    db_client.deleted_at = datetime.utcnow()
    db.commit()
    
    # Log action
    AuditLog.log_action(
        db=db,
        organization_id=db_client.organization_id,
        action='client_deleted',
        resource_type='client',
        resource_id=db_client.id,
        client_id=db_client.id,
        severity='warning',
        details={'name': db_client.name}
    )
    
    return None
