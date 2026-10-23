from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import psycopg
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from commander import auth, memory
from commander.contracts import (
    Bootstrap,
    ErrorResponse,
    Login,
    MemoryEdit,
    MemoryInput,
    MemoryView,
    UserView,
)
from commander.db import Database
from commander.errors import DomainError
from commander.settings import Settings


def create_app(settings=None, transport=None):
    settings = settings or Settings()
    db = Database(settings)

    @asynccontextmanager
    async def lifespan(app):
        db.migrate()
        yield

    app = FastAPI(
        title="TheCommander",
        version="0.2.0",
        lifespan=lifespan,
        responses={
            code: {"model": ErrorResponse}
            for code in (400, 401, 403, 404, 409, 413, 422, 429, 502, 503)
        },
    )
    app.state.db = db
    app.state.settings = settings
    app.state.transport = transport

    @app.exception_handler(DomainError)
    async def domain_error(request, exc):
        return JSONResponse(
            {"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic input fields can contain passwords and tokens. Never echo them.
        return JSONResponse(
            {
                "error": {
                    "code": "validation",
                    "message": "Check the submitted fields",
                    "fields": [
                        {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                        for e in exc.errors()
                    ],
                }
            },
            status_code=422,
        )

    @app.exception_handler(psycopg.errors.UniqueViolation)
    async def conflict(request, exc):
        return JSONResponse(
            {"error": {"code": "conflict", "message": "This record already exists"}},
            status_code=409,
        )

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return JSONResponse(
            {
                "error": {
                    "code": "unavailable",
                    "message": "Service unavailable. Check the server and database health.",
                }
            },
            status_code=503,
        )

    @app.middleware("http")
    async def boundaries(request, call_next):
        origin = request.headers.get("origin")
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and origin
            and origin != settings.app_origin
        ):
            return JSONResponse(
                {"error": {"code": "origin", "message": "Origin not allowed"}}, status_code=403
            )
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 65536:
                return JSONResponse(
                    {"error": {"code": "too_large", "message": "Request too large"}},
                    status_code=413,
                )
        request._body = bytes(body)
        if len(body) > 65536:
            return JSONResponse(
                {"error": {"code": "too_large", "message": "Request too large"}}, status_code=413
            )
        response = await call_next(request)
        response.headers.update(
            {
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            }
        )
        if settings.production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    def principal(request: Request):
        row = auth.authenticate(db, request)
        auth.throttle(db, "api:" + str(row["owner_id"]), 300)
        return row["owner_id"]

    def logged_in(response, owner):
        token, result = auth.session(db, owner)
        response.set_cookie(
            "commander_session",
            token,
            httponly=True,
            secure=settings.production,
            samesite="strict",
            max_age=43200,
            path="/",
        )
        return result

    from fastapi import Response

    @app.get("/health/live")
    def health_live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def health_ready():
        db.one("SELECT 1")
        return {"status": "ready"}

    @app.get("/api/auth/status")
    def auth_status():
        return {"bootstrap_required": not bool(db.one("SELECT 1 FROM owners LIMIT 1"))}

    @app.post("/api/auth/bootstrap", response_model=UserView)
    def bootstrap(data: Bootstrap, request: Request, response: Response):
        auth.throttle(db, "login:" + (request.client.host if request.client else "unknown"))
        owner = auth.bootstrap(db, settings, data)
        return logged_in(response, owner)

    @app.post("/api/auth/login", response_model=UserView)
    def login(data: Login, request: Request, response: Response):
        auth.throttle(db, "login:" + (request.client.host if request.client else "unknown"))
        return logged_in(response, auth.login(db, data))

    @app.get("/api/auth/me", response_model=UserView)
    def me(request: Request, owner=Depends(principal)):
        row = auth.authenticate(db, request)
        return {"owner_id": str(owner), "username": row["username"], "csrf": row["csrf"]}

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response, owner=Depends(principal)):
        db.one(
            "DELETE FROM auth_sessions WHERE token_hash=%s RETURNING owner_id",
            (auth.digest(request.cookies.get("commander_session", "")),),
        )
        response.delete_cookie("commander_session", path="/")
        return {"status": "signed_out"}

    @app.get("/api/memory", response_model=list[MemoryView])
    def memories(q: str = "", owner=Depends(principal)):
        return memory.list_memory(db, owner, q[:200])

    @app.get("/api/memory/export", response_model=list[MemoryView])
    def export_memory(owner=Depends(principal)):
        return db.all("SELECT * FROM memories WHERE owner_id=%s ORDER BY observed_at", (owner,))

    @app.post("/api/memory", response_model=MemoryView)
    def add_memory(data: MemoryInput, owner=Depends(principal)):
        return memory.save_memory(db, owner, data)

    @app.put("/api/memory/{item_id}", response_model=MemoryView)
    def edit_memory(item_id: UUID, data: MemoryEdit, owner=Depends(principal)):
        return memory.save_memory(db, owner, data, item_id)

    @app.delete("/api/memory/{item_id}")
    def delete_memory(item_id: UUID, owner=Depends(principal)):
        row = db.one(
            "DELETE FROM memories WHERE id=%s AND owner_id=%s RETURNING id", (item_id, owner)
        )
        if not row:
            raise DomainError("Memory not found", 404)
        return {"status": "deleted"}

    # Feature routes are installed here as the vertical slices are integrated.
    from commander.routes import install_routes

    install_routes(app, db, settings, principal, transport)
    dist = Path(__file__).parent.parent / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index():
            return FileResponse(dist / "index.html")

    return app
