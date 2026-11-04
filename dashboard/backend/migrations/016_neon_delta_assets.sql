-- Keep newer Neon image mappings separate until SQL image serving is live.
CREATE TABLE IF NOT EXISTS statarena.neon_asset_delta (
    url text PRIMARY KEY,
    path text NOT NULL,
    content_type text NOT NULL,
    size bigint NOT NULL CHECK (size >= 0),
    source_sha256 bytea NOT NULL CHECK (octet_length(source_sha256) = 32),
    target_path_at_capture text,
    target_content_type_at_capture text,
    captured_at timestamptz NOT NULL DEFAULT now()
);
