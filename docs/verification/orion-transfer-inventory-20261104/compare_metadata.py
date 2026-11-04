"""Reproduce the inventory locally from saved metadata; never connects remotely."""
from collections import Counter
import datetime
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
load = lambda name: json.loads((OUT / name).read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
plan = load("query-plan.json")
neon_receipt, aws_receipt = load("neon-direct.json"), load("aws-complete-direct.json")
neon, aws = neon_receipt["metadata"], aws_receipt["metadata"]
tls, budget = load("client-tls-readback-final.json"), load("final-execution-budget.json")


def indexed(rows, fields):
    result, duplicates = {}, 0
    for row in rows:
        key = tuple(row[f] for f in fields)
        if key in result:
            duplicates += 1
        result[key] = row
    return result, duplicates


def compare(kind, keys, values):
    n, nd = indexed(neon[kind], keys)
    a, ad = indexed(aws[kind], keys)
    rows = []
    for key in sorted(set(n) | set(a)):
        nr, ar = n.get(key), a.get(key)
        if nr is None:
            status = "present_in_aws_unverified_in_neon" if kind == "objects" else "absent_in_neon"
        elif ar is None:
            status = "absent_in_aws"
        elif all(nr.get(f) == ar.get(f) for f in values):
            status = "identical_metadata"
        else:
            status = "different_version_order_unverified"
        rows.append({"key": dict(zip(keys, key)), "classification": status, "neon": nr, "aws": ar})
    return {"counts": dict(Counter(r["classification"] for r in rows)), "uniqueNeon": len(n), "uniqueAws": len(a),
        "duplicateQueryRows": {"neon": nd, "aws": ad}, "rows": rows}


fixtures = compare("fixtures", ["season", "id"], ["day", "status"])
resources = compare("resources", ["endpoint", "params"], ["status", "ref_path", "ref_ordinal"])
objects = compare("objects", ["path"], ["sha256", "size"])
np = {r["provider_id"]: r for r in neon["profiles"]}
ap = {r["provider_id"]: r for r in aws["profiles"]}
profiles = []
conflict = plan["scope"]["knownProfileConflicts"][0]
for pid in plan["scope"]["profileIds"]:
    nr, ar = np[pid], ap[pid]
    if nr["endpoint"] is None and ar["endpoint"] is None:
        classification = "absent_exact_lookup_both_sources"
    elif nr["endpoint"] is None:
        classification = "absent_exact_lookup_in_neon"
    elif ar["endpoint"] is None:
        classification = "absent_exact_lookup_in_aws"
    elif all(nr.get(f) == ar.get(f) for f in ["status", "ref_path", "ref_ordinal", "object_sha256", "object_size"]):
        classification = "identical_metadata"
    else:
        classification = "ambiguous_pointer_or_version"
    known_conflict = pid == conflict["expectedProviderId"] and all(r.get("ref_path") == conflict["path"] and r.get("ref_ordinal") == str(conflict["ordinal"]) and r.get("object_sha256") == conflict["physicalSha256"] for r in [nr, ar])
    profiles.append({"providerId": pid, "classification": classification,
        "knownConflictSameCatalogueFingerprint": known_conflict, "memberIdentityReDecoded": False, "neon": nr, "aws": ar})
no = {r["path"]: r for r in neon["objects"]}
ao = {r["path"]: r for r in aws["objects"]}
archives = [{"path": p, "presentBoth": p in no and p in ao,
    "sameStoredShaAndSize": p in no and p in ao and no[p]["sha256"] == ao[p]["sha256"] and no[p]["size"] == ao[p]["size"],
    "awsIndexBoundToSameSha": p in ao and ao[p].get("indexed_status") == "ready" and ao[p].get("indexed_sha256") == ao[p]["sha256"]} for p in plan["scope"]["knownArchivePaths"]]
checks = []
check = lambda name, passed: checks.append({"name": name, "passed": bool(passed)})
check("final TLS client readback verify-full", tls["status"] == "pass" and tls["clientSslInUse"] and tls["parameters"]["sslmode"] == "verify-full")
for name, data in [("neon", neon), ("aws", aws)]:
    identity = data["identity"]
    check(name + " snapshot RR/RO and deadlines", identity["read_only"] == "on" and identity["isolation"] == "repeatable read" and identity["statement_timeout"] == "8s" and identity["lock_timeout"] == "1s")
    check(name + " fixture and object row caps not reached", all(not data[k] or len(data[k]) == data[k][0]["total_rows"] for k in ["fixtures", "objects"]))
    check(name + " representative prefixes and params not truncated", all((r.get("total_per_prefix") or 0) <= 128 and r.get("params_length", 0) <= 2048 for r in data["resources"]))
    check(name + " complete requested profile lookup set", {r["provider_id"] for r in data["profiles"]} == set(plan["scope"]["profileIds"]))
check("global statement and result byte caps", budget["passed"] and budget["statementsMaximum"] <= 20 and budget["resultBytes"] <= 16777216)
check("source input bytes unchanged", all(sha(ROOT / p) == h for p, h in plan["sourceInputsSha256"].items()))
missing_resources = [r for r in resources["rows"] if r["classification"] == "absent_in_aws"]
result = {"atUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "partial_metadata_inventory",
    "scope": {"leagueId": "l_3FJFUl", "seasons": plan["scope"]["seasons"], "profileIds": 63,
              "knownArchivePaths": 512, "representativeMatchPrefixes": load("fallback-query-plan.json")["representativeMatchPrefixes"]},
    "source": {"projectId": "sweet-queen-11955006", "projectName": "Orion Tech Sport", "branchId": "br-mute-bonus-be23014e", "branchName": "production",
               "computeId": "ep-steep-boat-bekuqo4w", "database": "neondb", "localConfigurationHostnameMatchesApiEndpoint": True},
    "snapshots": {"neon": neon["identity"], "aws": aws["identity"]},
    "fixtures": fixtures, "resources": resources, "objects": objects,
    "profiles": {"counts": dict(Counter(r["classification"] for r in profiles)), "rows": profiles},
    "knownArchivePaths": {"counts": {"requested": len(archives), "presentBoth": sum(r["presentBoth"] for r in archives), "sameStoredShaAndSize": sum(r["sameStoredShaAndSize"] for r in archives), "awsIndexBoundToSameSha": sum(r["awsIndexBoundToSameSha"] for r in archives)}, "rows": archives},
    "missingAwsResourceHttpStatusCounts": dict(Counter(str(r["neon"]["status"]) for r in missing_resources)),
    "supplierVersionOrdering": "unverified; resource/object/index import clocks do not establish supplier freshness",
    "staleVersionsConfirmed": 0, "bodyDataDownloaded": False, "rawBodiesPersisted": False, "remoteWrites": [],
    "fullTransferAcceptance": False, "purgeAuthorized": False, "checks": checks, "documentaryChecksPassed": all(c["passed"] for c in checks),
    "budget": budget,
    "limitations": [
        "Only the configured active source branch was queried. Vercel project morning-thunder-68538387/main br-hidden-math-awrw1xep is archived and unqueried; org-late-credit-34206597 returned401. Complete account/source discovery is unverified.",
        "Neon connector timeout and initial server-TLS guard failure are retained. SQL shows server-hop ssl=false; enforced client verify-full and a separate successful client TLS handshake are recorded. The first TLS capture helper also failed on an unsupported attribute; retained separately.",
        "Snapshots are sequential, not a simultaneous cross-database snapshot. No statement or byte cap was exceeded; broader resources/families were not enumerated.",
        "Same stored SHA/size proves catalogue agreement only. No payload-byte recomputation, member identity/type/leaf comparison, typed ingestion or manifest-body pointer decoding occurred.",
        "The AWS-only collected object key was not explicitly probed on Neon; its source absence is unverified. It must be preserved, not overwritten or deleted.",
        "62 missing exact profile lookup keys may have other representations or sources. The known wrong-identity member retains the same catalogue fingerprint; no new identity-body check occurred.",
        "15 missing resource keys include6HTTP404 observations. Negative provider outcomes are not missing business facts and do not authorize collection or transfer.",
        "has_error in raw query receipts is SQL non-nullability of the JSONB error column; JSON null may satisfy it. It is not interpreted as an actual provider error.",
        "13 duplicate AWS result rows originate from overlapping query UNION paths; comparison deduplicates by endpoint/params and excludes query counters. No duplicate source facts are inferred.",
        "Current manifest selection and supplier recency cannot be inferred from object paths or import timestamps. Different versions require content-aware reconciliation in a separately authorized typed-import phase."
    ],
    "reproduceOffline": "python3 -B docs/verification/orion-transfer-inventory-20261104/compare_metadata.py",
    "sourceReceiptsSha256": {n: sha(OUT / n) for n in ["discovery.json", "connector-errors.json", "neon-run.json", "neon-direct.json", "aws-direct.json", "aws-complete-direct.json", "client-tls-readback.json", "client-tls-readback-final.json", "query-plan.json", "fallback-query-plan.json", "aws-complete-query.json", "final-execution-budget.json", "prepare_inventory.py", "metadata_inventory.py", "verify_tls_and_complete_aws.py", "read_client_tls.py", "compare_metadata.py"]}}
(OUT / "inventory.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"status": result["status"], "checks": len(checks), "documentaryChecksPassed": result["documentaryChecksPassed"],
    "fixtures": fixtures["counts"], "resources": resources["counts"], "objects": objects["counts"], "profiles": result["profiles"]["counts"], "archives": result["knownArchivePaths"]["counts"]}))
