# File-backed deployment preparation

`FILE_STORAGE_ROOT` enables direct file reads and writes while retaining the existing PostgreSQL catalog and queries. The root directory contains the original `data/raw`, `data/computed`, `data/sources` and other catalogued paths. Files are verified using the catalog's SHA-256 and size. Updates use an atomic rename; previous mutable manifests are preserved under their digest. In this mode newly written files are not duplicated as SQL bodies. The application caches frequently read files in memory and at the CDN.

Point `NEON_DATABASE_URL` to the local PostgreSQL instance containing the `statarena` schema. For a local, unencrypted PostgreSQL connection set `STATARENA_DATABASE_SSLMODE=disable`; the default remains `verify-full`. `STATARENA_SQL_LIMIT_BYTES` and `STATARENA_OBJECT_LIMIT_BYTES` can set explicit collection limits; zero disables the corresponding limit in filesystem mode. Collection also checks the free space of the file volume.

## Copy and verify

With the source Neon read-only SQL and S3 credentials in the existing `NEON_*` variables, and the destination directory already created:

```sh
python dashboard/scripts/copy_neon_files_to_disk.py --destination /srv/statarena
python dashboard/scripts/copy_neon_files_to_disk.py --destination /srv/statarena --verify-only
```

Each object is written to its original `data/...` path only after its size and SHA-256 match the source catalog. A rerun verifies and reuses matching files. A source object changed during the copy is reported as a failure and must be recopied on the final pass. Copying every object from Neon incurs a one-time source transfer roughly equal to the data copied; the current catalog was approximately 3.93 GB on 3 November 2026. Do not switch readers until the final verification matches a consistent catalog and the local PostgreSQL catalog has also been migrated and validated.

The filesystem adapter alone does not configure a server, migrate the PostgreSQL catalog, change GitHub Actions, or switch production traffic. The current collection workflows must continue to receive the Pitch credential from GitHub Actions; a persistent machine would need an appropriately configured runner before cutover. Serve data directly from the new host if the goal is to use its outbound allowance instead of proxying all file bytes through Vercel.
