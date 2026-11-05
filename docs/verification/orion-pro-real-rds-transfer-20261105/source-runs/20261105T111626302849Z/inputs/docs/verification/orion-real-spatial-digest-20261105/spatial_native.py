"""Exact typed byte format for the independent spatial oracle, not ingestion."""
from __future__ import annotations
from decimal import Decimal
import hashlib
import json

SPATIAL_DIGEST_POLICY = 'orion_spatial_native_digest_v1'


def _number(value):
    value = value if type(value) is Decimal else Decimal(value)
    if not value.is_finite():
        raise ValueError('Spatial number must be finite')
    sign, digits, exponent = value.as_tuple()
    if not any(digits):
        return ['number', '0', '0']
    end = len(digits)
    while digits[end - 1] == 0:
        end -= 1
        exponent += 1
    coefficient = ''.join(str(digit) for digit in digits[:end])
    if sign:
        coefficient = '-' + coefficient
    return ['number', coefficient, str(exponent)]


def _tagged(value):
    if value is None:
        return ['null']
    if type(value) is bool:
        return ['boolean', value]
    if type(value) in (int, Decimal):
        return _number(value)
    if type(value) is str:
        return ['string', value]
    if type(value) in (list, tuple):
        return ['array', [_tagged(item) for item in value]]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError('Spatial object keys must be strings')
        return ['object', [[key, _tagged(value[key])] for key in sorted(value)]]
    raise TypeError('Unsupported spatial native type')


def spatial_canonical_bytes(value):
    return json.dumps([SPATIAL_DIGEST_POLICY, _tagged(value)], ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def spatial_native_digest(value):
    return hashlib.sha256(spatial_canonical_bytes(value)).hexdigest()
