"""PYG money helpers.

Paraguayan Guaraní (PYG) has no decimal subunit in circulation, so amounts
are stored and manipulated as plain integers everywhere in this codebase.
Never introduce Decimal or float for PYG amounts.
"""


def is_valid_pyg_amount(amount: int) -> bool:
    """Return True if `amount` is a valid positive PYG integer amount."""
    return isinstance(amount, int) and not isinstance(amount, bool) and amount > 0
