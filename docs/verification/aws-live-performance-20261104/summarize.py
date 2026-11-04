"""Summarize only successful, stable, semantically identical pairs."""

import json
import statistics
from pathlib import Path

folder = Path(__file__).resolve().parent
raw = json.loads((folder / "measurements.json").read_text())
summary = {
    "commit": raw["source"],
    "started": raw["started"],
    "finished": raw.get("finished"),
    "sourcesStable": raw.get("sourcesStable"),
    "routes": [],
}
for entry in raw["routes"]:
    route = {
        "route": entry["route"],
        "paired": entry["paired"] and raw.get("sourcesStable") is True,
        "selectionIssue": entry.get("stop"),
        "differences": entry.get("differences", []),
        "samples": [],
    }
    summary["routes"].append(route)
    if not route["paired"]:
        continue
    for stage in ["cold", "warm"]:
        for reader in ["legacy-app", "aws-app"]:
            rows = [
                x
                for x in entry["trials"]
                if x["stage"] == stage and x["reader"] == reader
            ]

            def median(values):
                return round(statistics.median(values), 3)

            durations = [x["elapsedMs"] for x in rows]
            fields = {
                k: median([x[k] for x in rows])
                for k in [
                    "httpBytes",
                    "handlerMs",
                    "pgDataRows",
                    "pgDataRowFrameBytes",
                    "pgFieldPayloadBytes",
                ]
            }
            metrics = {
                k: median([x["metrics"].get(k, 0) for x in rows])
                for k in [
                    "sql_count",
                    "pool_wait_ms",
                    "sql_ms",
                    "object_bytes",
                    "object_ms",
                    "parse_bytes",
                    "gzip_bytes",
                ]
            }
            route["samples"].append(
                {
                    "stage": stage,
                    "reader": reader,
                    "n": len(rows),
                    "elapsedMedianMs": median(durations),
                    "elapsedMinMs": min(durations),
                    "elapsedMaxMs": max(durations),
                    **fields,
                    **metrics,
                }
            )
(folder / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
