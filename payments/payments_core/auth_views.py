"""Operator (staff) session authentication endpoints for the dashboard.

CSRF choice: the login POST takes JSON credentials in the body and is
CSRF-exempt (there is no session yet to ride, so a cross-site request
cannot act on the victim's behalf). Django sets the session + CSRF
cookies on successful login; DRF's SessionAuthentication then enforces
the CSRF header on every subsequent unsafe request, logout included.
"""

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def post(self, request):
        username = str(request.data.get("username") or "")
        password = str(request.data.get("password") or "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED
            )
        if not user.is_staff:
            return Response(
                {"detail": "Only staff users may log in here."},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response({"username": user.get_username(), "is_staff": True})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.AllowAny]

    # The dashboard calls /me on every load; guaranteeing the CSRF cookie
    # here means later unsafe requests always have a token to send, even
    # for sessions established before a deploy rotated things.
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        user = request.user
        if not (user.is_authenticated and user.is_staff):
            return Response({"detail": "Not authenticated."}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"username": user.get_username(), "is_staff": True})
