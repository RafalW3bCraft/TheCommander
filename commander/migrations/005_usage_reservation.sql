-- Keep the original conservative reserve when a request's usage is unknown.
-- Old unknown rows use the largest supported context/output bound until expiry.
ALTER TABLE usage ADD COLUMN reserved_tokens integer NOT NULL DEFAULT 108192
 CHECK(reserved_tokens > 0);
