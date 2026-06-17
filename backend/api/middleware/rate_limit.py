"""
Rate Limiting Middleware
========================
Simple in-memory rate limiter for FastAPI.

Uses sliding window algorithm.
Per-IP limits:
  - Auth endpoints: 5 requests per minute
  - API endpoints: 100 requests per minute
  - Admin endpoints: 50 requests per minute
"""

import time
import logging
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter."""
    
    def __init__(self, app, limits: Dict[str, Tuple[int, int]] = None):
        super().__init__(app)
        self.limits = limits or {
            "/api/auth/": (5, 60),      # 5 per minute
            "/api/admin/": (50, 60),    # 50 per minute
            "/api/": (100, 60),         # 100 per minute
        }
        self.clients: Dict[str, list] = defaultdict(list)
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        
        # Find applicable limit
        limit, window = None, None
        for prefix, (max_requests, window_secs) in self.limits.items():
            if path.startswith(prefix):
                limit = max_requests
                window = window_secs
                break
        
        if limit is None:
            return await call_next(request)
        
        # Clean old entries
        now = time.time()
        self.clients[client_ip] = [
            t for t in self.clients[client_ip] if now - t < window
        ]
        
        # Check limit
        if len(self.clients[client_ip]) >= limit:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please try again in {window} seconds.",
                headers={"Retry-After": str(window)},
            )
        
        # Record request
        self.clients[client_ip].append(now)
        
        return await call_next(request)