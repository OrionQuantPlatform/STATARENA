import test from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { packageSource } from "../dashboard/scripts/prepare-vercel-source.mjs";

test("source package pins its data revision and excludes secrets and bulk data", async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), "statarena-vercel-package-"));
  const root = path.join(directory, "repo");
  const output = path.join(directory, "package");
  const tracked = ["dashboard/frontend/package.json", "dashboard/frontend/.env.local", "dashboard/shared/data-revision.js", "data/computed/dashboard/index.json", "data/raw/bulk.json"];
  try {
    for (const file of tracked) {
      const full = path.join(root, ...file.split("/"));
      await mkdir(path.dirname(full), { recursive: true });
      await writeFile(full, file.includes(".env") ? "SECRET=must-not-be-uploaded\n" : "{}\n");
    }
    const revision = "a".repeat(40);
    const result = await packageSource({ root, destination: output, revision, tracked });
    assert.equal(result.revision, revision);
    assert.match(await readFile(path.join(output, "dashboard/shared/data-revision.js"), "utf8"), new RegExp(revision));
    await assert.rejects(readFile(path.join(output, "dashboard/frontend/.env.local")), { code: "ENOENT" });
    await assert.rejects(readFile(path.join(output, "data/raw/bulk.json")), { code: "ENOENT" });
    await assert.rejects(packageSource({ root, destination: path.join(directory, "invalid"), revision: "main", tracked }), /Invalid Git revision/);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
