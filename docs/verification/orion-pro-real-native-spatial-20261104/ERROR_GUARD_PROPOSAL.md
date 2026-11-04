# Capture blocked: JSON null error is not SQL NULL

The single approved capture ended failed after4SELECT/9666054decoded bytes,
0HTTP/0physical HTTP bytes. No READY receipt or live RAM socket remains. Do not
reset this ledger, restart a source capture or claim native31/spatial E2E passed.

The actual Neon metadata fingerprint matches endpoint,params,status200,path,
ordinalNULL,SHA and3957B size. The sole refusal is the metadata bit
`r.error IS NOT NULL=true`. The same bit was already true in the prior frozen
neon-direct inventory; a changed source version has not been shown.

Local schema001_neon declares error jsonb. The existing neon_ingest writer wraps
body.get("error") in psycopg Jsonb, which can encode Python None as JSON null.
This is a hypothesis for the live bit, not a proof of its current content.
The failed capture read only error presence; no actual error JSON content is
available in its journal. No additional source query is authorized to resolve it.

Failure matrix specified before a corrective patch:

| Case in owned local PostgreSQL | Required classification |
|---|---|
| status200, SQL NULL error | no structured error |
| status200, JSON null error | no structured error; current IS NOT NULL is ambiguous |
| status200, error object/empty object/array/string/boolean/number | explicit error value; refuse, do not coerce emptiness/false/zero |
| status404, either null form | status unavailable still refuses independently |

No corrective patch or source-free error probe was executed in this pass.
ROOT took over this diagnosis before any probe script was created. A future
SQL-null/JSON-null E2E and predicate must follow ROOT's separately declared scope;
this document is a proposed failure matrix only. The current source error JSON
content remains unknown. No inference that it is JSON null is accepted here.

Suggested commit: `test: preserve failed capture and expose JSON null error ambiguity`.
