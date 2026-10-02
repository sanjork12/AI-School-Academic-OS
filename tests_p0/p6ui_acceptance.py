"""P6UI integrity report and gated, non-overwriting v1.8 freeze."""
import json
from pathlib import Path
from datetime import datetime, timezone
from academic_os.ai_qualification.reference_baseline import sha, production_files, verify_reference

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/p6ui2'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,value):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.write('\n')

def integrity():
    start=read(OUT/'before.json')
    history={p:h for p,h in start['history'].items() if p!='output/reference_freeze_active.json'}
    changed=[p for p,h in history.items() if sha(ROOT/p)!=h]
    assert not changed,changed
    assert sha(ROOT/'var/p0_q2.sqlite3')==start['database_sha256']
    return dict(historical_files_checked=len(history),historical_artifacts_unchanged=True,
        manifests_v1_through_v1_7_unchanged=True,database_sha256=start['database_sha256'],
        trusted_database_unchanged=True,governance_review_snapshots_unchanged=True,model_api_calls=0)

def freeze():
    target=ROOT/'output/reference_freeze_v1_8/reference_manifest.json'
    if target.parent.exists():raise FileExistsError('Never overwrite v1.8')
    start=read(OUT/'before.json');old=read(ROOT/start['active']['manifest_path'])
    assert read(ROOT/'output/reference_freeze_active.json')==start['active']
    assert sha(ROOT/start['active']['manifest_path'])==start['active']['manifest_sha256']
    backend=read(OUT/'backend-tests.json');browser=read(OUT/'frontend-e2e.json')
    assert backend['successful'] and backend['total']>=110
    assert browser['stats']['expected']==2 and browser['stats']['unexpected']==0 and browser['stats']['skipped']==0
    proof=integrity()
    allowed={'academic_os/ai_qualification/reference_baseline.py','tests_p0/test_reference_revision.py'}
    changes={p for p,h in old['files'].items() if sha(ROOT/p)!=h}
    assert changes==allowed,changes
    # All new source, UI configuration, tests, docs and key acceptance records.
    files={p:sha(ROOT/p) for p in old['files']}
    extras=set(production_files(ROOT))
    extras.update(['requirements-p6ui.txt','frontend/README.md','docs/P6UI2_INTERNAL_AUTHORING_CONSOLE.md',
        'tests_p0/test_p6ui_console.py','tests_p0/p6ui_acceptance.py'])
    extras.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'frontend/tests').rglob('*') if p.is_file())
    extras.update(p.relative_to(ROOT).as_posix() for p in OUT.iterdir() if p.is_file())
    for p in extras:files[p]=sha(ROOT/p)
    target.parent.mkdir()
    parent=target.parent/'parent-active-descriptor.json';write(parent,start['active']);files[parent.relative_to(ROOT).as_posix()]=sha(parent)
    historical=dict(old['historical_baselines']);historical['v1.7']={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'output/reference_freeze_v1_7').rglob('*') if p.is_file()}
    manifest=dict(old,reference_version='v1.8',parent_reference='v1.7',revision_type='internal_authoring_console',created_at=datetime.now(timezone.utc).isoformat(),
        files=files,production_inventory=production_files(ROOT),historical_baselines=historical,
        ui_revision=dict(scope='P6UI.2 local deterministic console',model_api_calls=0,trusted_writes=False,integrity=proof,
            verification={n:dict(path='output/p6ui2/'+n,sha256=sha(OUT/n)) for n in ('backend-tests.json','frontend-e2e.json','integrity.json')},
            excluded=['node_modules','.next','out','tmp','output/p6ui2/runs','secrets','__pycache__']))
    write(target,manifest)
    active=dict(active_reference_version='v1.8',manifest_path=target.relative_to(ROOT).as_posix(),manifest_sha256=sha(target))
    (ROOT/'output/reference_freeze_active.json').write_text(json.dumps(active,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    result=verify_reference(ROOT);assert result['valid'],result
    write(OUT/'baseline-creation.json',dict(active,protected_files=len(files)))
    print(json.dumps(dict(active,protected_files=len(files)),indent=2))

if __name__=='__main__':
    import sys
    if sys.argv[1:] == ['freeze']:freeze()
    else:
        result=integrity();write(OUT/'integrity.json',result);print(json.dumps(result,indent=2))
