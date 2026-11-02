import { readFile } from "node:fs/promises";
import path from "node:path";
import { gunzipSync } from "node:zlib";
import { databaseRoot } from "../config.js";
import { packagedDataRevision } from "../../shared/data-revision.js";

export const remoteData = Boolean(
  process.env.VERCEL || process.env.ORION_REMOTE_DATA === "1",
);
export function remoteDataRevision() {
  const revision = packagedDataRevision || process.env.ORION_DATA_REVISION || process.env.VERCEL_GIT_COMMIT_SHA;
  if (!/^[a-f0-9]{40}$/i.test(revision || ""))
    throw new Error("Missing immutable data revision");
  return revision;
}
export function remoteDataUrl(relative) {
  if (
    !/^(raw|computed)\/[A-Za-z0-9_./-]+$/.test(relative) ||
    relative.split("/").some((p) => p.startsWith("."))
  )
    throw new Error("Invalid data path");
  const revision = remoteDataRevision();
  return `https://raw.githubusercontent.com/OrionQuantPlatform/STATARENA/${revision}/data/${relative}`;
}

// A narrowly scoped Contents token stays in the server process. Only data paths
// validated by remoteDataUrl are ever sent to GitHub, at this deployment's SHA.
export async function fetchRemoteData(relative) {
  const publicUrl = remoteDataUrl(relative);
  const token = process.env.GITHUB_DATA_TOKEN;
  const revision = remoteDataRevision();
  const url = token
    ? `https://api.github.com/repos/OrionQuantPlatform/STATARENA/contents/data/${relative}?ref=${revision}`
    : publicUrl;
  return fetch(url, {
    headers: token ? {
      Accept: "application/vnd.github.raw+json",
      Authorization: `Bearer ${token}`,
      "User-Agent": "STATARENA",
      "X-GitHub-Api-Version": "2022-11-28",
    } : undefined,
    redirect: "error",
    cache: "no-store",
    signal: AbortSignal.timeout(25000),
  });
}

// An optional bounded warm-instance cache; Git is the durable source of truth.
const files = new Map();
let cachedBytes = 0;
export async function dataJson(relative) {
  let body;
  if (!remoteData) body = await readFile(path.join(databaseRoot, relative));
  else {
    if (files.has(relative)) return files.get(relative).value;
    const response = await fetchRemoteData(relative);
    if (!response.ok) throw new Error(`Canonical data HTTP ${response.status}`);
    const chunks = [];
    let bytes = 0;
    for await (const chunk of response.body) {
      bytes += chunk.byteLength;
      if (bytes > 32 * 1024 * 1024)
        throw new Error("Canonical file exceeds read limit");
      chunks.push(chunk);
    }
    body = Buffer.concat(chunks);
  }
  const value = JSON.parse(
    relative.endsWith(".gz")
      ? gunzipSync(body, { maxOutputLength: 128 * 1024 * 1024 }).toString(
          "utf8",
        )
      : body.toString("utf8"),
  );
  if (remoteData) {
    const size = Buffer.byteLength(JSON.stringify(value));
    while (files.size && cachedBytes + size > 64 * 1024 * 1024) {
      const first = files.keys().next().value;
      cachedBytes -= files.get(first).size;
      files.delete(first);
    }
    if (size <= 64 * 1024 * 1024) {
      files.set(relative, { value, size });
      cachedBytes += size;
    }
  }
  return value;
}
