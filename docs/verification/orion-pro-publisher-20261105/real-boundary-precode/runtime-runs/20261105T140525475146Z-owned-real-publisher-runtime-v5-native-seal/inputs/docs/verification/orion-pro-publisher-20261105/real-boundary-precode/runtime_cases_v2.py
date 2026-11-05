"""ROOT-reviewed case revision: R13 exercises native canonical uniqueness.

Original runtime_cases.py b384… remains exact. Its other30 functions are reused.
The publisher's defensive PROFILE_AMBIGUOUS branch is UNEXERCISED: native
current uniqueness and historical overlap checks forbid equal-rank winners.
"""
from runtime_cases import (R00, R01, R02, R03, R04, R05, R06, R07, R08, R09,
    R10, R11, R12, R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24,
    R25, R26, R27, R28, R29, R30)


def R13(c):
    for variant in ["provider_exact", "normalized", "manual", "null_winner"]:
        with c.fixture_change("profile_priority", variant=variant) as witness:
            c.apply_admission()
            plan = c.publish_plan()
            assert plan["profileSelections"] == witness["expectedSelections"]
    c.apply_admission()
    c.native_profile_ambiguity()


CASES = [R00, R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13,
    R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28,
    R29, R30]
