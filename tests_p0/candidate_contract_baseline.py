"""Explicit operator-authorized v1.2 builder; never reset a frozen manifest."""
import json
from pathlib import Path
from datetime import datetime, timezone
from academic_os.ai_qualification.reference_baseline import sha, production_files, compare_files
from tests_p0.reference_revision import live_comparisons, write_new

CHANGES = (
    'academic_os/ai_authoring/models.py', 'academic_os/ai_authoring/brief.py',
    'academic_os/ai_authoring/validation.py', 'academic_os/ai_authoring/service.py',
    'academic_os/ai_qualification/stress.py', 'academic_os/ai_qualification/runner.py',
    'academic_os/ai_qualification/reference_baseline.py', 'tests_p0/test_ai_authoring.py',
    'tests_p0/test_reference_revision.py', 'tests_p0/test_reference_freeze.py',
    'tests_p0/test_profile_presentation.py', 'tests_p0/test_ai_qualification.py')
ADDITIONS = ('tests_p0/test_candidate_contract.py','tests_p0/fixtures/p6a1c_gold.json',
             'tests_p0/candidate_contract_acceptance.py','tests_p0/candidate_contract_baseline.py',
             'docs/P6A1C_CANDIDATE_CONTRACT.md')


def build():
    root = Path('.').resolve()
    out = Path('output/reference_freeze_v1_2')
    path = out/'reference_manifest.json'
    if path.exists(): raise FileExistsError('Refusing to replace v1.2 manifest')
    start = json.loads(Path('output/p6a1c_candidate_contract/start-inventory.json').read_text())
    for name, expected in start.items():
        if name not in CHANGES and sha(name) != expected:
            raise ValueError('Unexpected delta: '+name)
    old = json.loads(Path('output/reference_freeze_v1_1/reference_manifest.json').read_text())
    files = dict(old['files'])
    for name in files:
        if name not in CHANGES and sha(name) != files[name]:
            raise ValueError('Unauthorized parent conformance delta: '+name)
    assert production_files(root) == old['production_inventory']
    out.mkdir(exist_ok=True)
    # Preserve the previous selector as history before explicitly selecting the child.
    write_new(out/'parent-active-descriptor.json', json.loads(Path('output/reference_freeze_active.json').read_text()))
    history = {p.as_posix():sha(p) for p in Path('output/reference_freeze_v1_1').rglob('*') if p.is_file()}
    history[(out/'parent-active-descriptor.json').as_posix()] = sha(out/'parent-active-descriptor.json')
    files.update(history)
    for p in Path('output/p6a1_live_qualification/run-3ce33e8d738f42df96182e5ca5409dd9').rglob('*'):
        if p.is_file(): files[p.as_posix()]=sha(p)
    for name in CHANGES+ADDITIONS:files[name]=sha(name)
    live = live_comparisons(json.loads(Path('output/reference_freeze/reference_manifest.json').read_text()))
    assert sha('var/p0_q2.sqlite3') == old['database_baseline']['sha256']
    manifest = dict(old,reference_version='v1.2',parent_reference='v1.1',
        revision_type='candidate_contract_alignment',created_at=datetime.now(timezone.utc).isoformat(),
        files=files,historical_baselines={'v1.1':history},invariance_evidence=live,
        contract_revision=dict(candidate='ai-author-candidate/2',brief='authoring-brief/2',
            authorization='Operator explicitly selected new v1.2 engineering baseline; retain v1.1 historical integrity.',
            parent_manifest=dict(path='output/reference_freeze_v1_1/reference_manifest.json',sha256=sha('output/reference_freeze_v1_1/reference_manifest.json')),
            deltas=[dict(path=name,before=start[name],after=sha(name)) for name in CHANGES],
            additions=list(ADDITIONS),academic_scope_change=False,trust_semantics_change=False,
            historical_verification_scope='artifact_integrity; no current-code conformance to v1.1 asserted'))
    write_new(path,manifest)
    # Explicit authorized selector update; neither frozen parent is rewritten.
    Path('output/reference_freeze_active.json').write_text(json.dumps(dict(active_reference_version='v1.2',
        manifest_path=path.as_posix(),manifest_sha256=sha(path)),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(manifest=str(path),protected_files=len(files),live_comparisons=len(live['comparisons']))))


if __name__ == '__main__':build()
