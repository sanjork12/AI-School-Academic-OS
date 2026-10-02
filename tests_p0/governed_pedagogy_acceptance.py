"""Additive negative-readiness acceptance, with unchanged P3B/P3C/P5 behavior."""
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
from academic_os.ai_qualification.reference_baseline import sha, production_files, verify_reference
from academic_os.curriculum_ingestion import core
from academic_os.curriculum_ingestion.service import IngestionService, serial
from academic_os.curriculum_capability.service import AcademicCapabilityService
from academic_os.governed_learning.service import GovernedLearningService
from academic_os.governed_pedagogy.service import GovernedPedagogyService
from academic_os.pedagogical_service import PedagogicalSpecificationService
from academic_os.pedagogical_validation import PedagogicalValidationService
from academic_os.lesson_profile_service import LessonProfileService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/p6ui5_pedagogical_specification'
CHANGES = {'academic_os/ai_qualification/reference_baseline.py', 'tests_p0/test_reference_revision.py'}


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f: f.write(serial(data) + b'\n')


def legacy_hashes():
    db = ROOT / 'var/p0_q2.sqlite3'
    pedagogy = PedagogicalSpecificationService(db).read_topic('standard-deviation', PROTECTED_SNAPSHOTS)
    validation = PedagogicalValidationService(db).read_topic('standard-deviation', PROTECTED_SNAPSHOTS)
    profiles = LessonProfileService(db).read_profiles('standard-deviation', PROTECTED_SNAPSHOTS)
    h = lambda value: hashlib.sha256(value.serialize().encode()).hexdigest()
    return dict(pedagogy=h(pedagogy.view), validation=h(validation.view), standard_profile=h(profiles.views['standard-lesson']))


def integrity():
    before = read(OUT / 'before.json')
    history = {p: h for p, h in before['history'].items() if p != 'output/reference_freeze_active.json'}
    changed = [p for p, h in history.items() if sha(ROOT / p) != h]; assert not changed, changed
    assert sha(ROOT / 'var/p0_q2.sqlite3') == before['database_sha256']
    assert legacy_hashes() == before['legacy_hashes']
    for p, h in before['inspected_sources'].items(): assert sha(ROOT / p) == h, p
    return dict(historical_files_checked=len(history), historical_artifacts_unchanged=True,
        manifests_through_v1_11_unchanged=True, trusted_state_unchanged=True,
        database_sha256=before['database_sha256'], standard_deviation_unchanged=True,
        legacy_hashes=before['legacy_hashes'], model_calls=0)


def evidence():
    assert (OUT / 'inspection.json').is_file()
    ingestion = IngestionService()
    try:
        previous = ROOT / 'output/p6ui4_learning_specification'
        learning = GovernedLearningService(AcademicCapabilityService(ingestion), previous / 'specifications')
        spec_id = read(previous / 'offline-acceptance.json')['scopes']['first-objective']['receipt']['spec_id']
        spec = learning.read_learning_spec(spec_id)
        service = GovernedPedagogyService(learning, OUT / 'qualifications')
        with (patch.object(core, 'live_parse', side_effect=AssertionError('No provider')),
              patch.object(ingestion, 'submit_parse', side_effect=AssertionError('No parse'))):
            q = service.qualify(spec); again = service.qualify(spec)
            assert serial(q) == serial(again)
            validation = service.validate_qualification(q); assert validation.valid
            assert q.eligibility.status == 'REVIEW_REQUIRED' and q.lesson_authoring_eligibility.status == 'BLOCKED'
            try: service.build_pedagogical_spec(spec, q.eligibility)
            except core.IngestionError as exc: assert exc.code == 'PEDAGOGICAL_INPUTS_INCOMPLETE'
            else: raise AssertionError('Missing pedagogy inputs were bypassed')
            receipt = service.persist_qualification(q)
            assert service.read_qualification(receipt['qualification_id']) == q
            assert service.persist_qualification(q) == receipt
        for name, value in [('eligibility', q.eligibility), ('role-contract', q.eligibility.role_contract),
                            ('lesson-authoring-eligibility', q.lesson_authoring_eligibility), ('validation', validation)]:
            write(OUT / (name + '.json'), value)
        write(OUT / 'construction-decision.json', dict(status='NOT_CONSTRUCTED',
            missing_requirements=q.eligibility.missing_requirements, pedagogical_specification=None,
            reason='Required pedagogy inputs missing; validated qualification is not an eligible pedagogical specification.'))
        comparison = dict(shared=['source-bound goals','coverage constraints','candidate/content distinction','role evidence','warning preservation'],
            legacy_specific=['capability-to-calculation mapping','summary statistics task form','fixed SD Gold sequencing/density','SL11 application-owned formula hint'],
            roles=dict(legacy_standard=15, new_executable=0, non_executable_required=['scope_framing'], non_executable_optional=['non_assessing_summary']),
            assessment=dict(legacy='Reviewed task forms and aligned candidate check slots', current='No success criteria or bounded check alignment; no assessment generated'),
            missing_generic_adapters=['reviewed success-criterion contract','bounded activity/task contract','check alignment','role-specific authoring/validation adapters'],
            current=dict(pedagogical_eligibility='REVIEW_REQUIRED', lesson_authoring='BLOCKED', pedagogy_constructed=False),
            legacy_hashes=legacy_hashes(), frozen_legacy_artifacts={p:sha(ROOT / p) for p in ['output/p3b_pedagogical_specification/standard_deviation.json','output/p3c_pedagogical_validation/standard_deviation.json']})
        write(OUT / 'standard-deviation-comparison.json', comparison)
        write(OUT / 'offline-acceptance.json', dict(status='PASS', target='EDX-4MA1-F-2.8-A',
            source_learning_spec_hash=spec_id, receipt=receipt, qualification_validation=validation.model_dump(mode='json'),
            pedagogical_eligibility='REVIEW_REQUIRED', lesson_authoring_eligibility='BLOCKED',
            pedagogical_specification_constructed=False, content_generated=False, model_calls=0, integrity=integrity()))
        print(json.dumps(dict(target='EDX-4MA1-F-2.8-A', eligibility=q.eligibility.status,
            missing=q.eligibility.missing_requirements, authoring=q.lesson_authoring_eligibility.status,
            semantic_sha256=receipt['semantic_sha256']), indent=2))
    finally: ingestion.close()


