import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";

const require = createRequire(
  new URL("../dashboard/package.json", import.meta.url),
);
const pg = require("pg");
const { S3Client } = require("@aws-sdk/client-s3");
const originalQuery = pg.Pool.prototype.query;
const originalSend = S3Client.prototype.send;
const jsonPath = "raw/testing/structured.json.gz";
const imagePath = "raw/testing/image.webp";
const image = Buffer.from("sql-only image");
const imageHash = createHash("sha256").update(image).digest("hex");
let s3Calls = 0;

process.env.NEON_DATABASE_URL = "postgresql://reader:test@localhost/statarena";
process.env.STATARENA_SQL_ONLY = "1";
delete process.env.NEON_STORAGE_ENDPOINT;
delete process.env.STATARENA_EXTERNAL_STORAGE;
pg.Pool.prototype.query = async function (sql, values) {
  if (sql.startsWith("SELECT path,size")) {
    if (values[0] === jsonPath)
      return {
        rows: [
          { path: jsonPath, size: 5, sha256: "a".repeat(64), inline: false },
        ],
      };
    if (values[0] === imagePath)
      return {
        rows: [
          {
            path: imagePath,
            size: image.length,
            sha256: imageHash,
            inline: false,
          },
        ],
      };
    return { rows: [] };
  }
  if (sql.includes("FROM statarena.current_file_documents"))
    return { rows: [{ document: { club: "Fenerbahçe" } }] };
  if (sql.startsWith("SELECT body,chunk_count"))
    return { rows: [{ body: image, chunk_count: 0 }] };
  throw new Error("Unexpected SQL: " + sql);
};
S3Client.prototype.send = async () => {
  s3Calls++;
  throw new Error("S3 must not be used");
};
const { dataJson } =
  await import("../dashboard/backend/services/data-store.js");
const { configured, objectMeta, objectBody } =
  await import("../dashboard/backend/services/neon.js");
test.after(() => {
  pg.Pool.prototype.query = originalQuery;
  S3Client.prototype.send = originalSend;
});

test("staging readers use JSONB and exact SQL bytes without S3 configuration", async () => {
  assert.equal(configured(), true);
  assert.deepEqual(await dataJson(jsonPath), { club: "Fenerbahçe" });
  assert.deepEqual(await objectBody(await objectMeta(imagePath)), image);
  assert.equal(s3Calls, 0);
});
