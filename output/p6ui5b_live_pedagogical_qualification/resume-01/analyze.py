"""Offline replay and neutral comparison. No provider or review calls."""
import json,html
from collections import Counter
from unittest.mock import patch
from qualification import (ROOT,OUT,read,write,services,unchanged,diagnostic,hash_of,DIMENSIONS)

def normalized(p):
    def trim(x,keys): return {k:v for k,v in x.items() if k not in keys}
    def ordered(items):return sorted(items,key=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False))
    cs={c['criterion_id']:trim(c,{'criterion_id','linked_learning_intention','evidence_basis'}) for c in p['success_criteria']}
    acts={a['activity_id']:{**trim(a,{'activity_id','criterion_ids','evidence_basis'}),'criteria':ordered([cs[c] for c in a['criterion_ids']])} for a in p['activity_scope']}
    checks={c['check_id']:{**trim(c,{'check_id','intention_id','criterion_id','activity_id','evidence_basis'}),'criterion':cs[c['criterion_id']],'activity':acts[c['activity_id']]} for c in p['check_alignment']}
    a=p['pedagogical_adapter']
    adapter={**trim(a,{'criterion_ids','activity_ids','check_ids','candidate_role_families','evidence_basis'}),
        'criteria':ordered([cs[c] for c in a['criterion_ids']]),'activities':ordered([acts[c] for c in a['activity_ids']]),
        'checks':ordered([checks[c] for c in a['check_ids']]),'role_families':sorted(a['candidate_role_families'])}
    return dict(success_criteria=ordered(list(cs.values())),activity_scope=ordered(list(acts.values())),check_alignment=ordered(list(checks.values())),pedagogical_adapter=adapter)

