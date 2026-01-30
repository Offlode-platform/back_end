from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies.auth import get_current_user
from app.models.user import User
from app.services.xero.transactions import fetch_bank_transactions
from app.services.xero.transaction_sync import upsert_xero_transactions

router = APIRouter(prefix="/internal/xero", tags=["Xero Debug"])


@router.post("/sync-transactions")
async def debug_sync_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    # ⚠️ TEMP: assume single client per org (MVP)
    client_id = db.execute(
        """
        SELECT id FROM clients
        WHERE organization_id = :org_id
        LIMIT 1
        """,
        {"org_id": current_user.organization_id},
    ).scalar()

    if not client_id:
        raise HTTPException(status_code=400, detail="No client found for org")

    xero_transactions = await fetch_bank_transactions(
        db=db,
        organization_id=current_user.organization_id,
    )

    upsert_xero_transactions(
        db=db,
        organization_id=current_user.organization_id,
        client_id=client_id,
        xero_transactions=xero_transactions,
    )

    return {
        "fetched": len(xero_transactions),
        "status": "sync completed",
    }
