-- Preserve Neon-only collection work without scheduling it on AWS prematurely.
CREATE TABLE IF NOT EXISTS statarena.neon_job_delta (
    endpoint text NOT NULL,
    params text NOT NULL,
    priority smallint NOT NULL,
    state text NOT NULL,
    attempts integer NOT NULL,
    available_at timestamptz NOT NULL,
    lease_until timestamptz,
    last_status smallint,
    last_error text,
    captured_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (endpoint, params)
);
