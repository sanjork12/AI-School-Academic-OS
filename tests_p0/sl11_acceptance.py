"""Offline P6A.7b acceptance, historical replay, and gated v1.7 creation."""
from datetime import datetime, timezone
from pathlib import Path
import contextlib
import json
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
from academic_os.ai_authoring.brief import digest, serial
from academic_os.ai_authoring.models import Candidate, ProviderContent
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_authoring import role_authoring as sl11
from academic_os.ai_authoring.roles import SL11, support_binding
from academic_os.ai_authoring.controlled import validate_case, context
from academic_os.ai_authoring.validation import validate_candidate, compose
from academic_os.ai_qualification.role_offline import evaluate, save, rebuild as rebuild_role
from academic_os.ai_qualification.reporting import rebuild
from academic_os.ai_qualification.storage import read, write_new
from academic_os.ai_qualification.reference_baseline import sha, production_files, verify_reference
from tests_p0.provenance_acceptance import source_hashes
from tests_p0.provenance_replay import historical_replay, symbolic_replay
from tests_p0.test_sl11_authoring import fixture, negative_cases
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT = Path('output/p6a7b_sl11')
CHANGES = ('academic_os/ai_authoring/validation.py', 'academic_os/ai_qualification/reference_baseline.py',
           'tests_p0/test_reference_revision.py')
ADDITIONS = ('academic_os/ai_authoring/numerical.py', 'academic_os/ai_authoring/roles.py',
    'academic_os/ai_authoring/role_authoring.py', 'academic_os/ai_qualification/role_offline.py',
    'tests_p0/test_sl11_authoring.py', 'tests_p0/sl11_acceptance.py', 'docs/P6A7_SL11_ROLE_AUTHORING.md')


def tests(mode):
    from tests_p0 import provenance_acceptance as runner
    runner.OUT = OUT
    runner.FOCUSED = (*runner.FOCUSED, 'tests_p0.test_controlled_inputs',
        'tests_p0.test_provenance_closure', 'tests_p0.test_sl11_authoring')
    if mode == 'focused': return runner.run('focused', 'focused-tests')
    # Full discovery is deliberately unfiltered, including actual conformance.
    if mode == 'full': return runner.run('full', 'full-tests')
    before = source_hashes()
    suite = unittest.defaultTestLoader.loadTestsFromNames(('tests_p0.test_reference_freeze',
        'tests_p0.test_reference_revision','tests_p0.test_ai_qualification','tests_p0.test_sl11_authoring'))
    with (OUT/'postfreeze-tests.log').open('x',encoding='utf-8') as log:
        result = unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    data = dict(total=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        successful=result.wasSuccessful(), source_hashes=source_hashes(),
        sources_unchanged_during_tests=before==source_hashes(),model_api_calls=0,
        details=[dict(test=str(t),traceback=s) for t,s in result.errors+result.failures])
    write_new(OUT/'postfreeze-tests.json',data)
    print(serial({k:v for k,v in data.items() if k != 'source_hashes'}))
    return result.wasSuccessful() and data['sources_unchanged_during_tests']


def evidence():
    i = read_inputs('var/p0_q2.sqlite3'); hint = support_binding(i)
    candidates = [('uncontrolled',fixture(i),{})]
    for name,values in [('primary',dict(n=5,sum_x='30',sum_x2='190')),
                        ('fraction',dict(n=2,sum_x='0.5',sum_x2='0.5'))]:
        case = validate_case(dict(controlled_case_id='SL11-'+name,inputs=values))
        ctx = dict(controlled_case=case,controlled_case_sha256=digest(case))
        candidates.append((name,fixture(i,values,**ctx),ctx))
    positive=[]
    for name,c,ctx in candidates:
        record=evaluate(c,i,support=hint,**ctx); assert record['validation']['accepted'],record
        path=save(record,OUT/'offline-qualification');assert rebuild_role(path,i)==record
        positive.append(dict(name=name,path=path.as_posix(),sha256=sha(path),all_gates_passed=True))
    c=candidates[0][1]; negative=[]
    for name,(bad,code) in negative_cases(c).items():
        record=evaluate(bad,i,support=hint);v=record['validation']
        assert not v['accepted'] and code in v['violations'],(name,v)
        path=save(record,OUT/'offline-qualification');assert rebuild_role(path,i)==record
        negative.append(dict(name=name,expected_diagnostic=code,path=path.as_posix(),sha256=sha(path),rejected=True))
    for name,bad,options,code in (
        ('missing_hint',c,dict(support=None),'application_formula_hint_missing_or_changed'),
        ('controlled_mismatch',fixture(i,dict(n=6,sum_x='30',sum_x2='174'),**candidates[1][2]),
         dict(support=hint,**candidates[1][2]),'controlled_input_n_mismatch')):
        record=evaluate(bad,i,**options);assert not record['validation']['accepted'] and code in record['validation']['violations']
        path=save(record,OUT/'offline-qualification');assert rebuild_role(path,i)==record
        negative.append(dict(name=name,expected_diagnostic=code,path=path.as_posix(),sha256=sha(path),rejected=True))
    opposite=validate_candidate(c,i);assert not opposite.accepted and 'role_binding_invalid' in opposite.violations
    write_new(OUT/'reverse-role-rejection.json',opposite)
    negative.append(dict(name='sl11_to_sl10',rejected=True,expected_diagnostic='role_binding_invalid',
        path=(OUT/'reverse-role-rejection.json').as_posix(),sha256=sha(OUT/'reverse-role-rejection.json')))
    result=dict(all_passed=True,positive=positive,negative=negative,positive_count=len(positive),
        negative_count=len(negative),model_api_calls=0,provider_invocations=0,source_hashes=source_hashes())
    write_new(OUT/'offline-evidence.json',result)
    print('Offline evidence:',len(positive),'positive;',len(negative),'negative controls PASS')


