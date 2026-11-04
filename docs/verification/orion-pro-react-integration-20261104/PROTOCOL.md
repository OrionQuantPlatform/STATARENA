# React integration acceptance

Suggested commit: `feat: integrate frozen SQL match pages in React`.

The real-browser failure matrix precedes implementation in `../orion-pro-ui-20261104/PROTOCOL.md`. The initial application RED is `../orion-pro-ui-20261104/runs/20261104T210742109610Z-pre-react-application-red/result.json`: Next and manifest HTTP200, then the legacy partition HTTP503 and zero visible matches. Browser acceptance and its original failures remain in that separate harness directory.

This integration additionally requires a production Next build from the executed source bytes in an owned disposable directory. The build must include the unchanged legacy bridge and the new Pro-only route branch, without credentials or a deployment. Expected: exit0, no source drift, temporary directory removed. Record command, source/input hashes, package versions, logs and cleanup. A successful build is compilation evidence only; it cannot certify UI behavior, source completeness, hosted runtime or latency gains.

The first UI scope is one published edition at a time:30-row cursor pages, light summary, explicit shots. Multiple editions with an all-competition filter require a competition selection; global immutable pagination, other typed pages and all-site parity remain open. The Pro flag stays off in production. The legacy manifest retains its existing season-loading branch.

No archive/provider fallback is allowed when the manifest is Pro. Data-bearing Pro React hooks retain only their mounted state and use the client's bounded cache, rather than duplicating response bodies in the legacy global resource cache. Mutable manifest refresh is explicit; old `v` resolves a pinned manifest, and every match request/link identifies its representation. Unknown team labels display an unknown state without modifying the NULL API value.
