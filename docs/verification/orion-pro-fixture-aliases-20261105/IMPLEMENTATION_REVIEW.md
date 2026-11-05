# Fixture alias adapter review

Suggested commit: `feat: serve versioned typed fixture aliases`.

Status: actual pre-code RED saved, followed by actual-app AFTER 16/16.
The exact result and practical limits are in BILAN.md. This document explains
the source; it does not replace the retained runtime evidence.

The new helper handles only the two inventoried date/league fixture aliases.
It validates params/cursor before SQL, admits exactly one published edition token
with sealed dg/cg, verifies league aliases and optional season, then calls the
existing orionProRoute interface for `/api/fixtures` with equivalent filters.
The frozen reader supplies every fixture DTO; no SQL sports payload, parser or
profile precedence is copied or modified. Statement work and ordering inherit
that reader. The small local qualification corpus covers numeric public IDs;
there is no separate mixed-case/collation performance or parity claim.

The additive pagination envelope retains data.matches. Outer cursors bind alias
path/date/league, explicit season filter, status, limit and v, and carry the inner
core cursor. Core and alias cursor transports cannot be interchanged. Unknown
dates remain unknown and are excluded only by the actual date filter; a league
page still retains them last. Status and all nullable DTO fields are unchanged.

The wrapper has its own contract header and ETag bound to the source validator
and canonical public request. HEAD and matching304 invoke only edition metadata
and the core HEAD metadata. A conditional miss then fetches the core GET and
verifies validator agreement. Planned calls are3SQL for a normal GET,2for HEAD/
304 and4for a conditional miss, constant in fixture count. These are counts, not
production cost/latency guarantees. The app remains Pro-only and requires v;
ProOFF dispatch is unchanged.

The source representation remains summary-v1-shots-v1. Its null image/playoff
projection is preserved; the wrapper does not claim exhaustive native detail or
new media data. Responses use15second revalidation. A pro1 token scopes one
edition; global day consumers need complete manifest edition/page traversal.
Partial-date scope must not be called a complete worldwide day.

The original16cases are frozen before wrapper implementation. F02's actual501
RED and its cleanup/pins are saved. AFTER will use the same expectations/fixture,
with direct core-reader DTO comparison plus independent source values and SQL/
HTTP boundary traces. ROOT owns app freeze/guard/CI integration and the57-route
matrix. Original four readers, appearanceb3d4, entity950 and prior evidence bundles
remain unchanged. The separate appearance admission follow-up records its
whole-edition database-value read cost; no such optimization is slipped in here.
