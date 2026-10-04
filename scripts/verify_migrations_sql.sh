#!/usr/bin/env bash
# Verifies migrations/versions/*.sql against a REAL PostgreSQL using only psql (no Python driver needed).
#   PGHOST=... PGPORT=... PGUSER=... ./scripts/verify_migrations_sql.sh
# Creates and drops two scratch databases. Exit code 0 only if every check passes.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PSQL="psql -X -q -v ON_ERROR_STOP=1 -t -A"
fail=0
check() { # description, got, expected
  if [ "$2" = "$3" ]; then echo "PASS  $1"; else echo "FAIL  $1 (got '$2', expected '$3')"; fail=1; fi
}
run_all() { # db -> applies every migration file inside one transaction like app/migrations.py does
  { echo "BEGIN;"; echo "SELECT pg_advisory_xact_lock(727274001);"; cat "$HERE"/migrations/versions/*.sql; echo "COMMIT;"; } | $PSQL -d "$1" >/dev/null
}
for db in juthoor_mig_old juthoor_mig_fresh; do $PSQL -d postgres -c "DROP DATABASE IF EXISTS $db" >/dev/null; $PSQL -d postgres -c "CREATE DATABASE $db" >/dev/null; done

# ---- OLD database: schema as shipped before this change, with duplicate and invalid rows -------------
# (it still contains the legacy organizations table from the removed teacher/school subsystem)
$PSQL -d juthoor_mig_old >/dev/null <<'SQL'
CREATE TABLE organizations (id uuid PRIMARY KEY, name text NOT NULL, slug varchar(80) UNIQUE NOT NULL);
CREATE TABLE users (id uuid PRIMARY KEY, email text UNIQUE NOT NULL);
CREATE TABLE skill_mastery (id uuid PRIMARY KEY, student_id uuid REFERENCES users(id), skill_id varchar(80),
  p_mastery double precision, attempts int, correct int, updated_at timestamp);
CREATE TABLE diagnosis_events (id uuid PRIMARY KEY, student_id uuid REFERENCES users(id), root_skill text);
INSERT INTO organizations VALUES ('00000000-0000-0000-0000-0000000000a1','School','school');
INSERT INTO users VALUES ('00000000-0000-0000-0000-000000000001','a@x'),('00000000-0000-0000-0000-000000000002','b@x');
-- student 1: duplicate rows for adding_integers (keep the one with more attempts)
INSERT INTO skill_mastery VALUES
 ('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','adding_integers',0.5,2,1,'2026-01-01'),
 ('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000001','adding_integers',0.7,5,4,'2026-01-02'),
 ('10000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000001','absolute_value',1.0,3,3,'2026-01-02'),
 ('10000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-000000000002','absolute_value',0.0,2,9,'2026-01-02'),
 ('10000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-000000000002','comparing_integers',0.4,1,1,'2026-01-02');
INSERT INTO diagnosis_events VALUES ('20000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000001','absolute_value');
SQL
run_all juthoor_mig_old
q() { $PSQL -d "$1" -c "$2"; }
check "old: duplicate collapsed to one row"        "$(q juthoor_mig_old "select count(*) from skill_mastery where student_id='00000000-0000-0000-0000-000000000001' and skill_id='adding_integers'")" "1"
check "old: the row with more attempts was kept"   "$(q juthoor_mig_old "select attempts from skill_mastery where skill_id='adding_integers'")" "5"
check "old: untouched rows preserved (5-1=4 left)" "$(q juthoor_mig_old "select count(*) from skill_mastery")" "4"
check "old: p=1.0 clamped below 1"                 "$(q juthoor_mig_old "select p_mastery<1 and p_mastery>0.99 from skill_mastery where id='10000000-0000-0000-0000-000000000003'")" "t"
check "old: p=0.0 clamped above 0"                 "$(q juthoor_mig_old "select p_mastery>0 and p_mastery<0.01 from skill_mastery where id='10000000-0000-0000-0000-000000000004'")" "t"
check "old: correct>attempts repaired"             "$(q juthoor_mig_old "select correct<=attempts from skill_mastery where id='10000000-0000-0000-0000-000000000004'")" "t"
check "old: valid row preserved exactly"           "$(q juthoor_mig_old "select p_mastery||'/'||attempts||'/'||correct from skill_mastery where id='10000000-0000-0000-0000-000000000005'")" "0.4/1/1"
check "old: diagnosis row preserved"               "$(q juthoor_mig_old "select count(*) from diagnosis_events")" "1"
check "old: diagnosis_events gained explanation"   "$(q juthoor_mig_old "select count(*) from information_schema.columns where table_name='diagnosis_events' and column_name in ('confidence_level','explanation')")" "2"
check "old: retired 0004 leaves the legacy organizations table untouched" "$(q juthoor_mig_old "select count(*) from information_schema.columns where table_name='organizations' and column_name='join_code_hash'")" "0"
check "old: legacy organizations rows are not destroyed" "$(q juthoor_mig_old "select count(*) from organizations")" "1"
check "old: answer_receipts exists"                "$(q juthoor_mig_old "select to_regclass('answer_receipts') is not null")" "t"
# constraints are enforced
dup=$($PSQL -d juthoor_mig_old -c "insert into skill_mastery values (gen_random_uuid(),'00000000-0000-0000-0000-000000000001','adding_integers',0.5,1,1,now())" 2>&1 | grep -c "uq_skill_mastery_student_skill")
check "old: duplicate insert is rejected by the unique constraint" "$dup" "1"
bad=$($PSQL -d juthoor_mig_old -c "insert into skill_mastery values (gen_random_uuid(),'00000000-0000-0000-0000-000000000001','x',1.0,1,1,now())" 2>&1 | grep -c "ck_skill_mastery_p_open_interval")
check "old: p=1.0 insert is rejected by the check constraint" "$bad" "1"
bad=$($PSQL -d juthoor_mig_old -c "insert into skill_mastery values (gen_random_uuid(),'00000000-0000-0000-0000-000000000001','y',0.5,1,2,now())" 2>&1 | grep -c "ck_skill_mastery_counts")
check "old: correct>attempts insert is rejected" "$bad" "1"
# idempotent second run
run_all juthoor_mig_old
check "old: re-running every migration is a no-op (rows unchanged)" "$(q juthoor_mig_old "select count(*) from skill_mastery")" "4"

# ---- FRESH database: tables as create_all would build them from the current models --------------------
$PSQL -d juthoor_mig_fresh >/dev/null <<'SQL'
CREATE TABLE users (id uuid PRIMARY KEY, email text UNIQUE NOT NULL);
CREATE TABLE skill_mastery (id uuid PRIMARY KEY, student_id uuid REFERENCES users(id), skill_id varchar(80),
  p_mastery double precision, attempts int, correct int, updated_at timestamp,
  CONSTRAINT uq_skill_mastery_student_skill UNIQUE (student_id, skill_id),
  CONSTRAINT ck_skill_mastery_p_open_interval CHECK (p_mastery > 0 AND p_mastery < 1),
  CONSTRAINT ck_skill_mastery_counts CHECK (attempts >= 0 AND correct >= 0 AND correct <= attempts));
CREATE TABLE diagnosis_events (id uuid PRIMARY KEY, student_id uuid REFERENCES users(id), root_skill text, confidence_level varchar(10), explanation text);
CREATE TABLE answer_receipts (student_id uuid NOT NULL REFERENCES users(id), request_id varchar(64) NOT NULL, response json NOT NULL, created_at timestamp NOT NULL DEFAULT now(), PRIMARY KEY (student_id, request_id));
SQL
run_all juthoor_mig_fresh
check "fresh: no duplicate constraints created" "$(q juthoor_mig_fresh "select count(*) from pg_constraint where conname like 'uq_skill_mastery%' or conname like 'ck_skill_mastery%'")" "3"
run_all juthoor_mig_fresh
check "fresh: second run is a no-op" "$(q juthoor_mig_fresh "select count(*) from pg_constraint where conname like 'uq_skill_mastery%' or conname like 'ck_skill_mastery%'")" "3"

for db in juthoor_mig_old juthoor_mig_fresh; do $PSQL -d postgres -c "DROP DATABASE $db" >/dev/null; done
[ $fail -eq 0 ] && echo "ALL MIGRATION SQL CHECKS PASSED" || echo "MIGRATION SQL CHECKS FAILED"
exit $fail
