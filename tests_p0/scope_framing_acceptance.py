"""Offline evidence and explicit baseline revision for deterministic framing."""
import sys,json,unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.append(str(ROOT/'tmp/p6ui-deps'))
from tests_p0.test_scope_framing import context,mutations
from tests_p0.governed_pedagogy_acceptance import read,write
from academic_os.ai_qualification.reference_baseline import sha,production_files,verify_reference
from academic_os.generic_role_authoring.scope import build_scope_framing,validate_scope_framing,build_lesson_authoring_plan
from academic_os.generic_role_authoring.policy import hash_of
from academic_os.generic_role_authoring.service import role_eligibility
from academic_os.curriculum_ingestion.service import serial
OUT=ROOT/'output/p6a7c1_scope_framing'
CHANGES={'academic_os/governed_pedagogy/authoring.py','academic_os/governed_pedagogy/service.py','academic_os/ai_qualification/reference_baseline.py','tests_p0/test_reference_revision.py'}

def integrity():
    b=read(OUT/'before.json');history={p:h for p,h in b['history'].items() if p!='output/reference_freeze_active.json'}
    assert all(sha(ROOT/p)==h for p,h in history.items()),'Historical file changed'
    assert {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'var').rglob('*') if p.is_file()}==b['state']
    assert sha(ROOT/'tmp/p6ui5c-human-review-authority/key.dpapi')==b['credential_sha256']
    assert all(sha(ROOT/p)==h for p,h in b['production'].items() if p not in CHANGES)
    return dict(historical_files=len(history),historical_unchanged=True,trusted_state_unchanged=True,credentials_unchanged=True,unrelated_production_unchanged=True,model_calls=0)

def evidence():
    ingestion,service,spec=context()
    try:
        with patch('socket.socket.connect',side_effect=AssertionError('No network')):
            before=service.evaluate_lesson_authoring_eligibility(spec)
            q=build_scope_framing(spec,service);r=validate_scope_framing(q,spec,service);assert r['valid'],r
            after=service.evaluate_lesson_authoring_eligibility(spec,scope_framing=q)
            assert before.status=='BLOCKED' and after.status=='ELIGIBLE_WITH_WARNINGS'
            assert service.validate_lesson_authoring_eligibility(after,spec,scope_framing=q)['valid']
            plan=build_lesson_authoring_plan(spec,q,service);replay=[]
            for n in range(2):
                q2=build_scope_framing(spec,service);r2=validate_scope_framing(q2,spec,service);p2=build_lesson_authoring_plan(spec,q2,service)
                assert serial(q2)==serial(q) and r2==r and p2==plan
                replay.append(dict(pass_number=n+1,scope_hash=hash_of(q2),validation_hash=hash_of(r2),plan_hash=hash_of(p2),identical=True))
            negatives={}
            for name,raw in mutations(q):
                result=validate_scope_framing(raw,spec,service);assert not result['valid'],name
                negatives[name]=dict(candidate=raw,validation=result)
            for name,value in {'scope-framing':q,'scope-validation':r,'lesson-authoring-plan':plan,'eligibility-before':before,'eligibility-after':after,
                'role-eligibility':{f:role_eligibility(spec,f,service) for f in ('REPRESENTATION','CONCEPT_CHECK')},'negative-tests':negatives,'offline-replay':replay}.items():write(OUT/(name+'.json'),value)
            write(OUT/'offline-acceptance.json',dict(status='PASS',negative_cases=len(negatives),replay_passes=2,scope_valid=True,overall_before=before.status,overall_after=after.status,integrity=integrity(),model_calls=0))
    finally:ingestion.close()

