"""One explicit engineering revision, never a runtime academic data builder."""
import json
from pathlib import Path
from datetime import datetime, timezone

from academic_os.ai_qualification.reference_baseline import sha, production_files, compare_files
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_reader import read_usable_snapshots
from academic_os.product_service import AcademicProductService
from academic_os.profile_presentation_service import ProfilePresentationService
from academic_os.profile_presentation import build_profile_manifest, profile_teacher_solutions
from academic_os.profiled_pedagogy import scope_fingerprint
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT = Path('output/reference_freeze_v1_1')
DOC = 'docs/STANDARD_DEVIATION_REFERENCE_REVISION_v1_1.md'
PERFORMANCE_SOURCE_HASH = 'f70a902dd37a8cdb671edbe05d5250180c3068b8cb0469b5a097f71dd92bcbb8'
AUTHOR_MODULES = ('__init__', '__main__', 'brief', 'models', 'provider', 'service', 'validation')
QUALIFICATION_MODULES = ('__init__', '__main__', 'integrity', 'models', 'observer', 'reporting', 'runner', 'storage', 'stress', 'reference_baseline')
COVERAGE_ADDITIONS = ('academic_os/examples/__init__.py', 'academic_os/examples/q2.py',
                      'academic_os/examples/q2_semantics.py', 'academic_os/migrations/001_initial.sql')
SELECTION_CHANGES = ('academic_os/ai_qualification/__main__.py',
                     'academic_os/ai_qualification/integrity.py',
                     'academic_os/ai_qualification/reference_baseline.py')
TEST_CHANGES = ('tests_p0/test_reference_freeze.py', 'tests_p0/test_profile_presentation.py')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def normalized(files):return {Path(p).as_posix():h for p,h in files.items()}


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2);f.write('\n')


def authorized_deltas(root, parent_files):
    """Closed allowlist with the specifically reviewed P6A.1a result hash."""
    root=Path(root).resolve();deltas=[]
    for name, old in normalized(parent_files).items():
        path=root/name;current=sha(path) if path.is_file() else None
        if current!=old:
            if name!='academic_os/sources.py' or current!=PERFORMANCE_SOURCE_HASH:
                raise ValueError('Unexpected protected delta: '+name)
            deltas.append(dict(path=name,before=old,after=current,classification='performance_optimization'))
    return deltas


def live_comparisons(old):
    inputs,_=ProfilePresentationService('var/p0_q2.sqlite3').read_profiles('standard-deviation',PROTECTED_SNAPSHOTS)
    checks={};fingerprints={};profiles={}
    def equal(name, model, path):
        value=model.model_dump(mode='json') if hasattr(model,'model_dump') else model
        checks[name]=value==read(path)
    for key,i in inputs.items():
        equal(key+'.profile',i.profile,f'output/p5a_lesson_profiles/{key}.lesson-profile.json')
        equal(key+'.pedagogy',i.pedagogy,f'output/p5a_lesson_profiles/{key}.profiled-pedagogy.json')
        equal(key+'.authored',i.package,f'output/p5b_profiled_authoring/{key}.profiled-authored.json')
        equal(key+'.validation',i.report,f'output/p5c_profiled_validation/{key}.validation.json')
        equal(key+'.learning',i.learning,'output/p3a_learning_specification/standard_deviation.json')
        equal(key+'.base_pedagogy',i.base,'output/p3b_pedagogical_specification/standard_deviation.json')
        equal(key+'.base_authored',i.authored,'output/p4a_authored_teaching_content/standard_deviation.json')
        equal(key+'.base_validation',i.p4b,'output/p4b_authored_content_validation/standard_deviation.json')
        manifest=build_profile_manifest(i)
        equal(key+'.presentation',manifest,f'output/p5d_profiled_presentation/{key}/presentation_manifest.json')
        equal(key+'.solutions',profile_teacher_solutions(i,manifest),f'output/p5d_profiled_presentation/{key}/teacher_solutions.json')
        fingerprints[key]=scope_fingerprint(i.learning)
        previous=next(p for p in old['lesson_profiles'] if p['profile_key']==key)
        checks[key+'.scope_fingerprint']=fingerprints[key]==previous['academic_scope_fingerprint']
        profiles[key]=dict(target_minutes=i.profile.duration.target_minutes,roles=len(i.pedagogy.profiled_roles),
                           substantive_roles=sum(r.substantive for r in i.pedagogy.profiled_roles))
    product=AcademicProductService('var/p0_q2.sqlite3').read_topic('standard-deviation',PROTECTED_SNAPSHOTS).view
    equal('teacher_product',product,'output/p2a_teacher_view/standard_deviation.json')
    learning=inputs['standard-lesson'].learning.model_dump(mode='json')
    checks['academic_scope']=all(learning[k]==v for k,v in old['academic_scope'].items())
    if not all(checks.values()):raise ValueError('Live semantic difference: '+str([k for k,v in checks.items() if not v]))
    return dict(all_live_comparisons_equal=True,comparisons=checks,recomputed_scope_fingerprints=fingerprints,
                learning_requirements=learning['learning_requirements'],assessment_evidence=learning['assessment_evidence'],profiles=profiles)


