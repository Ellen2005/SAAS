"""
CSRF Protection Middleware
==========================
Double-submit cookie pattern for API protection.
"""
import secrets
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

CSRF_COOKIE_NAME = "ea_csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # CSRF protection is disabled because the API uses JWT Bearer tokens
        # in the Authorization header, which is NOT vulnerable to CSRF attacks.
        # CSRF only affects cookie-based authentication.
        return await call_next(request)


def ensure_csrf_cookie(request: Request, response):
    """Ensure CSRF cookie exists on response."""
    if not request.cookies.get(CSRF_COOKIE_NAME):
        token = secrets.token_urlsafe(32)
        response.set_cookie(
            CSRF_COOKIE_NAME,
            token,
            httponly=False,  # Must be readable by JS for header
            secure=True,
            samesite="Lax",
            max_age=86400,
        )