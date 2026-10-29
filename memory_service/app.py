"""Private service with explicit authentication, bounded admission and redacted errors."""

import asyncio
import hmac
import os
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from memory_service.contracts import Record, RevisionedKey, Search


class RevisionConflict(Exception):
    pass


def create_app(backend=None, token=None):
    secret = token or os.environ.get("MEMORY_INDEX_TOKEN", "")
    if len(secret) < 32 or any(c.isspace() for c in secret):
        raise ValueError("MEMORY_INDEX_TOKEN must contain at least 32 non-whitespace characters")
    admission = threading.BoundedSemaphore(4)

    @asynccontextmanager
    async def lifespan(app):
        if app.state.backend is None:
            from memory_service.backend import Mem0Index

            app.state.backend = Mem0Index.from_environment()
        yield
        if hasattr(app.state.backend, "close"):
            app.state.backend.close()

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.backend = backend

    @app.middleware("http")
    async def admission_boundary(request: Request, call_next):
        # Authenticate before reading bodies; never echo credential/input validation values.
        supplied = request.headers.get("authorization", "")
        if not hmac.compare_digest(supplied.encode(), ("Bearer " + secret).encode()):
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        body = bytearray()
        try:
            async with asyncio.timeout(5):
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 32768:
                        return JSONResponse({"detail": "Request too large"}, status_code=413)
        except TimeoutError:
            return JSONResponse({"detail": "Request timeout"}, status_code=408)
        request._body = bytes(body)
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        return JSONResponse({"detail": "Invalid memory request"}, status_code=422)

    def get_backend():
        if not admission.acquire(blocking=False):
            raise HTTPException(429, "Memory service busy", headers={"Retry-After": "1"})
        try:
            if app.state.backend is None:
                raise HTTPException(503, "Memory service not initialized")
            yield app.state.backend
        finally:
            admission.release()

    def invoke(fn, value):
        try:
            return fn(value)
        except RevisionConflict:
            raise HTTPException(409, "Index revision changed") from None
        except Exception:
            raise HTTPException(503, "Derived memory unavailable") from None

    @app.get("/health")
    def health(store=Depends(get_backend)):
        invoke(lambda _: store.health(), None)
        return {"status": "ready", "backend": "mem0-pgvector", "dimensions": 384}

    @app.post("/v1/records/upsert")
    def upsert(record: Record, store=Depends(get_backend)):
        truncated = invoke(store.upsert, record)
        return {"status": "indexed", "truncated": truncated}

    @app.post("/v1/records/delete")
    def delete(record: RevisionedKey, store=Depends(get_backend)):
        invoke(store.delete, record)
        return {"status": "deleted"}

    @app.post("/v1/search")
    def search(query: Search, store=Depends(get_backend)):
        return invoke(store.search, query)

    return app
