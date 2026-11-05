#!/usr/bin/env python3
"""One ROOT-authorized local RAM GET; only identifiers, types and hashes persist."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
CAPTURE = ROOT / "docs/verification/orion-pro-real-native-spatial-20261104/capture.py"
CAPTURE_SHA = "1498d36da2f83ea548db8a3433dd4d78f08add0e0bd6a5c90ef68b60851f7fe9"
SOURCE = Path("/tmp/orion-real-rds-source-20261105-v3/source.sock")
PID = 29953


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    if isinstance(value, Decimal):
        return ["number", format(value, "f")]
    if isinstance(value, dict):
        return ["object", [[k, canonical(v)] for k, v in sorted(value.items())]]
    if isinstance(value, (list, tuple)):
        return ["array", [canonical(v) for v in value]]
    if isinstance(value, datetime):
        return ["timestamp", value.isoformat()]
    return [type(value).__name__, value]


def hashed(value):
    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def native_kind(value):
    if value is None:
        return "null"
    if type(value) is bool:
        return "boolean"
    if isinstance(value, (Decimal, int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    return "array" if isinstance(value, list) else "object" if isinstance(value, dict) else type(value).__name__


def unpack(table):
    dictionaries = table.get("dictionaries", {})
    for index, values in enumerate(table["rows"]):
        absent = {int(v) for v in table.get("missing", {}).get(str(index), [])}
        yield index, {key: dictionaries[str(j)][int(values[j])] if str(j) in dictionaries and values[j] is not None else values[j]
                      for j, key in enumerate(table["keys"]) if j not in absent}


def main():
    started = time.monotonic()
    run = BASE / "ram-inventory-v1"
    run.mkdir(exist_ok=False)
    receipt = {"kind": "ROOT_AUTHORIZED_ONE_RAM_GET_V1", "status": "preparing", "ramGetCalls": 0,
               "cloudCalls": 0, "postgresConnections": 0, "businessWrites": 0,
               "rawBodiesPersisted": False, "realNamesOrScalarValuesPersisted": False,
               "allowedPersisted": ["public identifiers", "cohorts", "actors", "key/type/presence counts", "locators", "digests"],
               "pid": PID, "socket": str(SOURCE), "suggestedCommit": "test: inspect real publication source states without persisting bodies"}
    ledger_paths = [ROOT / "docs/verification/orion-pro-real-native-spatial-20261104/budget-v3.json"]
    manifest_path = CAPTURE.parent / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    ledger_paths.append(ROOT / manifest["oldLedger"]["path"])
    ledger_before = {str(p.relative_to(ROOT)): digest(p) for p in ledger_paths}
    try:
        assert digest(CAPTURE) == CAPTURE_SHA
        parent = SOURCE.parent.resolve()
        parent_info, socket_info = parent.stat(), SOURCE.lstat()
        assert parent_info.st_uid == socket_info.st_uid == os.getuid()
        assert stat.S_IMODE(parent_info.st_mode) == 0o700 and stat.S_ISSOCK(socket_info.st_mode) and stat.S_IMODE(socket_info.st_mode) == 0o600
        process = subprocess.run(["ps", "-p", str(PID), "-o", "pid=,args="], text=True, capture_output=True, check=True, timeout=3).stdout.strip()
        assert process.startswith(str(PID) + " ") and str(CAPTURE) in process and "--socket " + str(SOURCE) in process
        os.kill(PID, 0)
        capture_receipt = json.loads((CAPTURE.parent / "capture-v3/capture.json").read_text())
        assert capture_receipt["pid"] == PID and capture_receipt["ready"] is True and capture_receipt["socket"] == str(SOURCE)
        assert capture_receipt["captureCodeSha256"] == CAPTURE_SHA
        receipt.update(status="before_get", captureCodeSha256=CAPTURE_SHA, sourceDirectoryUid=parent_info.st_uid,
                       directoryMode=oct(stat.S_IMODE(parent_info.st_mode)), socketMode=oct(stat.S_IMODE(socket_info.st_mode)),
                       ledgerBefore=ledger_before, beforeGetAt=datetime.now(timezone.utc).isoformat())
        (run / "before-get.json").write_text(json.dumps(receipt, indent=2) + "\n")
        spec = importlib.util.spec_from_file_location("publisher_frozen_ram_capture", CAPTURE)
        capture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(capture)
        # The frozen fetch function alone is authorized. Even an accidental
        # call to a capture/connect/configuration path cannot reach a provider.
        def denied(*args, **kwargs):
            raise RuntimeError("Only one local frozen RAM fetch is authorized")
        for name in ["capture", "configuration", "connect", "neon_object"]:
            setattr(capture, name, denied)
        original_connect = socket.socket.connect
        def local_connect(sock, address):
            assert sock.family == socket.AF_UNIX and address == str(SOURCE) and receipt["ramGetCalls"] == 0
            receipt["ramGetCalls"] += 1
            return original_connect(sock, address)
        socket.socket.connect = local_connect
        try:
            snapshot = capture.fetch_snapshot(str(SOURCE))
        finally:
            socket.socket.connect = original_connect
        assert receipt["ramGetCalls"] == 1 and len(snapshot["cache"]) == 4
        assert snapshot["captureBudget"] == {"selects": 4, "decodedBytes": 9682314, "objectHttpRequests": 3, "physicalHttpBytes": 3961}
        receipt.update(status="after_get", afterGetAt=datetime.now(timezone.utc).isoformat(),
                       snapshotDocuments=4, frozenCaptureBudget=snapshot["captureBudget"],
                       manifestSha256=snapshot["manifestSha256"], normalizerSha256=snapshot["normalizerSha256"])
        (run / "after-get.json").write_text(json.dumps(receipt, indent=2) + "\n")
        editions = []
        global_players, global_teams = set(), set()
        for declaration in manifest["aws"]["partitions"]:
            path = declaration["path"]
            doc = snapshot["cache"][path]
            assert snapshot["meta"][path]["physicalSha256"] == declaration["sha256"]
            tables, inventory = {}, {}
            for name, packed in doc["tables"].items():
                rows = list(unpack(packed))
                tables[name] = rows
                fields = {}
                for col, key in enumerate(packed["keys"]):
                    counts = Counter()
                    h = hashlib.sha256()
                    for ordinal, row in rows:
                        if key not in row:
                            counts["absent"] += 1
                            state = ["absent"]
                        else:
                            value = row[key]
                            counts[native_kind(value)] += 1
                            if isinstance(value, str) and not value:
                                counts["emptyString"] += 1
                            if type(value) is bool:
                                counts["true" if value else "false"] += 1
                            elif isinstance(value, (int, float, Decimal)):
                                counts["zero" if value == 0 else "positive" if value > 0 else "negative"] += 1
                            state = canonical(value)
                        h.update(json.dumps([ordinal, key, state], separators=(",", ":"), ensure_ascii=False).encode())
                        h.update(b"\n")
                    fields[key] = {"packedColumn": col, "states": dict(counts), "typedValuesSha256": h.hexdigest()}
                inventory[name] = {"rows": len(rows), "keys": list(packed["keys"]), "fields": fields,
                                   "decodedRowsSha256": hashed([row for _, row in rows])}
            players = {row["playerId"] for _, row in tables["players"]}
            teams = {row["id"] for _, row in tables["teams"]}
            global_players |= players
            global_teams |= teams
            fixtures = {row["id"]: (ordinal, row) for ordinal, row in tables["fixtures"]}
            performance = {(row["matchId"], row["playerId"], row["teamId"]): (ordinal, row) for ordinal, row in tables["performances"]}
            shots_by_match = {}
            for ordinal, row in tables["shots"]:
                shots_by_match.setdefault(row["matchId"], []).append((ordinal, row))
            coverage_ids = {row["id"] for _, row in tables["matches"]}
            cohort, actors = [], []
            for mid, (ordinal, fixture) in sorted(fixtures.items()):
                selected_shots = shots_by_match.get(mid, [])
                cohort.append({"matchPublicId": mid, "fixtureLocator": f"/tables/fixtures/rows/{ordinal}",
                               "fixtureSha256": hashed(fixture),
                               "participants": {side: (fixture.get(side + "_team") or {}).get("id") for side in ["home", "away"]},
                               "coverageDeclaredByNormalizedMatches": mid in coverage_ids,
                               "selectedShotIds": [str(row["id"]) for _, row in selected_shots],
                               "selectedShotLocators": [f"/tables/shots/rows/{i}" for i, _ in selected_shots],
                               "selectedShotsSha256": hashed([row for _, row in selected_shots])})
            actor_counts = Counter()
            for ordinal, shot in tables["shots"]:
                mid, pid, tid = shot["matchId"], shot.get("playerId"), shot.get("teamId")
                perf = performance.get((mid, pid, tid))
                minutes = perf[1].get("minutes") if perf else None
                positive = type(minutes) is not bool and isinstance(minutes, (Decimal, int, float)) and minutes > 0
                actor_counts["shots"] += 1
                actor_counts["actorAbsentOrNull" if pid is None else "actorResolved" if pid in players else "actorNotInNormalizedPlayers"] += 1
                actor_counts["hasExactPerformance" if perf else "missingExactPerformance"] += 1
                actor_counts["positiveNativeMinutes" if positive else "withoutPositiveNativeMinutes"] += 1
                actors.append({"matchPublicId": mid, "shotId": str(shot["id"]), "playerPublicId": pid,
                               "teamPublicId": tid, "shotLocator": f"/tables/shots/rows/{ordinal}",
                               "shotSha256": hashed(shot), "exactPerformanceLocator": f"/tables/performances/rows/{perf[0]}" if perf else None,
                               "performanceSha256": hashed(perf[1]) if perf else None,
                               "positiveNativeMinutes": positive})
            team_lineage = [{"teamPublicId": row["id"], "locator": f"/tables/teams/rows/{ordinal}",
                             "nameState": "absent" if "name" not in row else native_kind(row["name"]),
                             "nameSha256": hashed(row["name"]) if "name" in row else None,
                             "rowSha256": hashed(row)} for ordinal, row in tables["teams"]]
            proof = {"season": declaration["season"], "leaguePublicId": declaration["leagueId"], "sourcePath": path,
                     "physicalSha256": declaration["sha256"], "tableInventory": inventory,
                     "cohort": cohort, "actors": actors, "actorCounts": dict(actor_counts), "teamNameLineage": team_lineage,
                     "coverageMatchSetSha256": hashed(sorted(coverage_ids)), "fixtureMatchSetSha256": hashed(sorted(fixtures)),
                     "coverageIdsOutsideFixtures": sorted(coverage_ids - set(fixtures)),
                     "shotMatchIdsOutsideFixtures": sorted(set(shots_by_match) - set(fixtures)),
                     "rawBodyPersisted": False, "namesAndScalarValuesPersisted": False}
            out = run / ("edition-" + declaration["season"].replace("/", "-") + ".json")
            out.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
            editions.append({"season": declaration["season"], "path": out.name, "sha256": digest(out),
                             "rows": {name: len(rows) for name, rows in tables.items()}, "actorCounts": dict(actor_counts),
                             "shotsSourceKeys": inventory["shots"]["keys"]})
        receipt.update(status="pass", editions=editions, uniquePlayers=len(global_players), uniqueTeams=len(global_teams),
                       elapsedSeconds=round(time.monotonic() - started, 3))
    except BaseException as error:
        receipt.update(status="fail", errorType=type(error).__name__)
        raise
    finally:
        receipt["ledgerAfter"] = {str(p.relative_to(ROOT)): digest(p) for p in ledger_paths}
        receipt["oldLedgersUnchanged"] = receipt["ledgerAfter"] == ledger_before
        (run / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"status": receipt["status"], "ramGetCalls": receipt["ramGetCalls"],
                          "oldLedgersUnchanged": receipt["oldLedgersUnchanged"],
                          "receipt": str((run / "result.json").relative_to(ROOT))}))


if __name__ == "__main__":
    main()
