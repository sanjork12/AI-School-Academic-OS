"""Offline deterministic content builder. Writes only the new demo directory."""
import json
from collections import Counter
from teaching_assessment_content import (OUT,NOTICE,SCHEME_NOTICE,GUIDE,REPORT,PAGE,COMPETENCIES,cid,questions,slides)
from teaching_assessment_schema import CorePack

TARGETS = {'data_types':[10,15],'location':[20,25],'spread':[20,25],'comparison':[20,25],'lds':[15,20]}
ATTRIBUTION = 'Each part awards all its marks to one primary competency and its topic. Supporting links receive zero exclusive marks. Inclusive linked marks show exposure only and must not be summed.'

def build_core():
    ss=slides()
    sections=[]
    for title,start,end,mistake in [
        ('Purpose and objectives',1,3,'Claiming a sample proves a population conclusion'),
        ('Data types',4,5,'Confusing recorded precision with the underlying variable'),
        ('Measures of location',6,8,'Treating grouped estimates as exact'),
        ('Measures of spread',9,11,'Confusing variance units and SD units'),
        ('Comparison and outliers',12,14,'Deleting genuine extreme values'),
        ('Large Data Set',15,17,'Treating missing values as zero'),
        ('Applied worked examples',18,21,'Generalising short weather samples to climate'),
        ('Review and exam strategy',22,24,'Giving a number without interpretation'),
    ]:
        chosen=ss[start-1:end]; ids=sorted({c for s in chosen for c in s['competency_ids']})
        sections.append(dict(lesson_section=title,slide_ids=list(range(start,end+1)),
            learning_objectives=[name for key,name,group in COMPETENCIES if cid(key) in ids],
            canonical_competencies=ids,key_concepts=[s['title'] for s in chosen],
            worked_examples=[s['worked_example_id'] for s in chosen if s['worked_example_id']],
            student_checks=[s['student_check']['practice_id'] for s in chosen],
            common_mistakes=[mistake],exam_focus='Show a valid method, use units and qualify the contextual conclusion.'))
    return CorePack.model_validate(dict(schema_version='teaching_demo_0.1',context=dict(
        context_id='CTX-EDX-9MA0-2017-STAT',exam_board='Pearson Edexcel',qualification='A Level Mathematics',
        qualification_code='9MA0',curriculum_version='2017 qualification',educational_stage='UK Level 3 / A Level',
        component='Statistics / Applied Mathematics',unit='Statistics: Exploring and Summarising Data',material_notice=NOTICE,
        facts=[dict(kind='official_source_derived_fact',claim='Pearson offers AS and A level Mathematics (2017).',source_id='PEARSON-QUAL'),
               dict(kind='official_source_derived_fact',claim='The LDS contains Met Office weather for eight stations, May–October 1987 and 2015.',source_id='PEARSON-GUIDE',page=9),
               dict(kind='official_source_derived_fact',claim='Trace rainfall and limited month coverage require careful interpretation.',source_id='PEARSON-REPORT-2023',locator='Question 3'),
               dict(kind='teacher_demo_content',claim='This topic subset, lesson sequence, competencies and assessment weights are teacher selections.')],
        sources=[dict(source_id='PEARSON-QUAL',url=PAGE,title='Pearson Mathematics 2017 qualification page',accessed='2026-09-18'),
                 dict(source_id='PEARSON-GUIDE',url=GUIDE,title='GCE Maths and Further Maths Qualification and Assessment Guide',accessed='2026-09-18'),
                 dict(source_id='PEARSON-REPORT-2023',url=REPORT,title='9MA0/31 June 2023 examiner report',accessed='2026-09-18')],
        source_limitations='No local official 9MA0 specification or LDS workbook was available. Official guidance and report were consulted online. Exact specification objective mappings remain unverified and pending teacher review; no official objective text or exam question is copied.',
        numerical_data_origin='synthetic_illustrative'),
        competencies=[dict(competency_id=cid(k),skill_name=n,topic_group=g,classification='teaching_only_grouping' if k=='PURPOSE' else 'candidate_canonical',review_status='pending',provenance='teacher_generated') for k,n,g in COMPETENCIES],
        scopes=[dict(competency_id=cid(k),context_id='CTX-EDX-9MA0-2017-STAT',expectations={
            'data_types':'Interpret measurement, grouping and units in statistical contexts.',
            'location':'Use raw/frequency data, grouped estimates and stated quantile conventions, with interpretation.',
            'spread':'Use divisor n for descriptive variance/SD, summary statistics and appropriate units.',
            'comparison':'Combine numerical location and spread with justified conclusions and data-quality judgements.',
            'lds':'Use weather variables, explicit cleaning policies and limitations of station/date coverage.'}[g],status='teacher_selected_scope_pending_review') for k,n,g in COMPETENCIES],
        slides=ss,sections=sections,questions=questions(),total_marks=48,duration_minutes=55,material_notice=NOTICE,
        mark_scheme_notice=SCHEME_NOTICE,human_review_status='pending')).model_dump()

