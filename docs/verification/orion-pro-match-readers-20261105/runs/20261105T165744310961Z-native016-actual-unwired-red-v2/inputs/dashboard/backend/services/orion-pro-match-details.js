import { createHash } from "node:crypto";
import { query } from "./postgres.js";
import { send } from "./relational-core.js";
import { cacheHeaders, matchesEtag } from "./cache-policy.js";

const representation = "match-native-v1";
const legacyRepresentation = "summary-v1-shots-v1";
const modelBindings = new Map([
  [
    "orion_pro_publish_native107_v1/orion_pro_native107_v1",
    { model: "f516804f6e2381b5e55763860b6470127b88a567006973afa79c0a9f5f0d9ae3", core: false },
  ],
  [
    "orion_pro_publish_native107_core_v1/orion_pro_native107_core_v1",
    { model: "e06ba703bdebc3f8e7653521837f9e413b7147f4cb810fe1dc40f4668ea5f0e3", core: true },
  ],
]);
const pathPattern =
  /^\/api\/pitchapi\/matches\/(m_[A-Za-z0-9]{6})(?:\/(momentum|events|lineups|h2h|stats))?$/;
const sourcePattern = /^pro1\.([1-9][0-9]{0,18})\.[a-f0-9]{64}$/;
const nativePattern = /^native1\.([1-9][0-9]{0,18})\.[a-f0-9]{64}$/;
const hex = /^[a-f0-9]{64}$/;
const numeric = /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]+)?$/;
const maxBody = 1024 * 1024;
const maxTransferPerProjection = 4 * maxBody;
const limits = { match: 1, momentum: 2000, events: 1000, h2h: 500, lineups: 2, stats: 16 };
const membersLimit = 80;
const groupLimit = 128;
const itemLimit = 1000;
const unrecordedCore = ["referee", "has_playoff", "league.image_url"];
const knownStates = new Set(["absent", "null", "value"]);
const objectStates = new Set(["absent", "null", "object"]);
const digest = (data) => createHash("sha256").update(JSON.stringify(data)).digest("hex");
const at = (a, g) =>
  `${a}.recorded_from_gen<=${g} AND (${a}.recorded_to_gen IS NULL OR ${g}<${a}.recorded_to_gen)`;
const selected = (a, g) => `${at(a, g)} AND ${a}.is_canonical AND NOT ${a}.is_deleted`;

class NativeMatchError extends Error {
  constructor(status, code, message, fields) {
    super(message);
    Object.assign(this, { status, code, fields });
  }
}

function badVersion() {
  throw new NativeMatchError(400, "NATIVE_MATCH_VERSION_INVALID", "Version native du match invalide.");
}

function unavailable() {
  throw new NativeMatchError(503, "NATIVE_MATCH_UNAVAILABLE", "Ce détail natif n’est pas disponible pour cette publication.");
}

function missingCore() {
  throw new NativeMatchError(503, "NATIVE_CORE_FIELDS_UNRECORDED", "Des champs natifs du match ne sont pas enregistrés.", unrecordedCore);
}

function tooLarge() {
  throw new NativeMatchError(413, "PAGE_TOO_LARGE", "Ce détail dépasse la taille maximale de réponse.");
}

function requireFact(condition) {
  if (!condition) unavailable();
}

function one(rows) {
  requireFact(rows.length === 1);
  return rows[0];
}

function tokenId(token, pattern) {
  const match = pattern.exec(token || "");
  return match && BigInt(match[1]) <= 9223372036854775807n ? match[1] : null;
}

function argumentsFor(params) {
  const allowed = new Set(["representation", "v", "nv"]);
  if ([...params].some(([name, value]) => !allowed.has(name) || value.length > 100)
      || new Set(params.keys()).size !== params.size) badVersion();
  const v = params.get("v"), nv = params.get("nv");
  const buildId = tokenId(v, sourcePattern);
  if (params.get("representation") !== representation || !buildId
      || (nv !== null && tokenId(nv, nativePattern) !== buildId)) badVersion();
  return { v, nv, buildId };
}

