"""Create v1.6 only after exact-source P6A.6b offline verification succeeds."""
from datetime import datetime, timezone
from pathlib import Path
from academic_os.ai_authoring.brief import serial, digest
from academic_os.ai_authoring.models import Candidate, ProviderContent
from academic_os.ai_qualification.storage import read, write_new
from academic_os.ai_qualification.reference_baseline import sha, production_files
from tests_p0.provenance_acceptance import source_hashes
from tests_p0.reference_revision import live_comparisons
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p6a6_controlled_inputs')
CHANGES=(
    'academic_os/ai_authoring/brief.py','academic_os/ai_authoring/service.py','academic_os/ai_authoring/validation.py',
    'academic_os/ai_qualification/models.py','academic_os/ai_qualification/runner.py',
    'academic_os/ai_qualification/reporting.py','academic_os/ai_qualification/preflight.py',
    'academic_os/ai_qualification/__main__.py','academic_os/ai_qualification/reference_baseline.py',
    'tests_p0/test_reference_revision.py')
ADDITIONS=(
    'academic_os/ai_authoring/controlled.py','academic_os/ai_qualification/controlled_replay.py',
    'tests_p0/test_controlled_inputs.py','tests_p0/controlled_acceptance.py','tests_p0/controlled_baseline.py',
    'docs/P6A6_CONTROLLED_INPUT_STRESS.md')


def build():
    target=Path('output/reference_freeze_v1_6/reference_manifest.json')
    if target.parent.exists():raise FileExistsError('Refusing to replace v1.6')
    start=read(OUT/'before.json');descriptor=start['active_descriptor'];parent=Path(descriptor['manifest_path'])
    assert read('output/reference_freeze_active.json')==descriptor and sha(parent)==descriptor['manifest_sha256']
    old=read(parent);focused=read(OUT/'focused-tests.json');evidence=read(OUT/'offline-evidence.json')
    assert focused['successful'] and focused['sources_unchanged_during_tests']
    assert focused['source_hashes']==source_hashes(),'Sources changed after verification'
    replay=read(OUT/'final-source-replay.json')
    assert replay['all_passed'] and replay['source_hashes']==source_hashes()
    assert evidence['all_passed'] and evidence['case_count']==8 and evidence['model_api_calls']==0
    for row in evidence['cases']:assert sha(row['report_path'])==row['report_sha256']
    changed={n for n,h in start['files'].items() if sha(n)!=h}
    assert changed==set(CHANGES),(changed,set(CHANGES))
    assert set(production_files(Path('.')))-set(old['production_inventory'])==set(ADDITIONS[:2])
    assert state()==start['database'] and counts()==start['counts']
    assert digest(Candidate.model_json_schema())==start['candidate_schema_sha256']
    assert digest(ProviderContent.model_json_schema())==start['provider_schema_sha256']
    live=live_comparisons(read('output/reference_freeze/reference_manifest.json'))
    files=dict(old['files'])
    for n in start['files']:files[n]=sha(n)
    for n in CHANGES+ADDITIONS:files[n]=sha(n)
    for p in OUT.rglob('*'):
        if p.is_file():files[p.as_posix()]=sha(p)
    target.parent.mkdir()
    saved=target.parent/'parent-active-descriptor.json';write_new(saved,descriptor);files[saved.as_posix()]=sha(saved)
    parent_files={p.as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    historical=dict(old['historical_baselines']);historical['v1.5']=parent_files
    manifest=dict(old,reference_version='v1.6',parent_reference='v1.5',revision_type='controlled_input_binding',
        created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(Path('.')),
        historical_baselines=historical,invariance_evidence=live,
        controlled_input_revision=dict(mode='sl10-controlled-input/1',brief='authoring-brief/4',
            parent_manifest=descriptor,authorization='P6A.6b offline implementation and freeze after successful verification',
            deltas=[dict(path=n,before=start['files'][n],after=sha(n)) for n in CHANGES],additions=list(ADDITIONS),
            focused_tests=dict(path=(OUT/'focused-tests.json').as_posix(),sha256=sha(OUT/'focused-tests.json')),
            offline_evidence=dict(path=(OUT/'offline-evidence.json').as_posix(),sha256=sha(OUT/'offline-evidence.json')),
            model_api_calls=0,candidate_schema_changed=False,provider_schema_changed=False,
            parser_changed=False,provenance_changed=False,authored_math_changed=False,renderer_changed=False,
            trusted_state_changed=False,historical_acceptance_rewritten=False))
    write_new(target,manifest)
    active=dict(active_reference_version='v1.6',manifest_path=target.as_posix(),manifest_sha256=sha(target))
    Path('output/reference_freeze_active.json').write_text(serial(active),encoding='utf-8')
    write_new(OUT/'baseline-creation.json',dict(active,protected_files=len(files),live_comparisons=live))
    print(serial(dict(active,protected_files=len(files))))


if __name__=='__main__':build()
