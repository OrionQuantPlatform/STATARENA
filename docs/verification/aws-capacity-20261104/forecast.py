"""Use explicit inclusion weights for each saved/archive and endpoint-family stratum."""

import json, statistics, math
from pathlib import Path
from collections import Counter, defaultdict

folder = Path(__file__).resolve().parent
survey = json.loads((folder / "effective-sample.json").read_text())
live = json.loads(
    (folder.parent / "aws-release-20261104/inventory-first-ready.json").read_text()
)["actual"]
rels = {r["table"]: r for r in live["tables"] if r["schema"] == "statarena_app"}
allrows = survey["sample"]
sample = defaultdict(list)
for r in allrows:
    assert "error" not in r, r
    sample[r["s"]].append(r["rows"])
n_by = survey["strata"]
density = {
    k: v["physicalBytesIncludingIndexes"] / v["liveRowsEstimate"]
    for k, v in rels.items()
    if v["liveRowsEstimate"] > 0
}


def proj(calc):
    n = var = 0
    for s, r in sample.items():
        N = n_by[s]
        x = [calc(row, s) for row in r]
        n += N * statistics.mean(x)
        var += (
            N * N * (1 - len(x) / N) * statistics.variance(x) / len(x)
            if len(x) > 1
            else 0
        )
    se = math.sqrt(var)
    return {
        "estimate": round(n),
        "sample95Lower": round(max(0, n - 1.96 * se)),
        "sample95Upper": round(n + 1.96 * se),
    }


tables = set(k for row in allrows for k in row["rows"])
typed = {t: proj(lambda row, s: row.get(t, 0)) for t in sorted(tables)}
for t in typed:
    if t in density:
        typed[t]["bytesEstimate"] = round(typed[t]["estimate"] * density[t])
stable = {t for t in tables if rels.get(t, {}).get("liveRowsEstimate", 0) >= 100}
metrics = {"half_stat_metrics", "player_stat_metrics"}
detail = proj(
    lambda row, s: sum(count * density[t] for t, count in row.items() if t in stable)
)
metric = proj(lambda row, s: sum(row.get(t, 0) * density[t] for t in metrics))
other = proj(
    lambda row, s: sum(
        count * density[t] for t, count in row.items() if t in stable - metrics
    )
)
known_keys = sum(n_by.values())
head = round(known_keys * density["match_families"])
# These three independent normalized core relations mirror parent full-roster performance,
# match shots, and appearance memberships. Individually saved subresources never produce extra core rows.
core = proj(
    lambda row, s: (
        (
            row.get("match_players", 0)
            * (density["appearances"] + density["match_appearance_members"])
            if s.startswith("players/")
            else 0
        )
        + (
            row.get("match_shots", 0) * density["shots"]
            if s.startswith("shots/")
            else 0
        )
    )
)
physical = sum(v["physicalBytesIncludingIndexes"] for v in rels.values())
catalog = json.loads(
    (folder.parent / "aws-catalog-20261104/full-postgres-roundtrip.json").read_text()
)["physicalCatalogBytes"]
base = live["databaseBytes"] - physical
out = {
    "command": "python3 docs/verification/aws-capacity-20261104/forecast.py",
    "setup": "Effective population and sample, real physical bytes incl indexes divided by first-ready row counts. 95% bounds reflect independent stratified response sampling only; excludes uncertainty in bytes/row, catalog growth, source additions and core proxy choice. Counts and default layout are forecasts.",
    "currentDatabase": live["databaseBytes"],
    "currentApp": physical,
    "netRoomAtGuard": 16_000_000_000 - 256_000_000 - live["databaseBytes"],
    "sourceAndOtherBaseline": base,
    "eligibleHeaders": known_keys,
    "sampledKeys": len(allrows),
    "detailTablesPhysicalProjection": detail,
    "twoMetricsProjection": metric,
    "otherDetailProjection": other,
    "headerProjection": head,
    "coreRosterAndShotsProxy": core,
    "earlierMeasuredCatalogBytes": catalog,
    "lowPopulationOrUntestedDensities": sorted(tables - stable),
    "metricsRows": {k: typed[k] for k in metrics},
    "allTables": typed,
}
partial = base + detail["estimate"] + head + catalog + core["estimate"]
out["partialTotalBudgetScenarioBytes"] = partial
proof = json.loads((folder / "metric-layout/results.json").read_text())["layouts"]
out["partialTotalWithTrialRatios"] = {
    k: round(partial - metric["estimate"] * (1 - v / proof["baseline"]))
    for k, v in proof.items()
}
(folder / "forecast.json").write_text(json.dumps(out, indent=2) + "\n")
print(
    json.dumps(
        {
            k: v
            for k, v in out.items()
            if k not in ("setup", "allTables", "lowPopulationOrUntestedDensities")
        },
        indent=2,
    )
)
