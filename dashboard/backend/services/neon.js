import pg from "pg";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { createHash } from "node:crypto";
let pool, storage;
export const configured = () =>
  Boolean(process.env.NEON_DATABASE_URL && process.env.NEON_STORAGE_ENDPOINT);
export function database() {
  if (!process.env.NEON_DATABASE_URL) throw new Error("Neon is not configured");
  const url = new URL(process.env.NEON_DATABASE_URL);
  url.searchParams.set("sslmode", "verify-full");
  if (pool) return pool;
  pool = new pg.Pool({
    connectionString: url.href,
    max: 3,
    allowExitOnIdle: true,
    connectionTimeoutMillis: 10000,
    idleTimeoutMillis: 10000,
    maxLifetimeSeconds: 300,
    application_name: "statarena-runtime",
    query_timeout: 15000,
  });
  pool.on("error", (e) => console.error("Neon idle connection error", e.code));
  return pool;
}
export async function query(sql, values = []) {
  return (await database().query(sql, values)).rows;
}
export const canonical = (params = {}) =>
  JSON.stringify(
    Object.fromEntries(
      Object.entries(params).sort(([a], [b]) => a.localeCompare(b)),
    ),
  );
// Byte-bounded LRU with coalescing; failed loads are never retained.
export function cache(limit) {
  const entries = new Map(),
    pending = new Map();
  let bytes = 0;
  return async function load(key, loader, ttl = 30000) {
    const old = entries.get(key);
    if (old && old.until > Date.now()) {
      entries.delete(key);
      entries.set(key, old);
      return old.value;
    }
    if (old) {
      bytes -= old.size;
      entries.delete(key);
    }
    if (pending.has(key)) return pending.get(key);
    const promise = (async () => {
      const value = await loader();
      const size = Buffer.isBuffer(value)
        ? value.length
        : value?.body
          ? value.body.length + 512
          : Buffer.byteLength(JSON.stringify(value));
      while (entries.size && bytes + size > limit) {
        const first = entries.keys().next().value;
        bytes -= entries.get(first).size;
        entries.delete(first);
      }
      if (size <= limit) {
        entries.set(key, { value, size, until: Date.now() + ttl });
        bytes += size;
      }
      return value;
    })();
    pending.set(key, promise);
    try {
      return await promise;
    } finally {
      pending.delete(key);
    }
  };
}
// Coalesce concurrent reads without retaining file contents between requests.
const metadata = cache(0),
  bodies = cache(0);
export async function objectMeta(path) {
  if (
    !/^(raw|computed|sources)\/[A-Za-z0-9_./-]+$/.test(path) ||
    path.split("/").some((p) => p.startsWith("."))
  )
    throw new Error("Invalid data path");
  return metadata(
    path,
    async () =>
      (
        await query(
          "SELECT path,size,encode(sha256,'hex') AS sha256,etag,content_type FROM statarena.objects WHERE path=$1",
          [path],
        )
      )[0] || null,
  );
}
export async function objectBody(meta) {
  return bodies(
    meta.sha256,
    async () => {
      storage ||= new S3Client({
        endpoint: process.env.NEON_STORAGE_ENDPOINT,
        region: process.env.NEON_STORAGE_REGION || "us-east-2",
        forcePathStyle: true,
        credentials: {
          accessKeyId: process.env.NEON_STORAGE_ACCESS_KEY_ID,
          secretAccessKey: process.env.NEON_STORAGE_SECRET_ACCESS_KEY,
        },
        requestChecksumCalculation: "WHEN_REQUIRED",
        responseChecksumValidation: "WHEN_REQUIRED",
        maxAttempts: 3,
      });
      const read = async (path) => {
        const result = await storage.send(
          new GetObjectCommand({
            Bucket: process.env.NEON_STORAGE_BUCKET || "statarena-data",
            Key: "data/" + path,
          }),
          { abortSignal: AbortSignal.timeout(20000) },
        );
        return Buffer.from(await result.Body.transformToByteArray());
      };
      const matches = (body) =>
        body.length === Number(meta.size) &&
        createHash("sha256").update(body).digest("hex") === meta.sha256;
      const mutable =
        meta.path === "raw/index.json" ||
        meta.path === "computed/dashboard/index.json" ||
        meta.path.startsWith("computed/matchdays/");
      const extension = meta.path.endsWith(".gz") ? ".json.gz" : ".json";
      const previous = () =>
        read("raw/neon/versions/" + meta.sha256 + extension);
      let body;
      try {
        body = await read(meta.path);
      } catch (error) {
        if (!mutable || !["NoSuchKey", "NotFound"].includes(error.name))
          throw error;
        body = await previous();
      }
      // Mutable manifests are versioned before replacement. A reader can see
      // the new object before its metadata transaction commits; use the exact
      // previously published bytes until that transaction becomes visible.
      if (!matches(body) && mutable) body = await previous();
      if (!matches(body))
        throw new Error("Neon object integrity failure");
      return body;
    },
    0,
  );
}
