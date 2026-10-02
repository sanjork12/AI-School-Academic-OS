"""Explicit offline P6A.6b evidence; no provider construction or network access."""
import json
from pathlib import Path
import socket
import sys
import tempfile
from unittest.mock import patch
from academic_os.ai_authoring.brief import digest
from academic_os.ai_authoring.controlled import CATALOG, MODE, context
from academic_os.ai_authoring.models import Candidate, ProviderContent
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_authoring.expressions import context_for
from academic_os.authored_math import summary_stats, display
from academic_os.ai_qualification.runner import execute
from academic_os.ai_qualification.reporting import rebuild
from academic_os.ai_qualification.storage import read, write_new
from academic_os.ai_qualification.reference_baseline import sha, verify_reference, load_active
from tests_p0.provenance_replay import symbolic_content, historical_replay, symbolic_replay
from tests_p0.test_ai_qualification import SequenceAuthor
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p6a6_controlled_inputs')
LIVE=Path('output/p6a5_live_symbolic_provenance/run-a9e2b94c7a40453fb1489bc63be3aa83')


def tests(mode, label):
    from tests_p0 import provenance_acceptance as runner
    runner.OUT=OUT
    if mode=='focused':
        runner.FOCUSED=(*runner.FOCUSED,'tests_p0.test_provenance_closure','tests_p0.test_controlled_inputs')
    elif mode=='postfreeze':
        runner.FOCUSED=('tests_p0.test_reference_freeze','tests_p0.test_reference_revision',
                        'tests_p0.test_ai_qualification','tests_p0.test_controlled_inputs')
        # The parent helper defers this real-conformance test; run it separately
        # in the full suite, which never filters tests.
    return runner.run('full' if mode=='full' else 'focused',label)


def evidence():
    i=read_inputs('var/p0_q2.sqlite3'); rows=[]
    for key,case in CATALOG.items():
        trace=[]
        report,path=execute(i,lambda _:SequenceAuthor(symbolic_content(case.inputs.model_dump()),trace),
            attempts=1,output_dir=OUT/'offline-cases'/key,experiment_type='offline_synthetic',
            provider='synthetic_test',model='synthetic-no-model',integrity_reader=lambda:{'offline_fixture':True},
            input_loader=lambda:i,**context(case))
        assert report.status=='complete' and report.aggregate_validation['accepted_count']==1
        assert report.attempts[0].controlled_input_binding_valid is True
        replay,replay_path=rebuild(path.parents[1]);assert replay==report and replay_path==path
        _,expected=context_for(case.inputs.model_dump())
        _,_,sd=summary_stats(**case.inputs.model_dump())
        rows.append(dict(controlled_case=case.model_dump(mode='json'),controlled_case_sha256=digest(case),
            expected={k:str(v) for k,v in expected.items()},sd=str(sd),display=display(sd),
            report_path=path.as_posix(),report_sha256=sha(path),brief=report.authoring_brief,
            all_gates_passed=True,deterministic_replay_equal=True,synthetic_author_invocations=len(trace),model_api_calls=0))
    history=historical_replay();symbolic=symbolic_replay()
    assert history['expression_semantics_passed']==40 and history['historically_accepted']==10
    assert history['status_counts']['INSUFFICIENT_EVIDENCE']==40 and symbolic['all_expectations_met']
    live=[]
    for folder in sorted(LIVE.glob('attempt-*')):
        record=read(folder/'attempt.json');audit=read(folder/record['candidate_artifact_ref'])
        validation=validate_candidate(audit['candidate'],i).model_dump(mode='json')
        assert validation==audit['validation'],folder
        assert compose(audit['candidate'],i)==audit['experimental_package'],folder
        live.append(dict(attempt_id=folder.name,validation_identical=True,composition_identical=True,
                         accepted=validation['accepted'],artifact_sha256=sha(folder/record['candidate_artifact_ref'])))
    with tempfile.TemporaryDirectory() as temp:
        report,path=rebuild(LIVE,output_dir=temp)
        assert sha(path)==sha(LIVE/'reports'/path.name)
        live_report=dict(sha256=sha(path),identical=True,attempts=report.attempt_count)
    result=dict(mode=MODE,cases=rows,case_count=len(rows),all_passed=True,
        p6a3_p6a4_historical_replay=history,p6a4_symbolic_controls=symbolic,
        p6a5_replay=live,p6a5_report_replay=live_report,model_api_calls=0,
        live_stress_experiment_started=False,network_guard=True)
    write_new(OUT/'offline-evidence.json',result)
    print(json.dumps(dict(cases=len(rows),p6a5_candidates=len(live),historical_semantics=40,
                          symbolic_controls_passed=symbolic['all_expectations_met'],model_api_calls=0)))


