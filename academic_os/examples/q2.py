"""Manually located real 9MA0 Q2 input; no fabricated signatures or approvals."""
from pathlib import Path
from academic_os.sources import register_candidate,extract_candidate
from academic_os.models import normalise

DEFAULT_SOURCES=Path(__file__).resolve().parents[2]/'output/academic_knowledge_v03/source_audit_20260919/sources'
ROOTS=['part_mapping:MAP-Q2-a-MEAN-CALC','part_mapping:MAP-Q2-b-SD-CALC',
       'part_mapping:MAP-Q2-c-VARIATION-INTERPRET','part_mapping:MAP-Q2-c-CONTEXT-INFER']

def build_candidates(source_dir=DEFAULT_SOURCES):
    source_dir=Path(source_dir);items=[];sources={}
    for sid,name,title,kind,version,basis in [
        ('SPEC','9MA0-Specification-Issue4.pdf','Pearson Edexcel Level 3 Advanced GCE in Mathematics (9MA0)','official_syllabus','Issue 4, February 2020; first teaching September 2017','Cover identifies 9MA0 and Issue 4; printed page 31 identifies February 2020.'),
        ('QP','9MA0-2025-31-QP.pdf','Pearson Edexcel 9MA0/31 Statistics question paper','official_past_paper','19 June 2025, P75695A','Cover identifies 9MA0/31, Thursday 19 June 2025 and P75695A. Identity is a candidate assertion until local operator verification.'),
        ('MS','9MA0-2025-31-MS.pdf','Pearson Edexcel Mathematics 9MA0 Paper 31 Statistics mark scheme','official_mark_scheme','Summer 2025','Cover identifies Summer 2025, Mathematics (9MA0), Paper 31 Statistics. Operator must check authenticity/edition.'),
    ]:
        raw=register_candidate(sid,source_dir/name,title,kind,'Pearson Edexcel UK A Level Mathematics 9MA0',version,basis)
        _,v,r=normalise(raw);sources[sid]=(r,v);items.append(raw)
    def loc(sid,lid,page,label,summary,part=None,question=None,region=None):
        r,v=sources[sid]
        items.append(extract_candidate(r,v,lid,page,label,summary,region,part,question))
    loc('SPEC','SPEC-2.3',35,'Statistics section 2.3, printed page 31',
        'Location and variation, including standard deviation from summary statistics. Candidate scope association; no invented official objective ID.',region=[0.3,0.49,0.62,0.43])
    loc('QP','QP-Q2',4,'Question 2','Athletics coaches, 400 m best times; summary statistics and comparison.',question='Q2',region=[0.05,0.06,0.89,0.4])
    for label,summary in [('a','Calculate mean; 1 mark.'),('b','Calculate standard deviation; 2 marks.'),('c','Infer which coach is more likely to have trained the winner; 2 marks.')]:
        loc('QP','QP-Q2-'+label,4,'Q2('+label+')',summary,part='Q2-'+label,question='Q2',region=[0.07,0.12,0.85,0.31])
        loc('MS','MS-Q2-'+label,7,'Q2('+label+') scoring and notes',
            {'a':'Mean 55.1 seconds, B1.','b':'SD 2.2 seconds; method and accuracy. Scheme also accepts sample SD about 2.21.',
             'c':'Coach B, using greater SD and the likelihood of more extreme faster times. Conditional follow-through notes refer to answer (b). This contextual inference is not a universal implication of SD alone.'}[label],
             part='Q2-'+label,question='Q2',region=[0.05,0.02,0.91,0.82])
    def prov(*locators):return dict(origin='real',creation_method='rule',source_references=['locator:'+s for s in locators])
    def add(kind,payload,refs=()):items.append(dict(kind=kind,payload=payload,judgment_refs=list(refs)))
    add('context',dict(context_id='CTX-9MA0',exam_board='Pearson Edexcel',qualification='A Level Mathematics',subject='Mathematics',
        specification_code='9MA0',curriculum_version='2017 qualification; specification Issue 4 February 2020',educational_stage='UK Level 3 / A Level',provenance=prov('SPEC-2.3')))
    add('scope',dict(scope_id='SCOPE-STAT-2.3',context_id='CTX-9MA0',description='Candidate link to the actual section 2.3 on descriptive statistics, not an equivalence claim about every part of Q2.',
        locator_ids=['SPEC-2.3'],official_section_label='2.3 (Statistics)',association_status='candidate'))
    add('question',dict(question_id='Q2',paper_source_id='QP',label='June 2025 9MA0/31 Q2',source_locator_id='QP-Q2',curriculum_context_id='CTX-9MA0',provenance=prov('QP-Q2')))
    for name,kind,description in [
        ('SUMMARY','input_form','Coach A: n=120, sum x=6612, sum x squared=364902; x is best 400 m time in seconds. Formula glyphs in extracted PDF text are imperfect; check the original page.'),
        ('COMPARE','context_detail','Coach B: n=100, mean 55.1 seconds and SD 3.6 seconds. Equal numbers of the fastest runners from each coach compete. Mark scheme (c) uses result (b); larger SD alone is not a mathematical guarantee about extremes.')]:
        add('condition',dict(condition_id='COND-'+name,question_id='Q2',kind=kind,description=description,availability='given_in_question',provenance=prov('QP-Q2')))
    for label in 'abc':
        refs=['condition:COND-SUMMARY'] if label in 'ab' else ['condition:COND-COMPARE','condition:COND-SUMMARY','question_part:Q2-b']
        add('question_part',dict(part_id='Q2-'+label,question_id='Q2',label='Q2('+label+')',node_kind='assessable',source_locator_id='QP-Q2-'+label,provenance=prov('QP-Q2-'+label)),refs)
    for label,suffix,title,description,extent in [
        ('a','MEAN-CALC','Calculate the mean','Calculate the arithmetic mean using the total and number of observations.','partial'),
        ('b','SD-CALC','Calculate standard deviation','Calculate standard deviation from observations or summary statistics, using the stated convention.','partial'),
        ('c','VARIATION-INTERPRET','Interpret variation','Interpret a measure of variation in context without turning it into a guarantee about individual extremes.','partial'),
        ('c','CONTEXT-INFER','Make contextual statistical inferences','Use statistical summaries with task conditions to draw a qualified contextual conclusion.','partial'),
    ]:
        comp='CAN-STAT-'+suffix;mid='MAP-Q2-'+label+'-'+suffix
        add('competency',dict(canonical_id=comp,subject_domain='Statistics',skill_name=title,description=description,provenance=prov('SPEC-2.3','MS-Q2-'+label)))
        evid=[]
        for source in ['QP','MS']:
            eid='EV-'+source+'-'+mid;evid.append(eid)
            add('evidence',dict(evidence_id=eid,source_locator_ids=[source+'-Q2-'+label],target=dict(kind='part_mapping',id=mid),
                observation=('Candidate reading of '+source+' Q2('+label+'): '+description),content_kind='interpretation',
                evidence_role='supports',observation_status='observed',context_id='CTX-9MA0',provenance=prov(source+'-Q2-'+label)))
        refs=['scope:SCOPE-STAT-2.3'] if suffix!='CONTEXT-INFER' else []
        add('part_mapping',dict(mapping_id=mid,part_id='Q2-'+label,canonical_id=comp,role='assessed',assessment_extent=extent,
            rationale='Candidate mapping checked against question and mark scheme pages; academic approval pending. '+
                ('Exact syllabus association for contextual inference remains unresolved and is not asserted by this assessment mapping.' if suffix=='CONTEXT-INFER' else 'Section association is a separate candidate scope.'),
            evidence_ids=evid,mapping_method='rule',provenance=prov('QP-Q2-'+label,'MS-Q2-'+label)),refs)
    return items
