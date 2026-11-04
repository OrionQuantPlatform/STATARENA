# Match-level player positions

The saved response for /matches/m_00OYeh/players/p_1BvJC3 contains top-level position_id 33 and player.position_id null. Under 007, the real partition publisher rejected the top-level field, retained the dirty marker and preserved generation. The local 008 replay returned the original saved JSON through the single-player resource and kept the independent top-level value when publishing a full match player array.

Migration 008 adds a nullable PostgreSQL integer to match_players and regenerates its response function. Existing rows gain an absence marker on the first schema upgrade. Reapplying the migration preserves explicit null in later publications. The test distinguishes a top-level integer, zero, null and absent, while preserving nested player identity data. The accepted source type is integer. The observed response is saved in source.json.gz.

Sixteen existing publisher workflows passed, alongside the source-specific publication and upgrade tests, 63 match HTTP requests, and the batch concurrency/rollback suite. The before/player-position.json and after/player-position.json receipts include the original source checksum and actual outcomes. This verification runs in local PostgreSQL only.

```sh
node docs/verification/aws-match-schema-008-20261104/worker.mjs after
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/relational-match-20261104/verify.mjs after
PYTHONPATH=/tmp/statarena-archive-remat-pg/python bun docs/verification/aws-match-publish-20261104/run.mjs after
```

The pre-upgrade row replay uses the old writer from Git commit d74d6cbc4f. Sealed 004 and 007 still regenerate byte for byte. Suggested commit `fix: preserve match player positions in relational responses`.
