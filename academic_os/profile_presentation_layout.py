"""Reference-resolving extension of the P4C.1 editable classroom components."""
from types import SimpleNamespace
from .presentation_design import Components, DESIGN, LABELS, classroom_plan
from .presentation_layout import SYMBOLS
from .profile_presentation import validate_profile_manifest

PROFILE_LABELS = frozenset(('Concept retrieval', 'Mini worked example', 'Guided practice',
    'Independent practice', 'Exit check', 'QUICK RESPONSE', 'GUIDED PRACTICE', 'EXIT CHECK',
    'DATA', 'MEAN', 'DEVIATIONS', 'SQUARE', 'AVERAGE', 'SD'))


class ProfileComponents(Components):
    def add(self, kind, x, y, w, h, text='', source=None, field='', **style):
        if kind == 'text' and not source and style.get('text_class') is None and text in PROFILE_LABELS:
            style['text_class'] = 'profile_renderer_label'
        return super().add(kind, x, y, w, h, text, source, field, **style)


def profile_layout(manifest, i):
    validate_profile_manifest(manifest, i)
    objects = {q.ref: q for q in i.package.new_content}
    solutions = {s.item_ref: s for s in i.package.new_solutions}
    formulas = {f.ref: f for f in i.authored.instructional_formulas}
    pages = []
    new_types = {'quick_retrieval', 'mini_worked', 'profile_worked', 'guided_practice', 'profile_practice', 'exit_concept', 'exit_calculation'}
    for slide in manifest.slides:
        if slide.slide_type not in new_types:
            page = classroom_plan(SimpleNamespace(slides=(slide,), source_validation=manifest.source_validation), i.authored, i.learning)['slides'][0]
        else:
            q = objects[slide.content_refs[0]]; solution = solutions[q.ref]
            c = ProfileComponents(slide, i.authored.identity)
            if slide.slide_type == 'profile_worked':
                formula = next(formulas[r] for r in slide.content_refs if r in formulas)
                c.worked_example(q, solution, formula)
            elif slide.slide_type == 'mini_worked':
                c.header('METHOD')
                c.text(64,154,1152,90,q.question,q.ref,'question',size=28)
                steps = [('DATA', ', '.join(q.raw_values), q.ref, 'raw_values'),
                    ('MEAN', solution.mean, solution.ref, 'mean'),
                    ('DEVIATIONS', ', '.join(solution.deviations), solution.ref, 'deviations'),
                    ('SQUARE', ', '.join(solution.squared_deviations), solution.ref, 'squared_deviations'),
                    ('AVERAGE', solution.variance, solution.ref, 'variance'),
                    ('SD', 'σ ≈ '+solution.display_answer, solution.ref, 'display_answer')]
                for n,(label,value,source,field) in enumerate(steps):
                    y=256+n*61
                    c.label(64,y,260,label)
                    c.math(355,y-5,820,54,value,source,field,size=36)
            elif slide.slide_type == 'quick_retrieval':
                c.header('QUICK RESPONSE')
                c.text(64,180,1152,225,q.question,q.ref,'question',size=40)
                c.working_space(64,445,1152,185,'RESPONSE')
            elif slide.slide_type == 'guided_practice':
                c.header('GUIDED PRACTICE')
                c.text(64,155,1152,90,q.question,q.ref,'question',size=28)
                c.input_cards([(SYMBOLS[k],str(getattr(q.summary,k)),q.ref,'summary/'+k) for k in ('n','sum_x','sum_x2')],64,255,1152,80)
                for n,prompt in enumerate(q.scaffolding):
                    y=362+n*67
                    c.text(64,y,680,62,prompt,q.ref,f'scaffolding/{n}',size=27)
                    c.rect(786,y+42,430,1,DESIGN['line'],component='guided_working_space')
                if len(q.scaffolding)<3:
                    c.working_space(64,455,1152,180)
            elif slide.slide_type == 'exit_concept':
                c.header('EXIT CHECK')
                c.text(64,190,1152,190,q.concept_prompt,q.ref,'concept_prompt',size=42)
                c.working_space(64,418,1152,210,'RESPONSE')
            elif slide.slide_type == 'exit_calculation':
                c.header('EXIT CHECK')
                c.text(64,170,1152,105,q.question,q.ref,'question',size=28)
                c.input_cards([(SYMBOLS[k],str(getattr(q.summary,k)),q.ref,'summary/'+k) for k in ('n','sum_x','sum_x2')],64,292,1152,91)
                c.working_space(64,417,1152,213,'RESPONSE')
            else:
                c.practice_question(q)
            c.footer()
            page=dict(ref=slide.ref,number=slide.slide_number,elements=c.elements,metadata={},layout_family=slide.slide_type)
        # Presentation-only profile context, not an academic claim or timing promise.
        context=f'{manifest.profile_title} · {manifest.target_duration_minutes} min target'
        footer=next(e for e in page['elements'] if e.get('text_class')=='footer')
        footer['text'] += ' · ' + context
        footer['source_ref']=manifest.profile_key
        footer['source_field']='identity.title/duration.target_minutes:profile_label'
        if slide.slide_type == 'title_learning_goals':
            c=ProfileComponents(slide,i.authored.identity);c.elements=page['elements']
            c.text(64,510,400,76,context,manifest.profile_key,'identity.title/duration.target_minutes:profile_label',size=25,color='#FFFFFF')
        pages.append(page)
    return dict(design=DESIGN,slides=pages,manifest_binding=manifest.source_validation)
