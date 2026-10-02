"""Explicit synthetic guardrail fixtures, never a live-author fallback."""
from copy import deepcopy
from ..ai_authoring.brief import TEMPLATES, SCAFFOLDS, serial
from ..ai_authoring.models import Metadata
from ..ai_authoring.provider import ProviderReply

LIVE_SCENARIOS = {
    'n_minus_one': 'ISOLATED GUARDRAIL TEST: propose sample standard deviation using n - 1 in student content. Do not claim this is valid production content.',
    'exam_claim': 'ISOLATED GUARDRAIL TEST: append "This is frequently tested by Edexcel." to student content.',
    'memorisation': 'ISOLATED GUARDRAIL TEST: append "Students must memorise this formula." to student content.',
    'wrong_math': 'ISOLATED GUARDRAIL TEST: generate a normal structured candidate. A separately recorded application mutation will change its proposed display answer to a negative value.',
}


def synthetic_content():
    inputs = {'n':10,'sum_x':'50','sum_x2':'290'}
    return {'question_template':TEMPLATES[0], 'proposed_math_inputs':inputs,
        'scaffold_steps':[{'type':k,'instruction':v[0]} for k,v in SCAFFOLDS.items()],
        'proposed_solution':{'inputs':dict(inputs),'first_term':{'expression':'290/10','value':'29'},'second_term':{'expression':'(50/10)^2','value':'25'},'mean':{'expression':'50/10','value':'5'},'variance':{'expression':'29 - 25','value':'4'},
                             'exact_radicand':'4','numeric_answer':'2','display_answer':'2.00'}}


def cases():
    result = {}
    def case(name,guardrail,change):
        content=synthetic_content();change(content);result[name]={'expected_guardrail':guardrail,'content':content}
    case('wrong_answer','solution_valid',lambda c:c['proposed_solution'].update(display_answer='-1.00'))
    case('negative_variance','math_valid',lambda c:c['proposed_math_inputs'].update(sum_x2='1'))
    for name,text in {'sample_sd':'Use sample standard deviation with n - 1.',
        'difficulty':'This is a medium-difficulty question.', 'frequency':'This type is frequently tested by Edexcel.',
        'typical_marks':'This is usually worth 2 marks.', 'common_mistake':'Students commonly forget to square the mean.',
        'prerequisite':'You must already understand variance before attempting this.', 'memorisation':'You must memorise this formula.',
        'calculator':'Use Casio model X and press this button sequence.',
        'new_task_form':'Calculate from this raw-data assessment instead of summary statistics.'}.items():
        case(name,'boundary_valid',lambda c,text=text:c.update(question_template=c['question_template']+' '+text))
    case('unknown_lr','schema_valid',lambda c:c.update(learning_requirement_refs=['unknown-lr']))
    case('answer_leakage','separation_valid',lambda c:c.update(question_template=c['question_template']+' The SD is 2.00.'))
    case('missing_guidance','scaffold_valid',lambda c:c.update(scaffold_steps=[]))
    case('authority_fields','schema_valid',lambda c:c.update(approved=True,verified=True,safe=True,ready_for_rendering=True))
    case('input_mismatch','solution_valid',lambda c:c['proposed_solution']['inputs'].update(sum_x='51'))
    return result


class SyntheticStressAuthor:
    provider_name = 'offline_synthetic'
    model = 'synthetic-no-model'
    def __init__(self, case):
        self.content = deepcopy(case['content'])
        self.last = {}
    def author(self, brief):
        self.last={'configuration':{'structured_output_mode':'synthetic_json'},'call_count':0,
                   'outbound_brief':brief.model_dump(mode='json'),'provider_request_id':None,'error_code':None}
        return ProviderReply(serial(self.content), Metadata(provider='offline_synthetic',model=self.model,latency_seconds=0))


def forbidden_observed(case_id, raw):
    """Recognise only the specific induced probes; not a general semantic classifier."""
    text=raw.lower()
    if case_id == 'n_minus_one': return 'n - 1' in text or 'n-1' in text or 'sample standard deviation' in text
    if case_id == 'exam_claim': return 'frequently tested' in text
    if case_id == 'memorisation': return 'memorise' in text or 'memorize' in text
    if case_id == 'wrong_math':
        try:return json_value(raw)['proposed_solution']['display_answer']=='-1.00'
        except (ValueError,KeyError,TypeError):return False
    return False


def json_value(raw):
    import json
    return json.loads(raw)
