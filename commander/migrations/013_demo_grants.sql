-- Credentials remain in the operator connection; personal accounts receive only
-- revocable authority. Unknown consumption retains its conservative reservation.
CREATE TABLE demo_provider_pools (
 operator_id uuid PRIMARY KEY REFERENCES owners(id),
 max_usd numeric NOT NULL CHECK(max_usd>0),
 max_tokens bigint NOT NULL CHECK(max_tokens>0),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE demo_provider_grants (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 owner_id uuid UNIQUE NOT NULL REFERENCES owners(id),
 operator_id uuid NOT NULL REFERENCES demo_provider_pools(operator_id),
 connection_revision integer NOT NULL,
 model text NOT NULL,
 prices jsonb NOT NULL CHECK(jsonb_typeof(prices)='object'),
 max_usd numeric NOT NULL CHECK(max_usd>0),
 max_tokens bigint NOT NULL CHECK(max_tokens>0),
 max_runs integer NOT NULL CHECK(max_runs>0),
 expires_at timestamptz NOT NULL,
 revoked_at timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(id,owner_id)
);
ALTER TABLE usage ADD COLUMN demo_grant_id uuid;
ALTER TABLE usage ADD COLUMN reserved_cost_usd numeric CHECK(reserved_cost_usd>=0);
ALTER TABLE usage ADD CONSTRAINT usage_demo_grant_owner_fk
 FOREIGN KEY(demo_grant_id,owner_id) REFERENCES demo_provider_grants(id,owner_id);
CREATE INDEX usage_demo_grant_idx ON usage(demo_grant_id);
