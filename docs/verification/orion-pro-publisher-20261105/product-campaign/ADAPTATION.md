# Publisher product campaign

Suggested commit: `feat: publish immutable Pro V1 SQL summaries`.

This is a new ledger beside `qualified-precode`, at the same directory depth.
`COPIED_CONTRACTS.json` binds thirteen exact copies, including the four requested
workflow/input/typed/output oracle files. Their expectations and bytes have not
changed. The original workflow and budget are retained as `.precode.py` copies;
their active copies change only the operational SQL allocation from 1,500 to
4,000 at reservation and final accounting. The original HTTP launcher is retained as
`publisher_http_server.precode.mjs`; its active copy changes only the required
owned run prefix from `qualified-precode/runs` to `product-campaign/runs`.
The existing static gate retains its original missing-product assertion
and is copied as historical input; it is not a product acceptance check.

The source-free `run_campaign.py` wrapper imports the copied workflow and adapts
only execution supervision: `/tmp` tempfile root avoids macOS Unix socket path
limits, and the already qualified `tests/orion_e2e_process.py` bounds captured
subprocesses by one absolute 600-second campaign deadline. The shared reservation
epoch starts at that same boundary. No child gets a fresh 600 seconds; cleanup
has a separate maximum 20-second allowance. The copied workflow's actual SQL
timeouts, owned API/worker lifecycle, writer/network fences, all thirty cases,
failure stop and evidence are retained. A supervisor receipt prohibits implicit
reuse of this allocated campaign.

The product's environment descriptor declares immutable release pins for SQL012,
SQL013 and the frozen JavaScript reader. These files are independently verified
outside the fenced worker. The product reads and hashes the actual model and
Python release helpers, and checks the actual migration journal. The SQL/JS pins
are declared release dependencies, not claimed runtime file measurements.

ROOT must allocate the PG slot before this command is run:

```sh
PYTHONPATH=/tmp/statarena-publication-test-python python3 docs/verification/orion-pro-publisher-20261105/product-campaign/run_campaign.py --label product-v1
```

ROOT reviewed `STATIC_BUDGET_REVIEW.json`: a conservative lower bound of 1,521
SQL commands excludes all product SQL, additional API queries, probes and other
observers. The former internal 1,500-command allocation cannot complete the
unchanged workflow. ROOT allocated a distinct 4,000-command campaign; this is
an allocation correction, not a SQL optimization. The copied protocol and
matrix remain the original pre-code documents. This addendum records only
the new execution allocation; no business expectation is changed.

All other bounds and expected outputs remain the qualified protocol: 30 cases,
600 seconds, one owned PG/API, two workers, at most five connections, 5,000 rows,
three editions, 12 match identities, 20 builds, 100 match summaries, 20 edition
summaries, 24 generations, 30 publication intervals, 200 HTTP and 4,000 reserved
operational SQL calls. First unexpected failure stops and preserves its receipt.
No provider, RAM corpus, AWS, RDS, SSM, Neon, schema, grant, reader, model, historical
artifact or real data is part of this local software campaign.
