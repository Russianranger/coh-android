"""ARM64 evidence must be checked before sharing the existing save validators."""
import ast
import copy
import json
import zipfile
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))
import interactive_host as host
import stage_app_assets


class InteractiveEvidence(unittest.TestCase):
    def setUp(self):
        self.identity = dict(machine='ARM64', x86_bins_reused=False,
            archive_sha256='a' * 64, executable_sha256='b' * 64, client_run_id=123, data_run_id=122)
        files = {name: {'bytes': 1, 'sha256': 'c' * 64}
                 for name in host.character.host.assets_tool.PROBE_FILES | {'armport-client.zip'}}
        self.runtime = {'armport_client': self.identity, 'files': files}
        self.client = {'files': files}
        self.report = {'armport_client': dict(self.identity),
            'asset_sha256': {name: pin['sha256'] for name, pin in files.items()},
            'stages': [{'stage': 'existing', 'status': 'passed'} for _ in range(13)]}
        self.report['stages'][9] = dict(stage='armport_client_data', status='passed',
            machine='ARM64', x86_bins_reused=False, executable_sha256='b' * 64)

    def test_validated_projection_does_not_mutate_original_evidence(self):
        original = copy.deepcopy(self.report)
        projected = host.legacy_report(self.report, self.runtime, self.client)
        self.assertEqual(self.report, original)
        self.assertEqual(len(projected['stages']), 12)
        self.assertNotIn('armport-client.zip', projected['asset_sha256'])

    def test_avatar_projection_requires_exact_zero_counters(self):
        self.report['character_avatar_supplement'] = dict(
            legacy_repaired_files=0, legacy_backing_files_removed=0, archive_sha256='pinned')
        original = copy.deepcopy(self.report)
        projected = host.legacy_report(self.report, self.runtime, self.client)
        self.assertEqual(projected['character_avatar_supplement'], {'archive_sha256': 'pinned'})
        self.assertEqual(self.report, original)
        for key in ('legacy_repaired_files', 'legacy_backing_files_removed'):
            for value in (None, False, True, '0', -1, 1, 0.0):
                changed = copy.deepcopy(original)
                changed['character_avatar_supplement'][key] = value
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, 'legacy repair'):
                    host.legacy_report(changed, self.runtime, self.client)
            changed = copy.deepcopy(original)
            del changed['character_avatar_supplement'][key]
            with self.assertRaisesRegex(ValueError, 'legacy repair'):
                host.legacy_report(changed, self.runtime, self.client)
        self.report['character_avatar_supplement']['unexpected'] = 1
        self.assertIn('unexpected', host.legacy_report(self.report, self.runtime, self.client)
                      ['character_avatar_supplement'])

    def test_worktree_identity_binds_data_and_verified_native_closure(self):
        import hashlib
        data = dict(format=1, source_data='/game-import/data', import_={'receipt': 'x'},
            cache_archive_sha256='c', prerequisites_archive_sha256='p',
            prerequisites_manifest_sha256='m', normalized_mtime_epoch=1767225600)
        data['import'] = data.pop('import_')
        native = dict(source_commit='s', data_commit='d', files={'exe': {'sha256': 'e'}})
        digest = hashlib.sha256(json.dumps(dict(data=data, native=native),
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        report = {'client_worktree': dict(data, package_sha256='z',
            content_identity_sha256=digest, worktree_key='client-work-'+digest[:24])}
        manifest = {'armport_server_native_closure': native, 'files': {
            name: {'sha256': value} for name, value in
            [('client-runtime.zip', 'z'), ('client-caches.zip', 'c'), ('client-prerequisites.zip', 'p')]}}
        self.assertEqual(host.validation_manifest(report, manifest)
            ['armport_expected_worktree_key'], 'client-work-'+digest[:24])
        for field in ('package_sha256', 'cache_archive_sha256', 'prerequisites_archive_sha256',
                      'prerequisites_manifest_sha256', 'source_data', 'content_identity_sha256', 'worktree_key'):
            bad = copy.deepcopy(report); bad['client_worktree'][field] = 'changed'
            with self.subTest(field=field), self.assertRaises(ValueError):
                host.validation_manifest(bad, manifest)
        altered = copy.deepcopy(manifest); altered['armport_server_native_closure']['data_commit'] = 'other'
        with self.assertRaises(ValueError): host.validation_manifest(report, altered)

    def test_world_metrics_validate_fresh_and_reused_staging(self):
        contract = dict(archive_pin={'bytes': 90}, file_count=3, payload_bytes=100)
        self.runtime['armport_world_contract'] = contract
        for fresh in (True, False):
            world = dict(reuse_validation='pinned_content_verification' if fresh else 'unchanged_filesystem_receipt',
                archive_read_bytes=90 if fresh else 0, decoded_files=3 if fresh else 0,
                decoded_payload_bytes=100 if fresh else 0, installed_files=3 if fresh else 0,
                reused_files=0 if fresh else 3, preparation_elapsed_seconds=0.5, archive_sha256='pinned')
            self.report['atlas_world_supplement'] = world
            projected = host.legacy_report(self.report, self.runtime, self.client)
            self.assertEqual(projected['atlas_world_supplement']['archive_sha256'], 'pinned')
            self.assertNotIn('reuse_validation', projected['atlas_world_supplement'])
            for field in ('archive_read_bytes', 'decoded_files', 'decoded_payload_bytes'):
                for value in (None, False, -1, 999):
                    bad = copy.deepcopy(self.report); bad['atlas_world_supplement'][field] = value
                    with self.assertRaises(ValueError): host.legacy_report(bad, self.runtime, self.client)
            for value in (None, False, -1, float('inf'), float('nan')):
                bad = copy.deepcopy(self.report); bad['atlas_world_supplement']['preparation_elapsed_seconds'] = value
                with self.assertRaises(ValueError): host.legacy_report(bad, self.runtime, self.client)

    def test_wrong_binary_or_incomplete_input_inventory_rejected(self):
        self.report['armport_client']['executable_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'identity'):
            host.legacy_report(self.report, self.runtime, self.client)
        self.report['armport_client']['executable_sha256'] = 'b' * 64
        self.report['asset_sha256'].pop('armport-client.zip')
        with self.assertRaisesRegex(ValueError, 'input hashes'):
            host.legacy_report(self.report, self.runtime, self.client)

    def test_failed_or_misordered_preparation_cannot_be_removed(self):
        self.report['stages'][9]['status'] = 'failed'
        with self.assertRaisesRegex(ValueError, 'preparation'):
            host.legacy_report(self.report, self.runtime, self.client)
        self.report['stages'][9]['status'] = 'passed'
        self.report['stages'][8], self.report['stages'][9] = self.report['stages'][9], self.report['stages'][8]
        with self.assertRaisesRegex(ValueError, 'preparation'):
            host.legacy_report(self.report, self.runtime, self.client)

    def test_failure_notice_preserves_guest_cause_and_escapes_annotation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'latest-report.json').write_text(json.dumps(dict(
                failures=['client exited', 'cleanup incomplete'],
                stages=[dict(stage='client', status='failed')])))
            with zipfile.ZipFile(root / 'report.zip', 'w') as archive:
                archive.writestr('client-evidence/client-console.log',
                                 'wine: Unhandled page fault at 0x123\n')
            result = host.guest_failure_summary(root)
            self.assertEqual(result['failures'], ['client exited', 'cleanup incomplete'])
            self.assertEqual(result['failed_stages'], ['client'])
            self.assertIn('0x123', result['client_faults'][0])
            self.assertIn('%25', host.ci_notice({'error': '50% failed'}))
            self.assertNotIn('\n', host.ci_notice({'error': 'a\nb'}))

    def test_current_helpers_import_from_retained_donor_closure(self):
        tree = ast.parse((ROOT / 'tools/android/interactive/prepare_assets.py').read_text())
        names = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'GUEST_SCRIPTS' for target in node.targets))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in set(names) | set(stage_app_assets.GUEST_DEPENDENCIES):
                shutil.copyfile(ROOT / 'android/guest' / name, root / name)
            for name in ('armport_interactive.py', 'armport_client_package.py', 'client_stdio.py'):
                shutil.copyfile(ROOT / 'armport/app' / name, root / name)
            subprocess.run([sys.executable, '-I', '-c',
                'import sys; sys.path.insert(0,sys.argv[1]); import character_creation_diagnostic, '
                'character_reopen_diagnostic, armport_interactive', temporary], check=True)


if __name__ == '__main__':
    unittest.main()
