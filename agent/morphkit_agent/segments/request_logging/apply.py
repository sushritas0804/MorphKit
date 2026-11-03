from __future__ import annotations

from ...models import Snippet

DEFS = '''class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger_name: str = "morphkit.requests") -> None:
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        self.logger.info(
            "%s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response'''


def build(params: dict, slots: dict) -> Snippet:
    logger_name = params.get("logger_name") or "morphkit.requests"
    app_var = slots["app_var"]
    return Snippet(
        imports=[
            "import logging",
            "import time",
            "from starlette.middleware.base import BaseHTTPMiddleware",
        ],
        defs=[DEFS],
        register=[
            f'{app_var}.add_middleware(RequestLoggingMiddleware, logger_name="{logger_name}")'
        ],
    )
