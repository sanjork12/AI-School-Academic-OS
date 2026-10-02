"""One explicit model call. No provider is constructed during import or validation."""
from dataclasses import dataclass
import os
from time import monotonic
from typing import Protocol
from .models import ProviderContent, Metadata
from .brief import serial


def configured_model():
    """Resolve the same environment/dotenv configuration without SDK construction."""
    from dotenv import load_dotenv
    from .service import contains_secret
    import re
    load_dotenv(override=False)
    model = os.environ.get('ACADEMIC_OS_AUTHOR_MODEL', '').strip()
    if not model or not re.fullmatch(r'[A-Za-z0-9._:/-]{1,160}', model) or contains_secret(model):
        raise ValueError('Author model not configured or invalid')
    return model


@dataclass(frozen=True)
class ProviderReply:
    raw: str
    metadata: Metadata
    error_code: str | None = None


class CandidateAuthor(Protocol):
    def author(self, brief) -> ProviderReply: ...


class OpenAICandidateAuthor:
    def __init__(self, model, client):
        self.model, self.client = model, client

    @classmethod
    def from_environment(cls):
        # Same environment/dotenv convention as the older mapper, but opt-in only.
        model = configured_model()
        from openai import OpenAI
        if not os.environ.get('OPENAI_API_KEY'): raise ValueError('Live provider credentials are not configured')
        # SDK retries would violate the one-attempt experiment.
        return cls(model, OpenAI(max_retries=0, timeout=60.0))

    def author(self, brief):
        started = monotonic()
        usage = {}
        raw = ''
        code = None
        try:
            response = self.client.responses.parse(
                model=self.model, store=False, max_output_tokens=3000,
                input=[{'role': 'system', 'content': 'Propose one untrusted content candidate using only this structured brief. Return the content schema. Never select identities or claim authority.'},
                       {'role': 'user', 'content': serial(brief)}],
                text_format=ProviderContent)
            if response.usage:
                usage = {k: getattr(response.usage, k, None) for k in ('input_tokens', 'output_tokens', 'total_tokens')}
            raw = response.output_text
            if response.status != 'completed' or response.output_parsed is None:
                code = 'provider_incomplete_or_refused'
        except Exception:
            # SDK exception bodies can contain echoed credentials or untrusted output.
            code = 'provider_failed_no_retry'
        return ProviderReply(raw, Metadata(provider='openai', model=self.model,
            latency_seconds=monotonic()-started, **usage), code)
