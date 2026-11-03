import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createServer } from "node:http";

const files = new Map();
const requests = [];
const server = createServer((request, response) => {
  const path = decodeURIComponent(new URL(request.url, "http://test").pathname);
  requests.push(path);
  const body = files.get(path);
  if (!body) {
    response.writeHead(404);
    response.end();
    return;
  }
  response.writeHead(200, { "Content-Length": body.length });
  response.end(body);
});
let objectBody;
const digest = (body) => createHash("sha256").update(body).digest("hex");
const meta = (path, body) => ({
  path,
  size: body.length,
  sha256: digest(body),
  // A stale inline value must never be used as the source of the response.
  body: Buffer.from("inline value"),
});

before(async () => {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  process.env.NEON_STORAGE_ENDPOINT = `http://127.0.0.1:${server.address().port}`;
  process.env.NEON_STORAGE_BUCKET = "statarena-data";
  process.env.NEON_STORAGE_ACCESS_KEY_ID = "test";
  process.env.NEON_STORAGE_SECRET_ACCESS_KEY = "test";
  ({ objectBody } = await import("../dashboard/backend/services/neon.js"));
});
after(() => new Promise((resolve) => server.close(resolve)));

test("reads the verified file for each sequential request", async () => {
  const body = Buffer.from('{"id":"m_test"}');
  files.set("/statarena-data/data/raw/test.json", body);
  const start = requests.length;
  assert.deepEqual(await objectBody(meta("raw/test.json", body)), body);
  assert.deepEqual(await objectBody(meta("raw/test.json", body)), body);
  assert.equal(requests.length - start, 2);
});

test("rejects a file whose bytes do not match its catalog metadata", async () => {
  const expected = Buffer.from("expected");
  files.set("/statarena-data/data/raw/corrupt.json", Buffer.from("corrupted"));
  await assert.rejects(
    objectBody(meta("raw/corrupt.json", expected)),
    /integrity failure/,
  );
});

test("serves the committed version while a mutable manifest is replaced", async () => {
  const previous = Buffer.from('{"version":1}');
  const next = Buffer.from('{"version":2}');
  files.set("/statarena-data/data/raw/index.json", next);
  files.set(
    `/statarena-data/data/raw/neon/versions/${digest(previous)}.json`,
    previous,
  );
  assert.deepEqual(await objectBody(meta("raw/index.json", previous)), previous);
});

test("rejects a mismatched archived manifest", async () => {
  const previous = Buffer.from('{"version":3}');
  files.set("/statarena-data/data/raw/index.json", Buffer.from('{"version":4}'));
  files.set(
    `/statarena-data/data/raw/neon/versions/${digest(previous)}.json`,
    Buffer.from("invalid archive"),
  );
  await assert.rejects(
    objectBody(meta("raw/index.json", previous)),
    /integrity failure/,
  );
});
