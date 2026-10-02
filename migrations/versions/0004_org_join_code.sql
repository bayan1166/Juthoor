-- 0004: organization join code (SHA-256 hex). NULL = no code issued yet (issue one with scripts/org_join_code.py).
ALTER TABLE IF EXISTS organizations ADD COLUMN IF NOT EXISTS join_code_hash VARCHAR(64);
