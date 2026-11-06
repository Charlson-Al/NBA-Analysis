"""Approved arithmetic only; never change a supplied forecast or select a direction."""
from decimal import Decimal
from math import ceil, floor

from .catalog import COMPONENTS


def number(value):
    return Decimal(str(value))


def normalize(darko, dc_minutes, market):
    """Normalize compatible counts/rates, components first; retain all inputs elsewhere."""
    if dc_minutes is None or dc_minutes <= 0:
        raise ValueError('DC minutes missing')
    if darko['basis'] == 'per_game' and (darko['minutes'] is None or darko['minutes'] <= 0):
        raise ValueError('Original DARKO minutes missing')
    components = COMPONENTS.get(market, (market,))
    if any(stat not in darko['values'] for stat in components):
        raise ValueError('Compatible DARKO components missing')
    values = [number(darko['values'][stat]) * number(dc_minutes) for stat in components]
    if darko['basis'] == 'per_game':
        values = [value / number(darko['minutes']) for value in values]
    return sum(values, Decimal(0))


def exact_line(dc, darko, line, direction):
    a, b, threshold = map(number, (dc, darko, line))
    relation = 'Unresolved' if a == threshold or b == threshold else (
        'Agree Higher' if a > threshold else 'Agree Lower') if (a > threshold) == (b > threshold) else 'Disagree'
    return {'relationship': relation,
            'DC': str(a), 'DARKO_normalized': str(b), 'line': str(threshold),
            'wins': (str(floor(threshold) + 1) + '+') if direction == 'Higher' else
                    (str(ceil(threshold) - 1) + ' or fewer') if direction == 'Lower' else 'No direction',
            'ties': str(threshold) if threshold == threshold.to_integral_value() else 'No integer tie'}
