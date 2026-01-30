import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.exclusion_rule import ExclusionRule
from app.services.exclusion.engine import apply_exclusion_rules


def upsert_xero_transactions(
    db: Session,
    organization_id: str,
    client_id: str,
    xero_transactions: list[dict],
):
    """
    Upsert Xero BankTransactions into existing transactions table.
    """

    # Load enabled exclusion rules once
    rules = (
        db.query(ExclusionRule)
        .filter(
            ExclusionRule.organization_id == organization_id,
            ExclusionRule.enabled.is_(True),
        )
        .all()
    )

    now = datetime.utcnow()

    for tx in xero_transactions:
        xero_tx_id = tx.get("BankTransactionID")
        if not xero_tx_id:
            continue

        has_attachments = tx.get("HasAttachments", False)

        existing = (
            db.query(Transaction)
            .filter(
                Transaction.organization_id == organization_id,
                Transaction.xero_transaction_id == xero_tx_id,
            )
            .first()
        )

        if not existing:
            # 🆕 INSERT
            new_tx = Transaction(
                id=uuid.uuid4(),
                organization_id=organization_id,
                client_id=client_id,
                xero_transaction_id=xero_tx_id,
                xero_type=tx.get("Type"),
                date=tx.get("Date"),
                amount=tx.get("Total"),
                description=tx.get("Reference") or tx.get("LineAmountTypes"),
                supplier_name=(tx.get("Contact") or {}).get("Name"),
                document_required=not has_attachments,
                document_received=has_attachments,
                excluded=False,
                created_at=now,
                updated_at=now,
            )

            apply_exclusion_rules(new_tx, rules)
            db.add(new_tx)

        else:
            # 🔁 UPDATE (safe fields only)
            existing.xero_type = tx.get("Type")
            existing.date = tx.get("Date")
            existing.amount = tx.get("Total")
            existing.description = tx.get("Reference") or existing.description
            existing.supplier_name = (tx.get("Contact") or {}).get("Name")

            # Recalculate document requirement from Xero
            existing.document_required = not has_attachments

            # Only auto-set document_received if Xero already has attachment
            if has_attachments:
                existing.document_received = True

            existing.updated_at = now

            apply_exclusion_rules(existing, rules)

    db.commit()
