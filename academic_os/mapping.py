"""Transparent Q2 candidate rules using parsed prompts and scoring evidence."""
from copy import deepcopy
import re
from .models import normalise
from .parsing import parse_q2, PARSER_VERSION


def plan_q2(graph):
    """Return a standard Service.stage bundle; no writes and no approvals."""
    parsed = parse_q2(graph)
    items = list(parsed)
    rules = [('a', 'MEAN-CALC', r'calculate the mean', r'55\.1'),
             ('b', 'SD-CALC', r'calculate the standard deviation', r'2\.2'),
             ('c', 'VARIATION-INTERPRET', r'state, giving a reason', r'standard deviation is greater'),
             ('c', 'CONTEXT-INFER', r'more likely to have trained the winner', r'coach b')]
    for c, suffix, prompt_pattern, scheme_pattern in rules:
        parsed_record = parsed['abc'.index(c)]
        spans = {s['role']: s for s in parsed_record['payload']['spans']}
        prompt = ' '.join(spans['prompt']['text'].lower().split())
        scheme = ' '.join(spans['mark_scheme']['text'].lower().split())
        if not re.search(prompt_pattern, prompt) or not re.search(scheme_pattern, scheme):
            raise ValueError('Unresolved Q2 mapping rule ' + suffix + ': prompt/scheme does not match')
        mid = 'MAP-Q2-' + c + '-' + suffix
        key = 'part_mapping:' + mid
        candidate = deepcopy(graph[key]['record'])
        if candidate['payload']['canonical_id'] != 'CAN-STAT-' + suffix or candidate['payload']['part_id'] != 'Q2-' + c:
            raise ValueError('Existing mapping target differs from explicit Q2 rule: ' + key)
        parsed_ref = 'parsed_part:PARSED-Q2-' + c
        candidate['judgment_refs'] = sorted(set(candidate['judgment_refs'] + [parsed_ref]))
        candidate['payload']['rationale'] = (
            f'Candidate rule {PARSER_VERSION}/{suffix} matched the located prompt and scoring segment. '
            'Partial assessment only; requires academic review of definition, conditions and scheme notes. ' +
            ('Exact syllabus association remains unresolved and is not asserted.' if suffix == 'CONTEXT-INFER'
             else 'Existing section 2.3 scope remains a candidate association.'))
        items.append(candidate)
        for source, role in [('QP', 'prompt'), ('MS', 'mark_scheme')]:
            evidence = deepcopy(graph['evidence:EV-' + source + '-' + mid]['record'])
            evidence['judgment_refs'] = sorted(set(evidence['judgment_refs'] + [parsed_ref]))
            evidence['payload']['observation'] = (
                f'Candidate {suffix} association based on {role} span; exact text retained in {parsed_ref}. '
                'Extracted segment: ' + spans[role]['text'])
            items.append(evidence)
    return dict(items=items, expected_heads={normalise(x)[0]: graph.get(normalise(x)[0], {}).get('version') for x in items})
