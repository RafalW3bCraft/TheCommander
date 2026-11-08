# 005 — Private, derived Mem0 storage index

Date: 2026-10-29. Status: implemented and locally verified with controlled tests and real local Mem0/pgvector/E5 smoke.

## Decision and boundary

Keep Commander PostgreSQL authoritative for memory admission, owner/project scope,
revisions, expiry, corrections and deletion. Use Mem0 **2.2.1's pgvector storage
backend** in a separate private service for derived retrieval. This implements the
bounded indexing portion of milestone 3, not Mem0's automated extraction, memory
proposals, summaries, document ingestion or a new agent runtime.

Do not instantiate `mem0.Memory`: its defaults initialize external inference and
embedding providers. Import `mem0.vector_stores.pgvector.PGVector` explicitly and
supply every connection/storage option. The separately locked dependency graph
includes Mem0's upstream OpenAI/Qdrant dependencies; they are not configured or
invoked by this service. Telemetry is disabled. No provider API key is required.

Use local CPU `intfloat/multilingual-e5-small` at immutable revision
`614241f622f53c4eeff9890bdc4f31cfecc418b3`, 384 dimensions. Model files are fetched
at image build; runtime uses `local_files_only=True` and offline environment flags.
The model declares MIT licensing. The full memory-service dependency graph is in
`memory_service/uv.lock`, independent of the application lock. Mem0's inspected
PyPI wheel version 2.2.1 provided the verified constructor, filter, update and
keyword-search signatures. This is not a security review of every dependency.

## Retrieval and consistency

The application sends only admitted canonical records: UUID owner, optional UUID
project, UUID memory ID, monotonic revision and text. Exact scope filters apply
before both semantic and lexical queries. Results use reciprocal-rank fusion;
the score is rank information, never factual confidence. The service returns IDs,
revisions and scores, not authority-bearing text. The caller must reload records
and check current revision, owner/project scope and expiry before using content.

E5 uses `passage: ` and `query: ` prefixes with normalized vectors. The input
contract is at most 4,000 record characters or 2,000 query characters; embeddings
use the first supported sequence of at most 512 tokens, preserving the model's
special tokens. Upsert acknowledges `truncated`; search returns
`query_truncated`. Canonical content is unchanged. This is prefix indexing, not
full-document chunking. The UI must disclose the bound and degraded status.

Cross-process PostgreSQL advisory locks serialize mutations per scoped record.
Equal-revision, identical-content upserts are idempotent; mismatched content or
older revisions are rejected. Deletion retains a text-free revision tombstone.
Equal/older late upserts cannot resurrect it; a newer canonical correction can
renew expired memory. Older deletions cannot remove newer corrections. Do not
purge tombstones without proving all older work is drained. Application-side
final validation remains mandatory even with these index safeguards.

## Deployment contract

The optional overlay is selected explicitly from the repository root:

```sh
# Supply private MEMORY_ADMIN_PASSWORD, MEMORY_DB_PASSWORD and MEMORY_INDEX_TOKEN
# through the operator's secret environment; use distinct random values.
docker compose --env-file .env.runtime -f compose.yaml -f deploy/compose.memory.yaml --profile memory up -d --build
```

The main application's existing private environment must already be configured.
This command is an operator procedure, not evidence it was executed here. The
overlay has **no host-published memory ports**. API/worker join `memory-private`;
the index/database are attached only to that internal network. The index gets
`MEMORY_DB_*` connection fields, never the primary application database password.
The pgvector image is pinned to the inspected Linux amd64 manifest; other
architectures need a separately reviewed image digest.

A fresh dedicated volume initializes pgvector under `memory_admin` and creates
restricted login `memory_index`. The service role can manage its derived tables
in this separate database but is not superuser. The index container runs as UID
10002 with read-only root, dropped capabilities, limited CPU/memory/PIDs and
bounded temporary storage. PostgreSQL data is persistent in its own volume.
Existing application volumes, encryption keys and environments are untouched.

`MEMORY_INDEX_TOKEN` is an operator secret supplied through the environment, not
an application-encrypted credential. It is never returned or logged by endpoints;
operators must protect their secret storage and container inspection access.
HTTP is acceptable only inside the private Compose network/loopback; off-host
index connections require HTTPS. Constant-time authentication precedes request
body reads; requests are limited to 32 KiB and five seconds of body read time.
Routes have bounded concurrency and redacted errors. HTTP clients disallow
redirects and environment proxies, and bound timeouts and response bytes.

An unavailable service, malformed response or failed lexical query means degraded
canonical recall, not successful semantic search. Do not enable this overlay until
the operator accepts the additional database backup/restore and monitoring duties.

## Verification and remaining gates

Controlled tests in `tests/test_memory_index.py` cover the client/service boundary,
constant-time credential path, input/error redaction, excessive input, response
limits, redirects, owner/project filters, monotonic updates, deletion, renewal,
unknown acknowledgements and explicit truncation. They use controlled transports
and fake embeddings and must not be represented as real semantic acceptance.

Reproducible separate-service commands:

```sh
uv sync --project memory_service --frozen
uv run pytest -q tests/test_memory_index.py
uv run ruff check commander/memory_index.py memory_service tests/test_memory_index.py
uv run mypy commander/memory_index.py
uv run pip-audit --path memory_service/.venv/lib/python3.13/site-packages --skip-editable --timeout 60
memory_service/.venv/bin/python -m memory_service.smoke --download-model
```

The smoke command downloads the pinned public model only with the explicit flag,
creates its own randomly named disposable pgvector container with ephemeral
credentials and no retained volumes, exercises real local embeddings/storage,
and removes only that container. Later runs can omit `--download-model`. It never
uses a supplied application database or an existing container. Smoke data is
fictional. It does not prove the target recall@5, production availability,
container image build, full memory proposals, extraction or quality evaluation.

Current controlled result: **14 tests passed**. Separate lock resolution and local
dependency installation succeeded. A real local model/database smoke passed at
2026-10-29 11:15 UTC, using a disposable container removed afterward. Commands,
source-file hashes, timings and the final repeat are in
[service evidence](../evidence/upgrade-memory-service.json). The isolated dependency
audit found no known vulnerabilities; its direct PyPI check skipped the CPU Torch
wheel's `+cpu` version. A separate normalized `torch==2.15.0` advisory lookup also
found no known vulnerabilities; neither is a binary-security certification.
Optional container image build/startup evidence is separate from the local smoke;
do not infer an operational deployment from either.

## Sources inspected

- [Mem0 pgvector configuration](https://docs.mem0.ai/components/vectordbs/dbs/pgvector)
- [Mem0 Python quickstart and default external providers](https://docs.mem0.ai/open-source/python-quickstart)
- [Mem0 2.2.1 distribution](https://pypi.org/project/mem0ai/2.2.1/)
- [Pinned E5 model](https://huggingface.co/intfloat/multilingual-e5-small/tree/614241f622f53c4eeff9890bdc4f31cfecc418b3)
