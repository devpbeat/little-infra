"""Thin DocuSeal API client.

Docs: https://www.docuseal.com/docs/api
Auth: header ``X-Auth-Token: <token>``. Base path ``/api``.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("contracts_app")

TIMEOUT = 30


class DocuSealError(RuntimeError):
    pass


def _headers():
    if not settings.DOCUSEAL_API_TOKEN:
        raise DocuSealError(
            "DOCUSEAL_API_TOKEN is not set. Generate an API token in the "
            "DocuSeal UI (Settings -> API) and add it to the environment."
        )
    return {
        "X-Auth-Token": settings.DOCUSEAL_API_TOKEN,
        "Content-Type": "application/json",
    }


def _api_url(path: str) -> str:
    return f"{settings.DOCUSEAL_URL.rstrip('/')}/api/{path.lstrip('/')}"


def create_submission_from_html(name: str, html: str, submitters: list) -> dict:
    """Create a one-off submission directly from an HTML document.

    ``submitters`` is a list of dicts like
    ``{"role": "Client", "email": "a@b.com", "name": "..."}``.
    Returns the parsed JSON response (a list of submitter records).
    """
    payload = {
        "name": name,
        "send_email": False,
        "documents": [{"name": name, "html": html}],
        "submitters": submitters,
    }
    resp = requests.post(
        _api_url("submissions/html"),
        json=payload,
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if not resp.ok:
        logger.error("DocuSeal create submission failed: %s %s",
                     resp.status_code, resp.text[:500])
        raise DocuSealError(
            f"DocuSeal returned {resp.status_code}: {resp.text[:300]}"
        )
    return resp.json()


def get_submission(submission_id) -> dict:
    """Fetch a submission's current state, including signed documents."""
    resp = requests.get(
        _api_url(f"submissions/{submission_id}"),
        headers=_headers(),
        timeout=TIMEOUT,
    )
    if not resp.ok:
        raise DocuSealError(
            f"DocuSeal returned {resp.status_code}: {resp.text[:300]}"
        )
    return resp.json()


def public_signing_url(slug: str) -> str:
    """Build a public signing link from a submitter slug.

    We construct this from the configured public host rather than trusting
    the API's ``embed_src`` host, which reflects the internal call origin.
    """
    return f"{settings.DOCUSEAL_PUBLIC_URL.rstrip('/')}/s/{slug}"


def parse_submitters(response) -> list:
    """Normalise the create-submission response into a list of submitter
    dicts, tolerant of DocuSeal returning either a bare list or an object
    with a ``submitters`` key."""
    if isinstance(response, dict):
        if "submitters" in response and isinstance(response["submitters"], list):
            return response["submitters"]
        return [response]
    if isinstance(response, list):
        return response
    return []
