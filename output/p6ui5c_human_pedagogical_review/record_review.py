"""Record the user's explicit decision; never infer a pedagogical approval.

The local signing gateway attests the attached user decision, not a separately
verified named identity. Its random key is protected by Windows current-user
DPAPI and is never returned in evidence or console output.
"""
import sys,json,secrets,ctypes
from ctypes import wintypes
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.append(str(ROOT/'tmp/p6ui-deps'))
from academic_os.curriculum_ingestion.service import IngestionService,serial
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.pedagogy_evidence.service import PedagogicalEvidenceService,signature
from academic_os.pedagogy_evidence.models import Proposal,Review
from academic_os.pedagogy_evidence.validation import hash_of,COMPONENTS
from academic_os.pedagogy_evidence.integration import consume_approved_evidence
from academic_os.ai_qualification.reference_baseline import sha,verify_reference
OUT=Path(__file__).resolve().parent
LIVE=ROOT/'output/p6ui5b_live_pedagogical_qualification/resume-01'
SOURCE=Path('C:/Users/Administrator/.codex/attachments/d60ff7b1-bbc7-4fcb-a243-894335961666/已粘贴的文本.txt')
KEY=ROOT/'tmp/p6ui5c-human-review-authority/key.dpapi'
REVIEWER='human-user:d60ff7b1-bbc7-4fcb-a243-894335961666'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(serial(v)+b'\n')
class Blob(ctypes.Structure):
    _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]
def dpapi(data,decrypt=False):
    buf=(ctypes.c_ubyte*len(data)).from_buffer_copy(data);src=Blob(len(data),buf);dst=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p];kernel.LocalFree.restype=ctypes.c_void_p
    fn=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    if not fn(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)):raise ctypes.WinError(ctypes.get_last_error())
    try:return ctypes.string_at(dst.pbData,dst.cbData)
    finally:kernel.LocalFree(dst.pbData)
def inventory(folder):
    return {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/folder).rglob('*') if p.is_file() and not p.is_relative_to(OUT) and '__pycache__' not in p.parts}
