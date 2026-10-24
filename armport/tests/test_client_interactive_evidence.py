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
