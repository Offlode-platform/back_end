"""
Audit Logs API Endpoints
Read-only access to audit logs for compliance
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.models.client import Client
from app.schemas.audit_log import AuditLogResponse

router = APIRouter()


@router.get("/", response_model=List[AuditLogResponse])
def list_audit_logs(
    organization_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    client_id: Optional[UUID] = None,
    module: Optional[str] = None,
    severity: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List audit logs with filtering
    
    TODO: Add authentication and restrict to practice managers
    TODO: Filter by requester's organization automatically
    """
    
    query = db.query(AuditLog)
    
    # Filters
    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    
    if client_id:
        query = query.filter(AuditLog.client_id == client_id)
    
    if module:
        query = query.filter(AuditLog.module == module)
    
    if severity:
        query = query.filter(AuditLog.severity == severity)
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    # Order by timestamp descending (most recent first)
    query = query.order_by(AuditLog.timestamp.desc())
    
    logs = query.offset(skip).limit(limit).all()
    
    # Build responses with related data
    results = []
    for log in logs:
        response = AuditLogResponse.model_validate(log)
        
        # Get user info
        if log.user_id:
            user = db.query(User).filter(User.id == log.user_id).first()
            if user:
                response.user_email = user.email
                response.user_name = user.name
        
        # Get client info
        if log.client_id:
            client = db.query(Client).filter(Client.id == log.client_id).first()
            if client:
                response.client_name = client.name
        
        results.append(response)
    
    return results


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a specific audit log entry
    
    TODO: Add authentication and check permissions
    """
    
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log {log_id} not found"
        )
    
    # Build response with related data
    response = AuditLogResponse.model_validate(log)
    
    # Get user info
    if log.user_id:
        user = db.query(User).filter(User.id == log.user_id).first()
        if user:
            response.user_email = user.email
            response.user_name = user.name
    
    # Get client info
    if log.client_id:
        client = db.query(Client).filter(Client.id == log.client_id).first()
        if client:
            response.client_name = client.name
    
    return response


@router.get("/critical/recent", response_model=List[AuditLogResponse])
def get_critical_logs(
    organization_id: Optional[UUID] = None,
    hours: int = Query(24, ge=1, le=168),  # Last 24 hours by default, max 1 week
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get recent critical audit logs
    
    Useful for security monitoring and alerts
    
    TODO: Add authentication and restrict to practice managers
    """
    
    from datetime import timedelta
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(AuditLog)\
        .filter(AuditLog.severity == 'critical')\
        .filter(AuditLog.timestamp >= cutoff_time)
    
    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)
    
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    # Build responses
    results = []
    for log in logs:
        response = AuditLogResponse.model_validate(log)
        
        if log.user_id:
            user = db.query(User).filter(User.id == log.user_id).first()
            if user:
                response.user_email = user.email
                response.user_name = user.name
        
        if log.client_id:
            client = db.query(Client).filter(Client.id == log.client_id).first()
            if client:
                response.client_name = client.name
        
        results.append(response)
    
    return results


@router.get("/actions/summary", response_model=dict)
def get_action_summary(
    organization_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Get summary of actions (counts by action type)
    
    Useful for dashboards and reporting
    
    TODO: Add authentication
    """
    
    from sqlalchemy import func
    
    query = db.query(
        AuditLog.action,
        func.count(AuditLog.id).label('count')
    )
    
    if organization_id:
        query = query.filter(AuditLog.organization_id == organization_id)
    
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    
    results = query.group_by(AuditLog.action)\
        .order_by(func.count(AuditLog.id).desc())\
        .all()
    
    summary = {
        "total_actions": sum(count for _, count in results),
        "actions": {action: count for action, count in results}
    }
    
    return summary
