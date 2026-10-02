"""P3A acceptance: report protected state and write only learning artifacts."""
import hashlib
import json
from pathlib import Path
import re
from academic_os.learning_service import LearningSpecificationService
from academic_os.learning_core import build_learning_specification
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_service import AcademicProductService
from academic_os.assessment_intelligence import AssessmentIntelligenceService
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p3a_learning_specification')
DB=Path('var/p0_q2.sqlite3')


def test_result():
    raw=(OUT/'full-suite.txt').read_bytes()
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    match=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
    if not match:raise ValueError('Full suite has not completed')
    errors=re.findall(r'^ERROR: (.+)$',text,re.M)
    assert len(errors)==1 and 'test_preserved_project_files' in errors[0]
    assert 'FileNotFoundError' in text and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in text
    assert 'FAILED (errors=1)' in text and not re.search(r'^FAIL:',text,re.M)
    passed=sum(l.endswith(' ... ok') for l in text.splitlines());total=int(match[1])
    assert passed==total-1
    groups={}
    for module,expected in [('test_learning_specification',45),('test_teacher_product',60),('test_assessment_intelligence',40)]:
        lines=[l for l in text.splitlines() if re.match(r'test_.*\(tests_p0\.'+module+r'\.',l)]
        assert len(lines)==expected and all(l.endswith(' ... ok') for l in lines)
        groups[module]=len(lines)
    return dict(total=total,passed=passed,failures=0,errors=1,skipped=0,not_run=0,groups=groups,
        duration_seconds=float(match[2]),known_error='FileNotFoundError: AI_Academic_Operating_System_Brainstorm_CN.pptx; original protected-file test and pinned hash unchanged')


def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for file,digest in before['files'].items():assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==digest,file
    counts_before=counts()
    teacher=AcademicProductService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    assessment=AssessmentIntelligenceService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    assert teacher.view.serialize().encode()==Path('output/p2a_teacher_view/standard_deviation.json').read_bytes()
    assert assessment.view.serialize().encode()==Path('output/p2b_assessment_intelligence/standard_deviation.json').read_bytes()
    service=LearningSpecificationService(DB);result=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    serialized=result.view.serialize()
    assert service.read_topic('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS))).view.serialize()==serialized
    reverse_teacher=teacher.view.model_copy(update={'assessment_evidence':tuple(reversed(teacher.view.assessment_evidence))})
    reverse_assessment=assessment.view.model_copy(update={'reviewed_examples':tuple(reversed(assessment.view.reviewed_examples))})
    assert build_learning_specification(reverse_teacher,reverse_assessment).serialize()==serialized
    golden=json.loads(Path('tests_p0/fixtures/learning_standard_deviation_gold.json').read_text(encoding='utf-8'))
    oracle_map={}
    for collection,selector in [('learning_requirements','type'),('coverage_requirements','type'),('evidence_boundaries','code')]:
        actual={getattr(r,selector):r for r in getattr(result.view,collection)}
        assert len(actual)==len(golden[collection])
        for expected in golden[collection]:
            row=actual[expected[selector]];oracle_map[expected['oracle_id']]=row.ref
            for text in expected.get('required_meaning',[]):assert text in row.statement
            if 'source_refs' in expected:assert set(row.source_refs)==set(expected['source_refs'])
            if 'evidence' in expected:
                examples={e.ref:e for e in result.view.assessment_evidence}
                assert {(examples[r].year,examples[r].question_part) for r in row.evidence_refs}=={tuple(e) for e in expected['evidence']}
    pinned=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    changed=[f for f,digest in pinned.items() if Path(f).exists() and hashlib.sha256(Path(f).read_bytes()).hexdigest()!=digest]
    missing=[f for f in pinned if not Path(f).exists()]
    assert not changed and missing==['AI_Academic_Operating_System_Brainstorm_CN.pptx']
    assert state()==before['database'] and counts()==counts_before
    tests=test_result()
    report=dict(status='P3A EVIDENCE-BACKED LEARNING SPECIFICATION CORE PASSED',
        schema_version=result.view.schema_version,source_contracts=list(result.view.source_contracts),
        identity=result.view.identity.model_dump(mode='json'),
        learning_requirement_count=len(result.view.learning_requirements),coverage_requirement_count=len(result.view.coverage_requirements),
        evidence_boundary_count=len(result.view.evidence_boundaries),gold_standard_passed=True,oracle_to_product_refs=oracle_map,
        database_before=before['database'],database_after=state(),counts_before=counts_before,counts_after=counts(),
        new_source_decisions=0,new_academic_decisions=0,new_governance_decisions=0,new_trusted_snapshots=0,
        upstream_files_unchanged=before['files'],upstream_outputs_byte_identical=True,
        snapshot_usability=teacher.provenance['snapshot_usability'],protected_files=dict(changed=changed,missing=missing),
        determinism=dict(repeated=True,reversed_snapshots=True,reversed_evidence=True,sha256=hashlib.sha256(serialized.encode()).hexdigest()),
        test_results=tests,
        architectural_decisions=[
            'No frozen upstream defect prevents this slice; neither upstream schema or academic meaning changed.',
            'P2B lacks course identity, so fresh P2A provides it; service compares both provenance chains and core checks semantic agreement.',
            'Learning requirements derive from semantic roles and supported relationships; Gold Standard is acceptance-only.',
            'Coverage rules are explicit learning-contract policy tied to included requirements and reviewed evidence, not new academic facts.',
            'Contract IDs encode role plus Product source identities, independent of labels, evidence wording, marks, array order and time.',
            'Five boundaries retain upstream limitations; five state the scope of the current contracts.',
            'Stable refs support future coverage declarations; no lesson, question or PPT validator is implemented.',
            'Saved artifacts require fresh trust validation; core alone cannot authenticate arbitrary JSON.'
        ],
        changed_files=['academic_os/learning_models.py','academic_os/learning_core.py','academic_os/learning_service.py',
            'academic_os/learning_rendering.py','academic_os/cli.py','tests_p0/test_learning_specification.py',
            'tests_p0/learning_specification_acceptance.py','tests_p0/fixtures/learning_standard_deviation_gold.json',
            'docs/P3A_LEARNING_SPECIFICATION.md'])
    (OUT/'standard_deviation.json').write_bytes(serialized.encode())
    for name,data in [('provenance',result.provenance),('acceptance',report)]:
        (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],counts=counts(),tests=tests,database_unchanged=True,gold_standard_passed=True),indent=2))


if __name__=='__main__':main()
