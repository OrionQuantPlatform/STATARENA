# Coverage admission proposal — real key, no surrogate

Suggested commit: `docs: audit publisher harness against the sealed Pro schema`.

This replaces only the proposed harness/admission contract. It is **unapplied**, creates no model field and is not a source acceptance decision. The business declaration still has to specify exact edition/match revisions, source/policy, admitted types and collections; a matching artifact SHA does not supply that decision.

`ingest.match_coverage` has23 columns. Its physical PK is `(match_id,source_id,feature_code,variant_key,recorded_from_gen)`; its logical observation key is the first four columns. Neither `id` nor `revision_id` exists. `data_revision` is a positive content/family revision, **not** a replacement surrogate. `match_revision_id` binds `(match_id,match_revision_id)` to the actual match row. `recorded_to_gen` is the nullable exclusive interval end; no `is_deleted` column exists on this table.

The admission member should replace `coverageRevision` with `coverage`, either JSON null when there is no selected observation or this metadata object:

```text
coverage = {
  key: {
    match_id: bigint,
    source_id: bigint,
    feature_code: text,
    variant_key: text,
    recorded_from_gen: bigint
  },
  dataRevision: bigint,
  matchRevisionId: bigint,
  recordedToGeneration: bigint | null,
  sourceRecordId: bigint | null,
  documentId: bigint | null,
  coverageState: text,
  collectionState: text,
  observedRowCount: integer | null,
  isCanonical: boolean,
  isStale: boolean
}
```

Every field maps directly to its named approved column. SQL bigints remain lossless Python integers in this local Python→JSON→Python contract, range-checked as signed64-bit and never converted through float/JavaScript Number. The key must be complete and have feature_code=`shots` for these V1 readers. Source-record/document references remain nullable as the schema says; provider provenance separately requires the real non-null source_record_id. A nullable direct document_id must not reject a valid source_record→document binding. Contract/transform/provenance columns remain checked against the typed SQL row/source admission; they are not inferred from this object's hash.

Reconciliation at declared dataset generation dg must require the exact five-column key, correct match revision/source/variant and:

```text
recorded_from_gen <= dg
AND (recorded_to_gen IS NULL OR dg < recorded_to_gen)
AND is_canonical
```

There is no `NOT is_deleted` predicate for coverage. The canonical current unique index is `(match_id,feature_code) WHERE recorded_to_gen IS NULL AND is_canonical`; historical interval uniqueness is enforced by013. An attempted second canonical current coverage is an existing source-guard rejection23505, not an opportunity for a publisher to choose a latest row.

The declared interval end is typed metadata, not an immutable equality requirement forever. Existing SQL permits closing an open interval once. A retained old admission/pin may still select the same key after its end becomes a later generation: actual selection at dg must remain true and existing close-once rules must hold. Do not reject that historical representation merely because its earlier declaration had recordedToGeneration=null. A key whose actual end is≤dg is stale and must be rejected.

Native collection semantics are:

| Retained coverage | Count | Reader summary | Shots GET |
|---|---:|---|---|
| No selected row | n/a | coverageStates.shots=`unknown`; coverage.shots=null |404 NOT_COLLECTED/state unknown, no-store |
| collection_state=`present` | Positive, V1≤1000 | state present; availability true |200 actual selected source/variant rows, exact count |
| `empty` |0 | state empty; availability true |200 periods=[], no heavy shot query |
| `unavailable` | SQLNULL | state unavailable; availability false |404/state unavailable, no-store |
| `absent` | SQLNULL | state absent; availability false |404/state absent, no-store |
| `null` (the text enum) | SQLNULL | state `null`; availability false |404/state `null`, no-store |

SQLNULL for collection_state is forbidden. `unknown` is a reader state for no row, not a legal stored collection_state. No empty array or0 may stand in for absent/null/unavailable/unknown. The current five-match fixture covers the first four rows only; absent/null coverage behavior remains an explicit additional E2E requirement before a broad native-state claim. No reader DTO change is proposed.

The is_stale boolean must be preserved and included in reconciliation/dependency material. Whether a historical stale observation is admitted is an explicit source-policy decision; this review does not invent a freshness policy or use timestamps/IDs to choose observations. Failed/pending/invalid/not_requested canonical source collections are already refused by013. This is distinct from an admission claiming an old coverage key or data_revision.

For the controlled synthetic B collection change1→2, the proposed fixture must explicitly move data_revision1→2 while closing/inserting its real keyed versions. The same principle applies to synthetic changed score/shot/player-profile content where data_revision exists. It does not authorize rewriting source-native revisions in any real normalizer.

Required P05 counterexamples: change one key component; claim an old closed key at a newer dg; claim a wrong dataRevision or matchRevisionId; mismatch observed count/actor/period; try illegal duplicate canonical coverage. These must be distinguished from the valid historical old-key pin and the unchanged noncanonical decoy. No arbitrary latest-ID/timestamp selection is permitted.
