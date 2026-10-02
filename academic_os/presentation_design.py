"""Reusable classroom design components. No academic authoring or arithmetic.

All substantive strings resolve from frozen upstream objects. Labels are a
closed allowlist; geometry arithmetic is permitted only for visual placement.
"""
import re
from .presentation_layout import GOALS,SYMBOLS,equation

DESIGN=dict(width=1280,height=720,margin=64,font='Arial',math_font='Cambria Math',
    background='#FFFFFF',ink='#172E4C',muted='#53677E',accent='#315D8A',
    secondary='#637C96',line='#D7E1EC',tint='#EFF4F9',pale='#F7F9FC')
TYPE={'lesson_title':66,'slide_title':44,'section_label':20,'body':30,
      'mathematical_expression':42,'large_answer':72,'question':29,'small_footer':16}
LABELS=frozenset(('Standard Deviation','What is standard deviation?','Same mean, different spread',
    'How standard deviation works','From summary statistics','Worked example','Practice 1','Practice 2',
    'Concept check','Calculation check','Summary','LEARNING GOALS','CORE IDEA','METHOD',
    'WHAT YOU ARE GIVEN','SUBSTITUTE INTO','CALCULATE σ','IDENTIFY','SUBSTITUTE','SIMPLIFY','ANSWER',
    'TRY IT','WORKING SPACE','CHECK YOUR LEARNING','RESPONSE','CAN YOU NOW...','↓','1','2','3','4','5'))


def scale_position(value,minimum,maximum,left,width):
    value,minimum,maximum=map(float,(value,minimum,maximum))
    if maximum<=minimum or not minimum<=value<=maximum:raise ValueError('Invalid shared dot-plot scale')
    return left+(value-minimum)/(maximum-minimum)*width


