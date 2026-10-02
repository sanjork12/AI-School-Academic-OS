"""Read-only P2B acceptance. No decisions, promotion, or trusted-state writes."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from academic_os.assessment_intelligence import AssessmentIntelligenceService,_derive
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_service import AcademicProductService
from tests_p0.teacher_product_acceptance import state

OUTPUT=Path('output/p2b_assessment_intelligence')
DB=Path('var/p0_q2.sqlite3')


def counts():
    c=sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        reviews=c.execute('SELECT object_key FROM reviews').fetchall()
        requests=[json.loads(r[0]) for r in c.execute('SELECT result FROM requests')]
        source=sum(key.startswith(('source:','locator:')) for key, in reviews)
        return dict(review_decisions=len(reviews),source_and_locator_decisions=source,
            academic_decisions=len(reviews)-source,requests=len(requests),
            governance_decisions=sum(r.get('record_type')=='publication_governance/1' for r in requests),
            snapshots=c.execute('SELECT count(*) FROM snapshots').fetchone()[0])
    finally:c.close()


def full_tests():
    raw=(OUTPUT/'full-suite.txt').read_bytes()
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    result=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
    if not result:raise ValueError('Full suite has not finished')
    errors=re.findall(r'^ERROR: (.+)$',text,re.M)
    assert len(errors)==1 and 'test_preserved_project_files' in errors[0],errors
    assert 'FileNotFoundError' in text and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in text
    assert 'FAILED (errors=1)' in text and not re.search(r'^FAIL:',text,re.M)
    focused=[l for l in text.splitlines() if re.match(r'test_.*\(tests_p0.test_assessment_intelligence\.',l)]
    assert len(focused)==40 and all(l.endswith(' ... ok') for l in focused)
    previous=[l for l in text.splitlines() if re.match(r'test_.*\(tests_p0.test_teacher_product\.',l)]
    assert len(previous)==60 and all(l.endswith(' ... ok') for l in previous)
    total=int(result[1]);passed=sum(line.endswith(' ... ok') for line in text.splitlines())
    assert passed==total-1
    return dict(total=total,passed=passed,failures=0,errors=1,skipped=0,not_run=0,
        p2b_passed=len(focused),p2a1_passed=len(previous),duration_seconds=float(result[2]),
        known_error='FileNotFoundError: AI_Academic_Operating_System_Brainstorm_CN.pptx; original test and pinned hash unchanged')


def main():
    before=json.loads((OUTPUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before
    counts_before=counts()
    upstream=AcademicProductService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    old=Path('output/p2a_teacher_view/standard_deviation.json').read_bytes()
    assert upstream.view.serialize().encode()==old,'Frozen teacher-topic/2 output changed'
    service=AssessmentIntelligenceService(DB)
    result=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    serial=result.view.serialize()
    assert service.read_topic('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS))).view.serialize()==serial
    reversed_view=upstream.view.model_copy(update={'assessment_evidence':tuple(reversed(upstream.view.assessment_evidence))})
    assert _derive(reversed_view).serialize()==serial
    assert state()==before and counts()==counts_before
    pinned=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    changed=[p for p,h in pinned.items() if Path(p).exists() and hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    missing=[p for p in pinned if not Path(p).exists()]
    assert not changed
    assert missing==['AI_Academic_Operating_System_Brainstorm_CN.pptx']
    tests=full_tests()
    report=dict(status='P2B EVIDENCE-BACKED ASSESSMENT INTELLIGENCE PASSED',
        schema_version=result.view.schema_version,upstream_schema_version='teacher-topic/2',
        upstream_output_unchanged=True,upstream_sha256=hashlib.sha256(old).hexdigest(),
        database_before=before,database_after=state(),counts_before=counts_before,counts_after=counts(),
        new_source_decisions=0,new_academic_decisions=0,new_governance_decisions=0,new_trusted_snapshots=0,
        snapshot_usability=upstream.provenance['snapshot_usability'],protected_files=dict(changed=changed,missing=missing),
        determinism=dict(repeated=True,reversed_snapshots=True,reversed_evidence=True,sha256=hashlib.sha256(serial.encode()).hexdigest()),
        assessment_focus=result.view.assessment_focus.model_dump(mode='json'),
        reviewed_examples=[e.model_dump(mode='json') for e in result.view.reviewed_examples],
        observed_patterns=[p.model_dump(mode='json') for p in result.view.observed_patterns],
        limitations=[l.model_dump(mode='json') for l in result.view.limitations],
        trust_summary=result.view.trust_summary.model_dump(mode='json'),test_results=tests,
        architectural_decisions=[
            'Frozen upstream contract unchanged; no upstream defect prevents this slice.',
            'Only current AcademicProductService reads enter production; detached JSON is not a trust credential.',
            'Wording inequality supports distinct_question_wording only, not different_question_context or a context taxonomy.',
            'Example refs hash structured awarding body, qualification, specification, year, session, paper and question-part coordinates; missing or duplicate identity is rejected.',
            'Source warnings are retained as evidence notes; no frequency, difficulty, prediction, typical-mark or common-error inference.',
            'Saved output is a derived product artifact and requires fresh upstream validation before use.'
        ],changed_files=['academic_os/assessment_intelligence.py','academic_os/cli.py',
            'tests_p0/test_assessment_intelligence.py','tests_p0/assessment_intelligence_acceptance.py',
            'docs/P2B_ASSESSMENT_INTELLIGENCE.md'])
    (OUTPUT/'standard_deviation.json').write_bytes(serial.encode())
    for name,data in [('provenance',result.provenance),('acceptance',report)]:
        (OUTPUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],tests=tests,counts=counts(),database_unchanged=True),indent=2))


if __name__=='__main__':main()
