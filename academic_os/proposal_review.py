"""Render proposals through the existing P1B review-ticket contract."""
from .core import manifest, decision_state
from .review_bundles import object_view, source_view, guard


def proposal_view(graph,decisions,spec,publication):
    versions=manifest(graph,spec.roots);p=graph[spec.roots[0]]['record']['payload']
    parsed=graph['parsed_part:'+p['parsed_part_id']]['record']['payload']
    prompt=' '.join(s['text'] for s in parsed['spans'] if s['role'] in ('prompt','comparison_context'))
    return dict(bundle_id=spec.bundle_id,subject=spec.subject,participation=spec.participation,
        candidate_action=p['candidate_action'],evidence_scope=p['evidence_scope'],registry_lookup=p['registry_lookup'],alternatives=p['alternatives'],
        question_preview=prompt,concepts=[graph['concept:'+c]['record']['payload']['name'] for c in p['concept_ids']],
        competency=graph['competency:'+p['competency_id']]['record']['payload']['skill_name'] if p['competency_id'] else 'UNRESOLVED — no canonical competency asserted',
        role='primary',task_conditions=[graph['task_condition:'+c]['record']['payload']['name'] for c in p['task_condition_ids']],
        interpretation_notes=p['reasoning']+'\n'+p['observation'],parse_warnings=parsed['warnings'],
        required_objects=[object_view(graph,decisions,k) for k in versions],optional_candidate_objects=[],
        sources=source_view(graph,decisions,versions),source_verified=publication['source_verified'],human_approved=publication['human_approved'],
        publishable=publication['publishable'],blockers=publication['reasons'],
        stale_objects=[k for k in versions if decision_state(graph,k,decisions.get(k))=='stale'],
        decision_scope=dict(approve=[k for k in versions if graph[k]['record']['kind'] not in ('source','locator')],reject=list(spec.roots),revise=list(spec.roots)),
        review_ticket=guard(graph,decisions,spec,versions),notice='Registry approval does not approve this new question claim. Existing valid approvals are reused; unresolved requires stage revision.')
