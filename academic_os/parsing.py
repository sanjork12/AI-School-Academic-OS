"""Pure, fail-closed adapter for the already located June 2025 9MA0 Q2.

This is intentionally not a general PDF parser. Offsets address the unchanged
locator extraction, including imperfect formula glyphs.
"""
import re

PARSER_VERSION = '9ma0-2025-q2/1'


def unique(pattern, text):
    matches = list(re.finditer(pattern, text, re.MULTILINE))
    if len(matches) != 1:
        raise ValueError(f'Q2 parser expected one occurrence of {pattern!r}; found {len(matches)}')
    return matches[0]


def parse_q2(graph):
    def located(lid):
        row = graph['locator:' + lid]
        return row['record']['payload']['extracted_text']

    def span(lid, role, start, end):
        return dict(role=role, locator_id=lid, locator_version=graph['locator:' + lid]['version'],
                    start=start, end=end, text=located(lid)[start:end])

    qp = located('QP-Q2')
    start = unique(r'^2\.\s+Runners in an athletics club', qp).start()
    labels = {c: unique(r'^\s*\(' + c + r'\)', qp) for c in 'abc'}
    if not start < labels['a'].start() < labels['b'].start() < labels['c'].start():
        raise ValueError('Q2 parts are not in a/b/c order')
    parts = []
    for c in 'abc':
        lid = 'QP-Q2-' + c
        if located(lid) != qp:
            raise ValueError('Q2 part locator differs from shared question page')
        begin = labels[c].end()
        rest = qp[begin:]
        mark = re.search(r'\n\s*\((\d+)\)\s*(?=\n|$)', rest)
        if not mark:
            raise ValueError('Q2 missing mark allocation for ' + c)
        end = begin + mark.start()
        next_part = labels[chr(ord(c) + 1)].start() if c != 'c' else len(qp)
        if end >= next_part:
            raise ValueError('Q2 mark allocation crosses next part')
        if c == 'b':
            comparison_start = begin + mark.end()
        msid = 'MS-Q2-' + c
        ms = located(msid)
        msstart = unique(r'^2\(' + c + r'\)', ms).end()
        msend = (unique(r'^2\(' + chr(ord(c) + 1) + r'\)', ms).start()
                 if c != 'c' else unique(r'^\s*\(5 marks\)', ms).start())
        if msend <= msstart:
            raise ValueError('Q2 scheme parts are out of order')
        scheme_marks = unique(r'^\s*\((\d+)\)\s*$', ms[msstart:msend])
        if int(scheme_marks.group(1)) != int(mark.group(1)):
            raise ValueError('Q2 paper and mark scheme allocations disagree')
        notes = unique(r'^Notes:', ms).start()
        spans = [span('QP-Q2', 'shared_stem', start, labels['a'].start()),
                 span(lid, 'prompt', begin, end),
                 span(msid, 'mark_scheme', msstart, msend),
                 span(msid, 'mark_scheme_notes', notes, len(ms))]
        if c == 'c':
            spans.append(span('QP-Q2', 'comparison_context', comparison_start, labels[c].start()))
        parts.append(dict(kind='parsed_part', payload=dict(
            parsed_id='PARSED-Q2-' + c, part_id='Q2-' + c, parser_version=PARSER_VERSION,
            marks=int(mark.group(1)), spans=spans,
            warnings=['Formula glyphs are preserved verbatim; numerical/formula interpretation requires original-page review.'] +
                     (['Scheme (c) depends on (b); larger SD alone does not guarantee faster individual times.'] if c == 'c' else [])),
            judgment_refs=[]))
    return parts