def close():
    from tests_p0.controlled_baseline import CHANGES, ADDITIONS
    from tests_p0.provenance_acceptance import source_hashes
    before=read(OUT/'before.json');manifest,descriptor=load_active('.')
    unchanged={n:h for n,h in before['files'].items() if n not in CHANGES}
    assert all(sha(n)==h for n,h in unchanged.items())
    assert state()==before['database'] and counts()==before['counts']
    assert digest(Candidate.model_json_schema())==before['candidate_schema_sha256']
    assert digest(ProviderContent.model_json_schema())==before['provider_schema_sha256']
    focused=read(OUT/'focused-tests.json');post=read(OUT/'postfreeze-tests.json');full=read(OUT/'full-tests.json')
    assert focused['successful'] and post['successful']
    assert full['failures']==0 and full['errors']==1
    assert 'test_preserved_project_files' in full['error_details'][0]['test']
    assert 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in full['error_details'][0]['traceback']
    assert full['source_hashes']==source_hashes() and full['sources_unchanged_during_tests']
    assert focused['source_hashes']==source_hashes() and post['source_hashes']==source_hashes()
    conformance=verify_reference('.');assert conformance['valid'],conformance
    evidence=read(OUT/'offline-evidence.json');assert evidence['all_passed']
    acceptance=dict(milestone='P6A.6b',verdict='PASS',scope='offline controlled-input infrastructure',
        controlled_mode=MODE,provenance_policy='sl10-provenance-required/1',candidate_contract='ai-author-candidate/2',
        files_added=list(ADDITIONS),files_modified=list(CHANGES)+['output/reference_freeze_active.json'],
        historical_files_verified=len(unchanged),historical_artifacts_unchanged=True,
        trusted_state_unchanged=True,database_sha256=sha('var/p0_q2.sqlite3'),
        schema_hashes_unchanged=True,model_api_calls=0,live_stress_experiment_started=False,
        focused={k:focused[k] for k in ('total','passed','failures','errors','module_counts')},
        postfreeze={k:post[k] for k in ('total','passed','failures','errors')},
        full={k:full[k] for k in ('total','passed','failures','errors','error_details')},
        known_unrelated_full_suite_error=True,baseline=dict(descriptor,protected_files=len(manifest['files'])),
        evidence_sha256=sha(OUT/'offline-evidence.json'),current_conformance=conformance,
        academic_approval=False,renderer_readiness=False)
    write_new(OUT/'acceptance.json',acceptance)
    print(json.dumps(acceptance,indent=2))


def replay():
    from tests_p0.provenance_acceptance import source_hashes
    saved=read(OUT/'offline-evidence.json');i=read_inputs('var/p0_q2.sqlite3')
    rows=[]
    for row in saved['cases']:
        directory=Path(row['report_path']).parents[1]
        report,path=rebuild(directory)
        assert sha(path)==row['report_sha256']
        record=report.attempts[0];folder=directory/record.attempt_id
        audit=read(folder/record.candidate_artifact_ref)
        ctx=context(row['controlled_case'])
        assert validate_candidate(audit['candidate'],i,**ctx).model_dump(mode='json')==audit['validation']
        assert compose(audit['candidate'],i,**ctx)==audit['experimental_package']
        rows.append(dict(controlled_case_id=record.controlled_case.controlled_case_id,identical=True))
    assert historical_replay()==saved['p6a3_p6a4_historical_replay']
    assert symbolic_replay()==saved['p6a4_symbolic_controls']
    for row in saved['p6a5_replay']:
        folder=LIVE/row['attempt_id'];record=read(folder/'attempt.json')
        audit=read(folder/record['candidate_artifact_ref'])
        assert sha(folder/record['candidate_artifact_ref'])==row['artifact_sha256']
        assert validate_candidate(audit['candidate'],i).model_dump(mode='json')==audit['validation']
        assert compose(audit['candidate'],i)==audit['experimental_package']
    with tempfile.TemporaryDirectory() as temp:
        _,path=rebuild(LIVE,output_dir=temp)
        assert sha(path)==saved['p6a5_report_replay']['sha256']
    write_new(OUT/'final-source-replay.json',dict(all_passed=True,cases=rows,p6a5_candidates_identical=10,
        historical_semantics_passed=40,historical_provenance_insufficient_evidence=40,
        source_hashes=source_hashes(),model_api_calls=0))
    print('Final-source replay PASS: 8 controlled cases; 10 unchanged P6A.5 candidates; P6A.3/P6A.4 unchanged.')


if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('P6A.6b offline network guard')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('P6A.6b offline network guard')):
        mode=sys.argv[1]
        if mode=='evidence':evidence()
        elif mode=='replay':replay()
        elif mode=='close':close()
        else:raise SystemExit(0 if tests(mode,sys.argv[2]) else 1)
