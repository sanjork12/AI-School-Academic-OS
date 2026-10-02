"""Offline historical replay; saved JSON is test evidence, not runtime authority."""
from academic_os.ai_authoring.provenance import LEGACY_POLICY
import json
from pathlib import Path
from academic_os.ai_authoring.service import read_inputs, run_once
from academic_os.ai_authoring.validation import validate_candidate
from academic_os.ai_authoring.brief import serial
from academic_os.ai_qualification.reference_baseline import sha
from tests_p0.test_ai_authoring import FakeAuthor


def main():
    destination = Path('output/p6a1c_candidate_contract/offline-replay.json')
    if destination.exists(): raise FileExistsError('Replay already exists; historical output is immutable')
    source = Path('output/p6a1_live_qualification/run-3ce33e8d738f42df96182e5ca5409dd9')
    before = {p.as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
    database = sha('var/p0_q2.sqlite3')
    inputs = read_inputs('var/p0_q2.sqlite3')
    historical = []
    for path in sorted(source.glob('attempt-*/ai-candidate-*.json')):
        audit = json.loads(path.read_text(encoding='utf-8'))
        report = validate_candidate(audit['candidate'], inputs, policy=LEGACY_POLICY)
        assert report.violations == ('candidate_contract_version_unsupported',)
        historical.append(dict(path=path.as_posix(),sha256=sha(path),validation=report.model_dump(mode='json')))
    assert len(historical) == 10
    fixtures = []
    for case in json.loads(Path('tests_p0/fixtures/p6a1c_gold.json').read_text())['cases']:
        author = FakeAuthor(case['content'])
        audit = run_once(inputs, author, policy=LEGACY_POLICY)
        assert audit['validation']['accepted'] == case['accepted']
        assert author.calls == 1 and not audit['live_provider']
        fixtures.append(dict(id=case['id'],audit=audit))
    assert before == {p.as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
    assert database == sha('var/p0_q2.sqlite3')
    result=dict(format='p6a1c-offline-replay/1',historical=historical,fixtures=fixtures,
                original_run_unchanged=True,database_unchanged=True,provider_api_calls=0)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('x',encoding='utf-8') as stream:stream.write(serial(result))
    print(destination)


if __name__ == '__main__': main()
