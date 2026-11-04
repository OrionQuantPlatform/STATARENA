# Repeated heatmap actor observations — collision and bounded-context proof

Suggested commit: `docs: propose typed native match detail amendments with cohort proofs`.

This is a static model/contract proof plus a reference to **already executed** synthetic evidence. No SQL, mapper or new heatmap E2E is run here. It does not turn the earlier single-join experiment into a general profile-mapping acceptance.

Existing evidence: `docs/verification/orion-pro-heatmaps-20261104/runs/20261104T224628219790Z-root-reviewed-portable-sparse/result.json`, case `observed_profile_join_and_gap`, records `sameRecordActorVariantCohortJoin=1`, `repeatedTeamObservationCollision=true`, `generalProfileMappingAccepted=false`. The test intentionally inserts two profiles for one team under two map records but the same context/variant/generation and catches UniqueViolation. The failure occurs at insertion, before a better SELECT could help.

## Why the old key collides

The model has team-profile UQ `(team_id,profile_context,variant_key,recorded_from_gen)`, plus current variant uniqueness `(team_id,profile_context,variant_key)` and current canonical uniqueness `(team_id,profile_context)`. The first/current-variant keys apply even when `is_canonical=false`.

For two different source records A and B of team T in generation G, the experiment uses:

| Observation | team_id | profile_context | variant_key | recorded_from_gen |
|---|---|---|---|---|
| A | T | match_heatmap_observation | V | G |
| B | T | match_heatmap_observation | V | G |

Those unique tuples are identical. A join that additionally filters source_record_id cannot make the second row legal. Marking it noncanonical does not remove the generation/variant UQ. Relaxing these keys or choosing the largest ID is not proposed.

## Existing destinations with a precise occurrence context

Use a source record for each observed actor object, with an exact literal locator under the map row:

```text
root /teams/0        -> actor /teams/0/team
root /players/1     -> actor /players/1/team
root /players/0     -> actor /players/0/player
```

The full actual prefix is the explicitly referenced native response/map source record, not a global path search. Same source/document and UNIQUE(document_id,locator) give at most one actor record for each occurrence. A coarse root record shared by multiple occurrences is **not** sufficient. The current map-row external_key is a composite bookkeeping key; it must not be substituted as the actor's native ID. The actor-object record's external_key is the exact native string ID under its explicit state.

The proposed bounded policy is:

```text
profile_context = 'native_match_observation_v1:' || actor_source_record.id
variant_key = 'source:exact'
player external_profile_version_id = 'native-observation:' || actor_source_record.id
```

Here external_profile_version_id is explicitly a deterministic observation discriminator for this bounded new context, not a claimed provider profile-version ID or a new public alias. The native actor ID remains in the exact actor record's external_key under its state. Existing legacy/global contexts keep their old interpretation; a native profile-version field outside the qualified diagnostics would require separate faithful mapping review, not silent replacement by this discriminator.

Allowed actor-record kinds/paths are an explicit contract list: event player/sub-in, lineup member, root home/away team and heatmap row team/player. It is not a field-name/value registry or a free-form universal name table. The existing source-record FK supplies the complete source/document/locator ancestry; the context string is an eligibility key, not a row-ID preference or a replacement for that FK.

For records A≠B, the proposed contexts `native_match_observation_v1:A` and `...:B` differ. Therefore all existing team-profile generation/current-variant/current-canonical tuples differ, while the existing natural `(team_id,source_record_id,variant_key,recorded_from_gen)` UQ also differs by source record. For players, the source-record-specific external_profile_version_id additionally distinguishes the existing source/external-version/content-hash natural UQs even if two observations happen to have identical content hashes. No uniqueness constraint is weakened and no name table is added.

Repeated source IDs remain identifiers, not evidence that two observed name/shirt values are identical. The exact name and shirt type/value are retained in each observed profile. Existing raw shirt state/number columns preserve `'09'` versus9, NULL versus absent, and0. There is no global-profile substitution.

## Direct SQL predicate and cardinality

```sql
-- DESIGN ONLY, NOT EXECUTED. :suffix is the literal '/team' or '/player'
-- from the admitted actor kind, never an arbitrary client path.
SELECT p.id,p.display_name,p.source_name_state,
       p.shirt_number_state,p.shirt_number,p.shirt_number_source_number
FROM football.match_heatmaps h
JOIN ingest.source_records mr ON mr.id=h.source_record_id
JOIN ingest.source_records ar
  ON ar.source_id=h.source_id AND ar.document_id=mr.document_id
 AND ar.locator=mr.locator || '/player'
JOIN football.player_profile_versions p
  ON p.player_id=h.player_id AND p.source_id=h.source_id
 AND p.source_record_id=ar.id
 AND p.profile_context='native_match_observation_v1:' || ar.id::text
 AND p.variant_key='source:exact'
 AND p.recorded_from_gen<=:cg
 AND (p.recorded_to_gen IS NULL OR :cg<p.recorded_to_gen)
 AND p.is_canonical AND NOT p.is_deleted
WHERE h.id=:exact_heatmap_version_id;
```

Heatmap PK fixes one map row. Exact actor locator and existing record UQ fix at most one actor record. Actor+context+variant and the existing historical non-overlap guard fix at most one eligible profile at cg. Required existence/ownership/observed-value reconciliation must be checked before publication; zero rows is a gap, not a global fallback. The team query uses team_id/team_profile_versions and literal `/team` with the same proof. Profile variant does not have to equal the map's coordinate/capture variant: they are different scopes, both explicitly bound through the exact source record.

## Same record is a different case

If two renderings legitimately share the **same actor source record** and identical typed profile content, reuse the same physical profile. Do not insert a new context/version or allocate a timestamp/UUID suffix. If the same immutable actor record is given contradictory names/shirts, the unchanged UQs should reject it; changing the context to evade that conflict would hide a producer error. A true source correction uses a new source observation/record or an explicitly versioned transformation and new accepted generation, preserving the old frozen profile.

## Remaining limits and future E2E

No existing test has inserted this proposed context scheme. The later E2E must insert two same-team and two same-player observations with distinct records/context keys, including different names and `'09'`/9 shirts, and read each exact cohort. It must also reject contradictory same-record input, wrong actor/source/locator and a global-profile decoy; identical replay must reuse rows. The old collision receipt remains unchanged. Heatmap cells/shape/real-triplet acceptance remain owned by their separate lot and are not certified by this document.
