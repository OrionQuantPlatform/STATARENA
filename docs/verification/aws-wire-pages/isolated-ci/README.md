# Isolated workflow replay

The relational CI job runs `bun docs/verification/aws-wire-pages/disposable.mjs --ci`. A fresh dependency installation and a temporary checkout containing the pending decoder and harness changes passed on macOS. The Linux job will run after publication. A separate definition check found one of four controls before the change and four of four afterward. [Initial workflow](../ci-definition-before.json) · [Updated workflow](../ci-definition-after.json)

The replay used the existing checked-in synthetic football generator, a new PostgreSQL 18.6 cluster, the real normalizer, record and compact HTTP handlers and the production decoder. Each representation returned empty HEAD 200 and conditional GET/HEAD 304 bodies with the GET validator. Unknown format returned 400. All row values matched, including SQL null, missing, zero, numeric and string positions and all six dynamic metric-name cases. [SQL publication receipt](disposable-seed.json) · [HTTP result](disposable.json)

To repeat from a fresh checkout with the candidate changes and Bun installed, run the following from the repository root. The job uses its existing shared temporary dependency installations. This local replay uses fresh directories to verify isolation. The only inputs beside the checkout are public packages.

```sh
scratch=$(mktemp -d)
mkdir -p "$scratch"/{home,tools,python}
python3 -m pip install --target "$scratch/python" -r dashboard/scripts/neon-requirements.txt PyYAML==6.0.3
(cd "$scratch/tools" && npm install --no-save --no-package-lock --no-audit --no-fund embedded-postgres@18.6.0-beta.19)
(cd dashboard && bun install --frozen-lockfile)
env -i PATH="$PATH" HOME="$scratch/home" TMPDIR="$scratch" \
  AWS_EC2_METADATA_DISABLED=true \
  STATARENA_TEST_TOOLS="$scratch/tools" \
  STATARENA_TEST_PYTHONPATH="$scratch/python" \
  STATARENA_CI_EVIDENCE=docs/verification/aws-actions-20261104/relational-ci \
  bun docs/verification/aws-wire-pages/disposable.mjs --ci
```

The first stripped-environment run failed the seed’s idempotence check. It passed with a UTF-8 locale. The final fixture explicitly initializes PostgreSQL with UTF-8 and passes with no locale variable in its environment. [Initial seed failure](locale-before/disposable-seed.json)

The step writes fresh seed and HTTP receipts to the `season-wire` directory beneath the relational job’s existing always-uploaded artifact directory. No cloud login or browser installation is required.
