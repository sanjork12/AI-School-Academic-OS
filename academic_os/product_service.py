"""Trusted snapshots -> deterministic teacher meaning. No candidates or oracle files.

Composition is private: callers enter through AcademicProductService, which
checks every supplied snapshot on every call, without a payload cache.
"""
from dataclasses import dataclass
import json
import re
from .product_catalog import TOPICS,product_ref
from .product_models import (TeacherTopicView,TopicIdentity,AcademicMeaning,
    CurriculumWording,Curriculum,Capability,AssessmentExample,TrustSummary)
from .product_reader import read_usable_snapshots
from .core import dependencies


class CompositionConflict(ValueError):pass


@dataclass(frozen=True)
class ProductRead:
    view:TeacherTopicView
    provenance:dict


def _text(text):return ' '.join(text.split())


def _definition(row):
    # Review receipts may differ; immutable academic content may not.
    payload={k:v for k,v in row['payload'].items() if k not in ('review_decision_id','registry_decision_id','verification_reference')}
    return json.dumps(dict(kind=row['kind'],judgment_refs=row['judgment_refs'],payload=payload),sort_keys=True,ensure_ascii=False)


def _compose(topic_key,snapshots):
    if topic_key not in TOPICS:raise ValueError('Unsupported teacher topic: '+topic_key)
    spec=TOPICS[topic_key];objects={};owners={}
    for sid,payload in sorted(snapshots.items()):
        for key,row in sorted(payload['objects'].items()):
            if row['publication_state']!=('verified' if row['kind'] in ('source','locator') else 'approved'):
                raise ValueError('Non-trusted object at product boundary: '+key)
            if key in objects and (row['content_version']!=objects[key]['content_version'] or _definition(row)!=_definition(objects[key])):
                raise CompositionConflict('Incompatible published versions for '+key+' in '+', '.join(owners[key]+[sid]))
            objects[key]=row;owners.setdefault(key,[]).append(sid)
    def get(key):
        if key not in objects:raise ValueError('Required published object missing: '+key)
        return objects[key]['payload']
    concept_key='concept:'+spec.concept;competency_key='competency:'+spec.competency;task_key='task_condition:'+spec.task_condition
    concept=get(concept_key);competency=get(competency_key);task=get(task_key)
    examples={};traces={};contexts={};used={concept_key,competency_key,task_key};selected_scopes=set()
    for sid,snapshot in sorted(snapshots.items()):
        for unit in snapshot.get('semantic_units',[]):
            for interpretation in unit['interpretations']:
                if (interpretation['competency']['id']!=spec.competency
                    or spec.concept not in {c['id'] for c in interpretation['concepts']}
                    or spec.task_condition not in {t['id'] for t in interpretation['task_conditions']}):continue
                local=snapshot['objects'];parsed_key=interpretation['parsed_part_ref']
                if parsed_key not in local:raise ValueError('Semantic unit refers outside its trusted snapshot')
                parsed=get(parsed_key);part_key='question_part:'+parsed['part_id'];part=get(part_key)
                question_key='question:'+part['question_id'];question=get(question_key)
                context_key='context:'+question['curriculum_context_id'];contexts[context_key]=get(context_key)
                mapping_keys=[k for k in ('part_mapping:'+interpretation['mapping_id'],'proposal:'+interpretation['mapping_id']) if k in local]
                if len(mapping_keys)!=1:raise ValueError('Published interpretation does not identify one mapping')
                mapping_key=mapping_keys[0];mapping=get(mapping_key)
                if mapping.get('candidate_action')=='unresolved':raise ValueError('Unresolved interpretation cannot enter teacher view')
                if (mapping.get('canonical_id',mapping.get('competency_id'))!=spec.competency
                    or parsed['part_id']!=unit['part_id']):raise ValueError('Published semantic identity mismatch')
                relations=mapping.get('semantics') or mapping
                if spec.task_condition not in relations.get('task_condition_ids',[]):
                    raise ValueError('Capability/task relationship lacks published support')
                links=[get('concept_link:'+lid) for lid in relations.get('concept_link_ids',[])]
                if not any(l['canonical_id']==spec.competency and l['concept_id']==spec.concept for l in links):
                    raise ValueError('Capability/concept relationship lacks published support')
                used.update((parsed_key,part_key,question_key,context_key,mapping_key))
                selected_scopes.update(k for k in objects[mapping_key]['judgment_refs'] if k.startswith('scope:'))
                # Preserve the reviewed question label. Only recognized metadata in
                # that label is separated; unknown formats stay null, never guessed.
                label=question['label'];date=re.search(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Summer|Winter)\s+(20\d{2})\b',label)
                paper=re.search(r'\b'+re.escape(contexts[context_key]['specification_code'])+r'/\d+\b',label)
                prompts=[s for s in parsed['spans'] if s['role'] in ('comparison_context','prompt')]
                prompts.sort(key=lambda s:(s['role']!='comparison_context',s['locator_id'],s['start']))
                if not prompts:raise ValueError('No approved bounded question wording')
                form_ids=sorted(t['id'] for t in interpretation['task_conditions'])
                example=AssessmentExample(assessment_label=label,session=date[1] if date else None,
                    year=int(date[2]) if date else None,paper=paper[0] if paper else None,
                    question_part=part['label'],question_wording=_text(' '.join(s['text'] for s in prompts)),
                    marks=parsed['marks'],capability_ref=product_ref(competency_key),
                    task_form_refs=(product_ref(task_key),),
                    reading_notes=tuple(sorted(set(parsed['warnings']))))
                identity=(question['paper_source_id'],parsed['part_id'])
                if identity in examples and examples[identity]!=example:raise CompositionConflict('Conflicting assessment evidence for '+str(identity))
                examples[identity]=example
                trace=traces.setdefault(identity,dict(snapshot_ids=[],mapping_keys=[],parsed_part_key=parsed_key,
                    canonical_id=spec.competency,concept_id=spec.concept,task_condition_ids=form_ids))
                trace['snapshot_ids']=sorted(set(trace['snapshot_ids']+[sid]));trace['mapping_keys']=sorted(set(trace['mapping_keys']+[mapping_key]))
    if not examples:raise ValueError('No reviewed assessment examples for this topic selection')
    if len(contexts)!=1:raise CompositionConflict('Teacher topic combines incompatible curriculum contexts')
    context=next(iter(contexts.values()))
    # Do not turn an approved candidate association into official equivalence.
    scope_by_locator={}
    for key in sorted(selected_scopes):
        scope=get(key)
        for lid in scope['locator_ids']:scope_by_locator.setdefault('locator:'+lid,[]).append(scope)
    curriculum=[];curriculum_trace=[]
    for key in sorted(set(concept.get('provenance',{}).get('source_references',[]))):
        if not key.startswith('locator:'):continue
        loc=get(key);source_key='source:'+loc['source_id'];source=get(source_key)
        if source['source_type']!='official_syllabus':continue
        text=_text(loc['extracted_text']);start=text.find(spec.curriculum_excerpt)
        if start<0:continue
        scopes=scope_by_locator.get(key,[])
        curriculum.append(CurriculumWording(section=loc['label'],wording=text[start:start+len(spec.curriculum_excerpt)],
            association_status='candidate' if scopes else 'unavailable',
            association_note='; '.join(sorted({s['description'] for s in scopes})) if scopes else 'This wording does not establish equivalence with the whole question.'))
        curriculum_trace.append(dict(locator_key=key,source_key=source_key,normalized_text_start=start,normalized_text_end=start+len(spec.curriculum_excerpt)))
        used.update((key,source_key))
    # Count unique verified sources supporting the selected published claims,
    # not every source in the input snapshots or the number of example questions.
    todo=list(used)
    while todo:
        key=todo.pop()
        for dep in dependencies(objects[key]):
            if dep not in objects:raise ValueError('Published dependency missing: '+dep)
            if dep not in used:used.add(dep);todo.append(dep)
    source_keys=sorted(k for k in used if objects[k]['kind']=='source')
    ordered=sorted(examples,key=lambda k:(-(examples[k].year or 0),examples[k].session or '',examples[k].paper or '',examples[k].question_part,k))
    view=TeacherTopicView(identity=TopicIdentity(view_key=topic_key,title=spec.title,subject=context['subject'],qualification=context['qualification'],
        awarding_body=context['exam_board'],specification_code=context['specification_code'],curriculum_section=competency['subject_domain']),
        concepts=(AcademicMeaning(ref=product_ref(concept_key),name=concept['name'],description=concept['description']),),
        capabilities=(Capability(ref=product_ref(competency_key),name=competency['skill_name'],description=competency['description'],
            concept_refs=(product_ref(concept_key),),task_forms=(AcademicMeaning(ref=product_ref(task_key),name=task['name'],description=task['description']),)),),
        curriculum=Curriculum(references=tuple(sorted(curriculum,key=lambda x:(x.section,x.wording)))),
        assessment_evidence=tuple(examples[k] for k in ordered),
        trust_summary=TrustSummary(curriculum_verified=bool(curriculum),curriculum_association_confirmed=False,
            canonical_knowledge_approved=True,assessment_evidence_reviewed=True,source_count=len(source_keys),
            reviewed_example_count=len(examples),scope_note='Reviewed examples only; no frequency, difficulty or trend inference. Curriculum verification refers to located wording, not confirmed scope equivalence.'))
    provenance=dict(input_snapshot_ids=sorted(snapshots),snapshot_usability={sid:True for sid in sorted(snapshots)},
        canonical_objects={k:dict(version=objects[k]['content_version'],snapshot_ids=owners[k]) for k in (concept_key,competency_key,task_key)},
        assessment_examples=[traces[k] for k in ordered],curriculum_excerpts=curriculum_trace,
        supporting_sources=source_keys,conflicts=[])
    provenance['product_refs']={product_ref(k):dict(object_key=k,version=objects[k]['content_version'],snapshot_ids=owners[k]) for k in (concept_key,competency_key,task_key)}
    return ProductRead(view,provenance)


class AcademicProductService:
    def __init__(self,database):self.database=database
    def read_topic(self,topic_key,snapshot_ids):
        if topic_key not in TOPICS:raise ValueError('Unsupported teacher topic: '+topic_key)
        return _compose(topic_key,read_usable_snapshots(self.database,snapshot_ids))
    def get_topic_view(self,topic_key,snapshot_ids):return self.read_topic(topic_key,snapshot_ids).view