const buildSql = `/*orion:native-match:build-meta*/
 SELECT b.id::text build_id,b.competition_season_id::text edition_id,
        b.dataset_snapshot_id::text dataset_snapshot_id,d.generation::text dataset_generation,
        b.catalog_snapshot_id::text catalog_snapshot_id,c.generation::text catalog_generation,
        b.representation_version,b.code_content_sha256,b.dependencies_sha256,b.environment_sha256,
        b.metrics_contract_version,b.transform_version
 FROM analytics.aggregation_builds b
 JOIN ingest.dataset_snapshots d ON d.id=b.dataset_snapshot_id AND d.status='sealed'
 JOIN ingest.dataset_snapshots c ON c.id=b.catalog_snapshot_id AND c.status='sealed'
 JOIN football.competition_seasons e ON e.id=b.competition_season_id
   AND e.revision_id=b.competition_season_revision_id AND ${selected("e", "d.generation")}
 WHERE b.id=$1::bigint AND b.status='ready'
   AND EXISTS (SELECT 1 FROM analytics.publication_versions p
     WHERE p.build_id=b.id AND p.competition_season_id=b.competition_season_id
       AND p.catalog_snapshot_id=b.catalog_snapshot_id AND p.representation_version=b.representation_version)
 LIMIT 2`;

function sourceToken(row) {
  return `pro1.${row.build_id}.${digest([
    row.build_id, row.edition_id, row.dataset_snapshot_id, row.dataset_generation,
    row.catalog_snapshot_id, row.catalog_generation, row.representation_version,
    row.code_content_sha256, row.dependencies_sha256, row.environment_sha256,
    row.metrics_contract_version, row.transform_version,
  ])}`;
}

async function publication({ buildId, v, nv }) {
  const rows = await query(buildSql, [buildId]);
  if (rows.length !== 1 || sourceToken(rows[0]) !== v) badVersion();
  const b = rows[0];
  const binding = modelBindings.get(`${b.transform_version}/${b.metrics_contract_version}`);
  if (!binding || b.representation_version !== legacyRepresentation
      || ![b.dependencies_sha256, b.environment_sha256, b.code_content_sha256].every((value) => hex.test(value || ""))) {
    if (nv !== null) badVersion();
    unavailable();
  }
  const native = `native1.${buildId}.${digest([
    "orion-match-native-token-v1", representation, binding.model, v, b.build_id,
    b.dataset_generation, b.catalog_generation, b.dependencies_sha256,
    b.transform_version, b.metrics_contract_version, b.environment_sha256, b.code_content_sha256,
  ])}`;
  if (nv !== null && nv !== native) badVersion();
  return { ...b, binding, v, native };
}

const parentFields = ["match_id", "source_id", "feature_code", "variant_key", "recorded_from_gen"];
const parent = (a) =>
  `(${parentFields.map((key) => `${a}.${key}`).join(",")})=($1::bigint,$2::bigint,$3::text,$4::text,$5::bigint)`;
const lineage = (a, source, document, locator, ordinal = "NULL::int") =>
  `${a}.source_id=${source} AND ${a}.document_id=${document}
    AND ${a}.locator_kind='json_pointer' AND ${a}.locator=${locator}
    AND ${a}.ordinal IS NOT DISTINCT FROM ${ordinal}`;

