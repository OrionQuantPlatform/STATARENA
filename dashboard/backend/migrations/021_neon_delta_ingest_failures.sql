-- Capture Neon ingestion diagnostics without replacing AWS diagnostics.
CREATE TABLE IF NOT EXISTS statarena.neon_ingest_failure_delta (
    endpoint text NOT NULL,
    params text NOT NULL,
    status smallint NOT NULL,
    error jsonb,
    updated_at timestamptz NOT NULL,
    target_updated_at_at_capture timestamptz,
    target_digest_at_capture text,
    captured_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (endpoint, params)
);
