"""Resolve manifest refs into deterministic editable drawing instructions.

Transient layout, not an authored-content store. All substantive elements carry
source refs/field paths. Arithmetic is limited to geometry, never answer creation.
"""
import re
from .presentation_manifest import gate,validate_manifest

DESIGN=dict(width=1280,height=720,margin=72,font='Arial',math_font='Cambria Math',
    background='#FFFFFF',ink='#172B4D',muted='#526079',accent='#5865A8',secondary='#AE5E3C',line='#CBD2DE')
GOALS={'conceptual_understanding':'Understand what standard deviation represents.',
    'capability':'Calculate standard deviation.',
    'capability_under_task_form':'Calculate standard deviation from supplied summary statistics.'}
SYMBOLS={'n':'n','sum_x':'Σx','sum_x2':'Σx²','sum_squared_deviations':'Σ(x − x̄)²'}


def equation(expression,bindings=None):
    """Notation-only rendering of the supplied closed AST; no formula inference."""
    op=expression.get('op')
    if op=='variable' and set(expression)=={'op','name'} and expression['name'] in SYMBOLS:
        return str(bindings[expression['name']]) if bindings is not None else SYMBOLS[expression['name']]
    if set(expression)!={'op','args'}:raise ValueError('Unsupported formula representation')
    args=expression['args']
    if op=='sqrt' and len(args)==1:return '√('+equation(args[0],bindings)+')'
    if op=='square' and len(args)==1:return '('+equation(args[0],bindings)+')²'
    if op=='divide' and len(args)==2:return '('+equation(args[0],bindings)+' / '+equation(args[1],bindings)+')'
    if op=='subtract' and len(args)==2:return equation(args[0],bindings)+' − '+equation(args[1],bindings)
    raise ValueError('Unsupported formula operator; no replacement inferred')


