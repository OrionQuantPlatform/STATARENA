-- Preserve newer Neon projections without replacing independently updated AWS data.
CREATE TABLE IF NOT EXISTS statarena.neon_projection_delta (
    name text NOT NULL,
    params text NOT NULL,
    body jsonb NOT NULL,
    updated_at timestamptz NOT NULL,
    target_updated_at_at_capture timestamptz,
    target_digest_at_capture text,
    captured_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (name, params)
);
