"""Deterministic slot proof plus unchanged P5C composition; no model calls."""
from ..content_validation_rules import boundary_findings
from .models import Candidate, Validation
from .numerical import solution, verify_numerical
from .provenance import LEGACY_POLICY, POLICY, require_policy
from .brief import ROLE, TEMPLATES, SCAFFOLDS, compile_brief, current_binding, digest, role, p5c


def task_refs(i):
    return tuple(sorted({s for r in i.learning.learning_requirements if r.type == 'capability_under_task_form'
                         for s in r.source_refs if s.startswith('task-form-')}))


def validate_candidate(raw, i, *, policy=POLICY, controlled_mode=None, controlled_case=None, controlled_case_sha256=None):
    from .controlled import require_context, binding, ControlledValidation
    controlled = dict(controlled_mode=controlled_mode, controlled_case=controlled_case,
                      controlled_case_sha256=controlled_case_sha256)
    case = require_context(**controlled, policy=policy)
    controlled_valid, controlled_reason = None, 'controlled_input_not_evaluated' 
    require_policy(policy)
    provenance_valid = None
    provenance_status = 'NOT_EVALUATED'
    names = ('schema_valid', 'binding_valid', 'content_complete', 'scaffold_valid', 'math_valid',
        'solution_valid', 'expression_semantics_valid', 'scope_valid', 'boundary_valid', 'separation_valid', 'origin_valid', 'composition_valid')
    checks = dict.fromkeys(names, False)
    statuses = dict.fromkeys((*names, 'numeric_encoding', 'derivation_provenance_valid'), 'NOT_EVALUATED')
    if case is not None: statuses['controlled_input_binding_valid'] = 'NOT_EVALUATED'
    errors = []
    summary = {'stage_status': statuses, 'expression_math_verified': False, 'acceptance_policy': policy,
               'expression_policy': 'Controlled SL-10 expressions independently verified; no production rendering.'}
    cid = 'unparsed'
    brief_ref = 'standard-deviation-standard-lesson-SL-10/' + ('4' if case is not None else ('3' if policy == POLICY else '2'))
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
    stage = 'schema_valid'
    try:
        data = raw.model_dump() if isinstance(raw, Candidate) else raw
        if isinstance(data, dict):
            old = data.get('schema_version', 'ai-author-candidate/2') != 'ai-author-candidate/2'
            content = data.get('content', {})
            sol = content.get('proposed_solution', {}) if isinstance(content, dict) else {}
            old = old or (isinstance(sol, dict) and any(isinstance(sol.get(k), str)
                for k in ('first_term', 'second_term', 'mean', 'variance')))
            if old:
                mark('schema_valid', False)
                fail('candidate_contract_version_unsupported')
                raise Halt()
        try:
            c = Candidate.model_validate(data)
        except (ValueError, TypeError):
            mark('schema_valid', False)
            fail('schema_invalid')
            raise Halt()
        mark('schema_valid', True)
        cid = c.candidate_id
        if c.role_ref != ROLE: fail('role_binding_invalid', 'role_ref')
        if case is not None:
            controlled_valid, controlled_reason = binding(case, c.content.proposed_math_inputs)
            statuses['controlled_input_binding_valid'] = 'PASSED' if controlled_valid else 'FAILED'
            if not controlled_valid: fail(controlled_reason)
        stage = 'binding_valid'
        brief = compile_brief(i, policy=policy, **controlled)
        brief_ref = brief.identity
        r = role(i)
        mark('binding_valid', c.brief_ref == brief.identity and c.brief_sha256 == digest(brief)
            and c.current_inputs_sha256 == current_binding(i) and c.role_ref == ROLE)
        mark('scope_valid', c.learning_requirement_refs == r.learning_requirement_refs and c.task_form_refs == task_refs(i))
        mark('origin_valid', c.content_origin == 'ai_generated_candidate')
        content = c.content
        mark('content_complete', bool(content.question_template and content.scaffold_steps))
        mark('scaffold_valid', tuple(s.type for s in content.scaffold_steps) == tuple(SCAFFOLDS)
            and all(s.instruction in SCAFFOLDS[s.type] for s in content.scaffold_steps))
        closed_question = content.question_template in TEMPLATES
        mark('separation_valid', closed_question and checks['scaffold_valid'])
        sol = content.proposed_solution
        texts = [content.question_template, *(s.instruction for s in content.scaffold_steps),
                 *(getattr(sol, k).expression for k in ('first_term','second_term','mean','variance'))]
        mark('boundary_valid', closed_question and checks['scaffold_valid']
             and not any(boundary_findings(t) for t in texts))
        numerical = verify_numerical(c, policy=policy)
        checks.update(numerical['checks'])
        numerical_summary = numerical['summary']
        statuses.update(numerical_summary.pop('stage_status'))
        # Earlier binding failures retain their original diagnostic precedence.
        if 'primary_failure' in numerical_summary:
            summary.setdefault('primary_failure', numerical_summary.pop('primary_failure'))
        if 'failures' in numerical_summary:
            summary.setdefault('failures', []).extend(numerical_summary.pop('failures'))
        summary.update(numerical_summary)
        errors.extend(numerical['errors'])
        provenance_valid = numerical['derivation_provenance_valid']
        provenance_status = numerical['derivation_provenance_status']
        if numerical['halted']: raise Halt()
        if not all(v for k,v in checks.items() if k != 'composition_valid'): raise Halt()
        if policy == POLICY and provenance_valid is not True: raise Halt()
        if case is not None and controlled_valid is not True: raise Halt()
        stage = 'composition_valid'
        baseline = p5c(i)
        decision = [d for d in i.package.role_decisions if d.role_ref == ROLE]
        mark(stage, baseline.renderer_readiness.ready_for_rendering and len(decision) == 1
            and decision[0].decision == 'author_new' and len(decision[0].new_content_refs) == 1
            and r.items.minimum == r.items.target == 1)
        if not checks[stage]: fail('composition_invalid')
        summary['composition_policy'] = 'Unmodified deterministic P5C base plus independently validated one-for-one SL-10 overlay; not a P5C/1 renderer report for AI content.'
        summary['base_p5c_sha256'] = digest(baseline)
    except Halt:
        pass
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, StopIteration):
        if stage in checks: mark(stage, False)
        fail({'math_valid':'mathematical_value_invalid', 'solution_valid':'solution_verification_invalid',
              'composition_valid':'composition_invalid'}.get(stage, 'current_input_invalid'))
    errors.extend(k for k in names if statuses[k] == 'FAILED' and k != 'schema_valid')
    if errors and 'primary_failure' not in summary: summary['primary_failure'] = {'code': errors[0]}
    extra = {} if case is None else dict(controlled_mode=controlled_mode, controlled_case=case,
        controlled_case_sha256=controlled_case_sha256, controlled_input_binding_valid=controlled_valid,
        controlled_input_binding_status='NOT_EVALUATED' if controlled_valid is None else ('PASSED' if controlled_valid else 'FAILED'),
        controlled_input_binding_reason=controlled_reason)
    report_type = Validation if case is None else ControlledValidation
    return report_type(**extra, candidate_id=cid, brief_ref=brief_ref, **checks,
        derivation_provenance_valid=provenance_valid, derivation_provenance_status=provenance_status,
        acceptance_policy=policy,
        accepted=all(checks.values()) and not errors and (policy != POLICY or provenance_valid is True)
            and (case is None or controlled_valid is True),
        violations=tuple(sorted(set(errors))), warnings=('Acceptance is not human approval, publication permission, pedagogy certification or renderer readiness.',
            'Only the controlled SL-10 expression grammar is verified; no general symbolic proof or production rendering.'),
        verification_summary=summary)


