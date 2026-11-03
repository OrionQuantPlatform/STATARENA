import { createHash } from "node:crypto";
import { query, canonical } from "./neon.js";
import { response } from "./files.js";
import { cacheHeaders, matchesEtag } from "./cache-policy.js";
import { serializeJson } from "./metrics.js";

const ID = /^[lm]_[A-Za-z0-9]{6}$/;
const validDay = (s) =>
  /^\d{4}-\d{2}-\d{2}$/.test(s) &&
  Number(s.slice(0, 4)) > 0 &&
  Number.isFinite(Date.parse(s + "T00:00:00Z")) &&
  new Date(s + "T00:00:00Z").toISOString().slice(0, 10) === s;
const FIELD_NAMES = [
  "id",
  "date",
  "time_utc",
  "status",
  "score_home",
  "score_away",
  "season",
  "round_name",
  "has_playoff",
  "score_penalty_home",
  "score_penalty_away",
];
const identity = (key) =>
  `jsonb_build_object('id',body#>'{${key},id}','name',body#>'{${key},name}','image_url',body#>'{${key},image_url}')`;
const FIXTURE_FIELDS = [
  ...FIELD_NAMES.flatMap((key) => [`'${key}'`, `body->'${key}'`]),
  "'home_team'",
  identity("home_team"),
  "'away_team'",
  identity("away_team"),
  "'league'",
  identity("league"),
].join(",");
const json = (value, request, status = 200, headers = {}) =>
  response(request.method === "HEAD" ? null : serializeJson(value), status, {
    "Content-Type": "application/json; charset=utf-8",
    "X-Data-Source": "Neon",
    ...headers,
  });
const error = (request, message, status = 400) =>
  json(
    {
      error: {
        code: status === 409 ? "CURSOR_EXPIRED" : "INVALID_PARAMETER",
        message,
      },
    },
    request,
    status,
  );
const normalizeFixture = (f) => ({
  summaryVersion: 1,
  id: f.id,
  leagueId: f.league?.id,
  league: f.league?.name,
  season: f.season,
  date: f.date,
  timeUtc: f.time_utc,
  status: f.status,
  home: {
    ...f.home_team,
    imageUrl: f.home_team?.image_url,
    score: f.score_home,
  },
  away: {
    ...f.away_team,
    imageUrl: f.away_team?.image_url,
    score: f.score_away,
  },
  coverage: {},
  shots: [],
  stats: [],
  warnings: [],
});

export async function matchSummary(id, request) {
  const conditional =
    request.method === "HEAD" || request.headers.has("if-none-match");
  let row;
  try {
    row = (
      await query(
        `SELECT size,encode(sha256,'hex') AS sha256${conditional ? "" : ",body"} FROM statarena.match_summaries s WHERE match_id=$1 AND NOT EXISTS(SELECT 1 FROM statarena.dirty_match_summaries d WHERE d.match_id=s.match_id)`,
        [id],
      )
    )[0];
  } catch (e) {
    if (e.code !== "42P01") throw e;
  }
  if (row) {
    const headers = {
      ...cacheHeaders(60, 30),
      "Content-Type": "application/json; charset=utf-8",
      "X-Data-Source": "Neon",
      ETag: `"${row.sha256}"`,
    };
    if (matchesEtag(request.headers.get("if-none-match"), headers.ETag))
      return response(null, 304, headers);
    if (request.method === "HEAD")
      return response(null, 200, {
        ...headers,
        "Content-Length": String(row.size),
      });
    if (!row.body)
      row = (
        await query(
          "SELECT body,size,encode(sha256,'hex') AS sha256 FROM statarena.match_summaries s WHERE match_id=$1 AND sha256=decode($2,'hex') AND NOT EXISTS(SELECT 1 FROM statarena.dirty_match_summaries d WHERE d.match_id=s.match_id)",
          [id, row.sha256],
        )
      )[0];
    if (row?.body) {
      if (
        row.body.length !== Number(row.size) ||
        createHash("sha256").update(row.body).digest("hex") !== row.sha256
      )
        throw new Error("Summary integrity failure");
      return response(row.body, 200, {
        ...headers,
        "Content-Length": String(row.size),
      });
    }
  }
  const wildcard = request.headers.get("if-none-match")?.trim() === "*";
  const existenceOnly = request.method === "HEAD" || wildcard;
  const fixture = (
    await query(
      `SELECT ${existenceOnly ? "1 AS present" : `jsonb_build_object(${FIXTURE_FIELDS}) AS body`} FROM statarena.fixtures WHERE id=$1`,
      [id],
    )
  )[0];
  if (fixture && existenceOnly)
    return response(null, wildcard ? 304 : 200, {
      "Content-Type": "application/json; charset=utf-8",
      "X-Data-Source": "Neon",
    });
  return fixture
    ? json(
        {
          data: {
            version: 1,
            state: "pending",
            match: normalizeFixture(fixture.body),
          },
        },
        request,
      )
    : json(
        {
          error: { code: "RESOURCE_NOT_FOUND", message: "Match introuvable." },
        },
        request,
        404,
      );
}

