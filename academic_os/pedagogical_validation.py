"""Read-only contract diagnostics. No authored content or pedagogical quality claims."""
from dataclasses import dataclass
import json
import re
from typing import Literal
from pydantic import ValidationError
from .product_models import ProductModel
from .learning_models import LearningSpecification
from .learning_service import LearningSpecificationService
from .pedagogical_models import PedagogicalSpecification,SourceLearningContract,EvidenceReference
from .pedagogical_service import PedagogicalSpecificationService


class Finding(ProductModel):
    severity:Literal['ERROR','WARNING','INFO']
    code:str
    ref:str
    message:str


class Check(ProductModel):
    valid:bool


class CoverageRow(ProductModel):
    requirement_ref:str
    kind:Literal['learning_requirement','coverage_requirement']
    covered_by_block_refs:tuple[str,...]
    required_role:str
    coverage_status:Literal['covered','uncovered']


class StructuralCoverage(Check):
    learning_total:int
    learning_planned:int
    coverage_total:int
    coverage_planned:int


class ContentReadiness(ProductModel):
    ready:Literal[False]=False
    required_slots_total:int
    populated:int=0
    unpopulated:tuple[str,...]
    slot_types:dict[str,str]
    reason:str='Frozen candidate_slot objects contain specification instructions, not authored and validated content.'


class AuthoringReadiness(ProductModel):
    ready_for_content_authoring:bool
    ready_as_completed_teaching_content:Literal[False]=False


class SlotValidation(Check):
    required_roles:tuple[str,...]
    missing_roles:tuple[str,...]


class PedagogicalValidationReport(ProductModel):
    schema_version:Literal['pedagogical-validation/1']='pedagogical-validation/1'
    identity:dict
    input_contracts:tuple[str,...]
    structural_coverage:StructuralCoverage
    reference_integrity:Check
    boundary_validation:Check
    slot_validation:SlotValidation
    content_readiness:ContentReadiness
    authoring_readiness:AuthoringReadiness
    violations:tuple[Finding,...]
    warnings:tuple[Finding,...]
    coverage_matrix:tuple[CoverageRow,...]
    trust_summary:dict

    def serialize(self):return json.dumps(self.model_dump(mode='json'),ensure_ascii=False,sort_keys=True,indent=2)+'\n'


PRIMARY_ROLES={'conceptual_understanding':'conceptual_meaning','capability':'calculation_method',
    'capability_under_task_form':'supported_task_form','teaching_assessment_connection':'worked_assessment_connection',
    'assessment_alignment':'practice_learning_check'}
SLOT_TYPES={'calculation_method':'calculation_method_slot','supported_task_form':'task_input_slot',
    'worked_assessment_connection':'worked_example_slot','practice_learning_check':'learning_check_slot'}


