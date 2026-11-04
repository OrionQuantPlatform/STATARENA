-- Preserve Neon publication signals until their underlying data is reconciled.
CREATE TABLE IF NOT EXISTS statarena.neon_dirty_partition_delta (
    season text NOT NULL,
    league_id text NOT NULL,
    changed_at timestamptz NOT NULL,
    target_changed_at_at_capture timestamptz,
    captured_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (season, league_id)
);
