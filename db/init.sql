-- ===== LAMBDA =====
CREATE TABLE lambda_raw (
  seq BIGSERIAL,
  event_id UUID PRIMARY KEY, user_id INT, event_type TEXT,
  amount NUMERIC(10,2), ts TIMESTAMPTZ, ingested_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX lambda_raw_seq_idx ON lambda_raw (seq);

CREATE TABLE lambda_meta (id INT PRIMARY KEY, batch_seq BIGINT NOT NULL);
INSERT INTO lambda_meta VALUES (1, 0);

CREATE TABLE lambda_batch_view (
  minute TIMESTAMPTZ, event_type TEXT, n BIGINT, total NUMERIC,
  PRIMARY KEY (minute, event_type)
);
CREATE TABLE lambda_speed_view (
  minute TIMESTAMPTZ, event_type TEXT, n BIGINT, total NUMERIC,
  last_event_ts TIMESTAMPTZ, last_processed_at TIMESTAMPTZ,
  PRIMARY KEY (minute, event_type)
);

CREATE VIEW lambda_serving AS
SELECT minute, event_type, sum(n)::bigint AS n, sum(total) AS total,
       max(last_event_ts) AS last_event_ts, max(last_processed_at) AS last_processed_at
FROM (
  SELECT minute, event_type, n, total, NULL::timestamptz AS last_event_ts, NULL::timestamptz AS last_processed_at
  FROM lambda_batch_view
  UNION ALL
  SELECT minute, event_type, n, total, last_event_ts, last_processed_at
  FROM lambda_speed_view
) x
GROUP BY minute, event_type;

-- ===== KAPPA =====
CREATE TABLE kappa_view (
  minute TIMESTAMPTZ, event_type TEXT, n BIGINT, total NUMERIC,
  last_event_ts TIMESTAMPTZ, last_processed_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (minute, event_type)
);