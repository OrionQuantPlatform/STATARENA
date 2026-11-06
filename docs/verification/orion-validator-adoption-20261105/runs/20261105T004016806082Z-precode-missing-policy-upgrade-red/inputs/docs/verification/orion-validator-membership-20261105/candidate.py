"""Pure local validator overlay. Never changes a frozen helper or migration file."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
MODEL_SHA = '18da43f940870b7a3a3cb49323c847dd5e5174e5eea1f8ff0c8a159cf373cb08'
SQL_SHA = '85525221cad51b32aff79a777098211b4112f9f00ea7161ac93945654eeb6968'


def compile_candidate(model_path, sql_path):
    model_bytes, sql_bytes = Path(model_path).read_bytes(), Path(sql_path).read_bytes()
    assert hashlib.sha256(model_bytes).hexdigest() == MODEL_SHA
    assert hashlib.sha256(sql_bytes).hexdigest() == SQL_SHA
    model = json.loads(model_bytes)
    tables = {t['qualified_name']: t for s in model['schemas'] for t in s['tables'] if t['phase'] != 'models'}
    sys.path.insert(0, str(ROOT / 'dashboard/scripts'))
    import orion_pro_integrity as original
    source = sql_bytes.decode()
    assert original.integrity_sql(model, tables) == source, 'Default compiler is not the sealed013 producer'
    start = source.index('CREATE OR REPLACE FUNCTION "ingest"."validate_generation"(')
    end = source.index('$orion_pro$;', start) + len('$orion_pro$;')
    function = source[start:end]
    clauses = original._membership_checks(tables, model['selective_versioning'].get('append_only_revision_rules', {}))
    metadata = []; pairs = []
    rules = model['selective_versioning'].get('append_only_revision_rules', {})
    for child_name, child in tables.items():
        if original._selected(child, 'child', 'g', tables, rules) is None: continue
        for fk in child['foreign_keys']:
            parent = tables[fk['references']['table']]
            if parent['write_mode'] != 'immutable_values_close_interval_once': continue
            if child_name == 'ingest.public_aliases' and parent['qualified_name'] == 'football.player_profile_versions': continue
            columns = list(dict.fromkeys(parent['versioning']['logical_key'] + sorted(original._MEMBERSHIP.intersection(parent['columns']))))
            pairs.append((child_name, parent, fk, columns))
    assert len(pairs) == len(clauses) == 81
    changed = retained = 0; old_query = new_query = None
    for old, (child, parent, fk, columns) in zip(clauses, pairs):
        assert old in function and function.count(old) == 1
        rewritten = old; comparisons = []
        for column in columns:
            before = f'selected_parent."{column}" IS NOT DISTINCT FROM anchor."{column}"'
            assert old.count(before) == 1
            nullable = parent['columns'][column]['nullable']
            if nullable:
                retained += 1; operator = 'IS NOT DISTINCT FROM'
            else:
                rewritten = rewritten.replace(before, f'selected_parent."{column}" = anchor."{column}"')
                changed += 1; operator = '='
            comparisons.append({'column': column, 'nullable': nullable, 'operator': operator})
        function = function.replace(old, rewritten, 1)
        metadata.append({'child': child, 'parent': parent['qualified_name'], 'foreignKey': fk['name'], 'comparisons': comparisons})
        if child == 'football.player_match_metric_values' and parent['qualified_name'] == 'football.match_players':
            prefix = 'IF EXISTS ('
            old_query = old[len(prefix):old.index(') THEN RAISE')]
            new_query = rewritten[len(prefix):rewritten.index(') THEN RAISE')]
    assert changed == 139 and retained == 46 and old_query and new_query
    return {'kind': 'local_membership_nullable_candidate_v1', 'modelSha256': MODEL_SHA, 'sealed013Sha256': SQL_SHA,
            'changedNonNullComparisons': changed, 'retainedNullableComparisons': retained, 'membershipChecks': metadata,
            'original_query': old_query, 'candidate_query': new_query, 'sql': function}
