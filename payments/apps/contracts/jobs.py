"""In-process background runner for AI generation jobs.

A gunicorn sync worker handles one request at a time, but a daemon thread
it spawns keeps running after the request returns and frees the worker
immediately — so the HTTP round-trip no longer waits on the (30-90s)
Claude call, and the request never trips the gunicorn/nginx timeouts.

Deliberately no Celery/broker: template generation is admin-only and
rare, so an in-process thread preserves the single-service deployment.
Tradeoff: if the worker is recycled mid-run the job stays `running`
(the dashboard offers a retry); acceptable for this workload.
"""

import threading

from django.conf import settings
from django.db import close_old_connections

from .models import ContractTemplate, GenerationJob


def _run(job_id: int, deal_type: str, build_body) -> None:
    """Run the (already-bound) generator and record the result on the job."""
    try:
        body = build_body()
        template = ContractTemplate.objects.create(
            name=GenerationJob.objects.get(pk=job_id).name,
            deal_type=deal_type,
            body=body,
            is_approved=False,
        )
        GenerationJob.objects.filter(pk=job_id).update(
            status=GenerationJob.Status.DONE, result_template=template
        )
    except Exception as exc:  # surface the reason to the polling dashboard
        GenerationJob.objects.filter(pk=job_id).update(
            status=GenerationJob.Status.FAILED, error=str(exc)[:2000]
        )


def _run_in_thread(job_id: int, deal_type: str, build_body) -> None:
    try:
        _run(job_id, deal_type, build_body)
    finally:
        # Django connections are thread-local; release this thread's one.
        close_old_connections()


def start_generation_job(*, kind: str, name: str, deal_type: str, build_body) -> GenerationJob:
    """Create a RUNNING job and hand the actual work to a daemon thread.

    `build_body` is a zero-arg callable capturing whatever inputs the
    generator needs (already read from the request, since the thread must
    not touch request/file objects that close when the response is sent).
    """
    job = GenerationJob.objects.create(kind=kind, name=name)
    if getattr(settings, "GENERATION_JOBS_SYNC", False):
        # Tests / management contexts: run inline so the result is
        # deterministic (no real thread, no polling race).
        _run(job.pk, deal_type, build_body)
        job.refresh_from_db()
        return job
    thread = threading.Thread(
        target=_run_in_thread, args=(job.pk, deal_type, build_body), daemon=True
    )
    thread.start()
    return job
