"""Additive P6UI.4 evidence, read-only compatibility checks and gated v1.11 freeze."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from academic_os.ai_qualification.reference_baseline import sha, production_files, verify_reference
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import IngestionService, serial
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.learning_service import LearningSpecificationService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.capability_package_acceptance import RUNS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/p6ui4_learning_specification'
CHANGES = {'academic_os/ai_qualification/reference_baseline.py', 'tests_p0/test_reference_revision.py'}


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(serial(data) + b'\n')


def integrity():
    before = read(OUT / 'before.json')
    history = {p: h for p, h in before['history'].items() if p != 'output/reference_freeze_active.json'}
    changed = [p for p, h in history.items() if sha(ROOT / p) != h]
    assert not changed, changed
    assert sha(ROOT / 'var/p0_q2.sqlite3') == before['database_sha256']
    for p, h in before['inspected_sources'].items(): assert sha(ROOT / p) == h, p
    legacy = LearningSpecificationService(ROOT / 'var/p0_q2.sqlite3').read_topic('standard-deviation', PROTECTED_SNAPSHOTS)
    legacy_hash = hashlib.sha256(legacy.view.serialize().encode()).hexdigest()
    assert legacy_hash == before['standard_deviation_sha256']
    return dict(historical_files_checked=len(history), historical_artifacts_unchanged=True,
        manifests_through_v1_10_unchanged=True, trusted_state_unchanged=True,
        database_sha256=before['database_sha256'], standard_deviation_unchanged=True,
        standard_deviation_sha256=legacy_hash, model_calls=0)


def evidence():
    assert (OUT / 'inspection.json').is_file()
    ingestion = IngestionService()
    try:
        capabilities = AcademicCapabilityService(ingestion)
        service = GovernedLearningService(capabilities, OUT / 'specifications')
        results = {}
        scopes = [('foundation-topic', 'foundation', None, None), ('higher-topic', 'higher', None, None),
            ('foundation-subtopic', 'foundation', '2.8', None), ('first-objective', 'foundation', '2.8', 'A'),
            ('foundation-region', 'foundation', '2.8', 'E'), ('higher-region', 'higher', '2.8', 'B')]
        with (patch.object(ingestion, 'submit_parse', side_effect=AssertionError('No parse')),
              patch.object(core, 'live_parse', side_effect=AssertionError('No provider'))):
            for name, tier, sub, obj in scopes:
                target = ingestion.capabilities(RUNS[tier], sub, obj).target
                package = capabilities.build_capability_package(target)
                eligibility = service.evaluate_learning_spec_eligibility(package)
                write(OUT / 'eligibility' / (name + '.json'), eligibility)
                row = dict(status=eligibility.status, selected=len(eligibility.objective_results),
                    independently_ready=eligibility.independently_ready_source_ids,
                    unresolved=eligibility.unresolved_source_ids, excluded=eligibility.excluded_source_ids)
                if eligibility.status == 'ELIGIBLE_WITH_WARNINGS':
                    spec = service.build_learning_spec(package, eligibility)
                    again = service.build_learning_spec(package, eligibility)
                    assert serial(spec) == serial(again)
                    report = service.validate_learning_spec(spec); assert report.valid
                    assert report == service.validate_learning_spec(again)
                    receipt = service.persist(spec)
                    assert service.read_learning_spec(receipt.spec_id) == spec
                    row.update(receipt=receipt.model_dump(mode='json'), validation=report.model_dump(mode='json'))
                else:
                    try: service.build_learning_spec(package, eligibility)
                    except core.IngestionError as exc: assert exc.code == 'LEARNING_SPEC_NOT_ELIGIBLE'
                    else: raise AssertionError('Unqualified scope constructed')
                results[name] = row
        legacy = LearningSpecificationService(ROOT / 'var/p0_q2.sqlite3').read_topic('standard-deviation', PROTECTED_SNAPSHOTS)
        comparison = dict(legacy_schema=legacy.view.schema_version, new_schema='governed-learning-specification/1',
            shared=['curriculum identity', 'canonical capability meaning', 'source/evidence references', 'bounded capability intention', 'explicit unavailable evidence'],
            legacy_specific=['teacher-topic/2 and assessment-intelligence/1 composition', 'current trusted snapshots', 'SD catalog and product aliases', 'reviewed task-form requirements and coverage'],
            new_fields=['per-element provenance classification and rule', 'source package and eligibility hashes', 'source-specific human decision IDs', 'explicit qualified-reviewable governance state'],
            missing=['assessed success criteria', 'prerequisites', 'misconception evidence', 'concept graph', 'concrete task forms', 'reviewed assessment examples', 'publication approval'],
            trust_distinction='New reviewed intention evidence is not a migrated or weakened P3A trusted production view',
            legacy_result=dict(concepts=len(legacy.view.conceptual_basis), learning_requirements=len(legacy.view.learning_requirements), reviewed_examples=len(legacy.view.assessment_evidence)))
        write(OUT / 'comparison.json', comparison)
        write(OUT / 'offline-acceptance.json', dict(status='PASS', scopes=results, integrity=integrity(),
            model_calls=0, no_reparse=True, new_trust_decisions=0, pedagogy_generated=False))
        print(json.dumps({k: {f: v for f, v in row.items() if f not in ('receipt', 'validation', 'unresolved')} for k, row in results.items()}, indent=2))
    finally: ingestion.close()


def freeze():
    target = ROOT / 'output/reference_freeze_v1_11/reference_manifest.json'
    assert not target.parent.exists(), 'Never overwrite v1.11'
    before = read(OUT / 'before.json'); active = before['active']; parent = ROOT / active['manifest_path']
    assert read(ROOT / 'output/reference_freeze_active.json') == active
    assert sha(parent) == active['manifest_sha256']
    old = read(parent)
    assert read(OUT / 'backend-tests.json')['successful']
    assert read(OUT / 'offline-acceptance.json')['status'] == 'PASS'
    proof = integrity()
    changes = {p for p, h in old['files'].items() if sha(ROOT / p) != h}
    assert changes == CHANGES, changes ^ CHANGES
    files = {p: sha(ROOT / p) for p in old['files']}
    extra = set(production_files(ROOT)) | {'docs/P6UI4_GOVERNED_LEARNING_SPECIFICATION.md',
        'tests_p0/test_governed_learning.py', 'tests_p0/governed_learning_acceptance.py'}
    extra.update(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    extra.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'output/p6ui3b').iterdir() if p.is_file())
    for name in extra: files[name] = sha(ROOT / name)
    target.parent.mkdir(); saved = target.parent / 'parent-active-descriptor.json'
    write(saved, active); files[saved.relative_to(ROOT).as_posix()] = sha(saved)
    history = dict(old['historical_baselines'])
    history['v1.10'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest = dict(old, reference_version='v1.11', parent_reference='v1.10', revision_type='governed_learning_specification',
        created_at=datetime.now(timezone.utc).isoformat(), files=files, production_inventory=production_files(ROOT),
        historical_baselines=history, governed_learning_revision=dict(integrity=proof, changes=sorted(CHANGES),
            inspection_sha256=sha(OUT / 'inspection.json'), evidence_sha256=sha(OUT / 'offline-acceptance.json'),
            contract='governed-learning-specification/1', scope='qualified reviewable learning intentions only',
            model_calls=0, trusted_writes=False, publication=False, pedagogy=False))
    write(target, manifest)
    descriptor = dict(active_reference_version='v1.11', manifest_path=target.relative_to(ROOT).as_posix(), manifest_sha256=sha(target))
    (ROOT / 'output/reference_freeze_active.json').write_bytes(serial(descriptor) + b'\n')
    check = verify_reference(ROOT); assert check['valid'], check
    write(OUT / 'baseline-creation.json', dict(descriptor, protected_files=len(files)))
    print(json.dumps(dict(descriptor, protected_files=len(files)), indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['evidence']: evidence()
    elif sys.argv[1:] == ['freeze']: freeze()
    else: print(json.dumps(integrity(), indent=2))
