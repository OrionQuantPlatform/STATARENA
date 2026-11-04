import { readFileSync, writeFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { execFileSync } from "node:child_process";
// Read the pre-migration implementation at its immutable source revision.
const old = execFileSync("git", [
  "show",
  "923bb0ff4a:dashboard/frontend/src/services/player-honours.js",
]);
const { MESSI_ID, MESSI_HONOURS, projectionGroups, mergeMessiHonours } =
  await import("data:text/javascript;base64," + old.toString("base64"));
const rows = JSON.parse(
  gunzipSync(
    readFileSync(
      new URL("../aws-support-20261104/projections.json.gz", import.meta.url),
    ),
  ),
);
const [, params, body] = rows.find(
  ([n, p]) => n === "player-honours" && JSON.parse(p).id === MESSI_ID,
);
writeFileSync(
  new URL("curated-before.json", import.meta.url),
  JSON.stringify(
    {
      params,
      sourceGroups: projectionGroups(body.honours),
      expected: mergeMessiHonours(projectionGroups(body.honours)),
      withoutSource: MESSI_HONOURS,
    },
    null,
    2,
  ) + "\n",
);
