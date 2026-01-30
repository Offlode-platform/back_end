from typing import List

from app.models.transaction import Transaction
from app.models.exclusion_rule import ExclusionRule


def apply_exclusion_rules(
    transaction: Transaction,
    rules: List[ExclusionRule],
) -> bool:
    """
    Apply exclusion rules to a transaction.
    Returns True if transaction was excluded.
    """

    for rule in rules:
        if not rule.is_active:
            continue

        if rule.rule_type == "supplier_name":
            value = transaction.supplier_name
        elif rule.rule_type == "description":
            value = transaction.description
        else:
            continue

        if rule.matches(value):
            transaction.excluded = True
            transaction.document_required = False
            transaction.exclusion_reason = rule.reason or "Auto-excluded"
            return True

    return False
