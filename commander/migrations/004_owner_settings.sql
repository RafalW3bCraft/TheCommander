CREATE TABLE owner_settings (
 owner_id uuid PRIMARY KEY REFERENCES owners(id) ON DELETE CASCADE,
 preferences jsonb NOT NULL DEFAULT '{}',
 revision integer NOT NULL DEFAULT 1,
 updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE runs ADD COLUMN settings_snapshot jsonb;
