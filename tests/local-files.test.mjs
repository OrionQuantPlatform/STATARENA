import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

let root, objectBody;
const sha = (body) => createHash("sha256").update(body).digest("hex");
const meta = (file, body) => ({
  path: file,
  size: body.length,
  sha256: sha(body),
  body: Buffer.from("outdated SQL copy"),
});

before(async () => {
  root = await mkdtemp(path.join(tmpdir(), "statarena-files-"));
  await mkdir(path.join(root, "data", "raw", "neon", "versions"), { recursive: true });
  process.env.FILE_STORAGE_ROOT = root;
  ({ objectBody } = await import("../dashboard/backend/services/neon.js"));
});
after(async () => rm(root, { recursive: true, force: true }));

test("reads and checks the local file instead of an inline SQL body", async () => {
  const body = Buffer.from('{"fixture":"local"}');
  await writeFile(path.join(root, "data", "raw", "sample.json"), body);
  assert.deepEqual(await objectBody(meta("raw/sample.json", body)), body);
});

test("rejects corrupt local data", async () => {
  const expected = Buffer.from("expected");
  await writeFile(path.join(root, "data", "raw", "corrupt.json"), "wrong");
  await assert.rejects(objectBody(meta("raw/corrupt.json", expected)), /integrity failure/);
});

test("uses the committed version if a manifest replacement is not committed", async () => {
  const previous = Buffer.from('{"version":1}');
  await writeFile(path.join(root, "data", "raw", "index.json"), '{"version":2}');
  await writeFile(path.join(root, "data", "raw", "neon", "versions", sha(previous) + ".json"), previous);
  assert.deepEqual(await objectBody(meta("raw/index.json", previous)), previous);
});
