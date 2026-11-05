# Original22expectation regression namespace

Suggested commit: `fix: retain captured appearance profile observations`.

This folder reruns the original appearance22case acceptance after the narrow
physical-profile correction, without writing into or changing its frozen bundle.
NAMESPACE_ADAPTATION.json proves only the output namespace, exact reported
entrypoint and default label changed. The22case block SHA remains
84e6e2f7bd8c3a1ab2210b5b13b736a7bcf9f92230f725ee081736a32b80c0be.
The five copied support files are byte-identical to the original sources.

Actual result:22/22, Node24 and PG18.6,
`runs/20261105T144627298556Z-actual-node24-original22-after-profile-fix/result.json`,
SHA2569c9e9fc61bb10b7257127e0cc1110df8d996cda477a570508b73ca505335bd63.
All source pins and owned cleanup verified;0external calls. The correction's
specific pre-code RED/8-case AFTER/native legal-state proof are in the sibling
orion-pro-observed-profile-20261105/BILAN.md. This is local synthetic acceptance.

Exact rerun from the repository root:

```sh
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/orion_pro_appearances_regression_local.py --label actual-node24-original22-after-profile-fix --node24 /tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node
```
