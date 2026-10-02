"""Explicit v1.5 freeze only after exact-source offline tests and replay succeed."""
import json
from datetime import datetime,timezone
from pathlib import Path
from academic_os.ai_qualification.reference_baseline import sha,production_files
from tests_p0.reference_revision import live_comparisons,write_new
from tests_p0.provenance_replay import historical_replay,symbolic_replay
from tests_p0.provenance_acceptance import source_hashes

OUT=Path('output/p6a4_derivation_provenance')
CHANGES=(
 'academic_os/ai_authoring/models.py','academic_os/ai_authoring/brief.py',
 'academic_os/ai_authoring/validation.py','academic_os/ai_authoring/service.py',
 'academic_os/ai_authoring/__main__.py','academic_os/ai_qualification/models.py',
 'academic_os/ai_qualification/reporting.py','academic_os/ai_qualification/runner.py',
 'academic_os/ai_qualification/preflight.py','academic_os/ai_qualification/__main__.py',
 'academic_os/ai_qualification/reference_baseline.py','tests_p0/test_direct_v2_preflight.py',
 'tests_p0/test_reference_revision.py',
)
ADDITIONS=(
 'academic_os/ai_authoring/provenance.py','tests_p0/provenance_replay.py',
 'tests_p0/test_derivation_provenance.py','tests_p0/provenance_acceptance.py',
 'tests_p0/provenance_baseline.py','docs/P6A4_DERIVATION_PROVENANCE.md',
)


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def build():
    target=Path('output/reference_freeze_v1_5/reference_manifest.json')
    if target.parent.exists():raise FileExistsError('Refusing to replace v1.5 evidence')
    parent=Path('output/reference_freeze_v1_4/reference_manifest.json')
    start=read(OUT/'before.json');old=read(parent)
    assert sha(parent)==start['parent_manifest_sha256']
    assert sha('output/reference_freeze_active.json')==start['files']['output/reference_freeze_active.json']
    tests=read(OUT/'focused-tests.json')
    assert tests['successful'] and tests['sources_unchanged_during_tests']
    assert tests['source_hashes']==source_hashes(),'Source changed after passing focused tests'
    for name,digest in start['files'].items():
        if name not in CHANGES and sha(name)!=digest:raise ValueError('Unauthorized delta: '+name)
    actual_changes={name for name,digest in start['files'].items() if sha(name)!=digest}
    assert actual_changes==set(CHANGES),(actual_changes,set(CHANGES))
    assert set(production_files(Path('.')))-set(old['production_inventory'])=={'academic_os/ai_authoring/provenance.py'}
    history=historical_replay();symbolic=symbolic_replay()
    assert history==read(OUT/'historical-replay.json')==historical_replay()
    assert symbolic==read(OUT/'symbolic-controls.json')==symbolic_replay()
    assert history['status_counts']==dict(PASSED=0,FAILED=0,INSUFFICIENT_EVIDENCE=40,NOT_EVALUATED=0)
    assert symbolic['all_expectations_met']
    assert sha('var/p0_q2.sqlite3')==old['database_baseline']['sha256']
    live=live_comparisons(read('output/reference_freeze/reference_manifest.json'))
    target.parent.mkdir()
    descriptor=target.parent/'parent-active-descriptor.json'
    write_new(descriptor,read('output/reference_freeze_active.json'))
    parent_files={p.as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    historical=dict(old['historical_baselines']);historical['v1.4']=parent_files
    files=dict(old['files']);files.update(parent_files);files[descriptor.as_posix()]=sha(descriptor)
    for name in CHANGES+ADDITIONS:files[name]=sha(name)
    # Protect all P6A.3 closure evidence, including artifacts created after its manifest.
    for folder in (Path('output/p6a3_expression_verification'),OUT):
        for p in folder.rglob('*'):
            if p.is_file():files[p.as_posix()]=sha(p)
    manifest=dict(old,reference_version='v1.5',parent_reference='v1.4',
        revision_type='derivation_provenance_verification',created_at=datetime.now(timezone.utc).isoformat(),
        files=files,production_inventory=production_files(Path('.')),historical_baselines=historical,
        invariance_evidence=live,provenance_revision=dict(
            authorization='P6A.4b explicitly authorizes implementation and v1.5 after offline validation.',
            verifier='sl10-derivation-provenance/1',policy='sl10-provenance-required/1',
            candidate_contract='ai-author-candidate/2',generation_brief='authoring-brief/3',
            parent_manifest=dict(path=parent.as_posix(),sha256=sha(parent)),
            deltas=[dict(path=n,before=start['files'][n],after=sha(n)) for n in CHANGES],
            additions=list(ADDITIONS),focused_tests=dict(path=(OUT/'focused-tests.json').as_posix(),sha256=sha(OUT/'focused-tests.json')),
            parser_changed=False,scalar_math_changed=False,renderer_added=False,model_api_calls=0,
            historical_acceptance_rewritten=False,academic_scope_change=False))
    write_new(target,manifest)
    active=dict(active_reference_version='v1.5',manifest_path=target.as_posix(),manifest_sha256=sha(target))
    Path('output/reference_freeze_active.json').write_text(json.dumps(active,indent=2)+'\n',encoding='utf-8')
    write_new(OUT/'baseline-creation.json',dict(**active,protected_files=len(files),live_comparisons=live))
    print(json.dumps(dict(**active,protected_files=len(files))))


if __name__=='__main__':build()
