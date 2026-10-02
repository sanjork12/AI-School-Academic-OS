"""Read-only P5A acceptance, including explicit density-versus-scope proof."""
import hashlib,json
from pathlib import Path
from academic_os.lesson_profile_service import LessonProfileService,save_profile_read
from academic_os.lesson_profiles import KEYS,DENSITY_KEYS
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p5a_lesson_profiles')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(name):
    raw=(OUT/name).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')

def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for file,h in before['files'].items():assert digest(file)==h,file
    old_counts=counts();service=LessonProfileService(Path('var/p0_q2.sqlite3'))
    result=service.read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    reverse=service.read_profiles('standard-deviation',tuple(reversed(PROTECTED_SNAPSHOTS)))
    for k in KEYS:assert result.views[k].serialize()==reverse.views[k].serialize()
    paths=save_profile_read(result,OUT);hashes={p:digest(p) for p in paths}
    save_profile_read(result,OUT);assert hashes=={p:digest(p) for p in paths}
    fr,sl=(result.views[k] for k in KEYS)
    assert fr.academic_scope_fingerprint==sl.academic_scope_fingerprint
    assert fr.learning_requirement_refs==sl.learning_requirement_refs and len(fr.learning_requirement_refs)==3
    assert fr.coverage_requirement_refs==sl.coverage_requirement_refs and len(fr.coverage_requirement_refs)==2
    assert fr.source_learning_specification==sl.source_learning_specification
    assert fr.source_base_pedagogy==sl.source_base_pedagogy
    assert fr.evidence_boundaries==sl.evidence_boundaries
    assert (len(fr.profiled_roles),len(sl.profiled_roles))==(9,15)
    assert all(v.valid and v.ready_for_content_authoring and not v.ready_for_rendering for v in result.validations.values())
    comparison={kind:{k:getattr(result.views[k].density_summary,kind).model_dump() for k in KEYS} for kind in DENSITY_KEYS}
    assert [comparison[k]['focused-review']['target'] for k in DENSITY_KEYS]==[1,1,0,1,0,1,1,0,2,1,1,0]
    assert [comparison[k]['standard-lesson']['target'] for k in DENSITY_KEYS]==[1,1,1,1,1,1,2,2,3,1,1,1]
    focused=log('focused-tests.txt');baseline=log('baseline-tests.txt')
    assert 'Ran 180 tests' in focused and focused.strip().endswith('OK')
    assert sum(line.endswith(' ... ok') for line in focused.splitlines())==180
    assert 'Ran 40 tests' in baseline and baseline.strip().endswith('OK')
    assert state()==before['database'] and counts()==old_counts
    report=dict(status='P5A acceptance passed',tests=dict(baseline_passed=40,new_profile_tests_passed=50,total=180,passed=180,failures=0,errors=0,full_repository_suite_run=False),
        density_comparison=comparison,scope=dict(fingerprints={k:v.academic_scope_fingerprint for k,v in result.views.items()},
            same_learning_specification=fr.source_learning_specification.model_dump(),same_base_pedagogy=fr.source_base_pedagogy.model_dump(),
            learning_requirement_refs=fr.learning_requirement_refs,coverage_requirement_refs=fr.coverage_requirement_refs,
            evidence_boundary_refs=[b.ref for b in fr.evidence_boundaries],all_evidence_boundaries_preserved=True,academic_scope_expanded=False),
        planning={k:dict(role_count=len(v.profiled_roles),substantive_role_count=sum(r.substantive for r in v.profiled_roles),
            minimum_content_items=sum(r.items.minimum for r in v.profiled_roles),target_content_items=sum(r.items.target for r in v.profiled_roles),
            duration=result.profiles[k].duration.model_dump(),time_plan_is_guidance_only=True,
            new_authoring_role_refs=[a.role_ref for a in v.authoring_requirements if a.reuse_hint=='new_authoring_required'],
            additional_target_items={a.role_ref:a.additional_target_items for a in v.authoring_requirements if a.additional_target_items},
            populated_content_items=0,ready_for_rendering=False) for k,v in result.views.items()},
        determinism=dict(repeated_export_identical=True,reversed_snapshot_order_identical=True),
        source_configuration='User-specified Gold product design, not academic review credentials',
        database_before=before['database'],database_after=state(),counts_before=old_counts,counts_after=counts(),
        new_reviews=0,new_governance_decisions=0,new_snapshots=0,upstream_and_presentation_files_unchanged=before['files'],output_sha256=hashes,
        limitations=['Planning only; no authored questions, examples or answers.','Potential P4A reuse is not validated or counted as populated content.','Timing is not a runtime guarantee or a slide-count rule.'])
    data=(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode();target=OUT/'acceptance.json'
    if target.exists() and target.read_bytes()!=data:raise ValueError('Different existing acceptance evidence')
    target.write_bytes(data)
    print(json.dumps(dict(status=report['status'],tests=report['tests'],same_academic_scope=True,roles={'focused-review':9,'standard-lesson':15}),indent=2))

if __name__=='__main__':main()
