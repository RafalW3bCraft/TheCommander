# Manual environment setup and release handoff

Checked against `vultr` commit `f5a90fa88611cff0c27cf9bc539ac5cadc38be0d` on 2026-11-05. This guide adds instructions; it does not install real keys or deploy infrastructure. Work on `vultr` only.

## Historical starting evidence

The following records the starting failure, not the latest release status. See
[Vultr verification](VULTR_VERIFICATION.md) for current checks and blockers.

| Gate | Observed result at f5a90fa |
|---|---|
| Python/PostgreSQL | 174 passed, 3 real-container tests skipped, 90.44% coverage |
| Browser suite | 10 passed, 1 failed: `memory recall explains disabled and degraded index states`; login helper could not find the Project combobox |
| Sandbox workflow | Failed building egress image: `COPY deploy/sandbox/proxy.py` was excluded from the root Docker context |
| Real Vultr / gVisor deployment | Still unverified |

Runs: [Verify release](https://github.com/RafalW3bCraft/TheCommander/actions/runs/41971716067), [Sandbox containment](https://github.com/RafalW3bCraft/TheCommander/actions/runs/41971716172). These failures were addressed in the November 5 repair cycle; current containment and deployment results are recorded separately.

## 1. Prepare the existing checkout

For an existing clean checkout already on `vultr`:

```bash
set -euo pipefail
test "$(git branch --show-current)" = vultr
git status --short
git pull --ff-only origin vultr
uv sync --frozen
```

Do not pull over unrelated work. For a genuinely fresh checkout instead:

```bash
git clone --branch vultr --single-branch https://github.com/RafalW3bCraft/TheCommander.git
cd TheCommander
uv sync --frozen
```

The project uses Python 3.13 and Node 22.12+ within Node 22. Install Docker Engine 28+ and gVisor on the intended Linux execution VM. The API container must not receive the Docker socket.

## 2. Preserve the two-file configuration

The loader is intentionally `SettingsConfigDict(env_file=(".env", ".env.runtime"))`.

| Location | Purpose | Effective precedence |
|---|---|---|
| `.env` | Provider credentials and operator configuration | Base |
| `.env.runtime` | Existing generated encryption/bootstrap/database secrets and runtime overrides | Overrides the same name in `.env` |
| Process environment | Container/service-specific settings | Overrides both files |
| Compose `environment:` | Explicit container values, including internal DB URL | Overrides service env-file values |
| Owner Settings / saved connections | Persisted provider selection, budgets, credentials and scopes | Can retain an older owner selection/key despite changed environment defaults |

Keep every existing key/value unless a specific deliberate configuration change is needed. Never replace `ENCRYPTION_KEY` on an existing database: encrypted connections would become unreadable. Never change `POSTGRES_PASSWORD` merely by editing a file after the database volume was initialized. Preserve the matching secret/database backups.

**Fresh installation only**, after confirming there are no old database volumes/data to recover:

```bash
umask 077
test -f .env || cp env.release.example .env
uv run python scripts/setup_runtime.py
chmod 600 .env .env.runtime
test -z "$(git ls-files -- .env .env.runtime)"
git check-ignore .env .env.runtime
```

On an existing installation keep both files. If `.env.runtime` or a required secret is missing, recover the original matching secrets before starting; do not generate replacements over existing data. Create a protected local backup using your existing backup procedure. Never put private backups into a tracked folder or upload them as release evidence.

Edit locally:

```bash
nano .env
nano .env.runtime
```

Enter keys in your local editor, not in a chat, prompt, shell command argument, screenshot, test fixture or commit. Codex may load them for authorized tests but must report only key names/configuration status, never values. Do not run `cat .env`, `printenv`, `set -x`, or a normal `docker compose config` into a shared log: these can expose credentials. `docker compose config --quiet` is suitable for syntax checking.

## 3. Obtain the provider keys manually

### Required for Blast Radius Zero: Vultr inference

1. Open your Vultr Console and the Serverless Inference area. Activate/use your authorized hackathon inference subscription.
2. Open that subscription's management/overview page and copy its **inference API key** into `VULTR_API_KEY` in `.env`.
3. The application uses this as Bearer authentication to `https://api.vultrinference.com/v1`. This variable is the inference credential, not a general Compute-provisioning token.
4. Discover actual account model IDs with the command below. Choose a text/code-capable model and a separately verified image-input/vision model. Do not infer vision support from a model name or the fact that it is listed.

Official sources: [retrieve the inference key](https://docs.vultr.com/products/compute/serverless-inference/management/connection), updated October 23, 2026; [provisioning](https://docs.vultr.com/products/compute/serverless-inference/provisioning), updated November 4, 2026. Subscription creation and inference usage can incur charges; use the authorized account/budget.

This read-only model-list command prints model IDs, not credentials, and does not invoke `Settings()` before the final model configuration is ready:

```bash
uv run python - <<'PY'
import os
import sys
import httpx
from dotenv import dotenv_values

values = {**dotenv_values('.env'), **dotenv_values('.env.runtime'), **os.environ}
key = values.get('VULTR_API_KEY', '')
if not key:
    raise SystemExit('VULTR_API_KEY is missing; enter it locally first.')
try:
    response = httpx.get(
        'https://api.vultrinference.com/v1/models',
        headers={'Authorization': 'Bearer ' + key},
        follow_redirects=False,
        timeout=30,
    )
    if response.status_code != 200:
        raise SystemExit(f'Model discovery failed with HTTP {response.status_code}; no credential printed.')
    data = response.json()
    models = data.get('data') if isinstance(data, dict) else None
    if not isinstance(models, list):
        raise ValueError()
    for model in models:
        if not isinstance(model, dict) or not isinstance(model.get('id'), str):
            raise ValueError()
        print(model['id'])
except (httpx.HTTPError, ValueError):
    sys.exit('Model discovery failed or returned malformed data; inspect account access/network without logging credentials.')
PY
```

A returned model catalog alone does **not** establish credential validity: the
November 5 catalog request succeeded while an actual completion returned HTTP 401.
Require a real text request and a genuine image-input request before activating
models. Keep the Compute CLI credential in a separate protected administrative
configuration; the application `VULTR_API_KEY` remains an inference key.

Set the chosen text ID in **both** `PROVIDER_MODEL` and `SANDBOX_MODEL`. Set the proven image-input model in `SANDBOX_VISION_MODEL`. Keep `SANDBOX_ENABLED=false` until the execution runner passes containment checks.

### Optional integrations: retain existing working credentials

| Variable | How to obtain / scope it | Needed for |
|---|---|---|
| `GITHUB_TOKEN` | GitHub Settings → Developer settings → Personal access tokens → fine-grained token; select only the intended repository. Runtime app normally needs Metadata read and Issues read/write. | Repository issue research and human-approved issue creation |
| `GITHUB_REPOSITORY` | Set exactly `RafalW3bCraft/TheCommander`, or your deliberately selected single demo repository. This is not an API key. | Runtime GitHub scope |
| `TAVILY_API_KEY` | Obtain an API key from [Tavily's dashboard](https://app.tavily.com/). Then set approved research domains in the application's Connections settings. | Web research/briefings |
| `NEBIUS_API_KEY` | Retain the existing Nebius Token Factory API key; obtain one through your Token Factory account if deliberately enabling this optional provider. | Existing Nebius workflows outside the Vultr demo |
| `OPENAI_API_KEY` | Create an API key for your authorized OpenAI API project via [the API platform](https://platform.openai.com/api-keys). | Optional OpenAI app inference |
| `ANTHROPIC_API_KEY` | Create an authorized personal/service key in [Claude Console API keys](https://platform.claude.com/settings/keys). Verify compatibility with the current app adapter before use. | Optional Anthropic app inference |

Sources: [GitHub token instructions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens), [Tavily](https://docs.tavily.com/), [Nebius documentation](https://docs.tokenfactory.nebius.com/), [OpenAI quickstart](https://developers.openai.com/api/docs/quickstart), [Claude key instructions](https://platform.claude.com/docs/en/get-api-key).

Keep coding-agent Git authentication separate from the runtime app token. Publishing code/workflows may need Contents write and Workflows write; the runtime issue tool does not need that broader authority. Setting `GITHUB_TOKEN` in `.env` does not automatically authenticate a terminal `git push`. Likewise, the app's optional OpenAI key is separate from Codex login; use your normal Codex authentication.

The Vultr demo must dispatch its agent LLM calls to Vultr. Preserve optional keys, but explicitly select Vultr for the demo owner and new runs. Existing saved owner settings/connections override environment defaults; historical queued runs or schedules can retain older provider snapshots. Inspect/pause only the demo-relevant legacy work with the owner's authorization; do not rewrite historical records or silently change unrelated schedules.

## 4. Fill `.env` with the recognized names

This is a target configuration to merge into the existing file, **not** a command to overwrite it. Three fields intentionally remain blank until you supply your own account values. Do not start with blank model IDs while `INFERENCE_PROVIDER=vultr`.

```dotenv
# Use the actual Serverless Inference subscription key. Enter locally.
VULTR_API_KEY=

# Use actual authenticated account model IDs, not example names.
INFERENCE_PROVIDER=vultr
PROVIDER_MODEL=
SANDBOX_MODEL=
SANDBOX_VISION_MODEL=

# Enable only after code/browser containment probes pass.
SANDBOX_ENABLED=false
SANDBOX_RUNTIME=runsc
SANDBOX_TIMEOUT_SECONDS=45
SANDBOX_BROWSER_DOMAINS=["example.com"]
SANDBOX_BROWSER_IMAGE=localhost/commander-browser:1.64.1
SANDBOX_PROXY_IMAGE=localhost/commander-egress:1

# Initial local setup. Change the pair consistently before remote HTTPS use.
APP_ORIGIN=http://localhost:8000
PRODUCTION=false
APP_PORT=8000
DATABASE_SCHEMA=commander
WORKSPACE_ROOT=.runtime/notes

# Preserve existing operator ceilings if already configured.
MAX_STEPS=5
MAX_OUTPUT_TOKENS=2048
MAX_CONTEXT_CHARS=32000
MAX_RUN_SECONDS=180
MAX_DAILY_RUNS=50
MAX_DAILY_TOKENS=100000

# Retain existing values; do not erase them by copying blank assignments.
GITHUB_TOKEN=
GITHUB_REPOSITORY=RafalW3bCraft/TheCommander
TAVILY_API_KEY=
NEBIUS_API_KEY=
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1
NEBIUS_MODEL=nvidia/nemotron-3-super-120b-a12b
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Optional index remains disabled unless explicitly deploying its overlay.
MEMORY_INDEX_URL=
MEMORY_INDEX_TOKEN=
```

`example.com` is only a public read-only smoke-test destination. For fill/click tests add your own controlled public HTTPS demo hostname to the JSON list, for example `['example.com', 'your-real-host']` expressed with JSON **double quotes**. Enter actual owned hostnames; do not leave a fictional host in the allowlist. Exact domains are required; no wildcards, private IPs, localhost or metadata endpoints.

### Additional recognized variables and their treatment

| Variables | Treatment |
|---|---|
| `DATABASE_URL` | Required by native Python settings. Compose injects its working internal URL; a host runner needs the corresponding loopback/private URL, explained below. Do not use the example's passwordless URL as a working production credential. |
| `ENCRYPTION_KEY` | Existing/generated valid Fernet key in `.env.runtime`; do not rotate during setup. |
| `BOOTSTRAP_TOKEN` | Existing/generated token of at least 32 characters in `.env.runtime`; use locally for first owner bootstrap. |
| `POSTGRES_PASSWORD` | Existing/generated Compose database password in `.env.runtime`; keep matched to the initialized database. |
| `APP_DOMAIN` | Compose HTTPS hostname, without `https://` or a path. Enter the actual DNS hostname before applying the HTTPS overlay. |
| `SANDBOX_CODE_IMAGE` | Optional override; preserve the pinned Python image default in `commander/settings.py` unless a reviewed image update is needed. |
| `DAILY_SPEND_LIMIT_USD` | Optional strict dollar cap. Omit if not deliberately configured; preserve an existing cap. Current sandbox inference intentionally clears inherited provider prices, so enabling a strict cap without verified Vultr-specific accounting fails closed with `unknown_cost`. Have Codex implement/verify correct model pricing before claiming dollar enforcement; never silently disable a cap to get a green test. |
| `INPUT_USD_PER_MILLION`, `OUTPUT_USD_PER_MILLION` | Optional verified model prices only; do not reuse old Nebius prices for Vultr or invent current pricing. |
| `MODEL_ID` | Preserved legacy alias for `NEBIUS_MODEL`; avoid conflicting values. |
| `TEST_DATABASE_URL` | Test scripts only, pointing to a separate disposable PostgreSQL 17 database, never the application database. |
| `RUN_SANDBOX_DOCKER`, `RUN_SANDBOX_BROWSER`, `SANDBOX_TEST_RUNTIME` | Explicit test-process flags, not app credentials. Real deployment tests use values `1`, `1`, `runsc`. |
| `PG_BIN` | Optional local PostgreSQL binary directory for `scripts/test_db.sh`; default `/usr/lib/postgresql/17/bin`. |
| `MEMORY_ADMIN_PASSWORD`, `MEMORY_DB_PASSWORD` | Separate private secrets only if enabling `deploy/compose.memory.yaml`. Never reuse the main DB password. |
| `MEMORY_DB_HOST`, `MEMORY_DB_PORT`, `MEMORY_DB_NAME`, `MEMORY_DB_USER`, `MEM0_TELEMETRY` | Memory-service process settings. The supplied overlay sets its host/user/name and disables telemetry; port defaults to 5432. Do not add these to the main app unnecessarily. |

Optional numeric settings should be **omitted**, not assigned an empty string. `VULTR_MODEL`, `VULTR_BASE_URL`, `DATABASE_PASSWORD` and `JWT_SECRET` are not substitutes for this project's actual setting names. The Vultr inference endpoint is fixed in code; no `VULTR_BASE_URL` variable is currently read.

## 5. Start the control plane and import connections

After the prompt has fixed the Docker build context, use both interpolation files so `APP_PORT`, later `APP_DOMAIN`, and generated `POSTGRES_PASSWORD` are resolved correctly:

```bash
docker compose --env-file .env --env-file .env.runtime \
  -f compose.yaml -f deploy/compose.sandbox.yaml config --quiet

docker compose --env-file .env --env-file .env.runtime \
  -f compose.yaml -f deploy/compose.sandbox.yaml up -d --build
```

The sandbox overlay publishes PostgreSQL only at `127.0.0.1:5434` for the trusted host process. `api` and the ordinary `worker` use `db:5432` inside Compose. The `db` hostname does not resolve from a normal host process. The overlay does not start the sandbox worker by itself.

Open `http://localhost:8000` (or your chosen actual port), bootstrap the owner if needed, and go to Settings → Connections → **Import server credentials**, or enter the Vultr credential directly into its connection form. The import endpoint is `/api/connections/import-environment` and requires the authenticated owner's CSRF token. Prefer the UI rather than logging session tokens in commands.

Environment import only creates **missing** connection records. It will not replace an existing wrong, expired, disabled or revoked connection. Update/test that existing connection through its form. Changing `.env` also requires recreating affected containers before their environment changes. Use model discovery in Settings, select Vultr and the actual `PROVIDER_MODEL`, and test it. Set the GitHub repository and Tavily domain scopes before testing those connections.

## 6. Build and test the execution images

First Codex must fix the `.dockerignore` allowlist so only required public sandbox sources reach these build contexts. Preserve exclusions for `.env*`, `.git`, `.runtime`, secrets and caches.

```bash
docker build -f deploy/sandbox/Dockerfile.egress -t localhost/commander-egress:1 .
docker build -f deploy/sandbox/Dockerfile.browser -t localhost/commander-browser:1.64.1 .
```

Pre-pull the configured pinned code image once using the public image reference in `commander/settings.py`; the runner uses `--pull=never`. Docker/gVisor and Chromium namespace compatibility must pass on the real Vultr VM. Do not downgrade the runtime, add privilege, mount the host, expose the Docker daemon, or disable Chromium's sandbox to mask failures.

The following enables **only the explicit test process**, not the web app:

```bash
RUN_SANDBOX_DOCKER=1 RUN_SANDBOX_BROWSER=1 SANDBOX_TEST_RUNTIME=runsc \
  uv run pytest -q tests/test_sandbox_docker.py
```

The test file supplies its own test settings, uses `example.com` for observation, and does not establish live vision inference. For the live product, set `SANDBOX_ENABLED=true` in `.env` only after real containment succeeds, then recreate API/ordinary-worker containers with the same Compose command.

## 7. Run the native sandbox worker against the correct DB

For the **same-host, standard Compose database only**, this command derives a private loopback connection in process memory from the existing password. It neither prints the credential nor changes the saved `DATABASE_URL`. Do not use it for a differently configured or separate-VM database:

```bash
uv run python - <<'PY'
import os
from urllib.parse import quote
from dotenv import dotenv_values

values = {**dotenv_values('.env'), **dotenv_values('.env.runtime'), **os.environ}
password = values.get('POSTGRES_PASSWORD')
if not password:
    raise SystemExit('The existing Compose POSTGRES_PASSWORD is missing; recover it first.')
os.environ['DATABASE_URL'] = (
    'postgresql://commander:' + quote(password, safe='') + '@127.0.0.1:5434/commander'
)
os.environ['DATABASE_SCHEMA'] = 'commander'
from commander.sandbox.worker import main
main()
PY
```

Run this in a dedicated terminal while testing. For a separate runner VM, supply the real private-network PostgreSQL URI with TLS in that worker's service environment; do not use `db` or loopback for a remote database.

For persistence, install the existing `deploy/sandbox/commander-sandbox.service` only after preflight. It expects `/opt/thecommander`, `.venv`, an existing `commander-runner` account with the intended Docker access, a writable `.runtime`, and `/etc/thecommander/runner.env`. Populate that protected service file locally with the same `ENCRYPTION_KEY`, required bootstrap setting, actual `DATABASE_URL`, matching schema, model IDs, domain allowlist, runtime and enabled flag. Do not invent new encryption/bootstrap values. Verify systemd's permissions and the worker's ability to read only what it needs. The service manager loads `EnvironmentFile`; it is not an instruction to print that file.

Preflight/probe commands are:

```bash
uv run python -m scripts.sandbox_preflight
uv run python -m scripts.sandbox_preflight --execute-probe
```

Supply the same host-specific service environment to them. The basic preflight does not establish database access or successful live inference. The probe executes a known `6*7` program and must return `42` with an actual destroyed-container receipt.

## 8. Test, then enable HTTPS

Use an independent PostgreSQL 17 test database. On a non-root developer account with local PostgreSQL binaries, `scripts/test_db.sh` creates a disposable cluster and prints the test URI; export that exact URI as `TEST_DATABASE_URL`. In CI use the configured test service. Never reuse the application database, restore production into a disposable test schema by accident, or disable authorization tests.

```bash
./scripts/test_db.sh
# Set TEST_DATABASE_URL privately to the URI printed above.
./scripts/verify.sh
```

If PostgreSQL 17 binaries are not installed, have Codex create a disposable Docker-based test database with a distinct credential/volume/port and proper cleanup. Do not silently fall back to SQLite or skip tests. Continue until the browser regression and sandbox workflow both pass, then run live Vultr text, tool-call and vision probes and the two real product flows.

For remote HTTPS, point your real `APP_DOMAIN` DNS to the authorized Vultr VM. Set `APP_DOMAIN` in `.env`; set `PRODUCTION=true` and matching `APP_ORIGIN=https://your-real-hostname` in the effective configuration. Edit the existing `.env.runtime` `APP_ORIGIN` as well because its original `http://localhost:8000` overrides `.env` for native Python. In the Compose HTTPS overlay the process environment supplies the final HTTPS origin.

```bash
docker compose --env-file .env --env-file .env.runtime \
  -f compose.yaml -f deploy/compose.sandbox.yaml -f compose.https.yaml config --quiet

docker compose --env-file .env --env-file .env.runtime \
  -f compose.yaml -f deploy/compose.sandbox.yaml -f compose.https.yaml up -d --build
```

The normal `scripts/start.sh` does not include the sandbox or HTTPS overlays. Use the explicit commands above for that topology. `WORKSPACE_ROOT`/schema/database values inside Compose are explicitly supplied by `compose.yaml`; changing just the same variable in `.env` does not override those container values.

Keep ports 5434/5432 and Docker's daemon private. Check API readiness, sandbox heartbeat, login/session revocation, memory and schedules, backups/restore, real Python output and a controlled public HTTPS form. Approve browser effects yourself in the app; Codex must not manufacture or automatically accept your approval.

## 9. Start Codex with the complete prompt

From this repository with your normal Codex authentication:

```bash
test "$(git branch --show-current)" = vultr
codex "$(cat docs/VULTR_MANUAL_RELEASE_PROMPT.md)"
```

The prompt file contains instructions, not credentials. It is deliberately interactive, so you can enter secrets in a local editor and review browser actions yourself. The CLI accepts an initial prompt argument; no automatic-approval or sandbox-bypass flags are needed. Official reference: [Codex CLI](https://learn.chatgpt.com/docs/cli/reference).
