import logging
import signal
import threading
import uuid

from commander.db import Database
from commander.engine import Engine
from commander.errors import DomainError
from commander.runs import event
from commander.schedules import dispatch_due
from commander.settings import Settings

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.db = Database(settings)
        self.id = str(uuid.uuid4())
        self.engine = Engine(self.db, settings, transport)

    def heartbeat(self):
        self.db.one(
            "INSERT INTO worker_heartbeats(id) VALUES (%s) ON CONFLICT(id) DO UPDATE SET seen_at=now() RETURNING id",
            (self.id,),
        )

    def recover(self):
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs WHERE status='running' AND lease_until<now() FOR UPDATE SKIP LOCKED"
            ).fetchall()
            for row in rows:
                writes = conn.execute(
                    "SELECT 1 FROM actions WHERE run_id=%s AND status IN ('executing','uncertain')",
                    (row["id"],),
                ).fetchone()
                notes = conn.execute(
                    "SELECT 1 FROM events WHERE run_id=%s AND kind='note_intent'", (row["id"],)
                ).fetchone()
                proposed = conn.execute(
                    "SELECT 1 FROM actions WHERE run_id=%s AND status='pending'", (row["id"],)
                ).fetchone()
                succeeded = conn.execute(
                    "SELECT receipt FROM actions WHERE run_id=%s AND status='succeeded'",
                    (row["id"],),
                ).fetchone()
                if writes:
                    status = "uncertain"
                    conn.execute(
                        "UPDATE actions SET status='uncertain' WHERE run_id=%s AND status='executing'",
                        (row["id"],),
                    )
                elif succeeded:
                    status = "succeeded"
                elif proposed:
                    status = "waiting_approval"
                elif notes:
                    status = "uncertain"
                else:
                    status = "queued" if row["attempts"] < 3 else "failed"
                conn.execute(
                    "UPDATE runs SET status=%s,error=%s,result=%s,lease_until=NULL,available_at=now()+interval '5 seconds',updated_at=now() WHERE id=%s",
                    (
                        status,
                        None
                        if status == "succeeded"
                        else "Worker stopped; recovery checkpoint applied",
                        "Verified issue: " + succeeded["receipt"]["url"]
                        if status == "succeeded"
                        else row["result"],
                        row["id"],
                    ),
                )
                conn.execute(
                    "INSERT INTO events(run_id,kind) VALUES (%s,'recovered')", (row["id"],)
                )

    def claim(self):
        with self.db.connect() as conn:
            # Serialize brief claims, never the execution itself; one in-flight run per owner.
            conn.execute("SELECT pg_advisory_xact_lock(714895)")
            row = conn.execute("""SELECT * FROM runs r WHERE status='queued' AND available_at<=now()
              AND NOT EXISTS(SELECT 1 FROM runs active WHERE active.owner_id=r.owner_id AND active.status='running')
              ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED""").fetchone()
            if not row:
                return None
            token = uuid.uuid4()
            return conn.execute(
                "UPDATE runs SET status='running',lease_token=%s,lease_until=now()+make_interval(secs => %s),attempts=attempts+1,updated_at=now() WHERE id=%s RETURNING *",
                (token, self.settings.max_run_seconds + 60, row["id"]),
            ).fetchone()

    def tick(self):
        self.heartbeat()
        self.recover()
        dispatch_due(self.db, self.settings)
        run = self.claim()
        if not run:
            return False
        event(self.db, run["id"], "started", {"attempt": run["attempts"]})
        try:
            self.engine.execute(run)
        except Exception as exc:
            message = (
                exc.message
                if isinstance(exc, DomainError)
                else "Run failed due to an internal error; check diagnostics"
            )
            code = exc.code if isinstance(exc, DomainError) else "internal_error"
            # No exception strings/headers/prompts enter logs or public error payloads.
            logger.warning(
                "run_failure run=%s code=%s type=%s", run["id"], code, type(exc).__name__
            )
            self.db.one(
                "UPDATE runs SET status=CASE WHEN EXISTS(SELECT 1 FROM actions a WHERE a.run_id=runs.id AND a.status IN ('executing','uncertain')) OR EXISTS(SELECT 1 FROM events e WHERE e.run_id=runs.id AND e.kind='note_intent') THEN 'uncertain' ELSE 'failed' END,error=%s,lease_until=NULL,updated_at=now() WHERE id=%s AND status='running' AND lease_token=%s RETURNING id",
                (message, run["id"], run["lease_token"]),
            )
            event(self.db, run["id"], "error", {"message": message, "code": code})
        self.heartbeat()
        return True

    def serve(self):
        self.db.migrate()
        stop = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop.set())
        signal.signal(signal.SIGINT, lambda *_: stop.set())

        def pulse():
            while not stop.wait(10):
                try:
                    self.heartbeat()
                except Exception:
                    logger.error("worker_heartbeat_failed")

        thread = threading.Thread(target=pulse, daemon=True)
        thread.start()
        while not stop.is_set():
            try:
                worked = self.tick()
            except Exception:
                logger.error("worker_tick_failed")
                worked = False
            if not worked:
                stop.wait(2)
        thread.join(timeout=1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    Worker(Settings()).serve()
