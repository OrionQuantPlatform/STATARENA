# Browser replay

This workflow uses a production Next build with the existing read-only runtime environment. It intercepts only synthetic match `m_QA0001`; other bootstrap requests use Neon. No data is written to production. Required local paths and the browser executable are recorded explicitly; change them for another workstation.

From `/tmp/statarena-backend-p1-20261103`, build with `bun --cwd dashboard run build`. In a terminal from `dashboard/`, start the tested service:

```sh
ORION_EMBEDDED_API=1 STATARENA_METRICS_SAMPLE_RATE=1 NEXT_TELEMETRY_DISABLED=1 bun --env-file='/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking/dashboard/.env' --eval 'const server=Bun.spawn(["node","node_modules/next/dist/bin/next","start","frontend","--hostname","127.0.0.1","--port","3155"],{env:process.env,stdout:"inherit",stderr:"inherit"});for(const signal of ["SIGINT","SIGTERM"])process.on(signal,()=>server.kill("SIGTERM"));await server.exited;'
```

The environment file is not included. In another terminal, from the worktree root:

```sh
mkdir -p output/playwright/backend-p1-20261103
/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh -s=statarena-p1 open http://127.0.0.1:3155 --config=docs/verification/backend-p1-20261103/browser/browser.config.json
/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh -s=statarena-p1 run-code --filename=docs/verification/backend-p1-20261103/browser/workflow.js
/Users/lemonnierhugo/.codex/skills/playwright/scripts/playwright_cli.sh -s=statarena-p1 close
```

Expected: eleven successful assertions, four match requests (summary, shots, events, heatmaps), no aggregate archive/advanced-network request, no application exception or horizontal overflow. Four screenshots are written to the explicit output path in `workflow.js`. The recorded run's report is `results.json`; its CLI output is `browser-final.log`. Local Vercel Analytics script404s are visible in the service/browser output and are not counted as application exceptions. Stop the service started above with Ctrl-C; unrelated servers remain active.
