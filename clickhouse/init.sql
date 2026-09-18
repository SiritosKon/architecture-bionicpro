CREATE DATABASE IF NOT EXISTS reports;

CREATE TABLE IF NOT EXISTS reports.user_reports
(
    user_id          String,
    period           Date,
    full_name        String,
    prosthesis_model String,
    total_events     UInt64,
    avg_response_ms  Float64,
    p95_response_ms  Float64,
    movements_count  UInt64,
    avg_battery      Float64,
    updated_at       DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (user_id, period);
