"""Verify the application's /data/ URL prefix with HEAD only; preserve prior bad-prefix result."""
import datetime
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request

OUT = Path(__file__).resolve().parent
BUCKET = "statarena-football-333rosky-70db6e5f"
ACCOUNT = "361769570630"
DOMAIN = "https://d2clu0phovomb8.cloudfront.net/"


def aws(*args):
    return json.loads(subprocess.check_output(
        ["aws", "--profile", "statarena", "--region", "us-east-2", *args,
         "--output", "json"], text=True))


def head(kind, key):
    url = DOMAIN + urllib.parse.quote(key, safe="/")
    try:
        response = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=20)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return {"kind": kind, "url": url, "status": response.status,
                "downloadedBodyBytes": 0,
                "headers": {k: v for k, v in response.headers.items()
                            if k.lower() in ("content-type", "content-length", "cache-control", "x-cache")}}


assert aws("sts", "get-caller-identity", "--query", "Account") == ACCOUNT
function = aws("cloudfront", "get-function", "--name", "statarena-public-files-20261104",
               "--stage", "LIVE", str(OUT / "cdn-function.js"))
sample = json.loads((OUT / "supplement.json").read_text())["results"]["exampleImage"]["rows"][0][0]
objects = aws("s3api", "list-objects-v2", "--bucket", BUCKET,
              "--expected-bucket-owner", ACCOUNT, "--prefix", "data/raw/pitchapi-world/blobs/",
              "--max-keys", "1", "--no-paginate").get("Contents", [])
results = [head("image-with-correct-data-prefix", "data/" + sample),
           head("backup", "_migration/neon-full-initial.dump"),
           head("mutable-structured-manifest", "data/raw/index.json")]
if objects:
    results.append(head("immutable-structured-object", objects[0]["Key"]))
report = {"atUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "command": "python3 docs/verification/aws-architecture-audit-20261104/cdn_checks.py",
          "setup": "Existing CDN function readback and one S3 key metadata lookup; unauthenticated HEAD only; no object contents downloaded or remote writes. Correct /data/ prefix follows cloudFrontObjectUrl. Previous missing-prefix403 remains in supplement.json.",
          "function": function, "results": results}
(OUT / "cdn-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"statuses": [{"kind": r["kind"], "status": r["status"]} for r in results]}))
