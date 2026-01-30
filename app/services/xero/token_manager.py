from datetime import datetime, timedelta
import httpx

from sqlalchemy.orm import Session
from app.config import settings
from app.models.xero_connection import XeroConnection
from app.services.xero.token_crypto import decrypt_token, encrypt_token


async def get_valid_access_token(
    db: Session,
    organization_id,
) -> str:
    """
    Returns a valid Xero access token.
    Automatically refreshes if expired.
    """

    connection = (
        db.query(XeroConnection)
        .filter(XeroConnection.organization_id == organization_id)
        .first()
    )

    if not connection:
        raise Exception("No Xero connection found")

    # Token still valid (buffer of 2 minutes)
    if connection.expires_at > datetime.utcnow() + timedelta(minutes=2):
        return decrypt_token(connection.access_token_encrypted)

    # 🔄 Refresh token
    refresh_token = decrypt_token(connection.refresh_token_encrypted)

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": settings.XERO_CLIENT_ID,
        "client_secret": settings.XERO_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://identity.xero.com/connect/token",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        connection.sync_status = "revoked"
        db.commit()
        raise Exception("Failed to refresh Xero token")

    tokens = resp.json()

    # 🔁 Xero rotates refresh tokens
    connection.access_token_encrypted = encrypt_token(tokens["access_token"])
    connection.refresh_token_encrypted = encrypt_token(tokens["refresh_token"])
    connection.expires_at = datetime.utcnow() + timedelta(
        seconds=tokens["expires_in"]
    )
    connection.sync_status = "connected"

    db.commit()

    return decrypt_token(connection.access_token_encrypted)
