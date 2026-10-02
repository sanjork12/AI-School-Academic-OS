"""User-authorized P6A.6c orchestration; frozen application code is not modified.

One execution only. Eight distinct immutable runs, one call each. A preflight
failure stops before calls. No retry, repair, mutation or automatic resume.
"""
import json
import os
from pathlib import Path
import socket
import sys
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from academic_os.ai_authoring.brief import compile_brief, digest, ROLE
from academic_os.ai_authoring.controlled import CATALOG, MODE, context, validate_case
from academic_os.ai_authoring.expressions import context_for
from academic_os.ai_authoring.models import Candidate, ProviderContent
from academic_os.ai_authoring.provider import configured_model, OpenAICandidateAuthor
from academic_os.ai_authoring.provenance import POLICY, VERSION
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_qualification.integrity import capture
from academic_os.ai_qualification.observer import ObservedAuthor
from academic_os.ai_qualification.preflight import describe
from academic_os.ai_qualification.reference_baseline import load_active, sha, verify_reference
from academic_os.ai_qualification.reporting import CHECKS, rebuild
from academic_os.ai_qualification.runner import execute, now
from academic_os.ai_qualification.storage import read, write_new
from academic_os.authored_math import summary_stats, display
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT = Path('output/p6a6_live_controlled_stress')
MANIFEST_SHA = 'f1a7de965222282fe7f98b8da7994f942f9e99e6ab076f6a8d90a313e0e2178a'
DIMENSIONS = ('provider_call_completed','controlled_input_binding_valid',*CHECKS,'accepted')
EXPECTED = ((10,'50','290'),(4,'10','29'),(4,'8','18'),(3,'4','6'),
            (1,'-3','9'),(1000000,'1000000000','1000001000000'),(2,'1/3','5/81'),(2,'0.21','0.0441'))
FIELDS = ('first_term','second_term','mean','variance')


def emit(data):
    print(json.dumps(data,ensure_ascii=True),flush=True)


