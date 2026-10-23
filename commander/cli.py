"""Local administrative commands; no external writes."""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from commander.contracts import MemoryInput
from commander.db import Database
from commander.memory import save_memory
from commander.settings import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "seed", "import-legacy"])
    parser.add_argument("--owner")
    parser.add_argument("--file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = Database(Settings())
    db.migrate()
    if args.command == "migrate":
        print("Migrations applied transactionally. Existing public schema unchanged.")
        return
    owner = db.one("SELECT id FROM owners WHERE username=%s", (args.owner,))
    if not owner:
        raise SystemExit("Supply --owner with an existing owner username")
    if args.command == "seed":
        save_memory(
            db,
            owner["id"],
            MemoryInput(
                key="Fictional demo format", content="Prefer three short bullets with sources."
            ),
        )
        print("Fictional preference saved; no external action dispatched.")
        return
    if not args.file or not args.file.is_file():
        raise SystemExit("--file must identify the existing legacy JSON backup")
    data = json.loads(args.file.read_text())
    if not isinstance(data, dict):
        raise SystemExit("Expected a JSON object; nothing imported")
    records = data.get("knowledge_store", data)
    if not isinstance(records, dict):
        raise SystemExit("Invalid knowledge_store; nothing imported")
    valid = []
    errors = []
    for key, value in records.items():
        try:
            content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            valid.append(MemoryInput(kind="episodic", key=str(key), content=content))
        except ValueError:
            errors.append(str(key))
    conflicts = [
        r.key
        for r in valid
        if db.one(
            "SELECT 1 FROM memories WHERE owner_id=%s AND kind=%s AND key=%s",
            (owner["id"], r.kind, r.key),
        )
    ]
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "valid_records": len(valid),
                "malformed_keys": errors,
                "conflicts": conflicts,
            }
        )
    )
    if errors or conflicts:
        raise SystemExit("Resolve malformed records/conflicts before import; no records changed")
    if args.apply:
        backup = args.file.with_name(
            args.file.name + ".backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        )
        shutil.copy2(args.file, backup)
        with db.connect() as conn:
            for record in valid:
                conn.execute(
                    "INSERT INTO memories(owner_id,kind,key,content,source) VALUES (%s,%s,%s,%s,%s)",
                    (
                        owner["id"],
                        record.kind,
                        record.key,
                        record.content,
                        "legacy import: " + args.file.name,
                    ),
                )
        print(f"Imported {len(valid)} records; backup retained beside input file.")


if __name__ == "__main__":
    main()
