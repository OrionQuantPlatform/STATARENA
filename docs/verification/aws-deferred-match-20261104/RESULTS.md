# Selected-match demand loading

A cold finished match requests its bounded summary before any season partitions. Player performances load only on an explicit action for that match. The current match/client stay mounted while a separate cohort supplies percentiles, appearance detail and comparison. Already selected comparison rows remain usable across navigation; their bounded snapshots cannot start or replace another match's cohort.

The initial private Next replay used genuine captured AWS Reims–Sochaux data. It reduced the first view from **7 season requests to 0**, and from **3,738,727 to 10,746 structured response bytes (−99.7%)**. Its deliberately delayed development timings do not establish deployed latency. The 13 original scenarios, source hashes and their limits are in [REVIEW.md](REVIEW.md) and [results.json](results.json).

The parent independently built the final application for production and drove actual Chromium against the **live CloudFront→Lambda→RDS API**. All **26 checks passed**, including desktop/mobile zero-partition overview, actual score1–1,23shots,interceptions10–8, correct Durand appearance, requested owning cohort, comparison and season10matches804minutes. An independent six-check production workflow retained two genuine Serie A players across a delayed Ligue2 summary and verified Fofana's own cohort, without losing the pair or loading it preemptively. No JS exceptions. [Final production receipt](production-20261104T050142246253Z/result.json), [comparison receipt](production-race-20261104T050142246265Z/result.json), [exact commands](PRODUCTION.md).

The final repair also passed seven fresh captured-response Chromium scenarios: normal intent,503retry,bookmark/search,warm navigation,cross-league,native-season mapping and busy-modal cancellation. Their four source hashes match the final shared application. [Final regressions](final-regressions/final-regressions.json). The original cross-league/native and comparison race failures remain inspectable; the latter is [comparison-race-results.json](comparison-race-results.json). The initial production26-check receipt is retained separately and is not substituted for the final rerun.

The change intentionally leaves upcoming/context data on demand for the visible panel, scoped to the teams and competitions it needs. The studied upcoming match required three owning-league partition pages; standings required two fixture pages. A player dialog still loads its full required cohort. There is no claim of zero season reads for every feature or complete whole-site coverage from these selected fixtures. Vercel's daily deployment quota still prevents hosted verification of this source.

The React review checked stable page/client identity, unconditional hook ordering, primitive scope keys, promise reuse, explicit intent and cancel/retry behavior. Existing component structure and accessibility are preserved. Prettier and diff whitespace checks passed. No isolated unit tests were added.

Use [PROTOCOL.md](PROTOCOL.md) for retained response input extraction and baseline/first-candidate/final reruns. `final-candidate.patch` combines both changes against base.txt; the older patch files preserve review history. `inputs/manifest.json` pins the compressed public-response capture.

Suggested commit: `perf: defer selected-match season hydration until player data is requested`.
