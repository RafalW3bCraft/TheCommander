-- Additive: preserve existing provider selections, secrets and application runs.
ALTER TABLE connections DROP CONSTRAINT connections_kind_check;
ALTER TABLE connections ADD CONSTRAINT connections_kind_check
 CHECK(kind IN ('nebius','github','tavily','workspace','openai','anthropic','vultr'));
ALTER TABLE usage DROP CONSTRAINT usage_provider_check;
ALTER TABLE usage ADD CONSTRAINT usage_provider_check
 CHECK(provider IN ('nebius','openai','anthropic','vultr'));
CREATE TABLE sandbox_jobs (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 owner_id uuid NOT NULL REFERENCES owners(id),
 project_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN ('code','browser')),
 goal text NOT NULL,
 url text NOT NULL DEFAULT '',
 status text NOT NULL DEFAULT 'queued' CHECK(status IN
 ('queued','running','waiting_approval','approved','succeeded','failed','cancelled','denied','uncertain')),
 plan jsonb,
 evidence jsonb NOT NULL DEFAULT '{}',
 receipt jsonb NOT NULL DEFAULT '{}',
 approval_snapshot jsonb NOT NULL DEFAULT '{}',
 events jsonb NOT NULL DEFAULT '[]',
 approval_digest text,
 approval_expires_at timestamptz,
 approved_at timestamptz,
 lease_token uuid,
 lease_until timestamptz,
 error text,
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(project_id,owner_id) REFERENCES projects(id,owner_id)
);
CREATE INDEX sandbox_jobs_owner ON sandbox_jobs(owner_id,project_id,created_at DESC);
CREATE INDEX sandbox_jobs_queue ON sandbox_jobs(status,created_at);
CREATE TABLE sandbox_heartbeats (
 id text PRIMARY KEY,
 seen_at timestamptz NOT NULL DEFAULT now()
);
