"""Profile adapter for the existing presentation manifest, never an author."""
from dataclasses import dataclass
from typing import Literal
from .presentation_models import PresentationManifest, ManifestSlide
from .presentation_manifest import build_manifest, sha
from .profiled_content_validation import validate_profiled_content
from .profiled_pedagogy import digest


class ProfileSlide(ManifestSlide):
    profile_role_refs: tuple[str, ...]
    student_visible_refs: tuple[str, ...]
    layout_variant: str


class ProfileManifest(PresentationManifest):
    schema_version: Literal['presentation-manifest/2'] = 'presentation-manifest/2'
    slides: tuple[ProfileSlide, ...]
    profile_key: str
    profile_title: str
    target_duration_minutes: int
    academic_scope_fingerprint: str
    role_coverage: dict[str, tuple[str, ...]]
    target_density_attained: bool


@dataclass(frozen=True)
class ProfileInputs:
    package: object
    report: object
    profile: object
    pedagogy: object
    authored: object
    p4b: object
    learning: object
    base: object


NEW_LAYOUTS = {
    'early_concept_retrieval': ('quick_retrieval', 'Concept retrieval'),
    'mini_worked_example': ('mini_worked', 'Mini worked example'),
    'full_worked_examples': ('profile_worked', 'Worked example'),
    'guided_practice': ('guided_practice', 'Guided practice'),
    'independent_practice': ('profile_practice', 'Independent practice'),
    'exit_check': ('exit_calculation', 'Exit check'),
}


def gate(i):
    current = validate_profiled_content(i.package, i.profile, i.pedagogy, i.authored, i.p4b, i.learning, i.base)
    if current != i.report or not current.renderer_readiness.ready_for_rendering or current.violations:
        raise ValueError('Current P5C rendering gate is closed or its input binding is stale')
    return current


def same_scope(inputs):
    scopes = {(i.package.academic_scope_fingerprint,
               tuple(sorted(i.package.learning_requirement_refs)),
               tuple(sorted(i.package.coverage_requirement_refs)),
               tuple(b.model_dump_json() for b in i.package.evidence_boundaries),
               digest(i.learning)) for i in inputs.values()}
    if len(scopes) != 1:
        raise ValueError('Profile academic scopes differ; rendering refused')


def build_profile_manifest(i):
    gate(i)
    original = build_manifest(i.authored, i.p4b, i.learning, 'standard-deviation-classroom/2')
    by_block = {ref: s for s in original.slides for ref in s.content_refs
                if any(b.ref == ref for b in i.authored.content_blocks)}
    questions = {q.ref: q for q in i.package.new_content}
    solutions = {s.item_ref: s for s in i.package.new_solutions}
    decisions = {d.role_ref: d for d in i.package.role_decisions}
    roles = i.pedagogy.profiled_roles
    slides = []

    def add(kind, title, visible, lrs, role_refs, teacher=(), variant=None):
        n = len(slides) + 1
        slides.append(ProfileSlide(ref=f'{i.package.profile_key}-slide-{n:02}', slide_number=n,
            slide_type=kind, title=title, content_refs=tuple(visible),
            student_visible_refs=tuple(visible), learning_requirement_refs=tuple(lrs),
            teacher_only_refs=tuple(teacher), profile_role_refs=tuple(role_refs),
            layout_intent='classroom-v2/' + (variant or kind), layout_variant=variant or kind))

    framing = tuple(r.ref for r in roles if not r.substantive)
    add('title_learning_goals', 'Standard Deviation', (), original.slides[0].learning_requirement_refs, framing)
    for role in roles:
        if not role.substantive:
            continue
        d = decisions[role.ref]
        for ref in d.reused_content_refs:
            s = by_block[ref]
            add(s.slide_type, s.title, s.content_refs, s.learning_requirement_refs, (role.ref,), s.teacher_only_refs)
        for ref in d.new_content_refs:
            q = questions[ref]; sol = solutions[ref]
            kind, title = NEW_LAYOUTS[q.semantic_role]
            visible = [ref]; teacher = [sol.ref]
            if q.semantic_role in ('mini_worked_example', 'full_worked_examples'):
                visible.append(sol.ref); teacher = []
            if q.semantic_role == 'full_worked_examples':
                visible.extend(next(b for b in i.authored.content_blocks if b.kind == 'summary_statistics_method').formula_refs)
            if q.semantic_role == 'exit_check':
                add('exit_concept', 'Exit check', (ref,), q.concept_learning_requirement_refs, (role.ref,), teacher)
                add(kind, title, visible, q.calculation_learning_requirement_refs, (role.ref,), teacher)
            else:
                add(kind, title, visible, q.learning_requirement_refs, (role.ref,), teacher)
    closure = tuple(r.ref for r in roles if r.kind == 'exit_check')
    add('learning_summary', 'Summary', (), original.slides[-1].learning_requirement_refs, closure)
    refs = {r for s in slides for r in s.content_refs + s.teacher_only_refs}
    visibility = {r: ('teacher_sidecar_only' if any(r in s.teacher_only_refs for s in slides) else 'student_worked_example')
        for r in refs if r in {sol.ref for sol in (*i.authored.solutions, *i.package.new_solutions)}}
    roles_covered = {r.ref: tuple(s.ref for s in slides if r.ref in s.profile_role_refs) for r in roles}
    if not all(roles_covered.values()):
        raise ValueError('Required profile role missing from presentation')
    return ProfileManifest(identity=dict(topic_key='standard-deviation', title='Standard Deviation', profile='profile-classroom/1'),
        profile_key=i.package.profile_key, profile_title=i.profile.identity.title,
        target_duration_minutes=i.profile.duration.target_minutes,
        academic_scope_fingerprint=i.package.academic_scope_fingerprint,
        target_density_attained=i.report.density_validation.target_attainment,
        slides=tuple(slides), role_coverage=roles_covered,
        content_coverage={r: tuple(s.ref for s in slides if r in s.content_refs + s.teacher_only_refs) for r in sorted(refs)},
        solution_visibility=visibility, render_constraints=original.render_constraints,
        source_validation=dict(original.source_validation, profiled_content_sha256=digest(i.package),
            profiled_validation_sha256=digest(i.report), profiled_pedagogy_sha256=digest(i.pedagogy), lesson_profile_sha256=digest(i.profile)))


def validate_profile_manifest(manifest, inputs):
    if manifest != build_profile_manifest(inputs):
        raise ValueError('Profile manifest differs from current validated mapping, visibility or bindings')


def profile_teacher_solutions(i, manifest):
    objects = {s.ref: s for s in (*i.authored.solutions, *i.package.new_solutions)}
    return dict(schema_version='presentation-teacher-solutions/2', profile_key=manifest.profile_key,
        source_validation=manifest.source_validation,
        solutions={ref: dict(solution=objects[ref].model_dump(mode='json'),
            item_ref=objects[ref].item_ref,
            profile_role_refs=sorted({r for slide in manifest.slides if ref in slide.content_refs + slide.teacher_only_refs for r in slide.profile_role_refs}),
            visibility=visibility) for ref, visibility in manifest.solution_visibility.items()})
