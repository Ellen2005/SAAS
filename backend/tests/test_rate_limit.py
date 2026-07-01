import time
import pytest
from unittest.mock import MagicMock
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from api.middleware.rate_limit import RateLimitMiddleware


class TestRateLimitMiddleware:
    def test_rate_limit_allows_within_window(self, client):
        for _ in range(5):
            response = client.get("/api/ping")
            assert response.status_code == 200

    def test_rate_limit_blocks_exceeded(self):
        limiter = RateLimitMiddleware.__new__(RateLimitMiddleware)
        limiter.limits = {"/api/": (3, 60)}
        limiter.clients = {}
        limiter.redis_client = None

        client_ip = "testclient"
        path = "/api/test"
        key = f"{client_ip}:{path}"
        limiter.clients[key] = [time.time() for _ in range(3)]

        mock_request = MagicMock()
        mock_request.client.host = client_ip
        mock_request.url.path = path

        async def mock_call_next(req):
            return MagicMock(status_code=200)

        import asyncio
        loop = asyncio.new_event_loop()
        try:
            with pytest.raises(HTTPException) as exc_info:
                loop.run_until_complete(limiter.dispatch(mock_request, mock_call_next))
            assert exc_info.value.status_code == 429
        finally:
            loop.close()

    def test_rate_limit_skips_sse(self):
        limiter = RateLimitMiddleware.__new__(RateLimitMiddleware)
        limiter.clients = {}
        limiter.limits = {"/api/": (2, 60)}
        limiter.redis_client = None

        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.url.path = "/api/realtime/stream"

        import asyncio

        async def mock_call_next(req):
            return MagicMock(status_code=200)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                limiter.dispatch(mock_request, mock_call_next)
            )
            assert result.status_code == 200
        finally:
            loop.close()
