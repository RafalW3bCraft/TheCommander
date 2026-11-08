"""Canonical admission remains authoritative when the derived index is stale/hostile."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from test_workflows import app as workflow_app

from commander import memory
from commander.memory_index import IndexHit, IndexUnavailable

app = workflow_app


class Index:
    hits = []

    def __init__(self):
        self.writes = []

    def search(self, *args, **kwargs):
        return self.hits

    def search_with_status(self, *args, **kwargs):
        return self.search(*args, **kwargs), False

    def upsert(self, *args):
        self.writes.append(("upsert", args))

    def delete(self, *args):
        self.writes.append(("delete", args))


def save(client, key, **fields):
    r = client.post("/api/memory", json={"key": key, "content": key, **fields})
    assert r.status_code == 200, r.text
    return r.json()


def test_index_hints_cannot_restore_expired_deleted_wrong_project_or_revision(app):
    client, _, owner, db = app
    project = client.get("/api/projects").json()[0]["id"]
    other = client.post("/api/projects", json={"name": "Other"}).json()["id"]
    good = save(client, "python retries", project_id=project)
    stale = save(client, "old fact")
    expired = save(
        client, "expired", expires_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    )
    foreign = save(client, "other project", project_id=other)
    deleted = save(client, "deleted")
    assert client.delete("/api/memory/" + deleted["id"]).status_code == 200
    index = Index()
    index.hits = [
        IndexHit(good["id"], 1, 0.9),
        IndexHit(stale["id"], 999, 0.9),
        IndexHit(expired["id"], 1, 0.9),
        IndexHit(foreign["id"], 1, 0.9),
        IndexHit(deleted["id"], 1, 0.9),
        IndexHit(str(uuid4()), 1, 0.9),
    ]
    result = memory.retrieve(db, owner, project, "python", index=index)
    assert [str(r["id"]) for r in result["records"]] == [good["id"]]
    assert result["method"] == "hybrid"


def test_explicit_precedence_applies_before_semantic_ranking(app):
    client, _, owner, db = app
    project = client.get("/api/projects").json()[0]["id"]
    inferred = save(client, "style", kind="inferred", content="old style")
    explicit = save(client, "style", content="new style")
    index = Index()
    index.hits = [IndexHit(inferred["id"], 1, 0.99)]
    result = memory.retrieve(db, owner, project, "style", index=index)
    assert [str(r["id"]) for r in result["records"]] == [explicit["id"]]


def test_outage_is_explicit_and_lexical_context_survives(app):
    client, _, owner, db = app
    row = save(client, "python retries")

    class Down(Index):
        def search(self, *args, **kwargs):
            raise IndexUnavailable("secret internal exception")

    result = memory.retrieve(db, owner, None, "python", index=Down())
    assert result["method"] == "lexical"
    assert result["index_status"] == "degraded"
    assert "secret" not in str(result)
    assert str(result["records"][0]["id"]) == row["id"]


def test_durable_outbox_correction_deletion_and_retry(app, settings):
    from commander.memory_sync import sync_one

    client, _, owner, db = app
    row = save(client, "remember this")
    index = Index()
    assert sync_one(db, index)
    assert index.writes[-1][0] == "upsert"
    assert db.one("SELECT count(*) AS n FROM memory_index_jobs")["n"] == 0
    changed = client.put(
        "/api/memory/" + row["id"],
        json={"key": "remember this", "content": "corrected", "revision": 1},
    )
    assert changed.status_code == 200

    class Down(Index):
        def upsert(self, *args):
            raise IndexUnavailable("private detail")

    assert sync_one(db, Down())
    job = db.one("SELECT * FROM memory_index_jobs")
    assert job["attempts"] == 1 and job["last_error"] == "index_unavailable"
    assert client.delete("/api/memory/" + row["id"]).status_code == 200
    assert sync_one(db, index)
    assert index.writes[-1][0] == "delete"
    assert index.writes[-1][1][-1] == 3
    assert db.one("SELECT count(*) AS n FROM memory_index_jobs")["n"] == 0


def test_search_contract_scope_and_disabled_status(app):
    client, _, owner, db = app
    row = save(client, "canonical only")
    response = client.get("/api/memory/search", params={"q": "canonical"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["index_status"] == "disabled" and body["records"][0]["id"] == row["id"]
    assert (
        client.get(
            "/api/memory/search", params={"q": "canonical", "project_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert client.get("/api/memory/search", params={"q": " "}).status_code == 422


def test_delete_during_index_response_excludes_record(app):
    client, _, owner, db = app
    row = save(client, "remove during recall")

    class Racing(Index):
        def search(self, *args, **kwargs):
            assert client.delete("/api/memory/" + row["id"]).status_code == 200
            return [IndexHit(row["id"], 1, 0.99)]

    assert memory.retrieve(db, owner, None, "remove", index=Racing())["records"] == []


def test_expiry_removal_and_renewal_use_distinct_revisions(app):
    from commander.memory_sync import sync_one

    client, _, owner, db = app
    row = save(
        client,
        "expires later",
        expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    )
    index = Index()
    assert sync_one(db, index)
    # Simulate elapsed time in both canonical/index state without wall-clock sleeps.
    db.one(
        "UPDATE memories SET expires_at=now()-interval '1 second' WHERE id=%s RETURNING id",
        (row["id"],),
    )
    db.one(
        "UPDATE memory_index_state SET expires_at=now()-interval '1 second' WHERE memory_id=%s RETURNING memory_id",
        (row["id"],),
    )
    assert sync_one(db, index)
    assert index.writes[-1][0] == "delete"
    assert index.writes[-1][1][-1] == 1
    assert db.one("SELECT count(*) AS n FROM memory_index_state")["n"] == 0
    assert (
        client.put(
            "/api/memory/" + row["id"],
            json={"key": "expires later", "content": "renewed", "revision": 1},
        ).status_code
        == 200
    )
    assert sync_one(db, index)
    assert index.writes[-1][0] == "upsert" and index.writes[-1][1][3] == 2


def test_correction_during_dispatch_preserves_pending_new_revision(app):
    from commander.memory_sync import sync_one

    client, _, owner, db = app
    row = save(client, "changing")

    class Racing(Index):
        def upsert(self, *args):
            assert (
                client.put(
                    "/api/memory/" + row["id"],
                    json={"key": "changing", "content": "new content", "revision": 1},
                ).status_code
                == 200
            )

    assert sync_one(db, Racing())
    assert db.one("SELECT revision FROM memory_index_jobs")["revision"] == 2
    assert db.one("SELECT count(*) AS n FROM memory_index_state")["n"] == 0
    index = Index()
    assert sync_one(db, index)
    assert index.writes[-1][1][3] == 2
    assert db.one("SELECT revision FROM memory_index_state")["revision"] == 2


def test_foreign_owner_hints_and_prefix_index_diagnostics(app):
    from commander.memory_sync import sync_one

    client, _, owner, db = app
    other = db.one(
        "INSERT INTO owners(username,password_hash) VALUES ('index-other','not-a-login-hash') RETURNING id"
    )
    foreign = db.one(
        "INSERT INTO memories(owner_id,kind,key,content,source) VALUES (%s,'explicit','secret other','secret other','owner entry') RETURNING *",
        (other["id"],),
    )
    index = Index()
    index.hits = [IndexHit(str(foreign["id"]), 1, 0.99)]
    assert memory.retrieve(db, owner, None, "secret", index=index)["records"] == []
    save(client, "long record", content="word " * 1800)
    while sync_one(db, index):
        pass
    status = client.get("/api/memory/index-status").json()
    assert status["truncated"] == 1 and status["pending"] == 0
    assert all(len(call[1][-1]) <= 4000 for call in index.writes if call[0] == "upsert")
