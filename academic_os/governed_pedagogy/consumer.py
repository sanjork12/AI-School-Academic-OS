"""Exact approved evidence projection, authenticated again at every boundary."""
from typing import Literal
from academic_os.pedagogy_evidence.models import Model, Pack, Criterion, Activity, Check, Adapter
from academic_os.curriculum_ingestion.service import serial
from academic_os.curriculum_ingestion.core import digest
from academic_os.curriculum_ingestion.models import Warning

class ConsumedEvidence(Model):
    schema_version: Literal['approved-pedagogical-evidence-consumer/1'] = 'approved-pedagogical-evidence-consumer/1'
    pack: Pack
    pack_hash: str
    learning_spec_hash: str
    source_id: str
    tier: str
    proposal_hash: str
    review_hash: str
    brief_hash: str
    authoring_policy_version: str
    success_criteria: list[Criterion]
    activity_scope: list[Activity]
    check_alignment: list[Check]
    pedagogical_adapter: Adapter
    warnings: list[Warning]
    mapping: Literal['EXACT_COMPONENT_COPY_NO_SEMANTIC_TRANSFORMATION'] = 'EXACT_COMPONENT_COPY_NO_SEMANTIC_TRANSFORMATION'
    provenance: list[Literal['LEARNING_SPEC_DERIVED','APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY','HUMAN_REVIEWED']]

CLASSES=['LEARNING_SPEC_DERIVED','APPROVED_PEDAGOGICAL_EVIDENCE','DETERMINISTIC_POLICY','HUMAN_REVIEWED']
def hash_of(value):return digest(serial(value))
def authenticate(spec, value, authority):
    from academic_os.pedagogy_evidence.validation import validate_proposal, COMPONENTS
    if authority is None or authority.domain!='HUMAN_REVIEW':raise ValueError('HUMAN_REVIEW_AUTHORITY_REQUIRED')
    pack=Pack.model_validate(value);p=pack.proposal;r=pack.review_receipt
    if not authority.validate_pedagogical_evidence_pack(pack)['valid']:raise ValueError('APPROVED_PACK_INVALID')
    # A caller-supplied or monkey-patched validation boolean is not sufficient.
    if not validate_proposal(p,p.brief,authority.learning)['valid']:raise ValueError('PROPOSAL_INVALID')
    authority._verify_receipt(p,r)
    if r.review.domain!='HUMAN_REVIEW' or [d.component for d in r.review.decisions]!=COMPONENTS or any(d.decision!='APPROVE' for d in r.review.decisions):raise ValueError('ALL_COMPONENT_APPROVAL_REQUIRED')
    if pack.evidence_identity!=hash_of(dict(proposal_hash=hash_of(p),semantic_review_hash=r.semantic_hash)):raise ValueError('PACK_IDENTITY_INVALID')
    if p.brief.learning_spec_hash!=hash_of(spec) or p.brief.source_learning_spec!=spec:raise ValueError('PACK_LEARNING_BINDING_MISMATCH')
    if spec.curriculum_scope.source_ids!=[p.source_id] or spec.curriculum_scope.tier!=p.tier:raise ValueError('PACK_TARGET_TIER_MISMATCH')
    return pack

def consume(spec, value, authority):
    pack=authenticate(spec,value,authority);p=pack.proposal
    return ConsumedEvidence(pack=pack,pack_hash=hash_of(pack),learning_spec_hash=hash_of(spec),source_id=p.source_id,tier=p.tier,
        proposal_hash=hash_of(p),review_hash=pack.review_receipt.semantic_hash,brief_hash=hash_of(p.brief),authoring_policy_version=p.brief.policy_version,
        success_criteria=p.success_criteria,activity_scope=p.activity_scope,check_alignment=p.check_alignment,pedagogical_adapter=p.pedagogical_adapter,
        warnings=spec.warnings,provenance=CLASSES)

def validate_consumed(value,spec,authority):
    """Direct field checks, never calls consume()."""
    from academic_os.pedagogy_evidence.validation import COMPONENTS
    c=ConsumedEvidence.model_validate(value);pack=authenticate(spec,c.pack,authority);p=pack.proposal
    expected=(hash_of(pack),hash_of(spec),p.source_id,p.tier,hash_of(p),pack.review_receipt.semantic_hash,hash_of(p.brief),p.brief.policy_version)
    actual=(c.pack_hash,c.learning_spec_hash,c.source_id,c.tier,c.proposal_hash,c.review_hash,c.brief_hash,c.authoring_policy_version)
    if actual!=expected:raise ValueError('CONSUMER_BINDING_CHANGED')
    for key in COMPONENTS:
        if getattr(c,key)!=getattr(p,key):raise ValueError('CONSUMER_COMPONENT_CHANGED:'+key)
    if c.warnings!=spec.warnings or c.provenance!=CLASSES:raise ValueError('CONSUMER_WARNING_OR_PROVENANCE_CHANGED')
    return c
