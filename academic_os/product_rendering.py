"""Presentation uses only the teacher schema, never snapshot objects."""
def teacher_topic_text(view):
    i=view.identity
    lines=[i.title,f'{i.awarding_body} {i.qualification} ({i.specification_code})',i.curriculum_section,'', 'Concept']
    for c in view.concepts:lines.extend(['  '+c.name,'  '+c.description])
    lines.append('Students should be able to')
    capabilities={c.ref:c for c in view.capabilities}
    for c in view.capabilities:
        lines.append('  '+c.name);lines.append('  Task forms');lines.extend('    '+t.name for t in c.task_forms)
    lines.append('Curriculum reference')
    for c in view.curriculum.references:lines.extend(['  '+c.wording,'  Association: '+c.association_status,'  '+c.association_note])
    lines.append('Reviewed assessment evidence')
    for e in view.assessment_evidence:
        lines.extend([f'  {e.session or "Session not separately available"} {e.year or ""} — {e.paper or e.assessment_label} — {e.question_part}',
            '    '+e.question_wording,f'    Marks: {e.marks if e.marks is not None else "Not available"}'])
        capability=capabilities[e.capability_ref];forms={t.ref:t.name for t in capability.task_forms}
        lines+=['    Capability: '+capability.name,'    Task forms: '+', '.join(forms[r] for r in e.task_form_refs)]
        lines+=['    Evidence/source-quality note: '+note for note in e.reading_notes]
    t=view.trust_summary
    lines+=['Trust','  Curriculum wording '+('verified' if t.curriculum_verified else 'not available'),
            '  Academic knowledge approved',f'  {t.reviewed_example_count} reviewed assessment examples',
            '  '+t.scope_note]
    return '\n'.join(lines)
