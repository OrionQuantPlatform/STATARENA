-- Store exact source bytes in PostgreSQL, split into bounded chunks.
-- A namespace distinguishes application files from migration and release artifacts.
CREATE TABLE IF NOT EXISTS statarena.file_payloads (
    namespace text NOT NULL,
    path text NOT NULL,
    size bigint NOT NULL CHECK (size >= 0),
    sha256 bytea NOT NULL CHECK (octet_length(sha256) = 32),
    body bytea,
    content_type text NOT NULL,
    source_etag text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    chunk_count integer NOT NULL CHECK (chunk_count >= 0),
    verified_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (namespace, path),
    CHECK ((body IS NOT NULL AND chunk_count = 0 AND octet_length(body) = size)
        OR (body IS NULL AND chunk_count > 0))
);

CREATE TABLE IF NOT EXISTS statarena.file_payload_chunks (
    namespace text NOT NULL,
    path text NOT NULL,
    chunk_index integer NOT NULL CHECK (chunk_index >= 0),
    body bytea NOT NULL,
    sha256 bytea NOT NULL CHECK (octet_length(sha256) = 32),
    PRIMARY KEY (namespace, path, chunk_index),
    FOREIGN KEY (namespace, path) REFERENCES statarena.file_payloads(namespace, path) ON DELETE CASCADE
);
