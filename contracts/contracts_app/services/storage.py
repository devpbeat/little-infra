"""MinIO (S3-compatible) storage for archiving signed contract PDFs."""
import logging

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger("contracts_app")


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    """Create the target bucket if it does not exist. Idempotent."""
    client = _client()
    try:
        client.head_bucket(Bucket=settings.MINIO_BUCKET)
        return
    except ClientError:
        pass
    try:
        client.create_bucket(Bucket=settings.MINIO_BUCKET)
        logger.info("Created MinIO bucket %s", settings.MINIO_BUCKET)
    except ClientError as exc:
        # Racy create or already-owned: tolerate.
        code = exc.response.get("Error", {}).get("Code", "")
        if code not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            raise


def upload_pdf(key: str, data: bytes) -> str:
    """Upload PDF bytes and return the object key."""
    ensure_bucket()
    _client().put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=key,
        Body=data,
        ContentType="application/pdf",
    )
    return key


def presigned_url(key: str, expires: int = 3600) -> str:
    """Return a time-limited download URL, rewritten to the public host so
    the link works from a browser (the client signs against the internal
    endpoint, which isn't reachable externally)."""
    url = _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.MINIO_BUCKET, "Key": key},
        ExpiresIn=expires,
    )
    internal = settings.MINIO_ENDPOINT.rstrip("/")
    public = settings.MINIO_PUBLIC_ENDPOINT.rstrip("/")
    return url.replace(internal, public, 1)
