"""TEST ONLY isolated Q2 corpus/database, never opens the operator database."""
from pathlib import Path
import shutil
from academic_os.examples.q2 import build_candidates, DEFAULT_SOURCES
from academic_os.models import normalise
from academic_os.service import Service
from academic_os.storage import Store


def seed(directory):
    directory=Path(directory);sources=directory/'sources';sources.mkdir()
    for filename in ['9MA0-2025-31-QP.pdf','9MA0-2025-31-MS.pdf','9MA0-Specification-Issue4.pdf']:
        shutil.copyfile(DEFAULT_SOURCES/filename,sources/filename)
    store=Store(directory/'TEST-ONLY.db');service=Service(store)
    items=build_candidates(sources)
    service.stage(items,{normalise(x)[0]:None for x in items},'TEST-SEED')
    service.stage(**service.plan_q2(),request_id='TEST-PARSE')
    service.stage(**service.plan_q2_semantics(),request_id='TEST-SEMANTICS')
    return store,service


def verify_sources(service):
    views=service.review_sources()
    for group in views:
        for obj in [group['source'],*group['locators']]:
            item=service.inspect(obj['key'])
            service.review(item['key'],'verify','TEST-ONLY-OPERATOR','TEST ONLY copied source corpus',
                item['version'],item['dependency_digest'],item['expected_decision'],'TEST-VERIFY-'+item['key'])


def approve_core(service):
    for bid in ['BUNDLE-Q2-A','BUNDLE-Q2-B','BUNDLE-Q2-C-PRIMARY']:
        ticket=service.review_bundles(bid)['review_ticket']
        service.review_bundle(bid,'approve','TEST-ONLY-OPERATOR','TEST ONLY isolated workflow',ticket,'TEST-APPROVE-'+bid)


def scenario(service):
    def status():
        r=service.check_target('Q2-CORE')
        return {k:r[k] for k in ['source_verified','human_approved','publishable']}
    before=status();verify_sources(service);source_only=status();approve_core(service);after=status()
    published=service.publish_target('Q2-CORE');snapshot=service.snapshot(published['snapshot_id'])
    candidate='part_mapping:MAP-Q2-c-CONTEXT-INFER'
    optional=service.check_target('Q2-CORE')['optional_candidates']
    excluded=all(o['key'] not in snapshot['payload']['objects'] for o in optional)
    return dict(trust_boundary='TEST ONLY isolated database and copied sources; not a real operator decision',
        before_review=before,after_source_verification_only=source_only,after_core_academic_approval=after,
        publication=published,snapshot_usable=snapshot['usable'],
        optional_candidate_status=service.inspect(candidate)['state'],
        optional_candidates_excluded=excluded,semantic_units=snapshot['payload']['semantic_units'])
