"""SL-11 offline candidate binding and validation over the shared numerical core.

No provider entry point and no production lesson mutation or renderer adapter.
"""
from typing import Literal
from .models import Contract, Candidate, ProviderContent, Metadata
from .brief import TEMPLATES, digest, current_binding
from .controlled import ControlledCase, validate_case, binding
from .provenance import POLICY, VERSION
from .numerical import verify_numerical, solution
from .roles import SL11, FormulaHint, role, support_binding
from .validation import task_refs
from ..content_validation_rules import boundary_findings

CONTROLLED_MODE = 'summary-statistics-controlled-input/1'
ACCEPTANCE_POLICY = 'sl11-numerical-provenance-required/1'
AUTO_SUPPORT = object()


class RoleBrief(Contract):
    schema_version: Literal['numerical-role-authoring-brief/1'] = 'numerical-role-authoring-brief/1'
    identity: Literal['standard-deviation-standard-lesson-SL-11/1'] = 'standard-deviation-standard-lesson-SL-11/1'
    topic: str
    profile: str
    role_ref: str
    semantic_role: str
    learning_targets: tuple[str, ...]
    task_form: Literal['From summary statistics'] = 'From summary statistics'
    support_policy: str
    support_policy_sha256: str
    formula_hint: FormulaHint
    formula_hint_sha256: str
    required_output: tuple[str, ...]
    allowed_question_templates: tuple[str, ...]
    acceptance_policy: str = ACCEPTANCE_POLICY
    mathematical_policy: str = POLICY
    controlled_mode: str | None = None
    controlled_case: ControlledCase | None = None
    controlled_case_sha256: str | None = None


def controlled_context(case=None, case_sha256=None):
    if case is None:
        if case_sha256 is not None: raise ValueError('controlled_case_missing')
        return None
    parsed = validate_case(case)
    if case_sha256 != digest(parsed): raise ValueError('controlled_case_hash_mismatch')
    return parsed


def compile_brief(i, *, controlled_case=None, controlled_case_sha256=None):
    r = role(i)
    hint = support_binding(i)
    case = controlled_context(controlled_case, controlled_case_sha256)
    return RoleBrief(topic=SL11.topic, profile=SL11.profile, role_ref=r.ref, semantic_role=r.kind,
        learning_targets=tuple(lr.statement for lr in i.learning.learning_requirements if lr.ref in r.learning_requirement_refs),
        support_policy=SL11.version, support_policy_sha256=digest(SL11),
        formula_hint=hint, formula_hint_sha256=digest(hint), allowed_question_templates=TEMPLATES,
        required_output=(
            'Return ProviderContent for ai-author-candidate/2. scaffold_steps must be an empty list. Do not author a hint or any scaffold.',
            'Choose one allowed question_template verbatim. Keep all answers in proposed_solution; no student-visible solution.',
            'Use feasible population summary statistics; n is an integer, sums and values are exact scalar numeric strings.',
            'Use symbolic expressions: first_term=sum_x2 / n; second_term=(sum_x / n)^2; mean=sum_x / n; variance=first term - second term or sum_x2 / n - (sum_x / n)^2.',
            'Solution inputs must equal proposed inputs. Provide exact_radicand, finite numeric_answer within 1e-40, and display_answer to two decimals ROUND_HALF_UP.',
            'No new scope, sample SD, difficulty, prerequisite, common-mistake, exam prediction, memorisation, calculator or approval claims.',
            'Use exactly the application-owned controlled_case inputs.' if case else 'Propose one original feasible set of summary statistics.'),
        controlled_mode=CONTROLLED_MODE if case else None, controlled_case=case,
        controlled_case_sha256=digest(case) if case else None)


def role_binding(i, brief):
    return digest(dict(current_inputs=current_binding(i), role=role(i).model_dump(mode='json'), support_policy=SL11.model_dump(),
                       brief_sha256=digest(brief), formula_hint_sha256=brief.formula_hint_sha256))


def bind_candidate(content, i, *, candidate_id, metadata, **context):
    """Application binds identities; content cannot supply role or policy metadata."""
    brief = compile_brief(i, **context)
    return Candidate(candidate_id=candidate_id, brief_ref=brief.identity, brief_sha256=digest(brief),
        current_inputs_sha256=role_binding(i, brief), role_ref=SL11.role_ref,
        learning_requirement_refs=role(i).learning_requirement_refs, task_form_refs=task_refs(i),
        content=ProviderContent.model_validate(content), model_metadata=Metadata.model_validate(metadata))