def replay():
    i=read_inputs('var/p0_q2.sqlite3');rows=[];reports=[]
    for root in ('output/p6a5_live_symbolic_provenance','output/p6a6_live_controlled_stress'):
        audits=sorted(Path(root).rglob('ai-candidate-*.json'))
        assert len(audits)==(10 if 'p6a5' in root else 8)
        runs=set()
        for path in audits:
            audit=read(path);v=audit['validation'];ctx={}
            if v.get('controlled_mode'):ctx=context(v['controlled_case'])
            actual=validate_candidate(audit['candidate'],i,**ctx).model_dump(mode='json')
            assert actual==v,('Validation changed',path)
            assert compose(audit['candidate'],i,**ctx)==audit['experimental_package'],('Composition changed',path)
            rows.append(dict(path=path.as_posix(),sha256=sha(path),validation_identical=True,composition_identical=True))
            runs.add(path.parent.parent)
        for run in sorted(runs):
            with tempfile.TemporaryDirectory() as temp:
                report,path=rebuild(run,output_dir=temp)
                original=run/'reports'/path.name
                assert sha(path)==sha(original),(run,path)
                reports.append(dict(run=run.as_posix(),report_sha256=sha(path),identical=True))
    history=historical_replay();symbolic=symbolic_replay()
    assert history['expression_semantics_passed']==40 and symbolic['all_expectations_met']
    result=dict(all_passed=True,historical_candidates=rows,reports=reports,p6a3_p6a4=history,
        symbolic_controls=symbolic,source_hashes=source_hashes(),model_api_calls=0)
    write_new(OUT/'historical-replay.json',result)
    print('Historical replay PASS:',len(rows),'candidate validations/compositions;',len(reports),'reports')


def integrity():
    before=read(OUT/'before.json')
    changed={n for n,h in before['files'].items() if sha(n)!=h}
    assert changed==set(CHANGES),(changed,set(CHANGES))
    historical={n:h for n,h in before['historical_files'].items() if n!='output/reference_freeze_active.json'}
    assert all(sha(n)==h for n,h in historical.items())
    assert state()==before['database'] and counts()==before['counts']
    assert digest(Candidate.model_json_schema())==before['candidate_schema_sha256']
    assert digest(ProviderContent.model_json_schema())==before['provider_schema_sha256']
    return dict(historical_files_checked=len(historical),unchanged_parent_protected_files=len(before['files'])-len(changed),
        historical_artifacts_unchanged=True,trusted_state_unchanged=True,database_sha256=sha('var/p0_q2.sqlite3'),
        candidate_schema_unchanged=True,provider_schema_unchanged=True)


