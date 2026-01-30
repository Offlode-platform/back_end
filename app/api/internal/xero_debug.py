from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.dependencies.auth import get_current_user
from app.services.xero.transactions import fetch_bank_transactions
from app.models.user import User

router = APIRouter(prefix="/internal/xero", tags=["Xero Debug"])


@router.get("/bank-transactions")
async def debug_fetch_bank_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organization")

    transactions = await fetch_bank_transactions(
        db=db,
        organization_id=current_user.organization_id,
    )

    return {
        "count": len(transactions),
        "sample": transactions[:3],  # only first 3
    }
