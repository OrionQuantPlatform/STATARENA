# Full-data GitHub Actions measurement

- Run: https://github.com/OrionQuantPlatform/STATARENA/actions/runs/41611636818
- Immutable source/code commit: cbae004bfa368751c224066a07c5d30510f38754
- Branch: codex/measure-postgres-storage
- Environment: ubuntu-24.04, postgres:17 service, Python 3, psycopg[binary]==3.2.3.
- Command: `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/statarena_measure python3 -u dashboard/scripts/measure_postgres_storage.py --output /tmp/statarena-storage-evidence`
- Expected: every tracked data file processed, all SQL rows readback-verified, actual database and per-schema/table/index byte counts in SUMMARY.md/measurement.json.
- Actual result: failed before import with IndexError in family() on top-level data/README.md. Artifacts uploaded successfully. No complete storage measurement exists from this run.
- Actual results/logs: consult the run and its `postgres-storage-<commit>-1` artifact. A failed or partial run is not a measurement.

No production database, data files, collector credentials, collector workflow or main branch are changed. The run uses only a disposable PostgreSQL service and read-only repository permissions. No unit tests were added. Python compilation and git whitespace checks passed locally before publication; the real-data Action is the E2E validation.
