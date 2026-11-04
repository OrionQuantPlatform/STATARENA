# Compact frontend acceptance, 4 November 2026

The single scoped CLI request to Vercel returned HTTP 402 at 04:46:30 UTC. The response identified the daily API deployment limit, more than 100 deployments, with a 24-hour retry. The new commit therefore has no hosted preview receipt from this attempt. [CLI request and error](preview-cli.json)

The production Next build from exact Git commit `d5df4c5a9a31ee7954dc9403f2fdccb8736371e9` **passed 22/22 Chromium checks** when served on loopback with the live CloudFront API. Read-only TLS SQL independently confirmed Boulogne 1–1 Red Star and Damien Durand’s 10 matches and 804 minutes. Opening the match stats and shots tabs fetched their respective endpoints and rendered 10–8 interceptions and all 23 shots. The mobile match and player screens fit a 390px viewport. [Source](source.json) · [Build](build.log) · [Browser receipt and four adjacent screenshots](20261104T044728707534Z/result.json)

| Navigation | Prior protected preview partition requests | Current local build partition requests | Fixtures / matches / appearances | Current browser response body transfer |
|---|---:|---:|---|---:|
| Desktop match | 35 | 4 | 380 / 100 / 4,788 | 448,867 bytes |
| Mobile match | 35 | 4 | 380 / 100 / 4,788 | 448,328 bytes |
| Mobile player | 29 | 3 | 297 / 89 / 3,516 | 353,401 bytes |

The same three navigations went from 99 partition attempts to 11, an 88.9% reduction. All 11 used `format=columns`, limit 100, and returned HTTP 200 within a single source generation per traversal. The prior hosted run included nine size retries. Across these page and tab loads, the browser observed 36 CloudFront responses in the current run versus 127 previously. Of the 36, 20 returned HTTP 200, 15 redirected binary assets and the optional leagues request returned 404. No off-origin structured football requests or browser exceptions were observed. [Prior protected preview](../aws-preview-core-20261104/20261104T041639366828Z/result.json)

The first 100-fixture, 4,788-appearance page took 2.76 s on desktop and 6.29 s on mobile in this run. The observations include the live edge, origin and client network. They do not isolate the rendering cost or establish a before/after latency comparison. The local origin and earlier protected Vercel frontend differ. Both runs cover two published leagues and a single selected match and player.

## Reproduction

From the checkout root, create a private directory, extract the exact commit, install frozen dependencies and build Next. Keep the server running on an unused loopback port. Use the read-only connection file and CA referenced by the previous source-parity helper.

```sh
src=$(mktemp -d)
git archive d5df4c5a9a31ee7954dc9403f2fdccb8736371e9 dashboard/frontend dashboard/backend dashboard/shared dashboard/package.json dashboard/bun.lock dashboard/bunfig.toml | tar -x -C "$src"
(cd "$src/dashboard" && bun install --frozen-lockfile && NEXT_PUBLIC_API_ORIGIN=https://d317dq37z1tacb.cloudfront.net bun run build)
(cd "$src/dashboard" && NEXT_PUBLIC_API_ORIGIN=https://d317dq37z1tacb.cloudfront.net node node_modules/next/dist/bin/next start frontend --hostname 127.0.0.1 --port 51782)
```

In a second terminal at the checkout root, run:

```sh
PYTHONPATH=/tmp/statarena-archive-remat-pg/python python3 docs/verification/aws-compact-preview-20261104/local.py 51782
```