class Components:
    def __init__(self,slide,identity):
        self.slide=slide;self.elements=[];self.identity=identity
    def add(self,kind,x,y,w,h,text='',source=None,field='',role='body',color=None,bold=False,font=None,size=None,text_class=None,component=''):
        if kind=='text':
            text_class=text_class or ('upstream_content' if source else 'renderer_label')
            if text_class=='renderer_label' and text not in LABELS:raise ValueError('Renderer text is not an allowed label: '+text)
            if text_class=='upstream_content' and not source:raise ValueError('Substantive text requires a source reference')
        e=dict(name=f'{self.slide.ref}-element-{len(self.elements)+1:03}',kind=kind,x=round(x,4),y=round(y,4),w=round(w,4),h=round(h,4),
            text=str(text),source_ref=source,source_field=field,font=font or DESIGN['font'],size=size or TYPE[role],
            color=color or DESIGN['ink'],bold=bold,text_class=text_class,typography_role=role,component=component)
        if x<0 or y<0 or x+w>1280 or y+h>720:raise ValueError('Component outside slide: '+e['name'])
        self.elements.append(e);return e
    def rect(self,x,y,w,h,color,**kw):return self.add('rect',x,y,w,h,color=color,**kw)
    def text(self,x,y,w,h,text,source=None,field='',**kw):return self.add('text',x,y,w,h,text,source,field,**kw)
    def math(self,x,y,w,h,text,source,field,**kw):return self.text(x,y,w,h,text,source,field,role='mathematical_expression',font=DESIGN['math_font'],**kw)
    def label(self,x,y,w,text,**kw):return self.text(x,y,w,32,text,role='section_label',bold=True,color=DESIGN['accent'],**kw)
    def header(self,label=None):
        if label:self.label(64,32,1100,label)
        self.text(64,76 if label else 56,1152,76,self.slide.title,role='slide_title',bold=True)
    def footer(self):
        self.rect(64,662,1152,1,DESIGN['line'],component='footer')
        context=f'{self.identity.awarding_body.replace("Pearson ","")} {self.identity.qualification} — {self.identity.curriculum_section}'
        self.text(64,675,1075,27,context,role='small_footer',color=DESIGN['muted'],text_class='footer',component='footer')
        self.text(1170,675,45,27,str(self.slide.slide_number),role='small_footer',color=DESIGN['muted'],text_class='slide_number',component='footer')
    def input_cards(self,entries,x,y,width,height,definitions=False):
        gap=20;card=(width-2*gap)/3
        for j,(symbol,value,source,field) in enumerate(entries):
            left=x+j*(card+gap)
            self.rect(left,y,card,height,DESIGN['tint'],component='input_cards')
            self.math(left+22,y+13,card-44,62,symbol if definitions else symbol+' = '+value,source,field,size=40 if definitions else 36,component='input_cards')
            if definitions:self.text(left+22,y+73,card-44,height-78,value,source,field,size=24,component='input_cards')
    def formula_panel(self,x,y,w,h,formula,source,field,size=42):
        self.rect(x,y,w,h,DESIGN['ink'],component='formula_panel')
        self.math(x+28,y+18,w-56,h-24,formula,source,field,size=size,color='#FFFFFF',component='formula_panel')
    def worked_step(self,x,y,w,h,number,label,answer=False):
        self.rect(x,y,w,h,DESIGN['ink'] if answer else DESIGN['tint'],component='worked_step')
        self.text(x+20,y+16,35,30,str(number),role='section_label',color='#FFFFFF' if answer else DESIGN['accent'],bold=True,component='worked_step')
        self.text(x+58,y+16,w-78,30,label,role='section_label',color='#FFFFFF' if answer else DESIGN['accent'],bold=True,component='worked_step')
    def working_space(self,x,y,w,h,label='WORKING SPACE'):
        self.label(x,y,w,label,component='working_space')
        for j in range(1,4):self.rect(x,y+38+j*(h-40)/3,w,1,DESIGN['line'],component='working_space')
    def title_slide(self,requirements):
        self.rect(0,0,512,642,DESIGN['ink'],component='title_slide')
        self.text(64,155,400,230,'Standard Deviation',role='lesson_title',color='#FFFFFF',bold=True,component='title_slide')
        self.label(570,111,630,'LEARNING GOALS',component='title_slide')
        for j,r in enumerate(requirements):
            y=191+j*140
            self.text(570,y,46,40,str(j+1),role='section_label',bold=True,color=DESIGN['accent'],component='title_slide')
            self.text(630,y-5,570,122,GOALS[r.type],r.ref,'statement:student_goal_transform/1',size=31,component='title_slide')
            if j<2:self.rect(630,y+113,570,1,DESIGN['line'],component='title_slide')
    def concept_statement(self,b):
        self.header('CORE IDEA')
        sentences=re.split(r'(?<=\.)\s+',b.text)
        if len(sentences)!=2:raise ValueError('Concept layout requires two validated sentences')
        self.rect(64,201,6,218,DESIGN['accent'],component='concept_statement')
        self.text(100,193,1090,220,sentences[0],b.ref,'text/sentence/0',size=44,component='concept_statement')
        self.rect(64,468,1152,143,DESIGN['tint'],component='concept_statement')
        self.text(98,495,1084,104,sentences[1],b.ref,'text/sentence/1',size=33,component='concept_statement')
    def dot_plot(self,values,minimum,maximum,mean,label,source,y):
        left,width=248,904
        xpos=lambda v:scale_position(v,minimum,maximum,left,width)
        self.rect(64,y-50,1152,135,DESIGN['pale'],component='dot_plot')
        self.text(84,y-18,150,42,'Dataset '+label,source,f'visual/datasets/{label}:label',size=26,bold=True,component='dot_plot')
        self.rect(left,y,width,2,DESIGN['line'],source=source,field='visual:shared_scale',component='dot_plot')
        self.rect(xpos(mean)-1,y-44,2,32,DESIGN['accent'],source=source,field=f'visual/claims/{label}/mean',component='dot_plot')
        color=DESIGN['accent'] if label=='A' else DESIGN['secondary']
        for j,value in enumerate(values):
            px=xpos(value)
            self.add('ellipse',px-9,y-9,18,18,source=source,field=f'visual/datasets/{label}/{j}',color=color,component='dot_plot')
            self.text(px-24,y+21,56,40,value,source,f'visual/datasets/{label}/{j}',size=25,color=color,component='dot_plot')
        return dict(values=list(values),minimum=minimum,maximum=maximum,mean=mean,left=left,width=width)
    def process_flow(self,b,formula):
        self.header('METHOD')
        steps=re.split(r'(?<=\.)\s+',b.text)
        if len(steps)!=5:raise ValueError('Expected five authored process steps')
        for j,step in enumerate(steps):
            y=173+j*73
            self.rect(64,y,54,48,DESIGN['accent'],component='process_flow')
            self.text(81,y+4,32,39,str(j+1),size=27,bold=True,color='#FFFFFF',component='process_flow')
            self.text(144,y+2,1060,62,step,b.ref,f'text/sentence/{j}',size=29,component='process_flow')
            if j<4:self.text(82,y+48,32,29,'↓',size=22,color=DESIGN['muted'],component='process_flow')
        self.formula_panel(64,564,1152,80,'σ = '+equation(formula.expression),formula.ref,'expression',size=39)
    def task_form(self,b,formula):
        self.header();self.label(64,145,1152,'WHAT YOU ARE GIVEN')
        self.input_cards([(SYMBOLS[k],b.instructional_inputs[k],b.ref,'instructional_inputs/'+k) for k in ('n','sum_x','sum_x2')],64,187,1152,153,True)
        self.label(64,355,1152,'SUBSTITUTE INTO');self.text(591,345,60,40,'↓',size=34,color=DESIGN['accent'])
        self.formula_panel(64,393,1152,98,'σ = '+equation(formula.expression),formula.ref,'expression',size=44)
        self.label(64,517,1152,'CALCULATE σ');self.text(591,500,60,40,'↓',size=34,color=DESIGN['accent'])
        self.text(64,556,1152,87,b.text,b.ref,'text',size=25,component='task_form_method')
    def worked_example(self,q,solution,formula):
        self.header()
        self.text(64,142,1152,84,q.question,q.ref,'question',size=25,component='worked_example')
        for args in ((64,244,552,159,1,'IDENTIFY'),(644,244,572,159,2,'SUBSTITUTE'),(64,425,552,222,3,'SIMPLIFY'),(644,425,572,222,4,'ANSWER')):
            self.worked_step(*args,answer=args[-1]=='ANSWER')
        for j,k in enumerate(('n','sum_x','sum_x2')):
            value=str(getattr(q.summary,k))
            self.math(84+j*177,298,175,50,SYMBOLS[k]+' = '+value,q.ref,'summary/'+k,size=31,component='worked_example')
        self.math(84,353,510,40,solution.method_steps[0],solution.ref,'method_steps/0',size=26,component='worked_example')
        self.math(664,308,532,77,'σ = '+equation(formula.expression,q.summary.model_dump()),formula.ref,'expression:substitution:'+q.ref,size=32,component='worked_example')
        for j,step in enumerate(solution.method_steps[1:3],1):
            shown=re.sub(r'sqrt\(([^()]*)\)',r'√(\1)',step).replace('^2','²').replace('population SD','σ')
            self.math(84,482+(j-1)*75,512,64,shown,solution.ref,f'method_steps/{j}',size=25 if j==1 else 40,component='worked_example')
        self.math(674,474,520,95,'σ ≈ '+solution.display_answer,solution.ref,'display_answer',size=72,color='#FFFFFF',component='worked_example')
        self.text(674,589,515,45,solution.method_steps[3],solution.ref,'method_steps/3',size=23,color='#FFFFFF',component='worked_example')
    def practice_question(self,q,check=False):
        self.header('CHECK YOUR LEARNING' if check else 'TRY IT')
        self.text(64,170,1152,105,q.question,q.ref,'question',size=28,component='learning_check' if check else 'practice_question')
        self.input_cards([(SYMBOLS[k],str(getattr(q.summary,k)),q.ref,'summary/'+k) for k in ('n','sum_x','sum_x2')],64,292,1152,91)
        self.working_space(64,417,1152,213,'RESPONSE' if check else 'WORKING SPACE')
    def learning_check(self,q):
        if q.summary:return self.practice_question(q,True)
        self.header('CHECK YOUR LEARNING')
        self.rect(64,198,6,202,DESIGN['accent'],component='learning_check')
        self.text(102,196,1090,207,q.question,q.ref,'question',size=44,component='learning_check')
        self.working_space(102,434,1090,193,'RESPONSE')
    def summary_checklist(self,requirements):
        self.header();self.label(64,172,1152,'CAN YOU NOW...')
        for j,r in enumerate(requirements):
            y=249+j*120
            self.rect(64,y+6,32,32,DESIGN['accent'],component='summary_checklist')
            self.rect(67,y+9,26,26,'#FFFFFF',component='summary_checklist')
            self.text(130,y-1,1086,103,GOALS[r.type],r.ref,'statement:student_goal_transform/1',size=34,component='summary_checklist')


