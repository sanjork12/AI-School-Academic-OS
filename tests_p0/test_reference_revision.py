"""Version-aware engineering baselines; mutation tests use isolated copies."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from academic_os.ai_qualification.reference_baseline import (
    ACTIVE_REFERENCE_BASELINE, ACTIVE_MANIFEST, ACTIVE_DESCRIPTOR,
    load_active, sha, verify_reference)


class RevisionTests(unittest.TestCase):
    def test_current_and_historical_baselines(self):
        for version in ('v1', 'v1.1', 'v1.2', 'v1.3', 'v1.4', 'v1.5', 'v1.6', 'v1.7', 'v1.8', 'v1.9', 'v1.10', 'v1.11', 'v1.12', 'v1.13', 'v1.14', 'v1.15'):
            result = verify_reference('.', version)
            self.assertTrue(result['valid'], result['errors'])

    def test_parent_artifacts_identical_to_revision_start(self):
        start = json.loads(Path('output/reference_freeze_v1_1/revision-start.json').read_text())
        manifest, _ = load_active('.')
        self.assertEqual(manifest['lineage']['parent_artifacts'], start['parent_files'])
        for name, expected in start['parent_files'].items():
            self.assertEqual(sha(name), expected, name)

    def test_revision_identity_and_authorized_delta(self):
        m = json.loads(Path('output/reference_freeze_v1_1/reference_manifest.json').read_text())
        self.assertEqual(ACTIVE_REFERENCE_BASELINE, 'v1.15')
        self.assertEqual(m['parent_reference'], 'v1')
        self.assertEqual(m['revision_type'], 'trusted_read_performance')
        self.assertEqual([d['path'] for d in m['lineage']['protected_production_deltas']], ['academic_os/sources.py'])
        self.assertEqual(m['unexpected_deltas'], [])
        for field in ('semantic_change', 'academic_scope_change', 'trust_semantics_change'):
            self.assertIs(m['lineage'][field], False)
        self.assertIs(m['lineage']['performance_change'], True)

    def test_scope_profiles_and_reference_artifacts_preserved(self):
        m, _ = load_active('.')
        old = json.loads(Path('output/reference_freeze/reference_manifest.json').read_text())
        for field in ('academic_scope', 'lesson_profiles', 'gold_standards', 'protected_snapshots', 'reference_artifacts'):
            self.assertEqual(m[field], old[field], field)
        self.assertEqual(m['database_baseline'], old['database_baseline'])
        self.assertEqual(m['performance_evidence']['cold']['extractions'], 5)
        self.assertEqual(m['performance_evidence']['warm']['extractions'], 0)
        self.assertTrue(m['invariance_evidence']['all_live_comparisons_equal'])


class IsolatedConformanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        actual, _ = load_active('.')
        self.manifest = copy.deepcopy(actual)
        paths = ['academic_os/service.py', 'output/reference_freeze/reference_manifest.json',
                 'var/p0_q2.sqlite3', actual['lesson_profiles'][0]['pptx']]
        for name in paths:
            dest = self.root / name; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(name, dest)
        self.manifest['files'] = {name:sha(self.root/name) for name in paths}
        self.manifest['lineage']['parent_artifacts'] = {
            paths[1]:sha(self.root/paths[1])}
        self.manifest['historical_reference_artifacts'] = {paths[3]:sha(self.root/paths[3])}
        self.manifest['historical_baselines'] = {'v1.1': {paths[1]:sha(self.root/paths[1])}}
        self.manifest['production_inventory'] = [paths[0]]
        self.save_manifest()
        self.assertTrue(verify_reference(self.root)['valid'])

    def save_manifest(self):
        p = self.root / ACTIVE_MANIFEST; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.manifest), encoding='utf-8')
        (self.root/ACTIVE_DESCRIPTOR).write_text(json.dumps(dict(
            active_reference_version=ACTIVE_REFERENCE_BASELINE, manifest_path=ACTIVE_MANIFEST,
            manifest_sha256=sha(p))), encoding='utf-8')

    def test_unknown_protected_production_change(self):
        with (self.root/'academic_os/service.py').open('a') as f:f.write('\n# unexpected delta\n')
        self.assertFalse(verify_reference(self.root)['valid'])

    def test_unknown_new_production_file(self):
        (self.root/'academic_os/unapproved.py').write_text('# not approved')
        self.assertFalse(verify_reference(self.root)['valid'])

    def test_old_manifest_mutation(self):
        with (self.root/'output/reference_freeze/reference_manifest.json').open('a') as f:f.write(' ')
        for version in ('v1', 'v1.1', 'v1.2', 'v1.3', 'v1.4', 'v1.5', 'v1.6', 'v1.7', 'v1.8', 'v1.9'):
            self.assertFalse(verify_reference(self.root, version)['valid'])

    def test_ppt_copy_mutation(self):
        with (self.root/self.manifest['lesson_profiles'][0]['pptx']).open('ab') as f:f.write(b'changed')
        self.assertFalse(verify_reference(self.root)['valid'])

    def test_database_copy_mutation(self):
        with contextlib.closing(sqlite3.connect(self.root/'var/p0_q2.sqlite3')) as db:
            db.execute('INSERT INTO requests VALUES(?,?,?)', ('TEST-UNEXPECTED','TEST','{}'))
            db.commit()
        self.assertFalse(verify_reference(self.root)['valid'])

    def test_active_manifest_tampering(self):
        with (self.root/ACTIVE_MANIFEST).open('a') as f:f.write(' ')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):verify_reference(self.root)

    def test_explicit_selection_no_newest_directory(self):
        fake = self.root/'output/reference_freeze_v999'; fake.mkdir()
        (fake/'reference_manifest.json').write_text('{}')
        self.assertTrue(verify_reference(self.root)['valid'])
        descriptor = self.root/ACTIVE_DESCRIPTOR
        d=json.loads(descriptor.read_text());d['active_reference_version']='v999'
        descriptor.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'Unexpected active'):verify_reference(self.root)

    def test_path_escape_rejected(self):
        self.manifest['files']['../outside']='0'*64;self.save_manifest()
        with self.assertRaisesRegex(ValueError,'outside project'):verify_reference(self.root)

    def test_dry_run_fails_closed_before_provider(self):
        from academic_os.ai_qualification.__main__ import main
        from academic_os.ai_authoring.provider import OpenAICandidateAuthor
        from academic_os.ai_authoring.brief import ROLE
        with patch('academic_os.ai_qualification.__main__.read_inputs',return_value=None), \
             patch('academic_os.ai_qualification.__main__.compile_brief',return_value=None), \
             patch('academic_os.ai_qualification.__main__.capture',return_value={'freeze_inventory_matches':False}), \
             patch.object(OpenAICandidateAuthor,'from_environment',side_effect=AssertionError('No provider')), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['qualify-ai-author','standard-deviation','--profile','standard-lesson',
                                   '--role',ROLE,'--dry-run']),2)
