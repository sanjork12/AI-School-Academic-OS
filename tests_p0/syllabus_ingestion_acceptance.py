"""Verify historical bytes and gate a non-overwriting P6UI.3A / v1.9 revision."""
import json
from pathlib import Path
from datetime import datetime,timezone
from academic_os.ai_qualification.reference_baseline import sha,production_files,verify_reference
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/p6ui3a'
CHANGES={'add_source_ids.py','console_api/adapter.py','console_api/app.py','console_api/models.py',
    'extract_syllabus.py','frontend/package.json','frontend/playwright.console.config.ts',
    'frontend/src/components/authoring-console.tsx','frontend/tests/console/console.spec.ts',
    'parse_curriculum.py','requirements-p6ui.txt','validate_curriculum.py','frontend/README.md',
    'academic_os/ai_qualification/reference_baseline.py','tests_p0/test_reference_revision.py'}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')
def integrity():
    before=read(OUT/'before.json');history={p:h for p,h in before['history'].items() if p!='output/reference_freeze_active.json'}
    changed=[p for p,h in history.items() if sha(ROOT/p)!=h];assert not changed,changed
    assert sha(ROOT/'var/p0_q2.sqlite3')==before['database_sha256']
    return dict(historical_files_checked=len(history),historical_artifacts_unchanged=True,manifests_through_v1_8_unchanged=True,
        database_sha256=before['database_sha256'],trusted_state_unchanged=True,model_api_calls=0)
def freeze():
    target=ROOT/'output/reference_freeze_v1_9/reference_manifest.json'
    if target.parent.exists():raise FileExistsError('Never overwrite v1.9')
    before=read(OUT/'before.json');active=before['active'];parent=ROOT/active['manifest_path'];old=read(parent)
    assert read(ROOT/'output/reference_freeze_active.json')==active and sha(parent)==active['manifest_sha256']
    backend=read(OUT/'backend-tests.json');browser=read(OUT/'frontend-e2e.json')['stats'];accept=read(OUT/'api-acceptance.json')
    assert backend['successful'] and backend['total']>=191
    assert browser['expected']==3 and browser['unexpected']==0 and browser['skipped']==0
    assert accept['parse_run']['status']=='succeeded' and accept['model_api_calls']==0
    assert accept['capability']['CURRICULUM_BROWSABLE'] and not accept['capability']['LESSON_GENERATION_SUPPORTED']
    proof=integrity();changes={p for p,h in old['files'].items() if sha(ROOT/p)!=h};assert changes==CHANGES,changes^CHANGES
    files={p:sha(ROOT/p) for p in old['files']}
    extras=set(production_files(ROOT))|{'.gitignore','curriculum_schema.py','requirements-p6a.txt',
        'docs/P6UI3_SYLLABUS_INGESTION.md','tests_p0/test_syllabus_ingestion.py','tests_p0/syllabus_ingestion_acceptance.py'}
    extras.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'frontend/tests').rglob('*') if p.is_file())
    extras.update(p.relative_to(ROOT).as_posix() for p in OUT.iterdir() if p.is_file())
    for name in extras:files[name]=sha(ROOT/name)
    target.parent.mkdir();saved=target.parent/'parent-active-descriptor.json';write(saved,active);files[saved.relative_to(ROOT).as_posix()]=sha(saved)
    historical=dict(old['historical_baselines']);historical['v1.8']={p.relative_to(ROOT).as_posix():sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest=dict(old,reference_version='v1.9',parent_reference='v1.8',revision_type='bounded_syllabus_ingestion',
        created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(ROOT),historical_baselines=historical,
        ingestion_revision=dict(scope='P6UI.3A known 4MA1 Topic 2 PDF ingestion',integrity=proof,model_api_calls=0,
            trusted_writes=False,lesson_adapter=False,changes=sorted(CHANGES),
            evidence={name:dict(path='output/p6ui3a/'+name,sha256=sha(OUT/name)) for name in ('backend-tests.json','frontend-e2e.json','api-acceptance.json','integrity.json')},
            excluded=['var/p6ui/uploads','var/p6ui/runs','tmp','node_modules','.next','frontend/out','secrets','__pycache__']))
    write(target,manifest)
    active=dict(active_reference_version='v1.9',manifest_path=target.relative_to(ROOT).as_posix(),manifest_sha256=sha(target))
    (ROOT/'output/reference_freeze_active.json').write_text(json.dumps(active,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    check=verify_reference(ROOT);assert check['valid'],check
    write(OUT/'baseline-creation.json',dict(active,protected_files=len(files)));print(json.dumps(dict(active,protected_files=len(files)),indent=2))
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['freeze']:freeze()
    else:
        result=integrity();write(OUT/'integrity.json',result);print(json.dumps(result,indent=2))
