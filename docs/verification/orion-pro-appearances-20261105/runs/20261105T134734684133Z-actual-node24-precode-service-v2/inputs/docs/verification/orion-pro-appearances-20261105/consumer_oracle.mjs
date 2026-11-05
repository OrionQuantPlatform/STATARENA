// Existing consumer algorithms over independent synthetic descriptors and real
// HTTP results; no rewritten scoring and no database/source/network operation.
import { readFileSync, writeFileSync } from "node:fs";
import { decodePartition } from "../../../dashboard/frontend/src/season_data.js";
import {
  aggregateSeasonPlayers,
  seasonMetric,
} from "../../../dashboard/frontend/src/services/season-player.js";
import {
  buildCohorts,
  rankMetric,
  similarPlayers,
  SCOUT_METRICS,
} from "../../../dashboard/frontend/src/services/scouting.js";
import {
  allClubSummaries,
  clubStyleCohort,
  similarClubs,
} from "../../../dashboard/frontend/src/services/club-analysis.js";

const [inputPath, outputPath] = process.argv.slice(2),
  input = JSON.parse(readFileSync(inputPath, "utf8"));
const raw = JSON.parse(readFileSync(input.sourceDescriptors, "utf8"));
const expected = raw.rows.map(({ structural, native }) => {
  const row = { ...structural };
  for (const [field, kind, value] of native) {
    if (kind === "absent") continue;
    row[field] = kind === "number" ? Number(value) : value;
  }
  return row;
});
const pages = input.pages.map((page) => decodePartition(page.data));
const actual = pages.flatMap((page) => page.appearances);
if (input.packed) {
  const packed = decodePartition(input.packed.data);
  const packedByID = new Map(packed.appearances.map((row) => [row.id, row]));
  if (packedByID.size !== actual.length)
    throw Error("Packed cardinality mismatch");
  for (const row of actual) {
    const decoded = packedByID.get(row.id);
    if (!decoded || Object.keys(row).length !== Object.keys(decoded).length)
      throw Error("Packed property presence mismatch " + row.id);
    for (const [key, value] of Object.entries(row))
      if (JSON.stringify(decoded[key]) !== JSON.stringify(value))
        throw Error("Packed consumer mismatch " + row.id + "/" + key);
  }
}
const byID = new Map(actual.map((row) => [row.id, row]));
if (byID.size !== expected.length)
  throw Error(`Appearance cardinality ${byID.size}/${expected.length}`);
for (const row of expected) {
  const found = byID.get(row.id);
  if (!found) throw Error("Missing appearance " + row.id);
  for (const [field, value] of Object.entries(row)) {
    if (
      !Object.hasOwn(found, field) ||
      JSON.stringify(found[field]) !== JSON.stringify(value)
    )
      throw Error(`Source field mismatch ${row.id}/${field}`);
  }
  for (const [field, kind] of raw.rows.find(
    (item) => item.structural.id === row.id,
  ).native)
    if (kind === "absent" && Object.hasOwn(found, field))
      throw Error(`Absence converted ${row.id}/${field}`);
}
// Enforce the representation's total order independently of pagination size.
const order = (a, b) =>
  a.date === null
    ? b.date === null
      ? a.matchId.localeCompare(b.matchId) || a.id.localeCompare(b.id)
      : 1
    : b.date === null
      ? -1
      : a.date.localeCompare(b.date) ||
        a.matchId.localeCompare(b.matchId) ||
        a.id.localeCompare(b.id);
const canonicalExpected = [...expected].sort(order),
  canonicalActual = [...actual].sort(order);
