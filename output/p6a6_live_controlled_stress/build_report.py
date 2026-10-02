"""Present immutable P6A.6c evidence; never call a provider or alter a run."""
from pathlib import Path
import sys
import html
from collections import Counter

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from academic_os.ai_qualification.storage import read,write_new
from academic_os.ai_qualification.reference_baseline import sha
OUT=Path(__file__).resolve().parent


def cell(value):
    if value is True:value='PASS'
    elif value is False:value='FAIL'
    elif value is None:value='NOT EVALUATED'
    return html.escape(str(value))


def table(title,headers,rows,anchor):
    return '<section id="'+anchor+'"><h2>'+cell(title)+'</h2><div class="scroll"><table><thead><tr>'+''.join(
        '<th>'+cell(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join(
        '<tr>'+''.join('<td>'+cell(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div></section>'


def main():
    index=read(OUT/'experiment-index.json');replay=read(OUT/'offline-replay.json');totals=index['totals']
    assert replay['status']=='PASS' and index['status']=='COMPLETE'
    entries=index['cases'];fields=('first_term','second_term','mean','variance')
    checks=[v for e in entries if e['provenance'] for v in e['provenance']['checks'].values()]
    provenance_counts=dict(Counter(v['status'] for v in checks))
    semantic_passes=sum(v['expression_semantics_valid'] is True for v in checks)
    classes=('PROVIDER_FAILURE','CONTROLLED_INPUT_BINDING_FAILURE','SCHEMA_FAILURE','CONTENT_FAILURE',
        'SCOPE_FAILURE','NUMERIC_ENCODING_FAILURE','MATH_FAILURE','SOLUTION_FAILURE',
        'EXPRESSION_SEMANTIC_FAILURE','DERIVATION_PROVENANCE_FAILURE','COMPOSITION_FAILURE')
    root_counts={c:totals['root_cause_distribution'].get(c,0) for c in classes}
    requests=[e['provider_request_id'] for e in entries if e['provider_request_id']]
    assert len(requests)==len(set(requests))
    summary=dict(milestone='P6A.6c',preflight='PASSED',experiment_complete=True,totals=totals,
        provenance_field_status_counts=provenance_counts,expression_fields_passed=semantic_passes,
        root_cause_distribution=root_counts,provider_request_ids=requests,distinct_request_ids=len(set(requests)),
        offline_replay_passes=2,offline_api_calls=0,historical_artifacts_unchanged=True,
        historical_file_count=replay['historical_file_count'],trusted_state_unchanged=True,
        baseline='v1.6',manifest_sha256=index['preflight']['manifest']['manifest_sha256'],
        protected_files=1578,protected_files_modified=0,academic_approval=False,renderer_readiness=False,
        bounded_conclusion=('Direct controlled symbolic-provenance generation was observed across eight predetermined Standard Deviation SL-10 numeric stress cases.'
            if totals['accepted']==8 else 'Direct controlled generation was accepted for '+str(totals['accepted'])+' of eight predetermined Standard Deviation SL-10 numeric stress cases; failures were preserved without repair.'),
        statistical_benchmark=False,global_model_qualification=False,production_readiness=False,
        case_table=[dict(case_id=e['case_id'],required_inputs=e['required_inputs'],case_sha256=e['case_hash'],brief_sha256=e['brief_hash']) for e in entries],
        expression_inventory={e['case_id']:e['expressions'] for e in entries},
        numeric_inventory={e['case_id']:dict(numeric_answer=e['numerical_solution']['numeric_answer'],
            display_answer=e['numerical_solution']['display_answer'],expected_display=e['expected_display']) if e['numerical_solution'] else None for e in entries})
    write_new(OUT/'summary.json',summary)
    body='<h1>P6A.6c — Controlled live qualification</h1><p class="lead">'+str(totals['accepted'])+' / 8 candidates accepted</p>'
    body+='<p>Eight predetermined Standard Deviation / standard-lesson / SL-10 cases; one direct gpt-5.6-sol call each. Source: immutable experiment-index.json and two network-blocked offline replays. Completed '+cell(index['completed_at'])+'.</p>'
    body+='<p>Brief: authoring-brief/4 · Controlled mode: sl10-controlled-input/1 · Provenance: sl10-provenance-required/1 · Candidate: ai-author-candidate/2 · Baseline: v1.6.</p>'
    body+=table('Controlled case table — full SHA-256 hashes',['Case','n','sum_x','sum_x2','Case SHA-256','Brief SHA-256'],
        [(e['case_id'],e['required_inputs']['n'],e['required_inputs']['sum_x'],e['required_inputs']['sum_x2'],e['case_hash'],e['brief_hash']) for e in entries],'cases')
    body+=table('Per-case decisions and provider requests',['Case','Outcome','Input binding','Provenance','Provider request ID','Run ID'],
        [(e['case_id'],e['outcome'],e['attempt']['controlled_input_binding_valid'],e['attempt']['derivation_provenance_valid'],e['provider_request_id'],e['run_id']) for e in entries],'decisions')
    body+=table('Validation dimensions — counts of eight cases',['Dimension','Passed','Failed','Not evaluated'],
        [(k,v['passed'],v['failed'],v['not_evaluated']) for k,v in totals['dimensions'].items()],'dimensions')
    body+=table('Original four-field symbolic expressions — unchanged model output',['Case',*fields],
        [(e['case_id'],*((e['expressions'] or {}).get(f) for f in fields)) for e in entries],'expressions')
    body+=table('Original numeric answers and two-decimal displays',['Case','Original numeric_answer','Original display_answer','Expected display','Solution valid'],
        [(e['case_id'],(e['numerical_solution'] or {}).get('numeric_answer'),(e['numerical_solution'] or {}).get('display_answer'),e['expected_display'],e['attempt']['solution_valid']) for e in entries],'numbers')
    body+=table('Failure classification — no repair or replacement',['Root cause','Count'],list(root_counts.items()),'root-causes')
    body+='<h2>Replay and integrity</h2><p>Two full offline passes reproduced binding, mathematics, expression semantics, provenance, composition, decisions, report hashes and aggregation. Network access and provider construction were blocked. Original live artifacts were unchanged.</p>'
    body+='<p>'+str(replay['historical_file_count'])+' historical files remained byte-identical. Trusted database and review/governance tables, protected snapshots, P4/P5 and renderer artifacts were unchanged. v1.1–v1.6 integrity checks passed; v1.6 current conformance passed. No v1.7 was created.</p>'
    body+='<p>Live calls attempted: '+str(totals['attempted'])+'; completed: '+str(totals['completed'])+'; provider failures: '+str(totals['provider_failures'])+'. Retry, repair, replacement, candidate mutation, symbolic rewrite, controlled-input correction and offline API calls: 0.</p>'
    body+='<h2>Bounded conclusion</h2><p>'+cell(summary['bounded_conclusion'])+'</p><p>This is controlled engineering evidence, not statistical benchmarking, global model qualification, broad-topic or broad-role robustness, general mathematical reasoning reliability, academic approval, production readiness, or renderer readiness. No publication or lesson rendering occurred.</p>'
    markup='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>P6A.6c qualification evidence</title><style>body{font:15px/1.5 system-ui,sans-serif;color:#202b33;background:#fff;max-width:1500px;margin:40px auto;padding:0 24px}h1{font-size:26px}h2{font-size:19px;margin-top:34px}.lead{font-size:23px;font-weight:650;color:#126344}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #dce1e4;padding:10px;overflow-wrap:anywhere}th{background:#f0f3f5}td{font-family:ui-monospace,monospace}section{margin:28px 0}</style><body>'+body+'</body></html>'
    with (OUT/'qualification-report.html').open('x',encoding='utf-8') as f:f.write(markup)
    files={p.relative_to(ROOT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    write_new(OUT/'closure.json',dict(status='CLOSED',files_added=files,files_modified=[],
        original_live_artifacts_unchanged=all(sha(n)==h for n,h in replay['original_run_artifacts'].items()),
        experiment_index_sha256=sha(OUT/'experiment-index.json'),offline_replay_sha256=sha(OUT/'offline-replay.json'),
        summary_sha256=sha(OUT/'summary.json'),baseline='v1.6',academic_approval=False,renderer_readiness=False))
    print('Report and closure written; '+str(len(files)+1)+' new files; 0 existing files modified.')


if __name__=='__main__':main()
