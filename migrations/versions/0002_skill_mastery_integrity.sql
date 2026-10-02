-- 0002: one mastery row per (student, skill) and impossible values rejected by the database.
-- Existing data is repaired first so the constraints can be added to a database that already has
-- duplicates or out-of-range values. Idempotent: safe to run on a database that already has them.

-- 1. Collapse duplicate rows, keeping the one with the most attempts (then the newest, then the highest id).
DELETE FROM skill_mastery a
 USING skill_mastery b
 WHERE a.student_id = b.student_id
   AND a.skill_id = b.skill_id
   AND a.id <> b.id
   AND (a.attempts, COALESCE(a.updated_at, TIMESTAMP 'epoch'), a.id::text)
     < (b.attempts, COALESCE(b.updated_at, TIMESTAMP 'epoch'), b.id::text);

-- 2. Repair impossible values (clamp into the open interval used by the engine).
UPDATE skill_mastery SET p_mastery = 0.3 WHERE p_mastery IS NULL;
UPDATE skill_mastery SET p_mastery = LEAST(0.999, GREATEST(0.001, p_mastery))
 WHERE p_mastery <= 0 OR p_mastery >= 1;
UPDATE skill_mastery SET attempts = 0 WHERE attempts IS NULL OR attempts < 0;
UPDATE skill_mastery SET correct = 0 WHERE correct IS NULL OR correct < 0;
UPDATE skill_mastery SET correct = attempts WHERE correct > attempts;

-- 3. Constraints (names match the SQLAlchemy model).
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_skill_mastery_student_skill') THEN
    ALTER TABLE skill_mastery ADD CONSTRAINT uq_skill_mastery_student_skill UNIQUE (student_id, skill_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_skill_mastery_p_open_interval') THEN
    ALTER TABLE skill_mastery ADD CONSTRAINT ck_skill_mastery_p_open_interval CHECK (p_mastery > 0 AND p_mastery < 1);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_skill_mastery_counts') THEN
    ALTER TABLE skill_mastery ADD CONSTRAINT ck_skill_mastery_counts CHECK (attempts >= 0 AND correct >= 0 AND correct <= attempts);
  END IF;
END
$$;
