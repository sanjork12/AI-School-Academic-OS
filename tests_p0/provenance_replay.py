"""Offline immutable historical replay and separately labelled synthetic controls."""
import copy
import json
from pathlib import Path
from academic_os.ai_authoring.expressions import verify_solution_expressions
from academic_os.ai_authoring.provenance import VERSION, POLICY, STATUSES, verify_solution_provenance
from academic_os.ai_qualification.storage import write_new
from tests_p0.expression_replay import replay as expression_replay, RUN

OUT = Path('output/p6a4_derivation_provenance')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def historical_replay():
    semantics = expression_replay()
    if semantics != read('output/p6a3_expression_verification/replay-report.json'):
        raise ValueError('Frozen P6A.3 replay changed')
    rows = []
    for item in semantics['per_attempt']:
        folder = RUN/item['attempt_id']
        attempt = read(folder/'attempt.json')
        candidate = read(folder/attempt['candidate_artifact_ref'])['candidate']
        provenance = verify_solution_provenance(candidate['content'], historical=True,
                                               semantics=item['expression_semantics'])
        rows.append(dict(attempt_id=item['attempt_id'], candidate_id=candidate['candidate_id'],
                         historically_accepted=attempt['accepted'],
                         expression_semantics=item['expression_semantics'], provenance=provenance))
    checks = [c for row in rows for c in row['provenance']['checks'].values()]
    return dict(schema_version='sl10-provenance-replay/1', verifier_version=VERSION,
                policy=POLICY, source_run_id=RUN.name, candidate_count=len(rows),
                expression_checks=len(checks), historically_accepted=sum(r['historically_accepted'] for r in rows),
                expression_semantics_passed=sum(c['expression_semantics_valid'] is True for c in checks),
                status_counts={s:sum(c['status']==s for c in checks) for s in STATUSES},
                source_artifact_hashes=semantics['source_artifact_hashes'], per_attempt=rows,
                model_provider_calls=0, historical_results_rewritten=False, academic_approval=False,
                renderer_readiness=False)


def symbolic_content(inputs=None):
    from academic_os.ai_qualification.stress import synthetic_content
    from academic_os.ai_authoring.expressions import context_for
    from academic_os.authored_math import summary_stats, display
    c = synthetic_content()
    if inputs is not None:
        c['proposed_math_inputs'] = dict(inputs)
        c['proposed_solution']['inputs'] = dict(inputs)
    _, expected = context_for(c['proposed_math_inputs'])
    expressions = {'first_term':'sum_x2 / n', 'second_term':'(sum_x / n)^2',
                   'mean':'sum_x / n', 'variance':'first term - second term'}
    for field, expression in expressions.items():
        c['proposed_solution'][field] = dict(expression=expression,value=str(expected[field]))
    i = c['proposed_math_inputs']
    _, variance, sd = summary_stats(i['n'],i['sum_x'],i['sum_x2'])
    c['proposed_solution'].update(exact_radicand=str(variance), numeric_answer=str(sd), display_answer=display(sd))
    return c


def controls():
    result = []
    def add(name, content, field=None, expression=None, expected='PASSED', reason='provenance_verified'):
        content = copy.deepcopy(content)
        if field:
            content['proposed_solution'][field]['expression'] = expression
        result.append(dict(name=name, content=content, field=field, expected_status=expected, expected_reason=reason))
    normal = symbolic_content()
    zero = symbolic_content(dict(n=4,sum_x='0',sum_x2='0'))
    collision = symbolic_content(dict(n=4,sum_x='20',sum_x2='116'))
    add('symbolic_all_roles',normal)
    add('unicode_aliases',normal,'second_term','((Σx ÷ n))²')
    add('sum_squares_alias',normal,'first_term','Σx² ÷ n')
    add('expanded_variance',normal,'variance','Σx² / n - (Σx / n)²')
    add('coincident_symbolic',collision)
    add('zero_symbolic',zero)
    for name,field,expression in [('wrong_first_source','first_term','sum_x / n'),
                                  ('wrong_mean_source','mean','sum_x2 / n'),
                                  ('wrong_second_source','second_term','(sum_x2 / n)^2')]:
        add(name,zero,field,expression,'FAILED','provenance_wrong_source')
    add('swapped_variance_zero',zero,'variance','second term - first term','FAILED','provenance_swapped_operands')
    add('constant_first',normal,'first_term','29','FAILED','provenance_literal_source_unidentified')
    add('constant_variance',normal,'variance','4','FAILED','provenance_literal_source_unidentified')
    add('self_first',normal,'first_term','first term','FAILED','provenance_self_reference')
    add('self_second',normal,'second_term','second term','FAILED','provenance_self_reference')
    add('self_variance',normal,'variance','radicand','FAILED','provenance_self_reference')
    add('equal_wrong_denominator',collision,'first_term','sum_x2 / radicand','FAILED','provenance_wrong_source')
    add('equal_literal_denominator',collision,'first_term','sum_x2 / 4','FAILED','provenance_literal_source_unidentified')
    add('zero_literal',zero,'variance','0','FAILED','provenance_literal_source_unidentified')
    add('missing_square',zero,'second_term','sum_x / n','FAILED','provenance_wrong_structure')
    add('unsupported',normal,'mean','sum_x + n','FAILED','provenance_unsupported_for_role')
    add('malformed',normal,'mean','(sum_x / n','FAILED','provenance_unsupported_for_role')
    return result


def symbolic_replay():
    rows = []
    for case in controls():
        semantics = verify_solution_expressions(case['content'])
        provenance = verify_solution_provenance(case['content'],semantics=semantics)
        field = case['field']
        met = provenance['status'] == case['expected_status']
        if field:
            met = met and provenance['checks'][field]['reason'] == case['expected_reason']
        rows.append(dict(**case, expression_semantics=semantics, provenance=provenance, expectation_met=met))
    return dict(schema_version='sl10-symbolic-controls/1',verifier_version=VERSION,policy=POLICY,
                control_count=len(rows),positive_count=sum(r['expected_status']=='PASSED' for r in rows),
                negative_count=sum(r['expected_status']=='FAILED' for r in rows),
                all_expectations_met=all(r['expectation_met'] for r in rows),controls=rows,
                model_provider_calls=0, synthetic_not_historical=True)


def main():
    history=historical_replay();synthetic=symbolic_replay()
    assert history==historical_replay() and synthetic==symbolic_replay()
    assert history['status_counts']==dict(PASSED=0,FAILED=0,INSUFFICIENT_EVIDENCE=40,NOT_EVALUATED=0)
    assert synthetic['all_expectations_met']
    write_new(OUT/'historical-replay.json',history)
    write_new(OUT/'symbolic-controls.json',synthetic)
    print(json.dumps(dict(historical=history['status_counts'],controls=synthetic['control_count'],all_controls_passed=True)))


if __name__ == '__main__':
    main()
