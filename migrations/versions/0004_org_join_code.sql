-- 0004: retired. It used to add organizations.join_code_hash for the former teacher/school subsystem, which
-- has been removed (Juthoor is B2C: student = user, parent = buyer). The version is kept as a no-op so the
-- migration history stays consecutive; databases that already applied the old 0004 keep a harmless, unused
-- nullable column. Nothing is dropped: legacy tables are left in place and the application no longer uses them.
SELECT 1;
