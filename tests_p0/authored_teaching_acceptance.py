"""Read-only P4A acceptance and reproducible candidate artifacts."""
import hashlib
import json
from pathlib import Path
import re
from academic_os.authored_service import AuthoredTeachingService
from academic_os.authored_verification import verify_package_math
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p4a_authored_teaching_content')


def log(name):
    raw=(OUT/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')


def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for file,digest in before['files'].items():assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==digest,file
    prior_counts=counts();service=AuthoredTeachingService(Path('var/p0_q2.sqlite3'))
    result=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS);p=result.view
    assert service.read_topic('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS))).view.serialize()==p.serialize()
    verification=verify_package_math(p)
    assert verification.mathematical_checks_passed and verification.ready_for_downstream_content_validation
    assert not verification.ready_as_completed_teaching_content
    assert len(p.content_blocks)==9 and len(p.coverage_summary)==4 and all(r.populated for r in p.coverage_summary.values())
    pins=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    changed=[f for f,h in pins.items() if Path(f).exists() and hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h]
    missing=[f for f in pins if not Path(f).exists()]
    assert not changed and missing==['AI_Academic_Operating_System_Brainstorm_CN.pptx']
    full=log('full-suite.txt');match=re.search(r'Ran (\d+) tests in ([\d.]+)s',full)
    assert match and 'FAILED (errors=1)' in full and not re.search(r'^FAIL:',full,re.M)
    errors=re.findall(r'^ERROR: (.+)$',full,re.M)
    assert len(errors)==1 and 'test_preserved_project_files' in errors[0]
    assert 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in full and 'FileNotFoundError' in full
    passed=sum(l.endswith(' ... ok') for l in full.splitlines());assert passed==int(match[1])-1
    assert 'Ran 38 tests' in log('focused-tests.txt') and log('focused-tests.txt').strip().endswith('OK')
    assert 'Ran 40 tests' in log('baseline-tests.txt') and log('baseline-tests.txt').strip().endswith('OK')
    assert state()==before['database'] and counts()==prior_counts
    report=dict(status='P4A acceptance passed with one unchanged legacy missing-file test error',
        schema_version=p.schema_version,candidate_status=p.status,content_blocks=len(p.content_blocks),
        populated_slots=4,existing_learning_requirements=3,new_learning_requirements=0,
        verification=verification.model_dump(),database_before=before['database'],database_after=state(),
        counts_before=prior_counts,counts_after=counts(),new_review_decisions=0,new_governance_decisions=0,new_snapshots=0,
        frozen_files_unchanged=before['files'],protected_files=dict(changed=changed,missing=missing),
        determinism=dict(repeated_and_reversed_snapshots=True,sha256=hashlib.sha256(p.serialize().encode()).hexdigest()),
        tests=dict(baseline_passed=40,focused_passed=38,total=int(match[1]),passed=passed,failures=0,errors=1,not_run=0,
            known_error='Missing AI_Academic_Operating_System_Brainstorm_CN.pptx; original pin/test preserved'),
        limitations=['No academic approval or publication','No full authored-content/pedagogical quality validator',
            'Feasibility checks cover positive integer n, finite rational summaries, nonnegative variance and singleton consistency, not constrained moment problems',
            'No new requirements, models, renderer or student assessment'])
    for name,value in [('standard_deviation',p.model_dump(mode='json')),('provenance',result.provenance),('acceptance',report)]:
        payload=json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
        target=OUT/(name+'.json')
        if target.exists() and target.read_bytes()!=payload.encode():raise ValueError('Existing artifact differs: '+str(target))
        target.write_bytes(payload.encode())
    print(json.dumps(dict(status=report['status'],tests=report['tests'],database_unchanged=True),indent=2))


if __name__=='__main__':main()
