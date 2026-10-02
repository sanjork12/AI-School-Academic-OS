"""Observe the existing P6A adapter without changing its normal prompt or validator."""
import json
import re
from types import SimpleNamespace
from ..ai_authoring.provider import OpenAICandidateAuthor, ProviderReply
from ..ai_authoring.service import contains_secret
from ..ai_authoring.brief import serial
from .stress import LIVE_SCENARIOS


def safe_identifier(value):
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9._:/-]{1,160}',value) and not contains_secret(value) else None


def operational_code(exc):
    # No exception message, headers, URL or response body enters artifacts.
    names = {c.__name__ for c in type(exc).__mro__}
    for types, code in (({'AuthenticationError','PermissionDeniedError'},'authentication_or_permission_failure'),
        ({'RateLimitError'},'rate_limit'), ({'APITimeoutError','TimeoutError'},'provider_timeout'),
        ({'APIConnectionError','ConnectionError'},'network_error'),
        ({'ValidationError','JSONDecodeError','LengthFinishReasonError'},'structured_output_transport_failure')):
        if names & types: return code
    return 'provider_failure'


class ObservedAuthor:
    """Fresh observation per call. No candidate/error history is sent to the model."""
    provider_name = 'openai'
    def __init__(self, author, case_id=None):
        self.base_author = author
        self.model = author.model
        self.case_id = case_id
        self.last = {}

    def author_candidate(self, brief):
        outbound = brief.model_dump(mode='json')
        if self.case_id:
            outbound = {'experiment_type':'live_adversarial', 'production_brief':outbound,
                        'isolated_test_instruction': LIVE_SCENARIOS[self.case_id]}
        self.last = {'provider_request_id':None, 'error_code':None, 'configuration':{},
                     'outbound_brief':outbound, 'original_model_response':'', 'call_count':0}
        observed = self.last
        original = self.base_author.client.responses
        class Recorder:
            def parse(self, **kwargs):
                observed['call_count'] += 1
                observed['configuration'] = {k:kwargs[k] for k in ('model','store','max_output_tokens','temperature','reasoning') if k in kwargs}
                observed['configuration']['structured_output_mode'] = 'responses.parse'
                try:
                    result = original.parse(**kwargs)
                    observed['provider_request_id'] = safe_identifier(getattr(result,'_request_id',None))
                    observed['reported_model'] = safe_identifier(getattr(result,'model',None))
                    observed['original_model_response'] = result.output_text
                    return result
                except Exception as exc:
                    observed['error_code'] = operational_code(exc)
                    raise
        provider = OpenAICandidateAuthor(self.model, SimpleNamespace(responses=Recorder()))
        reply = provider.author(outbound)
        if self.case_id == 'wrong_math' and not reply.error_code:
            try:
                content = json.loads(reply.raw)
                content['proposed_solution']['display_answer'] = '-1.00'
                reply = ProviderReply(serial(content), reply.metadata)
                observed['application_mutation'] = 'Force proposed display_answer to -1.00; SD cannot be negative. Original response preserved separately.'
            except (ValueError,KeyError,TypeError):
                observed['application_mutation'] = 'Not applied: no mutable structured solution returned.'
        return reply

    def author(self, brief):
        return self.author_candidate(brief)
