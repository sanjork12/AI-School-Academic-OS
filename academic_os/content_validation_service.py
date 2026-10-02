"""Live read-only authored-content validation boundary; no saved-JSON trust path."""
from dataclasses import dataclass
from .authored_service import AuthoredTeachingService
from .learning_service import LearningSpecificationService
from .pedagogical_service import PedagogicalSpecificationService
from .content_validation import validate_authored_content
from .content_validation_models import AuthoredContentValidationReport


@dataclass(frozen=True)
class ContentValidationRead:
    view:AuthoredContentValidationReport
    provenance:dict


class AuthoredContentValidationService:
    def __init__(self,database):
        self._authored=AuthoredTeachingService(database)
        self._pedagogy=PedagogicalSpecificationService(database)
        self._learning=LearningSpecificationService(database)

    def read_topic(self,topic_key,snapshot_ids):
        authored=self._authored.read_topic(topic_key,snapshot_ids)
        pedagogy=self._pedagogy.read_topic(topic_key,snapshot_ids)
        learning=self._learning.read_topic(topic_key,snapshot_ids)
        if authored.provenance['upstream']['upstream']!=pedagogy.provenance or pedagogy.provenance['upstream']!=learning.provenance:
            raise ValueError('Upstream changed between content validation reads; retry')
        report=validate_authored_content(authored.view,pedagogy.view,learning.view)
        return ContentValidationRead(report,dict(upstream=authored.provenance,current_upstream_validated=True,validation_schema=report.schema_version))


def content_validation_text(report):
    lines=[report.identity['title'],'Authored Content Validation']
    for field in ('reference_integrity','content_completeness','mathematical_integrity','learning_alignment','coverage_requirement_validation','boundary_compliance'):
        lines.append(field.replace('_',' ').capitalize()+': '+('PASS' if getattr(report,field).valid else 'FAIL'))
    lines.append(f'Required slots populated: {sum(s.populated for s in report.slot_population)} / {len(report.slot_population)}')
    lines.append('Ready for rendering: '+('YES' if report.renderer_readiness.ready_for_rendering else 'NO'))
    lines.extend(f'{r.semantic_role}: {r.status}' for r in report.coverage_matrix)
    lines.extend(f'{f.severity} {f.code}: {f.message}' for f in (*report.violations,*report.warnings))
    lines.append('Renderer eligibility only; no academic publication, pedagogical approval or student mastery claim.')
    return '\n'.join(lines)
