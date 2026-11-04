Private prospect only, normal real Next app plus stable cache of the current published AWS CloudFront dataset. Compare cold finished match before vs deferred; record exact HTTP resource types/path counts and first-visible scoreboard. Deliberately delay only local partition replay equally in each run so request lifetime can be observed. A player click must leave the scoreboard mounted and provide a busy state until the correct cohort is present, after which rating, dialog and comparison resolve. A failed partition must allow retry, bookmarks must remain operable, search should load all only on intent, and a previously hydrated scope should be reused. Upcoming/context may legitimately request scoped partitions. No shared product file modifications.

## Cross-scope and native-season review cases

Before modifying the private candidate, warm the real Serie A list, navigate within the same Next app to the real Reims–Sochaux match with that still-selected league, then click its leading player. Require either the correct Ligue 2 appearance or an actionable error; a silent result is a failure. Separately, emulate a source using native single-year 2026 on this genuine match summary while the actual manifest publishes its league under 2026/2027. Verify the player dialog resolves that owning partition. Confirm loading can be canceled without reopening on late completion. Existing focused cases must still pass.

## Retained inputs and replay from a checkout

`inputs/aws-replay.tar.gz` retains every cached public response, with archive checksum in `inputs/manifest.json` and individual response hashes in `results.json`. Extract it in this evidence folder. The replay proxy adds the documented 220ms delay only to season pages. It neither needs DB credentials nor contacts the provider. A bounded fallback can fetch currently missing paths from the deployed AWS API.

Create an isolated checkout at the revision in base.txt, install `dashboard` dependencies from the lockfile, and make this evidence folder available there. Start `python3 docs/verification/aws-deferred-match-20261104/api.py`. In dashboard start Next dev with `NEXT_PUBLIC_API_ORIGIN=http://127.0.0.1:18947`, hostname127.0.0.1/port18948, as recorded in REVIEW.md. From the checkout root:

```
python3 docs/verification/aws-deferred-match-20261104/browser.py before
```

For the two originally reproduced review failures, apply `first-candidate.patch` to the baseline four application files and run modes `foreign-before` and `native-before`. Restore those four files to the baseline, apply `reviewed-candidate.patch`, then run modes `after`, `fault`, `intent`, `warm`, `shots`, `upcoming`, `standings`, `foreign-after`, `native-after` and `cancel`. Restart the dev server if the bundled application is stale. Use an isolated checkout: the restore operation is only for those four known files there. Original logs remain in replay-logs; fresh logs are emitted adjacent to browser.py. `emit-review.py` verifies assertions and regenerates its digest from the selected current application files; pin the reviewed candidate revision before using it.

The root's separate production workflow uses no proxy or artificial delay; see PRODUCTION.md.