BACKEND=['tests_p0.test_scope_framing','tests_p0.test_generic_role_authoring','tests_p0.test_approved_pedagogical_consumption','tests_p0.test_pedagogy_evidence','tests_p0.test_governed_pedagogy','tests_p0.test_governed_learning','tests_p0.test_pedagogical_specification','tests_p0.test_pedagogical_validation','tests_p0.test_lesson_profiles','tests_p0.test_syllabus_ingestion','tests_p0.test_curriculum_capability']
COMPAT=['tests_p0.test_ai_authoring','tests_p0.test_candidate_contract','tests_p0.test_derivation_provenance','tests_p0.test_provenance_closure','tests_p0.test_offline_candidate_replay','tests_p0.test_sl11_authoring','tests_p0.test_controlled_inputs','tests_p0.test_expression_semantics']
POST=['tests_p0.test_reference_freeze','tests_p0.test_reference_revision','tests_p0.test_ai_qualification']
def tests(name,modules):
    with (OUT/(name+'.txt')).open('x',encoding='utf-8') as f:
        result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(modules))
    report=dict(total=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),successful=result.wasSuccessful(),modules=modules,model_calls=0)
    write(OUT/(name+'.json'),report);print(json.dumps(report,indent=2))
    if not result.wasSuccessful():raise SystemExit(1)

def freeze():
    target=ROOT/'output/reference_freeze_v1_16/reference_manifest.json';assert not target.parent.exists()
    active=read(OUT/'before.json')['active'];parent=ROOT/active['manifest_path'];old=read(parent)
    assert read(ROOT/'output/reference_freeze_active.json')==active and sha(parent)==active['manifest_sha256']
    for name in ('backend-tests','compatibility-tests'):assert read(OUT/(name+'.json'))['successful']
    assert read(OUT/'offline-acceptance.json')['status']=='PASS'
    proof=integrity();changed={p for p,h in old['files'].items() if sha(ROOT/p)!=h};assert changed==CHANGES,changed
    files={p:sha(ROOT/p) for p in old['files']}
    extra=set(production_files(ROOT))|{'docs/P6A7C1_SCOPE_FRAMING.md','tests_p0/test_scope_framing.py','tests_p0/scope_framing_acceptance.py'}
    for folder in (OUT,ROOT/'output/p6a7c_generic_role_authoring'):
        extra.update(p.relative_to(ROOT).as_posix() for p in folder.rglob('*') if p.is_file())
    for p in extra:files[p]=sha(ROOT/p)
    target.parent.mkdir();saved=target.parent/'parent-active-descriptor.json';write(saved,active);files[saved.relative_to(ROOT).as_posix()]=sha(saved)
    history=dict(old['historical_baselines']);history['v1.15']={p.relative_to(ROOT).as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest=dict(old,reference_version='v1.16',parent_reference='v1.15',revision_type='deterministic_scope_framing',created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(ROOT),historical_baselines=history,
        scope_framing_revision=dict(integrity=proof,changes=sorted(CHANGES),evidence_sha256=sha(OUT/'offline-acceptance.json'),inspection_sha256=sha(OUT/'inspection.json'),model_calls=0,trusted_writes=False))
    write(target,manifest);descriptor=dict(active_reference_version='v1.16',manifest_path=target.relative_to(ROOT).as_posix(),manifest_sha256=sha(target))
    (ROOT/'output/reference_freeze_active.json').write_bytes(serial(descriptor)+b'\n')
    check=verify_reference(ROOT);assert check['valid'],check
    write(OUT/'baseline-creation.json',dict(descriptor,protected_files=len(files)));print(json.dumps(dict(descriptor,protected_files=len(files)),indent=2))

def finish():
    check=verify_reference(ROOT);assert check['valid'],check
    runs={n:read(OUT/(n+'.json')) for n in ('backend-tests','compatibility-tests','postfreeze-tests')};assert all(r['successful'] for r in runs.values())
    report=dict(status='PASS',milestone='P6A.7C.1',offline=read(OUT/'offline-acceptance.json'),tests=runs,total_tests=sum(r['total'] for r in runs.values()),baseline=read(OUT/'baseline-creation.json'),baseline_verification=check,integrity=integrity(),model_calls=0,
        no_candidate_content_generated=True,live_authoring_qualified=False,full_lesson_generated=False,rendered=False,published=False)
    write(OUT/'acceptance.json',report)
    write(OUT/'final-evidence-manifest.json',dict(files={p.relative_to(ROOT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()}))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    action=sys.argv[1]
    if action=='evidence':evidence()
    elif action=='backend':tests('backend-tests',BACKEND)
    elif action=='compatibility':tests('compatibility-tests',COMPAT)
    elif action=='postfreeze':tests('postfreeze-tests',POST)
    elif action=='freeze':freeze()
    elif action=='finish':finish()