async function matchMetadata(b, id, feature) {
  const core = feature === "match" && b.binding.core;
  const rows = await query(
    `/*orion:native-match:match-meta*/
 SELECT s.match_id::text,s.home_team_id::text,s.away_team_id::text,
        c.source_id::text,c.feature_code,c.variant_key,c.recorded_from_gen::text,
        c.match_revision_id::text,c.document_id::text,c.source_record_id::text,
        c.contract_version,c.coverage_state,c.collection_state,c.observed_row_count,
        c.source_match_id_state,c.source_home_team_state,c.source_away_team_state,
        c.source_home_team_profile_version_id::text,c.source_away_team_profile_version_id::text
        ${core ? ",o.source_referee_state,o.source_has_playoff_state,o.source_league_image_url_state" : ""}
 FROM analytics.match_summary s
 JOIN football.matches m ON m.id=s.match_id AND m.revision_id=s.match_revision_id
   AND m.competition_season_id=$2::bigint AND m.publication_state='published'
   AND ${selected("m", "$3::bigint")}
 JOIN ingest.public_aliases a ON a.route_kind='match' AND a.match_id=s.match_id
   AND a.public_key=$5::text AND ${at("a", "$4::bigint")} AND NOT a.is_deleted
   AND (a.match_revision_id IS NULL OR EXISTS (
     SELECT 1 FROM football.matches anchor WHERE anchor.revision_id=a.match_revision_id
       AND anchor.id=a.match_id AND anchor.competition_season_id=s.competition_season_id))
 LEFT JOIN LATERAL (SELECT co.* FROM ingest.match_coverage co WHERE co.match_id=s.match_id
   AND co.feature_code=$6::text AND co.is_canonical AND ${at("co", "$3::bigint")} LIMIT 2) c ON true
 ${core ? `LEFT JOIN football.match_observation_details o ON o.source_record_id=c.source_record_id
   AND o.match_id=s.match_id AND o.match_revision_id=c.match_revision_id
   AND o.recorded_from_gen=c.recorded_from_gen` : ""}
 WHERE s.build_id=$1::bigint AND s.competition_season_id=$2::bigint LIMIT 2`,
    [b.build_id, b.edition_id, b.dataset_generation, b.catalog_generation, id, feature],
  );
  if (!rows.length) throw new NativeMatchError(404, "NATIVE_MATCH_NOT_FOUND", "Match introuvable dans cette publication.");
  const c = one(rows);
  if (feature === "match" && (!b.binding.core || [c.source_referee_state, c.source_has_playoff_state,
      c.source_league_image_url_state].some((state) => !knownStates.has(state)))) missingCore();
  requireFact(c.contract_version === representation && c.variant_key === "source:exact"
    && c.document_id !== null && c.source_record_id !== null && c.match_revision_id !== null
    && knownStates.has(c.source_match_id_state)
    && objectStates.has(c.source_home_team_state) && objectStates.has(c.source_away_team_state));
  const count = c.observed_row_count, state = c.collection_state;
  const goodCount = (state === "present" && Number.isInteger(count) && count > 0)
    || (state === "empty" && count === 0)
    || ((state === "null" || state === "absent") && count === null);
  requireFact(goodCount && c.coverage_state === (state === "empty" ? "empty_response" : "available"));
  if (count > limits[feature]) tooLarge();
  if (feature === "lineups" || feature === "match") requireFact(state === "present" && count === limits[feature]);
  return { ...c, b, key: parentFields.map((key) => c[key]) };
}

function exactNumber(value) {
  requireFact(typeof value === "string" && value.length <= 150000 && numeric.test(value));
  return JSON.rawJSON(value);
}

function scalar(out, key, state, value, type) {
  if (state === "absent" || state === "null") {
    requireFact(value === null);
    if (state === "null") out[key] = null;
  } else {
    requireFact(state === "value" && typeof value === type
      && (type !== "number" || Number.isSafeInteger(value)));
    out[key] = value;
  }
}

function numberField(out, key, state, value) {
  if (state === "value") out[key] = exactNumber(value);
  else scalar(out, key, state, value, "string");
}

function field(out, row, key, column, stateColumn, type = "string") {
  scalar(out, key, row[stateColumn], row[column], type);
}

function fields(out, row, definitions) {
  for (const [key, column, state, type] of definitions) field(out, row, key, column, state, type);
  return out;
}

function observedObject(out, key, state, build) {
  requireFact(objectStates.has(state));
  if (state === "null") out[key] = null;
  if (state === "object") out[key] = build();
}

function declaredArray(out, key, state, count, rows, convert) {
  requireFact(rows.length === (count ?? 0));
  if (state === "present" || state === "empty") {
    requireFact(state === "present" ? count > 0 : count === 0);
    out[key] = rows.map(convert);
  } else {
    requireFact((state === "absent" || state === "null") && count === null);
    if (state === "null") out[key] = null;
  }
}

function ordered(rows, slot, convert) {
  return rows.map((row, index) => {
    requireFact(row[slot] === index);
    return convert(row, index);
  });
}

function collection(data, key, c, rows, slot, convert) {
  const items = ordered(rows, slot, convert);
  declaredArray(data, key, c.collection_state, c.observed_row_count, items, (value) => value);
}

function bucket(rows, key) {
  const result = new Map();
  for (const row of rows) {
    if (!result.has(row[key])) result.set(row[key], []);
    result.get(row[key]).push(row);
  }
  return result;
}

