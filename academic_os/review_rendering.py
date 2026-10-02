"""CLI presentation only; service output remains structured and UI-neutral."""
import json


def sources_text(groups, details=False):
    lines=[]
    for group in groups:
        source=group['source'];metadata=group['metadata']
        lines += [group['subject'], '  Bundle: '+group['bundle_id'],
                  '  Bundle verification: '+('VERIFIED' if group['source_verified'] else 'INCOMPLETE'),
                  f"  Source verification: {source['state'].upper()}",
                  '  Source version: '+source['version'],
                  '  Curriculum: '+metadata['curriculum_identity'], '  Source type: '+metadata['source_type'],
                  '  Edition: '+metadata['version_label'], '  File: '+metadata['artifact_reference'],
                  '  Identity basis: '+metadata['identity_basis']]
        for loc in group['locators']:
            lines += [f"  {loc['label']} — PDF page {loc['page_number']}: {loc['state'].upper()}",
                      '    Expected: '+loc['expected_content'], '    Open: '+loc['anchor'],
                      '    Review object: '+loc['key'], '    Locator version: '+loc['version']]
        lines += ['  Integrity problems: '+('; '.join(group['integrity_errors']) or 'none detected'),
                  '  Source verification does not approve academic interpretation.',
                  '  Inspection makes no decision; verify/reject covers the source and all included locators.', '']
    if details:lines += ['Technical details:',json.dumps(groups,ensure_ascii=False,indent=2)]
    return '\n'.join(lines)


def bundles_text(bundles, details=False):
    lines=[]
    for b in bundles:
        if 'candidate_action' in b:
            lines += ['  Canonical decision: '+b['candidate_action'].upper(), '  Evidence scope: '+b['evidence_scope']]
            if b['candidate_action']!='unresolved':
                lines += ['  Registry '+r['kind']+': '+r['query']+' ['+r['candidate_action'].upper()+']' for r in b['registry_lookup']]
            else:
                lines += ['  Registry searches are alternatives, not a CREATE_CANDIDATE decision.']
                for g in b.get('publication_governance',[]):
                    lines += ['  Publication participation: '+g['participation'], '  Human governance: '+('No decision' if g['governance_state']=='none' else g['governance_state'].upper()), '  Academic identity: STILL UNRESOLVED']
            lines += ['  Unresolved alternative: '+a for a in b['alternatives']]
        participation='Academic interpretation remains unresolved; target participation is shown above.' if b.get('publication_governance') else b['participation']
        lines += [b['subject'], '  '+participation, '  Question: '+b['question_preview'],
                  '  Concepts: '+', '.join(b['concepts']),
                  '  '+b['role'].capitalize()+' competency: '+b['competency'],
                  '  Task condition: '+'; '.join(b['task_conditions']),
                  '  Interpretation notes: '+b['interpretation_notes'],
                  '  Source verification: '+('VERIFIED' if b['source_verified'] else 'INCOMPLETE'),
                  '  Academic approval: '+('APPROVED' if b['human_approved'] else 'INCOMPLETE')]
        lines += ['  Parsing caution: '+warning for warning in b['parse_warnings']]
        for obj in b['required_objects']:
            if obj['kind'] not in ('source','locator'):
                lines.append(f"    {obj['kind']}: {obj['label']} [{obj['state'].upper()}]")
        if b['optional_candidate_objects']:
            lines.append('  Optional, outside this required closure:')
            for obj in b['optional_candidate_objects']:
                lines.append(f"    {obj['kind']}: {obj['label']} [{obj['state'].upper()}]")
        lines += ['  This bundle required closure: '+('READY' if b['publishable'] else 'BLOCKED'),
                  ('  Whole Q3 publication: check --target Q3-2023-CORE (unresolved blocks unless explicitly deferred for that target).' if 'candidate_action' in b else '  Whole Q2 publication: check --target Q2-CORE (all three core bundles required).')]
        lines += ['    '+reason for reason in b['blockers']]
        lines += ['  Bundle: '+b['bundle_id'], '  Inspection makes no decision.', '']
    if details:lines += ['Technical details:',json.dumps(bundles,ensure_ascii=False,indent=2)]
    return '\n'.join(lines)


def unresolved_text(view):
    lines=['Canonical decision: '+view['academic_state'].upper(),
           'Observed reasoning:',view['observation'],'Evidence scope: '+view['evidence_scope']]
    lines += [f'Possible interpretation {i+1}: {a}' for i,a in enumerate(view['alternatives'])]
    lines += ['Publication participation: '+view['participation'],
              'Human governance: '+('No decision' if view['governance_state']=='none' else view['governance_state'].upper())]
    if view['academic_state']=='unresolved':lines.append('Academic identity: STILL UNRESOLVED')
    if view['governance_event']:
        e=view['governance_event'];lines += ['Reviewer: '+e['reviewer'],'Reason: '+e['reason'],'Decision time: '+e['created_at']]
    lines += [view['notice']]
    return '\n'.join(lines)
