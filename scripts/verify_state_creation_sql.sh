#!/usr/bin/env bash
# Verifies on a REAL PostgreSQL (pgbench) the first-request race for the per-student state row:
# many clients touch the same not-yet-existing keys at the same moment.
#   (A) plain INSERT                         -> unique violations (what used to return HTTP 500)
#   (B) lock path: SELECT FOR UPDATE, INSERT ... ON CONFLICT DO NOTHING, SELECT FOR UPDATE again, update
#                                            -> 0 errors, one row per key, one increment per transaction
#   (C) provision path: SELECT, INSERT ... ON CONFLICT DO NOTHING, COMMIT
#                                            -> 0 errors, one row per key
# This verifies the database primitives used by engine_bridge, not the Python code.
#   PGHOST=... PGPORT=... PGUSER=... ./scripts/verify_state_creation_sql.sh [clients] [transactions_per_client] [keys]
set -u
CLIENTS=${1:-20}; TX=${2:-100}; KEYS=${3:-150}; DB=juthoor_state_check
PSQL="psql -X -q -v ON_ERROR_STOP=1 -t -A"
$PSQL -d postgres -c "DROP DATABASE IF EXISTS $DB" >/dev/null 2>&1; $PSQL -d postgres -c "CREATE DATABASE $DB" >/dev/null
reset() { $PSQL -d $DB >/dev/null <<'SQL'
DROP TABLE IF EXISTS st;
CREATE TABLE st (student_id int PRIMARY KEY, total int NOT NULL DEFAULT 0);
SQL
}
cat > /tmp/state_plain.sql <<SQL
\set k random(1,$KEYS)
INSERT INTO st (student_id) SELECT :k WHERE NOT EXISTS (SELECT 1 FROM st WHERE student_id = :k);
SQL
cat > /tmp/state_lock.sql <<SQL
\set k random(1,$KEYS)
BEGIN;
SELECT count(*) AS n FROM (SELECT 1 FROM st WHERE student_id = :k FOR UPDATE) q \gset
\if :n = 0
INSERT INTO st (student_id) VALUES (:k) ON CONFLICT (student_id) DO NOTHING;
SELECT total AS t FROM st WHERE student_id = :k FOR UPDATE \gset
\else
SELECT total AS t FROM st WHERE student_id = :k FOR UPDATE \gset
\endif
UPDATE st SET total = :t + 1 WHERE student_id = :k;
COMMIT;
SQL
cat > /tmp/state_prov.sql <<SQL
\set k random(1,$KEYS)
BEGIN;
INSERT INTO st (student_id) VALUES (:k) ON CONFLICT (student_id) DO NOTHING;
COMMIT;
SQL
fail=0
run() { # name script  -> prints errors, rows, sum
  reset
  out=$(pgbench -n -c "$CLIENTS" -j 4 -t "$TX" -f "$2" "$DB" 2>&1)
  ok=$(echo "$out" | sed -n 's/^number of transactions actually processed: \([0-9]*\).*/\1/p')
  failed=$(echo "$out" | sed -n 's/^number of failed transactions: \([0-9]*\).*/\1/p')
  rows=$($PSQL -d $DB -c "SELECT count(*) FROM st"); sum=$($PSQL -d $DB -c "SELECT coalesce(sum(total),0) FROM st")
  echo "$1: processed=$ok failed=${failed:-0} rows=$rows sum_total=$sum"
  RESULT_FAILED=${failed:-0}; RESULT_ROWS=$rows; RESULT_SUM=$sum; RESULT_OK=$ok
}
run "(A) racy check-then-insert, no ON CONFLICT" /tmp/state_plain.sql
EXPECTED=$((CLIENTS*TX))
if [ "$RESULT_OK" -lt "$EXPECTED" ]; then
  echo "     -> only $RESULT_OK of $EXPECTED transactions completed: clients aborted on a unique-key violation (the old HTTP 500)"
else
  echo "     -> no race happened in this run (increase clients or lower keys to provoke it)"
fi
run "(B) lock path (FOR UPDATE + ON CONFLICT + FOR UPDATE)" /tmp/state_lock.sql
[ "$RESULT_FAILED" = "0" ] && [ "$RESULT_SUM" = "$RESULT_OK" ] && [ "$RESULT_ROWS" -le "$KEYS" ] || { echo "FAIL (B)"; fail=1; }
run "(C) provision path (INSERT ON CONFLICT DO NOTHING + COMMIT)" /tmp/state_prov.sql
[ "$RESULT_FAILED" = "0" ] && [ "$RESULT_ROWS" -le "$KEYS" ] || { echo "FAIL (C)"; fail=1; }
[ $fail = 0 ] && echo "PASS: first-request creation is race-free (clients=$CLIENTS, tx/client=$TX, keys=$KEYS)"
exit $fail
