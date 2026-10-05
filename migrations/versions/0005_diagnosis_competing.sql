-- 0005: keep the competing root candidates of each diagnosis (additive, nullable; nothing is rewritten).
ALTER TABLE IF EXISTS diagnosis_events ADD COLUMN IF NOT EXISTS competing JSON;