def main():
    assert read(OUT/'live-complete.json')['calls']==5
    before=unchanged(); brief=read(OUT/'authoring-brief.json'); pre=read(OUT/'preflight.json')
    ingestion,learning=services(); replay=[]; summaries=[]; norms=[]; bundles=[]
    try:
        with patch('socket.socket.connect',side_effect=AssertionError('Offline replay network forbidden')):
            for attempt in sorted(OUT.glob('attempt-*')):
                result=read(attempt/'validation.json'); obs=read(attempt/'provider-observation.json'); completion=read(attempt/'completion.json')
                summary=dict(candidate_id=attempt.name,status=completion['status'],dimensions=result['dimensions'],reason_codes=result['reason_codes'],response_id=obs.get('response_id'),request_id=obs.get('request_id'),response_model=obs.get('response_model'))
                if (attempt/'parsed-response.json').exists():
                    raw=json.loads((attempt/'raw-output.txt').read_text(encoding='utf-8'))
                    assert raw==read(attempt/'parsed-response.json')
                    wire=read(attempt/'raw-provider-response.json')
                    wire_text=''.join(c['text'] for item in wire.get('output',[]) if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text')
                    assert json.loads(wire_text)==raw
                    again=[diagnostic(raw,brief,obs['provider_success'],learning) for _ in range(2)]
                    assert again[0]==again[1]==result
                    evidence=dict(candidate_id=attempt.name,replay_count=2,identical_validation=True,identical_reason_codes=True,proposal_hash=hash_of(raw),provider_calls=0,passes=again)
                    write(attempt/'offline-replay.json',evidence); replay.append(evidence)
                    summary['exact_proposal_hash']=hash_of(raw)
                if completion['status']=='VALID_FOR_HUMAN_REVIEW':
                    p=read(attempt/'parsed-proposal.json'); n=normalized(p); norms.append(n)
                    summary['normalized_semantic_hash']=hash_of(n)
                    summary['component_hashes']={k:hash_of(v) for k,v in n.items()}
                    s=brief['source_learning_spec']
                    bundle=dict(candidate_id=attempt.name,status='VALID_FOR_HUMAN_REVIEW',target_objective=p['source_id'],tier=p['tier'],
                        official_source_wording=p['source_wording'],reviewed_canonical_semantic=s['canonical_semantics'],governed_learning_intention=s['learning_intentions'],
                        proposed_success_criteria=p['success_criteria'],proposed_activity_scope=p['activity_scope'],proposed_check_alignment=p['check_alignment'],
                        proposed_pedagogical_adapter=p['pedagogical_adapter'],proposed_role_families=p['pedagogical_adapter']['candidate_role_families'],
                        inherited_warnings=s['warnings'],validation_result=result,proposal_hash=hash_of(p),brief_hash=pre['brief_sha256'],
                        review_decision=None,note='Contract-valid only. No pedagogical approval, trusted publication, lesson readiness or quality ranking.')
                    write(OUT/'human-review-bundles'/(attempt.name+'.json'),bundle); bundles.append(bundle)
                summaries.append(summary)
    finally: ingestion.close()
    assert len(summaries)==5
    response_ids=[s['response_id'] for s in summaries if s['response_id']]
    assert len(response_ids)==len(set(response_ids)), 'Repeated provider response identity'
    counts={d:sum(s['dimensions'][d] is True for s in summaries) for d in DIMENSIONS}
    reasons=Counter(r for s in summaries for r in s['reason_codes'])
    diversity=dict(scope='Valid candidates only; malformed/rejected structures are not normalized',
        normalization='Ignore local IDs and ordering; replace all references with their semantic content; exclude shared brief/provenance. Preserve duplicate multiplicity and all pedagogical fields. No edits to original proposals.',
        exact_distinct_proposals=len({s['exact_proposal_hash'] for s in summaries if 'exact_proposal_hash' in s}),
        normalized_distinct_proposals=len({hash_of(n) for n in norms}),
        component_distinct_counts={k:len({hash_of(n[k]) for n in norms}) for k in ['success_criteria','activity_scope','check_alignment','pedagogical_adapter']},
        role_family_distinct_count=len({tuple(sorted(b['proposed_role_families'])) for b in bundles}),
        valid_candidate_count=len(norms),quality_ranking=None)
    write(OUT/'diversity.json',diversity)
    write(OUT/'offline-replay.json',dict(candidates_replayed=len(replay),passes_per_candidate=2,all_identical=True,provider_calls=0))
    write(OUT/'review-comparison.json',dict(candidates=bundles,diversity=diversity,ranking=None))
    # Repository-local immutable review artifact; no external dependencies or scripts.
    esc=lambda v:html.escape(json.dumps(v,ensure_ascii=False,indent=2) if not isinstance(v,str) else v)
    rows=[('Roles','proposed_role_families'),('Success criteria','proposed_success_criteria'),('Activity constraints','proposed_activity_scope'),('Check alignment','proposed_check_alignment'),('Adapter','proposed_pedagogical_adapter')]
    page='<!doctype html><html lang="en"><meta charset="utf-8"><title>P6UI.5B neutral candidate comparison</title><style>body{font:15px system-ui;margin:28px;color:#172033;background:#fafafa}table{border-collapse:collapse;width:100%}th,td{border:1px solid #bbb;padding:12px;vertical-align:top;text-align:left}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;min-width:240px}h1{font-size:24px}.scroll{overflow:auto}a{color:#174ea6}</style><h1>P6UI.5B — human review comparison</h1><p>EDX-4MA1-F-2.8-A · Foundation · gpt-5.6-sol. Differences only; no winner or quality score. VALID_FOR_HUMAN_REVIEW does not mean approved.</p>'
    page+='<p>Frozen brief SHA-256: '+esc(pre['brief_sha256'])+'</p><p>Official source: '+esc(brief['source_learning_spec']['learning_objectives'][0]['official_text'])+'</p><p>Reviewed canonical meaning: '+esc(brief['source_learning_spec']['canonical_semantics'][0]['description'])+'</p>'
    if bundles:
        page+='<div class="scroll"><table><thead><tr><th>Contract component</th>'+''.join('<th>'+esc(b['candidate_id'])+'<br><a href="human-review-bundles/'+b['candidate_id']+'.json">Full review bundle</a></th>' for b in bundles)+'</tr></thead><tbody>'
        for label,key in rows:page+='<tr><th>'+label+'</th>'+''.join('<td><pre>'+esc(b[key])+'</pre></td>' for b in bundles)+'</tr>'
        page+='</tbody></table></div>'
    else:page+='<p>No candidate reached VALID_FOR_HUMAN_REVIEW. Consult validation evidence; no review decision is requested.</p>'
    page+='<h2>Deterministic repetition analysis</h2><pre>'+esc(diversity)+'</pre><h2>Inherited warnings</h2><pre>'+esc(brief['source_learning_spec']['warnings'])+'</pre></html>'
    with (OUT/'review-comparison.html').open('x',encoding='utf-8') as f:f.write(page)
    final_integrity=unchanged();write(OUT/'integrity.json',final_integrity)
    write(OUT/'acceptance.json',dict(verdict='PASS',experiment_integrity='PASS',resolved_model=pre['resolved_model'],identity={k:pre[k] for k in ['brief_id','brief_sha256','learning_spec_id','learning_spec_hash','source_objective_id','tier','policy_version']},
        calls=5,dimension_pass_counts=counts,model_contract_success_rate=f"{counts['overall_proposal_valid']}/5",rejected_count=5-counts['overall_proposal_valid'],reason_distribution=dict(reasons),candidates=summaries,
        retry=0,repair=0,replacement=0,mutation=0,replay_candidates=len(replay),replay_passes=2,review_bundles=len(bundles),human_approvals=0,approved_packs=0,diversity=diversity,integrity=final_integrity,
        active_baseline=read(OUT/'before.json')['active'],protected_implementation_changed=False,new_baseline_created=False,
        limitation='Small bounded five-call sample; structural contract checks are not pedagogical judgment. Model configured explicitly for this process from user instruction.'))
    write(OUT/'evidence-manifest.json',{p.relative_to(OUT).as_posix():__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    print(json.dumps(dict(verdict='PASS',counts=counts,diversity=diversity,reasons=dict(reasons)),indent=2))
if __name__=='__main__':main()
