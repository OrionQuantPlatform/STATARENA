"""ROOT-reviewed R23 native identity rollback; other V2 cases stay exact."""
from runtime_cases_v2 import (R00, R01, R02, R03, R04, R05, R06, R07, R08, R09,
    R10, R11, R12, R13, R14, R15, R16, R17, R18, R19, R20, R21, R22,
    R24, R25, R26, R27, R28, R29, R30)


def R23(c):
    c.correct("A")
    before = c.state()
    killed = c.start("publish", barrier="before_ready_commit")
    event = c.phase(killed, "before_ready_commit")
    c.kill(killed)
    c.assert_ready_rollback(before, event)
    orphan = c.start("publish", barrier="after_ready_commit")
    event = c.phase(orphan, "after_ready_commit")
    ids = event["buildIds"]
    c.kill(orphan)
    a, b = c.start("publish", barrier="after_plan"), c.start("publish", barrier="after_plan")
    c.phase(a, "after_plan"); c.phase(b, "after_plan")
    c.release(a); c.release(b)
    c.finish(a); c.finish(b)
    assert set(ids) <= set(c.ready_build_ids())
    c.correct("shared")
    previous = c.active_builds()
    child = c.start("publish", barrier="after_first_pointer_write")
    c.phase(child, "after_first_pointer_write")
    assert c.active_builds() == previous
    c.kill(child)
    assert c.active_builds() == previous
    c.publish()
    c.assert_products()


CASES = [R00, R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12, R13,
    R14, R15, R16, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R28,
    R29, R30]
