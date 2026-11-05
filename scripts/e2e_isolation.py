"""Client isolation for the disposable browser-test app ONLY.

Never register this middleware in commander.api: an untrusted client must not
choose its production rate-limit identity. Each Playwright test models a fresh
client while still exercising the real authentication and rate-limit code.
"""

from uuid import UUID


async def isolate_client(request, call_next):
    value = request.headers.get("X-E2E-Client")
    if value:
        try:
            identity = UUID(value).hex
        except ValueError:
            pass
        else:
            request.scope["client"] = ("e2e:" + identity, 0)
    return await call_next(request)
