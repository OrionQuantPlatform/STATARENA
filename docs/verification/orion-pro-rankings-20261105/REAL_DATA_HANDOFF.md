The older ranking collector defines three provider families and writes a catalogue of normalized editions. A real Pro publication still needs an independent source reconciliation before the publisher sets the ranking completeness flag or binds the root documents to the catalogue. The local fixture uses synthetic observations.

| Existing contract | Typed admission | Remaining coverage |
|---|---|---|
| FIFA men's ranking editions keyed by the observed date | Exact FIFA source, system and method, edition root, entry record and native identifier. Keep rank, points and observed timestamps separate. Bind all declared ancestor pages that supply entries. | Original flag and confederation fields, provider object, and catalogue collection metadata need independent representation if required. |
| UEFA club coefficient editions keyed by ending year | Preserve official edition, source period, raw member ID and exact actor mapping. Verify every declared page and all entries before admission. | Historical provider row extensions and ranking images are outside this typed DTO. The club history keeps unmapped clubs distinct from absence in an admitted edition. |
| UEFA association coefficient editions and annual components | Preserve the association, rank and coefficient, then the exact observed season year and both native national points and earned points. | Aggregate teams still playing is a different observation from any annual component. Model103 cannot publish that aggregate through this reader. |
| SportsAPI dated snapshots | Keep the source and official status independent. Admit only a complete cohort that can be represented with exact typed actor identity and rank. | The legacy collector explicitly allows duplicate actors and null positions for SportsAPI. Model103 cannot reproduce those occurrences in the current grain. |

The publisher closure needs the exact scopes in [DEPENDENCIES.json](DEPENDENCIES.json). The prior raw index's upstream counts and errors must be reconciled separately. Counts in this reader describe the selected typed cohort.

Suggested commit `docs: record real FIFA and UEFA ranking admission boundaries`.
