# Bounded live Lambda memory comparison

Goal: compare the same dense, lossless SQL-backed season page at 512 and 1024 MiB, with no database, concurrency, code or cache-policy changes. This is a temporary reversible Lambda memory setting. The script restores 512 MiB in `finally`; any retained choice must subsequently be expressed through CloudFormation.

Expected: every response is HTTP 200, no-store, gzip, identical ETag and logical SHA-256 `0d6bbe72588aa8df43b6d7933093a9d9cd8f028a1b53d61fc8c68bdc37f7d403`, decoded 1,973,314 bytes, encoded 431,391 bytes. No HTTP 413, timeout or truncated data. Capture the first request separately from subsequent warm requests. Preserve request timings and Lambda REPORT billed duration/memory for GB-second comparison. REPORT rows may include unrelated preview requests; only use clearly attributable sequential requests in analysis.

Failure modes: update failure or wrong account/function; unexpected original memory; response/content/version drift; non-success code; logs delayed; insufficient log attribution. Abort on unexpected data, retain failed receipt, restore original memory. Never print Lambda environment or credentials. No RDS modification.

Rerun from owner checkout:

```
python3 docs/verification/aws-lambda-memory-20261104/compare.py
```

Inputs: AWS profile `statarena`, region `us-east-2`, account `361769570630`, function `statarena-backend`; HTTPS URL is recorded by the script. Uses public TLS verification, one persistent HTTPS connection per configuration, sequential requests only. CloudWatch logs are retrieved only from this function's dedicated log group.
