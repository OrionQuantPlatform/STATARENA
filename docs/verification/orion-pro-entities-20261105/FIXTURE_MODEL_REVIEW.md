# Fixture audit against the sealed model before attempt three

Suggested commit: `feat: add typed edition-bound entity profile readers`.

This is static source/schema review, not a PostgreSQL pass. The product/router
remain byte-identical to attempts1/2. The original expectations and fixture are
preserved in the precode input archive, and both actual failed ledgers remain.

* Match participant status is `unused_substitute` with played=false, one of the
  approved five enum values. Its exact non-NULL match-team revision is supplied,
  with the same match/team/source as its parent. Its profile FK is genuinelyNULL,
  so the missing-profile case is legal and cannot use a mutable identity label.
* A has3matches/2engagements/2selected players; B has1/2/1; C has1/2/1;
  D has1/2/0. Finished counters come from the original match inputs. Only the new
  fixture derives team/player counters from canonical selected facts at build dg;
  the sealed013 validator still independently checks every ready build.
* D is not an empty edition: it has one upcoming published match, two explicit
  selected home/away sides and engagements, no final goals and no match_players.
  Its match/sides use the primary fixture source; the player/source set is
  genuinely empty. Team scope may therefore use primary-source provider profiles,
  while player scope yields no row. No zero player fact or profile is invented.
* Typed scalar cases preserve approved constraints: raw `07` string with no
  number, native0 number with matching raw/numeric columns, shirt null or empty
  string, and absent manual fields. The unsafe JSON number is finite/exact in SQL
  and remains a legal typed input; refusing its lossy JSON output is a reader gate.
* All new aliases are generation-bound; competition/season/match/side FK anchors
  are explicit. Snapshots are sealed before builds; ready outputs/publications
  use the original shared fixture workflow and its normal guards.
* Native index `football_player_profile_versions_sv_canonical_current_idx` is
  UNIQUE(player_id,profile_context) WHERE recorded_to_gen ISNULL AND is_canonical.
  E29's original same-context canonical ambiguity is therefore not constructible
  without weakening the model. Deactivating an anchored provider would also break
  selected-parent profile-context membership. ROOT approved replacing only this
  mistaken expectation: try a conflicting manual global C profile, require23505
  naming the exact index, rollback all row changes, then prove identical C
  GET/HEAD/ETag. Sequence allocation on a failed INSERT can advance; no claim of
  unchanged sequences is made. This does not hide a product failure.

Missing/future/source gaps and broad native fidelity remain separate from these
synthetic setup checks. No remote, source-body, credential or deployed read is
needed or authorized by this audit.
