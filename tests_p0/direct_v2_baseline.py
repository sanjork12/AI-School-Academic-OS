"""One operator-authorized v1.3 revision. Frozen parents are never rewritten."""
import json
from pathlib import Path
from datetime import datetime,timezone
from academic_os.ai_qualification.reference_baseline import sha,production_files
from tests_p0.reference_revision import live_comparisons,write_new

CHANGES=('academic_os/ai_authoring/provider.py','academic_os/ai_authoring/brief.py',
 'academic_os/ai_qualification/__main__.py','academic_os/ai_qualification/runner.py',
 'academic_os/ai_qualification/models.py','academic_os/ai_qualification/reporting.py',
 'academic_os/ai_qualification/reference_baseline.py','tests_p0/test_ai_qualification.py',
 'tests_p0/test_reference_revision.py')
ADDITIONS=('academic_os/ai_qualification/preflight.py','tests_p0/test_direct_v2_preflight.py',
 'tests_p0/direct_v2_baseline.py','docs/P6A2_DIRECT_V2_LIVE_QUALIFICATION.md')


def build():
 root=Path('.').resolve();out=Path('output/reference_freeze_v1_3');target=out/'reference_manifest.json'
 if target.exists():raise FileExistsError('Refusing to replace frozen v1.3')
 start=json.loads(Path('output/p6a2_live_qualification/implementation-start.json').read_text())
 for name,entry in start.items():
  if name not in CHANGES and sha(name)!=entry['sha256']:raise ValueError('Unauthorized delta: '+name)
 old=json.loads(Path('output/reference_freeze_v1_2/reference_manifest.json').read_text())
 for name,h in old['files'].items():
  if name not in CHANGES and sha(name)!=h:raise ValueError('Parent integrity mismatch: '+name)
 assert set(production_files(root))-set(old['production_inventory'])=={'academic_os/ai_qualification/preflight.py'}
 assert not set(old['production_inventory'])-set(production_files(root))
 out.mkdir(exist_ok=True)
 write_new(out/'parent-active-descriptor.json',json.loads(Path('output/reference_freeze_active.json').read_text()))
 history={p.as_posix():sha(p) for p in Path('output/reference_freeze_v1_2').rglob('*') if p.is_file()}
 history[(out/'parent-active-descriptor.json').as_posix()]=sha(out/'parent-active-descriptor.json')
 files=dict(old['files']);files.update(history)
 for name in CHANGES+ADDITIONS:files[name]=sha(name)
 for folder in ('output/p6a1d_offline_replay','output/p6a1c_candidate_contract'):
  for p in Path(folder).rglob('*'):
   if p.is_file():files[p.as_posix()]=sha(p)
 historical=dict(old['historical_baselines']);historical['v1.2']=history
 live=live_comparisons(json.loads(Path('output/reference_freeze/reference_manifest.json').read_text()))
 assert sha('var/p0_q2.sqlite3')==old['database_baseline']['sha256']
 manifest=dict(old,reference_version='v1.3',parent_reference='v1.2',revision_type='direct_v2_qualification_preflight',
  created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(root),
  historical_baselines=historical,invariance_evidence=live,
  qualification_revision=dict(authorization='Operator explicitly authorized v1.3 and preservation of v1.1/v1.2.',
   parent_manifest=dict(path='output/reference_freeze_v1_2/reference_manifest.json',sha256=sha('output/reference_freeze_v1_2/reference_manifest.json')),
   deltas=[dict(path=n,before=start[n]['sha256'],after=sha(n)) for n in CHANGES],additions=list(ADDITIONS),
   candidate_contract='ai-author-candidate/2',live_api_calls=0,academic_scope_change=False,
   trust_change='Adds fresh current trusted read before each provider call; existing post-call verification retained.'))
 write_new(target,manifest)
 Path('output/reference_freeze_active.json').write_text(json.dumps(dict(active_reference_version='v1.3',manifest_path=target.as_posix(),manifest_sha256=sha(target)),indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(manifest=str(target),protected_files=len(files),live_comparisons=len(live['comparisons']))))


if __name__=='__main__':build()
