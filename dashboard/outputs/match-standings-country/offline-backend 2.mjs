// E2E setup: real local data, with the external provider deliberately offline.
// Run from dashboard with: bun outputs/match-standings-country/offline-backend.mjs
import { handleRequest } from "../../backend/app.js";

const server = Bun.serve({
  hostname: "127.0.0.1",
  port: 8777,
  fetch(request) {
    const pathname = new URL(request.url).pathname;
    if (pathname === "/api/status")
      return Response.json({ ok: true, configured: false });
    if (pathname.startsWith("/api/pitchapi/"))
      return Response.json({ error: { message: "Provider offline for E2E" } }, { status: 503 });
    return handleRequest(request);
  },
});
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => { server.stop(true); process.exit(0); });
console.log("Offline E2E backend: http://127.0.0.1:8777");
