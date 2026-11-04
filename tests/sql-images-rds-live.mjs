import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import pg from "../dashboard/node_modules/pg/lib/index.js";
import { createSqlImageReader } from "../dashboard/backend/services/sql-images.js";
import { adapt } from "../infra/aws-backend/transport.mjs";

if (!process.env.STATARENA_RDS_TEST_URL || !process.env.STATARENA_RDS_TEST_CA)
  throw new Error("Explicit read-only RDS test credentials are required");
const db = new pg.Client({
  connectionString: process.env.STATARENA_RDS_TEST_URL,
  ssl: { ca: process.env.STATARENA_RDS_TEST_CA, rejectUnauthorized: true },
});
await db.connect();
try {
  const query = async (sql, values) => (await db.query(sql, values)).rows;
  const images = await query(
    "SELECT path FROM statarena.file_payloads WHERE namespace='data' AND path LIKE 'raw/neon/assets/%' AND body IS NOT NULL ORDER BY path LIMIT 5",
  );
  assert.equal(images.length, 5);
  const read = createSqlImageReader(query);
  const serve = adapt((req) => read(req, new URL(req.url).pathname.slice(6)));
  for (const { path } of images) {
    const response = await serve({
      version: "2.0",
      rawPath: "/data/" + path,
      rawQueryString: "",
      headers: {},
      requestContext: { http: { method: "GET" } },
    });
    assert.equal(response.statusCode, 200);
    assert.equal(response.isBase64Encoded, true);
    const body = Buffer.from(response.body, "base64");
    assert.equal(
      createHash("sha256").update(body).digest("hex"),
      path.split("/").pop().split(".")[0],
    );
  }
  console.log(
    JSON.stringify({
      status: "passed",
      sqlImages: images.length,
      transport: "lambda-function-url",
    }),
  );
} finally {
  await db.end();
}
