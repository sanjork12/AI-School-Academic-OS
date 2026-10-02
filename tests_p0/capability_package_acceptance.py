"""Additive P6UI.3B acceptance using existing P6UI.3A completed parse runs."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
from academic_os.ai_qualification.reference_baseline import sha, production_files, verify_reference
from academic_os.curriculum_ingestion.service import IngestionService, serial
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_capability.service import AcademicCapabilityService

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/p6ui3b'
CHANGES = {'.gitignore', 'academic_os/curriculum_ingestion/models.py',
    'academic_os/curriculum_ingestion/service.py', 'console_api/app.py',
    'academic_os/ai_qualification/reference_baseline.py', 'tests_p0/test_reference_revision.py'}
RUNS = {'foundation': '0987bc571907418d90ce56469c82a036', 'higher': 'ac2be810e3b84dc4abb2974ae6773802'}


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(serial(value) + b'\n')


def integrity():
    before = read(OUT / 'before.json')
    historical = {p: h for p, h in before['history'].items() if p != 'output/reference_freeze_active.json'}
    changed = [p for p, h in historical.items() if sha(ROOT / p) != h]
    assert not changed, changed
    assert sha(ROOT / 'var/p0_q2.sqlite3') == before['database_sha256']
    assert sha(ROOT / '.gitignore') == sha(OUT / 'start-gitignore.txt'), 'Concurrent ignore change'
    return dict(historical_files_checked=len(historical), historical_artifacts_unchanged=True,
        manifests_through_v1_9_unchanged=True, trusted_state_unchanged=True,
        database_sha256=before['database_sha256'], model_calls=0)


def evidence():
    service = IngestionService()
    try:
        capability = AcademicCapabilityService(service, OUT / 'packages')
        rows = {}
        with (patch.object(service, 'submit_parse', side_effect=AssertionError('No new parse')),
              patch.object(core, 'live_parse', side_effect=AssertionError('No provider'))):
            for name, tier, sub, obj in [('foundation', 'foundation', None, None), ('higher', 'higher', None, None),
                                        ('subtopic', 'foundation', '2.8', None), ('objective', 'foundation', '2.8', 'A')]:
                target = service.capabilities(RUNS[tier], sub, obj).target
                package = capability.build_capability_package(target)
                check = capability.validate_capability_package(package)
                receipt = capability.persist(package)
                assert capability.read_capability_package(receipt.package_id) == package
                assert serial(package) == serial(capability.build_capability_package(target))
                rows[name] = dict(receipt=receipt.model_dump(mode='json'), coverage=package.coverage.model_dump(), validation=check)
        from academic_os.learning_service import LearningSpecificationService
        from academic_os.product_catalog import PROTECTED_SNAPSHOTS
        learning = LearningSpecificationService(ROOT / 'var/p0_q2.sqlite3').read_topic('standard-deviation', PROTECTED_SNAPSHOTS)
        comparison = dict(standard_deviation=dict(schema_version=learning.view.schema_version,
            source_contracts=learning.view.source_contracts, conceptual_basis=len(learning.view.conceptual_basis),
            learning_requirements=len(learning.view.learning_requirements), assessment_examples=len(learning.view.assessment_evidence),
            trust_summary=learning.view.trust_summary.model_dump(mode='json'), snapshot_ids=PROTECTED_SNAPSHOTS),
            topic2=dict(schema_version='academic-capability-package/1', source_contract='selected-curriculum-target/2',
                source_bound=True, structure_valid=True, trusted_snapshot_backed=False,
                gaps=package.unresolved_items, learning_spec_generated=False),
            shared_concepts=['curriculum identity', 'source references', 'warning/evidence boundaries', 'explicit trust state'],
            generic_architecture=['versioned contracts', 'resolving source/evidence refs', 'consistent upstream read', 'coverage requirements'],
            standard_deviation_specific=['topic catalog selection', 'product aliases', 'concept/competency/task IDs', 'verified curriculum excerpt'])
        write(OUT / 'standard-deviation-comparison.json', comparison)
        write(OUT / 'offline-acceptance.json', dict(status='PASS', selections=rows, no_reparse=True, model_calls=0, integrity=integrity()))
        print(json.dumps(rows, indent=2))
    finally: service.close()


def freeze():
    target = ROOT / 'output/reference_freeze_v1_10/reference_manifest.json'
    assert not target.parent.exists(), 'Never overwrite v1.10'
    before = read(OUT / 'before.json'); active = before['active']
    assert read(ROOT / 'output/reference_freeze_active.json') == active
    oldpath = ROOT / active['manifest_path']; assert sha(oldpath) == active['manifest_sha256']
    old = read(oldpath)
    assert read(OUT / 'backend-tests.json')['successful']
    assert read(OUT / 'offline-acceptance.json')['status'] == 'PASS'
    proof = integrity()
    changed = {p for p, h in old['files'].items() if sha(ROOT / p) != h}
    assert changed == CHANGES, changed ^ CHANGES
    files = {p: sha(ROOT / p) for p in old['files']}
    extra = set(production_files(ROOT)) | {'docs/P6UI3B_ACADEMIC_CAPABILITY_PACKAGE.md',
            'tests_p0/test_curriculum_capability.py', 'tests_p0/capability_package_acceptance.py'}
    extra.update(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    extra.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'output/p6ui3a').iterdir() if p.is_file())
    for name in extra: files[name] = sha(ROOT / name)
    target.parent.mkdir(); saved = target.parent / 'parent-active-descriptor.json'
    write(saved, active); files[saved.relative_to(ROOT).as_posix()] = sha(saved)
    history = dict(old['historical_baselines'])
    history['v1.9'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in oldpath.parent.rglob('*') if p.is_file()}
    from datetime import datetime, timezone
    manifest = dict(old, reference_version='v1.10', parent_reference='v1.9', revision_type='selected_curriculum_capability',
        created_at=datetime.now(timezone.utc).isoformat(), files=files, production_inventory=production_files(ROOT),
        historical_baselines=history, capability_revision=dict(integrity=proof, changes=sorted(CHANGES),
            existing_delta='.gitignore had changed before milestone start; retained without rewriting v1.9',
            source='output/p6ui3b/offline-acceptance.json', package_version='academic-capability-package/1',
            model_calls=0, trusted_writes=False, generation_enabled=False))
    write(target, manifest)
    descriptor = dict(active_reference_version='v1.10', manifest_path=target.relative_to(ROOT).as_posix(), manifest_sha256=sha(target))
    (ROOT / 'output/reference_freeze_active.json').write_bytes(serial(descriptor) + b'\n')
    result = verify_reference(ROOT); assert result['valid'], result
    write(OUT / 'baseline-creation.json', dict(descriptor, protected_files=len(files)))
    print(json.dumps(dict(descriptor, protected_files=len(files)), indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['evidence']: evidence()
    elif sys.argv[1:] == ['freeze']: freeze()
    else: print(json.dumps(integrity(), indent=2))
