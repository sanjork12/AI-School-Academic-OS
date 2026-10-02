"""P3C authoring gate -> explicit deterministic provider -> authored candidate."""
from dataclasses import dataclass
from .pedagogical_validation import PedagogicalValidationService
from .pedagogical_service import PedagogicalSpecificationService
from .authored_sd import author_standard_deviation
from .authored_models import AuthoredTeachingPackage

PROVIDERS={'standard-deviation':author_standard_deviation}


@dataclass(frozen=True)
class AuthoredRead:
    view:AuthoredTeachingPackage
    provenance:dict


class AuthoredTeachingService:
    def __init__(self,database):
        self._validation=PedagogicalValidationService(database)
        self._pedagogy=PedagogicalSpecificationService(database)
    def read_topic(self,topic_key,snapshot_ids):
        if topic_key not in PROVIDERS:raise ValueError('No deterministic authoring provider registered for this topic')
        validation=self._validation.read_topic(topic_key,snapshot_ids)
        if not validation.view.authoring_readiness.ready_for_content_authoring:raise ValueError('P3C authoring gate is closed')
        pedagogy=self._pedagogy.read_topic(topic_key,snapshot_ids)
        if validation.provenance['upstream']!=pedagogy.provenance:raise ValueError('Upstream changed between authoring reads; retry')
        view=PROVIDERS[topic_key](pedagogy.view,validation.view)
        return AuthoredRead(view,dict(upstream=validation.provenance,authoring_provider=view.authoring_provider,
            content={b.ref:dict(teaching_block_refs=list(b.teaching_block_refs),slot_refs=list(b.instructional_slot_refs),learning_requirement_refs=list(b.covers_learning_requirement_refs+b.assesses_learning_requirement_refs),origin=b.origin) for b in view.content_blocks}))


def authored_text(view):
    lines=[view.identity.title,'Authored Teaching Content','Status: authored_candidate',
        'Provider: '+view.authoring_provider,f'Content blocks: {len(view.content_blocks)}',
        f'Slots supplied: {sum(r.populated for r in view.coverage_summary.values())} / {len(view.coverage_summary)}',
        'Mathematical verification: '+('VERIFIED' if view.verification_summary.mathematical_checks_passed else 'FAILED')]
    for block in view.content_blocks:
        lines.extend(['',block.kind.replace('_',' ').title(),block.text])
        if block.visual:lines.append(block.visual.brief)
    for question in (*view.worked_examples,*view.practice_items,*view.learning_checks):lines.extend(['',question.kind.replace('_',' ').title(),question.question])
    lines.extend(['','Teacher solutions (separate from question objects)'])
    for solution in view.solutions:
        if solution.expected_meaning:lines.append(solution.expected_meaning)
        else:lines.extend(solution.method_steps)
    lines.extend(['',view.trust_boundary])
    return '\n'.join(lines)
