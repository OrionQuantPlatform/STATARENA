-- Preserve Neon-only image collection work without scheduling it on AWS yet.
CREATE TABLE IF NOT EXISTS statarena.neon_asset_job_delta (
    url text PRIMARY KEY,
    attempts integer NOT NULL,
    next_attempt timestamptz NOT NULL,
    error text,
    captured_at timestamptz NOT NULL DEFAULT now()
);
