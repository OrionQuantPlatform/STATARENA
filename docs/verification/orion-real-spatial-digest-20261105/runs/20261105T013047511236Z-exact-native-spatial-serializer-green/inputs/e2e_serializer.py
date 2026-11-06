#!/usr/bin/env python3
"""Pre-code isolated qualification of the new native spatial byte format only."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from decimal import Decimal, Inexact, Rounded, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import shlex
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
MODULE = HERE / 'spatial_native.py'
POLICY = 'orion_spatial_native_digest_v1'


def require(ok, code):
    if not ok:
        raise AssertionError(code)


def expected(inner):
    return b'["orion_spatial_native_digest_v1",' + inner + b']'


def expected_number(coefficient, exponent):
    return expected(json.dumps(['number', coefficient, exponent], separators=(',', ':')).encode())


def cases(module):
    encode = module.spatial_canonical_bytes
    digest = module.spatial_native_digest

    def numeric_equivalence():
        wanted = expected_number('1', '0')
        for value in [1, Decimal('1'), Decimal('1.00'), Decimal('1E+0')]:
            require(encode(value) == wanted, 'EXACT_NUMBER_BYTES')
            require(digest(value) == hashlib.sha256(wanted).hexdigest(), 'EXACT_NUMBER_SHA')

    def native_scalar_type_separation():
        values = [1, '1', True, 0, '0', False, None, '', 'null']
        require(len({encode(value) for value in values}) == len(values), 'SCALAR_TYPE_COLLISION')
        require(encode(None) == expected(b'["null"]'), 'NULL_TAG')
        require(encode(True) == expected(b'["boolean",true]'), 'BOOL_TAG')
        require(encode('') == expected(b'["string",""]'), 'EMPTY_STRING_TAG')

    def signed_zero():
        wanted = expected_number('0', '0')
        for value in [0, Decimal('0'), Decimal('-0'), Decimal('-0.000'), Decimal('0E-999999')]:
            require(encode(value) == wanted, 'ZERO_VALUE_POLICY')
        require(encode('-0') != wanted and encode('0') != wanted, 'ZERO_STRING_COLLISION')

    def large_integer_precision():
        for digits in ['12345678901234567890123456781', '12345678901234567890123456789123456789123456789']:
            wanted = expected_number(digits, '0')
            require(encode(int(digits)) == wanted and encode(Decimal(digits)) == wanted, 'LARGE_INTEGER_EXACT')
        require(encode(Decimal('12345678901234567890123456781')) != encode(Decimal('12345678901234567890123456782')), 'LAST_DIGIT_LOST')

    def fractional_precision():
        wanted = expected_number('123456789012345678901234567891', '-30')
        require(encode(Decimal('0.123456789012345678901234567891')) == wanted, 'FRACTION_DIGITS_LOST')
        require(encode(Decimal('0.123456789012345678901234567891')) != encode(Decimal('0.123456789012345678901234567892')), 'FRACTION_LAST_DIGIT_LOST')

    def compact_exponents():
        require(encode(Decimal('1.2300E-1000000')) == expected_number('123', '-1000002'), 'SMALL_EXPONENT')
        require(encode(Decimal('1000E+1000000')) == expected_number('1', '1000003'), 'LARGE_EXPONENT')
        require(encode(1000) == encode(Decimal('1E3')), 'TRAILING_ZERO_EQUIVALENCE')

    def decimal_context_independence():
        value = Decimal('12345678901234567890123456781.123456789012345678901')
        wanted = expected_number('12345678901234567890123456781123456789012345678901', '-21')
        for precision in [1, 28, 100]:
            with localcontext() as context:
                context.prec = precision
                context.traps[Inexact] = True
                context.traps[Rounded] = True
                require(encode(value) == wanted, 'DECIMAL_CONTEXT_CHANGED_BYTES')

    def unicode_codepoints():
        value = 'é⚽\n"\\'
        wanted = expected('["string","é⚽\\n\\\"\\\\"]'.encode('utf-8'))
        require(encode(value) == wanted, 'UNICODE_UTF8_OR_ESCAPE')
        require(encode('é') != encode('e\u0301'), 'UNREQUESTED_UNICODE_NORMALIZATION')

    def ordered_arrays():
        require(encode((Decimal('1'), None, [])) == encode([1, None, ()]), 'TUPLE_LIST_EQUIVALENCE')
        require(encode([1, 2]) != encode([2, 1]), 'ARRAY_ORDER_LOST')
        require(len({encode(value) for value in [[], None, '', [[]], {}]}) == 5, 'ARRAY_STATE_COLLISION')

    def metadata_objects():
        wanted = expected(b'["object",[["a",["number","1","0"]],["b",["null"]]]]')
        require(encode({'b': None, 'a': Decimal('1.00')}) == wanted, 'OBJECT_SORT_OR_TAG')
        require(encode({'a': 1, 'b': None}) == wanted, 'OBJECT_NUMBER_EQUIVALENCE')
        try:
            encode({1: 'synthetic_metadata'})
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError('NONSTRING_KEY_ACCEPTED')

    def spatial_shaped_tuples():
        source = [('/data/players/synthetic', ('synthetic_team', 'synthetic_player', 'home', Decimal('16'), Decimal('12'), Decimal('6.5625'), Decimal('5.6666666666666666666666666667'), 'home_ltr', Decimal('9'), 'available'), [(Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'))])]
        typed = [('/data/players/synthetic', ('synthetic_team', 'synthetic_player', 'home', 16, 12, Decimal('6.562500'), Decimal('5.6666666666666666666666666667'), 'home_ltr', 9, 'available'), [(0, 0, 0, 0)])]
        require(encode(source) == encode(typed) and digest(source) == digest(typed), 'NESTED_SPATIAL_NUMERIC_IDENTITY')
        require(encode([Decimal('1')]) != encode(['1']) and encode([Decimal('1')]) != encode([True]), 'NESTED_SCALAR_TYPE_COLLISION')

    def rejected_types():
        values = [Decimal('NaN'), Decimal('sNaN'), Decimal('Infinity'), Decimal('-Infinity'), 1.0, 0.5, float('nan'), b'synthetic', {1}, object()]
        for value in values:
            try:
                encode(value)
            except (TypeError, ValueError) as error:
                require(str(error) in {'Unsupported spatial native type', 'Spatial number must be finite', 'Spatial object keys must be strings'}, 'ERROR_MAY_ECHO_VALUE')
            else:
                raise AssertionError('UNSUPPORTED_TYPE_ACCEPTED')

    def tag_framing_and_sha():
        value = [Decimal('1.0'), '1', True, None]
        wanted = expected(b'["array",[["number","1","0"],["string","1"],["boolean",true],["null"]]]')
        require(encode(value) == wanted, 'EXPLICIT_TAGGED_BYTES')
        require(digest(value) == hashlib.sha256(wanted).hexdigest(), 'DIGEST_NOT_EXACT_BYTES')
        require(len({digest(value) for value in [1, '1', ['number', '1', '0'], {'number': '1'}]}) == 4, 'TAG_SHAPE_COLLISION')
        require(module.SPATIAL_DIGEST_POLICY == POLICY, 'UNBOUND_POLICY')

    return [(f.__name__, f) for f in [numeric_equivalence, native_scalar_type_separation, signed_zero, large_integer_precision, fractional_precision, compact_exponents, decimal_context_independence, unicode_codepoints, ordered_arrays, metadata_objects, spatial_shaped_tuples, rejected_types, tag_framing_and_sha]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    if not re.fullmatch('[a-zA-Z0-9][a-zA-Z0-9-]{0,79}', args.label):
        parser.error('Use a bounded evidence label')
    run = HERE / 'runs' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + args.label)
    inputs = run / 'inputs'
    inputs.mkdir(parents=True)
    files = [Path(__file__), HERE / 'PROTOCOL.md'] + ([MODULE] if MODULE.exists() else [])
    for path in files:
        shutil.copy2(path, inputs / path.name)
    report = {'kind': 'new_spatial_serializer_isolated_contract_v1', 'command': shlex.join([sys.executable, *sys.argv]), 'scope': 'New serializer only; explicit synthetic constants in test input; no existing SQL oracle unit/mock', 'expected': str(HERE / 'PROTOCOL.md'), 'inputs': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}, 'cases': [], 'sqlInstructions': 0, 'postgresStarts': 0, 'cloudCalls': 0, 'ramReads': 0, 'rawBodiesPersisted': False, 'fullAcceptance': False}
    module = None
    try:
        spec = importlib.util.spec_from_file_location('new_spatial_native', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        require(callable(module.spatial_canonical_bytes) and callable(module.spatial_native_digest), 'MISSING_NEW_API')
        report['cases'].append({'case': 'new_serializer_available', 'status': 'pass'})
    except Exception as error:
        report['cases'].append({'case': 'new_serializer_available', 'status': 'fail', 'errorType': type(error).__name__, 'expected': 'New serializer exists and exposes the two pure APIs'})
    if module is None or report['cases'][0]['status'] != 'pass':
        for name, _ in cases(type('Unavailable', (), {'spatial_canonical_bytes': None, 'spatial_native_digest': None})()):
            report['cases'].append({'case': name, 'status': 'unverified', 'reason': 'New serializer unavailable'})
    else:
        for name, function in cases(module):
            try:
                function()
                report['cases'].append({'case': name, 'status': 'pass'})
            except Exception as error:
                report['cases'].append({'case': name, 'status': 'fail', 'errorType': type(error).__name__})
    report['counts'] = {status: sum(row['status'] == status for row in report['cases']) for status in ['pass', 'fail', 'unverified']}
    report['status'] = 'pass' if report['counts'] == {'pass': 14, 'fail': 0, 'unverified': 0} else 'fail'
    (run / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'evidence': str(run / 'result.json')}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
