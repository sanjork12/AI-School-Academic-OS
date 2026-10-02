"""Explicit P6A.3 v1.4 engineering revision, preserving all parent evidence."""
import json
from pathlib import Path
from datetime import datetime,timezone
from academic_os.ai_qualification.reference_baseline import sha,production_files
from tests_p0.reference_revision import live_comparisons,write_new

CHANGES=('academic_os/ai_authoring/models.py','academic_os/ai_authoring/validation.py',
 'academic_os/ai_qualification/models.py','academic_os/ai_qualification/reporting.py',
 'academic_os/ai_qualification/runner.py','academic_os/ai_qualification/preflight.py',
 'academic_os/ai_qualification/reference_baseline.py','tests_p0/test_reference_revision.py',
 'tests_p0/test_direct_v2_preflight.py','tests_p0/test_ai_authoring.py',
 'tests_p0/test_candidate_contract.py','tests_p0/test_offline_candidate_replay.py')
ADDITIONS=('academic_os/ai_authoring/expressions.py','tests_p0/expression_replay.py',
 'tests_p0/test_expression_semantics.py','tests_p0/expression_baseline.py','docs/P6A3_EXPRESSION_SEMANTICS.md')


def build():
 root=Path('.').resolve();out=Path('output/reference_freeze_v1_4');target=out/'reference_manifest.json'
 if target.exists():raise FileExistsError('Refusing to replace frozen v1.4')
 start=json.loads(Path('output/p6a3_expression_verification/before.json').read_text())
 for n,v in start.items():
  if n not in CHANGES and sha(n)!=v['sha256']:raise ValueError('Unauthorized delta: '+n)
 old=json.loads(Path('output/reference_freeze_v1_3/reference_manifest.json').read_text())
 for n,h in old['files'].items():
  if n not in CHANGES and sha(n)!=h:raise ValueError('Parent conformance mismatch: '+n)
 assert set(production_files(root))-set(old['production_inventory'])=={'academic_os/ai_authoring/expressions.py'}
 out.mkdir(exist_ok=True)
 write_new(out/'parent-active-descriptor.json',json.loads(Path('output/reference_freeze_active.json').read_text()))
 history={p.as_posix():sha(p) for p in Path('output/reference_freeze_v1_3').rglob('*') if p.is_file()}
 history[(out/'parent-active-descriptor.json').as_posix()]=sha(out/'parent-active-descriptor.json')
 files=dict(old['files']);files.update(history)
 for n in CHANGES+ADDITIONS:files[n]=sha(n)
 for p in Path('output/p6a2_live_qualification').rglob('*'):
  if p.is_file():files[p.as_posix()]=sha(p)
 historical=dict(old['historical_baselines']);historical['v1.3']=history
 live=live_comparisons(json.loads(Path('output/reference_freeze/reference_manifest.json').read_text()))
 assert sha('var/p0_q2.sqlite3')==old['database_baseline']['sha256']
 manifest=dict(old,reference_version='v1.4',parent_reference='v1.3',revision_type='expression_semantic_verification',
  created_at=datetime.now(timezone.utc).isoformat(),files=files,production_inventory=production_files(root),
  historical_baselines=historical,invariance_evidence=live,
  expression_revision=dict(authorization='P6A.3 explicitly requests engineering baseline revision for protected expression-verification changes.',
   parent_manifest=dict(path='output/reference_freeze_v1_3/reference_manifest.json',sha256=sha('output/reference_freeze_v1_3/reference_manifest.json')),
   deltas=[dict(path=n,before=start[n]['sha256'],after=sha(n)) for n in CHANGES],additions=list(ADDITIONS),
   candidate_contract='ai-author-candidate/2',verifier='sl10-expression/1',live_api_calls=0,academic_scope_change=False,
   prompt_changed=False,scalar_math_changed=False,renderer_added=False))
 write_new(target,manifest)
 Path('output/reference_freeze_active.json').write_text(json.dumps(dict(active_reference_version='v1.4',manifest_path=target.as_posix(),manifest_sha256=sha(target)),indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(manifest=str(target),protected_files=len(files),live_comparisons=len(live['comparisons']))))


if __name__=='__main__':build()
