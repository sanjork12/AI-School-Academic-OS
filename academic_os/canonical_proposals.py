"""Evidence-driven semantic rules and lookup, independent of question/year/answers.

Intentionally small transparent vocabulary, not a general natural-language model.
No imports from case fixtures or Gold Standard oracles.
"""
import re
from .core import decision_state, evaluate
from .sources import integrity
from .models import normalise
from validate_academic_knowledge_v03 import digest


def name_key(text):
    text=text.lower().replace('average','mean').replace('std deviation','standard deviation')
    return ' '.join(re.sub(r'\b(the|a|an)\b',' ',re.sub(r'[^a-z ]',' ',text)).split())


class Registry:
    def __init__(self,graph,decisions):
        self.graph=graph;self.decisions=decisions;self.cache={}

    def lookup(self,kind,name):
        field={'competency':'skill_name','concept':'name','task_condition':'name'}[kind]
        matches=[k for k,r in self.graph.items() if r['record']['kind']==kind and name_key(r['record']['payload'][field])==name_key(name)]
        trusted=[]
        for k in matches:
            if k not in self.cache:
                from .core import manifest
                self.cache[k]=evaluate(self.graph,[k],self.decisions,integrity(self.graph,manifest(self.graph,[k])))['publishable']
            if self.cache[k]:trusted.append(k)
        action='reuse_existing' if len(trusted)==1 and len(matches)==1 else ('unresolved' if matches else 'create_candidate')
        return dict(kind=kind,query=name,candidate_action=action,matches=[dict(key=k,version=self.graph[k]['version'],state=decision_state(self.graph,k,self.decisions.get(k))) for k in sorted(matches)],
                    selected=trusted[0] if action=='reuse_existing' else None)


def interpret(prompt,directive,scheme,notes,context):
    """No identity arguments: only source-derived linguistic evidence."""
    p=' '.join((directive+' '+prompt).lower().split());e=' '.join((scheme+' '+notes).lower().split())
    if re.search(r'clean|prepar',p) and re.search(r'replac|convert',e) and 'numerical value' in e:
        return dict(competency='Prepare data for statistical analysis',concept='Data cleaning / data preparation',
            task='Handle special/non-numeric values before calculating summary statistics',kind='input_form',
            scope='Partial evidence: replacing special/non-numeric values before summary calculations only; not all data preparation operations.',
            rule='Preparation instruction and scored numerical replacement evidence')
    calculation=bool(re.search(r'calculat|comput|work out|find',p))
    summary=bool(re.search(r'∑|summary statistics|sum of|summarised',context.lower()))
    if calculation and summary and ('standard deviation' in p) and ('standard deviation' in e or 'variance' in e):
        return dict(competency='Calculate standard deviation',concept='Standard deviation',task='From summary statistics',kind='input_form',
            scope='Partial evidence: compute a dispersion estimate from supplied summaries; estimate/context does not define a new competency.',rule='Calculation request, dispersion scoring and supplied summaries')
    if calculation and summary and re.search(r'\bmean\b|\baverage\b',p) and re.search(r'\bB1\b',scheme):
        return dict(competency='Calculate the mean',concept='Mean',task='From summary statistics',kind='input_form',
            scope='Partial evidence: compute a mean estimate from supplied summaries; estimation is a question condition.',rule='Mean calculation request, scored response and supplied summaries')
    if ('not be suitable' in p or 'not suitable' in p or 'representative' in p) and ('representative' in e) and ('covers' in e or 'whole year' in e or 'coverage' in e):
        return dict(competency='Assess whether data are representative',concept='Representativeness',
            task='Compare dataset coverage with the target population/time period',kind='comparison_form',
            scope='Partial evidence: coverage relative to a target period/population; not every aspect of data suitability.',rule='Suitability/representativeness request with coverage-based scoring evidence')
    directional=('estimate' in p and ('differ' in p or 'effect' in p)
                 and ('underestimate' in e or 'overestimate' in e) and ('missing' in e or 'coverage' in e))
    return dict(competency=None,concept=None,task=None,kind=None,
        scope='Observed reasoning is retained; canonical equivalence/distinctness is not established by this evidence alone.',
        rule='No sufficiently specific supported canonical rule; do not infer identity from contextual similarity',
        lookup_query=('Evaluate the effect of non-representative data on a statistical estimate' if directional else 'Contextual statistical reasoning'),
        alternatives=(['Apply representativeness to the direction of an estimate error',
                      'A distinct competency for effects of non-representative data on estimates may be needed; human boundary review required']
                      if directional else ['No supported semantic rule for this evidence', 'Human interpretation and canonical boundary review required']))


