from datetime import datetime, timedelta, timezone

from commander.db import json
from commander.errors import DomainError
from commander.preferences import resolve, values
from commander.skills import definition


def save(db, owner, data, schedule_id=None):
    from commander.projects import require

    existing = (
        db.one("SELECT * FROM schedules WHERE id=%s AND owner_id=%s", (schedule_id, owner))
        if schedule_id
        else None
    )
    if schedule_id and not existing:
        raise DomainError("Schedule changed or no longer exists", 409)
    project = require(db, owner, data.project_id or (existing["project_id"] if existing else None))
    if existing and existing["project_id"] != project["id"]:
        raise DomainError("A schedule cannot move between projects", 409)
    values = (
        data.skill,
        data.prompt,
        data.timezone,
        data.next_at,
        data.interval_seconds,
        data.paused,
        project["id"],
    )
    if schedule_id:
        row = db.one(
            """UPDATE schedules SET skill=%s,prompt=%s,timezone=%s,next_at=%s,interval_seconds=%s,paused=%s,project_id=%s,revision=revision+1
          WHERE id=%s AND owner_id=%s AND revision=%s RETURNING *""",
            (*values, schedule_id, owner, data.revision),
        )
        if not row:
            raise DomainError("Schedule changed or no longer exists", 409)
        return row
    return db.one(
        "INSERT INTO schedules(skill,prompt,timezone,next_at,interval_seconds,paused,project_id,owner_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
        (*values, owner),
    )


def dispatch_due(db, settings):
    now = datetime.now(timezone.utc)
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT s.* FROM schedules s JOIN owners o ON o.id=s.owner_id
             WHERE NOT s.paused AND s.next_at<=%s AND o.disabled_at IS NULL
             ORDER BY s.next_at LIMIT 50 FOR UPDATE OF s SKIP LOCKED FOR SHARE OF o""",
            (now,),
        ).fetchall()
        for row in rows:
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s,720))", (str(row["owner_id"]),)
            )
            count = conn.execute(
                "SELECT (SELECT count(*) FROM runs WHERE owner_id=%s AND created_at>now()-interval '1 day')+(SELECT count(*) FROM sandbox_jobs WHERE owner_id=%s AND created_at>now()-interval '1 day') AS n",
                (row["owner_id"], row["owner_id"]),
            ).fetchone()["n"]
            from commander.demo_grants import check_admission

            try:
                check_admission(db, row["owner_id"], conn=conn)
            except DomainError:
                conn.execute("UPDATE schedules SET paused=true WHERE id=%s", (row["id"],))
                continue
            effective = resolve(db, settings, row["owner_id"])
            if count >= effective.max_daily_runs:
                continue
            conn.execute(
                """INSERT INTO runs(owner_id,schedule_id,occurrence_at,skill,skill_version,prompt,settings_snapshot,project_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(schedule_id,occurrence_at) DO NOTHING""",
                (
                    row["owner_id"],
                    row["id"],
                    row["next_at"],
                    row["skill"],
                    definition(row["skill"])["hash"],
                    row["prompt"],
                    json(values(effective)),
                    row["project_id"],
                ),
            )
            next_at = None
            if row["interval_seconds"]:
                elapsed = (now - row["next_at"]).total_seconds()
                next_at = row["next_at"] + timedelta(
                    seconds=(int(elapsed // row["interval_seconds"]) + 1) * row["interval_seconds"]
                )
            conn.execute(
                "UPDATE schedules SET last_at=%s,next_at=%s,revision=revision+1 WHERE id=%s",
                (row["next_at"], next_at, row["id"]),
            )
