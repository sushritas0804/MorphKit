from __future__ import annotations

from ...models import Snippet

DEFS = '''class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers[self.header_name] = str(uuid.uuid4())
        return response'''


def build(params: dict, slots: dict) -> Snippet:
    header = params.get("header_name") or "X-Request-ID"
    app_var = slots["app_var"]
    return Snippet(
        imports=[
            "import uuid",
            "from starlette.middleware.base import BaseHTTPMiddleware",
        ],
        defs=[DEFS],
        register=[f'{app_var}.add_middleware(RequestIDMiddleware, header_name="{header}")'],
    )
