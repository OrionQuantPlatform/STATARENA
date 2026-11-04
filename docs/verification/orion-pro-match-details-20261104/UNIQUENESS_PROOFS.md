# Exact source cohorts and uniqueness — static proofs, no SQL execution

Suggested commit: `docs: propose typed native match detail amendments with cohort proofs`.

These are model implications/query designs. No database is queried. A complete predicate that implies an existing key proves **at most one**; completeness/count/identity checks must separately prove **exactly one**. Neither an ORDER BY row ID nor a timestamp/LIMIT1 is a uniqueness proof.

## ROOT-ID and ID-SLOT

Existing source_records has PK(id), UNIQUE(source_id,id) and UNIQUE(document_id,locator), and is append-only. A response root record is explicitly referenced by coverage.source_record_id. The proposed new contract makes its locator the native response data object and its external_key the native data.match_id, under coverage.source_match_id_state. It does not reuse an old archive-member external_key as if it were that field.

For a native ID field stored in metadata, the full predicate is same source, same immutable document and **exact locator equality**. It implies UNIQUE(document_id,locator), hence at most one. Explicit owning state controls omitted/null/value; missing metadata alone never establishes absent. External_key is used only for identifiers, not names, measurements, totals or formats.

```sql
-- DESIGN ONLY: :member_record is the explicit physical event/H2H record.
SELECT field.external_key
FROM ingest.source_records member
JOIN ingest.source_records field
  ON field.source_id=member.source_id
 AND field.document_id=member.document_id
 AND field.locator=member.locator || '/team_id'
WHERE member.id=:member_record;
```

H2H uses exact `/home/id` and `/away/id`; root/actor IDs use the designated root/object record's external_key and explicit state. No prefix LIKE, global scan, mutable public alias or numeric-to-text ID conversion decides the native identifier.

## OBS-PROFILE

Existing profiles have physical PK(id) and UNIQUE(id,actor_id). Proposed event refs and existing match_players.profile_version_id use these keys; root team refs use the team-profile PK plus a deferred selected-side check. Thus the physical pointer identifies at most one row. Exact document/locator/source/context validation prevents selecting a global resource profile for the same actor.

```sql
-- DESIGN ONLY: a native event player's exact physical profile reference.
SELECT p.display_name,p.source_name_state,p.source_image_url,
       p.source_image_url_state,p.raw_position_code_state,
       p.raw_position_code,p.raw_position_code_source_number
FROM football.match_events e
JOIN ingest.source_records er ON er.id=e.source_record_id
JOIN football.player_profile_versions p
  ON p.id=e.player_profile_version_id AND p.player_id=e.player_id
JOIN ingest.source_records pr
  ON pr.id=p.source_record_id AND pr.source_id=e.source_id
 AND pr.document_id=er.document_id AND pr.locator=er.locator || '/player'
WHERE e.match_id=:match_id AND e.source_id=:source_id
  AND e.feature_code='events' AND e.variant_key=:variant
  AND e.recorded_from_gen=:parent_from_gen AND e.event_seq=:event_seq
  AND p.profile_context='native_match_observation_v1:' || pr.id::text
  AND p.variant_key='source:exact'
  AND p.recorded_from_gen<=:cg
  AND (p.recorded_to_gen IS NULL OR :cg<p.recorded_to_gen)
  AND p.is_canonical AND NOT p.is_deleted;
```

The full event parent key plus event_seq implies its PK; the profile FK plus id implies its PK. Catalogue generation/context/ownership checks constrain eligibility, not ranking. A missing or nonmatching referenced profile fails reconciliation; there is no provider_global/manual fallback. The build must pin a catalogue snapshot containing this observed profile dependency.

Current global profile contexts do not prove this property. The current family mapper does not persist these exact native actor-object profiles. These are representable existing destinations requiring proper ingestion/binding, not an assertion that current rows already satisfy the design.

## EVT-PARENT and H2H-ENTRY

Both are already children of the complete coverage PK `(match_id,source_id,feature_code,variant_key,recorded_from_gen)`. Events add proposed UQ(parent,source_ordinal); their event_seq remains a within-parent key, not an external source ID. H2H already has PK(parent,entry_ordinal), with a proposed nonnegative check. Count/contiguity must be checked; neither unique key alone proves no member is missing.

Two source observations with the same match/minute/player/type remain distinct through parent keys/ordinals. Never group by those display values. No cross-parent children can be obtained through an exact full-key join.

## LIN-HEADER and LIN-SLOT

