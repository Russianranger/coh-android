"""Acceptance-gate tests with tiny synthetic data and subprocesses, never game code."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import compare_reference_templates as compare
import generate_runtime_data as generation


def digest(data):
    return hashlib.sha256(data).hexdigest()


class ReferenceComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime, self.reference = self.root / 'runtime', self.root / 'reference'
        self.runtime.mkdir()
        self.reference.mkdir()
        self.output = self.root / 'evidence'
        (self.root / 'docs').mkdir()
        self.text = {'data/defs/example.def': b'pinned text\n',
                     'data/server/db/servers.cfg': b'UseFakeAuth 1\n',
                     'data/defs/dbidmaps/invconcept.dbidmap': b'unchanged extra ID map\n'}
        self.text.update({name: b'old pinned identifiers\n' for name in compare.DBIDMAPS})
        for name, value in self.text.items():
            path = self.runtime / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
        for lock_name, commit, values in (
                ('upstream-lock.json', generation.SOURCE_COMMIT, {'data/server/db/servers.cfg': self.text['data/server/db/servers.cfg']}),
                ('content-lock.json', generation.DATA_COMMIT, self.text)):
            records = [{'path': name, 'size': len(value), 'sha256': digest(value)} for name, value in values.items()]
            manifest = 'docs/' + lock_name
            (self.root / manifest).write_text(json.dumps({'commit': commit, 'entries': records}))
            (self.root / lock_name).write_text(json.dumps({'commit': commit, 'files': len(records),
                                                         'bytes': sum(r['size'] for r in records), 'manifest': manifest}))
        asset = self.runtime / 'data/anim/example.anim'
        asset.parent.mkdir(parents=True)
        asset.write_bytes(b'asset payload')
        exe = b'synthetic reference executable; never executed'
        for directory in (self.runtime, self.reference):
            (directory / 'MapServer.exe').write_bytes(exe)
        self.hashes = {'MapServer.exe': digest(exe)}
        self.package = {'repository_commit': '1' * 40, 'postgresql_build_input': {'source_commit': generation.SOURCE_COMMIT},
                        'postgresql_persistence_fixture': False}
        self.inputs = {'status': 'staged_not_gameplay_validated', 'source_commit': generation.SOURCE_COMMIT,
                       'data_commit': generation.DATA_COMMIT, 'executables_supplied': True, 'binary_assets_supplied': True,
                       'reference_repository_commit': self.package['repository_commit'],
                       'postgresql_build_input': self.package['postgresql_build_input'],
                       'build_file_sha256': self.hashes, 'binary_asset_files': {'anim/example.anim': digest(asset.read_bytes())}}
        self.write_inputs()
        # Package PE/import/source reconstruction has independent tests. These
        # tests bind the wrapper to its result and exercise its actual input gate.
        fake_package = patch.object(compare, 'verify_binaries', return_value=(
            self.package, {'MapServer.exe': self.reference / 'MapServer.exe'}, self.hashes))
        fake_package.start()
        self.addCleanup(fake_package.stop)
        self.receipt = {'build_role': 'data_only_db_schema_generation', 'source_commit': generation.SOURCE_COMMIT}
        receipt = patch.object(compare, 'expected_schema_receipt', return_value=self.receipt)
        receipt.start()
        self.addCleanup(receipt.stop)
        self.schema = self.root / 'accepted'
        self.schema.mkdir()
        self.payloads = {name: ('generated ' + name + '\n').encode() for name in compare.EXPECTED}
        self.schema_report = self.schema / 'schema-generation-report.json'
        self.make_archive()

    def write_inputs(self):
        (self.runtime / 'runtime-inputs.json').write_text(json.dumps(self.inputs))

    def make_archive(self, extra=None):
        with zipfile.ZipFile(self.schema / 'schema-outputs.zip', 'w') as archive:
            for name, data in self.payloads.items():
                archive.writestr(name, data)
            if extra:
                archive.writestr(extra, b'bad')
        path = self.schema / 'schema-outputs.zip'
        self.report = {'status': compare.SCHEMA_SUCCESS, 'exit_code': 0, 'failures': [], 'queued_error_counts': [0],
                       'strict_reload_executed': True, 'attribute_files_stable': True,
                       'source_commit': generation.SOURCE_COMMIT, 'data_commit': generation.DATA_COMMIT,
                       'schema_build_input': self.receipt,
                       'schema_outputs_archive': {'bytes': path.stat().st_size, 'sha256': generation.sha256(path),
                           'files': [{'path': name, 'sha256': digest(data), 'bytes': len(data)} for name, data in self.payloads.items()]}}
        self.schema_report.write_text(json.dumps(self.report))

    def script(self, omit=(), suffix=''):
        payloads = {name: data for name, data in self.payloads.items() if name not in omit}
        return ('from pathlib import Path\n'
                f'for name, data in {payloads!r}.items():\n'
                '    path = Path(name)\n'
                '    path.parent.mkdir(parents=True, exist_ok=True)\n'
                '    path.write_bytes(data)\n' + suffix)

    def invoke(self, body=None, timeout=5, log_limit=compare.LOG_LIMIT):
        child = self.root / 'synthetic.py'
        child.write_text(self.script() if body is None else body)
        return compare.run(self.runtime, self.reference, self.schema_report, self.output,
                           timeout=timeout, root=self.root, runner=(sys.executable, str(child)), log_limit=log_limit)

    def assert_no_archive(self, report):
        self.assertNotEqual(report['status'], compare.SUCCESS)
        self.assertTrue(report['failures'])
        self.assertFalse((self.output / 'schema-outputs.zip').exists())

    def test_fresh_equal_56_files_pass_with_explicit_gameplay_and_queue_limits(self):
        report = self.invoke()
        self.assertEqual(report['status'], compare.SUCCESS)
        self.assertEqual(report['identical_fresh_output_count'], 56)
        self.assertEqual(report['output_differences'], [])
        self.assertEqual(len(report['seeded_identifier_sha256']), 11)
        self.assertEqual(report['verified_asset_files'], 1)
        self.assertFalse(report['gameplay_validated'])
        self.assertFalse(report['asset_coverage_complete'])
        self.assertIsNone(report['queued_error_count'])
        self.assertFalse(report['nonfatal_queued_errors_reviewed'])
        self.assertEqual((self.runtime / 'data/defs/dbidmaps/invconcept.dbidmap').read_bytes(), self.text['data/defs/dbidmaps/invconcept.dbidmap'])
        with zipfile.ZipFile(self.output / 'schema-outputs.zip') as archive:
            self.assertEqual(set(n.casefold() for n in archive.namelist()), compare.EXPECTED)
        self.assertEqual(json.loads((self.output / 'reference-template-comparison-report.json').read_text())['status'], compare.SUCCESS)

    def test_zero_exit_with_stale_seeded_identifiers_and_missing_templates_fails(self):
        report = self.invoke('print("done")\n')
        self.assertEqual(report['exit_code'], 0)
        self.assert_no_archive(report)
        stale = {item['path'] for item in report['output_differences'] if item['reason'] == 'not freshly rewritten'}
        self.assertEqual(stale, compare.SEEDS)
        self.assertEqual(len(report['output_differences']), 56)

    def test_missing_template_and_unrewritten_dbidmap_are_independent_failures(self):
        missing = 'data/server/db/templates/ents.template'
        stale = compare.DBIDMAPS[0]
        report = self.invoke(self.script(omit=(missing, stale)))
        self.assert_no_archive(report)
        self.assertEqual({(p['path'], p['reason']) for p in report['output_differences']},
                         {(missing, 'missing'), (stale, 'not freshly rewritten')})

    def test_byte_change_fails_even_when_every_output_is_fresh(self):
        name = 'data/server/db/templates/vars.attribute'
        report = self.invoke(self.script(suffix=f'Path({name!r}).write_bytes(b"changed IDs")\n'))
        self.assert_no_archive(report)
        self.assertEqual(report['output_differences'][0]['reason'], 'bytes differ')
        self.assertEqual(report['output_differences'][0]['path'], name)

    def test_visible_errors_and_schema_only_diagnostics_block_equal_outputs(self):
        report = self.invoke(self.script(suffix='print("ERROR: missing asset")\nprint("COH_DB_TEMPLATES_ONLY_WRITTEN queued_errors=0")\n'))
        self.assert_no_archive(report)
        self.assertTrue(report['failure_diagnostic_lines'])
        self.assertTrue(any('Schema-only' in reason for reason in report['failures']))

    def test_rejects_incomplete_stage_before_any_execution_or_seeding(self):
        (self.runtime / '.runtime-staging-incomplete').write_text('incomplete')
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.invoke()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.runtime / compare.ATTRIBUTES[0]).exists())

    def test_rejects_tampered_reference_binary(self):
        (self.runtime / 'MapServer.exe').write_bytes(b'schema-only or otherwise replaced executable')
        with self.assertRaisesRegex(ValueError, 'reference file hash mismatch'):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_rejects_tampered_asset_and_pinned_text(self):
        path = self.runtime / 'data/anim/example.anim'
        path.write_bytes(b'changed asset')
        with self.assertRaisesRegex(ValueError, 'Staged data hash mismatch'):
            self.invoke()
        path.write_bytes(b'asset payload')
        (self.runtime / 'data/defs/example.def').write_bytes(b'changed text')
        with self.assertRaisesRegex(ValueError, 'Staged data hash mismatch'):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_rejects_preexisting_output_and_cache_namespace(self):
        path = self.runtime / 'data/server/db/templates/ents.template'
        path.parent.mkdir(parents=True)
        path.write_bytes(self.payloads['data/server/db/templates/ents.template'])
        with self.assertRaisesRegex(ValueError, 'data namespace'):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_rejects_bad_source_receipt_and_unaccepted_schema_report(self):
        self.report['schema_build_input'] = {'wrong': True}
        self.schema_report.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, 'source receipt mismatch'):
            self.invoke()
        self.report['schema_build_input'] = self.receipt
        self.report['attribute_files_stable'] = False
        self.schema_report.write_text(json.dumps(self.report))
        with self.assertRaisesRegex(ValueError, 'strict bootstrap/reload'):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_archive_corruption_and_extra_unsafe_members_fail(self):
        archive = self.schema / 'schema-outputs.zip'
        archive.write_bytes(archive.read_bytes() + b'changed archive')
        with self.assertRaisesRegex(ValueError, 'archive hash/size mismatch'):
            self.invoke()
        self.make_archive(extra='../outside')
        with self.assertRaisesRegex(ValueError, 'archive count'):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_empty_symlink_output_directory_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        try:
            (self.runtime / 'data/bin').symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('Symlinks unavailable on host')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            self.invoke()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_reused_runtime_is_rejected(self):
        self.invoke()
        self.output = self.root / 'second-evidence'
        with self.assertRaisesRegex(ValueError, 'reused'):
            self.invoke()
        self.assertFalse(self.output.exists())

    def test_timeout_and_capture_limit_prevent_success(self):
        report = self.invoke('import time\nprint("started", flush=True)\ntime.sleep(30)\n', timeout=0.2)
        self.assert_no_archive(report)
        self.assertTrue(report['timed_out'])
        self.assertLess(report['elapsed_seconds'], 10)

    def test_source_database_config_overrides_companion_config(self):
        path = self.root / 'docs/content-lock.json'
        manifest = json.loads(path.read_text())
        for entry in manifest['entries']:
            if entry['path'] == 'data/server/db/servers.cfg':
                entry.update(size=3, sha256=digest(b'old'))
        path.write_text(json.dumps(manifest))
        lock_path = self.root / 'content-lock.json'
        lock = json.loads(lock_path.read_text())
        lock['bytes'] = sum(entry['size'] for entry in manifest['entries'])
        lock_path.write_text(json.dumps(lock))
        self.assertEqual(self.invoke()['status'], compare.SUCCESS)

    def test_internal_log_overflow_fails_even_with_equal_outputs(self):
        body = self.script(suffix='Path("logs").mkdir()\nPath("logs/errors.log").write_text("x" * 2048)\n')
        report = self.invoke(body, log_limit=1024)
        self.assert_no_archive(report)
        self.assertTrue(any('Internal log exceeded' in reason for reason in report['failures']))
        self.assertEqual(report['internal_logs'][0]['captured_bytes'], 1024)
        self.assertEqual((self.output / 'internal/logs/errors.log').stat().st_size, 1024)

    def test_stdout_limit_is_bounded_and_failed(self):
        report = self.invoke('import sys\nsys.stdout.write("x" * 100000)\nsys.stdout.flush()\n', log_limit=1024)
        self.assert_no_archive(report)
        self.assertTrue(report['log_limit_exceeded'])
        self.assertLessEqual((self.output / 'stdout.log').stat().st_size, 1024)


if __name__ == '__main__':
    unittest.main()
