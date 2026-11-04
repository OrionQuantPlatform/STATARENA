# Independent production-build acceptance

Run the reviewed four-file change in a real production Next server, with direct live CloudFront API and its typed RDS backend. Do not use the replay proxy for this check. The original SQL fixture is aws-preview-core-20261104/source.json: Boulogne1–1RedStar, DamienDurand90minutes/rating7.98, season10matches804minutes,23shots and10–8interceptions. The URL intentionally selects the other published league, exercising scoped player recovery.

Require zero season-page requests before either desktop/mobile match overview, successful summary + correct score, only requested stats/shots, the correct player on intent, comparison, continuously mounted scoreboard, unchanged season-player totals, no JS exceptions or non-AWS structured reads. Capture all API responses and phase, assertions, screenshots and product source hashes. Preserve failures. No hosted latency claim: the Next origin is localhost. Setup/build/runtime logs and script identify exact rerun commands.

```
(cd dashboard && NEXT_PUBLIC_API_ORIGIN=https://d317dq37z1tacb.cloudfront.net bun run build)
(cd dashboard && NEXT_TELEMETRY_DISABLED=1 node node_modules/next/dist/bin/next start frontend --hostname 127.0.0.1 --port 18954)
python3 docs/verification/aws-deferred-match-20261104/production.py 18954
```

The script uses the existing Playwright CLI headless config and the source verified by the earlier real read-only RDS receipt. It captures browser artifacts in output/playwright and copies the durable receipt into this evidence folder. No unit tests are added.

The final comparison-retention change also runs `production-race.py 18954` against this production server and live AWS. It selects two real Serie A leaders through the match list, navigates to a Ligue2 match in the same application while retaining the Serie A filter, delays only the genuine summary request by500ms, requires no foreign preemptive season fetch, opens the actual new player, and reopens the original pair. This is a controlled response delay, not a timing benchmark. The first summary-only implementation's reproduced failure and two-file fix are in comparison-race-results.json and comparison-followup.patch. `final-candidate.patch` combines both reviewed changes against the documented base; `reviewed-candidate.patch` retains the initial13-case implementation.
