"""P0 version envelopes around the unchanged v0.3 domain types."""
from typing import Literal
from pydantic import Field
import academic_knowledge_schema_v03 as v3
from validate_academic_knowledge_v03 import digest

class RegisteredSource(v3.SourceDocument):
    curriculum_identity: v3.Text
    version_label: v3.Text
    identity_basis: v3.Text

class LocatedText(v3.SourceLocator):
    source_version: v3.Digest
    extracted_text: v3.Text
    text_digest: v3.Digest
    text_summary: v3.Text
    extraction_method: Literal['pypdf_page_text'] = 'pypdf_page_text'
    extractor_version: v3.Text
    # Whole page extraction preserves layout-defective formula text, never silently repairs it.
    visual_region: list[float] = Field(min_length=4,max_length=4)

class JudgmentScope(v3.Model):
    scope_id: v3.ID
    context_id: v3.ID
    description: v3.Text
    locator_ids: list[v3.ID] = Field(min_length=1)
    official_section_label: str | None = None
    association_status: Literal['candidate','unresolved'] = 'candidate'

class Candidate(v3.Model):
    kind: v3.Text
    payload: dict
    # Extra actually-used scope/context/condition inputs beyond structural v0.3 refs.
    judgment_refs: list[v3.Text] = Field(default_factory=list)

class TextSpan(v3.Model):
    role: Literal['shared_stem','prompt','comparison_context','mark_scheme','mark_scheme_notes']
    locator_id: v3.ID
    locator_version: v3.Digest
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: v3.Text

class ParsedQuestionPart(v3.Model):
    parsed_id: v3.ID
    part_id: v3.ID
    parser_version: v3.Text
    marks: int = Field(gt=0)
    spans: list[TextSpan] = Field(min_length=3)
    warnings: list[v3.Text] = Field(default_factory=list)

class ReusableTaskCondition(v3.Reviewable):
    """Assessment form, independent of the question-specific given values."""
    condition_id: v3.ID
    name: v3.Text
    description: v3.Text
    kind: Literal['input_form', 'comparison_form']

class MappingSemantics(v3.Model):
    role: Literal['primary', 'secondary']
    parsed_part_id: v3.ID
    concept_link_ids: list[v3.ID] = Field(min_length=1)
    task_condition_ids: list[v3.ID] = Field(min_length=1)

class SemanticPartMapping(v3.PartCompetencyMapping):
    semantics: MappingSemantics | None = None

class SemanticProposal(v3.Reviewable):
    """A new question-to-knowledge claim, independent of registry approval."""
    proposal_id: v3.ID
    parsed_part_id: v3.ID
    candidate_action: Literal['reuse_existing','create_candidate','unresolved']
    competency_id: v3.ID | None = None
    concept_ids: list[v3.ID] = Field(default_factory=list)
    concept_link_ids: list[v3.ID] = Field(default_factory=list)
    task_condition_ids: list[v3.ID] = Field(default_factory=list)
    observation: v3.Text
    reasoning: v3.Text
    evidence_scope: v3.Text
    alternatives: list[v3.Text] = Field(default_factory=list)
    registry_lookup: list[dict] = Field(default_factory=list)


MODELS = {
 'proposal':(SemanticProposal,'proposal_id'),
 'source':(RegisteredSource,'source_id'), 'locator':(LocatedText,'locator_id'),
 'context':(v3.CurriculumContext,'context_id'), 'competency':(v3.CanonicalCompetency,'canonical_id'),
 'question':(v3.Question,'question_id'), 'question_part':(v3.QuestionPart,'part_id'),
 'condition':(v3.TaskCondition,'condition_id'), 'evidence':(v3.Evidence,'evidence_id'),
 'part_mapping':(SemanticPartMapping,'mapping_id'), 'scope':(JudgmentScope,'scope_id'),
 'parsed_part':(ParsedQuestionPart,'parsed_id'),
 'concept':(v3.CanonicalConcept,'concept_id'),
 'concept_link':(v3.CompetencyConceptLink,'link_id'),
 'task_condition':(ReusableTaskCondition,'condition_id'),
}

def normalise(raw):
    c=Candidate.model_validate(raw)
    if c.kind not in MODELS: raise ValueError('Unsupported P0 kind: '+c.kind)
    cls,id_field=MODELS[c.kind]; p=cls.model_validate(c.payload).model_dump()
    # Preserve all pre-P1A record hashes; no implicit defaults added to old mappings.
    if c.kind=='part_mapping' and p['semantics'] is None:p.pop('semantics')
    def boundary(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k=='verification_status' and v!='unverified':raise ValueError('Candidate cannot attest verification')
                if k=='review_status' and v!='pending':raise ValueError('Candidate cannot supply academic approval/rejection')
                if k=='status' and v!='draft':raise ValueError('Registry state is operator-owned')
                if k in ('registry_decision_id','review_decision_id','verification_reference') and v is not None:raise ValueError('Candidate review credentials are forbidden')
                boundary(v)
        elif isinstance(x,list):
            for v in x:boundary(v)
    boundary(p)
    if c.kind=='competency' and p.get('action_classification') is not None:
        raise ValueError('P0 does not publish nested action classifications; submit a basic definition')
    if c.kind=='locator':
        if p['page_index'] is None:raise ValueError('PDF page_index is required (zero based)')
        x,y,w,h=p['visual_region']
        if not (0<=x<=1 and 0<=y<=1 and 0<w<=1-x and 0<h<=1-y):raise ValueError('Invalid normalized page region')
        if digest(p['extracted_text'])!=p['text_digest']:raise ValueError('Extracted text digest mismatch')
    key=c.kind+':'+p[id_field]
    value=dict(kind=c.kind,payload=p,judgment_refs=sorted(set(c.judgment_refs)))
    if len(value['judgment_refs'])!=len(c.judgment_refs):raise ValueError('Duplicate judgment reference')
    return key,digest(value),value
