# Main integration and temporary deployment guard

User explicitly requires all future work committed/pushed to main, and stopping the old collector feeding Neon. This merges the existing verified AWS implementation into main without a new branch. The source-transfer owner remains the friend’s Codex.

Production currently serves the old Neon-backed frontend (public health200, sourceNeon, revision18). AWS serving tables are partially populated; the first resumed construction succeeded with four new partitions and405matches. The scoped temporary dashboard/frontend/vercel.json setting `git.deploymentEnabled.main=false` prevents automatic Git deployment on main during full source/API/UI validation and preserves the existing regionscle1 setting. It neither pauses current production nor changes other branches, provider plans or domain aliases. Remove the guard at accepted cutover and configure production NEXT_PUBLIC_API_ORIGIN before the final production build.

Official setting: https://vercel.com/docs/project-configuration/git-configuration . Authenticated project readback: rootDirectorydashboard/frontend, productionBranchmain, autoAssignCustomDomainstrue, pausedfalse, productiondpl_5WKUEwBpNkr3hUEk9Fk8qF8EVFBe at0aaf316e0aa525c90b3787df623bb5bfcc2936c8.

Setup: authenticated GitHub and Vercel CLI65.11.0 for teamteam_IYt7KqupdSTtMuQuMvNa9wiJ; repositoryOrionQuantPlatform/STATARENA. No credentials in receipts. Exact rerun commands:

```sh
gh run view 41784088755 -R OrionQuantPlatform/STATARENA --json databaseId,status,conclusion,headSha,workflowName,jobs
gh workflow list -R OrionQuantPlatform/STATARENA --all --json id,name,path,state
curl -sS --max-time 20 -i https://statarena-analytics.vercel.app/api/health
```

Expected: cancelled collector, disabled legacy scheduled entrypoints, publichealth200 on the pre-cutover backend. Actual cancellation: cancel-complete.json; disabled states: historical-disabled.json and daily-disabled.json; public health: production-before.json. Post-push remote/CI/deployment readbacks will be saved separately. A successful integration is not full AWS production acceptance. The failed local guard-edit attempt detected an existing Vercel regions configuration and stopped before replacing it; the corrected edit merges the guard and retainscle1.

Suggested commit: `feat: integrate AWS backend on main with guarded production rollout`.
