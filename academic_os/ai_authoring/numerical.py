"""Shared summary-statistics verification; no role, support, provider or rendering authority."""
import re
from ..authored_math import rational, summary_stats, verify_solution, solution_steps
from ..authored_models import SummaryStatistics
from ..profiled_content_models import NewSolution
from .expressions import verify_solution_expressions
from .provenance import POLICY, require_policy, verify_solution_provenance


def solution(candidate):
    content = candidate.content
    s = content.proposed_solution
    summary = SummaryStatistics(**content.proposed_math_inputs.model_dump())
    return NewSolution(ref=candidate.candidate_id+'-solution', item_ref=candidate.candidate_id,
        mean=s.mean.value, variance=s.variance.value, exact_answer={'op': 'sqrt', 'radicand': s.exact_radicand},
        numeric_answer=s.numeric_answer, display_answer=s.display_answer, method_steps=solution_steps(summary))


def verify_numerical(c, *, policy=POLICY):
    require_policy(policy)
    names = ('math_valid', 'solution_valid', 'expression_semantics_valid')
    checks = dict.fromkeys(names, False)
    statuses = dict.fromkeys((*names, 'numeric_encoding', 'derivation_provenance_valid'), 'NOT_EVALUATED')
    summary = {'stage_status': statuses, 'expression_math_verified': False}
    errors = []
    provenance_valid, provenance_status = None, 'NOT_EVALUATED'
    stage = 'numeric_encoding'
    halted = False
    def mark(key, value):
        checks[key] = bool(value)
        statuses[key] = 'PASSED' if value else 'FAILED'
    def fail(code, field=None):
        errors.append(code)
        detail = {'code': code}
        if field: detail['field'] = field
        summary.setdefault('primary_failure', detail)
        summary.setdefault('failures', []).append(detail)
    class Halt(Exception): pass
    content, sol = c.content, c.content.proposed_solution
    try:
        inputs = content.proposed_math_inputs
        stage = 'numeric_encoding'
        numbers = {'proposed_math_inputs.sum_x': inputs.sum_x, 'proposed_math_inputs.sum_x2': inputs.sum_x2,
                   'proposed_solution.inputs.sum_x': sol.inputs.sum_x, 'proposed_solution.inputs.sum_x2': sol.inputs.sum_x2}
        numbers.update({k+'.value': getattr(sol,k).value for k in ('first_term','second_term','mean','variance')})
        numbers.update({k: getattr(sol,k) for k in ('exact_radicand','numeric_answer','display_answer')})
        for field, value in numbers.items():
            if len(value) > 128 or not re.fullmatch(r'-?\d+(?:\.\d+|/\d+)?', value, re.ASCII):
                statuses[stage] = 'FAILED'
                fail('numeric_encoding_invalid', field)
                raise Halt()
        if inputs.n > 1000000 or sol.inputs.n > 1000000:
            statuses[stage] = 'FAILED'
            fail('numeric_encoding_invalid', 'n')
            raise Halt()
        statuses[stage] = 'PASSED'
        stage = 'math_valid'
        mean, variance, sd = summary_stats(inputs.n, inputs.sum_x, inputs.sum_x2)
        mark(stage, True)
        stage = 'expression_semantics_valid'
        expression_report = verify_solution_expressions(content.model_dump(mode='json'))
        summary['expressions'] = expression_report
        mark(stage, expression_report['expression_semantics_valid'])
        summary['expression_math_verified'] = checks[stage]
        if not checks[stage]:
            for field, item in expression_report['checks'].items():
                if not item['valid']: fail(item['reason'], field+'.expression')
        if policy == POLICY:
            stage = 'derivation_provenance_valid'
            provenance = verify_solution_provenance(content.model_dump(mode='json'), semantics=expression_report)
            summary['provenance'] = provenance
            provenance_valid = provenance['derivation_provenance_valid']
            provenance_status = provenance['status']
            statuses[stage] = provenance_status
            if provenance_valid is not True:
                for field, item in provenance['checks'].items():
                    if item['valid'] is not True: fail(item['reason'], field+'.expression')
        stage = 'solution_valid'
        if sol.inputs != inputs:
            mark(stage, False); fail('solution_verification_invalid', 'proposed_solution.inputs'); raise Halt()
        expected = {'first_term': rational(inputs.sum_x2)/inputs.n, 'second_term': mean*mean,
                    'mean': mean, 'variance': variance}
        for field, value in expected.items():
            try: equal = rational(getattr(sol,field).value) == value
            except ArithmeticError: equal = False
            except ValueError: equal = False
            if not equal:
                mark(stage, False); fail('mathematical_value_invalid', field+'.value'); raise Halt()
        check = verify_solution(SummaryStatistics(**inputs.model_dump()), solution(c))
        summary['mathematics'] = check.model_dump(mode='json')
        mark(stage, check.status == 'verified')
        if not checks[stage]:
            field = next((name for key, name in (('exact_answer_recomputed','exact_radicand'),
                ('numeric_answer_recomputed','numeric_answer'), ('rounding_recomputed','display_answer'))
                if check.checks.get(key) is False), None)
            fail('solution_verification_invalid', field); raise Halt()
    except Halt:
        halted = True
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, StopIteration):
        if stage in checks: mark(stage, False)
        fail({'math_valid':'mathematical_value_invalid', 'solution_valid':'solution_verification_invalid'}.get(stage, 'current_input_invalid'))
        halted = True
    return dict(checks=checks, summary=summary, errors=errors, halted=halted,
        derivation_provenance_valid=provenance_valid, derivation_provenance_status=provenance_status)
