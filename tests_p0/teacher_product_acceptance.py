"""Read-only protected-state acceptance; writes only P2A product artifacts."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_service import AcademicProductService

OUTPUT=Path('output/p2a_teacher_view')
DB=Path('var/p0_q2.sqlite3')


def state():
    c=sqlite3.connect(DB.resolve(strict=True).as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
    try:
        tables={}
        for name in ('versions','heads','reviews','review_heads','requests','snapshots','snapshot_members','snapshot_blocks'):
            rows=[dict(r) for r in c.execute('SELECT * FROM '+name)]
            tables[name]=dict(count=len(rows),digest=hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False).encode()).hexdigest())
        return dict(sha256=hashlib.sha256(DB.read_bytes()).hexdigest(),tables=tables)
    finally:c.close()


def test_result():
    raw=(OUTPUT/'p2a1-full-suite.txt').read_bytes()
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    match=re.search(r'Ran (\d+) tests? in ([\d.]+)s',text)
    if not match:raise ValueError('Full suite has not completed')
    failures=int(re.search(r'failures=(\d+)',text)[1]) if re.search(r'failures=(\d+)',text) else 0
    errors=int(re.search(r'errors=(\d+)',text)[1]) if re.search(r'errors=(\d+)',text) else 0
    skipped=int(re.search(r'skipped=(\d+)',text)[1]) if re.search(r'skipped=(\d+)',text) else 0
    focused=[l for l in text.splitlines() if re.match(r'test_.*\(tests_p0.test_teacher_product\.',l)]
    assert len(focused)==60 and all(l.endswith(' ... ok') for l in focused)
    assert failures==0 and errors==1 and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in text
    total=int(match[1])
    return dict(total=total,passed=total-failures-errors-skipped,failures=failures,errors=errors,skipped=skipped,not_run=0,
        focused_passed=len(focused),duration_seconds=float(match[2]),
        known_error='FileNotFoundError: AI_Academic_Operating_System_Brainstorm_CN.pptx; original integrity test and pinned hash preserved',
        log='output/p2a_teacher_view/p2a1-full-suite.txt')


def main():
    before=json.loads((OUTPUT/'p2a1_baseline/before.json').read_text(encoding='utf-8'))
    previous=json.loads((OUTPUT/'p2a1_baseline/standard_deviation.json').read_text(encoding='utf-8'))
    assert previous['schema_version']=='teacher-topic/1'
    assert state()==before,'Protected real state changed before acceptance'
    service=AcademicProductService(DB);result=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    second=service.get_topic_view('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS)))
    serialized=result.view.serialize()
    assert serialized==second.serialize()
    assert state()==before,'Product read changed protected state'
    examples=result.view.assessment_evidence
    assert [(e.year,e.question_part) for e in examples]==[(2025,'Q2(b)'),(2023,'Q3(b)(ii)')]
    assert all(len(v['snapshot_ids'])==2 for v in result.provenance['canonical_objects'].values())
    for forbidden in ('Q3(c)(ii)','underestimate','CONTEXT-INFER','dependency_digest','review_heads','content_version',*PROTECTED_SNAPSHOTS):
        assert forbidden not in serialized,'Internal or excluded content leaked into teacher view'
    tests=test_result()
    pinned=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    missing=[p for p in pinned if not Path(p).exists()]
    changed=[p for p,h in pinned.items() if Path(p).exists() and hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
    assert not changed
    artifact=OUTPUT/'standard_deviation.json'
    artifact.write_bytes(serialized.encode('utf-8'))
    (OUTPUT/'provenance.json').write_text(json.dumps(result.provenance,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    report=dict(status='P2A.1 TEACHER PRODUCT CONTRACT REFINEMENT PASSED',
        previous_schema_version=previous['schema_version'],new_schema_version=result.view.schema_version,
        migration=dict(result='passed',strategy='Clean replacement; no production/frontend v1 consumer found; CLI and tests migrated explicitly',
            previous_artifacts='output/p2a_teacher_view/p2a1_baseline',ontology_and_snapshot_migration=False),
        view_identity=result.view.identity.model_dump(mode='json'),
        product_refs=result.provenance['product_refs'],
        capabilities=[c.model_dump(mode='json') for c in result.view.capabilities],
        curriculum=result.view.curriculum.model_dump(mode='json'),trust_summary=result.view.trust_summary.model_dump(mode='json'),
        input_snapshot_ids=list(PROTECTED_SNAPSHOTS),snapshot_usability=result.provenance['snapshot_usability'],
        canonical_objects_reused=result.provenance['canonical_objects'],assessment_examples_composed=[e.model_dump(mode='json') for e in examples],
        conflicts=result.provenance['conflicts'],teacher_view_artifact=str(artifact),
        determinism=dict(reversed_inputs_byte_identical=True,sha256=hashlib.sha256(serialized.encode()).hexdigest()),
        database_before=before,database_after=state(),
        new_academic_decisions=0,new_source_decisions=0,new_governance_decisions=0,new_trusted_snapshots=0,
        q2_snapshot=dict(snapshot_id=PROTECTED_SNAPSHOTS[0],usable=True,unchanged=True),
        q3_snapshot=dict(snapshot_id=PROTECTED_SNAPSHOTS[1],usable=True,unchanged=True),
        safety=dict(q3_deferred_interpretation_absent=True,q2_pending_contextual_inference_absent=True,
                    raw_candidates_used=False,curriculum_association_confirmed=result.view.trust_summary.curriculum_association_confirmed),
        full_test_result=tests,protected_files=dict(pinned=len(pinned),missing=missing,changed=changed),
        changed_files=['academic_os/product_models.py','academic_os/product_catalog.py',
            'academic_os/product_service.py','academic_os/product_rendering.py',
            'tests_p0/test_teacher_product.py','tests_p0/teacher_product_acceptance.py','docs/P2A_TEACHER_PRODUCT_VIEW.md'],
        architectural_issues=[
            'Product view identity is navigation configuration, separate from academic concept identity, even when labels match.',
            'Product aliases bind typed canonical identities, not mutable display labels or snapshot versions; extending the slice requires explicit aliases.',
            'Capability concept/task relationships require published support; evidence refs must resolve within the corresponding product capability.',
            'Service.snapshot can append withdrawal blocks; product reads use a mode=ro database connection and disposable memory image to preserve real state.',
            'Published scope remains a candidate association; verified curriculum wording is not confirmed equivalence.',
            'Two examples do not establish frequency, typical marks, difficulty, trend or errors.',
            'Small local database backup per request is intentional; scale may require a foundation-owned pure status API.',
            'Saved product JSON is not a trusted snapshot; subsequent use must refresh validity through the service.'])
    (OUTPUT/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],tests=tests,database_unchanged=before==state(),examples=len(examples)),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