def history():
    result={}
    for folder in Path('output').iterdir():
        if folder.is_dir() and folder != OUT and (folder.name.startswith('p6a') or folder.name.startswith('reference_freeze')):
            result.update({p.as_posix():sha(p) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    result['output/reference_freeze_active.json']=sha('output/reference_freeze_active.json')
    return result


def roots(a):
    if a['outcome']=='provider_failure':return ['PROVIDER_FAILURE']
    if a['outcome']=='input_validation_failure':return ['TRUSTED_INPUT_FAILURE']
    if a['schema_valid'] is False:return ['SCHEMA_FAILURE']
    # Required-case failure takes precedence over math on the wrong triple.
    if a['controlled_input_binding_valid'] is False:return ['CONTROLLED_INPUT_BINDING_FAILURE']
    mapping=(('content_complete','CONTENT_FAILURE'),('scaffold_valid','CONTENT_FAILURE'),
        ('scope_valid','SCOPE_FAILURE'),('boundary_valid','SCOPE_FAILURE'),
        ('numeric_encoding_valid','NUMERIC_ENCODING_FAILURE'),('math_valid','MATH_FAILURE'),
        ('solution_valid','SOLUTION_FAILURE'),('expression_semantics_valid','EXPRESSION_SEMANTIC_FAILURE'),
        ('derivation_provenance_valid','DERIVATION_PROVENANCE_FAILURE'),('composition_valid','COMPOSITION_FAILURE'))
    failures=list(dict.fromkeys(label for key,label in mapping if a[key] is False))
    return failures or ([] if a['accepted'] else ['UNCLASSIFIED_REJECTION'])


def aggregate(entries):
    evaluated=[e for e in entries if e.get('attempt') is not None]
    reasons=Counter(reason for e in evaluated for reason in e['root_causes'])
    return dict(attempted=sum(e['attempt']['provider_calls'] for e in evaluated),
        completed=sum(e['attempt']['provider_call_completed'] is True for e in evaluated),
        provider_failures=sum(e['attempt']['outcome']=='provider_failure' for e in evaluated),
        accepted=sum(e['attempt']['accepted'] for e in evaluated),
        rejected=sum(e['attempt']['outcome'] in ('candidate_validation_rejected','candidate_schema_failure') for e in evaluated),
        dimensions={k:dict(passed=sum(e['attempt'][k] is True for e in evaluated),
            failed=sum(e['attempt'][k] is False for e in evaluated),
            not_evaluated=sum(e['attempt'][k] is None for e in evaluated)) for k in DIMENSIONS},
        root_cause_distribution=dict(sorted(reasons.items())),retry_count=0,repair_count=0,
        replacement_calls=0,candidate_mutations=0,symbolic_rewrites=0,controlled_input_corrections=0)


def main():
    # Exclusive marker prevents a second invocation from replacing calls.
    write_new(OUT/'execution-start.json',dict(experiment_id='P6A.6c-controlled-eight-cases',started_at=now(),
        source_sha256=sha(__file__),intended_calls=8,automatic_resume=False))
    os.environ['ACADEMIC_OS_AUTHOR_MODEL']='gpt-5.6-sol'
    provider=None;entries=[];phase='engineering_conformance';preflight={};before=None;prior=None
    try:
        with patch.object(socket.socket,'connect',side_effect=AssertionError('No network during preflight')), \
             patch.object(socket,'create_connection',side_effect=AssertionError('No network during preflight')):
            manifest,descriptor=load_active(ROOT)
            assert descriptor['active_reference_version']=='v1.6' and descriptor['manifest_sha256']==MANIFEST_SHA
            assert len(manifest['files'])==1578 and verify_reference(ROOT)['valid']
            before=capture('var/p0_q2.sqlite3',ROOT);assert before['freeze_inventory_matches']
            prior=history();trusted=state();decisions=counts()
            assert trusted['sha256']==read('output/p6a6_controlled_inputs/acceptance.json')['database_sha256']
            write_new(OUT/'before.json',dict(engineering=before,historical_files=prior,trusted=trusted,decisions=decisions))
            phase='model_and_credentials'
            assert configured_model()=='gpt-5.6-sol'
            assert bool(os.environ.get('OPENAI_API_KEY')),'credentials_missing'
            assert Candidate.model_fields['schema_version'].default=='ai-author-candidate/2'
            assert POLICY=='sl10-provenance-required/1' and VERSION=='sl10-derivation-provenance/1'
            assert MODE=='sl10-controlled-input/1'
            phase='trusted_read_and_case_briefs';inputs=read_inputs('var/p0_q2.sqlite3')
            for (key,case),triple in zip(CATALOG.items(),EXPECTED,strict=True):
                case=validate_case(case);values=case.inputs.model_dump()
                assert (values['n'],values['sum_x'],values['sum_x2'])==triple
                brief=compile_brief(inputs,policy=POLICY,**context(case))
                assert brief.schema_version=='authoring-brief/4' and brief.controlled_case==case
                _,derived=context_for(values);_,_,sd=summary_stats(**values)
                plan=describe(SimpleNamespace(command='qualify-ai-author',attempts=1,topic='standard-deviation',
                    profile='standard-lesson',role=ROLE,output_dir=OUT/('case-'+key)),brief,before,configured_model(),[])
                entries.append(dict(case_id=key,required_inputs=values,case_hash=digest(case),brief_hash=digest(brief),
                    brief=brief.model_dump(mode='json'),expected={k:str(v) for k,v in derived.items()},
                    expected_numeric_answer=str(sd),expected_display=display(sd),preflight_plan=plan,
                    run_id=None,run_path=None,provider_request_id=None,attempt=None,root_causes=[],outcome='NOT_RUN'))
            assert len(entries)==8
            phase='provider_construction'
            provider=OpenAICandidateAuthor.from_environment()
            assert provider.model=='gpt-5.6-sol' and provider.client.max_retries==0
            phase='preflight_integrity'
            assert capture('var/p0_q2.sqlite3',ROOT)==before and history()==prior
            assert state()==trusted and counts()==decisions
            preflight=dict(status='PASSED',phase='complete',model=provider.model,process_local_model=True,
                credentials_present=True,provider_constructed=True,provider_requests_during_preflight=0,
                manifest=descriptor,protected_files=1578,candidate_contract='ai-author-candidate/2',
                controlled_mode=MODE,brief_version='authoring-brief/4',policy=POLICY,provenance_verifier=VERSION,
                retry_count=0,repair_count=0,mutation_enabled=False,catalog_validated=8,
                candidate_schema_sha256=digest(Candidate.model_json_schema()),provider_schema_sha256=digest(ProviderContent.model_json_schema()),
                trusted_state_unchanged=True,historical_evidence_unchanged=True)
        write_new(OUT/'preflight.json',preflight)
    except Exception as exc:
        if provider is not None:provider.client.close()
        failure=dict(status='FAILED',phase=phase,error_type=type(exc).__name__,live_calls=0,
                     action='STOPPED; no retry or infrastructure modification')
        write_new(OUT/'preflight.json',failure)
        write_new(OUT/'experiment-index.json',dict(experiment_id='P6A.6c-controlled-eight-cases',status='PREFLIGHT_FAILED',
            case_ids=list(CATALOG),cases=entries,preflight=failure,provider_calls=0))
        emit(failure);return 2
    emit(dict(preflight='PASSED',cases=8,model=provider.model,provider_calls_so_far=0))
    stopped=None
    try:
        for entry in entries:
            key=entry['case_id']
            assert configured_model()=='gpt-5.6-sol' and provider.client.max_retries==0
            assert capture('var/p0_q2.sqlite3',ROOT)==before and history()==prior
            current=read_inputs('var/p0_q2.sqlite3');ctx=context(CATALOG[key])
            assert digest(compile_brief(current,policy=POLICY,**ctx))==entry['brief_hash']
            emit(dict(case=key,status='CALL_START',maximum_calls_for_case=1))
            observed=ObservedAuthor(provider)  # No adversarial case_id: no prompt or candidate mutation.
            report,path=execute(current,lambda _:observed,attempts=1,output_dir=OUT/('case-'+key),
                experiment_type='live_normal',provider='openai',model=provider.model,
                integrity_reader=lambda:capture('var/p0_q2.sqlite3',ROOT),
                input_loader=lambda:read_inputs('var/p0_q2.sqlite3'),policy=POLICY,**ctx)
            assert report.attempt_count==1 and observed.last.get('call_count')==1
            record=report.attempts[0];a=record.model_dump(mode='json');folder=path.parents[1]/record.attempt_id
            audit=read(folder/record.candidate_artifact_ref)
            assert not observed.last.get('application_mutation')
            assert observed.last['configuration']['model']=='gpt-5.6-sol'
            candidate=audit['candidate'];sol=candidate['content']['proposed_solution'] if candidate else None
            entry.update(run_id=report.identity,run_path=path.parents[1].as_posix(),report_path=path.as_posix(),
                report_sha256=sha(path),provider_request_id=record.provider_request_id,attempt=a,root_causes=roots(a),
                outcome=a['outcome'],returned_inputs=a['returned_inputs'],
                expressions={f:sol[f]['expression'] for f in FIELDS} if sol else None,
                numerical_solution=sol,numeric_verification=audit['validation']['verification_summary'].get('mathematics'),
                expression_verification=audit['validation']['verification_summary'].get('expressions'),
                provenance=audit['validation']['verification_summary'].get('provenance'))
            write_new(OUT/('case-'+key)/'case-result.json',entry)
            emit(dict(case=key,outcome=a['outcome'],binding=a['controlled_input_binding_valid'],
                      provenance=a['derivation_provenance_valid'],request_id=a['provider_request_id']))
            assert report.baseline_integrity['unchanged'] and capture('var/p0_q2.sqlite3',ROOT)==before
    except Exception as exc:
        stopped=dict(error_type=type(exc).__name__,action='STOPPED; no replacement, retry or code change')
        emit(stopped)
    finally:
        provider.client.close()
    index=dict(experiment_id='P6A.6c-controlled-eight-cases',completed_at=now(),
        status='COMPLETE' if all(e['attempt'] is not None for e in entries) else 'INCOMPLETE',
        model='gpt-5.6-sol',topic='standard-deviation',profile='standard-lesson',role=ROLE,
        controlled_mode=MODE,policy=POLICY,provenance_verifier=VERSION,brief_version='authoring-brief/4',
        preflight=preflight,cases=entries,totals=aggregate(entries),stop_reason=stopped,
        academic_approval=False,renderer_readiness=False,statistical_benchmark=False)
    write_new(OUT/'experiment-index.json',index)
    emit(dict(status=index['status'],totals=index['totals']))
    return 0 if index['status']=='COMPLETE' else 2


if __name__=='__main__':raise SystemExit(main())
