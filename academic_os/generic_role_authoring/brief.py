from .models import Brief,Binding
from .policy import CONTRACTS,PROHIBITED,PROVENANCE,hash_of,role_id,supported
from academic_os.governed_pedagogy.models import GovernedPedagogicalSpecification

def binding(spec,family):
    c=spec.approved_evidence
    return Binding(role_id=role_id(spec,family),role_family=family,source_id=c.source_id,tier=c.tier,pedagogical_spec_hash=hash_of(spec),learning_spec_hash=c.learning_spec_hash,
        approved_pack_id=c.pack.evidence_identity,approved_pack_hash=c.pack_hash,proposal_hash=c.proposal_hash,review_hash=c.review_hash,contract_version=CONTRACTS[family])

def build_brief(value,family,pedagogy_service):
    spec=GovernedPedagogicalSpecification.model_validate(value)
    if not pedagogy_service.validate_pedagogical_spec(spec).valid or not supported(spec,family):raise ValueError('ROLE_CONTEXT_NOT_SUPPORTED')
    c=spec.approved_evidence
    acts=[a for a in c.activity_scope if a.category==family]
    ids={i for a in acts for i in a.criterion_ids};aid={a.activity_id for a in acts}
    return Brief(binding=binding(spec,family),governed_spec=spec,source_context=spec.source_learning_spec.learning_objectives[0],reviewed_canonical=spec.source_learning_spec.canonical_semantics[0],learning_intention=spec.source_learning_spec.learning_intentions[0],
        success_criteria=[r for r in c.success_criteria if r.criterion_id in ids],activity_constraints=acts,check_alignments=[r for r in c.check_alignment if r.activity_id in aid and r.criterion_id in ids],
        allowed_modes=sorted({a.response_mode for a in acts}),prohibited_content=PROHIBITED,warnings=spec.warnings,provenance=PROVENANCE)
