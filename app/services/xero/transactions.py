import httpx
from sqlalchemy.orm import Session

from app.models.xero_connection import XeroConnection
from app.services.xero.token_manager import get_valid_access_token


async def fetch_bank_transactions(
    db: Session,
    organization_id: str,
):
    """
    Fetch bank transactions from Xero (read-only).
    """

    # 1️⃣ Get Xero connection
    connection = (
        db.query(XeroConnection)
        .filter(XeroConnection.organization_id == organization_id)
        .first()
    )

    if not connection:
        raise Exception("Xero not connected for this organization")

    # 2️⃣ Get valid access token (auto-refresh)
    access_token = await get_valid_access_token(db, organization_id)

    # 3️⃣ Call Xero API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.xero.com/api.xro/2.0/BankTransactions",
            headers={
                "Authorization": f"Bearer {access_token}",
                "xero-tenant-id": connection.xero_tenant_id,
                "Accept": "application/json",
            },
        )

    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch bank transactions: {response.text}"
        )

    data = response.json()

    return data.get("BankTransactions", [])
