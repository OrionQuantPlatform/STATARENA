# Deployed public availability readback

Read-only check of the existing frontend deployment, its two public aliases and the current CloudFront API. This is separate from typed RDS/publisher acceptance. No deployment, source ingestion, credential retrieval or data mutation is performed.

Before execution, expected outcomes are six GET responses with status200 and JSON content (health/manifest at each of three fixed origins), then three manifest HEAD responses with status200, no body and the matching GET ETag, then three conditional GET responses with status304 and no body. Every manifest must supply an ETag. The already captured Vercel control-plane metadata must bind both aliases to the exact READY production deployment/source commit. Errors, missing ETag, changed representation or redirects outside the fixed origin are failures; no retry or invented pass.

Command: `python3 docs/verification/orion-deployment-readback-20261105/verify_public.py`.

Limits:12 HTTP requests,10s/request,262144body bytes/response,2MiB total,180s whole run. TLS verified through the system trust store. Responses are held in RAM only; receipts retain metadata, sizes and SHA256, not sports bodies. Exact harness/protocol/control-plane inputs are archived per run. A failure is retained with remaining cases explicitly unverified. No browser/feature parity, Pro activation, SQL count, backend-only timing or production performance improvement is implied.

Commit suggested: `test: verify deployed frontend aliases and public API availability`.
