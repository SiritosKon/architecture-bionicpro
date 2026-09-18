CREATE TABLE clients (
    user_id          TEXT PRIMARY KEY,
    full_name        TEXT NOT NULL,
    email            TEXT,
    country          TEXT,
    prosthesis_model TEXT
);

CREATE TABLE telemetry (
    id               BIGSERIAL PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES clients(user_id),
    event_ts         TIMESTAMP NOT NULL,
    response_time_ms INTEGER NOT NULL,
    movement         TEXT,
    battery_pct      INTEGER,
    noise_level      REAL
);

INSERT INTO clients (user_id, full_name, email, country, prosthesis_model) VALUES
    ('prothetic1', 'Prothetic One',   'prothetic1@example.com', 'RU', 'BionicArm-X1'),
    ('prothetic2', 'Prothetic Two',   'prothetic2@example.com', 'RU', 'BionicArm-X2'),
    ('prothetic3', 'Prothetic Three', 'prothetic3@example.com', 'RU', 'BionicLeg-L1');

INSERT INTO telemetry (user_id, event_ts, response_time_ms, movement, battery_pct, noise_level)
SELECT
    c.user_id,
    (CURRENT_DATE - (g % 3) * INTERVAL '1 day') + (g || ' minutes')::interval,
    60 + (g * 7) % 90,
    (ARRAY['grip', 'release', 'rotate', 'pinch'])[1 + (g % 4)],
    100 - (g % 40),
    0.1 + ((g % 30) / 100.0)
FROM clients c
CROSS JOIN generate_series(1, 200) AS g;
