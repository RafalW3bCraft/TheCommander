import hashlib
import json as stdjson
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError

from commander.connections import Connections, owner_lock
from commander.contracts import Empty, Issue, Note, Search
from commander.db import json
from commander.errors import DomainError
from commander.runs import event, owned_run
from commander.skills import definition
from commander.workspace import Workspace

SCHEMAS: dict[str, type[BaseModel]] = {
    "github_read": Empty,
    "search": Search,
    "save_note": Note,
    "propose_issue": Issue,
}


def args_hash(args):
    return hashlib.sha256(
        stdjson.dumps(args, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def tools_for(skill):
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": {
                    "github_read": "Read configured repository issues",
                    "search": "Search approved sources",
                    "save_note": "Create a workspace Markdown note",
                    "propose_issue": "Prepare a GitHub issue for exact owner approval; does not execute a write",
                }[name],
                "parameters": SCHEMAS[name].model_json_schema(),
            },
        }
        for name in definition(skill)["tools"]
    ]


class Broker:
    def __init__(self, db, settings, transport=None):
        self.db, self.settings = db, settings
        self.connections = Connections(db, settings, transport)
        self.provider = self.connections.provider

    def active(self, run):
        current = owned_run(self.db, run["owner_id"], run["id"])
        if current["status"] != "running" or current["lease_token"] != run["lease_token"]:
            raise DomainError("Run is no longer active", 409, "cancelled")
        return current

    def call(self, run, name, arguments):
        if name not in definition(run["skill"])["tools"]:
            raise DomainError("This tool is not allowed for this skill", 403, "tool_denied")
        try:
            data = SCHEMAS[name].model_validate(arguments)
        except ValidationError:
            raise DomainError(
                "Tool arguments did not match the schema", 422, "invalid_tool"
            ) from None
        with owner_lock(self.db, run["owner_id"]):
            self.active(run)
            if name == "github_read":
                return self.read_github(run)
            if name == "search":
                assert isinstance(data, Search)
                return self.search(run, data.query)
            if name == "save_note":
                assert isinstance(data, Note)
                connection = self.connections.get(run["owner_id"], "workspace")
                if not connection["config"].get("enabled"):
                    raise DomainError("Workspace access is disabled", 403)
                event(
                    self.db,
                    run["id"],
                    "note_intent",
                    {
                        "name": data.name,
                        "sha256": hashlib.sha256(data.content.encode()).hexdigest(),
                    },
                )
                receipt = Workspace(self.settings.workspace_root, run["owner_id"]).write(
                    data.name, data.content
                )
                event(self.db, run["id"], "note_receipt", receipt)
                return receipt
            return self.propose(run, data)

    def read_github(self, run):
        conn = self.connections.get(run["owner_id"], "github")
        repo = conn["config"]["repository"]
        rows = self.provider.github_read(self.connections.secret(conn), repo)
        if not isinstance(rows, list):
            raise DomainError("GitHub returned malformed issues", 502)
        result = []
        for item in rows[:20]:
            if not isinstance(item, dict) or not isinstance(item.get("html_url"), str):
                raise DomainError("GitHub returned malformed issue", 502)
            url = item["html_url"]
            if not url.startswith("https://github.com/" + repo + "/"):
                continue
            title = str(item.get("title", ""))[:300]
            excerpt = str(item.get("body") or "")[:1500]
            self.db.one(
                "INSERT INTO evidence(run_id,url,title,excerpt) VALUES (%s,%s,%s,%s) RETURNING id",
                (run["id"], url, title, excerpt),
            )
            result.append({"url": url, "title": title, "excerpt": excerpt})
        event(self.db, run["id"], "github_read", {"count": len(result), "repository": repo})
        return result

    def search(self, run, query):
        conn = self.connections.get(run["owner_id"], "tavily")
        domains = conn["config"].get("domains", [])
        if not domains:
            raise DomainError(
                "Set approved research domains in Tavily connection settings",
                409,
                "source_scope_required",
            )
        rows = self.provider.search(self.connections.secret(conn), query, domains)
        if not isinstance(rows, dict) or not isinstance(rows.get("results"), list):
            raise DomainError("Search provider returned malformed evidence", 502)
        result = []
        for item in rows["results"][:5]:
            url = str(item.get("url", ""))
            parsed = urlparse(url)
            if parsed.scheme != "https" or not any(
                parsed.hostname == d or (parsed.hostname or "").endswith("." + d) for d in domains
            ):
                continue
            title = str(item.get("title", ""))[:300]
            excerpt = str(item.get("content", ""))[:3000]
            record = self.db.one(
                "INSERT INTO evidence(run_id,url,title,excerpt) VALUES (%s,%s,%s,%s) RETURNING fetched_at",
                (run["id"], url, title, excerpt),
            )
            result.append(
                {
                    "url": url,
                    "title": title,
                    "excerpt": excerpt,
                    "fetched_at": record["fetched_at"].isoformat(),
                }
            )
        if not result:
            raise DomainError("No evidence found in your approved domains", 502, "no_evidence")
        event(self.db, run["id"], "search", {"count": len(result)})
        return result

    def propose(self, run, data):
        conn = self.connections.get(run["owner_id"], "github")
        args = {"repository": conn["config"]["repository"], **data.model_dump()}
        row = self.db.one(
            "INSERT INTO actions(owner_id,run_id,tool,arguments,args_hash,connection_revision) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
            (
                run["owner_id"],
                run["id"],
                "github_create_issue",
                json(args),
                args_hash(args),
                conn["revision"],
            ),
        )
        event(self.db, run["id"], "approval_required", {"action_id": str(row["id"])})
        return {"action_id": str(row["id"]), "status": "requires_exact_approval", **args}

    def action(self, owner, action_id):
        row = self.db.one("SELECT * FROM actions WHERE owner_id=%s AND id=%s", (owner, action_id))
        if not row:
            raise DomainError("Action not found", 404)
        return row

    def approve(self, owner, action_id, supplied_hash):
        with owner_lock(self.db, owner):
            row = self.action(owner, action_id)
            if (
                row["status"] != "pending"
                or row["args_hash"] != supplied_hash
                or args_hash(row["arguments"]) != supplied_hash
                or row["expires_at"] < datetime.now(timezone.utc)
            ):
                raise DomainError(
                    "Approval is expired, changed or already used", 409, "invalid_approval"
                )
            conn = self.connections.get(owner, "github")
            run = owned_run(self.db, owner, row["run_id"])
            if (
                conn["revision"] != row["connection_revision"]
                or conn["config"]["repository"] != row["arguments"]["repository"]
                or run["status"] != "waiting_approval"
            ):
                raise DomainError("Action authority is no longer valid", 409, "revoked")
            with self.db.connect() as transaction:
                transaction.execute(
                    "UPDATE actions SET status='approved',approved_at=now() WHERE id=%s",
                    (action_id,),
                )
                transaction.execute(
                    "UPDATE runs SET status='queued',available_at=now(),updated_at=now() WHERE id=%s",
                    (row["run_id"],),
                )
                transaction.execute(
                    "INSERT INTO events(run_id,kind,payload) VALUES (%s,'approved',%s)",
                    (row["run_id"], json({"action_id": str(action_id)})),
                )
        return self.action(owner, action_id)

    def edit(self, owner, action_id, data):
        with owner_lock(self.db, owner):
            row = self.action(owner, action_id)
            if row["status"] not in ("pending", "approved"):
                raise DomainError("Action can no longer be edited", 409)
            args = {**row["arguments"], **data.model_dump()}
            with self.db.connect() as transaction:
                transaction.execute(
                    "UPDATE actions SET arguments=%s,args_hash=%s,status='pending',approved_at=NULL,expires_at=now()+interval '30 minutes' WHERE id=%s",
                    (json(args), args_hash(args), action_id),
                )
                transaction.execute(
                    "UPDATE runs SET status='waiting_approval',updated_at=now() WHERE id=%s",
                    (row["run_id"],),
                )
                transaction.execute(
                    "INSERT INTO events(run_id,kind,payload) VALUES (%s,'approval_invalidated',%s)",
                    (row["run_id"], json({"action_id": str(action_id)})),
                )
        return self.action(owner, action_id)

    def execute(self, run, action):
        with owner_lock(self.db, run["owner_id"]):
            self.active(run)
            row = self.action(run["owner_id"], action["id"])
            conn = self.connections.get(run["owner_id"], "github")
            if (
                row["status"] != "approved"
                or row["expires_at"] < datetime.now(timezone.utc)
                or row["connection_revision"] != conn["revision"]
                or args_hash(row["arguments"]) != row["args_hash"]
            ):
                raise DomainError("Write approval is no longer valid", 403, "revoked")
            args = row["arguments"]
            if args["repository"] != conn["config"]["repository"]:
                raise DomainError("Repository denied", 403)
            self.db.one(
                "UPDATE actions SET status='executing' WHERE id=%s RETURNING id", (row["id"],)
            )
            event(
                self.db,
                run["id"],
                "write_intent",
                {"action_id": str(row["id"]), "args_hash": row["args_hash"]},
            )
            marker = f"<!-- thecommander-action:{row['id']} -->"
            try:
                issue = self.provider.request(
                    "POST",
                    f"https://api.github.com/repos/{args['repository']}/issues",
                    self.connections.secret(conn),
                    {"title": args["title"], "body": args["body"] + "\n\n" + marker},
                )
                if not isinstance(issue, dict):
                    raise DomainError(
                        "Provider returned an unconfirmed write response", 502, "malformed_response"
                    )
                number = issue.get("number")
                if not isinstance(number, int) or number <= 0:
                    raise DomainError(
                        "Provider did not confirm the created issue", 502, "malformed_response"
                    )
                confirmed = self.provider.request(
                    "GET",
                    f"https://api.github.com/repos/{args['repository']}/issues/{number}",
                    self.connections.secret(conn),
                    retry=True,
                )
                return self.confirm(row, confirmed, marker)
            except Exception as exc:
                message = (
                    exc.message
                    if isinstance(exc, DomainError)
                    else "Write response could not be verified"
                )
                # Even a provider error after dispatch cannot prove no effect. Never repeat POST.
                self.db.one(
                    "UPDATE actions SET status='uncertain',error=%s WHERE id=%s RETURNING id",
                    (message, row["id"]),
                )
                self.db.one(
                    "UPDATE runs SET status='uncertain',error=%s,updated_at=now() WHERE id=%s RETURNING id",
                    (message, run["id"]),
                )
                event(self.db, run["id"], "uncertain", {"action_id": str(row["id"])})
                raise

    def confirm(self, row, issue, marker):
        args = row["arguments"]
        if not isinstance(issue, dict):
            raise DomainError("Invalid issue confirmation", 502, "malformed_response")
        number = issue.get("number")
        expected = f"https://github.com/{args['repository']}/issues/{number}"
        if (
            not isinstance(number, int)
            or number <= 0
            or issue.get("body") != args["body"] + "\n\n" + marker
            or issue.get("html_url") != expected
            or issue.get("title") != args["title"]
        ):
            raise DomainError("Issue could not be verified", 502, "unverified_write")
        receipt = {
            "provider": "github",
            "number": number,
            "url": expected,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.one(
            "UPDATE actions SET status='succeeded',receipt=%s,error=NULL WHERE id=%s RETURNING id",
            (json(receipt), row["id"]),
        )
        event(self.db, row["run_id"], "write_receipt", receipt)
        return receipt

    def reconcile(self, owner, action_id):
        with owner_lock(self.db, owner):
            row = self.action(owner, action_id)
            if row["status"] != "uncertain":
                raise DomainError("Only uncertain actions can be reconciled", 409)
            conn = self.connections.get(owner, "github")
            if conn["config"]["repository"] != row["arguments"]["repository"]:
                raise DomainError("Original repository connection required", 409)
            marker = f"<!-- thecommander-action:{row['id']} -->"
            matches: list[dict[str, Any]] = []
            # Read-only scan. Absence in this bounded window is NOT evidence to retry.
            for page in range(1, 4):
                rows = self.provider.request(
                    "GET",
                    f"https://api.github.com/repos/{row['arguments']['repository']}/issues?state=all&sort=created&direction=desc&per_page=100&page={page}",
                    self.connections.secret(conn),
                    retry=True,
                )
                matches.extend(i for i in rows if marker in (i.get("body") or ""))
                if len(rows) < 100:
                    break
            if len(matches) != 1:
                raise DomainError(
                    "No unique matching issue found. Action remains uncertain; no write retried.",
                    409,
                    "uncertain",
                )
            receipt = self.confirm(row, matches[0], marker)
            self.db.one(
                "UPDATE runs SET status=CASE WHEN status='cancelled' THEN status ELSE 'succeeded' END,result=%s,error=NULL,updated_at=now() WHERE id=%s RETURNING id",
                ("Verified issue: " + receipt["url"], row["run_id"]),
            )
            return self.action(owner, action_id)
