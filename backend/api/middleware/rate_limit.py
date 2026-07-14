"""
Rate Limiting Middleware
========================
Rate limiter for FastAPI with Redis backend and in-memory fallback.

Uses sliding window algorithm.
Per-IP limits:
  - Auth endpoints: 10 requests per minute
  - Admin endpoints: 100 requests per minute
  - API endpoints: 300 requests per minute

Redis-backed mode uses sorted sets for distributed rate limiting.
Falls back to in-memory when Redis is unavailable.
"""

import os
import time
import logging
from collections import defaultdict
from typing import Dict, Optional, Tuple

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding window rate limiter with Redis backend and in-memory fallback."""

    def __init__(self, app, limits: Dict[str, Tuple[int, int]] = None):
        super().__init__(app)
        self.limits = limits or {
            "/api/auth/": (10, 60),
            "/api/nlq": (20, 60),
            "/api/charts/custom": (20, 60),
            "/api/assistant/": (30, 60),
            "/api/analyst/": (30, 60),
            "/api/admin/": (100, 60),
            "/api/": (300, 60),
        }
        self.clients: Dict[str, list] = defaultdict(list)
        self.redis_client: Optional[object] = None
        self._connect_redis()

    def _connect_redis(self) -> None:
        """Attempt to connect to Redis using REDIS_URL env var."""
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            logger.info("REDIS_URL not set, using in-memory rate limiting")
            return

        try:
            import redis.asyncio as aioredis

            self.redis_client = aioredis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
                retry_on_timeout=False,
            )
            logger.info("Redis rate limiter connected to %s", redis_url)
        except ImportError:
            logger.warning(
                "redis package not installed, falling back to in-memory rate limiting"
            )
        except Exception as e:
            logger.warning(
                "Failed to connect to Redis (%s), falling back to in-memory rate limiting",
                e,
            )
            self.redis_client = None

    def _find_limit(self, path: str) -> Optional[Tuple[int, int]]:
        """Find the applicable rate limit for a given path."""
        for prefix, (max_requests, window_secs) in self.limits.items():
            if path.startswith(prefix):
                return max_requests, window_secs
        return None

    # ------------------------------------------------------------------
    # Redis-backed sliding window
    # ------------------------------------------------------------------

    async def _check_redis(
        self, key: str, limit: int, window: int
    ) -> Optional[int]:
        """Check rate limit using Redis sorted sets.

        Returns the number of allowed remaining requests, or None if Redis
        is unavailable (caller should fall back to in-memory).
        """
        try:
            now = time.time()
            window_start = now - window

            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, "-inf", window_start)
            pipe.zadd(key, {f"{now}": now})
            pipe.zcard(key)
            pipe.expire(key, window + 10)
            _, _, count, _ = await pipe.execute()

            if count > limit:
                # Remove the request we just added since it's over the limit
                await self.redis_client.zrem(key, f"{now}")
                return None

            return limit - count
        except Exception as e:
            logger.error("Redis rate limit check failed: %s", e)
            # Invalidate so next call attempts reconnection or falls back
            self.redis_client = None
            return None

    # ------------------------------------------------------------------
    # In-memory sliding window (fallback)
    # ------------------------------------------------------------------

    def _check_in_memory(
        self, client_ip: str, path: str, limit: int, window: int
    ) -> bool:
        """Check rate limit using in-memory sliding window.

        Returns True if the request is allowed, False if over limit.
        """
        now = time.time()
        key = f"{client_ip}:{path}"
        self.clients[key] = [t for t in self.clients[key] if now - t < window]

        # Evict stale keys when dict grows too large (every 10000 entries)
        if len(self.clients) > 10000:
            cutoff = now - window * 2
            stale_keys = [k for k, v in self.clients.items() if not v or max(v) < cutoff]
            for k in stale_keys[:len(stale_keys) // 2]:
                del self.clients[k]

        if len(self.clients[key]) >= limit:
            return False

        self.clients[key].append(now)
        return True

    # ------------------------------------------------------------------
    # Middleware dispatch
    # ------------------------------------------------------------------

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Skip rate limiting for SSE/stream endpoints (long-lived connections)
        if path.startswith("/api/realtime/stream"):
            return await call_next(request)

        # Find applicable limit
        result = self._find_limit(path)
        if result is None:
            return await call_next(request)

        limit, window = result

        # Try Redis first
        if self.redis_client is not None:
            key = f"ratelimit:{client_ip}:{path}"
            remaining = await self._check_redis(key, limit, window)
            if remaining is not None:
                logger.debug(
                    "Rate limit OK for %s on %s (%d remaining)",
                    client_ip, path, remaining,
                )
                return await call_next(request)
            # remaining is None => either over limit or Redis failed

            # If Redis is still connected, we exceeded the limit
            if self.redis_client is not None:
                logger.warning(
                    "Rate limit exceeded for %s on %s (Redis)", client_ip, path
                )
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Please try again in {window} seconds.",
                    headers={"Retry-After": str(window)},
                )

            # Redis failed mid-request; fall through to in-memory
            logger.warning("Redis unavailable, falling back to in-memory for this request")

        # In-memory fallback
        if not self._check_in_memory(client_ip, path, limit, window):
            logger.warning("Rate limit exceeded for %s on %s (in-memory)", client_ip, path)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please try again in {window} seconds.",
                headers={"Retry-After": str(window)},
            )

        return await call_next(request)
