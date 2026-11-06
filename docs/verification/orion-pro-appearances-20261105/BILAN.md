# Versioned typed appearances — local qualification

Suggested commit: `feat: serve versioned typed season appearances`.

The existing `/api/seasons/partition` is now served through the actual AWS app
when Pro mode, an admitted published pro1 token and matching edition are supplied.
Its new adapter contract is `normalized-season-v1-native31`; the four original
V1 readers and entity95021ded helper are unchanged. This adds one route form to
the earlier16 supported forms, leaving40 of the57 inventoried forms for later
reader/data work. ROOT owns the current global matrix and guard/CI update.

Actual run: `runs/20261105T142742229113Z-actual-node24-after-v1/result.json`.
SHA256: `7ad436304ade68867887368358a54b9d4723e59a5bffc8d63158140c5c7f4aea`.
All22 pre-code expectations passed under actual Nodev24.22.2/darwin-arm64 and
PostgreSQL18.6. The official Node archive hash is verified in runtime/DOWNLOAD.json;
this is local Node24 proof, not hosted Lambda/Linux deployment acceptance.

Exact rerun from the repository root:

```sh
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_appearances_local.py --label actual-node24-after-v1 --node24 /tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node
```

The runner supports explicit --pg-bin/--node24; reproduction of the Node binary
is recorded separately. It creates one owned cluster with sealed012/013/014 and
the approved103model, synthetic typed inputs, ordinary read-only runtime access,
an actual Node HTTP server and the existing unchanged browser consumer algorithms.
No unit tests were added. No provider/source/cloud/Neon credential or service is
used. All input descriptors, files, code pins, SQL/HTTP bodies/traces, consumer
output and owned cleanup results are retained in the run directory.

Measured total:16.264seconds,7,357initial→7,785final typed rows,3,370external
SQL calls and107actual HTTP requests (53public API calls),484,698public response
bytes, maximum recorded request SQL52.041ms. Observed owned disk81,490,107B;
evidence before the final report4,613,576B. These are synthetic local observations,
not production latency or a comparative speedup claim. The per-page GET uses8SQL;
HEAD/304 uses3metadataSQL and0response bytes with no native/fact/stats payload
query marker. Every captured source pin remained unchanged during the run.

The36match/192performance/5,952native-state fixture traverses18limit2 pages
without duplicate/lost IDs. Independent Python Decimal parsing preserves the
0.8200000000000000001 number, numeric0, string07, empty string, booleanfalse,
null and absent properties in both JSON and existing packed format. Numeric
NaN/±Infinity and unsafe integer inputs return503/NATIVE_NUMBER_INVALID; text
"NaN"/"Infinity" stays text. Missing native rows and admission coverage produce
named503 errors with no source/legacy fallback. Invalid params/cursors/scope400,
new versus frozen corrected facts, source/variant decoys, linked media changes
and historical-token revalidation are exercised through actual app.handleRequest.

Existing consumer agreement uses all192HTTP rows against independently saved
synthetic source descriptors:32season players, O cohort32 at450minutes and30at
540minutes, ordered top8 player similarity,12clubs and top6 club similarity.
The target495minutes has unweighted known-appearance rating40/6. A first page
alone yields0eligible similar players, preventing a truncated denominator claim.
Team reliabilityfalse excludes the first two clubs' one unqualified stats match:
5observations versus6for the other ten clubs. No algorithm/formula was changed.

The planned pre-code RED is retained separately:
`runs/20261105T140203974121Z-actual-node24-precode-frame-v5/result.json`,
SHA256 `85a5b21e3aa555aea224dacdbf7eb0db08e0a6cb21357bc82849902f5d4952c9`.
A01qualified7,357typed rows; A02received actual app501 before implementation;
the other20cases were unverified. Four earlier setup failures and their original
results remain, with exact corrections/SQL-count errata in FAILED_SETUP.md.
No functional expectation was weakened to achieve the AFTER result.

Cleanup verified: PostgreSQL/Node/admin clients stopped/closed and the owned
cluster directory removed.0external HTTP attempts. All cloud resources and real
data sources remain untouched by this lot.

Remaining limits: real core normalized_performance admission and unpreserved
structural facts still need qualified ingestion; dedicated efficient backend
aggregate endpoints, remaining detailed families/routes, full frontend UX and
hosted deployment/cutover are not completed by this local transport/consumer
proof. Heavy shots/events/heatmaps are explicit lazy/unknown projection families,
not fabricated collected-empty observations. Media is revalidated even for old
tokens. Pending model107 was not applied.
