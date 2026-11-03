import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createServer } from "node:http";

const dbUrl = new URL(process.env.NEON_DATABASE_URL);
assert.ok(["127.0.0.1", "localhost", "::1"].includes(dbUrl.hostname));
assert.equal(dbUrl.pathname, "/statarena_managed_test");
const files = new Map();
let requests = 0;
const server = createServer((req, res) => {
  requests++;
  const key = decodeURIComponent(new URL(req.url, "http://local").pathname);
  const value = files.get(key);
  if (!value) {
    res.writeHead(404, { "Content-Type": "application/xml" });
    res.end("<Error><Code>NoSuchKey</Code></Error>");
  } else {
    res.writeHead(200, { "Content-Length": value.length });
    res.end(value);
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
process.env.NEON_STORAGE_ENDPOINT = `http://127.0.0.1:${server.address().port}`;
process.env.NEON_STORAGE_BUCKET = "bucket";
process.env.NEON_STORAGE_REGION = "auto";
process.env.NEON_STORAGE_ACCESS_KEY_ID = "test";
process.env.NEON_STORAGE_SECRET_ACCESS_KEY = "test";
process.env.STATARENA_DATABASE_SSLMODE = "disable";
process.env.STATARENA_EXTERNAL_STORAGE = "1";
process.env.STATARENA_DIRECT_DOWNLOADS = "1";
const { database } = await import("../dashboard/backend/services/neon.js");
const { publicFile } = await import("../dashboard/backend/services/files.js");
const db = database();
const hash = (body) => createHash("sha256").update(body).digest();
const request = (headers = {}, method = "GET") =>
  new Request("http://localhost/data/example", { headers, method });
async function add(path, body) {
  files.set("/bucket/data/" + path, body);
  await db.query(
    "INSERT INTO statarena.objects(path,size,sha256,etag,content_type,body) VALUES($1,$2,$3,$4,$5,$6)",
    [
      path,
      body.length,
      hash(body),
      "etag",
      "application/json",
      Buffer.from("stale SQL body"),
    ],
  );
}
try {
  await db.query("CREATE SCHEMA statarena");
  await db.query(
    "CREATE TABLE statarena.objects(path text primary key,size bigint,sha256 bytea,etag text,content_type text,body bytea)",
  );
  const body = Buffer.from("direct file");
  const immutable = "raw/neon/assets/" + "a".repeat(64) + ".png";
  await add(immutable, body);
  const redirect = await publicFile(immutable, request());
  assert.equal(redirect.status, 307);
  assert.equal(requests, 0, "Signing must not fetch the object through Vercel");
  const url = new URL(redirect.headers.get("location"));
  assert.equal(url.searchParams.get("X-Amz-Expires"), "300");
  assert.ok(url.searchParams.get("X-Amz-Signature"));
  assert.deepEqual(Buffer.from(await (await fetch(url)).arrayBuffer()), body);
  const head = await publicFile(immutable, request({}, "HEAD"));
  assert.equal(head.status, 200);
  assert.equal(
    (
      await publicFile(
        immutable,
        request({ "If-None-Match": head.headers.get("etag") }),
      )
    ).status,
    304,
  );

  const previous = Buffer.from('{"version":1}');
  await add("raw/index.json", previous);
  files.set("/bucket/data/raw/index.json", Buffer.from('{"version":2}'));
  files.set(
    "/bucket/data/raw/neon/versions/" +
      hash(previous).toString("hex") +
      ".json",
    previous,
  );
  const manifest = await publicFile("raw/index.json", request());
  assert.equal(manifest.status, 200);
  assert.deepEqual(Buffer.from(await manifest.arrayBuffer()), previous);
  assert.equal((await publicFile("raw/../secret.json", request())).status, 403);
  console.log(
    JSON.stringify({
      status: "passed",
      checks: [
        "direct_signed_download",
        "head",
        "etag",
        "committed_manifest",
        "invalid_path",
      ],
    }),
  );
} finally {
  await db.end();
  await new Promise((resolve) => server.close(resolve));
}
