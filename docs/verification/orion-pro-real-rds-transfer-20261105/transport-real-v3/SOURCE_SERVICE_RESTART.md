# Source service recovery V4 for the real P2/015 transport

This is a proposed allocation, not a ROOT release. The existing owned typed root is stopped. The last service checkpoint `8f4d77a9358a36419ac6424560c98f8ebf166e882702aac968f2e69a36164db6` and epoch `2026-11-05T12:54:23.896939+00:00` are historical. No restart, GET, construction, live preflight or write was performed while preparing this allocation.

ROOT issues a new `core-checkpoint/ROOT_RECOVERY_RELEASE_V4.json` with `allocationId=core-recovery-v4` and fresh `atUtc`, using the same release kind and immutable controller, E2E, protocol and pins as the completed `ROOT_RECOVERY_RELEASE_V3.json` (`6abb413b6ffa9da4bc8571f48acfbfa218600559ee5f206da827d9740295324f`). No previous allocation or evidence is modified. Scope is exactly one restart of the same private root `/var/folders/8z/mp96_9353w79bsgv7kftgk2h0000gn/T/orion-pro-e2e-939fcgo9`, loopback55467, dbpostgres, PostgreSQL18.6 and TLS. Bounds: two reads of the retained capture through the existing RAM socket, no recapture/cloud, no business writes or schema changes, zero source construction,300s active/3GiB owned disk/64MiB proof/3,600s idle maximum. Stop on the first unexpected failure; preserve the corpus, release consumption and proof.

```sh
repo='/Users/lemonnierhugo/Desktop/Coding Project/Football_ranking'
checkpoint="$repo/docs/verification/orion-pro-real-rds-transfer-20261105/core-checkpoint"
release="$checkpoint/ROOT_RECOVERY_RELEASE_V4.json"
# Substitute the SHA-256 from ROOT's separate authorization.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/statarena-publication-test-python python3 "$checkpoint/e2e_v2.py" --run-recovery --release "$release" --release-sha256 ROOT_RELEASE_SHA256
```

Execute only with the explicit ROOT allocation and clean libpq routing environment. Preserve the output, release hash and new consumed record. The original controller remains physically live after READY; record execution session, PID, postmaster epoch, control socket, marker, descriptor, checkpoint and both native94/67 receipts. Wait for explicit ROOT STOP or the preexisting controller deadline. Keep this source service idle for ROOT preflight and bounded COPY, and stop it cleanly through the same control socket afterwards. Do not build a second source or perform spatial recovery during this allocation.

Expected seven passing cases: retained stopped root; exact read-only identity/P1 journal012/013; one sealed core phase `g2/sid2/run1`; independent semantic31 `5f9175c1526ad2db4426ebe02d3e412e20999c2bd6486aef5d82d082f34255e0`,15,437 appearances and478,547 cells; native94/67 before; fresh core-only no-op; native94/67 after. Both native observations must equal the exact retained `e0ba27c04c2d0936c9447c2a2aa74c1cfa8733d1062b855794cdf69032e6db79` bytes and semantic native94 `220b5da11d56ae16c010fbaa35c535b389af6fe8bc55988a84804f27057d1eb8`. The acceptance keeps logical checkpoint `35dba5b977335c957d39472ca85dbfc6c2ce0074a94a558badbec32f82fb73cc`. The pair and operation release pin the newly recovered service checkpoint and actual descriptor epoch; the source projection must equal the logical/historical checkpoints after excluding exactly `marker`, `markerPath`, `sourceDescriptor`, `sourceDescriptorSha256`, `native94Evidence`. Source business values, sequence values, receipts and original clocks stay exact. The currently qualified target remains independent actual RDS015, B0 only, with the previous24 sequence gaps retained.

Suggested commit: `docs: prepare fresh readonly core service allocation`
