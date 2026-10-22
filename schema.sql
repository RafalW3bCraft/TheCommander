-- TheCommander Database Schema
-- PostgreSQL 17 · Rebuild for Nebius x NVIDIA Hackathon
-- Run: psql -h 127.0.0.1 -p 5433 -U thecommander -d thecommander_db -f schema.sql

-- Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- full-text fuzzy search on memories

-- ─────────────────────────────────────────────────
-- OWNERS (single-owner system; always owner_id = 1)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS owners (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────
-- MEMORIES (persistent, owner-scoped)
-- Replaces: in-process knowledge_store + JSON file
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS memories (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id     INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    type         TEXT NOT NULL CHECK (type IN ('profile','episodic','task','procedural','evidence')),
    key          TEXT NOT NULL,
    content      TEXT NOT NULL,
    source       TEXT,                         -- URL | 'user_explicit' | 'inferred'
    sensitivity  TEXT NOT NULL DEFAULT 'private' CHECK (sensitivity IN ('private','shared')),
    observed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ,
    revision     INTEGER NOT NULL DEFAULT 1,
    UNIQUE(owner_id, type, key)
);
CREATE INDEX IF NOT EXISTS idx_memories_owner_type ON memories(owner_id, type);
CREATE INDEX IF NOT EXISTS idx_memories_content_trgm ON memories USING GIN(content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_memories_key_trgm    ON memories USING GIN(key gin_trgm_ops);

-- ─────────────────────────────────────────────────
-- SESSIONS (conversation sessions)
-- Replaces: in-process conversation_history dict
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_owner ON sessions(owner_id);

-- ─────────────────────────────────────────────────
-- MESSAGES (conversation messages per session)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id         BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user','assistant','tool','system')),
    content    TEXT NOT NULL,
    tool_name  TEXT,                          -- if role='tool'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

-- ─────────────────────────────────────────────────
-- SKILLS (versioned skill definitions)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skills (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id     INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    version      TEXT NOT NULL DEFAULT '1.0.0',
    content_hash TEXT NOT NULL,
    description  TEXT,
    definition   JSONB NOT NULL DEFAULT '{}',  -- inputs, tools, steps, budgets
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','draft','disabled')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(owner_id, name, version)
);

-- ─────────────────────────────────────────────────
-- RUNS (durable task/run records)
-- Replaces: in-memory CommandCenter task history
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id    INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    skill_id    UUID REFERENCES skills(id),
    intent      TEXT NOT NULL,
    inputs      JSONB DEFAULT '{}',
    status      TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued','running','waiting_approval','succeeded','failed','cancelled','denied','uncertain')),
    lease_id    UUID,
    lease_until TIMESTAMPTZ,
    result      JSONB,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_runs_owner_status ON runs(owner_id, status);
CREATE INDEX IF NOT EXISTS idx_runs_lease        ON runs(status, lease_until) WHERE status = 'running';

-- ─────────────────────────────────────────────────
-- RUN EVENTS (checkpoints / audit trail)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS run_events (
    id         BIGSERIAL PRIMARY KEY,
    run_id     UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,                  -- started|tool_call|tool_result|checkpoint|finished|error
    payload    JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_run_events_run ON run_events(run_id, created_at);

-- ─────────────────────────────────────────────────
-- ACTION RECEIPTS (every external write has a receipt)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS action_receipts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    owner_id        INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    connector       TEXT NOT NULL,             -- github|notes|calendar|tavily|files
    action_type     TEXT NOT NULL,             -- create_issue|write_file|search|etc
    arguments_hash  TEXT NOT NULL,             -- SHA256 of normalized args
    grant_ref       TEXT,                      -- grant_id reference
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','succeeded','failed','uncertain')),
    provider_result JSONB,                     -- raw provider response
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_receipts_owner ON action_receipts(owner_id, created_at);
CREATE INDEX IF NOT EXISTS idx_receipts_run   ON action_receipts(run_id);

-- ─────────────────────────────────────────────────
-- SCHEDULES (durable cron/one-shot job records)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    skill_id        UUID NOT NULL REFERENCES skills(id),
    cron_expr       TEXT,                       -- e.g. "0 9 * * 1-5"
    run_at          TIMESTAMPTZ,                -- one-shot
    iana_timezone   TEXT NOT NULL DEFAULT 'UTC',
    misfire_policy  TEXT NOT NULL DEFAULT 'catchup_once'
                    CHECK (misfire_policy IN ('catchup_once','skip','catchup_all')),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','deleted')),
    last_run_at     TIMESTAMPTZ,
    next_run_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_schedules_owner  ON schedules(owner_id, status);
CREATE INDEX IF NOT EXISTS idx_schedules_next   ON schedules(next_run_at) WHERE status = 'active';

-- ─────────────────────────────────────────────────
-- GRANTS (connector policy / permissions)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grants (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id   INTEGER NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
    connector  TEXT NOT NULL,                  -- github|notes|calendar|tavily
    scope      TEXT NOT NULL,                  -- e.g. "repo:read", "issues:create"
    policy     TEXT NOT NULL DEFAULT 'approval_required'
               CHECK (policy IN ('allowed','approval_required','denied')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_grants_owner ON grants(owner_id, connector, scope);

-- ─────────────────────────────────────────────────
-- INFERENCE LOG (Nebius usage + cost tracking)
-- ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS inference_log (
    id             BIGSERIAL PRIMARY KEY,
    run_id         UUID REFERENCES runs(id),
    owner_id       INTEGER NOT NULL REFERENCES owners(id),
    provider       TEXT NOT NULL DEFAULT 'nebius',
    model_id       TEXT NOT NULL,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    latency_ms     INTEGER,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_inference_owner_day ON inference_log(owner_id, created_at);

-- ─────────────────────────────────────────────────
-- SEED: default owner (change password before deployment!)
-- password_hash is bcrypt of "changeme" — CHANGE THIS
-- ─────────────────────────────────────────────────
INSERT INTO owners (username, password_hash)
VALUES ('commander', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeXPFXRlORo2KhFUy')
ON CONFLICT (username) DO NOTHING;
