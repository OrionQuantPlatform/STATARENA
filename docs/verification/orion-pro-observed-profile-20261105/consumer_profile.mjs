// Existing decoder, exercised before the retained-profile correction.
import { readFileSync, writeFileSync } from "node:fs";
import { decodePartition } from "../../../dashboard/frontend/src/season_data.js";
const [inputPath, outputPath] = process.argv.slice(2);
const input = JSON.parse(readFileSync(inputPath, "utf8"));
const expected = JSON.parse(readFileSync(input.sourceDescriptors, "utf8")).rows;
const json = decodePartition(input.json.data), packed = decodePartition(input.packed.data);
if (json.appearances.length !== 192 || packed.appearances.length !== 192)
  throw Error("Captured-profile decoder cardinality");
const byID = new Map(json.appearances.map((row) => [row.id, row]));
for (const row of packed.appearances) {
  const original = byID.get(row.id);
  if (!original || Object.keys(original).length !== Object.keys(row).length)
    throw Error("Packed profile property mismatch " + row.id);
  for (const key of Object.keys(row))
    if (JSON.stringify(original[key]) !== JSON.stringify(row[key]))
      throw Error("Packed profile value mismatch " + row.id + "/" + key);
}
for (const { structural } of expected) {
  const actual = byID.get(structural.id);
  for (const key of ["name", "playerRef", "imageUrl"])
    if (actual?.[key] !== structural[key])
      throw Error("Captured profile changed " + structural.id + "/" + key);
}
writeFileSync(outputPath, JSON.stringify({ runtime: process.version,
  decodedRows: packed.appearances.length,
  observed: packed.appearances.filter((p) => p.playerId === "p_100001").map(({id,name,playerRef,imageUrl}) => ({id,name,playerRef,imageUrl})),
  decoder: "existing season_data.decodePartition" }, null, 2) + "\n");