def main():
    assert not (OUT/'acceptance.json').exists(),'Do not overwrite a completed review operation'
    assert verify_reference(ROOT)['valid']
    if (OUT/'before.json').exists():
        before=read(OUT/'before.json')
        assert all(sha(ROOT/p)==h for p,h in before['history'].items()) and inventory('var')==before['state']
    else:
        before=dict(history=inventory('output'),state=inventory('var'),baseline=read(ROOT/'output/reference_freeze_active.json'))
        write(OUT/'before.json',before)
    manifest=read(LIVE/'evidence-manifest.json')
    assert all(sha(LIVE/p)==h for p,h in manifest.items())
    source_bytes=SOURCE.read_bytes()
    if (OUT/'human-decision-original.txt').exists():assert (OUT/'human-decision-original.txt').read_bytes()==source_bytes
    else:
        with (OUT/'human-decision-original.txt').open('xb') as f:f.write(source_bytes)
    b1=read(LIVE/'human-review-bundles/attempt-01.json');b2=read(LIVE/'human-review-bundles/attempt-02.json')
    p1=Proposal.model_validate(read(LIVE/'attempt-01/parsed-proposal.json'));p2=Proposal.model_validate(read(LIVE/'attempt-02/parsed-proposal.json'))
    assert hash_of(p1)==b1['proposal_hash'] and hash_of(p2)==b2['proposal_hash']
    assert {c.observable_student_action for c in p1.success_criteria}=={'INTERPRET_SYMBOL','SELECT_SYMBOL'}
    assert {c.observable_student_action for c in p2.success_criteria}=={'SELECT_SYMBOL'}
    assert p1.source_id==p2.source_id=='EDX-4MA1-F-2.8-A' and p1.tier==p2.tier=='Foundation'
    assert p1.brief==p2.brief and hash_of(p1.brief)==b1['brief_hash']==b2['brief_hash']
    assert p1.pedagogical_adapter.evidence_basis.origin==p2.pedagogical_adapter.evidence_basis.origin=='MODEL_PROPOSED'
    if not KEY.exists() or KEY.stat().st_size==0:
        KEY.parent.mkdir(parents=True,exist_ok=True)
        encrypted=dpapi(secrets.token_bytes(32))
        mode='wb' if KEY.exists() and KEY.stat().st_size==0 else 'xb'
        with KEY.open(mode) as f:f.write(encrypted)
    key=dpapi(KEY.read_bytes(),True);assert len(key)==32
    write(OUT/'review-authority.json',dict(reviewer_id=REVIEWER,authority='Explicit human user decision attached to this conversation',
        decision_source_sha256=sha(SOURCE),credential_protection='Windows current-user DPAPI; plaintext never persisted',
        credential_location=str(KEY),attestation_scope='Local gateway records the user-confirmed decision, not independent identity certification',
        recovery='Retain encrypted credential and the Windows user profile for future authenticated replay. No production default reviewer key was configured.'))
    ingestion=IngestionService()
    try:
        with patch('socket.socket.connect',side_effect=AssertionError('No provider or network calls')):
            learning=GovernedLearningService(AcademicCapabilityService(ingestion),ROOT/'output/p6ui4_learning_specification/specifications')
            spec=learning.read_learning_spec(p1.brief.learning_spec_hash);assert hash_of(spec)==p1.brief.learning_spec_hash
            service=PedagogicalEvidenceService(learning,OUT/'review-store',reviewer_keys={REVIEWER:key},domain='HUMAN_REVIEW')
            pedagogy=GovernedPedagogyService(learning)
            before_eligibility=pedagogy.evaluate_pedagogical_spec_eligibility(spec)
            before_authoring=pedagogy.evaluate_lesson_authoring_eligibility(learning_spec=spec)
            records=[]
            for label,p,b,decision,rationale in [
                ('attempt-01',p1,b1,'APPROVE','The human reviewer confirms separate INTERPRET_SYMBOL and SELECT_SYMBOL coverage; observable success criteria bounded to REVIEWED_INEQUALITY_SYMBOLS_ONLY; permitted activity vocabulary; an aligned observable check per criterion; proposal-supported REPRESENTATION and CONCEPT_CHECK families; no Standard Deviation calculation pedagogy.'),
                ('attempt-02',p2,b2,'REVISE','The human reviewer finds insufficient explicit independent evidence for the understand part of the canonical meaning. Add an explicit INTERPRET_SYMBOL success criterion and matching check; symbol selection alone is insufficient.')]:
                validation=service.validate_pedagogical_proposal(p,p.brief);assert validation['valid']
                binding=dict(proposal_hash=b['proposal_hash'],target_source_id=p.source_id,tier=p.tier,learning_spec_hash=p.brief.learning_spec_hash,brief_hash=b['brief_hash'],policy_version=p.brief.policy_version,human_decision_source_sha256=sha(SOURCE))
                scope='Approval scope, if APPROVE: governed pedagogical construction only; no source repair, curriculum trust promotion, canonical approval, trusted snapshot, lesson-content approval or publication. All inherited warnings remain.'
                text=rationale+' '+scope+' Exact bindings: '+json.dumps(binding,sort_keys=True)
                review=Review(proposal_hash=b['proposal_hash'],reviewer_id=REVIEWER,domain='HUMAN_REVIEW',decisions=[dict(component=c,decision=decision,rationale=text) for c in COMPONENTS])
                receipt=service.record_pedagogical_review(p,review,reviewer_signature=signature(review,key))
                assert service.record_pedagogical_review(p,review,reviewer_signature=signature(review,key))==receipt
                write(OUT/(label+'-review.json'),receipt)
                write(OUT/(label+'-bindings.json'),dict(binding,semantic_review_hash=receipt.semantic_hash,receipt_hash=hash_of(receipt),component_decisions={c:decision for c in COMPONENTS},review_valid=True,proposal_validation=validation))
                records.append(receipt)
            pack=service.build_approved_pedagogical_evidence_pack(p1,records[0])
            with patch.object(service,'build_approved_pedagogical_evidence_pack',side_effect=AssertionError('Validator cannot call constructor')):
                check=service.validate_pedagogical_evidence_pack(pack);assert check['valid']
            identity=service.persist_evidence_pack(pack);assert service.read_evidence_pack(identity)==pack
            # Reopen from a separately initialized authority instance to prove durable replay.
            again=PedagogicalEvidenceService(learning,OUT/'review-store',reviewer_keys={REVIEWER:dpapi(KEY.read_bytes(),True)},domain='HUMAN_REVIEW')
            assert again.read_evidence_pack(identity)==pack
            assert pack.proposal==p1 and pack.proposal.brief.source_learning_spec.warnings==spec.warnings
            write(OUT/'approved-evidence-pack.json',pack);write(OUT/'approved-pack-validation.json',check)
            consumption=consume_approved_evidence(spec,pack,service,pedagogy);write(OUT/'p6ui5-consumption.json',consumption)
            after=pedagogy.evaluate_pedagogical_spec_eligibility(spec)
            assert after.model_dump(mode='json')==consumption['existing_p6ui5_eligibility']
            assert after.status=='REVIEW_REQUIRED'
            after_authoring=pedagogy.evaluate_lesson_authoring_eligibility(learning_spec=spec)
            for name,value in [('eligibility-before',before_eligibility),('eligibility-after',after),('lesson-authoring-before',before_authoring),('lesson-authoring-after',after_authoring)]:write(OUT/(name+'.json'),value)
            write(OUT/'construction-result.json',dict(status='NOT_CONSTRUCTED',reason='Frozen P6UI.5 evaluates governed-learning/1 only; the consumption adapter supplies approved evidence but does not implement an evidence-aware eligibility policy or constructor.',reason_codes=after.reason_codes,missing_requirements=after.missing_requirements,pedagogical_specification_hash=None,validation='NOT_APPLICABLE_NO_SPECIFICATION'))
            # Evidence integrity and approval-boundary checks, without new review decisions.
            altered=pack.model_dump(mode='json');altered['proposal']['activity_scope'][0]['category']='CONCEPT_CHECK'
            assert not service.validate_pedagogical_evidence_pack(altered)['valid']
            assert not PedagogicalEvidenceService(learning,OUT/'review-store').validate_pedagogical_evidence_pack(pack)['valid']
            assert all(d.decision=='REVISE' for d in records[1].review.decisions)
            assert len(list((OUT/'review-store/packs').glob('*.json')))==1
            write(OUT/'verification.json',dict(exact_proposal_bytes_unchanged=True,review_idempotent=True,independent_pack_validation=True,persisted_pack_replay=True,separate_instance_replay=True,tamper_rejected=True,missing_authority_rejected=True,attempt02_revise_only=True,approved_pack_count=1))
    finally:ingestion.close()
    assert all(sha(ROOT/p)==h for p,h in before['history'].items())
    assert inventory('var')==before['state']
    baseline=verify_reference(ROOT);assert baseline['valid']
    integrity=dict(historical_files_checked=len(before['history']),historical_artifacts_unchanged=True,state_files_checked=len(before['state']),trusted_state_unchanged=True,baseline=baseline,protected_implementation_changed=False)
    write(OUT/'integrity.json',integrity)
    write(OUT/'acceptance.json',dict(verdict='PASS',scope='Real human decision recording and approved evidence pack; downstream frozen gate remains closed',
        reviewed_proposal_hash=b1['proposal_hash'],review_semantic_hash=records[0].semantic_hash,review_valid=True,
        evidence_pack_identity=identity,evidence_pack_sha256=hash_of(pack),pack_validation=check,warnings_preserved=len(spec.warnings),
        pedagogical_eligibility_before=before_eligibility.status,pedagogical_eligibility_after=after.status,pedagogical_specification_created=False,
        lesson_authoring_before=before_authoring.status,lesson_authoring_after=after_authoring.status,attempt02_disposition='REVISE',attempt02_pack_created=False,
        model_calls=0,provider_api_calls=0,integrity=integrity,active_baseline=before['baseline'],new_baseline_created=False))
    write(OUT/'evidence-manifest.json',{p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file()})
    print(json.dumps(read(OUT/'acceptance.json'),indent=2))
if __name__=='__main__':main()
