-- Opaque public session IDs are distinct from authentication token digests.
ALTER TABLE auth_sessions ADD COLUMN session_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE;
ALTER TABLE auth_sessions ADD COLUMN created_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE auth_sessions ADD COLUMN reauthenticated_at timestamptz;
-- Existing sessions require fresh credentials before a future sensitive action.
CREATE TABLE auth_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES owners(id),
 session_id uuid NOT NULL,
 kind text NOT NULL CHECK(kind IN ('reauthenticated','session_revoked')),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX auth_events_owner ON auth_events(owner_id,created_at DESC);
