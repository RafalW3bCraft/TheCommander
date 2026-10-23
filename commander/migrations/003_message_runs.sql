-- Associate new conversation turns with their run so queued future prompts cannot
-- enter an earlier task's model context. Keep historical messages intact.
ALTER TABLE messages ADD COLUMN run_id uuid;
ALTER TABLE messages ADD CONSTRAINT messages_run_owner_fk
 FOREIGN KEY(run_id,owner_id) REFERENCES runs(id,owner_id);
CREATE INDEX messages_run_idx ON messages(run_id);
