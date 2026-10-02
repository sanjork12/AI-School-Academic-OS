"""P4B read-only acceptance; no approvals or upstream output regeneration."""
import hashlib
import json
from pathlib import Path
import re
from academic_os.content_validation_service import AuthoredContentValidationService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p4b_authored_content_validation')


def log(name):
    raw=(OUT/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')


def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for file,h in before['files'].items():assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==h,file
    old_counts=counts();service=AuthoredContentValidationService(Path('var/p0_q2.sqlite3'))
    result=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS);v=result.view
    assert service.read_topic('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS))).view.serialize()==v.serialize()
    assert v.renderer_readiness.ready_for_rendering and not v.violations
    for field in ('reference_integrity','content_completeness','mathematical_integrity','learning_alignment','coverage_requirement_validation','boundary_compliance'):assert getattr(v,field).valid
    assert len(v.slot_population)==4 and all(s.populated for s in v.slot_population)
    assert len(v.coverage_matrix)==5
    assert sum(r.status=='covered' for r in v.coverage_matrix)==3
    assert sum(r.status=='satisfied' for r in v.coverage_matrix)==2
    assert len(v.verification_summary)==7 and all(c.status=='verified' for c in v.verification_summary.values())
    authored=Path('output/p4a_authored_teaching_content/standard_deviation.json')
    assert v.input_contracts['authored-teaching-content/1']==hashlib.sha256(authored.read_bytes()).hexdigest()
    pins=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    changed=[f for f,h in pins.items() if Path(f).exists() and hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h]
    missing=[f for f in pins if not Path(f).exists()]
    assert not changed and missing==['AI_Academic_Operating_System_Brainstorm_CN.pptx']
    full=log('full-suite.txt');match=re.search(r'Ran (\d+) tests in ([\d.]+)s',full)
    assert match and 'FAILED (errors=1)' in full and not re.search(r'^FAIL:',full,re.M)
    errors=re.findall(r'^ERROR: (.+)$',full,re.M)
    assert len(errors)==1 and 'test_preserved_project_files' in errors[0]
    assert 'FileNotFoundError' in full and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in full
    passed=sum(l.endswith(' ... ok') for l in full.splitlines());assert passed==int(match[1])-1
    assert 'Ran 57 tests' in log('focused-tests.txt') and log('focused-tests.txt').strip().endswith('OK')
    assert 'Ran 78 tests' in log('baseline-tests.txt') and log('baseline-tests.txt').strip().endswith('OK')
    assert state()==before['database'] and counts()==old_counts
    report=dict(status='P4B renderer-readiness acceptance passed; one unchanged legacy test error',
        schema_version=v.schema_version,renderer_readiness=v.renderer_readiness.model_dump(),
        learning_covered=3,coverage_requirements_satisfied=2,required_slots_populated=4,
        input_contracts=v.input_contracts,database_before=before['database'],database_after=state(),
        counts_before=old_counts,counts_after=counts(),new_review_decisions=0,new_governance_decisions=0,new_snapshots=0,
        frozen_files_unchanged=before['files'],protected_files=dict(changed=changed,missing=missing),
        determinism=dict(repeated_and_reversed_snapshots=True,sha256=hashlib.sha256(v.serialize().encode()).hexdigest()),
        tests=dict(baseline_passed=78,focused_passed=57,total=int(match[1]),passed=passed,failures=0,errors=1,not_run=0,
            known_error='Missing AI_Academic_Operating_System_Brainstorm_CN.pptx; original test and pin preserved'),
        limitations=[w.message for w in v.warnings],trust_summary=v.trust_summary)
    for name,payload in [('standard_deviation',v.serialize()),('provenance',json.dumps(result.provenance,ensure_ascii=False,sort_keys=True,indent=2)+'\n'),('acceptance',json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n')]:
        target=OUT/(name+'.json');encoded=payload.encode()
        if target.exists() and target.read_bytes()!=encoded:raise ValueError('Different existing artifact: '+str(target))
        target.write_bytes(encoded)
    print(json.dumps(dict(status=report['status'],tests=report['tests'],ready_for_rendering=True,database_unchanged=True),indent=2))


if __name__=='__main__':main()
