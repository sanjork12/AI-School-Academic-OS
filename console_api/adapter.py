"""Read existing contracts, call existing services, adapt to display DTOs."""
import hashlib
import json
from pathlib import Path
from .models import *
from academic_os.product_catalog import PROTECTED_SNAPSHOTS
from academic_os.product_service import AcademicProductService
from academic_os.assessment_intelligence import AssessmentIntelligenceService
from academic_os.learning_service import LearningSpecificationService
from academic_os.pedagogical_service import PedagogicalSpecificationService
from academic_os.lesson_profile_service import LessonProfileService
from academic_os.authored_service import AuthoredTeachingService
from academic_os.content_validation_service import AuthoredContentValidationService
from academic_os.profiled_content_service import ProfiledContentService
from academic_os.profiled_validation_service import ProfiledContentValidationService

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / 'var/p0_q2.sqlite3'
SNAPSHOTS = list(PROTECTED_SNAPSHOTS)
PROFILE = 'standard-lesson'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def dump(m): return m.model_dump(mode='json')
def sources():
    return [Source(id='standard-deviation',title='Existing Standard Deviation · 9MA0',capability='Assemble & Validate',database=str(DATABASE),snapshots=SNAPSHOTS),
        Source(id='topic2',title='Existing Edexcel 4MA1 Topic 2',capability='READ / INSPECT only')]

class Registry:
    def __init__(self): self.entries = {}
    def add(self, path, title, category, historical=True):
        path = path.resolve()
        if not path.is_relative_to((ROOT/'output').resolve()) or not path.is_file():
            raise ValueError('Artifact outside allowlisted output root')
        digest = sha(path)
        identity = hashlib.sha256((path.relative_to(ROOT).as_posix()+digest).encode()).hexdigest()
        dto = Artifact(id=identity,title=title,sha256=digest,category=category,historical=historical)
        self.entries[identity] = (path,dto)
        return identity
    def get(self, identity):
        path,dto = self.entries[identity]
        if path.resolve()!=path or not path.resolve().is_relative_to((ROOT/'output').resolve()) or sha(path)!=dto.sha256:
            raise ValueError('Artifact changed since registration')
        return path,dto
    def list(self): return [entry[1] for entry in self.entries.values()]

def historical(registry):
    rows=[]
    roots=[('P6A.5','p6a5_live_symbolic_provenance','ai-candidate-*.json'),('P6A.6','p6a6_live_controlled_stress','ai-candidate-*.json'),('P6A.7b','p6a7b_sl11/offline-qualification','*.json')]
    frozen=read(ROOT/'output/reference_freeze_v1_7/reference_manifest.json')['files']
    replay=ROOT/'output/p6a7b_sl11/historical-replay.json'
    if frozen.get(replay.relative_to(ROOT).as_posix()) != sha(replay): raise ValueError('Frozen replay evidence changed')
    frozen.update({row['path']:row['sha256'] for row in read(replay)['historical_candidates']})
    for milestone,folder,pattern in roots:
        for path in sorted((ROOT/'output'/folder).rglob(pattern)):
            if frozen.get(path.relative_to(ROOT).as_posix()) != sha(path):
                raise ValueError('Historical evidence is not frozen or has changed')
            data=read(path);v=data['validation'];st=v.get('verification_summary',{}).get('stage_status',{})
            stages=[]
            for key,label in [('math_valid','Math'),('expression_semantics_valid','Expression semantics'),('derivation_provenance_valid','Derivation provenance'),('controlled_input_binding_valid','Controlled input')]:
                raw=st.get(key) or v.get(key.replace('_valid','_status'))
                value=v.get(key)
                state={'PASSED':'PASS','FAILED':'FAIL','NOT_EVALUATED':'NOT_EVALUATED','NOT_APPLICABLE':'NOT_APPLICABLE'}.get(raw)
                if state is None: state=('PASS' if value else 'FAIL') if isinstance(value,bool) else 'NOT_EVALUATED'
                if key=='controlled_input_binding_valid' and not (v.get('controlled_mode') or data.get('controlled_case')): state='NOT_APPLICABLE'
                stages.append(Evidence(id=key,label=label,status=state,details={'violations':v.get('violations',[]),'validation':v}))
            rows.append(Historical(id=path.relative_to(ROOT).as_posix(),milestone=milestone,role='SL-11' if milestone=='P6A.7b' else 'SL-10',mode='offline role-aware' if milestone=='P6A.7b' else 'historical live',model=str(data.get('model_metadata',{}).get('model','not recorded')),accepted=v['accepted'],evidence=stages,limitations=v.get('warnings',[])+['Experimental; not academic approval, publication, or P5 renderer eligibility.']))
    return rows

def curriculum(registry):
    from academic_os.curriculum_ingestion.validation import validate_curriculum
    graph=read(ROOT/'output/topic2_canonical_promoted.json')
    result=[]
    for tier in ('foundation','higher'):
        p=ROOT/f'output/topic2_{tier}_parsed.json';before=sha(p)
        d=read(p)
        checked=validate_curriculum(d,tier)
        if sha(p)!=before: raise ValueError('Curriculum changed during validation')
        nodes=[];mapped=total=0
        for sub in d['subtopics']:
            objectives=[]
            for obj in sub['objectives']:
                mappings=[m for m in graph['mappings'] if m['official_source_id']==obj['source_id']]
                objectives.append(Objective(**obj,mappings=mappings));total+=1;mapped+=bool(mappings)
            nodes.append(Subtopic(code=sub['code'],name=sub['name'],notes=sub['notes'],objectives=objectives))
        aid=registry.add(p,f'Topic 2 {tier} parsed curriculum','curriculum')
        result.append(Curriculum(topic_code=d['topic_code'],topic_name=d['topic_name'],tier_source=d['tier_source'],subtopics=nodes,warnings=d['warnings'],structure=Evidence(id=tier,label='Structure validation only',status='PASS' if checked['structure_valid'] else 'FAIL',details={'report':checked,'sha256':before},artifact_id=aid),mapped=mapped,total=total,artifact_id=aid))
    return result

