# Owned local Node24 runtime

Suggested commit: `test: verify Node24 exact numeric wire runtime`.

ROOT authorized this temporary local runtime preparation. DOWNLOAD.json records
the actual official index response digest, selected version, archive/SHASUMS URLs,
archive digest, local binary and executed process identity/wire command.
Only HTTPS nodejs.org was contacted. No global PATH/install change was made.

The initial acquisition used Python urllib with a redirect handler requiring
HTTPS and hostname nodejs.org, fetched the official index, selected its newest
v24 entry supporting osx-arm64-tar, fetched SHASUMS256.txt and the named archive,
compared SHA256, and used tarfile.extractall(filter='data') into its marked owned
directory. Its precise selected result is pinned independently of future index
updates:

```
version=v24.22.2
archive=https://nodejs.org/dist/v24.22.2/node-v24.22.2-darwin-arm64.tar.xz
sha256=1f5ac075be50bed4780ea3be19a007fda95ea4d527d28d76d0b91de47d915115
binary=/tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node
```

Exact executed runtime/wire command (requires only the retained local runtime):

```
/tmp/statarena-node24-runtime/v24.22.2/node-v24.22.2-darwin-arm64/bin/node -p 'JSON.stringify({version:process.version,arch:process.arch,platform:process.platform,rawJSON:typeof JSON.rawJSON,wire:JSON.stringify({x:JSON.rawJSON("0.8200000000000000001")})})'
```

Actual process.version is v24.22.2; platform/arch are darwin/arm64. rawJSON is a
function and the inner JSON retains the exact decimal token. This is a local
Node24 engine observation, not a claim of the deployed Lambda patch/platform.
The later E2E passes this binary explicitly and verifies number tokens with
independent Python Decimal parsing; a Bun-only success is insufficient.

The archive and extraction remain under /tmp/statarena-node24-runtime/v24.22.2
for reproducibility. Their owned marker identifies this task. They can be removed
after the associated E2E work; no source/business data is stored there.
