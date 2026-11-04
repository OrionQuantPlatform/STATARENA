# Protected preview, 4 November 2026

The published match and player passed 19 of 19 checks on deployment 2a419. The desktop and 390px mobile scoreboards displayed Boulogne 1–1 Red Star. The desktop overview fetched the match summary. Opening Statistiques fetched the team statistics and rendered 10–8 interceptions. Opening Tirs & xG fetched and displayed all 23 shots, including Damien Durand’s third-minute goal with 0.55 xG. His mobile season view displayed 10 matches and 804 minutes. See [SQL source values](source.json) and the [browser receipt](20261104T041639366828Z/result.json).

The browser recorded 127 API responses across the three page loads. All football requests went to the dedicated CloudFront API. The selected tabs fetched no whole-match archive. There were 99 responses with HTTP 200, 16 binary asset redirects, nine partition size responses with HTTP 413 and three HTTP 404 responses. The 404s came from the leagues endpoint twice and the player honours endpoint once. Chromium reported no application exceptions.

Each page navigation downsized its partition request three times. The two match views each made 32 successful partition requests and the player view made 26. The summary arrived separately from those requests. Browser response-start timings for the desktop summary, stats and shots were 364 ms, 156 ms and 321 ms respectively, each a CloudFront miss. These samples exclude the time needed to load the initial partition data and do not establish whole-page or whole-site performance.

The open player view verifies season appearances. It does not verify a published profile or honours record. The evidence covers one Ligue 2 fixture and one player on the protected preview while two partitions were published. Production, remaining partitions, and archive or catalog coverage remain outside this run.

## Reproduction

In the checkout root, with project-authenticated Vercel CLI, Chromium and the private read-only Ohio RDS configuration available, run:

```sh
PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/aws-preview-core-20261104/source.py
python3 docs/verification/aws-preview-core-20261104/prove.py
```

The second command writes a timestamped result and screenshots. The protection cookie is scoped to the preview and removed after the run. The four screenshots share the browser receipt directory.
