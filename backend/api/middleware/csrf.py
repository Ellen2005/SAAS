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
        # Skip CSRF for safe methods and auth endpoints
        if request.method in SAFE_METHODS:
            return await call_next(request)
        
        path = request.url.path
        if path.startswith(("/api/auth/", "/api/ping", "/api/test-connection")):
            return await call_next(request)
        
        # Check CSRF token
        cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
        header_token = request.headers.get(CSRF_HEADER_NAME)
        
        if not cookie_token or not header_token or cookie_token != header_token:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing or invalid"
            )
        
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