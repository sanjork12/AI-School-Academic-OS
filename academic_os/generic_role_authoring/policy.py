"""Application-owned mapping for the one reviewed symbolic capability."""
from academic_os.curriculum_ingestion.service import serial
from academic_os.curriculum_ingestion.core import digest

MAPPING_VERSION='bounded-symbol-role-mapping/1'
VALIDATION_VERSION='generic-symbolic-role-validation/1'
SYMBOL_MEANINGS={'>':'GREATER_THAN','<':'LESS_THAN','≥':'GREATER_THAN_OR_EQUAL_TO','≤':'LESS_THAN_OR_EQUAL_TO'}
MEANING_LABELS={'GREATER_THAN':'greater than','LESS_THAN':'less than','GREATER_THAN_OR_EQUAL_TO':'greater than or equal to','LESS_THAN_OR_EQUAL_TO':'less than or equal to'}
CONTRACTS={'REPRESENTATION':'representation-role-candidate/1','CONCEPT_CHECK':'concept-check-role-candidate/1'}
PROHIBITED=['SOLVING_INEQUALITIES','NUMBER_LINE_SOLUTIONS','SOLUTION_REGIONS','COMPOUND_OR_QUADRATIC_INEQUALITIES','ALGEBRAIC_MANIPULATION','FREE_FORM_EXPLANATION','EXAM_BANK','HUMAN_APPROVAL_CLAIMS','SOURCE_GLYPH_REPAIR']
PROVENANCE={'source_context':'GOVERNED_SOURCE_CONTEXT','reviewed_canonical':'GOVERNED_SOURCE_CONTEXT','learning_intention':'GOVERNED_SOURCE_CONTEXT','success_criteria':'APPROVED_PEDAGOGICAL_CONSTRAINT','activity_constraints':'APPROVED_PEDAGOGICAL_CONSTRAINT','check_alignments':'APPROVED_PEDAGOGICAL_CONSTRAINT','warnings':'GOVERNED_SOURCE_CONTEXT'}
def hash_of(value):return digest(serial(value))
def role_id(spec,family):
    return 'generic-'+family.lower().replace('_','-')+'-'+hash_of(dict(source=spec.learning_scope.source_ids,tier=spec.learning_scope.tier,pedagogy=hash_of(spec),contract=CONTRACTS[family],mapping=MAPPING_VERSION))
def supported(spec,family):
    """Structural registry check; callers must also independently validate the spec."""
    if family not in CONTRACTS or spec.approved_evidence is None:return False
    if spec.learning_scope.source_ids!=['EDX-4MA1-F-2.8-A'] or spec.learning_scope.tier!='Foundation':return False
    canonical=spec.source_learning_spec.canonical_semantics
    if len(canonical)!=1 or canonical[0].canonical_id!='CAN-ALG-INEQ-SYMBOLS' or canonical[0].description!='Understand and use the symbols >, <, ≥ and ≤.':return False
    c=spec.approved_evidence
    if family not in c.pedagogical_adapter.candidate_role_families:return False
    action='INTERPRET_SYMBOL' if family=='REPRESENTATION' else 'SELECT_SYMBOL'
    mode='SYMBOL_INTERPRETATION' if family=='REPRESENTATION' else 'SYMBOL_SELECTION'
    cs={r.criterion_id:r for r in c.success_criteria}
    activities=[a for a in c.activity_scope if a.category==family and a.response_mode==mode]
    return any(cid in cs and cs[cid].observable_student_action==action and any(k.activity_id==a.activity_id and k.criterion_id==cid and k.evidence_form==mode for k in c.check_alignment) for a in activities for cid in a.criterion_ids)
