"""Read-only validation of content, derived reports, provenance and preserved files."""
import hashlib
import json
import re
from pathlib import Path
from teaching_assessment_schema import CorePack
from teaching_assessment_content import ROOT, OUT, NOTICE, SCHEME_NOTICE, ILLUSTRATIVE
from build_teaching_assessment_demo import derive, TARGETS

def require(ok,message):
    if not ok:raise ValueError(message)

def unique(items,label):
    require(len(items)==len(set(items)),f'Duplicate {label}')
    return set(items)

def validate_core(data):
    core=CorePack.model_validate(data).model_dump()
    cs=unique([c['competency_id'] for c in core['competencies']],'competency')
    require(core['material_notice']==NOTICE and core['mark_scheme_notice']==SCHEME_NOTICE,'Non-official notices required')
    require(core['context']['material_notice']==NOTICE,'Context provenance notice')
    source_ids=unique([s['source_id'] for s in core['context']['sources']],'source')
    for fact in core['context']['facts']:
        require(fact.get('kind') in ['official_source_derived_fact','teacher_demo_content'],'Unknown fact provenance')
        if fact['kind']=='official_source_derived_fact':require(fact.get('source_id') in source_ids,'Official fact missing verified source reference')
    for c in core['competencies']:
        require(not re.search('9MA0|ALEVEL|IGCSE|4MA1|IAL',c['competency_id']),'Curriculum-dependent competency ID')
        expected='GROUP-' if c['classification']=='teaching_only_grouping' else 'CAN-STAT-'
        require(c['competency_id'].startswith(expected),'Candidate/group ID distinction')
    require(unique([s['competency_id'] for s in core['scopes']],'scope')==cs,'Scope coverage')
    slides={s['slide_id']:s for s in core['slides']}
    unique([s['slide_id'] for s in core['slides']],'slide')
    require(set(slides)==set(range(1,len(slides)+1)) and 18<=len(slides)<=25,'Slide sequence/count')
    checks=unique([s['student_check']['practice_id'] for s in core['slides']],'practice')
    examples=unique([s['worked_example_id'] for s in core['slides'] if s['worked_example_id']],'example')
    require(set('ABCDEF')<=examples,'Required worked examples A–F')
    for s in core['slides']:
        require(set(s['competency_ids'])<=cs,'Unknown slide competency')
        require(s['data_notice']==ILLUSTRATIVE,'Illustrative slide data notice')
    for sec in core['sections']:
        require(set(sec['slide_ids'])<=set(slides),'Unknown section slide')
        require(set(sec['canonical_competencies'])<=cs,'Unknown section competency')
        require(set(sec['student_checks'])<=checks,'Unknown check')
        require(set(sec['worked_examples'])<=examples,'Unknown worked example')
        actual={c for n in sec['slide_ids'] for c in slides[n]['competency_ids']}
        require(set(sec['canonical_competencies'])==actual,'Section/slide competency mismatch')
    unique([q['question_id'] for q in core['questions']],'question')
    parts=[p for q in core['questions'] for p in q['parts']]
    unique([p['part_id'] for p in parts],'part')
    require(sum(p['marks'] for p in parts)==core['total_marks'],'Part marks do not reconcile')
    for q in core['questions']:
        require(q['notice']==NOTICE and q['data_notice']==ILLUSTRATIVE,'Question provenance labels')
        for p in q['parts']:
            require(p['part_id'].startswith(q['question_id']+'('),'Part parent mismatch')
            links=[p['primary_competency'],*p['supporting_competencies']]
            unique(links,'part competency link');require(set(links)<=cs,'Unknown assessment competency')
            require(len(p['marking_points'])==p['marks'],'Mark allocation count')
            require(all(re.match(r'^[MAB]1 ',m) for m in p['marking_points']),'Invalid mark point')
    derived=derive(core)
    cov=derived['assessment_coverage_report']
    require(sum(cov['marks_by_competency'].values())==core['total_marks'],'Coverage double counting')
    for topic,(lo,hi) in TARGETS.items():
        pct=cov['topic_percentages'].get(topic,0);require(lo<=pct<=hi,'Topic weighting outside demo target')
    for a in derived['teaching_assessment_alignment']['alignment']:
        if a['assessment_parts']:
            require(a['teaching_slides'] and a['practice_ids'],'Assessed competency lacks teaching/practice')
    return core

def validate_outputs(directory=OUT,check_stable=True):
    directory=Path(directory)
    core=validate_core(json.loads((directory/'pack.json').read_text(encoding='utf-8')))
    expected=derive(core)
    for name,value in expected.items():
        actual=json.loads((directory/(name+'.json')).read_text(encoding='utf-8'))
        require(actual==value,f'{name} is missing, stale or inconsistent with pack.json')
    vm=json.loads((directory/'teachingAssessmentDemo.json').read_text(encoding='utf-8'))
    for key,val in expected.items():require(vm[key]==val,f'View model {key} mismatch')
    stable_count=0
    if check_stable:
        baseline=json.loads((directory/'stable_baseline_sha256.json').read_text(encoding='utf-8'))
        for name,digest in baseline.items():
            require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,f'Stable file changed: {name}')
        stable_count=len(baseline)
    return dict(status='PASSED',slides=len(core['slides']),marks=core['total_marks'],questions=len(core['questions']),
                parts=sum(len(q['parts']) for q in core['questions']),stable_files_unchanged=stable_count,
                content_review='Academic human review pending; validation is structural, not endorsement.')

if __name__=='__main__':
    print(json.dumps(validate_outputs(),indent=2))
