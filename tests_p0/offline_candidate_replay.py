"""P6A.1d acceptance-only, hash-bound transcription. No provider invocation."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import copy
import json
import re
from pathlib import Path
from decimal import Decimal, localcontext
from academic_os.ai_authoring.brief import compile_brief, current_binding, digest, role, serial
from academic_os.ai_authoring.validation import validate_candidate, task_refs
from academic_os.ai_authoring.service import read_inputs
from academic_os.ai_qualification.reference_baseline import sha, verify_reference
from academic_os.authored_math import summary_stats, rational
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import read_usable_snapshots
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT = Path('output/p6a1d_offline_replay')
RUN = 'run-3ce33e8d738f42df96182e5ca5409dd9'
FIELDS = ('first_term','second_term','mean','variance')


def transcriptions():
    return json.loads(Path('tests_p0/fixtures/p6a1d_transcription.json').read_text(encoding='utf-8'))['attempts']


def fixture(row, inputs):
    """Apply only an enumerated, hash-bound offline transcription; no string parsing."""
    path=Path(row['source'])
    if sha(path)!=row['source_hash']:raise ValueError('Historical candidate differs from inspected evidence')
    audit=json.loads(path.read_text(encoding='utf-8'))
    original=audit['candidate']
    if json.loads(audit['raw_response'])!=original['content']:raise ValueError('Raw and recorded content disagree')
    c=copy.deepcopy(original)
    for key in FIELDS:
        if original['content']['proposed_solution'][key]!=row['original_working'][key]:
            raise ValueError('Inspected working changed')
        c['content']['proposed_solution'][key]={'expression':row['original_working'][key],'value':row['values'][key]}
    brief=compile_brief(inputs, policy=LEGACY_POLICY)
    updates=dict(schema_version='ai-author-candidate/2',brief_ref=brief.identity,brief_sha256=digest(brief),
        current_inputs_sha256=current_binding(inputs),learning_requirement_refs=list(role(inputs).learning_requirement_refs),
        task_form_refs=list(task_refs(inputs)))
    mappings={key:dict(old=original[key],new=value,reason='Explicit current replay binding; not a historical model claim') for key,value in updates.items()}
    c.update(updates)
    provenance=dict(source_attempt_id=row['attempt_id'],source_candidate_hash=row['source_hash'],source_run_id=RUN,
        source_path=row['source'],source_raw_response_sha256=digest(audit['raw_response']),
        contract_version_old=original['schema_version'],contract_version_new=c['schema_version'],
        transformation_kind='explicit_offline_contract_fixture',binding_mappings=mappings,
        intermediate_mappings={key:dict(original=row['original_working'][key],new=c['content']['proposed_solution'][key]) for key in FIELDS},
        preserved_fields='All other fields deep-copied unchanged, including proposed inputs, final answers, question, scaffolds, candidate ID and historical model metadata.',
        metadata_policy='Original identity/metadata are provenance only; this fixture is not a new provider response.',
        lost_fields=[],automatic_repair=False)
    return c,provenance,audit


def diagnostic(report):
    s=report.verification_summary
    p=s.get('primary_failure',{})
    code=p.get('code');field=p.get('field')
    category=code
    if code=='solution_verification_invalid':
        category={'proposed_solution.inputs':'input_binding_invalid','numeric_answer':'numeric_answer_invalid',
                  'display_answer':'display_answer_invalid','exact_radicand':'exact_radicand_invalid'}.get(field,code)
    return dict(failure_class=category,validator_code=code,field=field,
        failed_stages=[k for k,v in s['stage_status'].items() if v=='FAILED'],
        not_evaluated=[k for k,v in s['stage_status'].items() if v=='NOT_EVALUATED'])


def probes(base):
    result=[]
    def add(name,attempt,path,value,accepted,category=None):
        c=copy.deepcopy(base[attempt]);target=c['content']
        for key in path[:-1]:target=target[key]
        target[path[-1]]=value
        result.append(dict(name=name,candidate=c,expected_accepted=accepted,expected_failure_class=category))
    for number,value in enumerate(('55/5 = 11','11 - 9 = 2','(10/4)^2 = 25/4','therefore 11')):
        add('grammar-'+str(number),0,('proposed_solution','first_term','value'),value,False,'numeric_encoding_invalid')
    add('wrong-value',0,('proposed_solution','first_term','value'),'10',False,'mathematical_value_invalid')
    add('wrong-variance',1,('proposed_solution','variance','value'),'1',False,'mathematical_value_invalid')
    add('wrong-numeric',1,('proposed_solution','numeric_answer'),'1.50',False,'numeric_answer_invalid')
    add('wrong-display',1,('proposed_solution','display_answer'),'1.11',False,'display_answer_invalid')
    add('wrong-input-binding',1,('proposed_solution','inputs'),dict(n=5,sum_x='15',sum_x2='55'),False,'input_binding_invalid')
    add('wrong-radicand',1,('proposed_solution','exact_radicand'),'2',False,'exact_radicand_invalid')
    add('equivalent-rational',0,('proposed_solution','first_term','value'),'55/5',True)
    for index,text in enumerate(('30/4','30 ÷ 4','30/4 = 999')):
        add('expression-'+str(index),1,('proposed_solution','first_term','expression'),text,True)
    return result


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:f.write(serial(value))


def run():
    if (OUT/'replay_report.json').exists():raise FileExistsError('Replay already recorded; refusing overwrite')
    db_before=state();count_before=counts()
    before=json.loads((OUT/'before.json').read_text())
    inputs=read_inputs('var/p0_q2.sqlite3')
    snapshots=read_usable_snapshots('var/p0_q2.sqlite3',PROTECTED_SNAPSHOTS)
    results=[];base=[];provenances=[]
    for row in transcriptions():
        c,p,audit=fixture(row,inputs);base.append(c);provenances.append(p)
        report=validate_candidate(c,inputs, policy=LEGACY_POLICY)
        old=validate_candidate(audit['candidate'],inputs, policy=LEGACY_POLICY)
        old_invalid=[k for k in FIELDS if not re.fullmatch(r'-?\d+(?:\.\d+|/\d+)?',row['original_working'][k],re.ASCII)]
        assert not audit['validation']['accepted'] and old.violations==('candidate_contract_version_unsupported',)
        assert len(old_invalid)==4
        sol=c['content']['proposed_solution'];i=c['content']['proposed_math_inputs']
        mean,var,sd=summary_stats(i['n'],i['sum_x'],i['sum_x2'])
        with localcontext() as ctx:
            ctx.prec=80;error=abs(Decimal(sol['numeric_answer'])-sd)
        checks=report.verification_summary.get('mathematics',{}).get('checks',{})
        valid=report.math_valid and report.solution_valid
        result=dict(attempt_id=row['attempt_id'],original_candidate_hash=row['source_hash'],v2_replay_fixture_hash=digest(c),
            old_result=audit['validation'],old_scalar_guard_rejections=old_invalid,original_under_v2=old.model_dump(mode='json'),
            new_result=report.model_dump(mode='json'),category='REPLAY_ACCEPTED' if report.accepted else 'REPLAY_REJECTED',
            primary_validation_status=diagnostic(report),math_status=report.verification_summary['stage_status']['math_valid'],
            solution_status=report.verification_summary['stage_status']['solution_valid'],composition_status=report.verification_summary['stage_status']['composition_valid'],
            evidence_classification='mathematically_valid' if valid else 'mathematically_invalid' if report.math_valid or report.verification_summary['stage_status']['math_valid']=='FAILED' else 'insufficient_evidence',
            mathematical_evidence=dict(recomputed_first_term=str(rational(i['sum_x2'])/i['n']),recomputed_second_term=str(mean*mean),
                recomputed_mean=str(mean),recomputed_variance=str(var),recomputed_sd=str(sd),preserved_numeric_answer=sol['numeric_answer'],
                numeric_absolute_error=str(error),tolerance='1e-40',checks=checks),provenance=p)
        results.append(result)
        write(OUT/'fixtures'/(row['attempt_id']+'.json'),dict(candidate=c,provenance=p))
        write(OUT/'diagnostics'/(row['attempt_id']+'.json'),result)
    probe_results=[]
    for probe in probes(base):
        r=validate_candidate(probe['candidate'],inputs, policy=LEGACY_POLICY);d=diagnostic(r)
        assert r.accepted==probe['expected_accepted'],probe['name']
        assert d['failure_class']==probe['expected_failure_class'],(probe['name'],d)
        probe_results.append(dict(name=probe['name'],validation=r.model_dump(mode='json'),diagnostic=d,expected_accepted=probe['expected_accepted']))
        write(OUT/'fixtures'/(probe['name']+'.json'),probe)
    assert db_before==state() and count_before==counts()
    changes=[name for name,v in before.items() if not Path(name).is_file() or sha(name)!=v['sha256'] or Path(name).stat().st_mtime_ns!=v['mtime_ns']]
    assert not changes,changes
    summary=dict(source_run=RUN,original_candidate_count=len(results),replay_candidate_count=len(results),
        accepted=sum(r['category']=='REPLAY_ACCEPTED' for r in results),rejected=sum(r['category']=='REPLAY_REJECTED' for r in results),inconclusive=0,
        per_attempt=results,probe_results=probe_results,provider_calls=0,automatic_repair=0,
        database_before=db_before,database_after=state(),counts_before=count_before,counts_after=counts(),
        snapshot_status={k:'valid_current_trusted_read' for k in snapshots},
        existing_files_hash_and_mtime_unchanged=True,checked_files=len(before),baseline_checks=[verify_reference('.',v) for v in ('v1.1','v1.2')],
        limitations=['Expression semantics are not validated; 30/4 = 999 with correct scalar may pass. No renderer readiness.',
            'Explicit rebinding to the current brief/input digest is test setup, not evidence the historical model emitted v2.',
            'Replay cannot predict future v2 model compliance, diversity, pedagogy or live acceptance rate.'])
    write(OUT/'provenance.json',provenances);write(OUT/'replay_report.json',summary)
    print(serial({k:summary[k] for k in ('accepted','rejected','inconclusive','provider_calls')}))


if __name__=='__main__':run()
