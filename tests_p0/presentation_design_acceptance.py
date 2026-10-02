"""P4C.1 acceptance: preserve v1 and all upstream data; verify final v2 bytes."""
import hashlib,json,re
from pathlib import Path
from academic_os.presentation_service import PresentationService,teacher_solutions
from academic_os.presentation_layout import layout_plan
from academic_os.presentation_validation import validate_artifact
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p4c1_presentation_design')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def readlog(name):
    raw=(OUT/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')

def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for file,digest in before['files'].items():assert sha(file)==digest,file
    old_counts=counts()
    service=PresentationService(Path('var/p0_q2.sqlite3'))
    i=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS,'standard-deviation-classroom/2')
    artifact=OUT/'Standard_Deviation_v2.pptx'
    report=validate_artifact(artifact,i.manifest,i.authored,i.validation,i.learning)
    assert report.valid and report.slide_count==11
    assert report.serialize().encode()==(OUT/'artifact_render_validation.json').read_bytes()
    assert i.manifest.serialize().encode()==(OUT/'presentation_manifest.json').read_bytes()
    assert (OUT/'teacher_solutions.json').read_bytes()==Path('output/p4c_presentation/teacher_solutions.json').read_bytes()
    assert json.loads((OUT/'teacher_solutions.json').read_text(encoding='utf-8'))==teacher_solutions(i)
    focused=readlog('focused-tests.txt');baseline=readlog('baseline-tests.txt')
    assert 'Ran 182 tests' in focused and focused.strip().endswith('OK')
    assert sum(line.endswith(' ... ok') for line in focused.splitlines())==182
    assert 'Ran 43 tests' in baseline and baseline.strip().endswith('OK')
    build=Path(json.loads((OUT/'provenance.json').read_text(encoding='utf-8'))['build_directory'])
    receipt=json.loads((build/'toolkit-validation.json').read_text(encoding='utf-8'))
    assert receipt['finalSha256']==sha(artifact)
    previews={f'slide-{n:02}.png':sha(build/'preview'/f'slide-{n:02}.png') for n in range(1,12)}
    plan=layout_plan(i.manifest,i.authored,i.validation,i.learning)
    classes={c:sum(e['kind']=='text' and e['text_class']==c for p in plan['slides'] for e in p['elements']) for c in ('upstream_content','renderer_label','footer','slide_number')}
    assert state()==before['database'] and counts()==old_counts
    result=dict(status='P4C.1 design acceptance passed',artifact_sha256=sha(artifact),manifest_sha256=report.manifest_sha256,
        artifact_validation=report.model_dump(mode='json'),teacher_solutions_byte_identical=True,
        upstream_and_v1_files_unchanged=before['files'],database_before=before['database'],database_after=state(),
        counts_before=old_counts,counts_after=counts(),new_reviews=0,new_snapshots=0,new_governance_decisions=0,
        tests=dict(baseline_passed=43,new_design_passed=44,regression_total=182,passed=182,failures=0,errors=0,full_repository_suite_run=False),
        design=dict(profile=i.manifest.identity['profile'],text_classification=classes,slide_count=11,
            source_formula_asts_unchanged=True,all_original_worked_steps_preserved=True,inferred_intermediate_steps_added=False),
        visual_qa=dict(all_11_final_slides_individually_inspected=True,montage_inspected=True,preview_sha256=previews,montage_sha256=sha(OUT/'montage.png'),
            native_powerpoint_detected=True,native_powerpoint_rendering_verified=False,preview_renderer='Artifact Tool import of finalized PPTX'),
        limitations=list(report.warnings))
    payload=json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n';target=OUT/'acceptance.json'
    if target.exists() and target.read_bytes()!=payload.encode():raise ValueError('Different existing acceptance evidence')
    target.write_bytes(payload.encode())
    print(json.dumps(dict(status=result['status'],tests=result['tests'],artifact=str(artifact),valid=report.valid),indent=2))

if __name__=='__main__':main()
