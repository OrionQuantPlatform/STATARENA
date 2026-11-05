# Spatial and advanced owned attempts

Suggested commit: feat: serve typed spatial and advanced match statistics.

[31e8e210](runs/20261105T175633753453Z-spatial-advanced-unwired-red-v1/result.json):
X01 passed with the old composite period API; X02 returned actual 501,
no-store and zero SQL on the spatial request. Later cases unverified.

[da98bf91](runs/20261105T181346030630Z-spatial-advanced-actual-after-v1/result.json):
X01–X06 passed, including both heatmap frames, declared shape states and
the directed network. X07 stopped at the fixture transaction guard
(SQLSTATE 55000) before the intended network-frame admission check.
The negative setup opened the generation under a savepoint; the fixture
now begins and seals the candidate in the top-level rollback-only
transaction, satisfying its actual xmin ownership constraint.
No product behavior, environment descriptor or case oracle changed.

[3c01f9bd](runs/20261105T181446272678Z-spatial-advanced-actual-after-v2/result.json):
X01–X14 passed with unchanged runtime and environment pins. The corrected
X07 exercised the intended frame refusal, and X10 exercised conflicting
typed value refusal, before either could create READY.
