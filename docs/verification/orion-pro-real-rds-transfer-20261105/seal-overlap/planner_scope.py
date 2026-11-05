"""Experimental owned-only planner scope; the original native checks remain active."""
from __future__ import annotations

CHANGE = 'SET LOCAL enable_nestloop=off'
SETTINGS = """SELECT current_setting('enable_nestloop'),current_setting('enable_hashjoin'),
    current_setting('enable_mergejoin'),current_setting('statement_timeout'),current_setting('lock_timeout')"""


def activate(conn):
    """Use one transaction-local planner setting through seal and deferred commit."""
    if not conn.autocommit or conn.info.transaction_status.name != 'INTRANS':
        raise AssertionError('Planner scope requires the owned current explicit transaction')
    if conn.execute(SETTINGS).fetchone() != ('on', 'on', 'on', '8s', '1s'):
        raise AssertionError('Unexpected planner/deadline baseline')
    conn.execute(CHANGE)
    if conn.execute(SETTINGS).fetchone() != ('off', 'on', 'on', '8s', '1s'):
        raise AssertionError('Only the scoped nested-loop planner preference may change')
