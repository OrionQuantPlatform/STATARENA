# Edition-bound entity readers — pre-code protocol

Suggested commit: `feat: add typed edition-bound entity profile readers`.

Scope: a new opt-in backend helper only. No production route activation, model,
migration, publisher, frontend, credentials, remote source or cloud changes.
Approved model: `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08`.
The helper must preserve the existing summary/shots reader and its tokens exactly.

## Contract and failure modes (specified before implementation)

* Existing ID routes `/api/pitchapi/{players,teams,leagues}/{id}` return
  `{data: profile}`. Existing `/api/archive/profiles/{kind}/{id}` returns
  `{status:200,data:profile}`. These are normalized entity projections, not an
  assertion that all original provider keys/states have been represented.
* Existing `/api/pitchapi/leagues` returns `{data:{leagues:[...]},pagination}`.
  It groups currently published editions by public competition ID, supports
  limit1–100, cursor and q, and detects a changed publication set between pages.
  It never invents `is_free`, latest season or zero match counts. With `v`, it
  is a frozen single-edition catalogue. Without `v`, discovery is mutable.
* Profiles and `/api/scouting/routes` require one existing `pro1` edition token
  in `v`; missing/invalid tokens400, absent publication503. Routing keeps the
  existing `{routes,clubRoutes}` shape, up to8 player and8 team IDs, and returns
  only observed membership in that token's edition. It is not global history.
* Team scope is a selected engagement or a selected participant of a selected
  published match in the build. Player scope is a selected match participant.
  Canonical/temporal/publication selection applies at the pinned generations;
  mutable identity labels, `player_search`, legacy schemas and source bodies
  cannot be used as profile content. Unknown/cross-edition aliases404.
* Profile precedence is provider_global/provider:exact from the entity's
  selected edition source(s), then legacy_normalized_global from those sources,
  then manual global/sourceNULL. No row-ID/date tie-break: tied winners503.
  Missing profile404, with no invented identity fallback.
* Native position/shirt states preserve absent (key omitted), null, empty or
  numeric/string zero and leading-zero strings. An exact decimal that cannot
  round-trip through JSON's numeric representation503 instead of coercion.
* Missing image reference is null (unknown). A linked image must resolve to an
  existing, SHA-addressed image with matching MIME using the supplied media
  origin. Media metadata participates in ETags. Because media_assets is mutable,
  profile responses use revalidation even with v; no one-year immutable promise.
* HEAD and matching If-None-Match consult publication, identity, candidate and
  media metadata before content. They return zero body bytes and execute no
  entity-content/directory-content/routing-content query. Errors are no-store.
* Unknown parameters, duplicate keys, malformed IDs/cursors/filters, invalid
  methods and scope-reused cursors fail before content. Query values are bound.
  Pages use a total public-ID order with limit+1; no unbounded season download.

## E2E matrix

| Case | Setup/input | Expected observable outcome |
|---|---|---|
| E01 runtime | exact sealed012/013/014 + bootstrap |94tables; runtime read-only; write denied |
| E02 unpublished | entity catalogue before fixtures |503/no-store/no content |
| E03 parameters | duplicate/unknown/key malformed |400 and0SQL |
| E04 required version | profile/routing without v |400 and0SQL |
| E05 token | malformed/overlarge/tampered/missing build |400/503, no content |
| E06 player | A provider profile |name priority, empty country/short name, string07/null |
| E07 team | A provider/legacy profiles |correct source precedence; no mutable identity fallback |
| E08 player legacy | B competing-source profile |legacy same-source chosen |
| E09 team manual | B manual profile |manual chosen when source-qualified profiles absent |
| E10 absent scalars | C manual player |absent position/shirt keys omitted |
| E11 competition | A league profile |existing ID/name/country/image/season fields |
| E12 archives | all three archive profile kinds |status200 + data envelope matches provider route |
| E13 cross edition | player/team absent from token scope |404/no-store/no content |
| E14 missing profile | selected player with no profile |404/no-store/no content |
| E15 unscoped identity | valid alias/identity but no membership |404/no content |
| E16 routing | requested player/team IDs at A |only selected A membership, existing routing shape |
| E17 routing validation | no IDs, >8IDs, malformed lists |400 and0SQL |
| E18 catalogue pages | two competitions, limit1 |two unique IDs, deterministic cursor and terminal null |
| E19 catalogue validation | bounds/duplicate/unknown |400 and0SQL |
| E20 cursor scope | tamper or change q/limit |400/no content |
| E21 HEAD | cold catalogue/profile/archive/routing |200, body0, metadata only |
| E22 revalidation | GET ETag then matching/list If-None-Match |304/body0/metadata only; GET/HEAD validators agree |
| E23 missing HEAD | unknown scoped entity |404/body0/no-store, no content |
| E24 correction | typed profile correction + new A/B publication |new profile and validator; independent C token stable |
| E25 pinned reread | original token after correction |same original body/ETag |
| E26 mutable cursor | catalogue page1 before publication correction |409 after correction, no content |
| E27 corrected routing | new token, same scoped facts |same membership; new representation header |
| E28 unsafe number | exact9007199254740993 typed profile |GET/HEAD503, no lossy output |
| E29 ambiguous profile | two top-ranked legacy candidates |GET/HEAD503, no arbitrary selection |
| E30 closed boundary | unsupported match family + trace audit |helper null/0SQL;0external attempts; no legacy/current sports reads |

Run from repository root using the Python interpreter with psycopg and local
PG18.6 binaries:

```
python3 tests/orion_pro_entities_local.py --label precode --precode
python3 tests/orion_pro_entities_local.py --label entity-contract
```

The first command records the absent implementation before code without opening
a DB or a server. It is a structural RED, not executed API acceptance. The full
run owns one loopback PG/Bun server and a synthetic A/B/C/D corpus; each run saves
the command, expected cases, inputs+hashes, full HTTP/SQL traces, outcomes, logs,
and cleanup proof. A failed case stops dependent cases as unverified. No real
source data, RDS, browser, production cutover, global history or latency gain is
established by this fixture workflow. Root grants the PG slot before execution.

UX: existing profile and routing envelopes remain recognizable. DX: isolated
typed readers with one explicit snapshot contract. AX: bounded deterministic
pages and inspectable errors/versions. Tradeoff: explicit v and media
revalidation require frontend integration; this helper is not activated here.
