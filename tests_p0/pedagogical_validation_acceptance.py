"""P3C read-only acceptance: diagnostics, not pedagogical approval."""
import hashlib
import json
from pathlib import Path
import re
from academic_os.pedagogical_validation import PedagogicalValidationService,validate_pedagogical_contract
from academic_os.pedagogical_service import PedagogicalSpecificationService
from academic_os.learning_service import LearningSpecificationService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p3c_pedagogical_validation');DB=Path('var/p0_q2.sqlite3')


def tests():
    raw=(OUT/'full-suite.txt').read_bytes()
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    match=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
    if not match:raise ValueError('Full suite not complete')
    errors=re.findall(r'^ERROR: (.+)$',text,re.M)
    assert len(errors)==1 and 'test_preserved_project_files' in errors[0]
    assert 'FileNotFoundError' in text and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in text
    assert 'FAILED (errors=1)' in text and not re.search(r'^FAIL:',text,re.M)
    passed=sum(l.endswith(' ... ok') for l in text.splitlines());assert passed==int(match[1])-1
    focused_raw=(OUT/'focused-tests.txt').read_bytes()
    focused=focused_raw.decode('utf-16' if focused_raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    assert 'Ran 40 tests' in focused and focused.strip().endswith('OK')
    groups={}
    for module,n in [('test_pedagogical_validation',40),('test_pedagogical_specification',45),('test_learning_specification',45),('test_assessment_intelligence',40),('test_teacher_product',60)]:
        rows=[l for l in text.splitlines() if re.match(r'test_.*\(tests_p0\.'+module+r'\.',l)]
        assert len(rows)==n and all(l.endswith(' ... ok') for l in rows);groups[module]=n
    return dict(total=int(match[1]),passed=passed,failures=0,errors=1,skipped=0,not_run=0,groups=groups,latest_focused_passed=40,
        duration_seconds=float(match[2]),known_error='FileNotFoundError: AI_Academic_Operating_System_Brainstorm_CN.pptx; original test and pinned hash preserved')


def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'));assert state()==before['database']
    for f,h in before['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
    counts_before=counts();service=PedagogicalValidationService(DB)
    result=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS);v=result.view;serial=v.serialize()
    assert v.structural_coverage.valid and v.reference_integrity.valid and v.boundary_validation.valid and v.slot_validation.valid
    assert v.structural_coverage.learning_planned==3 and v.structural_coverage.coverage_planned==2
    assert v.authoring_readiness.ready_for_content_authoring and not v.authoring_readiness.ready_as_completed_teaching_content
    assert not v.content_readiness.ready and v.content_readiness.required_slots_total==4 and v.content_readiness.populated==0
    assert not v.violations
    assert service.read_topic('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS))).view.serialize()==serial
    p=PedagogicalSpecificationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    l=LearningSpecificationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    assert p.view.serialize().encode()==Path('output/p3b_pedagogical_specification/standard_deviation.json').read_bytes()
    data=p.view.model_dump(mode='json')
    for key in ('teaching_blocks','instructional_content','evidence_boundaries','generator_constraints'):data[key].reverse()
    assert validate_pedagogical_contract(data,l.view).serialize()==serial
    pinned=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    changed=[f for f,h in pinned.items() if Path(f).exists() and hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h]
    missing=[f for f in pinned if not Path(f).exists()];assert not changed and missing==['AI_Academic_Operating_System_Brainstorm_CN.pptx']
    assert state()==before['database'] and counts()==counts_before
    test_results=tests()
    report=dict(status='P3C PEDAGOGICAL CONTRACT VALIDATOR + COVERAGE READINESS PASSED',
        schema_version=v.schema_version,structural_coverage=v.structural_coverage.model_dump(),
        reference_integrity=v.reference_integrity.model_dump(),boundary_validation=v.boundary_validation.model_dump(),slot_validation=v.slot_validation.model_dump(),
        content_readiness=v.content_readiness.model_dump(),authoring_readiness=v.authoring_readiness.model_dump(),
        database_before=before['database'],database_after=state(),counts_before=counts_before,counts_after=counts(),
        new_source_decisions=0,new_academic_decisions=0,new_governance_decisions=0,new_trusted_snapshots=0,
        upstream_files_unchanged=before['files'],pedagogical_output_byte_identical=True,
        snapshot_usability=l.provenance['upstream']['upstream']['snapshot_usability'],protected_files=dict(changed=changed,missing=missing),
        determinism=dict(repeated=True,reversed_snapshots=True,reversed_collections=True,sha256=hashlib.sha256(serial.encode()).hexdigest()),
        test_results=test_results,architectural_notes=[
            'Task-form LR retains worked/practice references when its primary block is removed. Matrix reports those references but marks structural coverage uncovered without its required primary role.',
            'Frozen P3B model treats boundary order as significant. P3C normalizes unordered validation copies only; upstream schema and output remain unchanged.',
            'Frozen candidate_slot has no authored-content representation. Purpose text or a claimed populated status cannot establish readiness.',
            'Boundary text rules are explicit lexical checks, not an arbitrary-language semantic proof; warnings retain this limitation.',
            'Future authored artifact validation and pedagogical quality evaluation are not implemented.'
        ],changed_files=['academic_os/pedagogical_validation.py','academic_os/cli.py','tests_p0/test_pedagogical_validation.py',
            'tests_p0/pedagogical_validation_acceptance.py','docs/P3C_PEDAGOGICAL_VALIDATION.md'])
    (OUT/'standard_deviation.json').write_bytes(serial.encode())
    for name,value in [('provenance',result.provenance),('acceptance',report)]:
        (OUT/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],tests=test_results,database_unchanged=True,authoring_readiness=report['authoring_readiness']),indent=2))


if __name__=='__main__':main()
