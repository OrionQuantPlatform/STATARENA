-- Preserve the AWS version observed when a shared collector job differs.
ALTER TABLE statarena.neon_job_delta
    ADD COLUMN IF NOT EXISTS target_present_at_capture boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS target_digest_at_capture text;
