"""DocuSeal ContractSigner adapter.

Mirrors the conventions of the standalone contracts/ app's DocuSeal client
(X-Auth-Token header, /api base path, HTML submissions, public signing
links built from the configured public host rather than the API's
embed_src). Selected via CONTRACT_SIGNER=adapters.docuseal.signer.DocuSealSigner.
"""

import os

import httpx

from payments_core.ports.contract_signer import (
    ContractSigner,
    EnvelopeRequest,
    EnvelopeResult,
    EnvelopeStatus,
)

TIMEOUT = 30

# DocuSeal submission statuses → port statuses (defensive mapping).
_STATUS_MAP = {
    "completed": EnvelopeStatus.SIGNED,
    "declined": EnvelopeStatus.DECLINED,
    "expired": EnvelopeStatus.VOIDED,
    "archived": EnvelopeStatus.VOIDED,
}


class DocuSealError(RuntimeError):
    pass


def _base_url() -> str:
    url = os.environ.get("DOCUSEAL_URL", "").rstrip("/")
    if not url:
        raise DocuSealError("DOCUSEAL_URL is not configured.")
    return url


def _headers() -> dict:
    token = os.environ.get("DOCUSEAL_API_TOKEN", "")
    if not token:
        raise DocuSealError("DOCUSEAL_API_TOKEN is not configured.")
    return {"X-Auth-Token": token, "Content-Type": "application/json"}


class DocuSealSigner(ContractSigner):
    def create_envelope(self, request: EnvelopeRequest) -> EnvelopeResult:
        payload = {
            "name": request.document_name or request.template_reference,
            "send_email": True,
            "documents": [
                {
                    "name": request.document_name or "Contract",
                    "html": request.document_html,
                }
            ],
            "submitters": [
                {
                    "role": "Client",
                    "name": request.signer_name,
                    "email": request.signer_email,
                }
            ],
        }
        response = httpx.post(
            f"{_base_url()}/api/submissions/html",
            json=payload,
            headers=_headers(),
            timeout=TIMEOUT,
        )
        if response.is_error:
            raise DocuSealError(
                f"DocuSeal returned {response.status_code}: {response.text[:300]}"
            )
        data = response.json()
        submitters = (
            data.get("submitters", [data])
            if isinstance(data, dict)
            else data if isinstance(data, list) else []
        )
        first = submitters[0] if submitters else {}
        submission_id = str(first.get("submission_id") or first.get("id") or "")
        slug = str(first.get("slug") or "")
        public_url = os.environ.get("DOCUSEAL_PUBLIC_URL", _base_url()).rstrip("/")
        return EnvelopeResult(
            envelope_id=submission_id,
            raw=data if isinstance(data, dict) else {"submitters": data},
            signing_url=f"{public_url}/s/{slug}" if slug else "",
        )

    def get_envelope_status(self, envelope_id: str) -> str:
        response = httpx.get(
            f"{_base_url()}/api/submissions/{envelope_id}",
            headers=_headers(),
            timeout=TIMEOUT,
        )
        if response.is_error:
            raise DocuSealError(
                f"DocuSeal returned {response.status_code}: {response.text[:300]}"
            )
        raw_status = str(response.json().get("status") or "").lower()
        return _STATUS_MAP.get(raw_status, EnvelopeStatus.SENT)
