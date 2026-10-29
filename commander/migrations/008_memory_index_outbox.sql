-- Derived-index updates are durable, including deletes; never store a second text copy.
CREATE TABLE memory_index_jobs (
 memory_id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES owners(id),
 project_id uuid,
 revision integer NOT NULL CHECK(revision > 0),
 deleted boolean NOT NULL DEFAULT false,
 attempts integer NOT NULL DEFAULT 0,
 available_at timestamptz NOT NULL DEFAULT now(),
 lease_until timestamptz,
 last_error text,
 updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE memory_index_state (
 memory_id uuid PRIMARY KEY,
 owner_id uuid NOT NULL REFERENCES owners(id),
 project_id uuid,
 revision integer NOT NULL,
 expires_at timestamptz,
 truncated boolean NOT NULL DEFAULT false,
 synced_at timestamptz NOT NULL DEFAULT now()
);
CREATE FUNCTION queue_memory_index() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE item memories; removing boolean;
BEGIN
 removing := TG_OP = 'DELETE';
 IF removing THEN item := OLD; ELSE item := NEW; END IF;
 INSERT INTO memory_index_jobs(memory_id,owner_id,project_id,revision,deleted)
 VALUES(item.id,item.owner_id,item.project_id,item.revision + CASE WHEN removing THEN 1 ELSE 0 END,removing)
 ON CONFLICT(memory_id) DO UPDATE SET revision=EXCLUDED.revision,deleted=EXCLUDED.deleted,
 attempts=0,available_at=now(),lease_until=NULL,last_error=NULL,updated_at=now();
 RETURN NULL;
END $$;
CREATE TRIGGER memory_index_outbox AFTER INSERT OR UPDATE OR DELETE ON memories
 FOR EACH ROW EXECUTE FUNCTION queue_memory_index();
INSERT INTO memory_index_jobs(memory_id,owner_id,project_id,revision)
 SELECT id,owner_id,project_id,revision FROM memories;
CREATE INDEX memory_index_due ON memory_index_jobs(available_at);
