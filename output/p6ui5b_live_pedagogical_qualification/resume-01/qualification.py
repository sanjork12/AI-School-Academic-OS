"""Isolated experiment harness; never modifies or replaces frozen contracts."""
import os, sys, json, re, hashlib, socket, copy
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT)); sys.path.append(str(ROOT/'tmp/p6ui-deps'))
from academic_os.curriculum_ingestion.service import IngestionService, serial
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.pedagogy_evidence.service import PedagogicalEvidenceService
from academic_os.pedagogy_evidence.models import Proposal
from academic_os.pedagogy_evidence.validation import hash_of, validate_proposal
from academic_os.ai_authoring.provider import configured_model
from academic_os.ai_qualification.reference_baseline import verify_reference, sha
from pydantic import ValidationError
OUT=Path(__file__).resolve().parent
SID='263509477cf795f3c47a4ab68edc2a34e379a664880c6cab4254ad87b9b4cd1e'
EXPECTED='gpt-5.6-sol'
DIMENSIONS=['provider_success','contract_parse_valid','source_binding_valid','tier_binding_valid','learning_intention_binding_valid','success_criteria_valid','activity_scope_valid','check_alignment_valid','pedagogical_adapter_valid','role_family_valid','provenance_valid','proposal_status_valid','no_forged_approval','overall_proposal_valid']
def now(): return datetime.now(timezone.utc).isoformat()
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f: f.write(serial(v)+b'\n')
def bytes_write(p,v):
    with Path(p).open('xb') as f:f.write(v)
def configuration():
    # Explicit run-local configuration supplied by the user in the resume request.
    os.environ['ACADEMIC_OS_AUTHOR_MODEL']=EXPECTED
    model=configured_model()
    assert model==EXPECTED and os.environ.get('OPENAI_API_KEY')
    return model
def services():
    ingestion=IngestionService()
    learning=GovernedLearningService(AcademicCapabilityService(ingestion),ROOT/'output/p6ui4_learning_specification/specifications')
    return ingestion,learning
def inventory(folder):
    return {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/folder).rglob('*') if p.is_file() and not p.is_relative_to(OUT) and '__pycache__' not in p.parts}
def unchanged():
    b=read(OUT/'before.json'); changed=[]
    for group in ('history','state','protected'):
        changed.extend(p for p,h in b[group].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h)
    added_state=sorted(set(inventory('var'))-set(b['state']))
    assert not changed and not added_state,(changed,added_state)
    assert verify_reference(ROOT)['valid']
    return dict(historical_files_checked=len(b['history']),protected_files_checked=len(b['protected']),state_files_checked=len(b['state']),historical_unchanged=True,trusted_state_unchanged=True,state_files_added=[],protected_implementation_changed=False,baseline='v1.13')
