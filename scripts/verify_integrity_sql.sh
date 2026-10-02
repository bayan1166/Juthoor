#!/usr/bin/env bash
# Runs app/integrity_sql.py's checks through psql against a scratch PostgreSQL database that is
# first CLEAN (every check must report 0) and then deliberately CORRUPTED (each defect must be caught).
#   PGHOST=... PGPORT=... PGUSER=... ./scripts/verify_integrity_sql.sh
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"; DB=juthoor_integrity_check
PSQL="psql -X -q -v ON_ERROR_STOP=1 -t -A"
$PSQL -d postgres -c "DROP DATABASE IF EXISTS $DB" >/dev/null 2>&1; $PSQL -d postgres -c "CREATE DATABASE $DB" >/dev/null
$PSQL -d $DB >/dev/null <<'SQL'
CREATE TABLE users (id uuid PRIMARY KEY, role text NOT NULL);
CREATE TABLE skill_mastery (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), student_id uuid, skill_id text, p_mastery float, attempts int, correct int, status text);
CREATE TABLE attempt_logs (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), student_id uuid, skill_id text);
CREATE TABLE diagnosis_events (id uuid PRIMARY KEY DEFAULT gen_random_uuid(), student_id uuid, origin_skill text, root_skill text, confidence_level text, evidence json, path json);
CREATE TABLE student_adaptive_states (student_id uuid PRIMARY KEY, current_skill text, difficulty int, consec_wrong int, total_answered int, round_answered int, pending_question json);
CREATE TABLE answer_receipts (student_id uuid, request_id text);
INSERT INTO users VALUES ('00000000-0000-0000-0000-000000000001','student'),('00000000-0000-0000-0000-000000000002','teacher');
INSERT INTO student_adaptive_states VALUES ('00000000-0000-0000-0000-000000000001','adding_integers',2,0,3,1,'{"skill":"adding_integers"}');
INSERT INTO skill_mastery (student_id, skill_id, p_mastery, attempts, correct, status) VALUES
  ('00000000-0000-0000-0000-000000000001','adding_integers',0.6,2,1,'learning'),
  ('00000000-0000-0000-0000-000000000001','absolute_value',0.5,1,1,'gap');
INSERT INTO attempt_logs (student_id, skill_id) VALUES ('00000000-0000-0000-0000-000000000001','adding_integers'),('00000000-0000-0000-0000-000000000001','adding_integers'),('00000000-0000-0000-0000-000000000001','absolute_value');
INSERT INTO diagnosis_events (student_id, origin_skill, root_skill, confidence_level, evidence, path) VALUES
  ('00000000-0000-0000-0000-000000000001','adding_integers','absolute_value','high','[{"skill":"absolute_value"}]','["adding_integers","absolute_value"]');
SQL
runchecks() { python3 - "$HERE" <<'PY' | $PSQL -d $DB -F '|'
import sys; sys.path.insert(0, sys.argv[1])
from app import integrity_sql
for i, (sev, label, sql) in enumerate(integrity_sql.checks()):
    print(f"SELECT {i}, '{sev}', ({sql});")
PY
}
fail=0
clean=$(runchecks | awk -F'|' '$3!=0 && $2=="ERROR"{n++} END{print n+0}')
echo "clean database: ERROR checks reporting violations = $clean (expected 0)"; [ "$clean" = "0" ] || fail=1
# corrupt, one defect per statement; each must raise the matching check above zero
$PSQL -d $DB >/dev/null <<'SQL'
INSERT INTO skill_mastery (student_id, skill_id, p_mastery, attempts, correct, status) VALUES
  ('00000000-0000-0000-0000-000000000001','adding_integers',0.6,2,1,'learning'),   -- duplicate
  ('00000000-0000-0000-0000-000000000001','comparing_integers',1.0,1,1,'learning'),-- p=1.0
  ('00000000-0000-0000-0000-000000000001','no_such_skill',0.5,1,1,'learning'),     -- unknown skill
  ('99999999-9999-9999-9999-999999999999','absolute_value',0.5,1,1,'learning'),    -- orphan
  ('00000000-0000-0000-0000-000000000002','absolute_value',0.5,1,1,'learning');    -- owned by a teacher
INSERT INTO attempt_logs (student_id, skill_id) VALUES ('99999999-9999-9999-9999-999999999999','absolute_value');
INSERT INTO student_adaptive_states VALUES ('00000000-0000-0000-0000-000000000002','nope',9,-1,0,0,'{"skill":"ghost"}');
INSERT INTO diagnosis_events (student_id, origin_skill, root_skill, confidence_level, evidence, path) VALUES
  ('00000000-0000-0000-0000-000000000001','adding_integers','absolute_value','certain','[]','["adding_integers"]');
INSERT INTO answer_receipts VALUES ('99999999-9999-9999-9999-999999999999','r1');
INSERT INTO diagnosis_events (student_id, origin_skill, root_skill, confidence_level, evidence, path) VALUES
  ('99999999-9999-9999-9999-999999999999','adding_integers','absolute_value','high','[{}]','["absolute_value"]');   -- orphan diagnosis
INSERT INTO student_adaptive_states VALUES ('99999999-9999-9999-9999-999999999999','adding_integers',1,0,0,0,NULL);  -- orphan state
SQL
echo "corrupted database:"
python3 - "$HERE" > /tmp/_labels.txt <<'PY'
import sys; sys.path.insert(0, sys.argv[1])
from app import integrity_sql
for i,(s,l,_) in enumerate(integrity_sql.checks()): print(f"{i}|{s}|{l}")
PY
runchecks > /tmp/_counts.txt
detected=0; expected_errors=0
while IFS='|' read -r i sev label; do
  n=$(awk -F'|' -v i="$i" '$1==i{print $3}' /tmp/_counts.txt)
  if [ "$sev" = "ERROR" ]; then expected_errors=$((expected_errors+1)); if [ "${n:-0}" -gt 0 ]; then detected=$((detected+1)); echo "  DETECTED $n  $label"; else echo "  MISSED       $label"; fi; fi
done < /tmp/_labels.txt
echo "ERROR checks that detected their seeded defect: $detected / $expected_errors"
[ "$detected" = "$expected_errors" ] || fail=1
$PSQL -d postgres -c "DROP DATABASE $DB" >/dev/null
[ $fail -eq 0 ] && echo "INTEGRITY CHECKER VERIFIED" || echo "INTEGRITY CHECKER VERIFICATION FAILED"; exit $fail
