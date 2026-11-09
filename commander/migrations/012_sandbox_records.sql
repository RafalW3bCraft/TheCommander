-- Additive execution evidence; cancellation must not erase the observed outcome.
ALTER TABLE sandbox_jobs ADD CONSTRAINT sandbox_jobs_id_owner UNIQUE(id,owner_id);
CREATE TABLE sandbox_attempts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 job_id uuid NOT NULL,
 owner_id uuid NOT NULL,
 lease_token uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN ('code','browser')),
 container_name text NOT NULL,
 receipt jsonb NOT NULL DEFAULT '{}',
 error_code text,
 started_at timestamptz NOT NULL DEFAULT now(),
 finished_at timestamptz,
 UNIQUE(id,job_id,owner_id),
 FOREIGN KEY(job_id,owner_id) REFERENCES sandbox_jobs(id,owner_id)
);
CREATE INDEX sandbox_attempts_job ON sandbox_attempts(job_id,started_at);
CREATE TABLE sandbox_artifacts (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 job_id uuid NOT NULL,
 owner_id uuid NOT NULL,
 attempt_id uuid NOT NULL,
 name text NOT NULL CHECK(name ~ '^[A-Za-z0-9][A-Za-z0-9_. -]{0,99}$'),
 media_type text NOT NULL CHECK(media_type IN ('text/plain','text/csv','application/json')),
 data bytea CHECK(octet_length(data)<=1048576),
 deleted_at timestamptz,
 CHECK((data IS NULL)=(deleted_at IS NOT NULL)),
 sha256 text NOT NULL CHECK(sha256 ~ '^[a-f0-9]{64}$'),
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(job_id,owner_id) REFERENCES sandbox_jobs(id,owner_id),
 FOREIGN KEY(attempt_id,job_id,owner_id) REFERENCES sandbox_attempts(id,job_id,owner_id)
);
CREATE INDEX sandbox_artifacts_owner ON sandbox_artifacts(owner_id,job_id);
CREATE TABLE sandbox_calls (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 job_id uuid NOT NULL,
 owner_id uuid NOT NULL,
 phase text NOT NULL,
 provider text NOT NULL CHECK(provider='vultr'),
 model text NOT NULL,
 status text NOT NULL DEFAULT 'started' CHECK(status IN ('started','succeeded','failed')),
 input_tokens bigint,
 output_tokens bigint,
 duration_ms integer,
 error_code text,
 created_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY(job_id,owner_id) REFERENCES sandbox_jobs(id,owner_id)
);
CREATE INDEX sandbox_calls_job ON sandbox_calls(owner_id,job_id,created_at);