Existing lineup UNIQUE(match_id,team_id,revision_id) supports the proposed match_players version FK. The header's new complete collection FK binds the source/variant/coverage generation. Each member references its own immutable source record, whose exact relative locator is `/starters/<i>` or `/subs/<i>` under that side header. Its existing ordinal must equal the canonical decimal suffix, with `i>=0` and no leading zero representation except0.

```sql
-- DESIGN ONLY: direct SQL order from existing metadata, no new ordinal registry.
SELECT mp.revision_id,mr.ordinal,mp.profile_version_id,
       mp.shirt_number_state,mp.shirt_number,mp.shirt_number_source_number
FROM football.match_lineups l
JOIN ingest.source_records lr ON lr.id=l.source_record_id
JOIN football.match_players mp
  ON mp.lineup_revision_id=l.revision_id
 AND mp.match_id=l.match_id AND mp.team_id=l.team_id
JOIN ingest.source_records mr
  ON mr.id=mp.source_record_id AND mr.source_id=l.source_id
 AND mr.document_id=lr.document_id
 AND mr.locator=lr.locator || '/starters/' || mr.ordinal::text
WHERE l.revision_id=:lineup_revision_id AND mr.ordinal>=0
  AND mp.recorded_from_gen<=:dg
  AND (mp.recorded_to_gen IS NULL OR :dg<mp.recorded_to_gen)
  AND NOT mp.is_deleted
ORDER BY mr.ordinal;
```

Given one header/section/index, exact locator equality plus UNIQUE(document_id,locator) implies one member source_record. Proposed slot uniqueness `(lineup_revision_id,source_record_id)` at every historical generation then implies at most one active member fact. Parent list-state/count, contiguous indexes and exact actor/profile resolution prove completeness. Repeated player IDs in different slots remain possible; the slot and observation variant distinguish occurrences. This is a selected native source cohort, not a promotion of each member to global canonical participation.

**Current counterexample:** the current lineup mapper gives every member the family-root source_record_id, without a member ordinal/locator, so existing metadata cannot reconstruct order from those rows. Existing match_players logical uniqueness is by player/variant and permits different players under one record; it does not prove slot uniqueness. The proposal adds only the parent/slot guarantee, reusing the existing locator/ordinal fields. Historical non-overlap needs a deferred guard because a current-only unique index cannot prove past intervals did not overlap.

## STAT-PERIOD, STAT-GROUP and STAT-ITEM

Current per-side scalar source locators contain period/group/item positions, but there are no period/group records preserving empty structures or observed group/title/format values. Existing scalar logical keys cannot preserve repeated keys without explicit variants, and source_metric_mappings is unique in the **forward** raw-key mapping, not an inverse code→original-item key lookup.

New structural PKs are parent+source_record_id. Groups carry a complete same-parent FK to the exact period source record; items carry the corresponding group FK. For period/group/item records respectively, the new contract checks:

```text
period.locator = root.locator   || '/periods/' || period.ordinal::text
group.locator  = period.locator || '/groups/'  || group.ordinal::text
item.locator   = group.locator  || '/items/'   || item.ordinal::text
```

Same-source/document equality and canonical decimal ordinal are mandatory. UNIQUE(document_id,locator) proves one source record per position; the child PK/FK proves one structural row per that exact parent position. Count/state/contiguity proves the expected full collection. An empty group/period has a typed header and no children, preserving its native state without a fake scalar row.

Item home/away scalar FKs each imply one existing typed revision. Deferred checks validate dataset interval, same source/match/side/registered period/raw-key definition and declared observation variant. An unchanged scalar can be retained while a new layout child changes title/order; the membership pointer is explicit and its value/state must be reconciled with that new source observation before sealing. It is not chosen by latest ID/time or by reverse mapping a shared metric code. Two different items with the same raw key stay two physical layout items, even if their scalar values happen to match.

## H2H-ROOT

Proposed summary PK is exactly the existing coverage parent key, so there is at most one supplied-total record per observation, including an empty recent list. That key does not assert a relation between total_matches and list length. A full native response requires one summary child and a reconciled root state; absence of a legacy summary row means unrecorded/unknown, not four zeros.

## Proof limits

Keys/FKs prove cardinality and ownership; they do not prove a stored scalar equals its provider input. Qualified diagnostic types/counts do not prove all values were mapped. Exact source-to-typed reconciliation, metadata contract admission, identity resolution, deferred historical checks and actual reader/serializer E2E remain future gates. These designs have not been compiled or executed in PostgreSQL and do not authorize a migration.