def classroom_plan(manifest,authored,learning):
    objects={o.ref:o for o in (*authored.content_blocks,*authored.instructional_formulas,*authored.worked_examples,*authored.practice_items,*authored.learning_checks,*authored.solutions)}
    requirements={r.ref:r for r in learning.learning_requirements};pages=[]
    for s in manifest.slides:
        c=Components(s,authored.identity);metadata={}
        if s.slide_type in ('title_learning_goals','learning_summary'):
            ordered=sorted((requirements[r] for r in s.learning_requirement_refs),key=lambda r:list(GOALS).index(r.type))
            (c.title_slide if s.slide_number==1 else c.summary_checklist)(ordered)
        else:
            b=next(objects[r] for r in s.content_refs if hasattr(objects[r],'kind') and hasattr(objects[r],'text'))
            if s.slide_type=='concept':c.concept_statement(b)
            elif s.slide_type=='visual_comparison':
                c.header();visual=b.visual;values=[float(v) for row in visual.datasets.values() for v in row]
                mean=visual.claims['A']['mean']
                c.text(550,157,290,45,'Mean = '+mean,b.ref,'visual/claims/A/mean',size=30,bold=True,color=DESIGN['accent'])
                metadata['plots']=[c.dot_plot(visual.datasets[label],min(values),max(values),visual.claims[label]['mean'],label,b.ref,y) for label,y in (('A',278),('B',479))]
                c.text(64,591,1152,51,b.text,b.ref,'text',size=27)
            elif s.slide_type in ('calculation_method','task_form_method'):
                (c.process_flow if s.slide_type=='calculation_method' else c.task_form)(b,objects[b.formula_refs[0]])
            elif s.slide_type=='worked_example':
                c.worked_example(objects[b.item_ref],next(objects[r] for r in s.content_refs if hasattr(objects[r],'method_steps')),next(objects[r] for r in s.content_refs if hasattr(objects[r],'expression')))
            elif s.slide_type=='student_practice':c.practice_question(objects[b.item_ref])
            else:c.learning_check(objects[b.item_ref])
        c.footer();pages.append(dict(ref=s.ref,number=s.slide_number,elements=c.elements,metadata=metadata,layout_family=s.slide_type))
    return dict(design=DESIGN,slides=pages,manifest_binding=manifest.source_validation)
