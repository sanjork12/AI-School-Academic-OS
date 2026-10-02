"""Real pack acceptance, integrity verification and explicit v1.14 freeze."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.append(str(ROOT/'tmp/p6ui-deps'))
from tests_p0.test_approved_pedagogical_consumption import real_context,mutations
from tests_p0.governed_pedagogy_acceptance import legacy_hashes,read,write
from academic_os.ai_qualification.reference_baseline import sha,production_files,verify_reference
from academic_os.curriculum_ingestion.service import serial
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.governed_pedagogy.consumer import consume,validate_consumed
from academic_os.governed_pedagogy.validation import approved_role_errors
from academic_os.governed_pedagogy import authoring
from academic_os.pedagogy_evidence.validation import hash_of
OUT=ROOT/'output/p6ui5d_approved_evidence_consumption'
CHANGES={'academic_os/governed_pedagogy/'+n for n in ['models.py','policy.py','service.py','validation.py']}|{'academic_os/ai_qualification/reference_baseline.py','tests_p0/test_reference_revision.py'}

def integrity():
    b=read(OUT/'before.json');history={p:h for p,h in b['history'].items() if p!='output/reference_freeze_active.json'}
    assert all(sha(ROOT/p)==h for p,h in history.items())
    state={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'var').rglob('*') if p.is_file()}
    assert state==b['state']
    assert sha(ROOT/'tmp/p6ui5c-human-review-authority/key.dpapi')==b['credential_sha256']
    assert legacy_hashes()==b['legacy_hashes']
    assert all(sha(ROOT/p)==h for p,h in b['legacy_sources'].items())
    return dict(historical_files_checked=len(history),historical_artifacts_unchanged=True,review_and_credentials_unchanged=True,trusted_state_unchanged=True,standard_deviation_unchanged=True,legacy_hashes=b['legacy_hashes'],model_calls=0)

def evidence():
    ingestion,learning,authority,pack,ls=real_context()
    try:
        with patch('socket.socket.connect',side_effect=AssertionError('No network')):
            service=GovernedPedagogyService(learning,OUT/'stored',evidence_service=authority)
            before=service.evaluate_pedagogical_spec_eligibility(ls)
            c=consume(ls,pack,authority);assert validate_consumed(c,ls,authority)==c
            after=service.evaluate_pedagogical_spec_eligibility(ls,approved_pack=pack)
            ev=service.validate_pedagogical_eligibility(after,ls,approved_pack=pack);assert ev.valid
            assert after.status=='ELIGIBLE_WITH_WARNINGS'
            spec=service.build_pedagogical_spec(ls,after,approved_pack=pack)
            validation=service.validate_pedagogical_spec(spec);assert validation.valid
            assert serial(spec)==serial(service.build_pedagogical_spec(ls,after,approved_pack=pack))
            identity=service.persist_pedagogical_spec(spec)
            assert service.read_constructed_spec(identity)==spec
            gate=service.evaluate_lesson_authoring_eligibility(spec);assert gate.status=='BLOCKED'
            assert service.validate_lesson_authoring_eligibility(gate,spec)['valid']
            assert not approved_role_errors(spec.role_contract,after.role_contract)
            negative={}
            for name,p in mutations(pack):
                result=service.evaluate_pedagogical_spec_eligibility(ls,approved_pack=p)
                assert result.status=='BLOCKED';negative[name]=dict(rejected=True,status=result.status,reasons=result.reason_codes)
            other=learning.read_learning_spec('3a9e88369d5e66e1ce7b9aee74526bc75e474b16499ddcf1ada5870802515584')
            assert service.evaluate_pedagogical_spec_eligibility(other,approved_pack=pack).status=='BLOCKED'
            negative['cross-target-reuse']=dict(rejected=True)
            with patch.object(authority,'validate_pedagogical_evidence_pack',return_value={'valid':True}):
                assert service.evaluate_pedagogical_spec_eligibility(ls,approved_pack=dict(mutations(pack))['signature-forged']).status=='BLOCKED'
            negative['pack-validation-bypass']=dict(rejected=True)
            raw=spec.model_dump(mode='json');raw['role_contract']['roles'][-1]['legacy_role_ids']=['SL-13']
            assert not service.validate_pedagogical_spec(raw).valid;negative['invented-role-mapping']=dict(rejected=True)
            raw=spec.model_dump(mode='json');raw['warnings']=[]
            assert not service.validate_pedagogical_spec(raw).valid;negative['spec-warning-removed']=dict(rejected=True)
            for name,value in [('consumer-result',c),('eligibility-before',before),('eligibility-after',after),('eligibility-validation',ev),('pedagogical-specification',spec),('pedagogical-validation',validation),('role-contract',spec.role_contract),('lesson-authoring-eligibility',gate),('content-validation-requirements',authoring.requirements(spec,validation)),('negative-tests',negative)]:write(OUT/(name+'.json'),value)
            write(OUT/'offline-acceptance.json',dict(status='PASS',specification_hash=identity,pack_identity=pack.evidence_identity,pack_hash=hash_of(pack),before=before.status,after=after.status,lesson_authoring=gate.status,consumer_valid=True,eligibility_valid=True,spec_valid=True,role_contract_valid=True,authoring_gate_valid=True,deterministic=True,replay=True,negative_cases=len(negative),inherited_warnings=len(ls.warnings),spec_warnings=len(spec.warnings),model_calls=0,integrity=integrity()))
    finally:ingestion.close()

def freeze():
    target=ROOT/'output/reference_freeze_v1_14/reference_manifest.json';assert not target.parent.exists()
    before=read(OUT/'before.json');active=before['active'];parent=ROOT/active['manifest_path'];old=read(parent)
    assert read(ROOT/'output/reference_freeze_active.json')==active and sha(parent)==active['manifest_sha256']
    assert read(OUT/'backend-tests.json')['successful'] and read(OUT/'offline-acceptance.json')['status']=='PASS'
    proof=integrity();changed={p for p,h in old['files'].items() if sha(ROOT/p)!=h};assert changed==CHANGES,changed
    files={p:sha(ROOT/p) for p in old['files']}
    extra=set(production_files(ROOT))|{'docs/P6UI5D_APPROVED_EVIDENCE_CONSUMPTION.md','tests_p0/test_approved_pedagogical_consumption.py','tests_p0/approved_consumption_acceptance.py'}
    extra.update(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    for directory in ('p6ui5a_pedagogical_evidence','p6ui5b_live_pedagogical_qualification','p6ui5c_human_pedagogical_review'):
        extra.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'output'/directory).rglob('*') if p.is_file())
    for p in extra:files[p]=sha(ROOT/p)
    target.parent.mkdir();saved=target.parent/'parent-active-descriptor.json';write(saved,active);files[saved.relative_to(ROOT).as_posix()]=sha(saved)
    history=dict(old['historical_baselines']);history['v1.13']={p.relative_to(ROOT).as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest=dict(old,reference_version='v1.14',parent_reference='v1.13',revision_type='approved_pedagogical_evidence_consumption',created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(ROOT),historical_baselines=history,
        approved_consumption_revision=dict(integrity=proof,changes=sorted(CHANGES),evidence_sha256=sha(OUT/'offline-acceptance.json'),inspection_sha256=sha(OUT/'inspection.json'),model_calls=0,trusted_writes=False))
    write(target,manifest);descriptor=dict(active_reference_version='v1.14',manifest_path=target.relative_to(ROOT).as_posix(),manifest_sha256=sha(target))
    (ROOT/'output/reference_freeze_active.json').write_bytes(serial(descriptor)+b'\n')
    check=verify_reference(ROOT);assert check['valid'],check
    write(OUT/'baseline-creation.json',dict(descriptor,protected_files=len(files)));print(json.dumps(dict(descriptor,protected_files=len(files)),indent=2))
if __name__=='__main__':
    if sys.argv[1:]==['evidence']:evidence()
    elif sys.argv[1:]==['freeze']:freeze()
    else:print(json.dumps(integrity(),indent=2))
