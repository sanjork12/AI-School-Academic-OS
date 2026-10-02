"""Offline P6A.2 expression replay; never rebuild or write the historical run."""
import json
from pathlib import Path
from academic_os.ai_authoring.expressions import VERSION, verify_solution_expressions
from academic_os.ai_authoring.models import ProviderContent
from academic_os.ai_authoring.brief import digest,serial
from academic_os.ai_qualification.storage import checked_member
from academic_os.ai_qualification.reference_baseline import sha

RUN=Path('output/p6a2_live_qualification/run-46ccbed1b3874c04a226469477e4ea29')
OUT=Path('output/p6a3_expression_verification')


def replay(directory=RUN):
    directory=Path(directory)
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    manifest=read(directory/'run.json');completion=read(directory/'completion.json')
    if completion['status']!='complete' or manifest['requested_attempt_count']!=10:raise ValueError('Unexpected source run')
    results=[]
    for number in range(1,11):
        folder=directory/f'attempt-{number:02d}';attempt=read(folder/'attempt.json')
        for name,h in attempt['artifact_hashes'].items():checked_member(folder,name,h)
        path=folder/attempt['candidate_artifact_ref'];audit=read(path);candidate=audit['candidate']
        if not attempt['accepted'] or not audit['validation']['accepted']:raise ValueError('Expected saved P6A.2 accepted evidence')
        if digest(read(folder/'brief.json'))!=attempt['brief_hash'] or attempt['brief_hash']!=manifest['authoring_brief']['sha256']:
            raise ValueError('Saved brief binding differs')
        if json.loads(audit['raw_response'])!=candidate['content']:raise ValueError('Raw candidate differs')
        content=ProviderContent.model_validate(candidate['content']).model_dump(mode='json')
        report=verify_solution_expressions(content)
        reasons=[v['reason'] for v in report['checks'].values() if not v['valid']]
        category=('VERIFIED' if report['expression_semantics_valid'] else 'UNSUPPORTED' if any(r.startswith('unsupported') for r in reasons)
                  else 'PARSER_FAILURE' if 'parser_failure' in reasons else 'INVALID')
        results.append(dict(attempt_id=folder.name,accepted_by_p6a2=True,category=category,
            candidate_artifact_sha256=sha(path),candidate_content_sha256=digest(candidate),brief_sha256=attempt['brief_hash'],
            expression_semantics=report,academic_approval=False,renderer_readiness=False))
    return dict(implementation_version=VERSION,source_run_id=directory.name,replay_mode='offline',candidate_count=len(results),
        expression_semantics_valid_count=sum(r['category']=='VERIFIED' for r in results),
        expression_semantics_invalid_count=sum(r['category']=='INVALID' for r in results),
        unsupported_expression_count=sum(r['category']=='UNSUPPORTED' for r in results),
        parser_failure_count=sum(r['category']=='PARSER_FAILURE' for r in results),
        expression_checks_performed=sum(len(r['expression_semantics']['checks']) for r in results),
        per_attempt=results,source_artifact_hashes={p.relative_to(directory).as_posix():sha(p) for p in sorted(directory.rglob('*')) if p.is_file()},
        model_provider_calls=0,original_results_rewritten=False,
        scope='Offline expression/value and recomputed-input consistency only; no current academic trust, publication or rendering authority.')


def main():
    first=replay();second=replay()
    assert first==second
    OUT.mkdir(exist_ok=True)
    with (OUT/'replay-report.json').open('x',encoding='utf-8') as f:f.write(serial(first))
    print(serial({k:first[k] for k in ('candidate_count','expression_semantics_valid_count','expression_semantics_invalid_count','unsupported_expression_count','parser_failure_count')}))


if __name__=='__main__':main()
