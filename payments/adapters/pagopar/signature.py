"""Pagopar webhook token verification.

Contract confirmed against a captured staging callback (2026-09-17):
Pagopar POSTs ``{"resultado": [{..., "token": "<sha1 hex>", ...}],
"respuesta": true}`` and expects the ``resultado`` array echoed back
verbatim as the response body ("Paso 2" of their validation circuit).

The ``token`` field is the signature. Pagopar's scheme family is
``sha1(private_key + suffix)`` (confirmed from pagopar_sdk.auth for
outbound calls), but the exact suffix used for callbacks is not publicly
documented. Verification therefore checks a small set of NAMED candidate
constructions derived from that family and returns which one matched, so
the algorithm can be pinned to a single construction after one observed
staging callback. A match on any candidate requires knowledge of the
merchant's private key, so accepting the set does not weaken the check.
"""

import hashlib
import hmac


def _sha1_hex(raw: str) -> str:
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def candidate_tokens(
    private_key: str, *, hash_pedido: str, numero_pedido: str, monto: str
) -> dict[str, str]:
    """Candidate token constructions, keyed by a stable name for logging."""
    return {
        "priv+hash_pedido": _sha1_hex(f"{private_key}{hash_pedido}"),
        "priv+numero_pedido+monto": _sha1_hex(f"{private_key}{numero_pedido}{monto}"),
        "priv+numero_pedido": _sha1_hex(f"{private_key}{numero_pedido}"),
    }


def verify_token(
    *,
    private_key: str,
    provided_token: str,
    hash_pedido: str,
    numero_pedido: str,
    monto: str,
) -> str | None:
    """Return the name of the matching candidate construction, or None.

    FAIL CLOSED: an empty private key or empty token never matches —
    a candidate computed over an empty key would be reproducible by an
    attacker (review finding W4).
    """
    if not private_key or not provided_token:
        return None
    candidates = candidate_tokens(
        private_key,
        hash_pedido=hash_pedido,
        numero_pedido=numero_pedido,
        monto=monto,
    )
    for name, candidate in candidates.items():
        if hmac.compare_digest(candidate, provided_token):
            return name
    return None
