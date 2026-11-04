# Lossless season pages

Two published 2026/2027 partitions traversed in **7 requests**, down from 64. The production frontend loader and production backend handler communicated over localhost HTTP and read the same Ohio RDS publication via a verified TLS, read-only connection. Every request on the compact traversal returned HTTP 200 at limit 100. [Before](before.json) · [After](after.json)

| League | Fixtures | Matches | Appearances | Requests, before → after | Decoded HTTP bytes, before → after |
|---|---:|---:|---:|---:|---:|
| l_0275VP | 297 | 89 | 3,516 | 29 → 3 | 9,942,103 → 1,602,392 |
| l_0ALvwF | 380 | 100 | 4,788 | 35 → 4 | 10,542,354 → 2,133,817 |

Across the two traversals, HTTP body bytes fell 81.8%. Applying the same local gzip implementation separately to every response produced 1,976,602 bytes before and 743,101 after, a 62.4% reduction. These measurements include 413 responses and discarded partial traversals. Summed HTTP durations in this one local run were 13.59 s before and 2.70 s after. The local machine connects to Ohio over the WAN, so those durations do not establish deployed UI latency.

Both full decoded season hashes matched their record-format baselines. Only the cross-match ordering of appearances was canonicalized for hashing. SQL already orders appearances by match ID within a keyset page, while the pages are ordered by fixture date and ID. Native within-match order, shot geometry, stats, nested players, arrays, scalar types and record field presence were preserved. The single-window GET matched records without array normalization. A disposable PostgreSQL 18 fixture independently preserved numeric position 11, string position "11" and an optional metric absent on the second appearance. The existing Chromium restart/coalescing workflow also passed, including 409 and a 413 partway through a traversal. [Disposable SQL/HTTP](disposable.json) · [Browser regression](browser-regression.json)

The first packing pass still returned one 413 on the denser league. The final format keeps constant values once per table and encodes match player references as indexes into that page’s appearances, preserving their original order. Shot/stat rows are packed across the page and restored to the parent match using exact lengths. Tables use the existing frontend packed-row decoder. Default record GETs, SQL reads, origin cache policy and adaptive downsizing for future publications are unchanged. The denser first page finished at 1,973,314 bytes against a 2,097,152-byte cap. [First packing attempt](first-packing.json)

## Packaged runtime

The deterministic ZIP b5131a8329297deab127fc901a5e11c645a971b3e5ab208633aedbf029ffb647 ran through its Function URL event adapter locally on Node 24.22.2 with a 256 MiB JavaScript heap cap. Five GETs for the densest published page returned 200 and compressed to exactly 431,391 bytes. Peak process RSS reached 303.6 MiB. Warm process CPU for the entire request was 419–486 ms. HEAD 200, conditional GET 304 and conditional HEAD 304 had the same ETag and empty bodies. Independent codec replays on macOS took 94–119 ms per pack with Node 24 and 29–45 ms with Bun. These CPU and memory values are host measurements. A 512 MiB Lambda REPORT and new browser navigation on a rebuilt preview are separate deployment checks. [Sealed ZIP](zip-node24.json) · [Node codec](profile-node24.json) · [Bun codec](profile-bun.json) · [Next build](next-build.log)

## Reproduction

Run from the checkout root with dashboard dependencies installed, the private runtime connection file available and the local fixture tools and Node binary indicated below. The baseline used the unmodified product at 2a419fcdfe with this verification folder available. The newer product requires the after command. The source digest must still match for between-run comparisons.

```sh
bun docs/verification/aws-wire-pages/verify.mjs before
bun docs/verification/aws-wire-pages/verify.mjs after
bun docs/verification/aws-wire-pages/disposable.mjs
python3 docs/verification/aws-frontend-20261104/verify.py green
/tmp/statarena-node24-20261104 --expose-gc docs/verification/aws-wire-pages/profile.mjs
bun docs/verification/aws-wire-pages/profile.mjs
BUILD_NODE=/tmp/statarena-node24-20261104 python3 infra/aws-backend/package.py /tmp/statarena-wire-zip
unzip -o /tmp/statarena-wire-zip/b5131a8329297deab127fc901a5e11c645a971b3e5ab208633aedbf029ffb647.zip -d /tmp/statarena-wire-zip
/tmp/statarena-node24-20261104 --max-old-space-size=256 docs/verification/aws-wire-pages/zip.mjs
(cd dashboard && NEXT_PUBLIC_API_ORIGIN=https://d317dq37z1tacb.cloudfront.net bun run build)
```

The baseline command deliberately exits nonzero on the old version because compact format is rejected. The initial disposable fixture setup was corrected to use the seed workflow’s explicitly required local database name. [Original fixture guard failure](disposable-setup-before.json)

Deploy the backend before a frontend that requests the new format. Verify on the new preview that the network responses use format=columns, that both complete partition counts match RDS, and that the match tabs and mobile player totals remain correct.
