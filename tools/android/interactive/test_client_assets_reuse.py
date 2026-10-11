"""A timed-out beacon job cannot waive the separate completed graph gate."""
import copy
import unittest

import client_assets_reuse as reuse


class ReuseOwnerTests(unittest.TestCase):
    def setUp(self):
        self.source, self.commit, self.owner = 'a' * 40, 'b' * 40, '1234'
        self.marker = {'version': '0.13.28', 'asset_version': '1.0.0'}
        for role in ('resource', 'native', 'generator'):
            self.marker.update({role + '_run_id': self.owner, role + '_commit': self.source})
        self.values = reuse.marker_values(self.marker, self.commit)
        self.run = {'id': int(self.owner), 'repository': {'full_name': reuse.REPOSITORY},
            'head_repository': {'full_name': reuse.REPOSITORY}, 'head_branch': reuse.BRANCH,
            'path': reuse.WORKFLOW, 'head_sha': self.source, 'status': 'completed', 'conclusion': 'failure'}
        self.jobs = [
            {'id': 1, 'name': 'resources', 'conclusion': 'success'},
            {'id': 2, 'name': 'native / monorail', 'conclusion': 'success'},
            {'id': 3, 'name': 'native / beacons', 'conclusion': 'failure', 'steps': [
                {'name': reuse.ROLES['generator'][2], 'conclusion': 'success'}]},
        ]
        self.artifacts = [
            {'id': index, 'name': name, 'size_in_bytes': 123, 'expired': False,
             'workflow_run': {'id': int(self.owner), 'head_sha': self.source}}
            for index, name in enumerate(('coh-assets-resource-inputs', 'coh-assets-audio-inputs',
                                         'coh-monorail-native', 'coh-kings-row-host-generator'), 1)]
        self.comparison = {'status': 'ahead', 'files': [
            {'filename': 'tools/android/interactive/generate_kings_row_beacons.py'}]}

    def request(self, path):
        if path.startswith('/compare/'):
            return copy.deepcopy(self.comparison)
        if '/jobs?' in path:
            return {'total_count': len(self.jobs), 'jobs': copy.deepcopy(self.jobs)}
        if '/artifacts?' in path:
            return {'total_count': len(self.artifacts), 'artifacts': copy.deepcopy(self.artifacts)}
        self.assertEqual(path, '/actions/runs/' + self.owner)
        return copy.deepcopy(self.run)

    def authenticate(self):
        return reuse.authenticate_reuse(self.values, self.commit, self.request)

    def test_failed_run_retains_only_successful_components_without_claiming_completed_beacons(self):
        evidence = self.authenticate()
        self.assertEqual(set(evidence), {'resource', 'native', 'generator'})
        self.assertEqual(self.values['beacon_run_id'], '')
        self.assertEqual(self.values['beacon_commit'], self.commit)
        self.assertEqual(evidence['generator']['job_conclusion'], 'failure')
        self.assertFalse(any(row['physical_thor_validated'] for row in evidence.values()))

    def test_missing_or_failed_beacon_proof_cannot_be_reused_from_successful_native_compile(self):
        self.values.update(beacon_run_id=self.owner, beacon_commit=self.source)
        with self.assertRaisesRegex(ValueError, 'beacon producer job'):
            self.authenticate()
        self.jobs[-1]['conclusion'] = 'success'
        with self.assertRaisesRegex(ValueError, 'coh-kings-row-beacons'):
            self.authenticate()

    def test_failed_compile_upload_cannot_be_reused(self):
        self.jobs[-1]['steps'][0]['conclusion'] = 'failure'
        with self.assertRaisesRegex(ValueError, 'compile/upload'):
            self.authenticate()

    def test_reuse_needs_explicit_source_not_current_commit_default(self):
        del self.marker['generator_commit']
        with self.assertRaisesRegex(ValueError, 'generator source commit'):
            reuse.marker_values(self.marker, self.commit)

    def test_foreign_or_unfinished_workflow_owner_is_rejected(self):
        for field, value in (('head_sha', 'c' * 40), ('path', '.github/workflows/foreign.yml'),
                             ('head_repository', {'full_name': 'foreign/repo'}),
                             ('head_branch', 'main'), ('status', 'in_progress')):
            original = copy.deepcopy(self.run)
            self.run[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.authenticate()
            self.run = original

    def test_wrong_expired_or_ambiguous_artifact_fails_closed(self):
        original = copy.deepcopy(self.artifacts)
        for field, value in (('expired', True), ('size_in_bytes', 0),
                             ('workflow_run', {'id': 999, 'head_sha': self.source}),
                             ('workflow_run', {'id': int(self.owner), 'head_sha': 'c' * 40})):
            self.artifacts[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.authenticate()
            self.artifacts = copy.deepcopy(original)
        self.artifacts.append(copy.deepcopy(self.artifacts[0]))
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            self.authenticate()

    def test_changed_producer_source_rename_or_incomplete_diff_blocks_reuse(self):
        for comparison in (
            {'status': 'ahead', 'files': [{'filename': 'upstream/ouroboros/MapServer/src/svr/svrinit.c'}]},
            {'status': 'ahead', 'files': [{'filename': 'docs/HANDOFF.md', 'previous_filename': 'assets/reference-inputs-manifest.json'}]},
            {'status': 'diverged', 'files': []},
            {'status': 'ahead', 'files': [{'filename': 'docs/HANDOFF.md'}] * 300},
        ):
            self.comparison = comparison
            with self.subTest(comparison=comparison['status']), self.assertRaises(ValueError):
                self.authenticate()

    def test_successful_beacon_owner_stays_independent(self):
        self.values.update(beacon_run_id=self.owner, beacon_commit=self.source)
        self.jobs[-1]['conclusion'] = 'success'
        self.artifacts.append(dict(self.artifacts[0], id=99, name='coh-kings-row-beacons'))
        evidence = self.authenticate()
        self.assertEqual(evidence['beacon']['artifacts'][0]['id'], 99)


if __name__ == '__main__':
    unittest.main()
