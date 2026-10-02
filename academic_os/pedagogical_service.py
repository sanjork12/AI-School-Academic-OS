"""Fresh learning contract -> candidate pedagogy; no raw snapshot access."""
from dataclasses import dataclass
from .learning_service import LearningSpecificationService
from .pedagogical_core import build_pedagogical_specification
from .pedagogical_models import PedagogicalSpecification


@dataclass(frozen=True)
class PedagogicalRead:
    view:PedagogicalSpecification
    provenance:dict


class PedagogicalSpecificationService:
    def __init__(self,database):self._learning=LearningSpecificationService(database)
    def read_topic(self,topic_key,snapshot_ids):
        upstream=self._learning.read_topic(topic_key,snapshot_ids)
        view=build_pedagogical_specification(upstream.view)
        return PedagogicalRead(view,dict(upstream=upstream.provenance,
            teaching_blocks={b.ref:dict(learning_requirement_refs=list(b.covers_learning_requirement_refs),coverage_requirement_refs=list(b.covers_coverage_requirement_refs),evidence_refs=list(b.evidence_refs)) for b in view.teaching_blocks},
            status='candidate',coverage_status='planned_coverage'))


def pedagogical_specification_text(view):
    lines=[view.identity.title,'Pedagogical Specification','Status: Candidate','Coverage: planned only — not validated',
        'Block order below is not a required teaching sequence.']
    requirements={r.ref:r for r in view.source_learning_specification.learning_requirements}
    contents={c.ref:c for c in view.instructional_content}
    for block in view.teaching_blocks:
        lines.extend(['',block.title,'Covers:'])
        lines.extend(requirements[r].statement for r in block.covers_learning_requirement_refs)
        for c in block.constraints:lines.append(c.level.capitalize()+': '+c.statement)
        for ref in block.instructional_content_refs:
            item=contents[ref];lines.append('Candidate instructional slot: '+item.purpose)
            lines.extend('Evidence/source-quality note: '+n for n in item.source_quality_notes)
    lines.extend(['','Evidence boundaries',*(b.statement for b in view.evidence_boundaries),'',view.trust_boundary])
    return '\n'.join(lines)
