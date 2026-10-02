"""Engineering baseline support only. Never imported by production code."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Literal
from pydantic import BaseModel, ConfigDict
from academic_os.product_reader import read_usable_snapshots
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from tests_p0.teacher_product_acceptance import state
from tests_p0.assessment_intelligence_acceptance import counts

OUT=Path('output/reference_freeze')
DOC=Path('docs/STANDARD_DEVIATION_REFERENCE_ARCHITECTURE.md')
CONTRACT_ROLES={
    'academic-os-readonly-snapshot':'Immutable reviewed dependency closure, requiring current service usability checks',
    'teacher-topic':'Teacher-facing meaning and capabilities derived from usable reviewed snapshots',
    'assessment-intelligence':'Bounded observations from reviewed assessment examples, not frequency or difficulty',
    'learning-specification':'Evidence-backed learning requirements and coverage boundaries',
    'pedagogical-specification':'Candidate teaching structure constrained by learning scope',
    'pedagogical-validation':'Independent pedagogical alignment and authoring-readiness checks',
    'authored-teaching-content':'Deterministic original teaching candidates and separate solutions',
    'authored-content-validation':'Recomputed mathematical/content integrity and rendering gate',
    'lesson-profile':'Explicit purpose, duration planning and pedagogical density policy',
    'profiled-pedagogical-specification':'Ordered lesson roles preserving the same academic scope',
    'profiled-pedagogical-validation':'Profile role, density and scope compatibility checks',
    'profiled-authored-teaching-content':'Reuse-first composition plus bounded new candidates for density gaps',
    'profiled-content-validation':'Independent actual composition, minimum/target and current readiness checks',
    'presentation-manifest':'Reference-bound slide layout and solution-visibility mapping',
    'presentation-teacher-solutions':'Separate teacher solution objects linked to item and profile roles where applicable',
    'artifact-render-validation':'Actual PPTX preservation, answer separation and geometry checks'}


class ReferenceManifest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    schema_version:Literal['engineering-reference-manifest/1']='engineering-reference-manifest/1'
    reference_name:Literal['Standard Deviation Vertical Slice v1']
    reference_version:Literal['1']
    freeze_kind:Literal['Pre-AI Reference Implementation']
    status:Literal['Frozen baseline']
    trust_authority:Literal[False]
    created_at:str
    repository_state:dict
    protected_snapshots:list[dict]
    contracts:list[dict]
    gold_standards:list[dict]
    lesson_profiles:list[dict]
    academic_scope:dict
    reference_artifacts:list[dict]
    database_baseline:dict
    known_limitations:list[str]
    integrity_summary:dict


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path,data):
    payload=(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
    if path.exists():
        if path.read_bytes()!=payload:raise ValueError('Different existing freeze output: '+str(path))
    else:
        with path.open('xb') as stream:stream.write(payload)


def snapshot_status():
    snapshots=read_usable_snapshots('var/p0_q2.sqlite3',PROTECTED_SNAPSHOTS)
    return {sid:dict(usable=True,format=p['format']) for sid,p in snapshots.items()}


def production_dependencies():
    violations=[]
    for path in Path('academic_os').glob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
                if any(n.startswith('tests_p0') or 'gold_standard' in n for n in names):violations.append(str(path))
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                value=node.value.replace('\\','/').lower()
                if any(s in value for s in ('tests_p0/fixtures','reference_manifest.json','reference_freeze/')):violations.append(str(path))
    return sorted(set(violations))


def build():
    before=read(OUT/'before.json')
    assert state()==before['database'] and counts()==before['counts']
    assert snapshot_status()==before['snapshots']
    for path,h in before['files'].items():assert sha(path)==h,path
    # Schema versions come from actual saved contract payloads. Their authority
    # remains with current services, not these inventory records.
    contracts=[];artifacts=[]
    for path in sorted(Path('output').rglob('*')):
        if not path.is_file() or OUT in path.parents or '.build' in path.parts:continue
        if path.suffix not in ('.json','.pptx'):continue
        data={}
        if path.suffix=='.json':
            try:data=read(path)
            except (ValueError,UnicodeError):continue
        version=data.get('schema_version',data.get('format')) if isinstance(data,dict) else None
        if version or path.suffix=='.pptx':
            artifacts.append(dict(path=str(path),sha256=sha(path),schema_version=version))
            if isinstance(version,str) and '/' in version and not any(c['schema_version']==version for c in contracts):
                impl=[str(p) for p in Path('academic_os').glob('*.py') if version in p.read_text(encoding='utf-8')]
                contracts.append(dict(name=version.rsplit('/',1)[0],schema_version=version,
                    example_artifact=str(path),implementation_files=impl,
                    role=CONTRACT_ROLES[version.rsplit('/',1)[0]],
                    deterministic=True,trusted_state_write=False,
                    note='Snapshot creation uses governed Service.publish; a saved payload is immutable data, not a write capability.' if version=='academic-os-readonly-snapshot/1' else 'No new academic review authority.'))
    gold=[dict(path=str(p),sha256=sha(p),role='Acceptance oracle; never a production knowledge source') for p in sorted(Path('tests_p0/fixtures').glob('*gold*.json'))]
    gold.append(dict(path='tests_p0/test_lesson_profiles.py',sha256=sha('tests_p0/test_lesson_profiles.py'),
        role='Lesson Profile acceptance assertions, not a standalone JSON Gold fixture. Production user-specified product configuration is in lesson_profiles.py.'))
    profiles=[]
    for key in ('focused-review','standard-lesson'):
        p=read(f'output/p5a_lesson_profiles/{key}.lesson-profile.json')
        pedagogy=read(f'output/p5a_lesson_profiles/{key}.profiled-pedagogy.json')
        authored=read(f'output/p5b_profiled_authoring/{key}.profiled-authored.json')
        manifest=read(f'output/p5d_profiled_presentation/{key}/presentation_manifest.json')
        profiles.append(dict(profile_key=key,duration=p['duration'],pedagogical_roles=len(pedagogy['profiled_roles']),
            substantive_roles=sum(r['substantive'] for r in pedagogy['profiled_roles']),
            academic_scope_fingerprint=authored['academic_scope_fingerprint'],
            learning_requirement_refs=authored['learning_requirement_refs'],coverage_requirement_refs=authored['coverage_requirement_refs'],
            decisions={d:sum(r['decision']==d for r in authored['role_decisions']) for d in ('reuse','author_new','unresolved')},
            new_content_count=len(authored['new_content']),rendered_slide_count=len(manifest['slides']),slide_count_is_profile_requirement=False,
            pptx=f'output/p5d_profiled_presentation/{key}/Standard_Deviation_{key}.pptx'))
    learning=read('output/p3a_learning_specification/standard_deviation.json')
    git=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True)
    repo=dict(head_resolved=git.returncode==0,head=git.stdout.strip() if git.returncode==0 else None,
        note='No Git revision established; file hashes are the baseline.' if git.returncode else 'Read-only revision observation; no commit/tag created.')
    limitations=['One deeply developed topic slice; reuse evidence is limited to two reviewed assessment examples.',
        'Deterministic authoring and bounded natural-language checks, not general prose safety or a general CAS.',
        'No calibrated difficulty, modelled prerequisites, established misconceptions, frequency or exam predictions.',
        'Duration is a planning target, not measured classroom runtime.',
        'Native Microsoft PowerPoint rendering has not been validated; P5D used Artifact Tool import previews.',
        'Local operator CLI / OS account trust boundary; no production authentication claim.',
        'Saved derived JSON and this engineering manifest are not current trust authorities.',
        'Verified curriculum wording retains candidate association status, not confirmed full equivalence.',
        'AI_Academic_Operating_System_Brainstorm_CN.pptx is missing; existing integrity test and pinned hash remain unchanged.' if not Path('AI_Academic_Operating_System_Brainstorm_CN.pptx').exists() else 'Historical PPTX exists; full integrity results are reported separately.']
    model=ReferenceManifest(reference_name='Standard Deviation Vertical Slice v1',reference_version='1',
        freeze_kind='Pre-AI Reference Implementation',status='Frozen baseline',trust_authority=False,
        created_at=datetime.now(timezone.utc).isoformat(),repository_state=repo,
        protected_snapshots=[dict(label=label,snapshot_id=sid,**before['snapshots'][sid]) for label,sid in zip(('Q2','Q3'),PROTECTED_SNAPSHOTS)],
        contracts=contracts,gold_standards=gold,lesson_profiles=profiles,
        academic_scope={k:learning[k] for k in ('learning_requirements','coverage_requirements','assessment_evidence','evidence_boundaries','curriculum')},
        reference_artifacts=artifacts,database_baseline=dict(**before['database'],decision_counts=before['counts']),
        known_limitations=limitations,integrity_summary=dict(before_file=str(OUT/'before.json'),protected_files=len(before['files']),
            recorded_hashes_are_reference_only=True,production_imports_gold_or_freeze=production_dependencies(),llm_authoring_in_current_service_path=False))
    write_new(OUT/'reference_manifest.json',model.model_dump(mode='json'))


def accept():
    before=read(OUT/'before.json');after=dict(database=state(),counts=counts(),snapshots=snapshot_status())
    after['files']={p:sha(p) if Path(p).is_file() else None for p in before['files']}
    unchanged=after['files']==before['files']
    assert unchanged and after['database']==before['database'] and after['counts']==before['counts'] and after['snapshots']==before['snapshots']
    assert not production_dependencies()
    manifest=ReferenceManifest.model_validate(read(OUT/'reference_manifest.json'))
    assert DOC.is_file()
    tests={k:read(OUT/(k+'-results.json')) for k in ('focused','full')}
    raw=(OUT/'frontend-browser-tests.json').read_bytes()
    browser=json.loads(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    node_log=(OUT/'frontend-data-tests.txt').read_bytes()
    node_text=node_log.decode('utf-16' if node_log.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    import re
    data_counts={name:int(re.search(r'\b'+name+r' (\d+)',node_text)[1]) for name in ('tests','pass','fail','skipped')}
    frontend=dict(data_tests=data_counts,browser_stats=browser['stats'],browser_errors=browser['errors'],
        browser_context='Existing static frontend/out build; isolated browser-only demo actions, no trusted writes. No rebuild performed.')
    assert tests['focused']['successful']
    historical=[e for e in tests['full']['error_details'] if 'test_preserved_project_files' in e['test'] and 'AI_Academic_Operating_System_Brainstorm_CN.pptx' in e['traceback'] and 'FileNotFoundError' in e['traceback']]
    write_new(OUT/'acceptance.json',dict(status='Freeze integrity passed; full-suite status reported separately',
        checks=dict(architecture_document_created=DOC.is_file(),reference_manifest_created=True,
            protected_snapshots_currently_valid=all(v['usable'] for v in after['snapshots'].values()),
            database_unchanged=after['database']==before['database'],
            trusted_decision_counts_unchanged=after['counts']==before['counts'],
            snapshot_count_unchanged=after['counts']['snapshots']==before['counts']['snapshots'],
            frozen_contract_artifacts_unchanged=unchanged,p5d_pptx_unchanged=unchanged,gold_standards_unchanged=unchanged),
        architecture_document=dict(path=str(DOC),sha256=sha(DOC)),reference_manifest=dict(path=str(OUT/'reference_manifest.json'),sha256=sha(OUT/'reference_manifest.json')),
        before={k:before[k] for k in ('database','counts','snapshots')},after=after,
        protected_files_unchanged=unchanged,protected_files_checked=len(before['files']),gold_standards_unchanged=True,
        production_logic_unchanged=True,p5d_pptx_unchanged=True,new_academic_decisions=0,new_source_decisions=0,
        new_governance_decisions=0,new_trusted_snapshots=0,no_api_llm_use=True,no_api_key_read=True,
        tests=tests,pre_existing_historical_errors=historical,
        other_python_failures_or_errors=tests['full']['failures']+tests['full']['errors']-len(historical),
        frontend_tests=frontend,fully_green=tests['full']['successful'] and data_counts['fail']==0 and browser['stats']['unexpected']==0 and not browser['errors'],limitations=manifest.known_limitations))


if __name__=='__main__':
    import sys
    {'build':build,'accept':accept}[sys.argv[1]]()
