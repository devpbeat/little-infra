"""Pagopar webhook/callback signature verification.

########################################################################
# TODO (BLOCKING RISK — carried forward from Task 0 spike, see
# sdd/payments-microservice/spike-pagopar): the pagopar-sdk package does
# NOT implement webhook verification at all. There is no callback module
# in the SDK to read the real algorithm from.
#
# The implementation below is a BEST-EFFORT GUESS based on the SDK's
# OUTBOUND request-signing scheme (SHA1(private_key + fields), see
# pagopar_sdk.auth.build_token / build_start_transaction_token) applied
# by analogy to inbound callbacks. IT IS NOT CONFIRMED against Pagopar's
# actual callback payload format or documentation.
#
# DO NOT rely on this in production until it has been validated against
# a real or captured Pagopar webhook payload. Slice E (webhook handling)
# must not ship without either:
#   (a) confirming this construction against real Pagopar docs/support, or
#   (b) replacing it with the confirmed algorithm.
########################################################################
"""

import hashlib
import hmac


def compute_candidate_signature(private_key: str, order_id: str, status: str) -> str:
    """Best-effort candidate signature, mirroring the SDK's outbound scheme.

    UNCONFIRMED — see module-level TODO. Do not treat a match here as
    proof of a valid signature until confirmed against real Pagopar docs.
    """
    return hashlib.sha1(f"{private_key}{order_id}{status}".encode()).hexdigest()


def verify_signature(*, private_key: str, order_id: str, status: str, provided_signature: str) -> bool:
    """Compare `provided_signature` against the best-effort candidate.

    UNCONFIRMED — see module-level TODO. This uses constant-time
    comparison to avoid a timing side-channel, but the underlying
    algorithm itself is unverified against Pagopar's real callback spec.
    """
    candidate = compute_candidate_signature(private_key, order_id, status)
    return hmac.compare_digest(candidate, provided_signature)
