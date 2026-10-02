"""Located Q3 source structure only: no canonical mappings or acceptance oracle."""
from pathlib import Path
from pypdf import PdfReader
from .models import normalise
from .sources import register_candidate, extract_candidate

SOURCE_DIR=Path(__file__).resolve().parents[1]/'output/p1c_case2/sources'
QUESTION='Q3-2023'
PARTS=('a','b-i','b-ii','c-i','c-ii')


def between(text,start,end,offset=0):
    a=text.index(start,offset);b=text.index(end,a+len(start))
    return a,b


def build_source_plan(graph,source_dir=SOURCE_DIR):
    source_dir=Path(source_dir);items=[];locs={}
    def add(kind,payload,refs=()):
        r=dict(kind=kind,payload=payload,judgment_refs=list(refs));items.append(r);return r
    def prov(*ids):return dict(origin='real',creation_method='rule',source_references=['locator:'+x for x in ids])
    for sid,filename,kind,page,cover_terms,version in [
        ('QP-2023','June 2023 QP (Stats) (1).pdf','official_past_paper',8,('20 June 2023','9MA0/31','P72819A'),'20 June 2023; P72819A'),
        ('MS-2023','June 2023 MS (Stats).pdf','official_mark_scheme',9,('Summer 2023','9MA0','Paper 31 Statistics'),'Summer 2023; Paper 31 Statistics')]:
        path=source_dir/filename;cover=PdfReader(path).pages[0].extract_text()
        if not all(t in cover for t in cover_terms):raise ValueError('Source cover identity differs: '+sid)
        raw=register_candidate(sid,path,'Pearson Edexcel 9MA0/31 Statistics '+sid,kind,
            'Pearson Edexcel UK A Level Mathematics 9MA0',version,
            'Cover text: '+', '.join(cover_terms)+'. Local supplied PDF carries PMT branding; authenticity/edition awaits operator verification.')
        items.append(raw);_,v,r=normalise(raw)
        for part in (('whole','b','c')+PARTS if sid=='QP-2023' else PARTS):
            lid=sid+'-Q3-'+part
            loc=extract_candidate(r,v,lid,page,'Q3 '+part,
                'Exact source page and bounded parsed spans for Q3 '+part+'; interpretation is a separate pending proposal.',
                region=[0.08,0.06,0.84,0.84],assessment_part_id=None if part=='whole' else QUESTION+'-'+part,assessment_question_id=QUESTION)
            items.append(loc);locs[lid]=normalise(loc)
    qp=locs['QP-2023-Q3-whole'][2]['payload']['extracted_text']
    ms=locs['MS-2023-Q3-a'][2]['payload']['extracted_text']
    stem=between(qp,'3. Ben',' (a)')
    qa=between(qp,' (a)','(2)')
    qb=between(qp,' (b)','  (i)')
    qbi=between(qp,'  (i)','  (ii)',qb[0]);qbii=between(qp,'  (ii)','(3)',qb[0])
    qc=between(qp,' (c)','  (i)',qbii[1]);qci=between(qp,'  (i)','  (ii)',qc[0]);qcii=between(qp,'  (ii)','(2)',qc[0])
    prompts=dict(zip(PARTS,[qa,qbi,qbii,qci,qcii]));directives={'b-i':qb,'b-ii':qb,'c-i':qc,'c-ii':qc}
    ma=between(ms,'(a)','(b)(i)');mbi=between(ms,'(b)(i)','(ii)');mbii=between(ms,'(ii)','(c)(i)',mbi[0]);mci=between(ms,'(c)(i)','(ii)',mbii[1]);mcii=between(ms,'(ii)','( 7 marks)',mci[0])
    scores=dict(zip(PARTS,[ma,mbi,mbii,mci,mcii]))
    notes_start=ms.index(' Notes ')
    na=between(ms,'(a) M1','(b)(i) B1',notes_start)
    nbi=between(ms,'(b)(i) B1','(ii) M1',na[1]-1)
    nbii=between(ms,'(ii) M1',' Part (c)',nbi[1]-1)
    nci=between(ms,'(c)(i) B1','(ii)  B1',nbii[1]);ncii=(ms.index('(ii)  B1',nci[1]-1),ms.rindex('PMT'))
    notes=dict(zip(PARTS,[na,nbi,nbii,nci,ncii]))
    # Locator summaries quote bounded source text, not an academic interpretation.
    regions={'a':[0.12,0.255,0.76,0.065], 'b-i':[0.15,0.365,0.70,0.04],
             'b-ii':[0.15,0.398,0.74,0.037], 'c-i':[0.15,0.504,0.76,0.034],
             'c-ii':[0.15,0.529,0.76,0.055]}
    for raw in items:
        if raw['kind']!='locator':continue
        payload=raw['payload'];part=payload['locator_id'].split('-Q3-',1)[1]
        if part in PARTS:
            a,b=prompts[part] if payload['source_id']=='QP-2023' else scores[part]
            payload['text_summary']=' '.join(payload['extracted_text'][a:b].split())
            if payload['source_id']=='QP-2023':payload['visual_region']=regions[part]
        locs[payload['locator_id']]=normalise(raw)
    add('question',dict(question_id=QUESTION,paper_source_id='QP-2023',label='June 2023 9MA0/31 Q3',
        source_locator_id='QP-2023-Q3-whole',curriculum_context_id='CTX-9MA0',provenance=prov('QP-2023-Q3-whole')))
    for container in ('b','c'):
        add('question_part',dict(part_id=QUESTION+'-'+container,question_id=QUESTION,label='Q3('+container+')',node_kind='container',
            source_locator_id='QP-2023-Q3-'+container,provenance=prov('QP-2023-Q3-'+container)))
    add('condition',dict(condition_id='COND-Q3-2023-GIVEN',question_id=QUESTION,kind='context_detail',
        description=qp[stem[0]:qcii[1]]+'\nQP group marks: a=2, b=3, c=2. No glyph repair; original page review required.',
        availability='given_in_question',provenance=prov('QP-2023-Q3-whole')))
    add('scope',dict(scope_id='SCOPE-Q3-2023-LDS',context_id='CTX-9MA0',
        description='Dataset knowledge asserted by the mark scheme, not a universal rainfall fact:\n'+ms[mci[0]:mcii[1]]+'\n'+ms[nci[0]:ncii[1]],
        locator_ids=['MS-2023-Q3-c-i','MS-2023-Q3-c-ii'],association_status='candidate'))
    for part,marks in zip(PARTS,[2,1,2,1,1]):
        pid=QUESTION+'-'+part;qlid='QP-2023-Q3-'+part;mlid='MS-2023-Q3-'+part
        refs=['condition:COND-Q3-2023-GIVEN']
        if part.startswith('c'):refs+=['scope:SCOPE-Q3-2023-LDS','question_part:'+QUESTION+'-b-i']
        if part=='b-ii':refs+=['question_part:'+QUESTION+'-b-i']
        add('question_part',dict(part_id=pid,question_id=QUESTION,label='Q3('+part.replace('-',')(')+')',node_kind='assessable',
            source_locator_id=qlid,parent_part_id=None if part=='a' else QUESTION+'-'+part[0],provenance=prov(qlid)),refs)
        def span(role,lid,bounds):
            _,v,loc=locs[lid];a,b=bounds
            return dict(role=role,locator_id=lid,locator_version=v,start=a,end=b,text=loc['payload']['extracted_text'][a:b])
        spans=[span('shared_stem','QP-2023-Q3-whole',stem),span('prompt',qlid,prompts[part]),
               span('mark_scheme',mlid,scores[part]),span('mark_scheme_notes',mlid,notes[part])]
        if part in directives:spans.append(span('comparison_context',qlid,directives[part]))
        add('parsed_part',dict(parsed_id='PARSED-'+pid,part_id=pid,parser_version='located-q3-structure/1',marks=marks,spans=spans,
            warnings=['Formula/symbol extraction is layout-defective; no silent repair. Review original PDF page.',
                      'Individual subpart marks follow MS scoring rows; QP prints grouped totals.',
                      'Large Data Set statements are question-specific evidence, not canonical definitions.']))
    # Parsing is append-only and refuses to overwrite an existing differing object.
    for raw in items:
        k,v,_=normalise(raw)
        if k in graph and graph[k]['version']!=v:raise ValueError('Source/parse object exists with a different version; explicit revision required: '+k)
    return dict(items=items,expected_heads={normalise(x)[0]:graph.get(normalise(x)[0],{}).get('version') for x in items})