def derive(core):
    cs={c['competency_id']:c for c in core['competencies']}
    parts=[p for q in core['questions'] for p in q['parts']]
    primary=Counter(); topics=Counter(); demand=Counter(); inclusive=Counter()
    mappings=[]; scheme=[]; blueprint=[]
    for q in core['questions']:
        blueprint.append(dict(question_id=q['question_id'],marks=sum(p['marks'] for p in q['parts']),
            target_competencies=sorted({c for p in q['parts'] for c in [p['primary_competency'],*p['supporting_competencies']]}),
            question_purpose=q['question_purpose'],question_format=q['question_format'],estimated_demand=max(p['predicted_difficulty'] for p in q['parts']),
            context=q['context'],expected_reasoning={p['part_id']:p['reasoning_steps'] for p in q['parts']}))
    for p in parts:
        primary[p['primary_competency']]+=p['marks'];topics[cs[p['primary_competency']]['topic_group']]+=p['marks'];demand[str(p['predicted_difficulty'])]+=p['marks']
        for c in [p['primary_competency'],*p['supporting_competencies']]:inclusive[c]+=p['marks']
        mappings.append({k:p[k] for k in ['part_id','primary_competency','supporting_competencies','marks','predicted_difficulty','difficulty_basis','reasoning_steps']})
        scheme.append({k:p[k] for k in ['part_id','marks','answer','marking_points','acceptable_alternatives','interpretation_requirements']})
    alignment=[]
    for c in cs:
        taught=[s for s in core['slides'] if c in s['competency_ids']]
        linked=[p for p in parts if c in [p['primary_competency'],*p['supporting_competencies']]]
        alignment.append(dict(competency_id=c,teaching_slides=[s['slide_id'] for s in taught],
             worked_examples=[s['worked_example_id'] for s in taught if s['worked_example_id']],
             practice_ids=[s['student_check']['practice_id'] for s in taught],assessment_parts=[p['part_id'] for p in linked],
             exclusive_marks=primary[c],inclusive_linked_marks=inclusive[c]))
    assessed=sorted(inclusive); taught=sorted({c for s in core['slides'] for c in s['competency_ids']})
    coverage=dict(total_marks=sum(p['marks'] for p in parts),question_count=len(blueprint),question_part_count=len(parts),
        attribution_policy=ATTRIBUTION,marks_by_competency={c:primary[c] for c in cs},inclusive_linked_marks_by_competency={c:inclusive[c] for c in cs},
        marks_by_topic_group=dict(topics),topic_percentages={k:round(v/48*100,2) for k,v in topics.items()},
        difficulty_distribution_marks=dict(sorted(demand.items())),difficulty_distribution_parts=dict(sorted(Counter(str(p['predicted_difficulty']) for p in parts).items())),
        competencies_taught=taught,competencies_assessed=assessed,unassessed_competencies=sorted(set(taught)-set(assessed)),
        competency_coverage_percent=round(len(assessed)/len(taught)*100,2))
    return {
        'curriculum_context':core['context'],
        'competency_model':dict(competencies=core['competencies'],curriculum_scopes=core['scopes'],promotion_policy='No writes to approved graph; all candidate review pending.'),
        'teaching_blueprint':dict(unit=core['context']['unit'],sections=core['sections'],slides=core['slides'],lesson_timing='Two 55-minute lessons, then a separate 55-minute assessment.'),
        'assessment_blueprint':dict(total_marks=48,duration_minutes=55,topic_target_percentages=TARGETS,weighting_notice='Teacher/demo targets, not official Pearson assessment weightings.',questions=blueprint),
        'assessment_questions':dict(material_notice=NOTICE,data_notice=core['questions'][0]['data_notice'],questions=core['questions']),
        'mark_scheme':dict(notice=SCHEME_NOTICE,policy='M = method; A = accuracy; B = independent statement. Each listed point is 1 mark. A normally depends on its preceding M. B is independent. No double credit. Follow-through only when stated. Equivalent correct methods earn full credit.',entries=scheme),
        'question_competency_mapping':dict(mapping_unit='question_part',attribution_policy=ATTRIBUTION,mappings=mappings),
        'assessment_coverage_report':coverage,
        'teaching_assessment_alignment':dict(attribution_policy=ATTRIBUTION,alignment=alignment),
    }

def main():
    core=build_core(); OUT.mkdir(exist_ok=True)
    derived=derive(core)
    # The assessment blueprint is persisted before question/source artifacts.
    order=['assessment_blueprint']+[k for k in derived if k!='assessment_blueprint']
    for name in order:
        (OUT/(name+'.json')).write_text(json.dumps(derived[name],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'pack.json').write_text(json.dumps(core,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    vm=dict(demo_mode='Static simulation; no backend or AI call',**derived,
            artifacts=dict(ppt='Edexcel_9MA0_Statistics_Exploring_Data.pptx',slides=len(core['slides']),worked_examples=len([s for s in core['slides'] if s['worked_example_id']]),student_checks=len(core['slides']),student_pdf='Edexcel_9MA0_Statistics_Assessment.pdf',mark_scheme_pdf='Edexcel_9MA0_Statistics_Mark_Scheme.pdf'))
    (OUT/'teachingAssessmentDemo.json').write_text(json.dumps(vm,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(derived['assessment_coverage_report'],indent=2))

if __name__=='__main__':main()