def freeze():
    target = ROOT / 'output/reference_freeze_v1_12/reference_manifest.json'
    assert not target.parent.exists(), 'Never overwrite v1.12'
    before = read(OUT / 'before.json'); active = before['active']; parent = ROOT / active['manifest_path']
    assert read(ROOT / 'output/reference_freeze_active.json') == active
    assert sha(parent) == active['manifest_sha256']
    old = read(parent)
    assert read(OUT / 'backend-tests.json')['successful']
    assert read(OUT / 'offline-acceptance.json')['status'] == 'PASS'
    proof = integrity()
    changes = {p for p, h in old['files'].items() if sha(ROOT / p) != h}; assert changes == CHANGES, changes ^ CHANGES
    files = {p: sha(ROOT / p) for p in old['files']}
    extra = set(production_files(ROOT)) | {'docs/P6UI5_GOVERNED_PEDAGOGICAL_SPECIFICATION.md',
        'tests_p0/test_governed_pedagogy.py', 'tests_p0/governed_pedagogy_acceptance.py'}
    extra.update(p.relative_to(ROOT).as_posix() for p in OUT.rglob('*') if p.is_file())
    extra.update(p.relative_to(ROOT).as_posix() for p in (ROOT / 'output/p6ui4_learning_specification').iterdir() if p.is_file())
    for name in extra: files[name] = sha(ROOT / name)
    target.parent.mkdir(); saved = target.parent / 'parent-active-descriptor.json'; write(saved, active)
    files[saved.relative_to(ROOT).as_posix()] = sha(saved)
    history = dict(old['historical_baselines'])
    history['v1.11'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in parent.parent.rglob('*') if p.is_file()}
    manifest = dict(old, reference_version='v1.12', parent_reference='v1.11', revision_type='governed_pedagogical_qualification',
        created_at=datetime.now(timezone.utc).isoformat(), files=files, production_inventory=production_files(ROOT),
        historical_baselines=history, governed_pedagogical_revision=dict(integrity=proof, changes=sorted(CHANGES),
            inspection_sha256=sha(OUT / 'inspection.json'), evidence_sha256=sha(OUT / 'offline-acceptance.json'),
            pedagogical_spec_constructed=False, authoring_eligible=False, model_calls=0, trusted_writes=False))
    write(target, manifest)
    descriptor = dict(active_reference_version='v1.12', manifest_path=target.relative_to(ROOT).as_posix(), manifest_sha256=sha(target))
    (ROOT / 'output/reference_freeze_active.json').write_bytes(serial(descriptor) + b'\n')
    check = verify_reference(ROOT); assert check['valid'], check
    write(OUT / 'baseline-creation.json', dict(descriptor, protected_files=len(files)))
    print(json.dumps(dict(descriptor, protected_files=len(files)), indent=2))


if __name__ == '__main__':
    if sys.argv[1:] == ['evidence']: evidence()
    elif sys.argv[1:] == ['freeze']: freeze()
    else: print(json.dumps(integrity(), indent=2))
