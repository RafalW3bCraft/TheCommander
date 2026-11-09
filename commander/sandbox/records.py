"""Append execution evidence independently of a job's mutable lifecycle state."""

import base64
import uuid

from commander.db import json
from commander.sandbox.artifacts import validate_item


def start(db, job, kind):
    identifier = uuid.uuid4()
    return db.one(
        "INSERT INTO sandbox_attempts(id,job_id,owner_id,lease_token,kind,container_name) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (
            identifier,
            job["id"],
            job["owner_id"],
            job["lease_token"],
            kind,
            "commander-job-" + identifier.hex,
        ),
    )["id"]


def finish(db, job, attempt, result, error_code=None):
    receipt = result.get("receipt", {})
    with db.connect() as conn:
        conn.execute(
            "UPDATE sandbox_attempts SET receipt=%s,error_code=%s,finished_at=now() WHERE id=%s AND owner_id=%s",
            (json(receipt), error_code, attempt, job["owner_id"]),
        )
        # Cancellation retains its terminal status but still receives the observed receipt.
        conn.execute(
            "UPDATE sandbox_jobs SET receipt=%s WHERE id=%s AND owner_id=%s AND lease_token=%s",
            (json(receipt), job["id"], job["owner_id"], job["lease_token"]),
        )
    # Evidence commits before validating artifacts, including on malicious output.
    with db.connect() as conn:
        artifacts = result.get("artifacts", [])
        if len(artifacts) > 5:
            from commander.errors import DomainError

            raise DomainError("Sandbox artifact count exceeded", 422, "artifact_rejected")
        for entry in artifacts:
            data = base64.b64decode(entry["data"], validate=True)
            item = validate_item(entry["name"], data)
            conn.execute(
                "INSERT INTO sandbox_artifacts(job_id,owner_id,attempt_id,name,media_type,data,sha256) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (
                    job["id"],
                    job["owner_id"],
                    attempt,
                    item["name"],
                    item["media_type"],
                    data,
                    item["sha256"],
                ),
            )
