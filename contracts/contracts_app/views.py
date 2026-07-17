"""HTTP endpoints: health check + DocuSeal completion webhook."""
import json
import logging

import requests
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Contract
from .services import docuseal, storage

logger = logging.getLogger("contracts_app")

COMPLETION_EVENTS = {"submission.completed", "form.completed"}


@require_GET
def healthz(request):
    return HttpResponse("ok", content_type="text/plain")


def _authorized(request) -> bool:
    """Validate the shared webhook secret (skipped if none configured)."""
    expected = settings.DOCUSEAL_WEBHOOK_SECRET
    if not expected:
        return True
    provided = (
        request.headers.get("X-Docuseal-Secret")
        or request.headers.get("X-Webhook-Secret")
        or request.GET.get("secret", "")
    )
    return bool(provided) and constant_time_compare(provided, expected)


def _extract_submission_id(data: dict):
    """The completion payload may be a submission or a submitter record."""
    if not isinstance(data, dict):
        return None
    return (
        data.get("submission_id")
        or (data.get("submission") or {}).get("id")
        or data.get("id")
    )


def _download_signed_pdf(submission: dict) -> tuple[str, bytes] | None:
    """Return (filename, bytes) for the completed submission's PDF."""
    url = submission.get("combined_document_url")
    documents = submission.get("documents") or []
    if not url and documents:
        url = documents[0].get("url")
    if not url:
        return None
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    name = "contract.pdf"
    if documents and documents[0].get("name"):
        name = f"{documents[0]['name']}.pdf"
    return name, resp.content


@csrf_exempt
@require_POST
def docuseal_webhook(request):
    if not _authorized(request):
        logger.warning("Rejected DocuSeal webhook: bad/absent secret")
        return HttpResponseForbidden("forbidden")

    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    event = payload.get("event_type") or payload.get("event")
    data = payload.get("data") or payload

    if event not in COMPLETION_EVENTS:
        # Acknowledge non-completion events without doing work.
        return JsonResponse({"status": "ignored", "event": event})

    submission_id = _extract_submission_id(data)
    if submission_id is None:
        logger.warning("Completion webhook without a submission id: %s", data)
        return JsonResponse({"status": "no-submission-id"}, status=202)

    try:
        contract = Contract.objects.get(
            docuseal_submission_id=str(submission_id)
        )
    except Contract.DoesNotExist:
        logger.info("No contract for DocuSeal submission %s", submission_id)
        return JsonResponse({"status": "unknown-submission"}, status=202)

    try:
        submission = docuseal.get_submission(submission_id)
        # DocuSeal marks a submission complete only when every submitter signed.
        if submission.get("status") and submission["status"] != "completed":
            contract.status = Contract.Status.VIEWED
            contract.save(update_fields=["status", "updated_at"])
            return JsonResponse({"status": "pending-signers"})

        pdf = _download_signed_pdf(submission)
        if pdf:
            filename, content = pdf
            key = f"{contract.pk}/{filename}"
            contract.signed_pdf_object = storage.upload_pdf(key, content)

        contract.status = Contract.Status.COMPLETED
        contract.completed_at = timezone.now()
        contract.save()
    except Exception:  # noqa: BLE001 - log and 500 so DocuSeal retries
        logger.exception("Failed to archive submission %s", submission_id)
        return JsonResponse({"error": "processing failed"}, status=500)

    return JsonResponse({"status": "archived", "contract": contract.pk})
