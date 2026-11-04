import { createHash } from "node:crypto";
import { cacheHeaders, matchesEtag } from "./cache-policy.js";

const imagePath = /^raw\/neon\/assets\/([a-f0-9]{64})\.(?:webp|png|jpe?g)$/;
const maxImageBytes = 4 * 1024 * 1024;
const unavailable = (message, status = 503) =>
  Object.assign(new Error(message), { status });

// The injected query function keeps the SQL reader testable without a live bucket.
export function createSqlImageReader(query) {
  return async (request, path) => {
    const match = imagePath.exec(path);
    if (!match) throw unavailable("Fichier indisponible.", 404);
    const [meta] = await query(
      `SELECT p.size,encode(p.sha256,'hex') AS sha256,p.content_type,p.chunk_count,
              p.body IS NOT NULL AS inline
         FROM statarena.file_payloads p
         JOIN statarena.objects o ON o.path=p.path AND o.sha256=p.sha256 AND o.size=p.size
        WHERE p.namespace='data' AND p.path=$1`,
      [path],
    );
    if (!meta) throw unavailable("Fichier indisponible.", 404);
    if (meta.sha256 !== match[1]) throw unavailable("Fichier incohérent.");
    const size = Number(meta.size),
      etag = '"' + meta.sha256 + '"';
    if (!Number.isSafeInteger(size) || size < 0 || size > maxImageBytes)
      throw unavailable("Taille de fichier invalide.");
    const headers = {
      "Content-Type": meta.content_type,
      "Content-Length": String(size),
      "X-Content-Type-Options": "nosniff",
      "X-Data-Source": "AWS",
      ETag: etag,
      ...cacheHeaders(60, 0, { immutable: true }),
    };
    if (matchesEtag(request.headers.get("if-none-match"), etag))
      return new Response(null, { status: 304, headers });
    if (request.method === "HEAD")
      return new Response(null, { status: 200, headers });

    let body;
    if (meta.inline) {
      const [row] = await query(
        "SELECT body FROM statarena.file_payloads WHERE namespace='data' AND path=$1 AND sha256=decode($2,'hex')",
        [path, meta.sha256],
      );
      if (!Buffer.isBuffer(row?.body)) throw unavailable("Fichier incomplet.");
      body = row.body;
    } else {
      const chunks = await query(
        "SELECT chunk_index,body,sha256 FROM statarena.file_payload_chunks WHERE namespace='data' AND path=$1 ORDER BY chunk_index",
        [path],
      );
      if (
        chunks.length !== Number(meta.chunk_count) ||
        chunks.some(
          (row, i) =>
            row.chunk_index !== i ||
            !Buffer.isBuffer(row.body) ||
            !Buffer.isBuffer(row.sha256) ||
            !createHash("sha256").update(row.body).digest().equals(row.sha256),
        )
      )
        throw unavailable("Fichier incomplet.");
      body = Buffer.concat(chunks.map((row) => row.body));
    }
    if (
      body.length !== size ||
      createHash("sha256").update(body).digest("hex") !== meta.sha256
    )
      throw unavailable("Fichier incohérent.");
    return new Response(body, { status: 200, headers });
  };
}
