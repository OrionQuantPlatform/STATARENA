# Hosted preview verification, 4 November 2026

The protected Git preview at commit `e1771cc4376d0cd700c9ef59a643fb3c0ada949c` passed **26 match/player checks and six cross-competition checks** in separate authenticated Chromium contexts. The read-only Vercel deployment record identifies Git as the deployment source. The earlier manual deployment API 402 remains a separate historical receipt. [Hosted preview](https://statarena-analytics-7jfl1udrw-hlemonniers-projects.vercel.app) · [Deployment record](deployment.json)

| Interaction | Verified hosted result |
|---|---|
| Desktop and 390px mobile match opening | Boulogne 1–1 Red Star, with zero season partition requests on either overview. The match summary returned HTTP 200. |
| Stats and shots tabs | Each tab fetched its own endpoint on click. The browser displayed 10–8 interceptions and all 23 source shots, including Damien Durand’s third-minute goal. |
| Player selected from match | Selecting Damien Durand fetched exactly three owning-league partition pages, all HTTP 200. The scoreboard remained visible. The comparison retained both Durand and Gaëtan Poussin. |
| Mobile player season | The page displayed 10 matches and 804 minutes, matching fresh TLS, read-only RDS results. |
| Cross-competition comparison | Giovanni Daffara and Giovanni Fabbian remained selected across match navigation. The foreign match opened without preloading its league. Selecting Yaya Fofana fetched the three owning-league pages. Reopening the original comparison fetched no further partitions. |

[Match and player receipt](match-20261104T050752893646Z/result.json) · [Cross-competition receipt](comparison-20261104T050812316288Z/result.json) · [Source rows](source.json)

The served JavaScript chunk `/_next/static/immutable/chunks/12chxd3vr61-t.js` contained the dedicated CloudFront hostname. The browser inspected 34 AWS API requests in the first run and 50 in the second. None carried a cookie, Authorization or Vercel bypass header. There were no off-origin structured API requests or uncaught browser exceptions. One optional player-honours lookup and one league-catalog lookup returned HTTP 404. Those resource gaps remain visible in the per-request receipts.

The scope remains two published partitions with 189 matches. These checks establish preview behavior for the selected paths. Production cutover and full catalog, profile and historical coverage remain unverified.

## Rerun

Use the authenticated Vercel CLI and installed Chromium/Playwright CLI. The harness uses a fresh temporary directory and an exact-host cookie for each mode. The retained source values came from the read-only SQL helper in the earlier preview suite.

```sh
python3 docs/verification/aws-deferred-preview-20261104/verify.py access
python3 docs/verification/aws-deferred-preview-20261104/verify.py match
python3 docs/verification/aws-deferred-preview-20261104/verify.py comparison
```

The comparison test deliberately delays the genuine foreign-match summary by 500 ms to expose selection-ordering errors. All football values come from the deployed API.

[Mobile match](match-20261104T050752893646Z/mobile-match.png) · [Mobile comparison](match-20261104T050752893646Z/mobile-performance-comparison.png) · [Cross-competition comparison](comparison-20261104T050812316288Z/comparison.png)

## Hosted replay after the partition-read optimization

At 05:27 UTC the same e177 hosted preview passed **26/26** match and player checks against backend release ZIP `becaa1bf45650936555cd01a69fb1e41406e4e60c8da43cf30b68eb76fa35e91`. The read-only Lambda configuration check independently matched the deployed code hash and reported Active, Successful, Node 24 and 512 MiB. [Backend receipt](p2-backend.json) · [Fresh browser receipt](match-20261104T052729928341Z/result.json)

Both match overviews opened with zero season partition requests. Selecting the player triggered three successful owning-league pages. Score, stats, all 23 shots and season minutes continued to match the SQL fixture. The browser inspected 37 CloudFront requests and found no forwarded credentials, off-origin structured requests or uncaught JavaScript exceptions. Optional player-honours and league-catalog calls returned 404. The earlier cross-competition receipt remains the latest six-check run for that separate flow.

Latest deployment metadata subsequently confirms d17473058f READY. The frontend diff from the tested e1771cc437 is empty; its API backend is independently verified asZIPbecaa. The browser run remains attributed to its actual e177 host. [Latest metadata and limits](latest-ready.json).
