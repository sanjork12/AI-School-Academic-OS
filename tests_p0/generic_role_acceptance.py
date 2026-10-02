"""Offline symbolic authoring evidence and explicit v1.15 baseline revision."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.append(str(ROOT/'tmp/p6ui-deps'))
from tests_p0.test_generic_role_authoring import context,positive_fixtures,negative_fixtures
from tests_p0.governed_pedagogy_acceptance import read,write,legacy_hashes
from academic_os.ai_qualification.reference_baseline import sha,production_files,verify_reference
from academic_os.curriculum_ingestion.service import serial
from academic_os.generic_role_authoring.brief import build_brief
from academic_os.generic_role_authoring.validation import validate_candidate
from academic_os.generic_role_authoring.service import compose,validate_composition,role_eligibility
from academic_os.generic_role_authoring.policy import hash_of,MAPPING_VERSION,CONTRACTS,SYMBOL_MEANINGS
from academic_os.governed_pedagogy.authoring import requirements
OUT=ROOT/'output/p6a7c_generic_role_authoring'
CHANGES={'academic_os/governed_pedagogy/authoring.py','tests_p0/test_approved_pedagogical_consumption.py','academic_os/ai_qualification/reference_baseline.py','tests_p0/test_reference_revision.py'}
def integrity():
    b=read(OUT/'before.json');history={p:h for p,h in b['history'].items() if p!='output/reference_freeze_active.json'}
    assert all(sha(ROOT/p)==h for p,h in history.items())
    assert {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'var').rglob('*') if p.is_file()}==b['state']
    assert sha(ROOT/'tmp/p6ui5c-human-review-authority/key.dpapi')==b['credential_sha256']
    assert legacy_hashes()==b['legacy_hashes']
    assert all(sha(ROOT/p)==h for p,h in b['sd_sources'].items())
    assert all(sha(ROOT/p)==h for p,h in b['numerical_sources'].items() if p!='academic_os/ai_qualification/reference_baseline.py')
    return dict(historical_files_checked=len(history),historical_artifacts_unchanged=True,review_and_credentials_unchanged=True,trusted_state_unchanged=True,numerical_behavior_sources_unchanged=True,standard_deviation_unchanged=True,legacy_hashes=b['legacy_hashes'],model_calls=0)
def evidence():
    ingestion,service,spec=context()
    try:
        with patch('socket.socket.connect',side_effect=AssertionError('No network')):
            briefs={f:build_brief(spec,f,service) for f in CONTRACTS};fixtures={f:positive_fixtures(b) for f,b in briefs.items()}
            results={};compositions={};replays=[]
            for family,b in briefs.items():
                assert b==build_brief(spec,family,service)
                write(OUT/(family.lower().replace('_','-')+'-brief.json'),b)
                for n,c in enumerate(fixtures[family],1):
                    name=family.lower()+'-'+str(n);r=validate_candidate(c,b,service);assert r.valid
                    a=compose(c,b,service,validation=r);assert validate_composition(a,b,service)['valid']
                    for _ in range(2):
                        assert validate_candidate(c.model_dump(mode='json'),b,service)==r
                        assert hash_of(compose(c.model_dump(mode='json'),b,service))==hash_of(a)
                    write(OUT/'positive-fixtures'/(name+'.json'),c)
                    results[name]=r.model_dump(mode='json');compositions[name]=a.model_dump(mode='json')
                    replays.append(dict(candidate=name,passes=2,candidate_hash=hash_of(c),validation_hash=hash_of(r),composition_hash=hash_of(a),identical=True))
            rejected={}
            for name,family,c in negative_fixtures(fixtures['REPRESENTATION'][0],fixtures['CONCEPT_CHECK'][0]):
                r=validate_candidate(c,briefs[family],service);assert not r.valid,name
                write(OUT/'negative-fixtures'/(name+'.json'),c);rejected[name]=r.model_dump(mode='json')
            # Valid edited content still cannot reuse a prior validation receipt.
            old=fixtures['REPRESENTATION'][0];changed=old.model_dump(mode='json');changed['content'].update(symbol='<',expected_meaning='LESS_THAN')
            try:compose(changed,briefs['REPRESENTATION'],service,validation=validate_candidate(old,briefs['REPRESENTATION'],service))
            except ValueError:stale_rejected=True
            else:raise AssertionError('Stale validation accepted')
            gate=service.evaluate_lesson_authoring_eligibility(spec)
            roles={f:role_eligibility(spec,f,service) for f in CONTRACTS}
            assert gate.status=='BLOCKED' and all(r['status']=='ELIGIBLE_WITH_WARNINGS' for r in roles.values())
            write(OUT/'role-mapping-policy.json',dict(version=MAPPING_VERSION,contracts=CONTRACTS,semantic_policy=SYMBOL_MEANINGS,roles=roles,legacy_sl_roles_selected=[]))
            write(OUT/'validation-results.json',dict(positive=results,negative=rejected,stale_valid_candidate_report_rejected=stale_rejected))
            write(OUT/'composition-results.json',compositions)
            write(OUT/'offline-replay.json',replays)
            write(OUT/'authoring-eligibility.json',dict(role_level=roles,overall=gate.model_dump(mode='json'),requirements=requirements(spec,service.validate_pedagogical_spec(spec))))
            write(OUT/'compatibility.json',integrity())
            write(OUT/'offline-acceptance.json',dict(status='PASS',positive_candidates=len(results),negative_candidates=len(rejected),offline_only=True,model_calls=0,replay_passes=2,overall_authoring=gate.status,role_statuses={k:v['status'] for k,v in roles.items()},integrity=integrity()))
    finally:ingestion.close()
def freeze():
    target=ROOT/'output/reference_freeze_v1_15/reference_manifest.json';assert not target.parent.exists()
    before=read(OUT/'before.json');active=before['active'];parent=ROOT/active['manifest_path'];old=read(parent)
    assert read(ROOT/'output/reference_freeze_active.json')==active and sha(parent)==active['manifest_sha256']
    assert read(OUT/'backend-tests.json')['successful'] and read(OUT/'compatibility-tests.json')['successful'] and read(OUT/'offline-acceptance.json')['status']=='PASS'
    proof=integrity();changed={p for p,h in old['files'].items() if sha(ROOT/p)!=h};assert changed==CHANGES,changed
    files={p:sha(ROOT/p) for p in old['files']}
    extra=set(production_files(ROOT))|{'docs/P6A7C_GENERIC_ROLE_AUTHORING.md','tests_p0/test_generic_role_authoring.py','tests_p0/generic_role_acceptance.py'}
    extra.update(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    extra.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'output/p6ui5d_approved_evidence_consumption').iterdir() if p.is_file())
    for p in extra:files[p]=sha(ROOT/p)
    target.parent.mkdir();saved=target.parent/'parent-active-descriptor.json';write(saved,active);files[saved.relative_to(ROOT).as_posix()]=sha(saved)
    history=dict(old['historical_baselines']);history['v1.14']={p.relative_to(ROOT).as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest=dict(old,reference_version='v1.15',parent_reference='v1.14',revision_type='generic_symbolic_role_authoring',created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(ROOT),historical_baselines=history,
        generic_role_revision=dict(integrity=proof,changes=sorted(CHANGES),evidence_sha256=sha(OUT/'offline-acceptance.json'),inspection_sha256=sha(OUT/'inspection.json'),model_calls=0,trusted_writes=False))
    write(target,manifest);descriptor=dict(active_reference_version='v1.15',manifest_path=target.relative_to(ROOT).as_posix(),manifest_sha256=sha(target))
    (ROOT/'output/reference_freeze_active.json').write_bytes(serial(descriptor)+b'\n')
    check=verify_reference(ROOT);assert check['valid'],check
    write(OUT/'baseline-creation.json',dict(descriptor,protected_files=len(files)));print(json.dumps(dict(descriptor,protected_files=len(files)),indent=2))
if __name__=='__main__':
    if sys.argv[1:]==['evidence']:evidence()
    elif sys.argv[1:]==['freeze']:freeze()
    else:print(json.dumps(integrity(),indent=2))
