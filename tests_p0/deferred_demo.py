"""Reproducible TEST ONLY demonstration; never opens the real database."""
import json
from pathlib import Path
from .test_deferred_governance import DeferredGovernanceTests,KEY,TARGET


def main():
    fixture=DeferredGovernanceTests
    fixture.setUpClass()
    case=fixture('test_full_publication_excludes_unresolved')
    try:
        case.setUp();before=case.store.graph();a=case.s.check_target(TARGET)
        event=case.decide();b=case.s.check_target(TARGET)
        unchanged=before==case.store.graph()
        case.prepare_publication();c=case.s.check_target(TARGET)
        sid=case.s.publish_target(TARGET)['snapshot_id'];snapshot=case.s.snapshot(sid)
        payload=snapshot['payload']
        assert not a['publishable'] and KEY in a['versions']
        assert not b['publishable'] and KEY not in b['versions'] and unchanged
        assert c['publishable'] and snapshot['usable']
        assert len(payload['semantic_units'])==4 and KEY not in payload['objects']
        report=dict(test_only=True,real_database_opened=False,
            state_a=a,state_b=b,state_c=c,governance_event=event,
            proposal_unchanged_after_defer=unchanged,
            academic_state=case.inspect()['academic_state'],snapshot_id=sid,
            semantic_units=payload['semantic_units'],trusted_object_keys=sorted(payload['objects']),
            unresolved_entered_trusted_snapshot=KEY in payload['objects'],
            parsed_unresolved_entered_trusted_snapshot='parsed_part:PARSED-Q3-2023-c-ii' in payload['objects'],
            deterministic_republication=case.s.publish_target(TARGET)['snapshot_id']==sid,
            q2_usable=case.s.snapshot(case.q2)['usable'])
        output=Path('output/p1c1_deferred_unresolved/temporary-defer-test.json')
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print('TEST ONLY: A blocked, B deferred but blocked, C published four units; Q2 usable.')
        print(output)
    finally:
        case.doCleanups();fixture.tearDownClass()


if __name__=='__main__':main()
