"""Reuse v0.3 reference rules without treating candidate status fields as credentials.

P0 review events remain external to the v0.3 candidate representation. The legacy
review digest is NOT used as the publication gate; P0 binds the complete graph.
"""
from pathlib import Path
import academic_knowledge_schema_v03 as v3
from validate_academic_knowledge_v03 import (validate_document,ExternalTrust,SourceVerification,LocatorVerification,digest)
from .core import decision_state

COLLECTION={'context':'contexts','competency':'competencies','question':'questions',
 'question_part':'question_parts','condition':'task_conditions','evidence':'evidence','part_mapping':'part_mappings',
 'concept':'concepts','concept_link':'concept_links'}

def validate_v03(graph,decisions,reference_graph=None):
    # A reused definition may cite a locator whose descriptive question/part
    # association is outside this publication closure. Validate all original
    # associations first, without granting any external trust to unrelated data.
    if reference_graph is not None:validate_v03(reference_graph,{})
    data={name:[] for name,f in v3.AcademicKnowledgePrototype.model_fields.items()
          if name not in ['schema_version','purpose','evidence_notice']}
    data['evidence_notice']='P0 candidate projection. Trust comes only from the operator database; publication uses the P0 dependency gate.'
    trust=ExternalTrust()
    for key,r in graph.items():
        rec=r['record'];p=rec['payload'];kind=rec['kind']
        if kind=='source':
            obj={k:p[k] for k in v3.SourceDocument.model_fields}
            if decision_state(graph,key,decisions.get(key))=='verify':
                obj.update(verification_status='verified',verification_reference='db:'+decisions[key]['decision_id'])
                trust.sources[obj['verification_reference']]=SourceVerification(digest(obj),Path(obj['artifact_reference']),obj['content_digest'])
            data['sources'].append(obj)
        elif kind=='locator':
            obj={k:p[k] for k in v3.SourceLocator.model_fields}
            if reference_graph is not None:
                # Projection only: original records, hashes and dependency manifests
                # are untouched. Full association validation above is mandatory.
                if 'question_part:'+str(obj['assessment_part_id']) not in graph:obj['assessment_part_id']=None
                if 'question:'+str(obj['assessment_question_id']) not in graph:obj['assessment_question_id']=None
            skey='source:'+p['source_id']
            if decision_state(graph,key,decisions.get(key))=='verify' and decision_state(graph,skey,decisions.get(skey))=='verify':
                obj.update(verification_status='verified',verification_reference='db:'+decisions[key]['decision_id'])
                trust.locators[obj['verification_reference']]=LocatorVerification(digest(obj),graph[skey]['record']['payload']['content_digest'],p['extracted_text'])
            data['locators'].append(obj)
        elif kind in COLLECTION:
            # The v0.3 validator checks its unchanged domain projection. P1A's
            # semantic extension is validated by the same P0 dependency graph.
            projected={k:v for k,v in p.items() if k!='semantics'} if kind=='part_mapping' else p
            data[COLLECTION[kind]].append(projected)
        # P0 scope records are explicit candidate associations, not invented OfficialObjectiveReferences.
    pairs=set()
    for key,r in graph.items():
        if r['record']['kind'] in ['part_mapping','question_part']:
            p=r['record']['payload'];part=p['part_id']
            for ref in r['record']['judgment_refs']:
                if ref.startswith('condition:'):pairs.add((part,ref.split(':',1)[1]))
    data['part_condition_links']=[dict(part_id=p,condition_id=c) for p,c in sorted(pairs)]
    return validate_document(data,trust)
