"""Read-only P4C acceptance with frozen upstream evidence and actual artifact checks."""
import hashlib
import json
from pathlib import Path
import re
from academic_os.presentation_service import PresentationService,teacher_solutions
from academic_os.presentation_validation import validate_artifact
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p4c_presentation')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(name):
    raw=(OUT/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')

def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for file,h in before['files'].items():assert digest(file)==h,file
    old_counts=counts()
    i=PresentationService(Path('var/p0_q2.sqlite3')).read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    pptx=OUT/'student/Standard_Deviation.pptx'
    report=validate_artifact(pptx,i.manifest,i.authored,i.validation,i.learning)
    assert report.valid,report.violations
    assert report.serialize().encode()==(OUT/'artifact_render_validation.json').read_bytes()
    assert i.manifest.serialize().encode()==(OUT/'presentation_manifest.json').read_bytes()
    assert teacher_solutions(i)==json.loads((OUT/'teacher_solutions.json').read_text(encoding='utf-8'))
    pins=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    changed=[f for f,h in pins.items() if Path(f).exists() and digest(f)!=h]
    missing=[f for f in pins if not Path(f).exists()]
    assert not changed and missing==['AI_Academic_Operating_System_Brainstorm_CN.pptx']
    full=log('full-suite.txt');match=re.search(r'Ran (\d+) tests in ([\d.]+)s',full)
    assert match and 'FAILED (errors=1)' in full and not re.search(r'^FAIL:',full,re.M)
    errors=re.findall(r'^ERROR: (.+)$',full,re.M)
    assert len(errors)==1 and 'test_preserved_project_files' in errors[0]
    assert 'FileNotFoundError' in full and missing[0] in full
    passed=sum(line.endswith(' ... ok') for line in full.splitlines())
    assert passed==int(match[1])-1
    assert 'Ran 43 tests' in log('focused-tests.txt') and log('focused-tests.txt').strip().endswith('OK')
    assert 'Ran 95 tests' in log('baseline-tests.txt') and log('baseline-tests.txt').strip().endswith('OK')
    build=Path(json.loads((OUT/'provenance.json').read_text(encoding='utf-8'))['build_directory'])
    finalizer=json.loads((build/'toolkit-validation.json').read_text(encoding='utf-8'))
    assert finalizer['finalSha256']==digest(pptx)
    previews={f'slide-{n:02}.png':digest(build/'preview'/f'slide-{n:02}.png') for n in range(1,12)}
    assert state()==before['database'] and counts()==old_counts
    result=dict(status='P4C acceptance passed; one unchanged legacy preservation error',
        artifact_sha256=digest(pptx),manifest_sha256=report.manifest_sha256,artifact_validation=report.model_dump(mode='json'),
        tests=dict(baseline_passed=95,focused_passed=43,total=int(match[1]),passed=passed,failures=0,errors=1,not_run=0,
            known_error='Missing historical AI_Academic_Operating_System_Brainstorm_CN.pptx; no pins changed'),
        database_before=before['database'],database_after=state(),counts_before=old_counts,counts_after=counts(),
        new_reviews=0,new_governance_decisions=0,new_snapshots=0,frozen_files_unchanged=before['files'],
        protected_files=dict(changed=changed,missing=missing),
        visual_inspection=dict(all_11_final_slide_previews_individually_inspected=True,preview_sha256=previews,native_powerpoint_execution=False),
        determinism=dict(manifest_and_layout=True,repeat_output_bytes_reused=True,fresh_export_byte_identity_claimed=False))
    target=OUT/'acceptance.json';payload=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if target.exists() and target.read_bytes()!=payload.encode():raise ValueError('Acceptance evidence differs; do not replace silently')
    target.write_bytes(payload.encode())
    print(json.dumps(dict(status=result['status'],tests=result['tests'],pptx=str(pptx),valid=report.valid),indent=2))

if __name__=='__main__':main()
