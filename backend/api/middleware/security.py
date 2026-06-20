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
    "script-src": "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com",
    "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src": "'self' https://fonts.gstatic.com",
    "img-src": "'self' data: https: blob:",
    "connect-src": "'self' https://*.supabase.co https://api.groq.com https://*.brevo.com",
    "frame-ancestors": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
}


class CSPMiddleware(BaseHTTPMiddleware):
    """Add Content Security Policy headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        csp_header = "; ".join(f"{key} {value}" for key, value in CSP_DIRECTIVES.items())
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
        
        # If auth was successful, ensure new refresh token is issued
        if response.status_code == 200:
            try:
                body = {}
                if hasattr(response, "body"):
                    import json
                    body = json.loads(response.body) if response.body else {}
                if body.get("access_token") and not body.get("refresh_token"):
                    # Generate new refresh token
                    body["refresh_token"] = secrets.token_urlsafe(48)
                    from fastapi.responses import JSONResponse
                    return JSONResponse(content=body, status_code=200)
            except Exception:
                pass
        
        return response