def semantic_plan(graph,decisions,parsed_keys):
    registry=Registry(graph,decisions);items={}
    def add(kind,payload,refs=()):
        raw=dict(kind=kind,payload=payload,judgment_refs=list(refs));key,v,record=normalise(raw)
        if key in graph:
            if graph[key]['version']!=v:raise ValueError('Existing candidate differs; explicit stage revision required: '+key)
        elif key in items and normalise(items[key])[1]!=v:raise ValueError('Ambiguous generated canonical definition: '+key)
        items[key]=record
        return key.split(':',1)[1]
    for pk in sorted(parsed_keys):
        parsed=graph[pk]['record']['payload'];part=graph['question_part:'+parsed['part_id']]['record']
        spans=parsed['spans']
        def texts(role):return '\n'.join(s['text'] for s in spans if s['role']==role)
        given='\n'.join(graph[k]['record']['payload'].get('description','') for k in part['judgment_refs'] if k.startswith('condition:'))
        meaning=interpret(texts('prompt'),texts('comparison_context'),texts('mark_scheme'),texts('mark_scheme_notes'),texts('shared_stem')+'\n'+given)
        provenance=dict(origin='real',creation_method='rule',source_references=sorted({'locator:'+s['locator_id'] for s in spans}))
        lookup=[];selected={};action='unresolved'
        if meaning['competency']:
            for kind,field in [('competency','competency'),('concept','concept'),('task_condition','task')]:
                found=registry.lookup(kind,meaning[field])
                previous=graph.get('proposal:PROPOSE-'+parsed['part_id'],{}).get('record',{}).get('payload',{})
                # Deterministic regeneration of our own still-pending candidates:
                # retain the original lookup observation, then verify exact content below.
                old=next((r for r in previous.get('registry_lookup',[]) if r['kind']==kind and r['query']==meaning[field]),None)
                owned=previous.get('competency_id') if kind=='competency' else next(iter(previous.get('concept_ids' if kind=='concept' else 'task_condition_ids',[])),None)
                if (old and old['candidate_action']=='create_candidate' and len(found['matches'])==1
                        and found['matches'][0]['key']==kind+':'+str(owned) and found['matches'][0]['state']=='pending'):
                    found=old
                lookup.append(found)
                if found['candidate_action']=='reuse_existing':selected[kind]=found['selected'].split(':',1)[1]
            if not any(r['candidate_action']=='unresolved' for r in lookup):
                for found in lookup:
                    kind=found['kind'];name=found['query']
                    if kind in selected:continue
                    prefix={'competency':'CAN-STAT-','concept':'CON-STAT-','task_condition':'TC-'}[kind]
                    cid=prefix+re.sub(r'[^A-Z0-9]+','-',name.upper()).strip('-')
                    common=dict(provenance=provenance)
                    if kind=='competency':payload=dict(canonical_id=cid,subject_domain='Statistics',skill_name=name,description=name+'. Evidence scope is recorded on each proposal.',**common)
                    elif kind=='concept':payload=dict(concept_id=cid,subject_domain='Statistics',name=name,description=name+' as a general statistical concept.',**common)
                    else:payload=dict(condition_id=cid,name=name,description=name+'. No particular dataset, year or numerical value is part of this identity.',kind=meaning['kind'],**common)
                    selected[kind]=add(kind,payload)
                action=lookup[0]['candidate_action']
        else:
            # Even an unresolved distinction queries the trusted registry; no automatic creation.
            lookup.append(registry.lookup('competency',meaning['lookup_query']))
        links=[]
        if action!='unresolved':
            matches=[k for k,r in graph.items() if r['record']['kind']=='concept_link' and r['record']['payload']['canonical_id']==selected['competency'] and r['record']['payload']['concept_id']==selected['concept']]
            if len(matches)==1:links=[matches[0].split(':',1)[1]]
            elif matches:raise ValueError('Ambiguous concept relationship; explicit resolution required')
            else:
                lid='LINK-'+digest([selected['competency'],selected['concept']])[:24]
                links=[add('concept_link',dict(link_id=lid,canonical_id=selected['competency'],concept_id=selected['concept'],
                    rationale='Pending proposal that this general competency applies this concept; question-specific scope remains separate.',provenance=provenance))]
        proposal=dict(proposal_id='PROPOSE-'+parsed['part_id'],parsed_part_id=parsed['parsed_id'],candidate_action=action,
            competency_id=selected.get('competency') if action!='unresolved' else None,
            concept_ids=[selected['concept']] if action!='unresolved' else [],concept_link_ids=links,
            task_condition_ids=[selected['task_condition']] if action!='unresolved' else [],
            observation=texts('prompt')+'\nScoring evidence:\n'+texts('mark_scheme')+'\nScoring notes:\n'+texts('mark_scheme_notes'),
            reasoning=meaning['rule'],evidence_scope=meaning['scope'],
            alternatives=meaning.get('alternatives',[]) if action=='unresolved' else [],registry_lookup=lookup,provenance=provenance)
        if action=='unresolved' and not proposal['alternatives']:proposal['alternatives']=['Matching registry identity is pending or ambiguous; resolve before reuse or creation']
        add('proposal',proposal)
    return dict(items=list(items.values()),expected_heads={k:graph.get(k,{}).get('version') for k in items})
