-- 0003: idempotency receipts for answer submission (retry returns the stored response).
CREATE TABLE IF NOT EXISTS answer_receipts (
    student_id UUID NOT NULL REFERENCES users (id),
    request_id VARCHAR(64) NOT NULL,
    response JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    PRIMARY KEY (student_id, request_id)
);
CREATE INDEX IF NOT EXISTS ix_answer_receipts_created_at ON answer_receipts (created_at);