def baseline():
    target=Path('output/reference_freeze_v1_7/reference_manifest.json')
    if target.parent.exists():raise FileExistsError('Refusing to replace v1.7')
    start=read(OUT/'before.json');descriptor=start['active_descriptor'];parent=Path(descriptor['manifest_path'])
    assert read('output/reference_freeze_active.json')==descriptor and sha(parent)==descriptor['manifest_sha256']
    for name in ('focused-tests','offline-evidence','historical-replay'):
        evidence=read(OUT/(name+'.json'))
        assert evidence.get('successful',evidence.get('all_passed')) and evidence['source_hashes']==source_hashes(),name
    assert read(OUT/'focused-tests.json')['sources_unchanged_during_tests']
    proof=integrity();old=read(parent)
    assert set(production_files(Path('.')))-set(old['production_inventory'])==set(ADDITIONS[:4])
    for row in read(OUT/'offline-evidence.json')['positive']+read(OUT/'offline-evidence.json')['negative']:
        assert sha(row['path'])==row['sha256']
    files=dict(old['files'])
    for name in CHANGES+ADDITIONS:files[name]=sha(name)
    for p in OUT.rglob('*'):
        if p.is_file():files[p.as_posix()]=sha(p)
    target.parent.mkdir()
    saved=target.parent/'parent-active-descriptor.json';write_new(saved,descriptor);files[saved.as_posix()]=sha(saved)
    historical=dict(old['historical_baselines'])
    historical['v1.6']={p.as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest=dict(old,reference_version='v1.7',parent_reference='v1.6',
        revision_type='sl11_role_generalized_numerical_authoring',created_at=datetime.now(timezone.utc).isoformat(),
        files=files,production_inventory=production_files(Path('.')),historical_baselines=historical,
        role_authoring_revision=dict(role_ref=SL11.role_ref,support_policy=SL11.version,
            brief='numerical-role-authoring-brief/1',candidate_contract='ai-author-candidate/2',
            authorization='P6A.7b offline implementation; v1.7 after successful verification',
            deltas=[dict(path=n,before=start['files'][n],after=sha(n)) for n in CHANGES],additions=list(ADDITIONS),
            integrity=proof,model_api_calls=0,renderer_integration=False,
            verification={n:dict(path=(OUT/(n+'.json')).as_posix(),sha256=sha(OUT/(n+'.json')))
                          for n in ('focused-tests','offline-evidence','historical-replay')}))
    write_new(target,manifest)
    active=dict(active_reference_version='v1.7',manifest_path=target.as_posix(),manifest_sha256=sha(target))
    Path('output/reference_freeze_active.json').write_text(serial(active),encoding='utf-8')
    assert verify_reference('.')['valid']
    write_new(OUT/'baseline-creation.json',dict(active,protected_files=len(files)))
    print(serial(dict(active,protected_files=len(files))))


def close():
    proof=integrity();focused=read(OUT/'focused-tests.json');post=read(OUT/'postfreeze-tests.json');full=read(OUT/'full-tests.json')
    assert focused['successful'] and post['successful']
    assert all(r['source_hashes']==source_hashes() and r['sources_unchanged_during_tests'] for r in (focused,post,full))
    # Retain the existing unrelated missing-file error honestly; never suppress it.
    known=(full['failures']==0 and full['errors']==1 and 'test_preserved_project_files' in full['error_details'][0]['test']
           and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in full['error_details'][0]['traceback'])
    assert full['successful'] or known,full['error_details']+full['failure_details']
    conformance=verify_reference('.');assert conformance['valid'],conformance
    evidence=read(OUT/'offline-evidence.json');replay=read(OUT/'historical-replay.json')
    acceptance=dict(milestone='P6A.7b',verdict='PASS',scope='SL-11 offline role-generalized numerical authoring',
        files_added=list(ADDITIONS),files_modified=list(CHANGES)+['output/reference_freeze_active.json'],
        integrity=proof,positive_controls=evidence['positive_count'],negative_controls=evidence['negative_count'],
        historical_candidate_replays=len(replay['historical_candidates']),historical_report_replays=len(replay['reports']),
        tests={name:{k:r[k] for k in ('total','failures','errors','successful')} for name,r in [('focused',focused),('postfreeze',post),('full',full)]},
        known_unrelated_full_suite_error=known,full_suite_error_details=full['error_details'],
        baseline=read(OUT/'baseline-creation.json'),current_conformance=conformance,
        model_api_calls=0,provider_invocations=0,academic_approval=False,ready_for_rendering=False,publishable=False)
    write_new(OUT/'acceptance.json',acceptance)
    print(serial(acceptance))


if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('P6A.7b offline network guard')), \
         patch.object(socket,'create_connection',side_effect=AssertionError('P6A.7b offline network guard')):
        mode=sys.argv[1]
        if mode in ('focused','postfreeze','full'):raise SystemExit(0 if tests(mode) else 1)
        {'evidence':evidence,'replay':replay,'baseline':baseline,'close':close}[mode]()
