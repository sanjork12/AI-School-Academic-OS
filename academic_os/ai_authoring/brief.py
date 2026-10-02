"""Minimal outbound brief, compiled only after existing live contract gates."""
from hashlib import sha256
import json
from ..profiled_content_validation import validate_profiled_content
from .models import AuthoringBrief, ProvenanceBrief
from .provenance import LEGACY_POLICY, POLICY, require_policy

ROLE = 'profiled-sd-standard-lesson-SL-10'
TEMPLATES = (
    'A dataset contains {n} observations. Their sum is {sum_x} and the sum of their squares is {sum_x2}. Calculate the population standard deviation.',
    'For {n} observations, the supplied summary statistics are sum x = {sum_x} and sum x squared = {sum_x2}. Find the population standard deviation.',
)
SCAFFOLDS = {
    'compute_first_term': ('Calculate Σx² / n.', 'Divide the sum of squares by the number of observations.'),
    'compute_second_term': ('Calculate (Σx / n)².', 'Divide the sum by the number of observations, then square the result.'),
    'subtract_variance_terms': ('Subtract the second result from the first.', 'Find the difference: first term minus second term.'),
    'square_root': ('Take the square root.', 'Take the square root of the variance.'),
}


def serial(value):
    if hasattr(value, 'model_dump'): value = value.model_dump(mode='json')
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n'


def digest(value):
    return sha256(serial(value).encode()).hexdigest()


def current_binding(i):
    return digest({k: digest(getattr(i, k)) for k in ('package', 'profile', 'pedagogy', 'authored', 'p4b', 'learning', 'base')})


def role(i):
    if i.profile.identity.profile_key != 'standard-lesson':
        raise ValueError('Only standard-lesson SL-10 is supported')
    matches = [r for r in i.pedagogy.profiled_roles if r.ref == ROLE and r.role_key == 'SL-10']
    if len(matches) != 1 or matches[0].kind != 'guided_practice' or matches[0].support_mode != 'guided':
        raise ValueError('SL-10 contract mismatch')
    return matches[0]


def p5c(i):
    return validate_profiled_content(i.package, i.profile, i.pedagogy, i.authored, i.p4b, i.learning, i.base)


def compile_brief(i, *, policy=POLICY, controlled_mode=None, controlled_case=None, controlled_case_sha256=None):
    from .controlled import require_context, ControlledBrief
    case = require_context(controlled_mode=controlled_mode, controlled_case=controlled_case,
                           controlled_case_sha256=controlled_case_sha256, policy=policy)
    require_policy(policy)
    r = role(i)
    report = p5c(i)
    if not report.renderer_readiness.ready_for_rendering:
        raise ValueError('Current deterministic profile failed P5C')
    targets = tuple(x.statement for x in i.learning.learning_requirements if x.ref in r.learning_requirement_refs)
    if len(targets) != 2: raise ValueError('Expected two existing learning targets')
    formula = next(f for f in i.authored.instructional_formulas if f.ref == 'authored-sd-v1-summary-formula')
    brief = AuthoringBrief(
        profile_context='Standard lesson, guided calculation practice', learning_targets=targets,
        formula=formula.display_expression,
        required_output=('One original feasible set of n, sum_x, sum_x2; use numeric strings for sums.',
                         'Choose one permitted question template verbatim, preserving its placeholders.',
                         'Four ordered scaffold types, with one permitted instruction for each.',
                         'Separate solution with identical inputs. first_term, second_term, mean and variance each require expression and value. Expression is explanatory working (equations allowed); never numeric authority. Value must be a scalar integer, decimal or simple rational literal only. Do not put equations containing =, explanatory text, units, prose or calculation chains into value. BAD: first_term="55/5 = 11"; GOOD: first_term={expression:"55/5",value:"11"}. BAD: variance value="11 - 9 = 2"; GOOD: variance={expression:"11 - 9",value:"2"}. exact_radicand remains an exact scalar. numeric_answer must be a finite decimal within 1e-40 of computed SD (no fixed digit count); display_answer is exactly two decimals, ROUND_HALF_UP.'),
        allowed_question_templates=TEMPLATES, allowed_scaffolds=SCAFFOLDS,
        forbidden_content=('new learning requirements, concepts, competencies or task forms', 'sample standard deviation or n - 1',
            'population/sample comparison', 'difficulty, common-mistake or prerequisite claims', 'frequency, typical marks or exam predictions',
            'formula memorisation', 'calculator models or button sequences', 'Pearson copying or official endorsement',
            'approval, verification, safety, trust or readiness declarations'),
        copyright_policy='Original numerical problem required. No official source wording is supplied. Do not claim copied or official Pearson material.',
        solution_policy='Teacher solution only in proposed_solution; student template and scaffolds must contain no answers. Use the supplied formula without modification.')

    if policy == LEGACY_POLICY:
        return brief
    data = brief.model_dump(exclude={'schema_version', 'identity'})
    data['required_output'] = (*brief.required_output[:3],
        'Separate solution with identical inputs. first_term, second_term, mean and variance each require expression and value. '
        'Preserve operand identity: first_term expression must be sum_x2 / n; second_term must be (sum_x / n)^2; '
        'mean must be sum_x / n; variance must be first term - second term or sum_x2 / n - (sum_x / n)^2. '
        'Use symbolic quantities, not literal substitutions such as 55/5 or 11 - 9. '
        'Existing aliases Σx and Σx², ÷, ², whitespace and redundant parentheses are allowed. '
        'No equations, equality chains, extra operators or self-reference shortcuts. '
        'Value and exact_radicand must be scalar integer, decimal or simple rational strings only. '
        'numeric_answer must be a finite decimal within 1e-40 of computed SD; display_answer is exactly two decimals, ROUND_HALF_UP. '
        'Provenance is independent of numeric semantics and does not grant academic approval or renderer readiness.')
    if case is not None:
        data['required_output'] = (
            'Use exactly the application-owned controlled_case.inputs: n=' + str(case.inputs.n) +
            ', sum_x=' + case.inputs.sum_x + ', sum_x2=' + case.inputs.sum_x2 +
            '. Do not select or replace inputs. Preserve identical input copies in the solution. '
            'Exact rational-equivalent sum encodings are permitted; n must be the same integer.',
            *data['required_output'][1:])
        data['copyright_policy'] = 'Use the supplied numerical case and permitted template. Do not claim copied or official Pearson material.'
        return ControlledBrief(**data, controlled_case=case, controlled_case_sha256=controlled_case_sha256)
    return ProvenanceBrief(**data)
