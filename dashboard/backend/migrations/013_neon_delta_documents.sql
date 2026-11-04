-- Stage newer Neon JSON content in SQL without changing live AWS catalog rows.
CREATE TABLE IF NOT EXISTS statarena.neon_delta_documents (
    path text PRIMARY KEY,
    size bigint NOT NULL CHECK (size >= 0),
    source_sha256 bytea NOT NULL CHECK (octet_length(source_sha256) = 32),
    content_type text NOT NULL,
    etag text NOT NULL,
    document jsonb NOT NULL,
    target_sha256_at_capture bytea,
    captured_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS statarena.neon_delta_queue (
    path text PRIMARY KEY,
    size bigint NOT NULL CHECK (size >= 0),
    source_sha256 bytea NOT NULL CHECK (octet_length(source_sha256) = 32),
    content_type text NOT NULL,
    target_sha256_at_capture bytea
);
