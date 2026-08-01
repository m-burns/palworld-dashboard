from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class PublicRequestGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > 16_384:
                    return JSONResponse({"detail": "Request body too large"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)

        if request.url.path.startswith("/api/"):
            client = request.client.host if request.client else "unknown"
            is_vote = request.method == "POST" and request.url.path.startswith("/api/polls/")
            limit = 10 if is_vote else 180
            key = f"{client}:{'vote' if is_vote else 'api'}"
            if not await self._allow(key, limit):
                return JSONResponse(
                    {"detail": "Too many requests"},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )

        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
            "object-src 'none'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; form-action 'self'"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000"
            )
        return response

    async def _allow(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        async with self._lock:
            if len(self._requests) >= 4_096:
                stale_keys = [
                    candidate
                    for candidate, timestamps in self._requests.items()
                    if not timestamps or timestamps[-1] < now - 60
                ]
                for stale_key in stale_keys:
                    self._requests.pop(stale_key, None)
            if key not in self._requests and len(self._requests) >= 8_192:
                return False
            requests = self._requests[key]
            while requests and requests[0] < now - 60:
                requests.popleft()
            if len(requests) >= limit:
                return False
            requests.append(now)
            return True