def preflight():
    assert not (OUT/'preflight.json').exists()
    model=configuration(); baseline=verify_reference(ROOT); assert baseline['valid']
    active=read(ROOT/'output/reference_freeze_active.json'); manifest=read(ROOT/active['manifest_path'])
    before=dict(active=active,history=inventory('output'),state=inventory('var'),protected=manifest['files'])
    write(OUT/'before.json',before)
    ingestion,learning=services()
    try:
        with patch('socket.socket.connect',side_effect=AssertionError('No preflight network')):
            spec=learning.read_learning_spec(SID); assert learning.validate_learning_spec(spec).valid
            s=PedagogicalEvidenceService(learning,OUT/'unused-review-store')
            b=s.build_pedagogical_authoring_brief(spec)
            assert serial(b)==serial(s.build_pedagogical_authoring_brief(spec))
            assert serial(b)==serial(read(ROOT/'output/p6ui5a_pedagogical_evidence/authoring-brief.json'))
            assert spec.curriculum_scope.source_ids==['EDX-4MA1-F-2.8-A']
            schema=Proposal.model_json_schema(); assert callable(validate_proposal)
            # Exercise the independent frozen validator with the already-frozen fixture.
            assert validate_proposal(read(ROOT/'output/p6ui5a_pedagogical_evidence/positive-fixture.json'),b,learning)['valid']
    finally: ingestion.close()
    write(OUT/'authoring-brief.json',b); write(OUT/'proposal-schema.json',schema)
    instruction='Return exactly one complete JSON object conforming to the supplied frozen pedagogical-evidence-proposal/1 JSON Schema. This is an unapproved MODEL_PROPOSED proposal for human review only. Copy the entire brief unchanged into the brief field. Preserve source_wording exactly from learning_objectives[0].official_text, including unclear glyphs; do not replace it with canonical description. Set every evidence_basis origin to MODEL_PROPOSED and classification to PROPOSED; bind brief_hash to the supplied hash. Propose only success criteria, activity constraints, check alignment, adapter and permitted role families within the schema. No lesson prose, questions, answers, slides, explanations, examples, review decisions, approvals, publication or SD calculation assumptions. The frozen validator below defines linkage constraints; satisfy it without changing any input. Choose a bounded proposal independently; do not supply multiple candidates. Include every schema field, including defaulted version/status/provenance fields.'
    payload=dict(brief=b.model_dump(mode='json'),brief_sha256=hash_of(b),proposal_schema=schema,frozen_validator=(ROOT/'academic_os/pedagogy_evidence/validation.py').read_text(encoding='utf-8'))
    request=dict(model=model,store=False,max_output_tokens=24000,input=[dict(role='system',content=instruction),dict(role='user',content=serial(payload).decode('utf-8'))],text={'format':{'type':'json_object'}})
    write(OUT/'request.json',request)
    import openai
    write(OUT/'preflight.json',dict(status='PASS',started_at=now(),resolved_provider='openai',resolved_model=model,model_configuration_source='USER_EXPLICIT_RESUME_CONFIGURATION_RUN_LOCAL',key_available=True,
        brief_id=hash_of(b),brief_sha256=hash_of(b),learning_spec_id=SID,learning_spec_hash=hash_of(spec),source_objective_id=spec.curriculum_scope.source_ids[0],tier=spec.curriculum_scope.tier,policy_version=b.policy_version,
        schema_sha256=hash_of(schema),request_sha256=hash_of(request),runner_sha256=sha(__file__),sdk_version=openai.__version__,planned_calls=5,retry=0,repair=0,replacement=0,mutation=0,provider_calls=0,baseline=active,
        configuration_fingerprint=hash_of({'model':model,'base_url':os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1'),'organization':os.getenv('OPENAI_ORG_ID'),'project':os.getenv('OPENAI_PROJECT_ID')})))
    unchanged(); print('PREFLIGHT PASS: gpt-5.6-sol; no provider calls',flush=True)

def diagnostic(raw,brief,provider_success,learning):
    dims={k:None for k in DIMENSIONS}; dims['provider_success']=provider_success
    reasons=[]; p=None; report=None
    try: p=Proposal.model_validate(raw)
    except ValidationError as exc:
        dims['contract_parse_valid']=False
        errors=exc.errors(include_url=False,include_input=False)
        return dict(dimensions={**dims,'overall_proposal_valid':False},reason_codes=['CONTRACT_PARSE_FAILURE'],schema_errors=errors,validation=validate_proposal(raw,brief,learning))
    dims['contract_parse_valid']=True
    b=brief; s=b['source_learning_spec']; obj=s['learning_objectives'][0]; intention=s['learning_intentions'][0]; can=s['canonical_semantics'][0]
    def check(key,ok,code):
        dims[key]=bool(ok)
        if not ok: reasons.append(code)
    check('source_binding_valid',p.brief.model_dump(mode='json')==b and p.source_id==obj['source_id'] and p.source_wording==obj['official_text'],'SOURCE_BINDING_INVALID')
    check('tier_binding_valid',p.tier==obj['tier'] and p.brief.source_learning_spec.curriculum_scope.tier==s['curriculum_scope']['tier'],'TIER_BINDING_INVALID')
    check('learning_intention_binding_valid',all(c.linked_learning_intention==intention['intention_id'] for c in p.success_criteria) and all(c.intention_id==intention['intention_id'] for c in p.check_alignment),'LEARNING_INTENTION_BINDING_INVALID')
    cs={c.criterion_id:c for c in p.success_criteria}; acts={a.activity_id:a for a in p.activity_scope}; ch={c.check_id:c for c in p.check_alignment}
    criteria_ok=len(cs)==len(p.success_criteria)
    for c in p.success_criteria:
        expected=('SYMBOL_REPRESENTATION','MEANING_MATCHES_REVIEWED_SYMBOL') if c.observable_student_action=='INTERPRET_SYMBOL' else ('RELATION_REPRESENTATION','SYMBOL_MATCHES_STATED_RELATION')
        criteria_ok &= (c.conditions,c.quality_or_completion_rule)==expected and c.linked_learning_intention==intention['intention_id']
    check('success_criteria_valid',criteria_ok,'SUCCESS_CRITERION_BINDING_OR_RULE_INVALID')
    activity_ok=len(acts)==len(p.activity_scope) and {c for a in p.activity_scope for c in a.criterion_ids}==set(cs)
    for a in p.activity_scope:
        activity_ok &= len(a.criterion_ids)==len(set(a.criterion_ids))
        for cid in a.criterion_ids:
            activity_ok &= cid in cs and a.response_mode==('SYMBOL_INTERPRETATION' if cid in cs and cs[cid].observable_student_action=='INTERPRET_SYMBOL' else 'SYMBOL_SELECTION')
    check('activity_scope_valid',activity_ok,'ACTIVITY_SCOPE_INVALID')
    check_ok=len(ch)==len(p.check_alignment) and {c.criterion_id for c in p.check_alignment}==set(cs)
    for c in p.check_alignment:
        a=acts.get(c.activity_id)
        check_ok &= bool(a and c.criterion_id in a.criterion_ids and c.evidence_form==a.response_mode and c.intention_id==intention['intention_id'])
    check('check_alignment_valid',check_ok,'CHECK_ALIGNMENT_BROKEN')
    a=p.pedagogical_adapter; adapter_ok=(a.canonical_id,a.action_meaning)==(can['canonical_id'],can['description'])
    for refs,ids in [(a.criterion_ids,cs),(a.activity_ids,acts),(a.check_ids,ch)]:adapter_ok &= set(refs)==set(ids) and len(refs)==len(set(refs))
    check('pedagogical_adapter_valid',adapter_ok,'ADAPTER_SCOPE_INVALID')
    roles=a.candidate_role_families
    check('role_family_valid',len(roles)==len(set(roles)) and ({x.category for x in p.activity_scope}|{'CONCEPT_CHECK'}).issubset(roles),'ROLE_FAMILY_UNSUPPORTED')
    bases=[r.evidence_basis for r in [*p.success_criteria,*p.activity_scope,*p.check_alignment,a]]
    check('provenance_valid',all((x.brief_hash,x.source_id,x.intention_id)==(hash_of(b),obj['source_id'],intention['intention_id']) for x in bases) and len({x.origin for x in bases})==1,'PROVENANCE_INVALID')
    dims['proposal_status_valid']=p.status=='PROPOSED'; dims['no_forged_approval']=True
    report=validate_proposal(raw,brief,learning)
    dims['overall_proposal_valid']=provider_success and report['valid']
    if not report['valid']: reasons.extend(report['errors'])
    if not provider_success: reasons.insert(0,'PROVIDER_FAILURE')
    return dict(dimensions=dims,reason_codes=list(dict.fromkeys(reasons)),validation=report,model_proposed_origin=all(x.origin=='MODEL_PROPOSED' for x in bases))

def live():
    pre=read(OUT/'preflight.json'); assert pre['status']=='PASS'; assert sha(__file__)==pre['runner_sha256']
    assert not (OUT/'live-started.json').exists(), 'Never rerun a live experiment'
    model=configuration(); request=read(OUT/'request.json'); brief=read(OUT/'authoring-brief.json')
    assert hash_of(request)==pre['request_sha256'] and hash_of(brief)==pre['brief_sha256']
    assert hash_of({'model':model,'base_url':os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1'),'organization':os.getenv('OPENAI_ORG_ID'),'project':os.getenv('OPENAI_PROJECT_ID')})==pre['configuration_fingerprint']
    unchanged()
    from openai import OpenAI
    ingestion,learning=services()
    try:
        with OpenAI(max_retries=0,timeout=180.0) as client:
            write(OUT/'live-started.json',dict(started_at=now(),planned_calls=5,retries=0))
            for n in range(1,6):
                unchanged(); assert sha(__file__)==pre['runner_sha256']
                attempt=OUT/f'attempt-{n:02}'; attempt.mkdir()
                write(attempt/'request-metadata.json',dict(attempt_id=f'P6UI5B-R01-{n:02}',started_at=now(),model=model,brief_hash=pre['brief_sha256'],request_sha256=pre['request_sha256'],max_retries=0))
                print(f'CALL {n}/5 START',flush=True)
                observation=dict(model=model,started_at=now(),provider_success=False)
                raw=None; text=''
                try:
                    response=client.responses.with_raw_response.create(**request)
                    # Preserve exact HTTP response body; authorization/request headers are never stored.
                    bytes_write(attempt/'raw-provider-response.json',response.http_response.content)
                    value=response.parse(); text=value.output_text
                    observation.update(provider_success=value.status=='completed',status=value.status,response_id=value.id,request_id=response.headers.get('x-request-id'),response_model=value.model,usage=value.usage.model_dump(mode='json') if value.usage else None)
                    bytes_write(attempt/'raw-output.txt',text.encode('utf-8'))
                except Exception as exc:
                    body=getattr(getattr(exc,'response',None),'content',None)
                    if body is not None and not (attempt/'raw-provider-response.json').exists(): bytes_write(attempt/'raw-provider-response.json',body)
                    observation.update(status='PROVIDER_FAILURE',failure_class=type(exc).__name__,request_id=getattr(exc,'request_id',None),http_status=getattr(exc,'status_code',None))
                observation['ended_at']=now(); write(attempt/'provider-observation.json',observation)
                try: raw=json.loads(text)
                except (ValueError,TypeError): pass
                if raw is not None:
                    write(attempt/'parsed-response.json',raw)
                    result=diagnostic(raw,brief,observation['provider_success'],learning)
                    if result['dimensions']['contract_parse_valid']:write(attempt/'parsed-proposal.json',raw)
                else:
                    state='PROVIDER_FAILURE' if not observation['provider_success'] else 'CONTRACT_PARSE_FAILURE'
                    result=dict(dimensions={**{k:None for k in DIMENSIONS},'provider_success':observation['provider_success'],'contract_parse_valid':False,'overall_proposal_valid':False},reason_codes=[state],validation=None)
                write(attempt/'validation.json',result)
                status='VALID_FOR_HUMAN_REVIEW' if result['dimensions']['overall_proposal_valid'] else ('PROVIDER_FAILURE' if not observation['provider_success'] else ('CONTRACT_PARSE_FAILURE' if not result['dimensions']['contract_parse_valid'] else 'VALIDATION_REJECTED'))
                write(attempt/'completion.json',dict(status=status,first_reason=result['reason_codes'][0] if result['reason_codes'] else None,all_reasons=result['reason_codes']))
                print(f'CALL {n}/5 {status}',flush=True)
        write(OUT/'live-complete.json',dict(calls=5,completed_at=now(),retry=0,repair=0,replacement=0,mutation=0))
    finally: ingestion.close()

if __name__=='__main__':
    if sys.argv[1]=='preflight':preflight()
    elif sys.argv[1]=='live':live()