// Limit the wire volume of a typed projection before shipping it to the API.
// The SELECTs project approved columns only; no source body or JSON column is
// read. The budget aggregate measures the ephemeral SQL row representation.
async function payload(label, sql, values) {
  const rows = await query(
    `/*orion:native-match:payload:${label}*/
 WITH projected AS MATERIALIZED (${sql}), budget AS (
   SELECT coalesce(sum(octet_length(row_to_json(p)::text)),0)>${maxTransferPerProjection} AS exceeded FROM projected p
 ) SELECT p.*,budget.exceeded FROM budget LEFT JOIN projected p ON NOT budget.exceeded`,
    values,
  );
  if (rows[0]?.exceeded) tooLarge();
  return rows.filter((row) => row.witness !== null);
}

function bounded(rows, limit) {
  if (rows.length > limit) tooLarge();
  return rows;
}

const profileColumns = (a, prefix, player = false) => `
 ${a}.id::text AS ${prefix}_profile,${a}.external_key AS ${prefix}_external_key,
 ${a}.source_external_id_state AS ${prefix}_id_state,${a}.display_name AS ${prefix}_name,
 ${a}.source_name_state AS ${prefix}_name_state,${a}.source_image_url AS ${prefix}_image,
 ${a}.source_image_url_state AS ${prefix}_image_state${player ? `,
 ${a}.raw_position_code AS ${prefix}_position,${a}.raw_position_code_state AS ${prefix}_position_state,
 ${a}.raw_position_code_source_number::text AS ${prefix}_position_number` : ""}`;

const profileJoin = ({ alias, player, physical, actor, source, document, locator, ordinal, cg }) => `
 LEFT JOIN LATERAL (
   SELECT p.*,r.external_key FROM football.${player ? "player" : "team"}_profile_versions p
   JOIN ingest.source_records r ON r.id=p.source_record_id AND ${lineage("r", source, document, locator, ordinal)}
   WHERE p.id=${physical} AND p.${player ? "player" : "team"}_id=${actor} AND p.source_id=${source}
     AND p.profile_context='native_match_observation_v1:'||r.id::text AND p.variant_key='source:exact'
     AND ${at("p", cg)} AND NOT p.is_deleted
 ) ${alias} ON true`;

function codeField(out, key, state, text, number) {
  if (state === "number") {
    requireFact(typeof text === "string");
    numberField(out, key, "value", number);
  } else {
    requireFact(number === null);
    scalar(out, key, state === "string" ? "value" : state, text, "string");
  }
}

function profile(row, prefix, withPosition = false) {
  requireFact(row[`${prefix}_profile`] !== null);
  const out = fields({}, row, [
    ["id", `${prefix}_external_key`, `${prefix}_id_state`],
    ["name", `${prefix}_name`, `${prefix}_name_state`],
    ["image_url", `${prefix}_image`, `${prefix}_image_state`],
  ]);
  if (withPosition) codeField(out, "position_id", row[`${prefix}_position_state`], row[`${prefix}_position`], row[`${prefix}_position_number`]);
  return out;
}

async function rootData(c) {
  const [h, a] = ["home", "away"].map((side) => profileJoin({
    alias: side, physical: `$5::bigint${side === "away" ? "+($6::bigint-$5::bigint)" : ""}`,
    actor: side === "home" ? "$7::bigint" : "$8::bigint", source: "$2::bigint", document: "$3::bigint",
    locator: `'/data/${side}_team'`, cg: "$4::bigint",
  }));
  const row = one(await payload("root", `
 SELECT r.id witness,r.external_key,${profileColumns("home", "home")},${profileColumns("away", "away")}
 FROM ingest.source_records r ${h} ${a}
 WHERE r.id=$1::bigint AND ${lineage("r", "$2::bigint", "$3::bigint", "'/data'")}`,
  [c.source_record_id, c.source_id, c.document_id, c.b.catalog_generation,
    c.source_home_team_profile_version_id, c.source_away_team_profile_version_id, c.home_team_id, c.away_team_id]));
  const data = {};
  scalar(data, c.feature_code === "match" ? "id" : "match_id", c.source_match_id_state, row.external_key, "string");
  for (const side of ["home", "away"]) {
    observedObject(data, side + "_team", c[`source_${side}_team_state`], () => profile(row, side));
  }
  return data;
}
