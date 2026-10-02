"""Fresh upstream services -> learning contract. No trusted database writes."""
from dataclasses import dataclass
from .product_service import AcademicProductService
from .assessment_intelligence import AssessmentIntelligenceService
from .learning_core import build_learning_specification
from .learning_models import LearningSpecification


@dataclass(frozen=True)
class LearningRead:
    view:LearningSpecification
    provenance:dict


class LearningSpecificationService:
    def __init__(self,database):
        self._teacher=AcademicProductService(database)
        self._assessment=AssessmentIntelligenceService(database)

    def read_topic(self,topic_key,snapshot_ids):
        assessment=self._assessment.read_topic(topic_key,snapshot_ids)
        teacher=self._teacher.read_topic(topic_key,snapshot_ids)
        if assessment.provenance['upstream']!=teacher.provenance:
            raise ValueError('Upstream provenance changed between reads; retry with current trusted inputs')
        view=build_learning_specification(teacher.view,assessment.view)
        return LearningRead(view,dict(source_contracts=list(view.source_contracts),upstream=assessment.provenance,
            learning_requirements={r.ref:dict(type=r.type,source_refs=list(r.source_refs),evidence_refs=list(r.evidence_refs)) for r in view.learning_requirements},
            coverage_requirements={r.ref:r.model_dump(mode='json') for r in view.coverage_requirements},
            notice='Derived learning contract, not a new academic approval. Refresh validity through upstream services.'))
