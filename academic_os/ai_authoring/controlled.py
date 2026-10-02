"""Application-owned request binding, orthogonal to derivation provenance.

The hash binds the original case representation; candidate sums compare as exact
rationals. Neither this module nor its callers normalize candidate strings.
"""
import re
from types import MappingProxyType
from typing import Literal
from .models import Contract, Inputs, ProvenanceBrief, Validation
from .provenance import POLICY
from ..authored_math import rational, summary_stats

MODE = 'sl10-controlled-input/1'


class ControlledCase(Contract):
    controlled_case_id: str
    inputs: Inputs


class ControlledBrief(ProvenanceBrief):
    schema_version: Literal['authoring-brief/4'] = 'authoring-brief/4'
    identity: Literal['standard-deviation-standard-lesson-SL-10/4'] = 'standard-deviation-standard-lesson-SL-10/4'
    controlled_mode: Literal['sl10-controlled-input/1'] = MODE
    controlled_case: ControlledCase
    controlled_case_sha256: str


class ControlledValidation(Validation):
    controlled_mode: Literal['sl10-controlled-input/1'] = MODE
    controlled_case: ControlledCase
    controlled_case_sha256: str
    controlled_input_binding_valid: bool | None
    controlled_input_binding_status: Literal['PASSED', 'FAILED', 'NOT_EVALUATED']
    controlled_input_binding_reason: str


def validate_case(value):
    # Reparse even frozen instances: model_copy/model_construct can bypass validation.
    case = ControlledCase.model_validate(value.model_dump() if hasattr(value, 'model_dump') else value)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', case.controlled_case_id):
        raise ValueError('controlled_case_id_invalid')
    i = case.inputs
    if type(i.n) is not int or not 1 <= i.n <= 1000000:
        raise ValueError('controlled_case_n_invalid')
    for value in (i.sum_x, i.sum_x2):
        if len(value) > 128 or not re.fullmatch(r'-?\d+(?:\.\d+|/\d+)?', value, re.ASCII):
            raise ValueError('controlled_case_encoding_invalid')
        rational(value)
    summary_stats(i.n, i.sum_x, i.sum_x2)
    return case


def require_context(*, controlled_mode=None, controlled_case=None, controlled_case_sha256=None, policy=POLICY):
    from .brief import digest
    if controlled_mode is None:
        if controlled_case is not None or controlled_case_sha256 is not None:
            raise ValueError('controlled_mode_missing')
        return None
    if controlled_mode != MODE or policy != POLICY:
        raise ValueError('controlled_mode_or_policy_invalid')
    if controlled_case is None or controlled_case_sha256 is None:
        raise ValueError('controlled_context_missing')
    case = validate_case(controlled_case)
    if controlled_case_sha256 != digest(case):
        raise ValueError('controlled_case_hash_mismatch')
    return case


def context(case):
    from .brief import digest
    case = validate_case(case)
    return dict(controlled_mode=MODE, controlled_case=case, controlled_case_sha256=digest(case))


def binding(case, inputs):
    try:
        value = Inputs.model_validate(inputs.model_dump() if hasattr(inputs, 'model_dump') else inputs)
        if value.n != case.inputs.n:
            return False, 'controlled_input_n_mismatch'
        for key in ('sum_x', 'sum_x2'):
            actual = getattr(value, key)
            if len(actual) > 128 or not re.fullmatch(r'-?\d+(?:\.\d+|/\d+)?', actual, re.ASCII):
                return False, 'controlled_input_encoding_invalid'
            if rational(actual) != rational(getattr(case.inputs, key)):
                return False, 'controlled_input_' + key + '_mismatch'
        return True, 'controlled_inputs_match'
    except (ValueError, TypeError, ArithmeticError):
        return False, 'controlled_input_encoding_invalid'


# Source triples only. Derived expectations always come from existing mathematics.
CATALOG = MappingProxyType({key: validate_case(dict(controlled_case_id=key,
    inputs=dict(n=n, sum_x=sx, sum_x2=sx2))) for key, n, sx, sx2 in (
    ('A', 10, '50', '290'), ('B', 4, '10', '29'), ('C', 4, '8', '18'),
    ('D', 3, '4', '6'), ('E', 1, '-3', '9'),
    ('F', 1000000, '1000000000', '1000001000000'),
    ('G', 2, '1/3', '5/81'), ('H', 2, '0.21', '0.0441'))})
