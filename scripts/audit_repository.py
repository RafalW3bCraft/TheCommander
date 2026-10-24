"""Local-only reproducible source inventory and ECC applicability ledger.

Reads repository source and catalog metadata; never executes catalog scripts,
imports legacy modules, reads private runtime data, or installs remote scanners.
This is structural evidence, not a claim of exhaustive semantic certification.
"""

import ast
import hashlib
import json
import re
import subprocess
import tomllib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence"
APPLIED = {
    "configure-ecc": ["docs/ECC_SETUP.md", "scripts/setup_ecc.sh"],
    "tdd-workflow": ["docs/evidence/audit-regressions-red.txt", "tests/test_workflows.py"],
    "verification-loop": ["scripts/verify.sh", "docs/evidence/audit-verification.txt"],
    "fastapi-patterns": ["commander/api.py", "commander/contracts.py"],
    "postgres-patterns": ["commander/db.py", "commander/migrations/003_message_runs.sql"],
    "security-review": ["docs/FINDINGS.md", "docs/THREAT_MODEL.md"],
    "frontend-patterns": ["frontend/src/main.tsx", "frontend/src/api.ts"],
    "api-design": ["commander/contracts.py", "docs/openapi.json"],
    "e2e-testing": ["frontend/e2e/workflows.spec.ts", "docs/evidence/browser-results.json"],
    "agent-architecture-audit": ["docs/evidence/agent-architecture-audit.json"],
    "click-path-audit": ["docs/CLICK_PATH_AUDIT.md", "frontend/e2e/workflows.spec.ts"],
    "browser-qa": ["docs/CODEBASE_AUDIT.md", "docs/evidence/browser-results.json"],
    "production-audit": ["docs/CODEBASE_AUDIT.md", "docs/RELEASE_REPORT.md"],
    "contract-first": ["commander/contracts.py", "frontend/src/api-schema.d.ts"],
    "database-migrations": ["commander/migrations/003_message_runs.sql", "docs/OPERATIONS.md"],
    "eval-harness": ["scripts/evaluate_live.py", "docs/EVALUATION.md"],
    "ai-regression-testing": ["tests/test_workflows.py", "frontend/e2e/workflows.spec.ts"],
    "module-regression": ["docs/REGRESSION.md", "scripts/verify.sh"],
    "change-impact": ["docs/CODEBASE_AUDIT.md", "docs/adr/002-retire-legacy-entrypoint.md"],
}
SPECIAL = {
    "repo-scan": (
        "bootstrap-only",
        "ECC entry installs another scanner; no external install or scan performed. Local inventory uses this script.",
    ),
    "delivery-gate": (
        "host-specific-not-activated",
        "Claude Stop hook; no native Codex hook parity or activation claimed. Explicit verification script provides project gates.",
    ),
    "agent-eval": (
        "reviewed-not-applied",
        "Coding-agent head-to-head benchmark is separate from the application's model acceptance evaluation.",
    ),
    "skill-stocktake": (
        "inventory-guidance-only",
        "Catalog metadata inventoried locally; no complete per-skill quality/currency review, global history scan or Claude cache mutation claimed.",
    ),
    "config-gc": (
        "reviewed-not-applied",
        "Claude configuration garbage collection does not apply to source cleanup; existing user catalog is preserved.",
    ),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def category(path):
    if path.startswith(".agents/"):
        return "ecc-development-tooling"
    if path.startswith("commander/") or path == "main.py":
        return "release-backend"
    if path.startswith("frontend/src/"):
        return "generated-contract" if path.endswith("api-schema.d.ts") else "release-frontend"
    if path.startswith(("tests/", "frontend/e2e/", "scripts/")):
        return "verification-and-operations"
    if path.startswith("docs/evidence/"):
        return "verification-evidence"
    if (
        path.startswith("docs/")
        or path.endswith(".md")
        or path in {"LICENSE", "THIRD_PARTY_NOTICES"}
    ):
        return "documentation"
    if (
        path.startswith(("agents/", "legacy/", "static/", "templates/"))
        or path.endswith(".py")
        or path in {"schema.sql", "requirements.txt", "env.example", "generated-icon.png"}
    ):
        return "preserved-legacy"
    return "release-build-and-configuration"


def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    raw = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT)
    paths = sorted(set(p.decode() for p in raw.split(b"\0") if p))
    inventory, modules, routes, missing = [], [], [], []
    duplicates = defaultdict(list)
    for relative in paths:
        path = ROOT / relative
        # Never follow a user symlink or inspect private env files, even if tracked.
        if path.is_symlink() or path.name.startswith(".env"):
            inventory.append({"path": relative, "category": "excluded-private-or-symlink"})
            continue
        if not path.is_file():
            missing.append(relative)
            continue
        kind = category(relative)
        row = {"path": relative, "category": kind, "bytes": path.stat().st_size}
        if kind == "verification-evidence":
            row["hash_scope"] = "not hashed: mutable output, including this inventory"
        else:
            data = path.read_bytes()
            row["sha256"] = digest(data)
            if data and kind != "ecc-development-tooling":
                duplicates[row["sha256"]].append(relative)
            if path.suffix == ".py" and kind != "ecc-development-tooling":
                tree = ast.parse(data, filename=relative)
                imports = sorted(
                    {
                        name
                        for node in ast.walk(tree)
                        for name in (
                            [alias.name for alias in node.names]
                            if isinstance(node, ast.Import)
                            else [node.module or ""]
                            if isinstance(node, ast.ImportFrom)
                            else []
                        )
                    }
                )
                modules.append({"path": relative, "imports": imports, "syntax": "parsed"})
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for dec in node.decorator_list:
                            if (
                                isinstance(dec, ast.Call)
                                and isinstance(dec.func, ast.Attribute)
                                and dec.func.attr in {"get", "post", "put", "delete", "patch"}
                                and dec.args
                                and isinstance(dec.args[0], ast.Constant)
                                and isinstance(dec.args[0].value, str)
                                and dec.args[0].value.startswith("/")
                            ):
                                routes.append(
                                    {
                                        "method": dec.func.attr.upper(),
                                        "route": dec.args[0].value,
                                        "handler": node.name,
                                        "source": relative,
                                        "line": node.lineno,
                                    }
                                )
        inventory.append(row)

    catalog = []
    for path in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
        content = path.read_text()
        match = re.search(r"^description:\s*(.+)$", content, re.M)
        name = path.parent.name
        if name in APPLIED:
            status, reason = (
                "applied-guidance",
                "Guidance used in project work; linked artifacts record actual execution and limits.",
            )
        else:
            status, reason = SPECIAL.get(
                name,
                (
                    "catalogued-not-invoked",
                    "Available reference; not selected for this FastAPI/PostgreSQL/React engineering task. No execution or skill-quality certification claimed.",
                ),
            )
        catalog.append(
            {
                "name": name,
                "path": path.relative_to(ROOT).as_posix(),
                "description": match.group(1).strip('"') if match else "",
                "sha256": digest(content.encode()),
                "status": status,
                "reason": reason,
                "artifacts": APPLIED.get(name, []),
            }
        )
    receipt = json.loads((ROOT / ".agents/ecc-install-state.json").read_text())
    artifacts = [r for r in inventory if r["category"] == "ecc-development-tooling"]
    ecc = {
        "generated_at": timestamp,
        "scope": "All project .agents skills and supporting artifacts; applicability inventory, not all skills executed",
        "installation": {
            k: receipt[k]
            for k in ("schemaVersion", "installedAt", "request", "resolution", "source")
        },
        "target": receipt["target"]["id"],
        "source_reference": {
            "version": "2.2.3",
            "commit": "90606c8315ee09cafc303515c5f33024db6b9882",
            "path": ".tools/ecc",
        },
        "counts": dict(Counter(row["status"] for row in catalog)),
        "artifact_counts": dict(Counter(Path(row["path"]).parts[1] for row in artifacts)),
        "skills": catalog,
        "artifacts": artifacts,
    }
    dependencies = tomllib.loads((ROOT / "pyproject.toml").read_text())
    frontend = json.loads((ROOT / "frontend/package.json").read_text())
    report = {
        "generated_at": timestamp,
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "scope": "All tracked and unignored files recursively; first-party Python AST/imports/routes, complete ECC artifact hashes, dependency manifests",
        "limits": [
            "Metadata enumeration is not line-by-line semantic certification of every catalog or third-party dependency.",
            "Ignored .git, .tools source checkout, .venv, node_modules, caches, .runtime database/notes and private environment contents excluded. Locked dependencies are checked by package audits.",
            "Mutable evidence outputs omit hashes to avoid self-referential inventory churn.",
            "Legacy modules are inventoried and retained, not enabled or claimed production-safe.",
        ],
        "counts": dict(Counter(row["category"] for row in inventory)),
        "files": inventory,
        "missing_tracked_files": missing,
        "python_modules": modules,
        "routes": routes,
        "identical_nonempty_files": [group for group in duplicates.values() if len(group) > 1],
        "dependencies": {
            "python": dependencies["project"]["dependencies"],
            "python_dev": dependencies["dependency-groups"]["dev"],
            "frontend": frontend["dependencies"],
            "frontend_dev": frontend["devDependencies"],
        },
    }
    OUT.mkdir(exist_ok=True)
    (OUT / "ecc-catalog.json").write_text(json.dumps(ecc, indent=2) + "\n")
    (OUT / "recursive-inventory.json").write_text(json.dumps(report, indent=2) + "\n")
    reference = ROOT / ".tools/ecc"
    if (reference / ".git").exists():
        reference_paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=reference).split(
            b"\0"
        )
        reference_files = []
        reference_skills = []
        for raw_path in sorted(p for p in reference_paths if p):
            relative = raw_path.decode()
            path = reference / relative
            if not path.is_file() or path.is_symlink():
                continue
            data = path.read_bytes()
            reference_files.append({"path": relative, "bytes": len(data), "sha256": digest(data)})
            if re.fullmatch(r"skills/[^/]+/SKILL\.md", relative):
                name = path.parent.name
                reference_skills.append(
                    {
                        "name": name,
                        "path": relative,
                        "status": "applied-guidance"
                        if name in APPLIED
                        else "catalogued-not-invoked",
                        "artifacts": APPLIED.get(name, []),
                        "installed_project_copy": name in {r["name"] for r in catalog},
                    }
                )
        reference_report = {
            "generated_at": timestamp,
            "commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=reference, text=True
            ).strip(),
            "scope": "Every tracked regular file in pinned ECC source; hash inventory, not code execution or per-file quality certification",
            "files": reference_files,
            "skills": reference_skills,
        }
        (OUT / "ecc-reference-inventory.json").write_text(
            json.dumps(reference_report, indent=2) + "\n"
        )
    print(
        json.dumps(
            {
                "files": len(inventory),
                "python_modules": len(modules),
                "routes": len(routes),
                "ecc_skills": len(catalog),
                "ecc_artifacts": len(artifacts),
                "missing_tracked": len(missing),
            }
        )
    )


if __name__ == "__main__":
    main()
