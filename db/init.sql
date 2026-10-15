CREATE TABLE lambda_raw (
  event_id UUID PRIMARY KEY, user_id INT, event_type TEXT,
  amount NUMERIC(10,2), ts TIMESTAMPTZ, ingested_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE lambda_batch_view (
  minute TIMESTAMPTZ, event_type TEXT, n BIGINT, total NUMERIC,
  PRIMARY KEY (minute, event_type)
);
CREATE TABLE lambda_speed_view (
  minute TIMESTAMPTZ, event_type TEXT, n BIGINT, total NUMERIC,
  PRIMARY KEY (minute, event_type)
);
CREATE TABLE kappa_view (
  minute TIMESTAMPTZ, event_type TEXT, n BIGINT, total NUMERIC,
  last_event_ts TIMESTAMPTZ, last_processed_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (minute, event_type)
);