from __future__ import annotations

from ...models import Snippet

DEFS = '''class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 60) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60.0
        # shortcut: unbounded per-client map, add eviction or Redis before production use
        self.hits = {}

    async def dispatch(self, request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start, count = self.hits.get(client, (now, 0))
        if now - window_start >= self.window_seconds:
            window_start, count = now, 0
        count += 1
        self.hits[client] = (window_start, count)
        if count > self.requests_per_minute:
            return JSONResponse(
                {"detail": "rate limit exceeded"},
                status_code=429,
                headers={"Retry-After": str(int(self.window_seconds))},
            )
        return await call_next(request)'''


def build(params: dict, slots: dict) -> Snippet:
    limit = params.get("requests_per_minute") or 60
    app_var = slots["app_var"]
    return Snippet(
        imports=[
            "import time",
            "from fastapi.responses import JSONResponse",
            "from starlette.middleware.base import BaseHTTPMiddleware",
        ],
        defs=[DEFS],
        register=[f"{app_var}.add_middleware(RateLimitMiddleware, requests_per_minute={limit})"],
    )
