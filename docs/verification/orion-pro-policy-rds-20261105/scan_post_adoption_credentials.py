#!/usr/bin/env python3
"""Reuse the frozen live-value scanner with a new receipt; no secret output."""
from pathlib import Path
import hashlib
ROOT = Path(__file__).resolve().parents[3]
original = ROOT / 'docs/verification/aws-release-20261104/scan_credentials.py'
source = original.read_text()
assert hashlib.sha256(original.read_bytes()).hexdigest() == '86c7f9667eddfb1c6000b6490e6dcfe6f20612d4573c890e127011e929c21f02'
source = source.replace("out = pathlib.Path(__file__).with_name('credential-scan-final.json')", "out = ROOT / 'docs/verification/orion-pro-policy-rds-20261105/ROOT_RDS014_CREDENTIAL_SCAN.json'")
source = source.replace('python3 docs/verification/aws-release-20261104/scan_credentials.py', 'python3 docs/verification/orion-pro-policy-rds-20261105/scan_post_adoption_credentials.py')
exec(compile(source, str(original), 'exec'), {'__file__': str(original), '__name__': '__main__'})
