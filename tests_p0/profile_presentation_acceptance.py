"""P5D live acceptance, source preservation and final artifact evidence."""
import hashlib
import json
from pathlib import Path
from academic_os.profile_presentation_service import ProfilePresentationService
from academic_os.profile_presentation import build_profile_manifest, same_scope
from academic_os.profile_presentation_validation import validate_profile_artifact
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/p5d_profiled_presentation')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_log(name,count):
    raw=(OUT/name).read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    assert f'Ran {count} tests' in text and text.strip().endswith('OK'),name
    assert sum(line.endswith(' ... ok') for line in text.splitlines())==count,name
    return dict(passed=count,failures=0,errors=0,sha256=sha(OUT/name))


def main():
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))
    assert state()==before['database']
    for path,digest in before['files'].items():assert sha(path)==digest,path
    old_counts=counts();service=ProfilePresentationService('var/p0_q2.sqlite3')
    inputs,provenance=service.read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    same_scope(inputs);profiles={}
    qa=json.loads((OUT/'visual_review.json').read_text(encoding='utf-8'))
    for key,i in inputs.items():
        manifest=build_profile_manifest(i);directory=OUT/key
        artifact=directory/('Standard_Deviation_'+key+'.pptx')
        report=validate_profile_artifact(artifact,manifest,i)
        assert report.valid,report.violations
        assert report.serialize().encode()==(directory/'artifact_render_validation.json').read_bytes()
        assert manifest.serialize().encode()==(directory/'presentation_manifest.json').read_bytes()
        hashes={p.name:sha(p) for p in directory.iterdir() if p.is_file()}
        reused=service._render_one(i,provenance,directory)
        assert reused['reused'] and hashes=={p.name:sha(p) for p in directory.iterdir() if p.is_file()}
        build=Path(json.loads((directory/'provenance.json').read_text(encoding='utf-8'))['build_directory'])
        receipt=json.loads((build/'toolkit-validation.json').read_text(encoding='utf-8'))
        assert receipt['finalSha256']==sha(artifact)
        previews={str(p):sha(p) for p in sorted((build/'preview').glob('*.png'))}
        assert len(previews)==len(manifest.slides) and qa['profiles'][key]['preview_sha256']==previews
        profiles[key]=dict(slide_count=len(manifest.slides),role_count=len(manifest.role_coverage),
            scope_fingerprint=manifest.academic_scope_fingerprint,learning_requirement_refs=report.learning_requirement_refs,
            target_density_attained=manifest.target_density_attained,artifact_validation=report.model_dump(mode='json'),
            file_sha256=hashes,preview_sha256=previews,idempotent_reuse_verified=True)
    tests={name:test_log(name,n) for name,n in [('baseline-tests.txt',137),('new-tests.txt',30),('final-tests.txt',262)]}
    assert state()==before['database'] and counts()==old_counts
    for path,digest in before['files'].items():assert sha(path)==digest,path
    result=dict(status='P5D acceptance passed',profiles=profiles,tests=tests,full_repository_suite_run=False,
        database_before=before['database'],database_after=state(),counts_before=old_counts,counts_after=counts(),
        protected_files_checked=len(before['files']),new_reviews=0,new_snapshots=0,new_governance_decisions=0,
        visual_review=qa,minimum_only_subset_test='test_11_minimum_target_subset',
        frozen_p4c1_semantic_regression='test_05_focused_semantic_regression',
        limitations=['No native PowerPoint rendering verification.','No timing, difficulty, quality or mastery guarantee.'])
    payload=(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    target=OUT/'acceptance.json'
    if target.exists() and target.read_bytes()!=payload:raise ValueError('Different existing acceptance evidence')
    target.write_bytes(payload)
    print(json.dumps(dict(status=result['status'],slides={k:v['slide_count'] for k,v in profiles.items()},tests=tests),indent=2))


if __name__=='__main__':main()