def assembly(stage):
    # All nine public services read current academic inputs. No model provider.
    results={}
    services=[('source','Source / snapshot available',AcademicProductService,'read_topic'),('assessment','Assessment evidence available',AssessmentIntelligenceService,'read_topic'),('learning','Learning specification available',LearningSpecificationService,'read_topic'),('pedagogy','Pedagogical specification available',PedagogicalSpecificationService,'read_topic'),('profile','Profile available',LessonProfileService,'read_profiles'),('authored','Deterministic content assembled',AuthoredTeachingService,'read_topic'),('p4b','Authored content validation',AuthoredContentValidationService,'read_topic'),('content','Profiled content assembled',ProfiledContentService,'read_profiles'),('p5c','Profiled content validation',ProfiledContentValidationService,'read_profiles')]
    for key,label,cls,method in services:
        value=getattr(cls(DATABASE),method)('standard-deviation',SNAPSHOTS);results[key]=value
        details={'provenance':value.provenance}
        if key in ('source','assessment','learning','pedagogy'):details['view']=dump(value.view)
        if key=='profile':details['profile']=dump(value.profiles[PROFILE]);details['pedagogy']=dump(value.views[PROFILE])
        report = value.reports[PROFILE] if key=='p5c' else value.view if key=='p4b' else None
        valid=True
        if report is not None:
            details['report']=dump(report);valid=not report.violations
        stage(Evidence(id=key,label=label,status='PASS' if valid else 'FAIL',details=details))
        if not valid: raise ValueError(label+' failed')
    return results

def lesson_views(r, history):
    a=dump(r['authored'].view);p=dump(r['content'].packages[PROFILE]);ped=dump(r['profile'].views[PROFILE]);v=dump(r['p5c'].reports[PROFILE])
    # Bind the separately-read terminal report to the content shown to the user.
    if (r['p5c'].provenance['upstream'] != r['content'].provenance
        or r['content'].provenance['upstream'] != r['profile'].provenance
        or r['content'].provenance['source_p4b'] != r['p4b'].provenance
        or r['p4b'].provenance['upstream'] != r['authored'].provenance):
        raise ValueError('Validation/content provenance mismatch')
    decisions={x['role_ref']:x for x in p['role_decisions']};coverage={x['profiled_role_ref']:x for x in v['coverage_matrix']}
    blocks={x['ref']:x for x in a['content_blocks']};formulas={x['ref']:x for x in a['instructional_formulas']}
    items={x['ref']:x for k in ('worked_examples','practice_items','learning_checks') for x in a[k]}
    items.update({x['ref']:x for x in p['new_content']})
    solutions={x['item_ref']:x for x in a['solutions']+p['new_solutions']}
    roles=[];questions=[];answers=[]
    for role in ped['profiled_roles']:
        d=decisions.get(role['ref'],{});refs=d.get('reused_content_refs',[])+d.get('new_content_refs',[]);display=[]
        for ref in refs:
            block=blocks.get(ref);item=items.get(block.get('item_ref')) if block else items.get(ref)
            if item:
                sol=solutions.get(item['ref']);inputs={k:item[k] for k in ('summary','raw_values') if item.get(k)}
                questions.append(Question(id=item['ref'],role=role['role_key'],text=item['question'],inputs=inputs,solution_id=sol['ref'] if sol else None))
                display.append(Block(id=ref,text=item['question'],details=dict(inputs,scaffolding=item.get('scaffolding',[]))))
                if sol: answers.append(Solution(id=sol['ref'],item_ref=item['ref'],role=role['role_key'],steps=sol.get('method_steps',[]),answer=sol.get('display_answer') or sol.get('expected_meaning') or '',details=sol))
            elif block:
                display.append(Block(id=ref,text=block['text'],details={k:block[k] for k in ('visual','instructional_inputs') if block.get(k)}))
                for f in block['formula_refs']: display.append(Block(id=f,text=formulas[f]['display_expression']))
        if not refs: display.append(Block(id=role['ref'],text=role['title'],details={'learning_requirement_refs':p['framing'].get(role['ref'],[])}))
        eligible=[h for h in history if h.role==role['role_key'] and h.accepted]
        capability=('Historical live AI capability verified · experimental' if role['role_key']=='SL-10' else 'Offline role-aware capability verified · no live qualification') if eligible else 'NOT AI-ENABLED · not P6-qualified'
        roles.append(Role(id=role['ref'],slot=role['role_key'],semantic_role=role['kind'],title=role['title'],purpose=role['profile_reason'],source_type='REUSED' if d.get('decision')=='reuse' else 'DETERMINISTIC',source_refs=refs,validation='PASS' if coverage[role['ref']]['minimum_compliance'] else 'FAIL',ai_capability=capability,blocks=display))
    return Lesson(roles=roles,limitations=p['content_boundaries']),questions,answers
