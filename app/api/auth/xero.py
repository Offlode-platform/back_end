from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import urllib.parse
import uuid
import httpx

from app.config import settings
from app.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.models.xero_connection import XeroConnection
from app.models.audit_log import AuditLog
from app.services.xero.state_store import store_oauth_state, consume_oauth_state
from app.services.xero.token_crypto import encrypt_token

router = APIRouter(prefix="/auth/xero", tags=["Xero Auth"])


# ----------------------------
# CONNECT ENDPOINT
# ----------------------------
@router.get("/connect")
def connect_xero(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1️⃣ Ensure user has an organization
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # 2️⃣ Ensure role is allowed
    if current_user.role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # 3️⃣ Generate secure state token
    state = secrets.token_urlsafe(32)

    # 4️⃣ Store state temporarily
    store_oauth_state(
        state=state,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        expires_at=datetime.utcnow() + timedelta(minutes=15),
    )

    # 5️⃣ Build Xero authorization URL
    params = {
        "response_type": "code",
        "client_id": settings.XERO_CLIENT_ID,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "scope": settings.XERO_SCOPES,
        "state": state,
    }

    auth_url = (
        "https://login.xero.com/identity/connect/authorize?"
        + urllib.parse.urlencode(params)
    )

    # 6️⃣ Redirect to Xero
    return RedirectResponse(url=auth_url)


# ----------------------------
# CALLBACK ENDPOINT
# ----------------------------
@router.get("/callback")
async def xero_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    # 1️⃣ Extract query params
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    # 2️⃣ Validate and consume state
    state_data = consume_oauth_state(state)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    user_id = state_data["user_id"]
    organization_id = state_data["organization_id"]

    # 3️⃣ Exchange code for tokens
    token_payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.XERO_REDIRECT_URI,
        "client_id": settings.XERO_CLIENT_ID,
        "client_secret": settings.XERO_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://identity.xero.com/connect/token",
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange token")

    tokens = token_resp.json()

    access_token = encrypt_token(tokens["access_token"])
    refresh_token = encrypt_token(tokens["refresh_token"])
    expires_at = datetime.utcnow() + timedelta(seconds=tokens["expires_in"])

    # 4️⃣ Fetch Xero tenant
    async with httpx.AsyncClient() as client:
        tenants_resp = await client.get(
            "https://api.xero.com/connections",
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
                "Accept": "application/json",
            },
        )

    tenants = tenants_resp.json()
    if not tenants:
        raise HTTPException(status_code=400, detail="No Xero tenant found")

    tenant = tenants[0]  # MVP assumption

    # 5️⃣ Upsert xero_connections
    connection = (
        db.query(XeroConnection)
        .filter(XeroConnection.organization_id == organization_id)
        .first()
    )

    if not connection:
        connection = XeroConnection(
            id=uuid.uuid4(),
            organization_id=organization_id,
            xero_tenant_id=tenant["tenantId"],
            xero_tenant_name=tenant.get("tenantName"),
            access_token_encrypted=access_token,
            refresh_token_encrypted=refresh_token,
            expires_at=expires_at,
            sync_status="connected",
            connected_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(connection)
    else:
        connection.access_token_
