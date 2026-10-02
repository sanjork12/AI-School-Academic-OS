"""Read-only P6A.6 closure audit; all new evidence stays outside original runs."""
import copy
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT));os.chdir(ROOT)
from academic_os.ai_authoring.brief import compile_brief, digest
from academic_os.ai_authoring.controlled import CATALOG, context, require_context
from academic_os.ai_authoring.expressions import context_for, verify_solution_expressions
from academic_os.ai_authoring.provenance import verify_solution_provenance
from academic_os.ai_authoring.provider import OpenAICandidateAuthor
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_qualification.integrity import capture
from academic_os.ai_qualification.reference_baseline import load_active, sha, verify_reference
from academic_os.ai_qualification.reporting import rebuild
from academic_os.ai_qualification.storage import read,write_new,checked_member
from academic_os.authored_math import summary_stats,display,rational
from tests_p0.provenance_replay import symbolic_content
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

EXPECTED=dict(zip('ABCDEFGH',((10,'50','290'),(4,'10','29'),(4,'8','18'),(3,'4','6'),
    (1,'-3','9'),(1000000,'1000000000','1000001000000'),(2,'1/3','5/81'),(2,'0.21','0.0441'))))
DISPLAYS=dict(zip('ABCDEFGH',('2.00','1.00','0.71','0.47','0.00','1.00','0.06','0.11')))
COVERAGE=dict(zip('ABCDEFGH',(
    'integer mean / integer variance','fractional mean / integer variance',
    'fractional variance / irrational SD','fractional mean / fractional variance / irrational SD',
    'negative mean / singleton / zero variance','maximum n / large sums / cancellation',
    'rational-encoded inputs / repeating decimal SD','decimal source inputs / exact ROUND_HALF_UP tie')))
FIELDS=('first_term','second_term','mean','variance')


def assert_rejected(candidate,inputs,ctx):
    result=validate_candidate(candidate,inputs,**ctx)
    assert not result.accepted
    try:compose(candidate,inputs,**ctx)
    except ValueError:pass
    else:raise AssertionError('Composition bypassed rejection')
    return result


