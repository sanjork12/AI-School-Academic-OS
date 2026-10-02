"""Two network-blocked replays and integrity closure of saved P6A.6c evidence."""
import importlib.util
from pathlib import Path
import socket
import sys
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('p6a6c_orchestration',HERE/'run_experiment.py')
experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)
from academic_os.ai_authoring.controlled import require_context
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_authoring.provider import OpenAICandidateAuthor
from academic_os.ai_qualification.reporting import rebuild
from academic_os.ai_qualification.storage import read, write_new
from academic_os.ai_qualification.reference_baseline import sha, verify_reference
from academic_os.ai_qualification.integrity import capture
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts
import json


def main():
    index=read(HERE/'experiment-index.json');before=read(HERE/'before.json')
    assert index['status']=='COMPLETE','Do not claim a complete experiment from partial evidence'
    assert index['totals']['attempted']==8
    original={p.as_posix():sha(p) for e in index['cases'] for p in Path(e['run_path']).rglob('*') if p.is_file()}
    original[(HERE/'experiment-index.json').as_posix()]=sha(HERE/'experiment-index.json')
    passes=[]
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Offline replay network blocked')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('Offline replay network blocked')), \
         patch.object(OpenAICandidateAuthor,'from_environment',side_effect=AssertionError('Offline replay provider blocked')), \
         patch.object(OpenAICandidateAuthor,'__init__',side_effect=AssertionError('Offline replay provider blocked')):
        for number in (1,2):
            inputs=read_inputs('var/p0_q2.sqlite3');rows=[];replayed_entries=[]
            for entry in index['cases']:
                directory=Path(entry['run_path']);manifest=read(directory/'run.json')
                ctx={k:manifest[k] for k in ('controlled_mode','controlled_case','controlled_case_sha256')}
                expected=require_context(**ctx,policy=manifest['acceptance_policy'])
                assert expected.controlled_case_id==entry['case_id']
                assert manifest['controlled_case_sha256']==entry['case_hash']
                assert manifest['authoring_brief']['sha256']==entry['brief_hash']
                folder=directory/'attempt-01';record=read(folder/'attempt.json')
                audit=read(folder/record['candidate_artifact_ref']);candidate=audit['candidate']
                validation=validate_candidate(candidate if candidate is not None else {},inputs,
                                              policy=manifest['acceptance_policy'],**ctx)
                if candidate is None:validation=validation.model_copy(update={'candidate_id':audit['candidate_id']})
                assert validation.model_dump(mode='json')==audit['validation'],entry['case_id']+' validation'
                if candidate is not None:
                    raw=read(folder/'raw_candidate.json')['raw_response']
                    assert raw==audit['raw_response']
                    assert json.loads(raw)==candidate['content'],'Original model content was changed'
                package=compose(candidate,inputs,policy=manifest['acceptance_policy'],**ctx) if validation.accepted else None
                assert package==audit['experimental_package'],entry['case_id']+' composition'
                report,path=rebuild(directory,output_dir=HERE/('replay-'+str(number))/('case-'+entry['case_id']))
                assert sha(path)==entry['report_sha256']
                assert report.attempts[0].model_dump(mode='json')==record==entry['attempt']
                assert experiment.roots(record)==entry['root_causes']
                replayed_entries.append(dict(entry,attempt=report.attempts[0].model_dump(mode='json')))
                rows.append(dict(case_id=entry['case_id'],binding_identical=True,validation_identical=True,
                    mathematics_identical=True,semantics_identical=True,provenance_identical=True,
                    composition_identical=True,decision_identical=True,report_identical=True,
                    original_returned_content_unchanged=True,report_sha256=sha(path)))
            aggregate=experiment.aggregate(replayed_entries)
            assert aggregate==index['totals']
            passes.append(dict(pass_number=number,cases=rows,aggregate=aggregate,aggregate_identical=True,model_api_calls=0))
        assert passes[0]['cases']==passes[1]['cases'] and passes[0]['aggregate']==passes[1]['aggregate']
        after=capture('var/p0_q2.sqlite3',experiment.ROOT)
        assert after==before['engineering']
        assert state()==before['trusted'] and counts()==before['decisions']
        assert experiment.history()==before['historical_files']
        assert all(sha(name)==h for name,h in original.items())
        references={v:verify_reference(experiment.ROOT,v) for v in ('v1','v1.1','v1.2','v1.3','v1.4','v1.5','v1.6')}
        assert all(r['valid'] for r in references.values())
    evidence=dict(status='PASS',replay_passes=passes,deterministic=True,network_blocked=True,
        provider_construction_blocked=True,offline_model_api_calls=0,original_run_artifacts=original,
        original_run_artifacts_unchanged=True,historical_artifacts_unchanged=True,
        historical_file_count=len(before['historical_files']),trusted_state_unchanged=True,
        baseline_unchanged=True,references=references,academic_approval=False,renderer_readiness=False)
    write_new(HERE/'offline-replay.json',evidence)
    experiment.emit(dict(offline_replay='PASS',passes=2,cases_per_pass=8,historical_files=len(before['historical_files']),
                         trusted_state_unchanged=True,model_api_calls=0))


if __name__=='__main__':main()
