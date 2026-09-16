"""drf-spectacular extension so `ApiKeyAuthentication` renders correctly in the
OpenAPI schema instead of showing up as an unrecognized/unauthenticated scheme.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ApiKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "payments_core.auth.ApiKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Format: `Api-Key <prefix>.<secret>`",
        }
