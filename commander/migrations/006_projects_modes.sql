-- Add project scope without widening the permissions of existing owners/runs.
CREATE TABLE projects (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 owner_id uuid NOT NULL REFERENCES owners(id),
 name text NOT NULL CHECK(length(btrim(name)) BETWEEN 1 AND 120),
 is_default boolean NOT NULL DEFAULT false,
 revision integer NOT NULL DEFAULT 1,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(id,owner_id)
);
CREATE UNIQUE INDEX projects_default_owner ON projects(owner_id) WHERE is_default;
INSERT INTO projects(owner_id,name,is_default) SELECT id,'Personal',true FROM owners;
CREATE FUNCTION create_owner_project() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO projects(owner_id,name,is_default) VALUES(NEW.id,'Personal',true);
 RETURN NEW;
END $$;
CREATE TRIGGER owner_default_project AFTER INSERT ON owners
 FOR EACH ROW EXECUTE FUNCTION create_owner_project();
ALTER TABLE conversations ADD COLUMN project_id uuid;
ALTER TABLE schedules ADD COLUMN project_id uuid;
ALTER TABLE runs ADD COLUMN project_id uuid;
ALTER TABLE runs ADD COLUMN mode text NOT NULL DEFAULT 'automate'
 CHECK(mode IN ('ask','plan','research','build','review','automate'));
UPDATE conversations c SET project_id=p.id FROM projects p WHERE p.owner_id=c.owner_id AND p.is_default;
UPDATE schedules s SET project_id=p.id FROM projects p WHERE p.owner_id=s.owner_id AND p.is_default;
UPDATE runs r SET project_id=p.id FROM projects p WHERE p.owner_id=r.owner_id AND p.is_default;
CREATE FUNCTION assign_default_project() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.project_id IS NULL THEN
  SELECT id INTO NEW.project_id FROM projects WHERE owner_id=NEW.owner_id AND is_default;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER conversation_default_project BEFORE INSERT ON conversations
 FOR EACH ROW EXECUTE FUNCTION assign_default_project();
CREATE TRIGGER schedule_default_project BEFORE INSERT ON schedules
 FOR EACH ROW EXECUTE FUNCTION assign_default_project();
CREATE TRIGGER run_default_project BEFORE INSERT ON runs
 FOR EACH ROW EXECUTE FUNCTION assign_default_project();
ALTER TABLE conversations ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE schedules ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE runs ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE conversations ADD FOREIGN KEY(project_id,owner_id) REFERENCES projects(id,owner_id);
ALTER TABLE schedules ADD FOREIGN KEY(project_id,owner_id) REFERENCES projects(id,owner_id);
ALTER TABLE runs ADD FOREIGN KEY(project_id,owner_id) REFERENCES projects(id,owner_id);
ALTER TABLE conversations ADD UNIQUE(id,owner_id,project_id);
ALTER TABLE schedules ADD UNIQUE(id,owner_id,project_id);
ALTER TABLE runs ADD FOREIGN KEY(conversation_id,owner_id,project_id) REFERENCES conversations(id,owner_id,project_id);
ALTER TABLE runs ADD FOREIGN KEY(schedule_id,owner_id,project_id) REFERENCES schedules(id,owner_id,project_id) ON DELETE SET NULL (schedule_id);
CREATE INDEX conversations_project_idx ON conversations(owner_id,project_id,created_at DESC);
CREATE INDEX runs_project_idx ON runs(owner_id,project_id,created_at DESC);
-- Null memory scope means a deliberate owner-wide preference (legacy behavior).
ALTER TABLE memories ADD COLUMN project_id uuid;
ALTER TABLE memories ADD FOREIGN KEY(project_id,owner_id) REFERENCES projects(id,owner_id);
ALTER TABLE memories DROP CONSTRAINT memories_owner_id_kind_key_key;
CREATE UNIQUE INDEX memory_scoped_key ON memories(owner_id,project_id,kind,key) NULLS NOT DISTINCT;
