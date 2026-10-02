-- 0001: columns that were added after the first release (formerly the ADDED_COLUMNS ALTER list).
ALTER TABLE IF EXISTS diagnosis_events ADD COLUMN IF NOT EXISTS confidence_level VARCHAR(10);
ALTER TABLE IF EXISTS diagnosis_events ADD COLUMN IF NOT EXISTS explanation TEXT;
