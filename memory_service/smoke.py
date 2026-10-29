"""Local acceptance with a fresh disposable container, real Mem0 and local E5.

Run from repository root with memory_service/.venv/bin/python -m memory_service.smoke.
The first run needs --download-model; runtime service itself never downloads models.
No existing database, container, volume or application environment is changed.
"""

import argparse
import json
import os
import secrets
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

IMAGE = "docker.io/pgvector/pgvector:0.8.2-pg17-bookworm@sha256:e04af45eb526378554a24ed05b37d9ea56fd623feca9adf264d4f47d875c9a93"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download-model", action="store_true")
    args = parser.parse_args()
    os.environ["HF_HOME"] = str(Path("memory_service/.cache/huggingface").resolve())
    os.environ["MEM0_TELEMETRY"] = "false"
    from memory_service.backend import MODEL, REVISION, Mem0Index

    if args.download_model:
        from sentence_transformers import SentenceTransformer

        SentenceTransformer(MODEL, revision=REVISION, device="cpu", trust_remote_code=False)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import psycopg
    from fastapi.testclient import TestClient
    from psycopg import sql

    from memory_service.app import create_app

    name = "tc-memory-acceptance-" + uuid4().hex[:12]
    password = secrets.token_urlsafe(32)
    service_password = secrets.token_urlsafe(32)
    token = secrets.token_urlsafe(32)
    env = os.environ | {"POSTGRES_PASSWORD": password, "POSTGRES_DB": "memory_index"}
    started = time.monotonic()
    created = False
    try:
        subprocess.run(
            [
                "podman",
                "run",
                "--detach",
                "--rm",
                "--name",
                name,
                "--label",
                "thecommander.disposable=true",
                "--publish",
                "127.0.0.1::5432",
                "--env",
                "POSTGRES_PASSWORD",
                "--env",
                "POSTGRES_DB",
                IMAGE,
            ],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        created = True
        port = (
            subprocess.run(
                ["podman", "port", name, "5432"], check=True, capture_output=True, text=True
            )
            .stdout.strip()
            .rsplit(":", 1)[1]
        )
        for attempt in range(30):
            try:
                with psycopg.connect(
                    host="127.0.0.1",
                    port=port,
                    dbname="memory_index",
                    user="postgres",
                    password=password,
                    connect_timeout=2,
                ) as conn:
                    conn.execute("CREATE EXTENSION vector")
                    conn.execute(
                        sql.SQL("CREATE ROLE memory_index LOGIN PASSWORD {}").format(
                            sql.Literal(service_password)
                        )
                    )
                    conn.execute("GRANT USAGE, CREATE ON SCHEMA public TO memory_index")
                break
            except psycopg.OperationalError:
                time.sleep(1)
        else:
            raise RuntimeError("Disposable database did not become ready")
        os.environ.update(
            {
                "MEMORY_DB_HOST": "127.0.0.1",
                "MEMORY_DB_PORT": port,
                "MEMORY_DB_PASSWORD": service_password,
                "MEMORY_DB_NAME": "memory_index",
            }
        )
        backend = Mem0Index.from_environment()
        headers = {"Authorization": "Bearer " + token}
        owner, project, item = (str(uuid4()) for _ in range(3))
        other = str(uuid4())
        with TestClient(create_app(backend, token)) as client:
            assert client.get("/health", headers=headers).status_code == 200

            def put(who, rev, text):
                return client.post(
                    "/v1/records/upsert",
                    headers=headers,
                    json={
                        "owner_id": who,
                        "project_id": project,
                        "id": item,
                        "revision": rev,
                        "text": text,
                    },
                )

            assert (
                put(
                    owner, 1, "The fictional Project Lantern uses Python for backend development."
                ).status_code
                == 200
            )
            assert (
                put(
                    other, 1, "The fictional Project Lantern uses Java for backend development."
                ).status_code
                == 200
            )
            response = client.post(
                "/v1/search",
                headers=headers,
                json={
                    "owner_id": owner,
                    "project_id": project,
                    "query": "Which programming language does Lantern use?",
                },
            )
            assert response.status_code == 200, response.status_code
            assert response.json()["hits"][0]["id"] == item
            assert len(response.json()["hits"]) == 1
            assert put(owner, 2, "The fictional Project Lantern now uses Rust.").status_code == 200
            assert put(owner, 1, "Stale Python preference").status_code == 409
            assert (
                client.post(
                    "/v1/records/delete",
                    headers=headers,
                    json={"owner_id": owner, "project_id": project, "id": item, "revision": 3},
                ).status_code
                == 200
            )
            assert put(owner, 2, "Late Rust correction").status_code == 409
            assert (
                client.post(
                    "/v1/search",
                    headers=headers,
                    json={
                        "owner_id": owner,
                        "project_id": project,
                        "query": "Lantern programming language",
                    },
                ).json()["hits"]
                == []
            )
            assert (
                put(owner, 4, "Fictional renewed preference for reviewed changes.").status_code
                == 200
            )
            assert put(owner, 5, "word " * 700).json()["truncated"] is True
        print(
            json.dumps(
                {
                    "status": "Locally verified",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "backend": "mem0ai==2.2.1 / pgvector 0.8.2",
                    "model": MODEL,
                    "revision": REVISION,
                    "seconds": round(time.monotonic() - started, 3),
                    "checks": [
                        "authenticated readiness",
                        "real local embedding and hybrid retrieval",
                        "owner filtering",
                        "revision correction",
                        "stale rejection",
                        "tombstone exclusion",
                        "expiry renewal",
                        "disclosed truncation",
                    ],
                    "limitations": "Fictional bounded smoke, not recall@5 benchmark, deployed availability or live provider evidence.",
                },
                indent=2,
            )
        )
    finally:
        if created:
            subprocess.run(["podman", "rm", "--force", name], check=True, capture_output=True)


if __name__ == "__main__":
    main()
