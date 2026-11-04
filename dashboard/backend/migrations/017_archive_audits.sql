-- Record content-level checks separately for each immutable source version.
CREATE TABLE IF NOT EXISTS statarena.archive_audits (
    path text NOT NULL,
    source_sha256 bytea NOT NULL CHECK (octet_length(source_sha256) = 32),
    status text NOT NULL CHECK (status IN ('verified', 'needs_review')),
    regular_members bigint NOT NULL,
    special_members bigint NOT NULL,
    unsupported_members bigint NOT NULL,
    parsed_documents bigint NOT NULL,
    parse_errors bigint NOT NULL,
    document_mismatches bigint NOT NULL,
    audited_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (path, source_sha256)
);
