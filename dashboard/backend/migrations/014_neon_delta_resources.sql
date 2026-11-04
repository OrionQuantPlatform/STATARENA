-- Keep later Neon resource references isolated until their documents and readers are reconciled.
CREATE TABLE IF NOT EXISTS statarena.neon_resource_delta (
    endpoint text NOT NULL,
    params text NOT NULL,
    status smallint NOT NULL,
    ref jsonb,
    error jsonb,
    updated_at timestamptz NOT NULL,
    captured_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (endpoint, params)
);
