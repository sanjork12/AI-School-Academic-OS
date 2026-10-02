"""Application-owned role policy for the first numerical role extension."""
from typing import Literal
from .models import Contract
from .brief import digest, p5c


class NumericalRolePolicy(Contract):
    version: Literal['sl11-single-formula-hint/1'] = 'sl11-single-formula-hint/1'
    topic: Literal['standard-deviation'] = 'standard-deviation'
    profile: Literal['standard-lesson'] = 'standard-lesson'
    role_ref: Literal['profiled-sd-standard-lesson-SL-11'] = 'profiled-sd-standard-lesson-SL-11'
    semantic_role: Literal['guided_practice'] = 'guided_practice'
    support_mode: Literal['guided'] = 'guided'
    support_owner: Literal['application'] = 'application'
    support_model: Literal['single_formula_hint'] = 'single_formula_hint'
    model_scaffold_count: Literal[0] = 0
    solution_visibility: Literal['teacher_sidecar_only'] = 'teacher_sidecar_only'


SL11 = NumericalRolePolicy()
HINT = 'Use σ = sqrt(Σx² / n - (Σx / n)²).'


class FormulaHint(Contract):
    identity: Literal['sl11-application-formula-hint/1'] = 'sl11-application-formula-hint/1'
    owner: Literal['application'] = 'application'
    text: Literal['Use σ = sqrt(Σx² / n - (Σx / n)²).'] = HINT
    source_ref: str
    source_field: Literal['scaffolding/0'] = 'scaffolding/0'
    source_sha256: str
    formula_ref: Literal['authored-sd-v1-summary-formula'] = 'authored-sd-v1-summary-formula'
    formula_sha256: str


def role(i):
    if i.profile.identity.profile_key != SL11.profile:
        raise ValueError('SL-11 profile mismatch')
    matches = [r for r in i.pedagogy.profiled_roles if r.ref == SL11.role_ref]
    if len(matches) != 1:
        raise ValueError('SL-11 role missing or ambiguous')
    r = matches[0]
    if (r.role_key != 'SL-11' or r.kind != SL11.semantic_role or r.support_mode != SL11.support_mode
            or r.items.minimum != 1 or r.items.target != 1):
        raise ValueError('SL-11 role policy mismatch')
    return r


def support_binding(i):
    role(i)
    report = p5c(i)
    if report.violations or not report.renderer_readiness.ready_for_rendering:
        raise ValueError('Current deterministic base failed P5C')
    decisions = [d for d in i.package.role_decisions if d.role_ref == SL11.role_ref]
    if len(decisions) != 1 or decisions[0].decision != 'author_new' or len(decisions[0].new_content_refs) != 1:
        raise ValueError('SL-11 source decision mismatch')
    q = next(q for q in i.package.new_content if q.ref == decisions[0].new_content_refs[0])
    if q.scaffolding != (HINT,) or q.support_mode != 'guided' or q.semantic_role != 'guided_practice':
        raise ValueError('Application formula hint missing or changed')
    f = next(f for f in i.authored.instructional_formulas if f.ref == 'authored-sd-v1-summary-formula')
    return FormulaHint(source_ref=q.ref, source_sha256=digest(q), formula_sha256=digest(f))