const summarize = (rows, minimum = 450) => {
  const profiles = aggregateSeasonPlayers(rows),
    cohorts = buildCohorts(profiles, minimum);
  const p = profiles.find((player) => player.id === "p_100001");
  const ranks = Object.fromEntries(
    Object.keys(SCOUT_METRICS).map((key) => [key, rankMetric(p, key, cohorts)]),
  );
  const similar = similarPlayers(p, cohorts).map((item) => ({
    id: item.profile.id,
    similarity: item.similarity,
    parts: item.parts,
  }));
  return {
    profiles,
    cohorts,
    target: {
      id: p.id,
      matches: p.matches,
      minutes: p.minutes,
      rating: p.rating,
      stats: p.stats,
      ratios: p.ratios,
      unknownMinutes: p.unknownMinutes,
      role: p.role,
    },
    ranks,
    similar,
    groups: Object.fromEntries(
      [...cohorts.groups].map(([group, value]) => [
        group,
        {
          players: value.profiles.length,
          metricCounts: Object.fromEntries(
            Object.entries(value.distributions).map(([key, values]) => [
              key,
              values.length,
            ]),
          ),
        },
      ]),
    ),
  };
};
const a = summarize(canonicalActual),
  e = summarize(canonicalExpected);
for (const key of ["target", "ranks", "similar", "groups"])
  if (JSON.stringify(a[key]) !== JSON.stringify(e[key]))
    throw Error("Existing consumer mismatch " + key);
if (a.target.rating !== 40 / 6)
  throw Error("Known-appearance rating mean changed");
if (a.target.rating === (45 * 10 + 5 * 90 * 6) / (45 + 5 * 90))
  throw Error("Rating became minutes-weighted");
if (a.groups.O?.players !== 32 || a.similar.length !== 8)
  throw Error("Complete cohort/top8 not observed");
const firstOnly = summarize(pages[0].appearances);
if (firstOnly.similar.length !== 0)
  throw Error("First page should not masquerade as eligible full cohort");
const stricter = summarize(canonicalActual, 540),
  stricterExpected = summarize(canonicalExpected, 540);
if (JSON.stringify(stricter.groups) !== JSON.stringify(stricterExpected.groups))
  throw Error("Peer-minute eligibility changed");
const data = {
  matches: pages.flatMap((page) => page.matches),
  fixtures: pages.flatMap((page) => page.fixtures),
  appearances: canonicalActual,
  teams: [
    ...new Map(
      pages.flatMap((page) => page.teams).map((team) => [team.id, team]),
    ).values(),
  ],
};
const clubs = allClubSummaries(data),
  clubCohort = clubStyleCohort(clubs);
if (clubs.length !== 12) throw Error("Typed club context is incomplete");
for (let index = 0; index < 12; index++) {
  const club = clubs.find((row) => row.id === "t_" + String(100001 + index));
  if (club?.matches !== 6) throw Error("Club result denominator mismatch");
  const expected = index < 2 ? 5 : 6;
  if (club.stats.xgFor?.count !== expected)
    throw Error("Registered team-stat reliability exclusion changed");
}
const report = {
  runtime: {
    version: process.version,
    arch: process.arch,
    platform: process.platform,
  },
  sourceRows: expected.length,
  decodedRows: actual.length,
  profileCount: a.profiles.length,
  target: a.target,
  groups: a.groups,
  similar: a.similar,
  ranks: a.ranks,
  firstPageSimilar: firstOnly.similar.length,
  stricterGroups: stricter.groups,
  clubCount: clubs.length,
  clubs: clubs.map((club) => ({
    id: club.id,
    matches: club.matches,
    excludedStats: club.excludedStats,
    stats: club.stats,
  })),
  clubSimilar: clubs[0]
    ? similarClubs(clubs[0], clubs, clubCohort).map((item) => ({
        id: item.club.id,
        similarity: item.similarity,
        parts: item.parts,
      }))
    : [],
  dataReadThrough:
    "actual Node24 HTTP -> existing packed/season/scouting/club consumer algorithms",
};
writeFileSync(outputPath, JSON.stringify(report, null, 2) + "\n");
console.log(
  JSON.stringify({
    sourceRows: report.sourceRows,
    decodedRows: report.decodedRows,
    profiles: report.profileCount,
    targetRating: report.target.rating,
    similar: report.similar.length,
    clubs: report.clubCount,
    clubSimilar: report.clubSimilar.length,
    runtime: report.runtime,
  }),
);
