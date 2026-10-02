"""Reproducible P5C live-chain acceptance and frozen-state verification."""
import hashlib
import json
from pathlib import Path

from academic_os.profiled_validation_service import ProfiledContentValidationService, save_profiled_validation
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT = Path('output/p5c_profiled_validation')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verified_test_log(name, count):
    raw = (OUT / name).read_bytes()
    text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    assert f'Ran {count} tests' in text and text.strip().endswith('OK'), name
    assert sum(line.endswith(' ... ok') for line in text.splitlines()) == count, name
    return {'passed': count, 'failures': 0, 'errors': 0, 'sha256': sha(OUT / name)}


def main():
    before = json.loads((OUT / 'before.json').read_text(encoding='utf-8'))
    assert state() == before['database']
    for path, expected in before['files'].items():
        assert sha(path) == expected, path
    old_counts = counts()
    result = ProfiledContentValidationService(Path('var/p0_q2.sqlite3')).read_profiles(
        'standard-deviation', PROTECTED_SNAPSHOTS)
    files = save_profiled_validation(result, OUT)
    hashes = {path: sha(path) for path in files}
    save_profiled_validation(result, OUT)
    assert hashes == {path: sha(path) for path in files}
    profiles = {}
    for key, required in (('focused-review', 9), ('standard-lesson', 15)):
        report = result.reports[key]
        assert report.renderer_readiness.ready_for_rendering and not report.violations
        assert report.role_population.populated == report.role_population.required == required
        assert report.density_validation.minimum_compliance and report.density_validation.target_attainment
        assert len(report.learning_requirement_coverage) == 3
        assert len(report.coverage_requirement_coverage) == 2
        assert all(row.teaching_coverage and row.assessment_check_coverage for row in report.learning_requirement_coverage)
        profiles[key] = report.model_dump(mode='json')
    assert sum('numeric_answer_recomputed' in v['checks'] for v in result.reports['standard-lesson'].mathematical_verification.values()) == 6
    assert result.reports['focused-review'].input_contracts['learning-specification/1'] == result.reports['standard-lesson'].input_contracts['learning-specification/1']
    tests = {name: verified_test_log(name, count) for name, count in (
        ('baseline-tests.txt', 45), ('new-tests.txt', 50), ('verified-tests.txt', 202))}
    assert state() == before['database'] and counts() == old_counts
    for path, expected in before['files'].items():
        assert sha(path) == expected, path
    evidence = dict(status='P5C acceptance passed', profiles=profiles, tests=tests,
        full_repository_suite_run=False, output_sha256=hashes,
        database_before=before['database'], database_after=state(),
        counts_before=old_counts, counts_after=counts(),
        new_reviews=0, new_governance_decisions=0, new_snapshots=0,
        protected_files_checked=len(before['files']),
        case_c=dict(test='test_07_case_c_minimum_without_target_ready',
            minimum_compliance=True, target_attainment=False, ready_for_rendering=True,
            evidence='Executed in both new-tests.txt and verified-tests.txt; isolated in-memory mutation.'),
        limitations=['Composition eligibility only; no academic approval or PPTX generation.',
            'Language validation is bounded to current deterministic provider content.',
            'No classroom duration guarantee or quality score.'])
    payload = (json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    target = OUT / 'acceptance.json'
    if target.exists() and target.read_bytes() != payload:
        raise ValueError('Different existing acceptance evidence')
    target.write_bytes(payload)
    print(json.dumps(dict(status=evidence['status'], profiles={k:v['renderer_readiness'] for k,v in profiles.items()}, tests=tests), indent=2))


if __name__ == '__main__':
    main()
