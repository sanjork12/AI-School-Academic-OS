"""P5B acceptance: current chain, exact reuse identity, new maths, frozen state."""
import json,hashlib
from collections import Counter
from pathlib import Path
from academic_os.profiled_content_service import ProfiledContentService,save_profiled_content
from academic_os.profiled_sd_provider import verify_new_content
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p5b_profiled_authoring')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def log(name):
    raw=(OUT/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')

def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for file,h in before['files'].items():assert sha(file)==h,file
    old_counts=counts();result=ProfiledContentService(Path('var/p0_q2.sqlite3')).read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    paths=save_profiled_content(result,OUT);hashes={p:sha(p) for p in paths}
    save_profiled_content(result,OUT);assert hashes=={p:sha(p) for p in paths}
    fr=result.packages['focused-review'];sl=result.packages['standard-lesson']
    assert Counter(d.decision for d in fr.role_decisions)=={'reuse':9}
    assert Counter(d.decision for d in sl.role_decisions)=={'reuse':7,'author_new':7}
    assert len(fr.new_content)==0 and len(sl.new_content)==7
    assert {r.ref for r in fr.reused_content}=={r.ref for r in sl.reused_content}
    assert fr.academic_scope_fingerprint==sl.academic_scope_fingerprint
    assert fr.learning_requirement_refs==sl.learning_requirement_refs and len(fr.learning_requirement_refs)==3
    assert fr.coverage_requirement_refs==sl.coverage_requirement_refs and fr.evidence_boundaries==sl.evidence_boundaries
    assert all(p.content_complete and p.minimum_density_met and p.target_density_met and p.ready_for_p5c and not p.ready_for_rendering for p in result.packages.values())
    solutions={s.item_ref:s for s in sl.new_solutions};numerical=[]
    for item in sl.new_content:
        assert verify_new_content(item,solutions[item.ref]).status=='verified'
        if item.summary or item.raw_values:
            numerical.append(item.ref)
            assert verify_new_content(item,solutions[item.ref].model_copy(update={'numeric_answer':'999'})).status=='failed'
    assert len(numerical)==6
    d=next(d for d in sl.role_decisions if d.role_key=='SL-12')
    assert len(d.reused_content_refs)==2 and len(d.new_content_refs)==1
    final=log('final-tests.txt');baseline=log('baseline-tests.txt')
    assert 'Ran 190 tests' in final and final.strip().endswith('OK')
    assert sum(line.endswith(' ... ok') for line in final.splitlines())==190
    assert 'Ran 145 tests' in baseline and baseline.strip().endswith('OK')
    assert state()==before['database'] and counts()==old_counts
    report=dict(status='P5B acceptance passed',tests=dict(baseline_passed=145,new_tests_passed=45,final_total=190,passed=190,failures=0,errors=0,full_repository_suite_run=False,
        initial_development_run='Boundary collection order mismatch caused 6 failures/2 errors; corrected to compare complete boundary objects by stable ref; final run passed.'),
        packages={key:dict(decisions=dict(Counter(d.decision for d in p.role_decisions)),role_decisions=[d.model_dump(mode='json') for d in p.role_decisions],
            reused_refs=[r.ref for r in p.reused_content],new_refs=[q.ref for q in p.new_content],unresolved=p.unresolved_role_refs,
            content_complete=p.content_complete,minimum_density_met=p.minimum_density_met,target_density_met=p.target_density_met,
            ready_for_p5c=p.ready_for_p5c,ready_for_rendering=p.ready_for_rendering) for key,p in result.packages.items()},
        academic_scope=dict(fingerprint=fr.academic_scope_fingerprint,same_scope=True,learning_requirement_refs=fr.learning_requirement_refs,coverage_requirement_refs=fr.coverage_requirement_refs),
        maths=dict(existing_engine_reused=True,numerical_items_recomputed=numerical,each_corrupt_numeric_answer_rejected=True,concept_response_exact_string_grading=False),
        output_sha256=hashes,database_before=before['database'],database_after=state(),counts_before=old_counts,counts_after=counts(),
        new_reviews=0,new_governance_decisions=0,new_snapshots=0,frozen_files_unchanged=before['files'],
        limitations=['Candidate pending P5C. No render/publication eligibility.','Concept expected meanings are deterministic authored responses, not a student NLP grading system.'])
    payload=(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();target=OUT/'acceptance.json'
    if target.exists() and target.read_bytes()!=payload:raise ValueError('Different existing acceptance evidence')
    target.write_bytes(payload)
    print(json.dumps(dict(status=report['status'],tests=report['tests'],focused_review=report['packages']['focused-review']['decisions'],standard_lesson=report['packages']['standard-lesson']['decisions']),indent=2))

if __name__=='__main__':main()
