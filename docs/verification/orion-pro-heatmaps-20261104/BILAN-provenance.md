# Heatmap provenance root result

**9/9 local heatmap workflows and 8/8 unchanged native31 workflows pass.** All observations remain synthetic, source queries are zero, **0/1344 real triplets compared**, `fullAcceptance=false`.

The genuine pre-code RED accepted a direct `{data:...}` envelope under the archive default and wrote five false `/response/data/...` SQL source-record locators. It remains in `runs/20261104T223421196704Z-provenance-root-precode-red/result.json`; the normalizer was still the previous sparse SHA `55262439e4dfdae31da12e93c184c7e63ad4bf51564ba87cc85ce72c48e7657f`.

The helper now accepts only the explicit relative data roots `/response/data` (unchanged default), `/data`, or an empty relative root for a record already situated at a `data` member. Before local writes, it resolves the source-record locator plus that root against the already decoded cached document and checks the supplied data's exact semantic hash, retaining native scalar kind distinctions. A direct envelope with the archive default, unknown root, missing path, bare-document empty root or mismatched observation is refused. Invalid/non-finite source values refuse as MappingError; the intermediate ValueError failure is preserved in `runs/20261104T223640986297Z-provenance-root-final/result.json`.

Independent SQL checks document/source parent identity, `json_pointer` locator kind and every parent-collection and coverage-slot locator. Archived records at `/0` use `/0/response/data/...`; direct document records at the empty pointer use `/data/...`; records already at `/data` also use `/data/...`. Each shape writes exactly six observed cell rows, and the in-memory source envelope hash is unchanged. No source wrapper is manufactured or persisted, and no source query is added.

The previous eight heatmap greens remain historical in `runs/20261104T222221141055Z-sparse-final-bounded-contract/result.json`. The new final receipt is `runs/20261104T223658644533Z-provenance-root-final-guard/result.json`; the unchanged native31 suite receipt is `native31-regression/runs/20261104T223702410963Z-heatmap-regression/result.json`. A new exec process reuses core/family receipts with all 94 tables and 67 sequences unchanged (`dd4b26c5bc4bb8bd6296714e8d6cd9c8086d13fa82752a32414fcf88bc54c7dd`). Both disposable local databases were stopped and removed. Model and sealed 012/013, protected pilot/native31 tests/proofs and old source ledger remain byte-identical to 5745197060; no remote actions, captures, provider requests, commit or deployment occurred in this pass.

The patch `review-provenance-root-only.patch` is the exact source/spec delta from the preceding frozen eight-green input copies. The earlier patch and runtime manifests are retained. `runtime-manifest.json` in the final run records code/spec/result hashes, four verified local migration executions, unchanged frozen files and patch verification. The pre-code protocol and synthetic setup recipe are included in every run's inputs.

The sparse spatial mapper and metric31 transformation rules remain unchanged. Names/shirt observations remain qualified gaps; absent actions is refused, and no general observed-profile mapping is claimed. No real triplet, real document version or future capture is implicitly validated by these synthetic runs.

- Normalizer SHA-256: `4b98a829bc7e32e11a7e66381ffecae6248ce536d17771aa080502374fe844bc`
- Heatmap E2E SHA-256: `0ebec3ef6cea39d200c10951dd35988227bb78eda02d6ba7be595ba9e9221cc5`
- Final result SHA-256: `db225de72237fb63acdef1ba204fd5edc0da19cbce653f6037f05510405852dd`
- Native31 result SHA-256: `b04f663f0e91c78e69ac6f2ef5fa682210d57401de11524fbadf2b17bd8dd455`
- Provenance-only patch SHA-256: `a2512e853beb839e5531fb624d8f6613e0a5fed73e5931f792cb11b9679e0d87`

Rerun from the repository root with the existing Python/psycopg runtime and embedded PG18.6 binaries (default `/tmp/statarena-cache-test-tools/node_modules/@embedded-postgres/darwin-arm64/native/bin`):

```sh
PYTHONPATH=/tmp/statarena-publication-test-python /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_heatmaps_local.py --label provenance-root-final-guard
```

Suggested commit: `fix: validate sparse heatmap source locator roots`.
