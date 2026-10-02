"""Read-only P3B acceptance and candidate artifact export."""
import hashlib
import json
from pathlib import Path
import re
from academic_os.pedagogical_service import PedagogicalSpecificationService
from academic_os.pedagogical_core import build_pedagogical_specification
from academic_os.learning_service import LearningSpecificationService
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p3b_pedagogical_specification');DB=Path('var/p0_q2.sqlite3')


def test_result():
    raw=(OUT/'full-suite.txt').read_bytes()
    text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    match=re.search(r'Ran (\d+) tests in ([\d.]+)s',text)
    if not match:raise ValueError('Full suite has not completed')
    errors=re.findall(r'^ERROR: (.+)$',text,re.M)
    assert len(errors)==1 and 'test_preserved_project_files' in errors[0]
    assert 'FileNotFoundError' in text and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in text
    assert 'FAILED (errors=1)' in text and not re.search(r'^FAIL:',text,re.M)
    passed=sum(l.endswith(' ... ok') for l in text.splitlines());total=int(match[1]);assert passed==total-1
    groups={}
    for module,expected in [('test_pedagogical_specification',45),('test_learning_specification',45),('test_teacher_product',60),('test_assessment_intelligence',40)]:
        lines=[l for l in text.splitlines() if re.match(r'test_.*\(tests_p0\.'+module+r'\.',l)]
        assert len(lines)==expected and all(l.endswith(' ... ok') for l in lines)
        groups[module]=len(lines)
    return dict(total=total,passed=passed,failures=0,errors=1,skipped=0,not_run=0,groups=groups,
        duration_seconds=float(match[2]),known_error='FileNotFoundError: AI_Academic_Operating_System_Brainstorm_CN.pptx; original test and pinned hash unchanged')


def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'));assert state()==before['database']
    for file,digest in before['files'].items():assert hashlib.sha256(Path(file).read_bytes()).hexdigest()==digest,file
    before_counts=counts();upstream=LearningSpecificationService(DB).read_topic('standard-deviation',PROTECTED_SNAPSHOTS)
    assert upstream.view.serialize().encode()==Path('output/p3a_learning_specification/standard_deviation.json').read_bytes()
    service=PedagogicalSpecificationService(DB);result=service.read_topic('standard-deviation',PROTECTED_SNAPSHOTS);view=result.view
    serial=view.serialize()
    assert service.read_topic('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS))).view.serialize()==serial
    fixture=upstream.view.model_dump(mode='json')
    for field in ('learning_requirements','coverage_requirements','evidence_boundaries','assessment_evidence','conceptual_basis'):fixture[field].reverse()
    assert build_pedagogical_specification(fixture).serialize()==serial
    gold=json.loads(Path('tests_p0/fixtures/pedagogical_standard_deviation_gold.json').read_text(encoding='utf-8'))
    lr={r.ref:r.type for r in upstream.view.learning_requirements};cr={r.ref:r.type for r in upstream.view.coverage_requirements}
    blocks={b.role:b for b in view.teaching_blocks};assert len(blocks)==len(gold['blocks'])==5
    for expected in gold['blocks']:
        b=blocks[expected['role']]
        assert {lr[r] for r in b.covers_learning_requirement_refs}==set(expected['learning_types'])
        assert {cr[r] for r in b.covers_coverage_requirement_refs}==set(expected['coverage_types'])
        assert {c.level for c in b.constraints}==set(expected['levels'])
        for level in ('required','recommended','flexible'):
            if level+'_contains' in expected:assert expected[level+'_contains'] in ' '.join(c.statement for c in b.constraints if c.level==level)
        if 'content_type' in expected:
            assert any(c.type==expected['content_type'] and c.ref in b.instructional_content_refs for c in view.instructional_content)
    for attr in ('learning_requirements','coverage_requirements','evidence_boundaries'):
        assert {r.ref:r for r in getattr(upstream.view,attr)}=={r.ref:r for r in getattr(view.source_learning_specification,attr)}
    assert all(not c.formula_memorisation_required and c.status=='candidate_slot' for c in view.instructional_content)
    assert view.coverage_map.status=='planned_coverage' and view.status=='candidate'
    assert 'question_wording' not in serial
    pinned=json.loads(Path('output/academic_knowledge_v03/stable_baseline_sha256.json').read_text(encoding='utf-8'))['files']
    changed=[f for f,digest in pinned.items() if Path(f).exists() and hashlib.sha256(Path(f).read_bytes()).hexdigest()!=digest]
    missing=[f for f in pinned if not Path(f).exists()]
    assert not changed and missing==['AI_Academic_Operating_System_Brainstorm_CN.pptx']
    assert state()==before['database'] and counts()==before_counts
    tests=test_result()
    report=dict(status='P3B PEDAGOGICAL SPECIFICATION CANDIDATE PASSED',artifact_status=view.status,
        schema_version=view.schema_version,upstream_schema_version='learning-specification/1',
        teaching_block_count=len(view.teaching_blocks),instructional_slot_count=len(view.instructional_content),
        preserved_counts=dict(learning_requirements=len(lr),coverage_requirements=len(cr),evidence_boundaries=len(view.evidence_boundaries)),
        coverage_map=view.coverage_map.model_dump(mode='json'),gold_standard_passed=True,
        database_before=before['database'],database_after=state(),counts_before=before_counts,counts_after=counts(),
        new_source_decisions=0,new_academic_decisions=0,new_governance_decisions=0,new_trusted_snapshots=0,
        upstream_files_unchanged=before['files'],learning_output_byte_identical=True,
        snapshot_usability=upstream.provenance['upstream']['upstream']['snapshot_usability'],
        determinism=dict(repeated=True,reversed_snapshots=True,reversed_collections=True,sha256=hashlib.sha256(serial.encode()).hexdigest()),
        protected_files=dict(changed=changed,missing=missing),test_results=tests,
        architectural_decisions=[
            'No frozen upstream schema changed; service consumes freshly validated LearningSpecificationService.',
            'Pedagogical rules use requirement types and source refs, never topic/question/year branching or the Gold Standard.',
            'Required means planned design obligation, not proof of sufficient generated content.',
            'Visual comparison and guided-to-independent progression are recommendations; no fixed practice sequence is required.',
            'Exact calculation method and structured input notation are unavailable upstream; candidate slots preserve cautions without inventing formulas or glyphs.',
            'Source learning requirements, coverage requirements and boundaries retain exact content; evidence is referenced compactly without reproducing question wording.',
            'Normal output uses Product refs; separate provenance retains canonical traceability.',
            'Candidate status creates no new approval, review ticket or governance system.'
        ],changed_files=['academic_os/pedagogical_models.py','academic_os/pedagogical_core.py','academic_os/pedagogical_service.py',
            'academic_os/cli.py','tests_p0/test_pedagogical_specification.py','tests_p0/pedagogical_specification_acceptance.py',
            'tests_p0/fixtures/pedagogical_standard_deviation_gold.json','docs/P3B_PEDAGOGICAL_SPECIFICATION.md'])
    (OUT/'standard_deviation.json').write_bytes(serial.encode())
    for name,data in [('provenance',result.provenance),('acceptance',report)]:
        (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=report['status'],artifact_status=view.status,tests=tests,counts=counts(),database_unchanged=True),indent=2))


if __name__=='__main__':main()
