"""Capture offline evidence only. Paid/live qualification is never invoked here."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import argparse
import json
from pathlib import Path
import unittest
from academic_os.ai_qualification.runner import execute
from academic_os.ai_qualification.stress import synthetic_content,cases,SyntheticStressAuthor
from academic_os.ai_qualification.integrity import capture
from academic_os.ai_qualification.models import QualificationReport
from academic_os.ai_qualification.storage import write_new,file_hash,read
from tests_p0.test_ai_qualification import QualificationTests,SequenceAuthor
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts
from tests_p0.reference_freeze import snapshot_status


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=Path('output/p6a1_offline_acceptance'))
    out=parser.parse_args().output_dir
    before=read('output/p6a1_offline_acceptance/before.json')
    out.mkdir(parents=True,exist_ok=True)
    if not (out/'before.json').exists():write_new(out/'before.json',before)
    with (out/'tests.txt').open('x',encoding='utf-8') as log:
        result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('tests_p0.test_ai_qualification'))
    stats={'total':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
           'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped)}
    demos={}
    if result.wasSuccessful():
        i=QualificationTests.inputs
        bad=synthetic_content();bad['proposed_solution']['display_answer']='-1.00'
        schema=synthetic_content();schema['approved']=True
        values=iter([synthetic_content(),bad,schema,RuntimeError('synthetic provider failure')]+[synthetic_content() for _ in range(6)])
        trace=[]
        normal,path=execute(i,lambda case:SequenceAuthor(next(values),trace),attempts=10,output_dir=out/'normal_synthetic_demo',
            experiment_type='offline_synthetic',provider='synthetic_test',model='synthetic-no-model',
            integrity_reader=lambda:capture('var/p0_q2.sqlite3',Path.cwd()),input_loader=lambda:i, policy=LEGACY_POLICY)
        demos['normal']={'report':str(path),'outcomes':normal.operational_outcomes,'attempts':normal.attempt_count,'identical_briefs':len(set(trace))==1}
        catalog=[dict(case_id=k,**v) for k,v in cases().items()]
        stress,path=execute(i,lambda case:SyntheticStressAuthor(case),attempts=len(catalog),output_dir=out/'stress_synthetic_demo',
            experiment_type='offline_synthetic_stress',provider='offline_synthetic',model='synthetic-no-model',
            integrity_reader=lambda:capture('var/p0_q2.sqlite3',Path.cwd()),input_loader=lambda:i,stress_cases=catalog, policy=LEGACY_POLICY)
        demos['stress']={'report':str(path),'summary':stress.stress_summary}
        if stress.stress_summary['unexpectedly_accepted'] or stress.stress_summary['correctly_blocked']!=16:
            raise AssertionError('A forbidden synthetic stress case was not correctly blocked')
    changed=[name for name,sha in before['files'].items() if not Path(name).is_file() or file_hash(name)!=sha]
    after=state();after_counts=counts();snapshots=snapshot_status()
    checks={'protected_files_unchanged':not changed,'database_unchanged':after==before['database'],
            'decisions_unchanged':after_counts==before['counts'],
            'snapshot_usability_unchanged':snapshots==read('output/reference_freeze/before.json')['snapshots']}
    write_new(out/'report.schema.json',QualificationReport.model_json_schema())
    receipt={'format':'p6a1-offline-acceptance/1','new_tests':stats,'protected_file_count':len(before['files']),
        'checks':checks,'changed_files':changed,'demonstrations':demos,
        'live_calls_executed':0,'live_model_qualification':'NOT RUN; requires explicit operator --live command',
        'full_suite':'not run; historical missing PPTX error remains documented in the freeze receipt',
        'database_after':after,'counts_after':after_counts,'snapshots':snapshots}
    write_new(out/'acceptance.json',receipt)
    print(json.dumps({'tests':stats,'checks':checks,'demos':demos},indent=2))
    return 0 if result.wasSuccessful() and all(checks.values()) else 1


if __name__=='__main__':raise SystemExit(main())
