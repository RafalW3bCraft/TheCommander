-- Optional providers do not change existing connections or Nebius defaults.
ALTER TABLE connections DROP CONSTRAINT connections_kind_check;
ALTER TABLE connections ADD CONSTRAINT connections_kind_check
 CHECK (kind IN ('nebius','github','tavily','workspace','openai','anthropic'));
ALTER TABLE usage ADD COLUMN provider text NOT NULL DEFAULT 'nebius'
 CHECK (provider IN ('nebius','openai','anthropic'));
