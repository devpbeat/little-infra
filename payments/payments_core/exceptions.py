"""RFC-7807-ish exception handler (design §5): partner apps branch on `code`, not prose."""

from rest_framework.views import exception_handler as drf_exception_handler


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    code = getattr(exc, "default_code", None) or exc.__class__.__name__.lower()
    if isinstance(detail, dict) and "detail" in detail and len(detail) == 1:
        detail_text = detail["detail"]
    elif isinstance(detail, (list, dict)):
        detail_text = str(detail)
    else:
        detail_text = str(detail)

    response.data = {
        "type": f"https://payments.ignitesolutions.click/errors/{code}",
        "title": exc.__class__.__name__,
        "detail": detail_text,
        "code": code,
    }
    return response
