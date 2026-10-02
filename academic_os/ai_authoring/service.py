"""Live read-only inputs, one author call, and separate auditable experiment output."""
import json
import os
import re
from pathlib import Path
from uuid import uuid4
from .brief import ROLE, compile_brief, current_binding, digest, role, serial
from .models import Candidate
from .provenance import POLICY, require_policy
from .validation import validate_candidate, compose, task_refs


def read_inputs(database):
    from ..profile_presentation_service import ProfilePresentationService
    from ..product_catalog import PROTECTED_SNAPSHOTS
    # This method reads/validates; it does not invoke presentation rendering.
    inputs, _ = ProfilePresentationService(database).read_profiles('standard-deviation', PROTECTED_SNAPSHOTS)
    return inputs['standard-lesson']


def contains_secret(text):
    if re.search(r'OPENAI_API_KEY|Bearer\s+\S+|\bsk-[A-Za-z0-9_-]+', text, re.I): return True
    if any(value and value in text for key, value in os.environ.items()
           if any(term in key.upper() for term in ('SECRET', 'TOKEN', 'API_KEY', 'PASSWORD'))): return True
    # Scan decoded nested JSON too (including an escaped raw-response JSON string).
    if text.lstrip().startswith(('{', '[')):
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return False
        def scan(value):
            if isinstance(value, str): return contains_secret(value)
            if isinstance(value, dict): return any(scan(k) or scan(v) for k, v in value.items())
            if isinstance(value, list): return any(scan(v) for v in value)
            return False
        return scan(data)
    return False


def run_once(i, author, refresh=None, *, policy=POLICY, controlled_mode=None, controlled_case=None, controlled_case_sha256=None):
    from .controlled import require_context
    case = require_context(controlled_mode=controlled_mode, controlled_case=controlled_case,
                           controlled_case_sha256=controlled_case_sha256, policy=policy)
    controlled = dict(controlled_mode=controlled_mode, controlled_case=case,
                      controlled_case_sha256=controlled_case_sha256)
    require_policy(policy)
    brief = compile_brief(i, policy=policy, **controlled)
    binding = current_binding(i)
    # Application-owned request identity; never sent as an academic identity.
    candidate_id = 'ai-candidate-' + uuid4().hex
    candidate = None
    payload = {}
    metadata = None
    raw = ''
    error = None
    try:
        reply = author.author(brief)
        metadata = reply.metadata.model_dump(mode='json')
        raw = reply.raw
        error = reply.error_code
        if contains_secret(serial({'raw': raw, 'metadata': metadata})):
            raw, metadata, error = '[WITHHELD: secret-like output]', None, 'secret_output_rejected'
        if len(raw) > 65536:
            raw, error = '[WITHHELD: excessive output]', 'response_size_limit'
        if not error:
            # JSON parser with duplicate-key rejection: ambiguous fields cannot win by order.
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result: raise ValueError('Duplicate JSON key')
                    result[key] = value
                return result
            content = json.loads(raw, object_pairs_hook=pairs)
            payload = dict(candidate_id=candidate_id, brief_ref=brief.identity, brief_sha256=digest(brief),
                current_inputs_sha256=binding, role_ref=ROLE, learning_requirement_refs=role(i).learning_requirement_refs,
                task_form_refs=task_refs(i), content=content, model_metadata=reply.metadata.model_dump())
            candidate = Candidate.model_validate(payload)
    except Exception:
        # Do not persist exception messages from providers or rejected schema values.
        error = 'provider_or_schema_failure_no_retry'
    if refresh is not None:
        try:
            i = refresh()
        except Exception:
            candidate = None
            payload = {}
            error = 'current_source_refresh_failed'
    report = validate_candidate(candidate if candidate else payload, i, policy=policy, **controlled)
    if candidate is None:
        report = report.model_copy(update={'candidate_id': candidate_id})
    accepted = compose(candidate, i, policy=policy, **controlled) if report.accepted else None
    audit = {'format': 'ai-slot-experiment/1', 'candidate_id': candidate_id, 'brief': brief.model_dump(mode='json'),
        'raw_response_label': 'UNTRUSTED MODEL OUTPUT', 'raw_response': raw, 'model_metadata': metadata,
        'provider_error_code': error, 'candidate': candidate.model_dump(mode='json') if candidate else None,
        'validation': report.model_dump(mode='json'), 'experimental_package': accepted,
        'academic_approval': False, 'ready_for_rendering': False, 'live_provider': metadata is not None and metadata['provider'] == 'openai'}
    if contains_secret(serial(audit)): raise ValueError('Artifact contains secret-like data; refused persistence')
    return audit


def save(audit, output_dir):
    data = serial(audit)
    if contains_secret(data): raise ValueError('Secret-like data cannot be persisted')
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # Entire attempt is one file; temp staging plus rename never overwrites an existing attempt.
    from tempfile import NamedTemporaryFile
    destination = out / (audit['candidate_id'] + '.json')
    if not re.fullmatch(r'ai-candidate-[0-9a-f]{32}', audit['candidate_id']): raise ValueError('Invalid application candidate identity')
    with NamedTemporaryFile(mode='w', encoding='utf-8', dir=out, prefix='.attempt-', suffix='.tmp', delete=False) as f:
        temp = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        # Hard-link creates the destination exclusively and publishes a complete file.
        os.link(temp, destination)
    finally:
        temp.unlink()
    return destination
