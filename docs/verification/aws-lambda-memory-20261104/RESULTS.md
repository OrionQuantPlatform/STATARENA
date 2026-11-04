# Live memory comparison — configuration restored

All 12 dense-page GETs returned the identical complete 1,973,314-byte logical body and 431,391-byte gzip representation. Each response was HTTP 200, no-store, and a CloudFront MISS. Exact response `X-Amzn-RequestId` values matched all twelve Lambda REPORT rows. The first call after each memory change is excluded from the warm medians below.

| Five warm calls | 512 MiB | 1024 MiB | Difference at 1024 |
|---|---:|---:|---:|
| Median public HTTP | 3,924.20 ms | 2,716.53 ms | −30.8% |
| Median Lambda duration | 3,685.75 ms | 2,237.98 ms | −39.3% |
| Median billed GB-seconds | 1.843 | 2.238 | +21.4% |
| Maximum memory observed, including first call | 219 MiB | 279 MiB | — |

**512 MiB was restored**, with unchanged code SHA and successful function configuration. Doubling memory made this CPU-heavy page faster but increased its measured compute usage per request. This single small sequential A/B run is descriptive: other browser verification requests overlapped on the shared RDS, the order was 1024 then 512, and it does not establish the best configuration for the complete workload or a monthly bill. No permanent memory or infrastructure-budget increase is justified by this run alone. The direct match-summary optimization separately avoids these dense pages until the user requests their data.

[Plan and failure modes](PLAN.md), [script](compare.py), [all public responses and selected CloudWatch REPORT lines](result.json), [request-ID attribution and derived measurements](summary.json). The script preserves the original memory through `finally` and prints no environment or credentials.

Suggested commit: `test: compare live Lambda memory latency and billed compute`.
