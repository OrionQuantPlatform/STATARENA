# Two pinned normalized shot detail routes: protocol before code

Suggested commit: feat: serve typed match and player shot details.

This first sublot serves the two nested shot paths in ROUTE_SCOPE.md.
It preserves the frozen collection reader. Both routes require
representation=shot-detail-normalized-v1 and an exact v=pro1 token of one
published edition. The data envelope stays the single shot object or
player-with-shots object. Explicit representation metadata identifies the
normalized edition shots origin. The immutable build selects DG/CG.

A valid s_ key is the exact football.shots.external_shot_id inside the
canonical match/source/variant coverage. There is no global shot alias.
A valid p_ key resolves a pinned public alias and a proved player in this
match. The returned player uses the frozen V1 alias and profile order.
Secondary aliases may address the same actor. The player list is complete
only with exact coverage and no unknown shooter. Unknown shooters fail
closed in this first projection. A proved player can have a known empty
list; unknown coverage or identity cannot produce one.

Each shot preserves the existing V1 normalized DTO, coordinate state,
source coordinate fields, observed labels and zero/false. Independent
raw keeper, goal-crossing and blocked context is outside this
representation. Only the requested shot or player's facts should transfer
on GET. Metadata may check bounded IDs/counts, but no coordinates or values
on HEAD/304. The ETag binds v, route and parameters. The admitted parent
limit is 1,000 shots; body limit 1 MiB; 2 metadata SELECTs / 4 GET SELECTs.
Errors are named and no-store. No source, provider, Neon, RDS or S3 access.

| Case | Actual handler workflow | Required result |
|---|---|---|
| S01 | Owned PG18.6 012–015, Node24, frozen V1 baseline and typed positive/empty/unknown facts | Exact baseline token and DTO, read-only role, no dependency on 016/017 |
| S02 | Actual pre-dispatch GET individual shot | 501/no-store/zero SQL; after wiring exact selected V1 DTO |
| S03 | Other edition, same s_ ID and other frame | Pinned edition yields its own shot; V1 source coordinates and frame stay exact |
| S04 | Player with multiple shots and a noncanonical decoy | Exact player and source order, decoy excluded |
| S05 | Secondary alias to same player | Same typed actor and canonical returned ID/name, distinct route/validator |
| S06 | Proved participant with no shots and explicit empty match | Known empty only with coverage and playing evidence |
| S07 | Missing/unavailable coverage, absent shot, unknown/out-of-match player | Correct 404 and named no-store errors, no invented [] |
| S08 | Unresolved actor in complete match collection | Single shot preserves V1 null player; player list returns 503 |
| S09 | Corrected xG/profile, old and unrelated tokens | New facts/tag exact, old and unrelated pinned bytes unchanged |
| S10 | HEAD and matching weak 304 on both forms including admitted [] | Same tag, zero bytes, at most two metadata SELECTs |
| S11 | Conditional miss | Complete same GET body, no mixed generations |
| S12 | Duplicate/unknown/missing params, malformed or mixed token, method | 400/405 before values, no-store |
| S13 | Selection and transfer bounds | Only requested facts transfer; query and encoded size caps hold |
| S14 | Original V1 and legacy OFF coexistence; permission and cleanup | Frozen readers unchanged; runtime write denied; exact pins and zero external |

One owned PG18.6, at most 5,000 typed rows, 90 s, 4,000 SQL calls, 200 actual
loopback HTTP including traces, 64 MiB evidence, 1 GiB disk, five connections.
ROOT allocates a slot before a run. Freeze code, setup and independent expected
outcomes before the first query. Keep exact command, response/SQL traces,
first unexpected failure and cleanup. No hosted or real data acceptance.
