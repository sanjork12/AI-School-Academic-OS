"""Independent content-readiness diagnostics; no authoring implementation implied."""
from .models import LessonAuthoringEligibility
from academic_os.pedagogy_evidence.validation import hash_of

VERSION='approved-pedagogy-lesson-authoring-gate/1'
def requirements(spec, validation):
    valid=validation.valid
    families=spec.approved_evidence.pedagogical_adapter.candidate_role_families if spec.approved_evidence else []
    rows=[dict(key='pedagogical_spec_valid',available=valid),dict(key='approved_evidence_bound',available=valid and spec.approved_evidence is not None),
          dict(key='role_families_determined',available=valid and bool(families)),dict(key='concrete_role_mapping',available=False),
          dict(key='authoring_contract',available=False),dict(key='content_provenance_constraints',available=False)]
    for family in families:rows.append(dict(key=family+'_CONTENT_VALIDATOR',available=False))
    return dict(schema_version='role-content-validation-requirements/1',checks=rows,
        family_contracts={f:dict(status='REQUIRED_NOT_IMPLEMENTED',checks=(['exact approved symbol scope','source/canonical separation','observable representation','proposal and content provenance'] if f=='REPRESENTATION' else ['intention and criterion coverage','observable student evidence','no unreviewed assessment claims','proposal and content provenance'])) for f in families},
        concrete_role_mapping=[],content_generated=False)

def evaluate(spec,validation):
    diagnostic=requirements(spec,validation)
    missing=[r['key'] for r in diagnostic['checks'] if not r['available']]
    return LessonAuthoringEligibility(status='BLOCKED',reason_codes=['ROLE_CONTENT_CONTRACTS_INCOMPLETE'] if validation.valid else ['INVALID_PEDAGOGICAL_SPEC'],
        missing_requirements=missing,warnings=spec.warnings,evidence_refs=spec.eligibility.evidence_refs,
        learning_spec_hash=spec.learning_spec_hash,pedagogical_spec_hash=hash_of(spec),policy_version=VERSION)

def validate_gate(value,spec,validation):
    # Pure gate evaluation, independent of the specification constructor.
    gate=LessonAuthoringEligibility.model_validate(value)
    return dict(valid=gate==evaluate(spec,validation),errors=[] if gate==evaluate(spec,validation) else ['AUTHORING_GATE_CHANGED'])
