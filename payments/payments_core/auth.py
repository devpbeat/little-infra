"""API-key authentication and per-app scoping (design §5, spec: client-onboarding).

Every non-webhook request MUST authenticate via `Authorization: Api-Key <prefix>.<secret>`
and every view MUST scope its queryset to the authenticated app. `ScopedByAppMixin` is
default-deny: a viewset that forgets to filter by `request.app` returns nothing rather
than leaking another tenant's rows.
"""

from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from rest_framework import authentication, exceptions, permissions

from apps.apps_registry.models import ApiKey

# Only write `last_used_at` if it is older than this, so a hot polling client
# (e.g. GET /entitlement) does not generate a write on every single request.
LAST_USED_THROTTLE_SECONDS = 60


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Authenticate requests using `Authorization: Api-Key <prefix>.<secret>`.

    On success, sets `request.app` to the resolved `ConsumingApp` and returns
    `(AnonymousUser(), api_key)` — this service has no end-user auth model, so
    `request.user` is always anonymous; `request.app` is the real tenant scope.
    """

    keyword = "Api-Key"
    www_authenticate_realm = "api"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None

        parts = header.split(" ", 1)
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        credential = parts[1].strip()
        if "." not in credential:
            raise exceptions.AuthenticationFailed("Malformed API key.")

        prefix, secret = credential.split(".", 1)

        try:
            api_key = ApiKey.objects.select_related("app").get(prefix=prefix)
        except ApiKey.DoesNotExist as exc:
            raise exceptions.AuthenticationFailed("Invalid API key.") from exc

        if not check_password(secret, api_key.hashed_secret):
            raise exceptions.AuthenticationFailed("Invalid API key.")

        if not api_key.is_active or api_key.revoked_at is not None:
            raise exceptions.AuthenticationFailed("API key has been revoked.")

        if not api_key.app.is_active:
            raise exceptions.AuthenticationFailed("App is inactive.")

        self._touch_last_used(api_key)

        request.app = api_key.app
        return (AnonymousUser(), api_key)

    def authenticate_header(self, request):
        return self.keyword

    @staticmethod
    def _touch_last_used(api_key: ApiKey) -> None:
        now = timezone.now()
        if api_key.last_used_at is not None:
            age = (now - api_key.last_used_at).total_seconds()
            if age < LAST_USED_THROTTLE_SECONDS:
                return
        api_key.last_used_at = now
        api_key.save(update_fields=["last_used_at"])


def _is_staff_session(request) -> bool:
    """True when the request authenticated as a staff user via session."""
    user = getattr(request, "user", None)
    return bool(user is not None and user.is_authenticated and user.is_staff)


class IsAuthenticatedApp(permissions.BasePermission):
    """Permission companion to `ApiKeyAuthentication`.

    DRF's stock `IsAuthenticated` checks `request.user.is_authenticated`, but
    API-key requests carry no end user — `ApiKeyAuthentication` always returns
    `AnonymousUser()`, whose `is_authenticated` is unconditionally `False`.
    The "authenticated" signal for machines is `request.app` being set.

    A STAFF session (the operator dashboard login) also passes: admins can
    read across apps. App-context-only actions (signup, payment initiation)
    must additionally check `request.app` themselves.
    """

    def has_permission(self, request, view) -> bool:
        return getattr(request, "app", None) is not None or _is_staff_session(request)


class IsAuthenticatedAppOnly(permissions.BasePermission):
    """Only an API-key-authenticated app may act — staff sessions get 403.

    Used by write actions that create billing state for a specific app
    (signup, payment initiation): an admin has no app context, so allowing
    it would create orphaned or misattributed records.
    """

    message = "This action requires an app API key; admin sessions cannot perform it."

    def has_permission(self, request, view) -> bool:
        return getattr(request, "app", None) is not None


class ScopedByAppMixin:
    """Force every queryset through `.filter(**{app_scope_field: request.app})`.

    Default-deny: if `request.app` is not set (authentication did not run, or
    ran against a view that should not have `request.app` at all — should
    never happen behind `ApiKeyAuthentication`), returns an empty queryset
    instead of the unfiltered one. This is the fitness property the
    cross-tenant isolation test in `tests/test_auth_scoping.py` asserts.

    `app_scope_field` defaults to `"app"` (direct FK, e.g. `Customer`) but
    models one hop away from `ConsumingApp` (e.g. `Contract`, `Subscription`,
    which only have a `customer` FK) must override it to `"customer__app"`.
    """

    app_scope_field = "app"

    def get_queryset(self):
        queryset = super().get_queryset()
        app = getattr(self.request, "app", None)
        if app is None:
            # Staff sessions (operator dashboard) read across all apps;
            # everything else stays default-deny.
            if _is_staff_session(self.request):
                return queryset
            return queryset.none()
        return queryset.filter(**{self.app_scope_field: app})
