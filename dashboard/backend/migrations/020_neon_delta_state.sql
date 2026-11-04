-- Capture later Neon workflow state for explicit reconciliation at cutover.
CREATE TABLE IF NOT EXISTS statarena.neon_state_delta (
    name text PRIMARY KEY,
    value jsonb NOT NULL,
    updated_at timestamptz NOT NULL,
    target_updated_at_at_capture timestamptz,
    target_digest_at_capture text,
    captured_at timestamptz NOT NULL DEFAULT now()
);
