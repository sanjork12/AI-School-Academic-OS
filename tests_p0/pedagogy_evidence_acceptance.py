"""Offline artifacts and versioned freeze; synthetic reviews stay in temporary stores."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]/'tmp/p6ui-deps'))
import json
import tempfile
from unittest.mock import patch
from datetime import datetime, timezone
from tests_p0.governed_pedagogy_acceptance import ROOT, read, write, legacy_hashes
from tests_p0.test_pedagogy_evidence import fixture, negatives, review_for, TEST_KEY, SPEC_ID
from academic_os.ai_qualification.reference_baseline import sha, production_files, verify_reference
from academic_os.curriculum_ingestion.service import IngestionService
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.pedagogy_evidence.service import PedagogicalEvidenceService, signature
from academic_os.pedagogy_evidence.models import Brief, Proposal, Review, Pack
from academic_os.pedagogy_evidence.validation import hash_of, ROLE_REFERENCES
from academic_os.pedagogy_evidence.integration import consume_approved_evidence
from academic_os.curriculum_ingestion.service import serial

OUT=ROOT/'output/p6ui5a_pedagogical_evidence'
CHANGES={'academic_os/ai_qualification/reference_baseline.py','tests_p0/test_reference_revision.py','tests_p0/test_syllabus_ingestion.py'}

def integrity():
    b=read(OUT/'before.json'); history={p:h for p,h in b['history'].items() if p!='output/reference_freeze_active.json'}
    assert all(sha(ROOT/p)==h for p,h in history.items())
    assert sha(ROOT/'var/p0_q2.sqlite3')==b['database_sha256']
    assert legacy_hashes()==b['legacy_hashes']
    assert all(sha(ROOT/p)==h for p,h in b['inspected_sources'].items())
    assert sha(ROOT/'tests_p0/test_syllabus_ingestion.py')==b['preexisting_test_sha256']
    return dict(historical_files_checked=len(history),historical_artifacts_unchanged=True,
        trusted_state_unchanged=True,database_sha256=b['database_sha256'],standard_deviation_unchanged=True,
        legacy_hashes=b['legacy_hashes'],model_calls=0)

def evidence():
    assert (OUT/'inspection.json').is_file()
    ingestion=IngestionService()
    try:
        learning=GovernedLearningService(AcademicCapabilityService(ingestion),ROOT/'output/p6ui4_learning_specification/specifications')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp, patch('socket.socket.connect',side_effect=AssertionError('No network')):
            service=PedagogicalEvidenceService(learning,temp,reviewer_keys={'offline-test-reviewer':TEST_KEY},domain='SYNTHETIC_TEST_ONLY')
            spec=learning.read_learning_spec(SPEC_ID); brief=service.build_pedagogical_authoring_brief(spec)
            assert brief==service.build_pedagogical_authoring_brief(spec)
            proposal=fixture(brief); positive=service.validate_pedagogical_proposal(proposal,brief); assert positive['valid']
            results={}
            for name,p in negatives(proposal).items():
                result=service.validate_pedagogical_proposal(p,brief); assert not result['valid'],name
                results[name]=result; write(OUT/'negative-fixtures'/(name+'.json'),p)
            review=review_for(proposal)
            receipt=service.record_pedagogical_review(proposal,review,reviewer_signature=signature(review,TEST_KEY))
            pack=service.build_approved_pedagogical_evidence_pack(proposal,receipt)
            assert service.validate_pedagogical_evidence_pack(pack)['valid']
            changed=proposal.model_dump(mode='json'); changed['activity_scope'][0]['category']='CONCEPT_CHECK'
            write(OUT/'negative-fixtures/changed-proposal-after-review.json',dict(proposal=changed,review=review.model_dump(mode='json'),synthetic_test_only=True))
            try: service.build_approved_pedagogical_evidence_pack(changed,receipt)
            except ValueError: results['changed-proposal-after-review']=dict(valid=False,reason='EXACT_REVIEW_HASH_MISMATCH')
            else: raise AssertionError('Review mutation accepted')
            integrated=consume_approved_evidence(spec,pack,service,GovernedPedagogyService(learning))
            write(OUT/'authoring-brief.json',brief); write(OUT/'positive-fixture.json',proposal)
            write(OUT/'validation-results.json',dict(positive=positive,negative=results,synthetic_test_only=True,model_calls=0))
            write(OUT/'review-contract.json',dict(schema=Review.model_json_schema(),pack_schema=Pack.model_json_schema(),
                brief_schema=Brief.model_json_schema(),proposal_schema=Proposal.model_json_schema(),real_review_status='PENDING',real_reviews_recorded=0,
                authentication='Configured reviewer HMAC-SHA256; no default human credentials; exact immutable receipt required',synthetic_domain='SYNTHETIC_TEST_ONLY'))
            write(OUT/'integration-result.json',dict(synthetic_test_only=True,contract_demonstration=integrated,
                real_state=dict(review='PENDING',pedagogical_eligibility='REVIEW_REQUIRED',lesson_authoring='BLOCKED',approved_pack_created=False),
                synthetic_pack_persisted=False,model_calls=0))
            write(OUT/'standard-deviation-comparison.json',dict(migration=False,legacy_hashes=legacy_hashes(),role_category_references=ROLE_REFERENCES,
                conceptual_mapping=dict(P3A='governed intentions and exact scope in brief',P3B='pedagogical requirements map to proposed activity constraints',
                    P3C='coverage validation maps to criteria/check references',P5='historical roles inform categories only',P6='future model output stays proposed'),
                excluded=['SD calculation method','summary statistics','fixed 15-role sequence','numerical worked examples'],behavior_unchanged=True))
            write(OUT/'offline-acceptance.json',dict(status='PASS',target='EDX-4MA1-F-2.8-A',valid_proposals=1,rejected_negative_fixtures=len(results),
                real_approvals=0,model_calls=0,integrity=integrity()))
    finally: ingestion.close()

def freeze():
    target=ROOT/'output/reference_freeze_v1_13/reference_manifest.json'; assert not target.parent.exists()
    before=read(OUT/'before.json'); active=before['active']; parent=ROOT/active['manifest_path']; old=read(parent)
    assert read(ROOT/'output/reference_freeze_active.json')==active and sha(parent)==active['manifest_sha256']
    assert read(OUT/'backend-tests.json')['successful'] and read(OUT/'offline-acceptance.json')['status']=='PASS'
    assert read(OUT/'upstream-tests.json')['successful']
    proof=integrity(); changes={p for p,h in old['files'].items() if sha(ROOT/p)!=h}; assert changes==CHANGES,changes
    files={p:sha(ROOT/p) for p in old['files']}
    extra=set(production_files(ROOT))|{'docs/P6UI5A_PEDAGOGICAL_EVIDENCE_AUTHORING.md','tests_p0/test_pedagogy_evidence.py','tests_p0/pedagogy_evidence_acceptance.py'}
    extra.update(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    extra.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'output/p6ui5_pedagogical_specification').iterdir() if p.is_file())
    for name in extra: files[name]=sha(ROOT/name)
    target.parent.mkdir(); saved=target.parent/'parent-active-descriptor.json'; write(saved,active); files[saved.relative_to(ROOT).as_posix()]=sha(saved)
    history=dict(old['historical_baselines']); history['v1.12']={p.relative_to(ROOT).as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest=dict(old,reference_version='v1.13',parent_reference='v1.12',revision_type='pedagogical_evidence_authoring_contract',
        created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(ROOT),historical_baselines=history,
        pedagogy_evidence_revision=dict(integrity=proof,changes=sorted(CHANGES),preexisting_test_change='Two explicit UTF-8 reads retained',
            inspection_sha256=sha(OUT/'inspection.json'),evidence_sha256=sha(OUT/'offline-acceptance.json'),real_approvals=0,model_calls=0,trusted_writes=False))
    write(target,manifest)
    descriptor=dict(active_reference_version='v1.13',manifest_path=target.relative_to(ROOT).as_posix(),manifest_sha256=sha(target))
    (ROOT/'output/reference_freeze_active.json').write_bytes(serial(descriptor)+b'\n')
    check=verify_reference(ROOT); assert check['valid'],check
    write(OUT/'baseline-creation.json',dict(descriptor,protected_files=len(files)))
    print(json.dumps(dict(descriptor,protected_files=len(files)),indent=2))

if __name__=='__main__':
    if sys.argv[1:]==['evidence']: evidence()
    elif sys.argv[1:]==['freeze']: freeze()
    else: print(json.dumps(integrity(),indent=2))
