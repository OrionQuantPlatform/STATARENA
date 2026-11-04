import assert from "node:assert/strict";
import { createHash } from "node:crypto";

if (process.env.STATARENA_SQL_ONLY !== "1" || !process.env.NEON_DATABASE_URL)
  throw new Error("Explicit SQL-only RDS test configuration is required");
const { dataJson } =
  await import("../dashboard/backend/services/data-store.js");
const { objectMeta, objectBody } =
  await import("../dashboard/backend/services/neon.js");
const manifest = await dataJson("computed/dashboard/index.json");
assert.ok(Array.isArray(manifest.seasons));
const path = process.env.STATARENA_SQL_TEST_IMAGE;
assert.ok(path?.startsWith("raw/neon/assets/"));
const meta = await objectMeta(path);
const body = await objectBody(meta);
assert.equal(body.length, Number(meta.size));
assert.equal(createHash("sha256").update(body).digest("hex"), meta.sha256);
console.log(
  JSON.stringify({
    status: "passed",
    jsonFromSQL: true,
    imageFromSQL: true,
    s3Configured: Boolean(process.env.NEON_STORAGE_ENDPOINT),
  }),
);
