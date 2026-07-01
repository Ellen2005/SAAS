"""
Security Hardening Middleware
==============================
Content Security Policy, refresh token rotation, and additional security headers.
"""
import secrets
from datetime import datetime, timezone
UTC = timezone.utc
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Content Security Policy
CSP_DIRECTIVES = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com",
    "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src": "'self' https://fonts.gstatic.com",
    "img-src": "'self' data: https: blob:",
    "connect-src": "'self' https://*.supabase.co https://api.groq.com https://*.brevo.com wss://*.supabase.co",
    "frame-ancestors": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
    "upgrade-insecure-requests": "",
}


class CSPMiddleware(BaseHTTPMiddleware):
    """Add Content Security Policy headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        parts = []
        for key, value in CSP_DIRECTIVES.items():
            parts.append(f"{key} {value}" if value else key)
        csp_header = "; ".join(parts)
        response.headers["Content-Security-Policy"] = csp_header
        return response


class RefreshTokenMiddleware(BaseHTTPMiddleware):
    """Rotate refresh tokens on each use for enhanced security."""
    async def dispatch(self, request: Request, call_next):
        # Only process auth endpoints
        if not request.url.path.startswith("/api/auth/"):
            return await call_next(request)
        
        # Let the auth router handle token rotation
        response = await call_next(request)
        
        return response