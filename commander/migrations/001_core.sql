CREATE TABLE owners (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), username text UNIQUE NOT NULL,
 password_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE auth_sessions (
 token_hash text PRIMARY KEY, owner_id uuid NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
 csrf text NOT NULL, expires_at timestamptz NOT NULL
);
CREATE TABLE rate_limits (key text PRIMARY KEY, window_at timestamptz NOT NULL DEFAULT now(), count integer NOT NULL);
CREATE TABLE memories (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL REFERENCES owners(id),
 kind text NOT NULL CHECK (kind IN ('explicit','inferred','episodic','task','evidence','procedural')),
 key text NOT NULL, content text NOT NULL, source text NOT NULL, sensitivity text NOT NULL DEFAULT 'private',
 observed_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 expires_at timestamptz, revision integer NOT NULL DEFAULT 1, UNIQUE(owner_id,kind,key)
);
CREATE TABLE conversations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL REFERENCES owners(id),
 title text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(id,owner_id)
);
CREATE TABLE messages (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, owner_id uuid NOT NULL REFERENCES owners(id),
 conversation_id uuid NOT NULL, role text NOT NULL CHECK (role IN ('user','assistant')),
 content text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (conversation_id,owner_id) REFERENCES conversations(id,owner_id) ON DELETE CASCADE
);
CREATE TABLE connections (
 owner_id uuid NOT NULL REFERENCES owners(id), kind text NOT NULL CHECK(kind IN ('nebius','github','tavily','workspace')),
 secret bytea, config jsonb NOT NULL DEFAULT '{}', status text NOT NULL DEFAULT 'configured',
 revision integer NOT NULL DEFAULT 1, validated_at timestamptz, detail text,
 PRIMARY KEY(owner_id,kind)
);
CREATE TABLE schedules (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL REFERENCES owners(id),
 skill text NOT NULL, prompt text NOT NULL, timezone text NOT NULL, next_at timestamptz,
 interval_seconds integer CHECK(interval_seconds >= 60), paused boolean NOT NULL DEFAULT false,
 revision integer NOT NULL DEFAULT 1, last_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(id,owner_id)
);
CREATE TABLE runs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL REFERENCES owners(id),
 conversation_id uuid, schedule_id uuid, occurrence_at timestamptz,
 skill text NOT NULL, skill_version text NOT NULL, prompt text NOT NULL,
 status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','waiting_approval','succeeded','failed','uncertain','cancelled')),
 result text, error text, lease_token uuid, lease_until timestamptz, attempts integer NOT NULL DEFAULT 0,
 available_at timestamptz NOT NULL DEFAULT now(), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(schedule_id,occurrence_at), UNIQUE(id,owner_id),
 FOREIGN KEY(conversation_id,owner_id) REFERENCES conversations(id,owner_id),
 FOREIGN KEY(schedule_id,owner_id) REFERENCES schedules(id,owner_id) ON DELETE SET NULL (schedule_id)
);
CREATE TABLE events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
 kind text NOT NULL, payload jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE evidence (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), run_id uuid NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
 url text NOT NULL, title text NOT NULL, excerpt text NOT NULL, fetched_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE actions (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), owner_id uuid NOT NULL REFERENCES owners(id), run_id uuid NOT NULL,
 tool text NOT NULL, arguments jsonb NOT NULL, args_hash text NOT NULL, connection_revision integer NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','executing','succeeded','uncertain','denied','failed')),
 expires_at timestamptz NOT NULL DEFAULT now()+interval '30 minutes', approved_at timestamptz,
 receipt jsonb, error text, created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(run_id,owner_id) REFERENCES runs(id,owner_id) ON DELETE CASCADE
);
CREATE TABLE usage (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, owner_id uuid NOT NULL REFERENCES owners(id),
 run_id uuid REFERENCES runs(id), model text NOT NULL, tokens jsonb, cost_usd numeric,
 latency_ms integer NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE worker_heartbeats (id text PRIMARY KEY, seen_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX memories_owner_idx ON memories(owner_id,kind);
CREATE INDEX messages_conversation_idx ON messages(conversation_id,id);
CREATE INDEX runs_queue_idx ON runs(status,available_at,created_at);
CREATE INDEX runs_owner_idx ON runs(owner_id,created_at DESC);
CREATE INDEX schedules_due_idx ON schedules(next_at) WHERE NOT paused;
CREATE INDEX actions_run_idx ON actions(run_id);
CREATE INDEX events_run_idx ON events(run_id,id);
CREATE INDEX evidence_run_idx ON evidence(run_id);
CREATE INDEX usage_owner_idx ON usage(owner_id,created_at);
