-- Additive, forward-only account expansion. Rollback deploys must retain these
-- columns/tables and the disabled-account authorization checks. Test restoration
-- against an isolated backup before applying to an existing installation.
ALTER TABLE owners ADD COLUMN role text NOT NULL DEFAULT 'personal'
 CHECK(role IN ('operator','personal'));
ALTER TABLE owners ADD COLUMN disabled_at timestamptz;
ALTER TABLE owners ADD COLUMN display_name text NOT NULL DEFAULT ''
 CHECK(length(display_name)<=120);
-- Only the original bootstrap principal gains operator authority. Invitations
-- and direct future INSERTs always default to personal.
UPDATE owners SET role='operator' WHERE id=(SELECT id FROM owners ORDER BY created_at,id LIMIT 1);

CREATE TABLE workspaces (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 owner_id uuid UNIQUE NOT NULL REFERENCES owners(id),
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(id,owner_id)
);
INSERT INTO workspaces(owner_id) SELECT id FROM owners;
CREATE FUNCTION create_account_workspace() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 INSERT INTO workspaces(owner_id) VALUES(NEW.id);
 RETURN NEW;
END $$;
-- AFTER triggers execute alphabetically; workspace exists before the retained
-- owner_default_project trigger creates its default project.
CREATE TRIGGER owner_account_workspace AFTER INSERT ON owners
 FOR EACH ROW EXECUTE FUNCTION create_account_workspace();
ALTER TABLE projects ADD COLUMN workspace_id uuid;
UPDATE projects p SET workspace_id=w.id FROM workspaces w WHERE w.owner_id=p.owner_id;
CREATE FUNCTION assign_account_workspace() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.workspace_id IS NULL THEN
  SELECT id INTO NEW.workspace_id FROM workspaces WHERE owner_id=NEW.owner_id;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER project_account_workspace BEFORE INSERT ON projects
 FOR EACH ROW EXECUTE FUNCTION assign_account_workspace();
ALTER TABLE projects ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE projects ADD CONSTRAINT projects_workspace_owner_fk
 FOREIGN KEY(workspace_id,owner_id) REFERENCES workspaces(id,owner_id);

CREATE TABLE account_invitations (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 token_hash text NOT NULL UNIQUE,
 created_by uuid NOT NULL REFERENCES owners(id),
 purpose text NOT NULL CHECK(purpose IN ('personal','judge')),
 expires_at timestamptz NOT NULL,
 consumed_at timestamptz,
 consumed_by uuid REFERENCES owners(id),
 revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 CHECK((consumed_at IS NULL)=(consumed_by IS NULL))
);
CREATE TABLE account_events (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor_id uuid NOT NULL REFERENCES owners(id),
 subject_id uuid REFERENCES owners(id),
 kind text NOT NULL CHECK(kind IN ('registered','invitation_created','invitation_revoked',
  'profile_updated','password_changed','sessions_revoked','account_disabled')),
 created_at timestamptz NOT NULL DEFAULT now()
);
-- Preserve the existing run FK and add tenant identity to its relationship.
ALTER TABLE usage ADD CONSTRAINT usage_run_owner_fk
 FOREIGN KEY(run_id,owner_id) REFERENCES runs(id,owner_id);
-- Index tombstones deliberately outlive memories; project scope can still be
-- enforced without an FK to the deleted memory itself.
ALTER TABLE memory_index_jobs ADD CONSTRAINT memory_jobs_project_owner_fk
 FOREIGN KEY(project_id,owner_id) REFERENCES projects(id,owner_id);
ALTER TABLE memory_index_state ADD CONSTRAINT memory_state_project_owner_fk
 FOREIGN KEY(project_id,owner_id) REFERENCES projects(id,owner_id);
