"""Q2(c) concept-boundary regression; decisions only in temporary databases."""
import copy
import tempfile
import unittest
from academic_os.examples.q2_semantics import PRIMARY_KEY, BOUNDARY_NOTE, build_boundary_correction
from academic_os.models import normalise
from .bundle_fixtures import seed, verify_sources

C='BUNDLE-Q2-C-PRIMARY'
OLD_LINK='concept_link:LINK-VARIATION-INTERPRET-EXTREMES'
SECONDARY='part_mapping:MAP-Q2-c-CONTEXT-INFER'

class BoundaryCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store,self.s=seed(self.tmp.name);self.addCleanup(self.store.close)
        # Reconstruct the prior P1A candidate shape using the same copied corpus.
        graph=self.store.graph();mapping=copy.deepcopy(graph[PRIMARY_KEY]['record'])
        p=mapping['payload'];p['focus_concept_ids'].append('CON-STAT-EXTREMES')
        p['semantics']['concept_link_ids'].append(OLD_LINK.split(':')[1])
        p['rationale']=p['rationale'].replace(' '+BOUNDARY_NOTE,'')
        link=copy.deepcopy(graph['concept_link:LINK-CONTEXT-INFER-EXTREMES']['record'])
        link['payload'].update(link_id=OLD_LINK.split(':')[1],canonical_id='CAN-STAT-VARIATION-INTERPRET',
            provenance=graph['competency:CAN-STAT-VARIATION-INTERPRET']['record']['payload']['provenance'])
        self.s.stage([mapping,link],{PRIMARY_KEY:graph[PRIMARY_KEY]['version'],OLD_LINK:None},'TEST-LEGACY')

    def correct(self):return self.s.stage(**build_boundary_correction(self.store.graph()),request_id='TEST-BOUNDARY')

    def test_correction_changes_only_mapping_and_preserves_history(self):
        before=self.store.graph();versions=[tuple(r) for r in self.store.db.execute('select * from versions')]
        self.correct();after=self.store.graph()
        self.assertEqual([k for k in before if before[k]!=after[k]],[PRIMARY_KEY])
        self.assertTrue(set(versions).issubset({tuple(r) for r in self.store.db.execute('select * from versions')}))
        self.assertEqual(before[OLD_LINK],after[OLD_LINK]);self.assertEqual(before[SECONDARY],after[SECONDARY])

    def test_old_ticket_rejected_with_expected_current_versions(self):
        ticket=self.s.review_bundles(C)['review_ticket'];old=ticket['versions'][PRIMARY_KEY]
        self.correct();new=self.store.graph()[PRIMARY_KEY]['version']
        with self.assertRaises(ValueError) as error:
            self.s.review_bundle(C,'approve','TEST-ONLY-OPERATOR','TEST ONLY stale attempt',ticket,'TEST-STALE')
        self.assertIn('stale/conflict',str(error.exception));self.assertIn(old,str(error.exception));self.assertIn(new,str(error.exception))
        self.assertEqual(self.store.decisions(),{})

    def test_primary_closure_excludes_extremes_but_retains_reasoning(self):
        self.correct();view=self.s.review_bundles(C)
        self.assertEqual(view['concepts'],['Standard deviation','Variation / spread'])
        self.assertEqual(view['competency'],'Interpret measures of variation')
        self.assertEqual(view['task_conditions'],['Compare variation using standard deviation'])
        self.assertNotIn(OLD_LINK,view['review_ticket']['versions'])
        self.assertNotIn('concept:CON-STAT-EXTREMES',view['review_ticket']['versions'])
        self.assertIn('more extreme values',view['interpretation_notes'])
        self.assertIn('locator:MS-Q2-c',view['review_ticket']['versions'])

    def test_approved_a_b_preserved_and_core_blocked(self):
        verify_sources(self.s)
        for bid in ['BUNDLE-Q2-A','BUNDLE-Q2-B']:
            self.s.review_bundle(bid,'approve','TEST-ONLY-OPERATOR','TEST ONLY preexisting approvals',
                self.s.review_bundles(bid)['review_ticket'],'TEST-APPROVE-'+bid)
        decisions=self.store.decisions();self.correct()
        self.assertEqual(decisions,self.store.decisions())
        self.assertTrue(self.s.review_bundles('BUNDLE-Q2-A')['human_approved'])
        self.assertTrue(self.s.review_bundles('BUNDLE-Q2-B')['human_approved'])
        self.assertFalse(self.s.review_bundles(C)['human_approved'])
        r=self.s.check_target('Q2-CORE')
        self.assertTrue(r['source_verified']);self.assertFalse(r['human_approved']);self.assertFalse(r['publishable'])

    def test_secondary_unchanged_pending(self):
        before=self.s.review_bundles('BUNDLE-Q2-C-SECONDARY-CANDIDATE')
        self.correct();after=self.s.review_bundles('BUNDLE-Q2-C-SECONDARY-CANDIDATE')
        self.assertEqual(before,after)
        self.assertIn('concept_link:LINK-CONTEXT-INFER-EXTREMES',after['review_ticket']['versions'])
        self.assertEqual(self.s.inspect(SECONDARY)['state'],'pending')

    def test_repeated_correction_is_content_stable(self):
        self.correct();version=self.store.graph()[PRIMARY_KEY]['version']
        plan=build_boundary_correction(self.store.graph())
        self.assertEqual(normalise(plan['items'][0])[1],version)
        self.assertEqual(plan['items'][0]['payload']['rationale'].count(BOUNDARY_NOTE),1)

if __name__=='__main__':unittest.main()