def layout_plan(manifest,authored,validation,learning):
    errors=validate_manifest(manifest,authored,validation,learning)
    if errors:raise ValueError('; '.join(errors))
    a,v,l=gate(authored,validation,learning)
    if manifest.identity['profile']=='standard-deviation-classroom/2':
        from .presentation_design import classroom_plan
        return classroom_plan(manifest,a,l)
    objects={o.ref:o for o in (*a.content_blocks,*a.instructional_formulas,*a.worked_examples,*a.practice_items,*a.learning_checks,*a.solutions)}
    lr={r.ref:r for r in l.learning_requirements};output=[]
    for s in manifest.slides:
        elements=[]
        def element(kind,x,y,w,h,text='',source=None,field='',size=30,color=None,bold=False,font=None):
            e=dict(name=f'{s.ref}-element-{len(elements)+1:03}',kind=kind,x=round(x,4),y=round(y,4),w=round(w,4),h=round(h,4),
                text=text,source_ref=source,source_field=field,font=font or DESIGN['font'],size=size,color=color or DESIGN['ink'],bold=bold)
            elements.append(e);return e
        def text(x,y,w,h,value,source=None,field='',**style):return element('text',x,y,w,h,value,source,field,**style)
        def math(x,y,w,h,value,source,field,size=40):return text(x,y,w,h,value,source,field,size=size,font=DESIGN['math_font'])
        text(72,54,1136,90,s.title,size=56 if s.slide_number==1 else 44,bold=True)
        context=f'{a.identity.awarding_body.replace("Pearson ","")} {a.identity.qualification} — {a.identity.curriculum_section}'
        text(72,670,1050,25,context,size=16,color=DESIGN['muted'])
        text(1170,670,60,25,str(s.slide_number),size=16,color=DESIGN['muted'])
        if s.slide_type in ('title_learning_goals','learning_summary'):
            text(72,190,1000,35,'Learning goals' if s.slide_number==1 else 'Learning summary',size=23,color=DESIGN['accent'],bold=True)
            ordered=sorted((lr[r] for r in s.learning_requirement_refs),key=lambda r:list(GOALS).index(r.type))
            for i,r in enumerate(ordered):text(72,267+i*98,1100,82,GOALS[r.type],r.ref,'statement:student_goal_transform/1',size=34)
            if s.slide_number==11:text(72,605,1110,48,'Original teaching material aligned to reviewed curriculum and assessment evidence.',size=18,color=DESIGN['muted'])
        else:
            b=next(objects[r] for r in s.content_refs if hasattr(objects[r],'kind') and hasattr(objects[r],'text'))
            if s.slide_type=='concept':
                sentences=re.split(r'(?<=\.)\s+',b.text)
                for i,sentence in enumerate(sentences):text(72,215+i*175,1110,150,sentence,b.ref,f'text/sentence/{i}',size=40 if i==0 else 34)
            elif s.slide_type=='visual_comparison':
                visual=b.visual;all_values=[float(v) for row in visual.datasets.values() for v in row];low=min(all_values);high=max(all_values)
                if high<=low:raise ValueError('Cannot lay out a zero-width comparison scale')
                left=260;width=865
                xpos=lambda value:left+(float(value)-low)/(high-low)*width
                for i,label in enumerate(('A','B')):
                    y=292+i*205;color=DESIGN['accent'] if i==0 else DESIGN['secondary']
                    text(72,y-26,170,55,'Dataset '+label,b.ref,f'visual/datasets/{label}:label',size=26,bold=True,color=color)
                    element('rect',left,y,width,2,source=b.ref,field='visual:shared_scale',color=DESIGN['line'])
                    for j,value in enumerate(visual.datasets[label]):
                        x=xpos(value);element('ellipse',x-8,y-8,16,16,source=b.ref,field=f'visual/datasets/{label}/{j}',color=color)
                        text(x-25,y+21,60,40,value,b.ref,f'visual/datasets/{label}/{j}',size=25,color=color)
                mean=visual.claims['A']['mean'];mx=xpos(mean)
                for y in (226,431):element('rect',mx-1,y,2,54,source=b.ref,field='visual/claims/A/mean',color=DESIGN['muted'])
                text(mx-105,170,240,42,'Mean = '+mean,b.ref,'visual/claims/A/mean',size=28,bold=True)
                text(72,598,1110,45,b.text,b.ref,'text',size=26)
            elif s.slide_type=='calculation_method':
                steps=[x.strip() for x in re.split(r'(?<=\.)\s+',b.text) if x.strip()]
                if len(steps)!=5:raise ValueError('Unsupported method layout; expected five authored sentences')
                for i,step in enumerate(steps):text(72,178+i*64,1120,56,step,b.ref,f'text/sentence/{i}',size=29)
                f=objects[b.formula_refs[0]]
                math(72,543,1120,82,'σ = '+equation(f.expression),f.ref,'expression',size=42)
            elif s.slide_type=='task_form_method':
                f=objects[b.formula_refs[0]]
                math(72,176,1120,85,'σ = '+equation(f.expression),f.ref,'expression',size=42)
                for i,key in enumerate(('n','sum_x','sum_x2')):
                    math(72,300+i*62,135,50,SYMBOLS[key],b.ref,'instructional_inputs/'+key,size=32)
                    text(230,300+i*62,930,50,b.instructional_inputs[key],b.ref,'instructional_inputs/'+key,size=28)
                text(72,517,1110,119,b.text,b.ref,'text',size=25)
            else:
                q=objects[b.item_ref]
                if q.summary:
                    # Exact original question remains visible; numeric panels repeat
                    # supplied values for visual hierarchy, without changing them.
                    text(72,171,1110,138,q.question,q.ref,'question',size=29)
                    if s.slide_type=='worked_example':
                        solution=next(objects[r] for r in s.content_refs if hasattr(objects[r],'method_steps'))
                        formula=next(objects[r] for r in s.content_refs if hasattr(objects[r],'expression'))
                        math(72,325,1120,54,'σ = '+equation(formula.expression,q.summary.model_dump()),formula.ref,'expression:substitution:'+q.ref,size=33)
                        for i,step in enumerate(solution.method_steps):
                            shown=re.sub(r'sqrt\(([^()]*)\)',r'√(\1)',step).replace('^2','²').replace('population SD','σ')
                            math(72,387+i*62,1120,54,shown,solution.ref,f'method_steps/{i}',size=31)
                    else:
                        for i,(symbol,value,field) in enumerate((('n',str(q.summary.n),'n'),('Σx',q.summary.sum_x,'sum_x'),('Σx²',q.summary.sum_x2,'sum_x2'))):
                            math(72+i*380,349,355,78,symbol+' = '+value,q.ref,'summary/'+field,size=42)
                        # Unlabelled working space is layout only, not new prose.
                else:text(72,242,1110,225,q.question,q.ref,'question',size=42)
        for e in elements:
            if e['x']<0 or e['y']<0 or e['x']+e['w']>1280 or e['y']+e['h']>720:raise ValueError('Element outside slide: '+e['name'])
        output.append(dict(ref=s.ref,number=s.slide_number,elements=elements))
    return dict(design=DESIGN,slides=output,manifest_binding=manifest.source_validation)
