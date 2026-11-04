import { gunzipSync } from "node:zlib";
import { objectMeta, objectBody, cache, query, sqlOnly } from "./neon.js";
import { record, timeSync } from "./metrics.js";
const parsed = cache(64 * 1024 * 1024, { name: "parsed" });
export async function dataJson(path) {
  for (let attempt = 0; attempt < 2; attempt++) {
    const meta = await objectMeta(path, { fresh: attempt > 0 });
    if (!meta) {
      const e = new Error("Neon data not found");
      e.code = "ENOENT";
      throw e;
    }
    try {
      return await parsed(
        meta.sha256,
        async () => {
          if (sqlOnly() && /\.json(?:\.gz)?$/i.test(path)) {
            const [row] = await query(
              `SELECT d.document FROM statarena.current_file_documents d
                 JOIN statarena.objects o ON o.path=d.source_path AND o.sha256=decode($2,'hex')
                WHERE d.source_path=$1 AND d.document_path=$1 AND d.format='json'`,
              [path, meta.sha256],
            );
            if (row) return row.document;
          }
          const body = await objectBody(meta);
          let decoded = body;
          if (path.endsWith(".gz")) {
            decoded = timeSync("gzip_ms", () =>
              gunzipSync(body, { maxOutputLength: 128 * 1024 * 1024 }),
            );
            record("gzip_bytes", decoded.length);
          }
          record("parse_bytes", decoded.length);
          return timeSync("parse_ms", () =>
            JSON.parse(decoded.toString("utf8")),
          );
        },
        15 * 60 * 1000,
      );
    } catch (error) {
      if (error.code !== "ESTALE" || attempt === 1) throw error;
    }
  }
}
