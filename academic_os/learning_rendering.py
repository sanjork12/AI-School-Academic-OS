"""Human-readable WHAT coverage, deliberately not a teaching sequence."""
def learning_specification_text(view):
    lines=[view.identity.title,'Learning Specification',
        f'{view.identity.awarding_body} — {view.identity.qualification} — {view.identity.specification_code}',
        '', 'What students need to understand']
    lines.extend(r.statement for r in view.learning_requirements if r.type=='conceptual_understanding')
    lines.extend(['','What students need to be able to do'])
    lines.extend(r.statement for r in view.learning_requirements if r.type!='conceptual_understanding')
    lines.extend(['','Assessment evidence'])
    for e in view.assessment_evidence:
        lines.append(f'{e.session} {e.year} — {e.paper} — {e.question_part}')
        lines.extend('Evidence/source-quality note: '+note for note in e.reading_notes)
    lines.extend(['','Coverage requirements',*(r.statement for r in view.coverage_requirements),
        '', 'Evidence boundaries',*(r.statement for r in view.evidence_boundaries),
        '', 'Curriculum association remains separate from verified curriculum wording.'])
    for r in view.curriculum.references:lines.append(r.section+': '+r.association_status)
    lines.extend(['',view.trust_summary.upstream.validity_notice])
    return '\n'.join(lines)
