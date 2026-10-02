"""Offline synthetic demonstration and integrity receipt. No live API calls."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import argparse
import hashlib
import json
from pathlib import Path
import unittest
from academic_os.ai_authoring.brief import serial
from academic_os.ai_authoring.models import AuthoringBrief, Candidate, ProviderContent, Validation
from academic_os.ai_authoring.service import run_once, save
from tests_p0.test_ai_authoring import AIAuthoringTests, FakeAuthor, synthetic
from tests_p0.reference_freeze import snapshot_status
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts


def main():
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=Path('output/p6a_ai_authoring'))
    out=p.parse_args().output_dir
    out.mkdir(parents=True,exist_ok=False)
    before=state();before_counts=counts()
    freeze=json.loads(Path('output/reference_freeze/before.json').read_text(encoding='utf-8'))
    def protected():
        return {name:hashlib.sha256(Path(name).read_bytes()).hexdigest()==expected for name,expected in freeze['files'].items()}
    before_files=protected()
    with (out/'tests.txt').open('x',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AIAuthoringTests))
    report=dict(total=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),successful=result.wasSuccessful())
    if result.wasSuccessful():
        accepted=AIAuthoringTests.good
        bad=synthetic();bad['proposed_solution']['display_answer']='9.99'
        rejected=run_once(AIAuthoringTests.i,FakeAuthor(bad), policy=LEGACY_POLICY)
        save(accepted,out/'synthetic_accepted');save(rejected,out/'synthetic_rejected')
        (out/'authoring_brief.json').write_text(serial(AIAuthoringTests.brief),encoding='utf-8')
    for name,model in (('authoring-brief',AuthoringBrief),('ai-author-candidate',Candidate),('provider-content',ProviderContent),('ai-candidate-validation',Validation)):
        (out/(name+'.schema.json')).write_text(serial(model.model_json_schema()),encoding='utf-8')
    after_files=protected();after=state();after_counts=counts();snapshots=snapshot_status()
    checks=dict(protected_files_unchanged=all(before_files.values()) and all(after_files.values()),
        database_unchanged=before==after==freeze['database'],decisions_unchanged=before_counts==after_counts==freeze['counts'],
        snapshots_usable_and_unchanged=snapshots==freeze['snapshots'])
    receipt=dict(format='p6a-offline-acceptance/1',tests=report,checks=checks,protected_file_count=len(after_files),
        live_api_called=False,live_integration_status='not_run_requires_explicit_operator_command',
        scope='Only SL-10 experimental candidate; existing renderer remains closed to AI package',
        full_suite_status='not_rerun_this_task; previous freeze recorded 984 passed and one missing historical PPTX error',
        database_before=before,database_after=after,counts_before=before_counts,counts_after=after_counts,snapshots=snapshots)
    (out/'acceptance.json').write_text(serial(receipt),encoding='utf-8')
    print(serial({'tests':report,'checks':checks,'output':str(out)}))
    return 0 if result.wasSuccessful() and all(checks.values()) else 1


if __name__=='__main__':raise SystemExit(main())