def _unordered(value):
    if isinstance(value,dict):return {k:_unordered(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return sorted((_unordered(v) for v in value),key=lambda v:json.dumps(v,sort_keys=True))
    return value


def validate_pedagogical_contract(candidate,learning):
    """Pure diagnostics on isolated inputs; only the service establishes current trust."""
    source=LearningSpecification.model_validate(learning)
    data=candidate.model_dump(mode='json') if isinstance(candidate,PedagogicalSpecification) else candidate
    errors=[];warnings=[];categories=set()
    def error(category,code,ref,message):
        categories.add(category);errors.append(Finding(severity='ERROR',code=code,ref=str(ref),message=message))
    if not isinstance(data,dict):data={}
    shape_invalid=False
    try:PedagogicalSpecification.model_validate(_unordered(data))
    except ValidationError as exc:
        shape_invalid=any(e['loc'] for e in exc.errors())
        error('schema','contract_schema_invalid','contract','Candidate does not satisfy the frozen pedagogical-specification/1 schema or its internal consistency checks.')
    if data.get('schema_version')!='pedagogical-specification/1':error('schema','unsupported_schema','contract','Expected pedagogical-specification/1.')
    def rows(value):return [x for x in value if isinstance(x,dict)] if isinstance(value,(list,tuple)) else []
    def refs(value):return tuple(x for x in value if isinstance(x,str)) if isinstance(value,(list,tuple)) else ()
    blocks=rows(data.get('teaching_blocks'));contents=rows(data.get('instructional_content'))
    learning_rows={r.ref:r for r in source.learning_requirements};coverage_rows={r.ref:r for r in source.coverage_requirements}
    evidence={e.ref:e for e in source.assessment_evidence};boundaries={b.ref:b for b in source.evidence_boundaries}
    products={s for r in source.learning_requirements for s in r.source_refs}
    registry={r:'learning_requirement' for r in learning_rows}|{r:'coverage_requirement' for r in coverage_rows}|{r:'evidence' for r in evidence}|{r:'boundary' for r in boundaries}|{r:'product' for r in products}
    for kind,items in [('block',blocks),('content',contents)]:
        for item in items:
            ref=item.get('ref')
            if not isinstance(ref,str) or not ref.strip():error('references','invalid_identity',kind,'Identity must be a nonempty string.');continue
            if ref in registry:error('references','duplicate_or_colliding_ref',ref,'Identity collides with another entity.')
            registry[ref]=kind
    def check_refs(owner,field,allowed):
        for ref in refs(owner.get(field)):
            if ref not in allowed:error('references','wrong_kind_ref' if ref in registry else 'broken_ref',owner.get('ref',field),field+' does not resolve to the required entity kind: '+ref)
    embedded=data.get('source_learning_specification')
    if isinstance(embedded,dict):
        capability_refs={e.capability_ref for e in source.assessment_evidence}
        task_refs={t for e in source.assessment_evidence for t in e.task_form_refs}
        for e in rows(embedded.get('assessment_evidence')):
            check_refs(e,'task_form_refs',task_refs)
            cap=e.get('capability_ref')
            if not isinstance(cap,str) or cap not in capability_refs:
                error('references','wrong_kind_ref' if isinstance(cap,str) and cap in registry else 'broken_ref',e.get('ref','evidence'),'Evidence capability_ref does not resolve to an upstream capability.')
    content_by_ref={c['ref']:c for c in contents if isinstance(c.get('ref'),str)}
    for b in blocks:
        for field,allowed in [('covers_learning_requirement_refs',learning_rows),('covers_coverage_requirement_refs',coverage_rows),('evidence_refs',evidence),('boundary_refs',boundaries),('instructional_content_refs',content_by_ref)]:check_refs(b,field,allowed)
    for c in contents:
        for field,allowed in [('supports_learning_requirement_refs',learning_rows),('assesses_learning_requirement_refs',learning_rows),('evidence_refs',evidence),('source_product_refs',products)]:check_refs(c,field,allowed)
        supported=[learning_rows[r] for r in refs(c.get('supports_learning_requirement_refs')) if r in learning_rows]
        allowed_products={s for r in supported for s in r.source_refs};allowed_evidence={e for r in supported for e in r.evidence_refs}
        if not set(refs(c.get('source_product_refs')))<=allowed_products or not set(refs(c.get('evidence_refs')))<=allowed_evidence:
            error('references','instructional_alignment_mismatch',c.get('ref','content'),'Instructional Product/evidence refs must support the declared learning requirements.')
        if not set(refs(c.get('assesses_learning_requirement_refs')))<=set(refs(c.get('supports_learning_requirement_refs'))):error('references','learning_check_alignment_mismatch',c.get('ref','content'),'Assessment refs must be supported by this slot.')
        if any(r not in products for r in refs(c.get('source_product_refs'))):error('boundaries','unsupported_task_form',c.get('ref','content'),'An unsupported Product/task ref cannot be a required learning target.')
    expected=SourceLearningContract(identity=source.identity,conceptual_basis=source.conceptual_basis,
        learning_requirements=source.learning_requirements,coverage_requirements=source.coverage_requirements,
        evidence_boundaries=source.evidence_boundaries,assessment_evidence=tuple(EvidenceReference(**e.model_dump(include=set(EvidenceReference.model_fields))) for e in source.assessment_evidence))
    if _unordered(data.get('source_learning_specification'))!=_unordered(expected.model_dump(mode='json')):
        error('boundaries','upstream_learning_changed','source_learning_specification','Embedded learning content or evidence differs from the current upstream contract.')
    if _unordered(data.get('evidence_boundaries'))!=_unordered([b.model_dump(mode='json') for b in source.evidence_boundaries]):
        error('boundaries','evidence_boundaries_changed','evidence_boundaries','Every upstream evidence boundary must be preserved exactly.')
    # Bounded lexical rules, not an NLP proof. Split contrast clauses so a preceding
    # negation cannot suppress an affirmative claim after "but" or "however".
    rules={
        'formula_memorisation':r'(?:must|required to|need to|shall)\s+(?:be able to\s+)?memori[sz]e|formula.{0,35}memori[sz]ation.{0,20}(?:required|mandatory)',
        'calculator_method':r'(?:must|required to|shall).{0,65}(?:calculator|button sequence)|calculator[- ]only|specific calculator.{0,35}(?:required|mandatory)',
        'difficulty':r'\b(?:easy|medium|hard|introductory|advanced)[- ]difficulty\b|difficulty\s*(?:is|:|=)\s*(?:easy|medium|hard|introductory|advanced)|\b(?:easy|medium|hard|introductory|advanced)\s+(?:topic|question|task|lesson)',
        'common_mistakes':r'students commonly|common mistakes?|typical misconceptions?',
        'prerequisites':r'must be mastered (?:first|before)|(?:is|as|a) (?:formal )?prerequisite|prerequisite\s*:',
        'teaching_sequence':r'sequence.{0,30}academically required|academically required.{0,30}(?:sequence|order)',
        'frequency':r'frequently tested|commonly tested|high frequency|low frequency|often appears|rarely appears',
        'typical_marks':r'usually\s+\d+\s+marks|typically (?:worth )?\d+\s+marks',
        'exam_prediction':r'likely to appear|expected next year|will appear.{0,25}exam',
        'unsupported_task_form':r'(?:must|required to).{0,40}(?:all possible|every possible|another|additional|unsupported) task forms?|(?:must|required|calculate).{0,80}(?:raw data|frequency table|grouped data)',
    }
    def scan(text,ref):
        if not isinstance(text,str):return
        for clause in re.split(r'[.;\n]|\bbut\b|\bhowever\b|\band\b',text.lower()):
            negative=bool(re.search(r'\b(?:not|never|neither|without|no)\b',clause))
            for code,pattern in rules.items():
                if re.search(pattern,clause) and not negative:error('boundaries',code,ref,'Unsupported boundary claim detected: '+clause.strip())
    for item in blocks+contents:
        ref=item.get('ref','item')
        for field in ('title','purpose'):scan(item.get(field),ref)
        for c in rows(item.get('constraints')):scan(c.get('statement'),ref)
        if item.get('formula_memorisation_required') is True:error('boundaries','formula_memorisation',ref,'Formula memorisation is not an established learning requirement.')
    for c in rows(data.get('generator_constraints')):scan(c.get('statement'),'generator_constraints')
    matrix=[];required_slots=set()
    for kind,requirements,field in [('learning_requirement',learning_rows,'covers_learning_requirement_refs'),('coverage_requirement',coverage_rows,'covers_coverage_requirement_refs')]:
        for ref,r in sorted(requirements.items()):
            role=PRIMARY_ROLES[r.type]
            citing=[b for b in blocks if ref in refs(b.get(field))]
            primary=[b for b in citing if b.get('role')==role]
            if not primary:
                error('structure','missing_required_role',ref,'Planned references alone are insufficient; required role missing: '+role)
            matrix.append(CoverageRow(requirement_ref=ref,kind=kind,covered_by_block_refs=tuple(sorted(set(b['ref'] for b in citing if isinstance(b.get('ref'),str)))),required_role=role,coverage_status='covered' if primary else 'uncovered'))
    for b in blocks:
        role=b.get('role');ref=b.get('ref','block')
        if not any(c.get('level')=='required' for c in rows(b.get('constraints'))):error('slots','missing_required_constraint',ref,'Required pedagogical function has no required constraint.')
        if isinstance(role,str) and role in SLOT_TYPES:
            matching=[content_by_ref[r] for r in refs(b.get('instructional_content_refs')) if r in content_by_ref and content_by_ref[r].get('type')==SLOT_TYPES[role]]
            if not matching:error('slots','required_slot_missing',ref,'Missing required content slot: '+SLOT_TYPES[role])
            for c in matching:
                required_slots.add(c['ref'])
                if not isinstance(c.get('purpose'),str) or not c['purpose'].strip():error('slots','slot_instruction_missing',c['ref'],'An authoring slot needs a nonempty specification instruction.')
                if not set(refs(b.get('covers_learning_requirement_refs')))<=set(refs(c.get('supports_learning_requirement_refs'))):error('slots','slot_support_incomplete',c['ref'],'Slot must support all learning requirements declared by its block.')
                if role=='practice_learning_check' and set(refs(c.get('assesses_learning_requirement_refs')))!=set(refs(b.get('covers_learning_requirement_refs'))):error('slots','learning_check_targets_missing',c['ref'],'Learning check must declare the learning requirements it assesses.')
    if 'structure' in categories:categories.add('slots')
    declared=data.get('coverage_map') if isinstance(data.get('coverage_map'),dict) else {}
    for name,requirements,field in [('learning_requirements',learning_rows,'covers_learning_requirement_refs'),('coverage_requirements',coverage_rows,'covers_coverage_requirement_refs')]:
        actual={r:sorted(b['ref'] for b in blocks if r in refs(b.get(field)) and isinstance(b.get('ref'),str)) for r in requirements}
        if _unordered(declared.get(name))!=_unordered(actual):error('references','coverage_map_mismatch',name,'Declared map does not match block references.')
    if declared.get('status')!='planned_coverage':error('structure','coverage_completion_overclaim','coverage_map','Only planned coverage is supported.')
    warnings.append(Finding(severity='WARNING',code='content_unpopulated',ref='instructional_content',message='Required slots are instructions only; frozen candidate_slot has no authored-content representation.'))
    warnings.append(Finding(severity='WARNING',code='bounded_text_rules',ref='boundary_validation',message='Boundary text checks cover explicit rule patterns, not arbitrary-language semantic proof. Future authored content still requires content-level review.'))
    valid=lambda category:category not in categories and not shape_invalid
    lr=[r for r in matrix if r.kind=='learning_requirement'];cr=[r for r in matrix if r.kind=='coverage_requirement']
    identity=source.identity.model_dump();identity['view_type']='pedagogical_validation'
    ordered=lambda values:tuple(sorted(set((v.code,v.ref,v.message,v.severity) for v in values)))
    clean=lambda values:tuple(Finding(code=c,ref=r,message=m,severity=s) for c,r,m,s in ordered(values))
    return PedagogicalValidationReport(identity=identity,input_contracts=('learning-specification/1','pedagogical-specification/1'),
        structural_coverage=StructuralCoverage(valid=valid('structure'),learning_total=len(lr),learning_planned=sum(r.coverage_status=='covered' for r in lr),coverage_total=len(cr),coverage_planned=sum(r.coverage_status=='covered' for r in cr)),
        reference_integrity=Check(valid=valid('references')),boundary_validation=Check(valid=valid('boundaries')),slot_validation=SlotValidation(valid=valid('slots'),required_roles=tuple(sorted({r.required_role for r in matrix})),missing_roles=tuple(sorted({r.required_role for r in matrix if r.coverage_status=='uncovered'}))),
        content_readiness=ContentReadiness(required_slots_total=len(required_slots),unpopulated=tuple(sorted(required_slots)),slot_types={r:str(content_by_ref[r].get('type','unknown')) for r in sorted(required_slots)}),
        authoring_readiness=AuthoringReadiness(ready_for_content_authoring=not errors),violations=clean(errors),warnings=clean(warnings),coverage_matrix=tuple(matrix),
        trust_summary=dict(trust_basis='Caller must supply current service-validated inputs; pure validation does not authenticate JSON.',pedagogical_approval=False,content_level_validation_implemented=False))


@dataclass(frozen=True)
class ValidationRead:
    view:PedagogicalValidationReport
    provenance:dict


class PedagogicalValidationService:
    def __init__(self,database):
        self._pedagogy=PedagogicalSpecificationService(database);self._learning=LearningSpecificationService(database)
    def read_topic(self,topic_key,snapshot_ids):
        pedagogy=self._pedagogy.read_topic(topic_key,snapshot_ids);learning=self._learning.read_topic(topic_key,snapshot_ids)
        if pedagogy.provenance['upstream']!=learning.provenance:raise ValueError('Upstream changed between validation reads; retry')
        view=validate_pedagogical_contract(pedagogy.view,learning.view)
        return ValidationRead(view,dict(upstream=pedagogy.provenance,current_upstream_validated=True,validation_schema=view.schema_version))


def validation_text(view):
    s=view.structural_coverage
    lines=[view.identity['title'],'Pedagogical Contract Validation',
        f'Structural coverage: {"PASS" if s.valid else "FAIL"}',f'Learning Requirements: {s.learning_planned} / {s.learning_total} planned',f'Coverage Requirements: {s.coverage_planned} / {s.coverage_total} planned',
        'Reference integrity: '+('PASS' if view.reference_integrity.valid else 'FAIL'),
        'Evidence boundaries: '+('PASS' if view.boundary_validation.valid else 'FAIL'),
        'Required slot structure: '+('PASS' if view.slot_validation.valid else 'FAIL'),
        f'Content readiness: INCOMPLETE ({view.content_readiness.populated} / {view.content_readiness.required_slots_total} required slots populated)',
        'Ready for content authoring: '+('YES' if view.authoring_readiness.ready_for_content_authoring else 'NO'),
        'Ready as completed teaching content: NO']
    lines.extend(f'{f.severity} {f.code}: {f.message}' for f in (*view.violations,*view.warnings))
    lines.extend(['','Required pedagogical roles',*(r.replace('_',' ')+(': MISSING' if r in view.slot_validation.missing_roles else ': represented') for r in view.slot_validation.required_roles),
        '', 'Unpopulated required authoring slots',*(view.content_readiness.slot_types[r].replace('_',' ') for r in view.content_readiness.unpopulated)])
    return '\n'.join(lines)
