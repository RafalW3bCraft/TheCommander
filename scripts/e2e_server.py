"""Explicit offline browser-test server; never part of production packaging."""

import atexit
import json
import os
import threading
import uuid
from pathlib import Path

import httpx
import psycopg
from cryptography.fernet import Fernet
from psycopg import sql

from commander.api import create_app
from commander.auth import hasher
from commander.db import Database
from commander.settings import Settings
from commander.worker import Worker

schema = "test_e2e_" + uuid.uuid4().hex
settings = Settings(
    _env_file=None,
    database_url=os.getenv(
        "TEST_DATABASE_URL", "postgresql://thecommander@127.0.0.1:5433/thecommander_db"
    ),
    database_schema=schema,
    encryption_key=Fernet.generate_key().decode(),
    bootstrap_token="test-only-bootstrap-token-not-used-in-production",
    workspace_root=Path(".runtime") / schema,
    app_origin="http://127.0.0.1:8010",
)
db = Database(settings)
db.migrate()
db.one(
    "INSERT INTO owners(username,password_hash) VALUES (%s,%s) RETURNING id",
    ("browser-owner", hasher.hash("fictional-browser-password")),
)
issues = []


def vendor(request):
    body = json.loads(request.content) if request.content else {}
    path = request.url.path
    if path.endswith("/models"):
        return httpx.Response(200, json={"data": [{"id": settings.nebius_model}]})
    if path.endswith("/chat/completions"):
        tools = [t["function"]["name"] for t in body.get("tools", [])]
        research = "propose_issue" in tools and "save_note" not in tools
        if research:
            message = {
                "tool_calls": [
                    {
                        "id": "test-call",
                        "type": "function",
                        "function": {
                            "name": "propose_issue",
                            "arguments": json.dumps(
                                {
                                    "title": "Improve retry safety",
                                    "body": "Use bounded retries. Evidence: https://docs.python.org/3/",
                                }
                            ),
                        },
                    }
                ]
            }
        else:
            message = {
                "content": "Offline browser fixture: review the retry tests and document the next step."
            }
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": message, "finish_reason": "tool_calls" if research else "stop"}
                ],
                "usage": {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50},
            },
        )
    if path == "/search":
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://docs.python.org/3/",
                        "title": "Python documentation",
                        "content": "Explicit error handling.",
                    }
                ]
            },
        )
    if path.endswith("/issues") and request.method == "POST":
        issue = {
            "number": len(issues) + 1,
            "title": body["title"],
            "body": body["body"],
            "html_url": f"https://github.com/fictional/browser/issues/{len(issues) + 1}",
        }
        issues.append(issue)
        return httpx.Response(201, json=issue)
    if "/issues/" in path:
        return httpx.Response(200, json=issues[-1])
    if path.endswith("/issues"):
        return httpx.Response(200, json=issues)
    return httpx.Response(200, json={"full_name": "fictional/browser"})


transport = httpx.MockTransport(vendor)
app = create_app(settings, transport)
stop = threading.Event()


# A real background worker loop, independent of browser requests. The same
# process hosts the test transport; production runs a separate worker process.
def loop():
    worker = Worker(settings, transport)
    while not stop.wait(0.5):
        worker.tick()


threading.Thread(target=loop, daemon=True).start()


def cleanup():
    stop.set()
    with psycopg.connect(settings.database_url) as conn:
        conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))


atexit.register(cleanup)
