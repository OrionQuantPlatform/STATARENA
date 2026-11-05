# Four normalized player period routes: protocol before code

Suggested commit: feat: serve versioned typed player period statistics.

This is the second sublot under the player/advanced category. A separate
orion-pro-match-statistics.js leaves the qualified shot module unchanged.
It claims /players, /players/halves, /players/{player} and
/players/{player}/halves only. Requests explicitly name
representation=match-statistics-v1 and one exact v=pro1 token. The published
pair remains native107_core_v1/017, so existing native match details coexist.
The additional exact environment SHA in STATISTICS_PUBLICATION.json admits
this composite release. A legacy READY or another environment cannot claim
stats. ROOT controls the real writer. A local fixture may use ordinary
publication roles/guards and actual typed closure digests, never arbitrary
hash strings or a fake READY claim.

## Shape and selected facts

The v1 output keeps the old data container shapes (array for /players,
one player for /players/{player}, match_id + players for /players/halves,
match_id + one player for /players/{player}/halves). A representation member
states the normalized typed provenance. These are projections of a selected
family, not captures of independent subject requests.

Canonical coverage for players and player_halves is selected independently
at DG; match identity and player public aliases are checked at CG. Coverage
declares how many distinct source participants have complete typed facts.
An explicitly empty collection is allowed. Missing, unrecorded, unavailable,
ambiguous, foreign or partial coverage cannot produce an empty body.

Each admitted participant is an exact physical match_players row, linked to
its captured typed profile and match side. Its source record has the same
document/source and exact /data/i or /data/players/i slot. The physical profile
is valid at CG, uses match_statistics_observation_v1:<actor record> and
source:exact, and resolves its source fields from the same participant's
/player record. Global or other-source profiles do not substitute. Output
id/team_id use proven public aliases; name/image/position retain their
declared captured state. An alias outside the complete cohort is 404, not
a fabricated player row. Repeated source actor rows are rejected for this
normalized cohort. Their original observations can be retained independently.

A physical player_match_stats row supplies observed period membership. It
uses the exact participant and family document, declared period code/version
and coverage variant; it does not contribute calculated statistics. The
full-match family permits one full_match membership. The halves family
uses explicitly observed period memberships only and renders their existing
normalized period labels in the typed definition order. A missing half
cannot be inferred. A known empty stats set within a declared period can
emit stats=[] only when the production publisher proves it. The admitted
input contract forbids using synthetic summary or period rows to certify
unobserved coverage.

Actual numbers, strings, booleans, nulls and omissions are selected through
player_match_metric_values with the same physical member/period and exact
source scope. Explicit typed absent does not become zero or null. No numeric
calculation or conversion from the summary takes place. A stored denominator
is shown only when it and the retained numerator are finite exact numeric
facts. The adapter never derives a missing total, proportion, count or half.
Metric labels and keys come from registered typed definitions/mappings.
Each period has one normalized group, top_stats, whose labels must be unique
and whose entries have stable metric key order. The source groups, titles,
arrays, stat.type and raw total omission in the independent archive are
separate fidelity work. An original duplicate across source groups does not
justify silently overwriting a normalized metric: conflicting admitted
values fail closed. Empty sets and value kinds remain explicit.

The existing PlayerMetrics consumer uses data.stats[].stats[display label].
Each entry has its registered key and typed stat.value/total where observed.
The existing period labels All, FirstHalf, SecondHalf, ExtraFirstHalf,
ExtraSecondHalf keep the UI path intact. No group label, position, display
name or sort key is taken from a current live resource.

## Closure and validators

Same effective DG/CG for all three components. The exact stats component
includes the two coverage rows per match (including known empty), complete
source records/documents, selected noncanonical physical memberships and
period rows, selected scalar revisions and all used metric definitions,
source mappings, period definitions, captured player profiles, participating
team/match revisions and selected public aliases. Include row identity,
observation type and presence, physical provenance and all represented
typed values. Exclude interval ends and volatile write clocks. Numeric
and timestamp domains are canonical typed encodings. The synthetic oracle
captures actual typed tuples independently of the reader's SQL.

A stats-only correction must change its component, joint dependencies, pro1
and response validator; an old v and independent edition remain exact. The
unchanged native017 binding still supplies native1 and existing six routes.
Admitted HEAD/304 use the exact READY environment and bounded coverage/
subject metadata. They transfer no metric or profile values. GET budgets
are 2 metadata SQL calls plus at most 3 typed payload SQL calls, 120 members,
8 explicit periods per member, 3,000 metrics and 1 MiB encoded body. No silent
truncation and no query per athlete/metric. External source calls are zero.

## Before-code owned HTTP matrix

| Case | Workflow | Observable requirement |
|---|---|---|
| P01 | 012–017 actual migration/app, guarded 017 baseline with another environment | Old native match reader usable, stats route refuses once wired |
| P02 | Composite synthetic READY with actual tuple digests, actual unwired route | Expected 501 RED/zero SQL; wired success names exact v/env and data |
| P03 | Full-match typed cohort with two players | Exact alias/member, observed profile and keyed stats; noncanonical decoys omitted by physical scope |
| P04 | Single player scope | Same own row, another match/player not found, secondary alias resolves the same actor |
| P05 | Halves batch | Exact observed periods in definition order; full-match values cannot fill a missing half |
| P06 | Single halves | Exact match_id and the selected observed periods, independent of full-match collection |
| P07 | Presence and numeric types | Number lexemes 9007199254740993 and 0.8200000000000000001 exact; known null, absent, false and zero distinct |
| P08 | Denominator | Exact stored denominator retained; an unknown/absent total does not become a computed number |
| P09 | Coverage and empty | Empty typed family and proved empty period produce appropriate []; missing scope named 503; no false empty player |
| P10 | Wrong source or ambiguous rows | Missing/foreign profile, foreign member/period or repeated labels refuse; no alternate alias/source fallback |
| P11 | HEAD/304 and conditional miss | Same scoped validator/zero value reads on validators; nonmatch returns same complete body |
| P12 | Version/method/token | Wrong env/pair, invalid/duplicate parameters, out-of-scope match; status and no-store exact |
| P13 | Stats-only correction | New joint/pro1/ETag, unchanged V1/native facts; previous body/ETag and independent edition exact |
| P14 | Permissions, cap, coexistence | Runtime grants deny writes, original V1 and six native readers still available on admitted snapshots, bounded metrics and no fallback |

Proposed one owned PG18.6, 120 s, 5,000 typed rows, 4,000 SQL, 200 actual HTTP
including traces, 64 MiB evidence, 1 GiB owned disk, five connections,
source-free. Request ROOT allocation only when frozen. Persist exact command,
expected/actual, typed setup, SQL/HTTP traces and owned cleanup; stop on first
unexpected failure. No production/source/hosted qualification.
