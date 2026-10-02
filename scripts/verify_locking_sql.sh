#!/usr/bin/env bash
# Demonstrates, on a REAL PostgreSQL with pgbench, why engine_bridge locks the student row:
# the same read-modify-write the app performs per answer, run by many concurrent clients,
#   (A) without a lock       -> lost updates (counter ends below the number of transactions)
#   (B) with SELECT FOR UPDATE -> exactly one increment per transaction
# This verifies the database primitive, not the Python application code.
#   PGHOST=... PGPORT=... PGUSER=... ./scripts/verify_locking_sql.sh [clients] [transactions_per_client]
set -u
CLIENTS=${1:-20}; TX=${2:-200}; DB=juthoor_lock_check
PSQL="psql -X -q -v ON_ERROR_STOP=1 -t -A"
$PSQL -d postgres -c "DROP DATABASE IF EXISTS $DB" >/dev/null 2>&1; $PSQL -d postgres -c "CREATE DATABASE $DB" >/dev/null
reset() { $PSQL -d $DB >/dev/null <<'SQL'
DROP TABLE IF EXISTS st; DROP TABLE IF EXISTS mastery;
CREATE TABLE st (student_id int PRIMARY KEY, total int NOT NULL DEFAULT 0);
CREATE TABLE mastery (student_id int, skill text, attempts int NOT NULL DEFAULT 0, UNIQUE (student_id, skill));
INSERT INTO st VALUES (1, 0); INSERT INTO mastery VALUES (1, 'a', 0);
SQL
}
cat > /tmp/nolock.sql <<'SQL'
BEGIN;
SELECT total AS t FROM st WHERE student_id = 1 \gset
UPDATE st SET total = :t + 1 WHERE student_id = 1;
SELECT attempts AS a FROM mastery WHERE student_id = 1 AND skill = 'a' \gset
UPDATE mastery SET attempts = :a + 1 WHERE student_id = 1 AND skill = 'a';
COMMIT;
SQL
cat > /tmp/lock.sql <<'SQL'
BEGIN;
INSERT INTO st (student_id) VALUES (1) ON CONFLICT (student_id) DO NOTHING;
SELECT total AS t FROM st WHERE student_id = 1 FOR UPDATE \gset
UPDATE st SET total = :t + 1 WHERE student_id = 1;
SELECT attempts AS a FROM mastery WHERE student_id = 1 AND skill = 'a' \gset
UPDATE mastery SET attempts = :a + 1 WHERE student_id = 1 AND skill = 'a';
COMMIT;
SQL
want=$((CLIENTS*TX))
reset; pgbench -n -c $CLIENTS -j 4 -t $TX -f /tmp/nolock.sql $DB >/dev/null 2>&1
a_total=$($PSQL -d $DB -c "select total from st"); a_att=$($PSQL -d $DB -c "select attempts from mastery")
echo "(A) no lock:        expected $want increments, st.total=$a_total mastery.attempts=$a_att  -> lost updates: $((want-a_total))"
reset; pgbench -n -c $CLIENTS -j 4 -t $TX -f /tmp/lock.sql $DB >/dev/null 2>&1
b_total=$($PSQL -d $DB -c "select total from st"); b_att=$($PSQL -d $DB -c "select attempts from mastery")
echo "(B) FOR UPDATE:     expected $want increments, st.total=$b_total mastery.attempts=$b_att  -> lost updates: $((want-b_total))"
$PSQL -d postgres -c "DROP DATABASE $DB" >/dev/null
if [ "$b_total" = "$want" ] && [ "$b_att" = "$want" ]; then echo "PASS: locking prevents lost updates (clients=$CLIENTS, tx/client=$TX)"; exit 0; else echo "FAIL"; exit 1; fi