export async function fixturePage(request) {
  const url = new URL(request.url),
    params = url.searchParams;
  const allowed = new Set([
    "league",
    "leagues",
    "season",
    "seasons",
    "status",
    "from",
    "to",
    "q",
    "limit",
    "cursor",
  ]);
  if (
    [...params].length > allowed.size ||
    new Set(params.keys()).size !== [...params].length ||
    [...params].some(([k, v]) => !allowed.has(k) || v.length > 4096)
  )
    return error(request, "Paramètres invalides.");
  const limit = Number(params.get("limit") || 50),
    status = params.get("status") || "all";
  if (
    !Number.isInteger(limit) ||
    limit < 1 ||
    limit > 100 ||
    !["all", "played", "upcoming"].includes(status)
  )
    return error(request, "Limite ou statut invalide.");
  const leagues = (params.get("leagues") || params.get("league") || "")
    .split(",")
    .filter(Boolean)
    .sort();
  const seasons = (params.get("seasons") || params.get("season") || "")
    .split(",")
    .filter(Boolean)
    .sort();
  if (
    (params.has("league") && params.has("leagues")) ||
    (params.has("season") && params.has("seasons")) ||
    leagues.length > 100 ||
    leagues.some((l) => !ID.test(l) || !l.startsWith("l_")) ||
    seasons.length > 2 ||
    seasons.some((s) => !/^\d{4}(?:\/\d{4})?$/.test(s))
  )
    return error(request, "Compétition ou saison invalide.");
  const from = params.get("from"),
    to = params.get("to"),
    q = params.get("q") || "";
  if (
    (from && !validDay(from)) ||
    (to && !validDay(to)) ||
    (from && to && from > to) ||
    q.length > 200
  )
    return error(request, "Date ou recherche invalide.");
  const scope = createHash("sha256")
    .update(canonical({ leagues, seasons, status, from, to, q, limit }))
    .digest("hex");
  let cursor;
  try {
    if (params.has("cursor")) {
      const encoded = params.get("cursor");
      if (!/^[A-Za-z0-9_-]{1,1024}$/.test(encoded)) throw Error();
      cursor = JSON.parse(Buffer.from(encoded, "base64url").toString("utf8"));
      if (
        cursor.v !== 1 ||
        cursor.scope !== scope ||
        !/^\d{1,20}$/.test(cursor.generation) ||
        !/^m_[A-Za-z0-9]{6}$/.test(cursor.id) ||
        (cursor.day !== null && !validDay(cursor.day))
      )
        throw Error();
    }
  } catch {
    return error(request, "Curseur invalide pour ces filtres.");
  }
  const values = [],
    where = [];
  const bind = (value) => {
    values.push(value);
    return `$${values.length}`;
  };
  if (leagues.length) where.push(`league_id=ANY(${bind(leagues)}::text[])`);
  if (seasons.length) where.push(`season=ANY(${bind(seasons)}::text[])`);
  if (status !== "all")
    where.push(
      `status=${bind(status === "played" ? "finished" : "not_started")}`,
    );
  if (from) where.push(`day>=${bind(from)}::date`);
  if (to) where.push(`day<=${bind(to)}::date`);
  if (q)
    where.push(
      `regexp_replace(normalize(lower(concat_ws(' ',body#>>'{home_team,name}',body#>>'{away_team,name}',body#>>'{league,name}')),NFD),'[̀-ͯ]','','g') LIKE ${bind(
        "%" +
          q
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .replace(/[\\%_]/g, "\\$&") +
          "%",
      )}`,
    );
  if (cursor) {
    const id = bind(cursor.id);
    if (cursor.day === null) where.push(`day IS NULL AND id>${id}`);
    else {
      const date = bind(cursor.day);
      where.push(
        `(day>${date}::date OR (day=${date}::date AND id>${id}) OR day IS NULL)`,
      );
    }
  }
  const fields = FIXTURE_FIELDS;
  const row = (
    await query(
      `SELECT jsonb_build_object('generation',generation::text,'rows',(SELECT COALESCE(jsonb_agg(jsonb_build_object('day',day::text,'id',id,'fixture',fixture) ORDER BY day NULLS LAST,id),'[]'::jsonb) FROM(SELECT day,id,jsonb_build_object(${fields}) AS fixture FROM statarena.fixtures ${where.length ? "WHERE " + where.join(" AND ") : ""} ORDER BY day NULLS LAST,id LIMIT ${bind(limit + 1)}) page)) AS body FROM statarena.fixture_generation WHERE singleton`,
      values,
    )
  )[0];
  if (!row) throw new Error("Fixture generation unavailable");
  const page = row.body;
  if (cursor && cursor.generation !== page.generation)
    return error(
      request,
      "Les matchs ont été actualisés. Rechargez la première page.",
      409,
    );
  const selected = page.rows.slice(0, limit),
    last = selected.at(-1);
  const next =
    page.rows.length > limit
      ? Buffer.from(
          JSON.stringify({
            v: 1,
            scope,
            generation: page.generation,
            day: last.day,
            id: last.id,
          }),
        ).toString("base64url")
      : null;
  const payload = {
    data: { matches: selected.map((r) => r.fixture) },
    pagination: { limit, nextCursor: next, generation: page.generation },
  };
  const text = serializeJson(payload);
  if (Buffer.byteLength(text) > 2 * 1024 * 1024)
    return error(request, "Page trop volumineuse. Réduisez la limite.", 413);
  // Generation-bound pages must restart at the origin, not a stale CDN first page.
  return response(request.method === "HEAD" ? null : text, 200, {
    "Content-Type": "application/json; charset=utf-8",
    "X-Data-Source": "Neon",
  });
}
