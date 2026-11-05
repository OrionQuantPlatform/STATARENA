# Typed operational endpoints

Suggested commit: `feat: serve Pro health settings and media from typed SQL`.

Pro health now checks sealed typed publications; status/settings and media use typed metadata. Settings pagination preserves numeric ID order and exposes bounded scalar state only. Media resolves registered legacy aliases to verified hash/key/MIME metadata; attribution is never a fallback. The former legacy-serving lookups stay in ProOFF only.

Actual Nodev24.22.2/PG18.6:14/14 E2E,34HTTP,22SQL,10117response bytes,2.4s,232typed rows,0external calls. Health GET/HEAD/304 each1metadataSQL and no response body for HEAD/304; settings HEAD0SQL. Settings31runs cross2pages without overlap. Complete fallback/native/legacy regression20/20, including11nonempty ProOFF controls and unchanged4native-reader bytes. Remaining unimplemented route forms42→41; this is coverage progress, not a latency speedup.

Two failures are preserved: initial Pro health queried statarena_app (42P01); first product settings used lexical ID order and skipped rows, corrected with qualified bigint ORDER BY r.id. There is no comparable production before/after latency or hosted binary acceptance for this lot. New product is not deployed; RDS core import separately rolled back at native seal8s.
