"""Fictional public test form. Run behind the operator's approved HTTPS reverse proxy.

No credentials or application data belong here. No scripts, redirects, external resources,
GET side effects, or automatic retries. SQLite transactions prove one write per operation.
"""

import argparse
import hashlib
import html
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
from uuid import UUID


def state(conn):
    count = conn.execute("SELECT count(*) FROM operations").fetchone()[0]
    return hashlib.sha256(str(count).encode()).hexdigest()


def form(conn):
    return (
        "<!DOCTYPE html><html><head><title>Controlled demo fixture</title></head><body>"
        "<h1>Fictional demo message</h1><p>This form stores fictional test text only.</p>"
        '<form method="post" action="/fixture/commit">'
        '<label for="message">Message</label><input id="message" name="message" maxlength="2000">'
        '<button id="submit" type="submit">Save test message</button></form>'
        '<p>Current revision: <span id="revision">' + state(conn) + "</span></p></body></html>"
    )


def connect(path, initialize=True):
    conn = sqlite3.connect(
        path if initialize else "file:" + str(path) + "?mode=rw",
        uri=not initialize,
        timeout=2,
        isolation_level=None,
    )
    conn.execute("PRAGMA max_page_count=8192")
    if initialize:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, digest TEXT NOT NULL)"
        )
    return conn


def receipt(conn, operation):
    row = conn.execute("SELECT digest FROM operations WHERE id=?", (operation,)).fetchone()
    return {
        "operation_id": operation,
        "status": "committed" if row else "absent",
        "writes": 1 if row else 0,
        "message_sha256": row[0] if row else None,
    }


def commit(conn, operation, expected_state, body):
    UUID(operation)
    data = parse_qs(body, keep_blank_values=True, strict_parsing=True)
    if set(data) != {"message"} or len(data["message"]) != 1 or len(data["message"][0]) > 2000:
        raise ValueError("Invalid fictional message")
    digest = hashlib.sha256(data["message"][0].encode()).hexdigest()
    conn.execute("BEGIN IMMEDIATE")
    try:
        previous = receipt(conn, operation)
        if previous["status"] == "committed":
            if previous["message_sha256"] != digest:
                raise ValueError("Operation payload changed")
            return previous
        if expected_state != state(conn):
            raise ValueError("State changed")
        conn.execute("INSERT INTO operations(id,digest) VALUES (?,?)", (operation, digest))
        return receipt(conn, operation)
    finally:
        # Validation exceptions roll back; never partially apply.
        if conn.in_transaction:
            conn.execute("COMMIT" if __import__("sys").exc_info()[0] is None else "ROLLBACK")


def handler(database):
    class FixtureHandler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(6)

        def log_message(self, *args):
            pass  # Request targets and payloads must not enter public access logs.

        def respond(self, code, text):
            data = text.encode()
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            with connect(database, initialize=False) as conn:
                if self.path == "/fixture":
                    self.respond(200, form(conn))
                elif self.path.startswith("/fixture/state/"):
                    operation = self.path.removeprefix("/fixture/state/")
                    try:
                        UUID(operation)
                    except ValueError:
                        self.respond(404, "Unknown operation")
                        return
                    self.respond(
                        200,
                        '<!DOCTYPE html><html><head><title>Write receipt</title></head><body><h1>Controlled write receipt</h1><pre id="receipt">'
                        + html.escape(json.dumps(receipt(conn, operation)))
                        + "</pre></body></html>",
                    )
                else:
                    self.respond(404, "Unknown reviewed route")

        def do_POST(self):
            if (
                self.path != "/fixture/commit"
                or self.headers.get("Content-Type") != "application/x-www-form-urlencoded"
            ):
                self.respond(403, "Unreviewed request")
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 12000 or self.headers.get("Transfer-Encoding"):
                    raise ValueError()
                body = self.rfile.read(size).decode("utf-8", "strict")
                with connect(database, initialize=False) as conn:
                    result = commit(
                        conn,
                        self.headers.get("X-Commander-Operation-Id", ""),
                        self.headers.get("If-Match", ""),
                        body,
                    )
                self.respond(
                    200,
                    "<html><body><p>Committed fictional message.</p><pre>"
                    + html.escape(json.dumps(result))
                    + "</pre></body></html>",
                )
            except (ValueError, UnicodeError, sqlite3.Error):
                self.respond(409, "Changed request or state; no new write")

    return FixtureHandler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--port", type=int, default=8081)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    with connect(args.database):
        pass
    HTTPServer((args.host, args.port), handler(args.database)).serve_forever()


if __name__ == "__main__":
    main()