def compose(candidate, i, *, policy=POLICY, controlled_mode=None, controlled_case=None, controlled_case_sha256=None):
    """Revalidate instead of accepting a caller-supplied acceptance flag."""
    report = validate_candidate(candidate, i, policy=policy, controlled_mode=controlled_mode,
        controlled_case=controlled_case, controlled_case_sha256=controlled_case_sha256)
    if not report.accepted: raise ValueError('Candidate rejected: '+','.join(report.violations))
    c = Candidate.model_validate(candidate.model_dump() if isinstance(candidate, Candidate) else candidate)
    r = role(i)
    package = i.package.model_dump(mode='json')
    decision = next(d for d in package['role_decisions'] if d['role_ref'] == ROLE)
    old_ref = decision['new_content_refs'][0]
    original = next(q for q in package['new_content'] if q['ref'] == old_ref)
    q = dict(original, ref=c.candidate_id, content_origin='ai_generated_candidate', lineage='validated_ai_candidate',
        question=c.content.question_template.format(**c.content.proposed_math_inputs.model_dump()),
        summary=c.content.proposed_math_inputs.model_dump(), scaffolding=[s.instruction for s in c.content.scaffold_steps])
    s = solution(c).model_dump(mode='json')
    s['content_origin'] = 'ai_generated_candidate'
    package['new_content'] = [q if x['ref'] == old_ref else x for x in package['new_content']]
    package['new_solutions'] = [s if x['item_ref'] == old_ref else x for x in package['new_solutions']]
    decision['new_content_refs'] = [c.candidate_id]
    decision['solution_refs'] = [s['ref']]
    decision['reason'] = 'P6A single-slot candidate accepted by deterministic checks; no academic approval.'
    decision['compatibility'] = {c.candidate_id: {'single_slot_validated': True}}
    package['mathematical_verification'].pop(old_ref, None)
    package['mathematical_verification'][c.candidate_id] = report.verification_summary['mathematics']
    package['schema_version'] = 'experimental-profiled-ai-content/1'
    package['authoring_provider'] = 'single-slot-ai/1'
    package['status'] = 'accepted_candidate_not_renderable'
    package['ready_for_p5c'] = False
    package['ready_for_rendering'] = False
    package['ai_lineage'] = {'candidate_id': c.candidate_id, 'candidate_sha256': digest(c), 'brief_sha256': c.brief_sha256,
        'validation_sha256': digest(report), 'deterministic_base_sha256': digest(i.package), 'role_ref': r.ref}
    return package