def audit():
    initial={p.relative_to(ROOT).as_posix():sha(p) for p in HERE.rglob('*') if p.is_file()}
    prior_closure=read(HERE/'closure.json')
    for path,expected in prior_closure['files_added'].items():assert sha(path)==expected,path
    assert len(prior_closure['files_added'])==122
    assert len(initial)==124  # 123 original files, plus this new audit script.
    original={k:v for k,v in initial.items() if k!=Path(__file__).relative_to(ROOT).as_posix()}
    assert len(original)==123
    index=read(HERE/'experiment-index.json');old=read(HERE/'before.json');prior_replay=read(HERE/'offline-replay.json')
    spec=importlib.util.spec_from_file_location('recorded_experiment',HERE/'run_experiment.py')
    experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)
    assert sha(HERE/'run_experiment.py')==read(HERE/'execution-start.json')['source_sha256']
    manifest,descriptor=load_active(ROOT)
    assert descriptor['active_reference_version']=='v1.6' and len(manifest['files'])==1578
    assert descriptor['manifest_sha256']=='f1a7de965222282fe7f98b8da7994f942f9e99e6ab076f6a8d90a313e0e2178a'
    assert verify_reference(ROOT)['valid']
    assert capture('var/p0_q2.sqlite3',ROOT)==old['engineering']
    assert state()==old['trusted'] and counts()==old['decisions']
    assert experiment.history()==old['historical_files']
    assert prior_replay['deterministic'] and prior_replay['offline_model_api_calls']==0
    assert read(HERE/'preflight.json')['retry_count']==0
    assert index['status']=='COMPLETE' and [e['case_id'] for e in index['cases']]==list(EXPECTED)
    dirs=list(HERE.glob('case-*/run-*'))
    assert len(dirs)==8 and len(list(HERE.rglob('run.json')))==8
    assert {p.resolve() for p in dirs}=={Path(e['run_path']).resolve() for e in index['cases']}
    assert len(list(HERE.rglob('provider_observation.json')))==8
    assert len(list(HERE.rglob('raw_candidate.json')))==8
    assert len(list(HERE.rglob('attempt.json')))==8
    assert len(list(HERE.rglob('ai-candidate-*.json')))==8
    inputs=read_inputs('var/p0_q2.sqlite3');rows=[];expressions=[];negative=[]
    run_ids=[];candidate_ids=[];request_ids=[];case_hashes=[];brief_hashes=[]
    for entry in index['cases']:
        key=entry['case_id'];directory=Path(entry['run_path']);run=read(directory/'run.json')
        assert directory.parent.name=='case-'+key and len(list(directory.parent.glob('run-*')))==1
        assert len(list(directory.glob('attempt-*')))==1
        folder=directory/'attempt-01';a=read(folder/'attempt.json');observation=read(folder/'provider_observation.json')
        for name,h in a['artifact_hashes'].items():checked_member(folder,name,h)
        saved=read(folder/a['candidate_artifact_ref']);candidate=saved['candidate'];validation=saved['validation']
        raw=read(folder/'raw_candidate.json')['raw_response'];brief=read(directory/'brief.json')
        ctx={k:run[k] for k in ('controlled_mode','controlled_case','controlled_case_sha256')}
        case=require_context(**ctx,policy=run['acceptance_policy'])
        assert case.controlled_case_id==key and case==CATALOG[key]
        required=dict(zip(('n','sum_x','sum_x2'),EXPECTED[key]))
        assert case.inputs.model_dump()==required==entry['required_inputs']
        assert candidate['content']['proposed_math_inputs']==required==candidate['content']['proposed_solution']['inputs']
        assert entry['returned_inputs']==a['returned_inputs']==required
        assert digest(case)==run['controlled_case_sha256']==entry['case_hash']
        assert digest(brief)==run['authoring_brief']['sha256']==a['brief_hash']==entry['brief_hash']==candidate['brief_sha256']
        assert brief==read(folder/'brief.json')==saved['brief']==entry['brief']==compile_brief(inputs,**ctx).model_dump(mode='json')
        assert brief['schema_version']=='authoring-brief/4'
        assert run['requested_attempt_count']==1 and run['experiment_type']=='live_normal'
        assert run['configuration']['retry_policy']==run['configuration']['repair_policy']=='none'
        assert a['case_id'] is None and a['provider_calls']==observation['call_count']==1
        assert a['provider_call_completed'] and observation['error_code'] is None
        assert observation['configuration']['model']==run['model']=='gpt-5.6-sol'
        assert 'application_mutation' not in observation
        assert a['provider_request_id']==observation['provider_request_id']==entry['provider_request_id']
        assert candidate['candidate_id']==a['candidate_id']==saved['candidate_id']
        assert a['accepted'] and validation['accepted'] and a['outcome']==entry['outcome']=='candidate_accepted'
        assert validation['controlled_input_binding_valid'] is True
        assert raw==saved['raw_response'] and json.loads(raw)==candidate['content']
        assert read(folder/'validation.json')==validation
        assert read(directory.parent/'case-result.json')==entry and a==entry['attempt']
        assert run['run_id']==entry['run_id']==directory.name
        assert read(directory/'completion.json')['completed_attempt_count']==1
        assert datetime.fromisoformat(run['created_at'])<=datetime.fromisoformat(a['started_at'])<=datetime.fromisoformat(a['completed_at'])
        assert read(folder/'started.json')['started_at']==a['started_at']
        _,derived=context_for(required);mean,variance,sd=summary_stats(**required)
        sol=candidate['content']['proposed_solution']
        assert all(rational(sol[f]['value'])==derived[f] for f in FIELDS)
        assert str(sd)==entry['expected_numeric_answer'] and sol['display_answer']==display(sd)==DISPLAYS[key]
        assert {f:str(v) for f,v in derived.items()}==entry['expected']
        if key=='H':assert str(sd)=='0.105'
        sem=verify_solution_expressions(candidate['content'])
        prov=verify_solution_provenance(candidate['content'],semantics=sem)
        assert sem==validation['verification_summary']['expressions']==entry['expression_verification']
        assert prov==validation['verification_summary']['provenance']==entry['provenance']
        for f in FIELDS:
            expr=sol[f]['expression'];check=prov['checks'][f]
            assert check['valid'] is True and check['status']=='PASSED' and check['expression_semantics_valid'] is True
            assert check['ast'] is not None and check['resolved_symbolic_sources']
            assert expr==json.loads(raw)['proposed_solution'][f]['expression']==entry['expressions'][f]
            category='derived-reference variance' if f=='variance' and 'first term' in expr else ('Unicode symbolic' if not expr.isascii() else 'ASCII symbolic')
            expressions.append(dict(case_id=key,field=f,expression=expr,category=category,parsed=True,
                semantic_pass=True,provenance_pass=True,literal_only=False,rewritten=False))
        # Synthetic in-memory audit probe only; never edits or replaces live evidence.
        alternative=copy.deepcopy(candidate);alternative['content']=symbolic_content(dict(n=5,sum_x='15',sum_x2='55'))
        rejected=assert_rejected(alternative,inputs,ctx)
        assert rejected.controlled_input_binding_valid is False
        assert rejected.math_valid and rejected.solution_valid and rejected.expression_semantics_valid and rejected.derivation_provenance_valid
        negative.append(dict(case_id=key,probe='old internally valid 5/15/55 triple',live_evidence_modified=False,
            internally_correct=True,input_binding=False,accepted=False,composition_rejected=True,
            reason=rejected.controlled_input_binding_reason))
        rows.append(dict(case_id=key,required_inputs=required,returned_inputs=a['returned_inputs'],case_hash=entry['case_hash'],
            brief_hash=entry['brief_hash'],run_id=entry['run_id'],run_path=entry['run_path'],candidate_id=a['candidate_id'],
            provider_request_id=a['provider_request_id'],started_at=a['started_at'],completed_at=a['completed_at'],
            timestamp_basis='Recorded application timestamps, UTC; not separate provider timestamps',
            raw_response_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),raw_response_artifact_sha256=sha(folder/'raw_candidate.json'),
            candidate_sha256=digest(candidate),audit_artifact_sha256=sha(folder/a['candidate_artifact_ref']),
            qualification_report_sha256=sha(entry['report_path']),outcome=a['outcome'],provider_calls=1,
            numeric_path=COVERAGE[key],derived_values={f:str(v) for f,v in derived.items()},
            returned_numeric_answer=sol['numeric_answer'],expected_numeric_answer=str(sd),display=display(sd),
            numeric_solution_verified=validation['verification_summary']['mathematics']['checks']))
        run_ids.append(entry['run_id']);candidate_ids.append(a['candidate_id']);request_ids.append(a['provider_request_id'])
        case_hashes.append(entry['case_hash']);brief_hashes.append(entry['brief_hash'])
    for values in (run_ids,candidate_ids,request_ids,case_hashes,brief_hashes):assert len(set(values))==8
    passes=[]
    for number in (1,2):
        results=[];rebuilt_entries=[]
        with tempfile.TemporaryDirectory() as temp:
            for entry in index['cases']:
                directory=Path(entry['run_path']);run=read(directory/'run.json');folder=directory/'attempt-01'
                a=read(folder/'attempt.json');saved=read(folder/a['candidate_artifact_ref']);c=saved['candidate']
                ctx={k:run[k] for k in ('controlled_mode','controlled_case','controlled_case_sha256')}
                v=validate_candidate(c,inputs,**ctx)
                assert v.model_dump(mode='json')==saved['validation']
                assert compose(c,inputs,**ctx)==saved['experimental_package']
                report,path=rebuild(directory,output_dir=Path(temp)/entry['case_id'])
                assert sha(path)==entry['report_sha256']==sha(entry['report_path'])
                assert report.attempts[0].model_dump(mode='json')==a
                rebuilt_entries.append(dict(entry,attempt=report.attempts[0].model_dump(mode='json')))
                results.append(dict(case_id=entry['case_id'],binding=v.controlled_input_binding_valid,
                    all_validation_identical=True,solution_identical=True,composition_identical=True,
                    decision_identical=True,report_sha256=sha(path)))
        totals=experiment.aggregate(rebuilt_entries);assert totals==index['totals']
        passes.append(dict(pass_number=number,cases=results,aggregate=totals,aggregate_identical=True,provider_calls=0))
    assert passes[0]['cases']==passes[1]['cases']
    assert passes[0]['aggregate']==passes[1]['aggregate']==prior_replay['replay_passes'][0]['aggregate']==prior_replay['replay_passes'][1]['aggregate']
    assert all(sha(n)==h for n,h in original.items())
    assert experiment.history()==old['historical_files']
    assert capture('var/p0_q2.sqlite3',ROOT)==old['engineering'] and state()==old['trusted'] and counts()==old['decisions']
    references={v:verify_reference(ROOT,v) for v in ('v1','v1.1','v1.2','v1.3','v1.4','v1.5','v1.6')}
    assert all(v['valid'] for v in references.values())
    result=dict(verdict='CLOSED / FROZEN / PASS FOR CONTROLLED STRESS SCOPE',experiment_id=index['experiment_id'],
        exact_run_count=8,case_run_mapping=rows,provider_call_identity=dict(distinct_recorded_calls=True,
            distinct_request_ids=8,distinct_candidate_ids=8,attempted=8,completed=8,provider_failures=0,
            evidence_scope='Recorded request IDs, single-call observations, timestamps, immutable raw output and frozen retry-disabled execution path; no statistical independence or independent network/billing audit is asserted.'),
        controlled_gate_audit=dict(authority='Saved application-owned run context, checked against approved catalog and hashed brief; never inferred from candidate output',
            acceptance_requires_binding_true=True,composition_revalidates=True,reporting_recomputes_binding=True,
            source_paths=['academic_os/ai_authoring/controlled.py','academic_os/ai_authoring/brief.py','academic_os/ai_authoring/service.py',
                'academic_os/ai_authoring/validation.py','academic_os/ai_qualification/runner.py','academic_os/ai_qualification/controlled_replay.py'],
            alternative_input_probes=negative,probe_scope='In-memory rejection checks only; no new live cases or changed saved candidates'),
        validation_totals=index['totals'],expression_inventory=expressions,
        expression_categories=dict(Counter(x['category'] for x in expressions)),semantics_passed=32,provenance_passed=32,
        literal_only_provenance_passes=0,expression_rewrites=0,offline_replay=dict(network_blocked=True,
            provider_construction_blocked=True,passes=passes,prior_two_pass_evidence_verified=True,deterministic=True),
        index_integrity=dict(valid=True,missing=0,duplicates=0,mismatches=0,sha256=sha(HERE/'experiment-index.json')),
        baseline_integrity=dict(version='v1.6',protected_files=1578,manifest_sha256=descriptor['manifest_sha256'],
            all_files_match=True,new_baseline_created=False,references=references),
        historical_integrity=dict(unchanged=True,files_verified=len(old['historical_files']),prior_outcomes_reinterpreted=False),
        trusted_state_integrity=dict(unchanged=True,database_sha256=state()['sha256'],review_governance_tables_unchanged=True,
            protected_snapshots_unchanged=True,academic_content_unchanged=True,renderer_artifacts_unchanged=True,
            candidates_promoted_to_trusted_state=0),
        original_artifact_hashes=original,original_artifacts_unchanged=True,original_artifact_count=123,
        api_provider_calls_during_closure=0,files_added=['output/p6a6_live_controlled_stress/audit_closure.py',
            'output/p6a6_live_controlled_stress/closure-audit.json'],existing_files_modified=[],
        audit_script_sha256=sha(__file__),
        establishes=['Direct controlled generation across eight predetermined numeric cases','Correct adherence to application-owned inputs',
            'Expression semantics across those cases','Symbolic operand provenance across those cases','Deterministic offline replay',
            'No recorded retries, repairs, replacements or mutations; frozen SDK retry setting is zero'],
        does_not_establish=['Statistical reliability','Arbitrary numeric robustness','Different topic robustness',
            'Different lesson-role robustness','Pedagogical quality','Production readiness','Academic approval',
            'Publication permission','Renderer readiness','Global model qualification'],
        p6a7_started=False,p6b_started=False)
    write_new(HERE/'closure-audit.json',result)
    print(json.dumps({k:result[k] for k in ('verdict','exact_run_count','expression_categories','semantics_passed','provenance_passed','api_provider_calls_during_closure','historical_integrity','existing_files_modified')},indent=2))


if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Closure network blocked')), \
         patch.object(socket.socket,'connect_ex',side_effect=AssertionError('Closure network blocked')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('Closure network blocked')), \
         patch.object(OpenAICandidateAuthor,'from_environment',side_effect=AssertionError('Closure provider blocked')), \
         patch.object(OpenAICandidateAuthor,'__init__',side_effect=AssertionError('Closure provider blocked')):
        audit()
