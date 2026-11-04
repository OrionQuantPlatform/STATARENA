import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";

const require = createRequire(
  new URL("../dashboard/package.json", import.meta.url),
);
const pg = require("pg");
const originalConnect = pg.Pool.prototype.connect;
const bytes = Buffer.from("sql image body");
const digest = createHash("sha256").update(bytes).digest("hex");
const path = `raw/neon/assets/${digest}.webp`;
process.env.DATABASE_URL =
  "postgresql://reader:test@127.0.0.1/statarena?sslmode=disable";
process.env.STATARENA_TEST_DATABASE = "1";
process.env.STATARENA_DATA_PROVIDER = "aws";
process.env.STATARENA_SQL_ONLY = "1";
pg.Pool.prototype.connect = async () => ({
  async query(sql) {
    if (sql.includes("FROM statarena.file_payloads p"))
      return {
        rows: [
          {
            size: String(bytes.length),
            sha256: digest,
            content_type: "image/webp",
            chunk_count: 0,
            inline: true,
          },
        ],
      };
    if (sql.startsWith("SELECT body")) return { rows: [{ body: bytes }] };
    throw new Error("Unexpected query: " + sql);
  },
  release() {},
});
const { handleRequest } = await import("../dashboard/backend/aws-app.js");
test.after(() => {
  pg.Pool.prototype.connect = originalConnect;
});

test("AWS app serves a verified SQL image and keeps other data paths unavailable", async () => {
  const image = await handleRequest(
    new Request("https://example.test/data/" + path),
  );
  assert.equal(image.status, 200);
  assert.deepEqual(Buffer.from(await image.arrayBuffer()), bytes);
  const denied = await handleRequest(
    new Request("https://example.test/data/raw/private.json"),
  );
  assert.equal(denied.status, 404);
  process.env.STATARENA_SQL_ONLY = "0";
  assert.equal(
    (await handleRequest(new Request("https://example.test/data/" + path)))
      .status,
    410,
  );
});
