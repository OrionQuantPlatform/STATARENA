"""Executable native SQL workflows authored before016; no simulated outcomes."""
from __future__ import annotations
from decimal import Decimal

def D00(c):
    """Old schema RED, before any016 statement."""
    return c.expect_sqlstate('old_schema',lambda:c.db.execute('SELECT source_object_state FROM football.match_lineups LIMIT 0'),{'42703'})

def D01(c):
    """Migration rollback preserves native catalogue/data/journal."""
    return c.migration_rollback()

def D02(c):
    """Actual additive migration, old projected facts exact, no-op apply."""
    return c.upgrade_and_compare()

def D03(c):
    return c.native_workflow('events','events_exact',commit=False)

def D04(c):
    return c.native_workflow('lineups','lineups_exact',commit=False)

def D05(c):
    return c.native_workflow('stats','stats_exact',commit=False)

def D06(c):
    return c.native_workflow('h2h','h2h_empty_totals',empty=True,commit=False)

def D07(c):
    return c.native_workflow('events','event_unrecorded',overrides={'event_0':{'source_minute_state':'unrecorded'}},reject='native107: admission')

def D08(c):
    return c.native_workflow('events','event_locator',overrides={'event_record_0':{'locator':'/data/events/00'}},reject='native107: locator')

def D09(c):
    return c.native_workflow('events','event_profile_global',overrides={'event_profile_0':{'profile_context':'provider_global'}},reject='native107: profile')

def D10(c):
    return c.native_workflow('events','event_profile_wrong_source',overrides={'event_profile_0':{'variant_key':'provider:exact'}},reject='native107: profile')

def D11(c):
    return c.native_workflow('lineups','lineup_gap',overrides={'member_record_1':{'ordinal':2,'locator':'/data/home/starters/2'}},reject='native107: lineup')

def D12(c):
    return c.native_workflow('lineups','lineup_scalar_state',overrides={'member_0':{'shirt_number':'7','shirt_number_state':'string'},'member_profile_0':{'shirt_number':'8','shirt_number_state':'string'}},reject='native107: lineup')

def D13(c):
    return c.native_workflow('stats','stats_gap',overrides={'item_record_1':{'ordinal':3,'locator':'/data/periods/0/groups/0/items/3'}},reject='native107: stats')

def D14(c):
    return c.native_workflow('stats','stats_wrong_mapping',overrides={'item_0':{'raw_key':'unregistered'}},reject='native107: stats')

def D15(c):
    return c.native_workflow('stats','stats_nonfinite',overrides={'scalar_home0':{'numeric_value':Decimal('Infinity')}},reject='native107: stats')

def D16(c):
    return c.native_workflow('h2h','h2h_order_gap',overrides={'h2h_record_0':{'ordinal':1,'locator':'/data/recent_matches/1'}},reject='native107: h2h')

def D17(c):
    return c.native_workflow('h2h','h2h_summary_missing',omit={'summary'},reject='native107: h2h')

def D18(c):
    return c.native_workflow('events','root_wrong_id_state',overrides={'root':{'external_key':None}},reject='native107: identity')

def D19(c):
    return c.native_workflow('events','event_team_metadata_missing',omit={'event_team_0'},reject='native107: identity')

def D20(c):
    return c.child_immutability_and_roles()

def D21(c):
    return c.native_workflow('events','events_persisted',commit=True)

def D22(c):
    return c.legacy_closed_profile_and_015_guards()

CASES=[D00,D01,D02,D03,D04,D05,D06,D07,D08,D09,D10,D11,D12,D13,D14,D15,D16,D17,D18,D19,D20,D21,D22]