def build():
    root=Path('.').resolve();start=read(OUT/'revision-start.json')
    old=read('output/reference_freeze/reference_manifest.json');before=read('output/reference_freeze/before.json')
    assert not compare_files(root,start['parent_files']), 'Parent artifacts changed during revision'
    old_accept=read('output/reference_freeze/acceptance.json')
    for field in ('architecture_document','reference_manifest'):
        assert sha(old_accept[field]['path'])==old_accept[field]['sha256']
    deltas=authorized_deltas(root,before['files'])
    assert len(deltas)==1 and state()==before['database']==start['database'] and counts()==before['counts']
    # No existing file from the observed starting state may change except these
    # explicitly requested engineering selection/current-conformance edits.
    for name,h in normalized(start['start_inventory']).items():
        if sha(root/name)!=h and name not in SELECTION_CHANGES+TEST_CHANGES:
            raise ValueError('Unexpected change during revision: '+name)
    old_inventory=normalized(before['files'])
    expected_new=set(COVERAGE_ADDITIONS)
    expected_new.update('academic_os/ai_authoring/'+m+'.py' for m in AUTHOR_MODULES)
    expected_new.update('academic_os/ai_qualification/'+m+'.py' for m in QUALIFICATION_MODULES)
    production=production_files(root)
    unexpected=set(production)-set(old_inventory)-expected_new
    if unexpected:raise ValueError('Unexpected production additions: '+str(sorted(unexpected)))
    live=live_comparisons(old)
    snapshots=read_usable_snapshots('var/p0_q2.sqlite3',PROTECTED_SNAPSHOTS)
    assert set(snapshots)==set(before['snapshots'])
    files={name:sha(root/name) for name in old_inventory}
    files.update(normalized(start['parent_files']))
    for name in production:files[name]=sha(root/name)
    additions=[]
    for dirname in ('p6a_ai_authoring','p6a1_offline_acceptance','p6a1_offline_acceptance_final','p6a1a_trusted_read_performance'):
        for p in sorted((root/'output'/dirname).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                name=p.relative_to(root).as_posix();files[name]=sha(p)
                additions.append(dict(path=name,classification='post_freeze_engineering_experiment',academic_reference=False))
    support=['docs/P6A_SINGLE_SLOT_AI_AUTHORING.md','docs/P6A1_LIVE_MODEL_QUALIFICATION.md',
             'docs/P6A1A_TRUSTED_READ_PERFORMANCE.md',DOC,'tests_p0/test_ai_authoring.py',
             'tests_p0/test_ai_qualification.py','tests_p0/test_source_cache.py',
             'tests_p0/test_source_cache_integration.py','tests_p0/test_reference_revision.py',
             'tests_p0/reference_revision.py',*TEST_CHANGES]
    for name in support:
        files[name]=sha(root/name)
        additions.append(dict(path=name,classification='verification_addition' if name.startswith('tests_p0/') else 'architecture_operational_documentation',academic_reference=False))
    for name in sorted(set(production)-set(old_inventory)):
        classification=('legacy_inventory_coverage_addition' if name in COVERAGE_ADDITIONS else
                        'engineering_baseline_selection' if name in SELECTION_CHANGES else 'post_v1_experimental_production_module')
        additions.append(dict(path=name,classification=classification,academic_reference=False))
    historical={a['path']:a['sha256'] for a in old['reference_artifacts']+old['gold_standards']}
    assert not compare_files(root,historical)
    performance=read('output/p6a1a_trusted_read_performance/acceptance.json')
    result=dict(schema_version='engineering-reference-revision/1',reference_name='Standard Deviation Vertical Slice',
        reference_version='v1.1',freeze_kind='pre_ai_reference_revision',revision_type='trusted_read_performance',
        parent_reference='v1',status='frozen_baseline_revision',trust_authority=False,
        created_at=datetime.now(timezone.utc).isoformat(),
        lineage=dict(parent_name='Standard Deviation Vertical Slice v1',
            parent_manifest=dict(path='output/reference_freeze/reference_manifest.json',sha256=sha('output/reference_freeze/reference_manifest.json')),
            parent_artifacts=start['parent_files'],authorized_change='P6A.1a Trusted Read Performance Fix',
            protected_production_deltas=deltas,semantic_change=False,academic_scope_change=False,
            trust_semantics_change=False,performance_change=True,
            p6a1b_engineering_selection_changes=[dict(path=p,before=normalized(start['start_inventory']).get(p),after=sha(root/p)) for p in SELECTION_CHANGES]),
        unexpected_deltas=[],files=files,production_inventory=production,historical_reference_artifacts=historical,
        additional_inventory=additions,invariance_evidence=live,
        performance_evidence=dict(before=performance['prior_diagnosis_baseline'],
            cold=dict(extractions=5,readers=5),warm=dict(extractions=0,readers=0),
            trust_checks=dict(product_reads=80,snapshot=160,integrity=240),
            observed=performance['timing_after_tests'],timings_are_guarantees=False),
        trust_principle='Cache extraction computation, not the trust decision',
        inventory_limitations=['v1 shallow inventory omitted examples and migration source; no historical byte equality is asserted for those coverage additions.',
            'Engineering baseline is local operator configuration, not signed authentication or academic authority.'])
    for field in ('academic_scope','lesson_profiles','gold_standards','protected_snapshots','reference_artifacts','database_baseline','contracts'):
        result[field]=old[field]
    path=OUT/'reference_manifest.json'
    if path.exists() or Path('output/reference_freeze_active.json').exists():
        raise ValueError('Refusing to overwrite a baseline or active descriptor')
    write_new(path,result)
    write_new('output/reference_freeze_active.json',dict(active_reference_version='v1.1',
        manifest_path=path.as_posix(),manifest_sha256=sha(path)))
    print(json.dumps(dict(manifest=str(path),protected_files=len(files),unexpected_deltas=0,live_comparisons=live['comparisons']),indent=2))


if __name__=='__main__':build()
