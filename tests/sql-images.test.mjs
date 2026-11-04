import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createSqlImageReader } from "../dashboard/backend/services/sql-images.js";

const hash = (value) => createHash("sha256").update(value).digest();
const data = Buffer.from("example image bytes");
const sha = hash(data).toString("hex");
const path = `raw/neon/assets/${sha}.webp`;

function reader({ body = data, chunks = null, digest = sha } = {}) {
  let calls = 0;
  const query = async (sql) => {
    calls++;
    if (sql.includes("FROM statarena.file_payloads p"))
      return [
        {
          size: String(data.length),
          sha256: digest,
          content_type: "image/webp",
          chunk_count: chunks?.length || 0,
          inline: !chunks,
        },
      ];
    if (sql.startsWith("SELECT body")) return [{ body }];
    if (sql.startsWith("SELECT chunk_index")) return chunks;
    throw new Error("Unexpected SQL");
  };
  return { read: createSqlImageReader(query), calls: () => calls };
}

test("returns the exact image from PostgreSQL with immutable cache headers", async () => {
  const { read } = reader();
  const response = await read(
    new Request("https://example.test/data/asset"),
    path,
  );
  assert.equal(response.status, 200);
  assert.deepEqual(Buffer.from(await response.arrayBuffer()), data);
  assert.equal(response.headers.get("content-type"), "image/webp");
  assert.equal(response.headers.get("etag"), `"${sha}"`);
  assert.match(response.headers.get("cache-control"), /immutable/);
});

test("HEAD and conditional GET avoid loading the file body", async () => {
  const { read, calls } = reader();
  assert.equal(
    (
      await read(
        new Request("https://example.test/data/a", { method: "HEAD" }),
        path,
      )
    ).status,
    200,
  );
  assert.equal(
    (
      await read(
        new Request("https://example.test/data/a", {
          headers: { "if-none-match": `"${sha}"` },
        }),
        path,
      )
    ).status,
    304,
  );
  assert.equal(calls(), 2);
});

test("checks chunk order, chunk hashes and full-file hash", async () => {
  const chunks = [data.subarray(0, 5), data.subarray(5)].map(
    (body, chunk_index) => ({ chunk_index, body, sha256: hash(body) }),
  );
  const ok = reader({ chunks });
  assert.deepEqual(
    Buffer.from(
      await (
        await ok.read(new Request("https://example.test/data/a"), path)
      ).arrayBuffer(),
    ),
    data,
  );
  const corrupt = reader({
    chunks: [{ ...chunks[0], body: Buffer.from("wrong") }, chunks[1]],
  });
  await assert.rejects(
    corrupt.read(new Request("https://example.test/data/a"), path),
    /incomplet/,
  );
  await assert.rejects(
    reader({ body: Buffer.from("wrong") }).read(
      new Request("https://example.test/data/a"),
      path,
    ),
    /incohérent/,
  );
});

test("rejects non-image paths and a digest inconsistent with the filename", async () => {
  await assert.rejects(
    reader().read(
      new Request("https://example.test/data/a"),
      "raw/private.json",
    ),
    (error) => error.status === 404,
  );
  await assert.rejects(
    reader({ digest: "a".repeat(64) }).read(
      new Request("https://example.test/data/a"),
      path,
    ),
    /incohérent/,
  );
});
