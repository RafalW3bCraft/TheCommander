"""Remove expired private payloads while retaining ownership and receipt tombstones."""


def purge(db, days):
    with db.connect() as conn:
        artifacts = conn.execute(
            "UPDATE sandbox_artifacts SET data=NULL,deleted_at=now() WHERE deleted_at IS NULL AND created_at<now()-(%s*interval '1 day') RETURNING id",
            (days,),
        ).fetchall()
        screenshots = conn.execute(
            """UPDATE sandbox_jobs SET evidence=evidence-'screenshot',approval_snapshot=approval_snapshot-'screenshot'
        WHERE status NOT IN ('queued','running','approved','waiting_approval') AND updated_at<now()-(%s*interval '1 day')
        AND (evidence ? 'screenshot' OR approval_snapshot ? 'screenshot') RETURNING id""",
            (days,),
        ).fetchall()
    return {"artifacts_removed": len(artifacts), "screenshots_removed": len(screenshots)}
