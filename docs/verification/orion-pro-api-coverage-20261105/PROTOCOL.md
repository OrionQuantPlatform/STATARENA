# Pro API coverage and publisher review — documentation only

Suggested commit: `docs: map Pro API coverage and define publication rollout`.

Scope: read canonical local code/model/docs only; write this new directory only. No implementation, test execution, SQL execution or new SQL, source-body/provider/object/Neon/AWS reads, DB/service, model/migration/normalizer/frontend changes, commits or deployment. The107-table proposal remains **PENDING user approval**; its tables/columns cannot be assumed available. Baseline is the approved103-table document, SHA256 `18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08` (94 active +9 deferred), with existing012/013. Table definitions do not prove that source data, publishers or readers are populated/accepted.

Subsequent ROOT authorization extends this initial read-only phase **only** to the closed ProON fallback guard: local pre-code E2E, new tests/orion_pro_route_guard_local.py and helpers/evidence here, minimal aws-app.js guard and ProON-only asset MIME/cache check if its counterexample is confirmed. No orion-pro.js/frozen V1, existing fixtures, model, migrations, normalizer, frontend, CI, WORKLOG, Git or cloud change is included. GUARD_E2E_PROTOCOL.md precedes the new harness and product change. Publisher and coverage expansion remain proposals.

Priority order for this review:

1. Exact existing API/client/screen matrix and a closed ProON route policy. The current subclass override does not stop direct helper calls from reaching historical relational routes.
2. A pre-code E2E failure matrix for that future policy, preserving old V1 bodies/ETags and metadata-only HEAD/304; no E2E is executed in this documentation lot.
3. A bounded production-publisher design using existing103-table destinations and guards: edition builds, distinct dataset/catalogue generations, exact dependency closure, summary/aggregate contracts, coherent atomic publication pointers and unchanged independent C.
4. Ordered route lots outside the pending107 native-detail amendment, with explicit parity blockers rather than partial native DTO claims.

The coverage inventory concerns the canonical Next transport and AWS relational router selected by the deployed app configuration, plus the frontend call sites. Historical `legacy-app.js` and `legacy-compat.js` remain a distinct transport branch, not evidence of Pro coverage. No hosted configuration or live endpoint is inspected. No untracked numbered source copies are read/exported.

Expected review outputs: PRO_ON_ROUTE_POLICY.md, API_ROUTE_MATRIX.json/.md, CLIENT_SCREEN_MATRIX.md, PUBLISHER_PLAN.md, IMPLEMENTATION_ORDER.md and a source/checksum inventory. Source paths/line references identify code at this read-only snapshot. Nothing in this folder claims a new route, publisher, test result or activation.