def validate_candidate(raw, i, *, support=AUTO_SUPPORT, controlled_case=None, controlled_case_sha256=None):
    context = dict(controlled_case=controlled_case, controlled_case_sha256=controlled_case_sha256)
    dimensions = ('schema_valid','binding_valid','role_binding_valid','support_policy_valid','content_complete',
        'scope_valid','boundary_valid','numeric_encoding_valid','math_valid','solution_valid',
        'expression_semantics_valid','separation_valid','composition_valid')
    checks = dict.fromkeys(dimensions, False)
    statuses = dict.fromkeys(dimensions, 'NOT_EVALUATED')
    errors = []
    report = dict(schema_version='numerical-role-validation/1', role_ref=SL11.role_ref,
        semantic_role=SL11.semantic_role, support_policy=SL11.version, acceptance_policy=ACCEPTANCE_POLICY,
        mathematical_policy=POLICY, candidate_contract='ai-author-candidate/2', scaffold_valid=None,
        scaffold_status='NOT_APPLICABLE', derivation_provenance_valid=None,
        derivation_provenance_status='NOT_EVALUATED', controlled_input_binding_valid=None,
        controlled_input_binding_status='NOT_EVALUATED', verification_summary={},
        academic_approval=False, ready_for_rendering=False, publishable=False)
    def mark(name, value, diagnostic=None):
        checks[name] = bool(value)
        statuses[name] = 'PASSED' if value else 'FAILED'
        if not value: errors.append(diagnostic or name)
    try:
        c = Candidate.model_validate(raw.model_dump() if isinstance(raw, Candidate) else raw)
        mark('schema_valid', True)
        report['candidate_id'] = c.candidate_id
        mark('role_binding_valid', c.role_ref == SL11.role_ref, 'role_binding_invalid')
        brief = compile_brief(i, **context)
        expected_hint = brief.formula_hint
        actual_hint = expected_hint if support is AUTO_SUPPORT else support
        try:
            actual_hint = FormulaHint.model_validate(actual_hint.model_dump() if isinstance(actual_hint, FormulaHint) else actual_hint)
            hint_ok = actual_hint == expected_hint
        except (TypeError, ValueError): hint_ok = False
        mark('support_policy_valid', hint_ok and not c.content.scaffold_steps, 'support_policy_invalid')
        if not hint_ok: errors.append('application_formula_hint_missing_or_changed')
        if c.content.scaffold_steps: errors.append('model_authored_scaffold_forbidden')
        brief_ok = c.brief_ref == brief.identity and c.brief_sha256 == digest(brief)
        if not brief_ok: errors.append('brief_binding_invalid')
        policy_ok = c.current_inputs_sha256 == role_binding(i, brief)
        if not policy_ok: errors.append('role_policy_binding_invalid')
        mark('binding_valid', brief_ok and policy_ok and checks['role_binding_valid'])
        report.update(brief=brief.model_dump(mode='json'), brief_sha256=digest(brief),
            support_policy_sha256=digest(SL11), formula_hint=expected_hint.model_dump(mode='json'),
            formula_hint_sha256=digest(expected_hint), candidate_sha256=digest(c))
        mark('scope_valid', c.learning_requirement_refs == role(i).learning_requirement_refs and c.task_form_refs == task_refs(i))
        content = c.content
        mark('content_complete', bool(content.question_template))
        closed = content.question_template in TEMPLATES
        mark('separation_valid', closed and not content.scaffold_steps, 'student_visible_answer_or_support_invalid')
        texts = [content.question_template, *(s.instruction for s in content.scaffold_steps),
                 *(getattr(content.proposed_solution, k).expression for k in ('first_term','second_term','mean','variance'))]
        mark('boundary_valid', closed and not content.scaffold_steps and not any(boundary_findings(t) for t in texts))
        case = brief.controlled_case
        if case:
            ok, reason = binding(case, content.proposed_math_inputs)
            report.update(controlled_input_binding_valid=ok, controlled_input_binding_status='PASSED' if ok else 'FAILED',
                          controlled_input_binding_reason=reason)
            if not ok: errors.append(reason)
        numerical = verify_numerical(c)
        checks.update(numerical['checks'])
        statuses.update(numerical['summary']['stage_status'])
        checks['numeric_encoding_valid'] = statuses['numeric_encoding'] == 'PASSED'
        statuses['numeric_encoding_valid'] = statuses['numeric_encoding']
        report['verification_summary'] = numerical['summary']
        errors.extend(numerical['errors'])
        report.update({k:numerical[k] for k in ('derivation_provenance_valid','derivation_provenance_status')})
        if all(v for k,v in checks.items() if k != 'composition_valid') and numerical['derivation_provenance_valid'] is True and not errors:
            mark('composition_valid', True)
    except (ValueError, TypeError, KeyError, AttributeError, ArithmeticError, StopIteration):
        if not checks['schema_valid']: statuses['schema_valid'] = 'FAILED'
        errors.append('schema_invalid' if not checks['schema_valid'] else 'current_role_context_invalid')
    errors.extend(k for k,v in statuses.items() if v == 'FAILED')
    report.update(checks, stage_status=statuses, violations=sorted(set(errors)),
        accepted=all(checks.values()) and not errors and report['derivation_provenance_valid'] is True)
    return report


def compose(candidate, i, **options):
    report = validate_candidate(candidate, i, **options)
    if not report['accepted']: raise ValueError('SL-11 candidate rejected: '+','.join(report['violations']))
    c = Candidate.model_validate(candidate.model_dump() if isinstance(candidate, Candidate) else candidate)
    return dict(schema_version='experimental-numerical-role-content/1', status='accepted_candidate_not_renderable',
        role_ref=SL11.role_ref, semantic_role=SL11.semantic_role, support_policy=SL11.model_dump(mode='json'),
        support_policy_sha256=digest(SL11), formula_hint=report['formula_hint'], formula_hint_sha256=report['formula_hint_sha256'],
        student_content=dict(question=c.content.question_template.format(**c.content.proposed_math_inputs.model_dump()),
            summary=c.content.proposed_math_inputs.model_dump(), formula_hint_ref=report['formula_hint']['identity']),
        teacher_solution=dict(solution(c).model_dump(mode='json'), content_origin='ai_generated_candidate'),
        solution_visibility=SL11.solution_visibility,
        lineage=dict(candidate_id=c.candidate_id, candidate_sha256=digest(c), brief_ref=c.brief_ref,
            brief_sha256=c.brief_sha256, current_inputs_sha256=c.current_inputs_sha256,
            validation_sha256=digest(report), deterministic_base_sha256=digest(i.package),
            acceptance_policy=ACCEPTANCE_POLICY, provenance_verifier=VERSION),
        academic_approval=False, ready_for_p5c=False, ready_for_rendering=False, publishable=False)
