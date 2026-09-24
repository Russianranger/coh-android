"""Schema-only wrapper gates using synthetic subprocesses, never a game runtime."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import generate_runtime_data as generation
import run_schema_generation as schema


def minimal_pe():
    data = bytearray(512)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 128)
    data[128:132] = b'PE\0\0'
    struct.pack_into('<HH', data, 132, 332, 0)
    struct.pack_into('<H', data, 148, 96)
    struct.pack_into('<H', data, 152, 0x10b)
    struct.pack_into('<I', data, 212, len(data))
    return data


def parse6():
    def pascal(value):
        raw = struct.pack('<H', len(value)) + value
        return raw + b'\0' * (-len(raw) % 4)
    return (b'CrypticS' + struct.pack('<I', 123) + pascal(b'Parse6') + pascal(b'Files1') +
            struct.pack('<IIII', 4, 0, 4, 0))


class SchemaRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'runtime'
        (self.runtime / 'data').mkdir(parents=True)
        self.exe = self.runtime / 'MapServer.exe'
        self.exe.write_bytes(minimal_pe())
        self.exe_hash = generation.sha256(self.exe)
        self.inputs = {'source_commit': generation.SOURCE_COMMIT, 'data_commit': generation.DATA_COMMIT,
                       'executables_supplied': False, 'binary_assets_supplied': False, 'build_file_sha256': {}}
        self.input_path = self.runtime / 'runtime-inputs.json'
        self.input_path.write_text(json.dumps(self.inputs))
        self.original_manifest = self.input_path.read_bytes()
        self.receipt = {'schema_version': 1, 'build_role': 'data_only_db_schema_generation',
                        'source_commit': generation.SOURCE_COMMIT, 'schema_patch_sha256': '1' * 64}
        self.receipt_path = self.root / 'schema-generation-build-input.json'
        self.receipt_path.write_text(json.dumps(self.receipt))
        # Source reconstruction has its own tests; these isolate the runner's
        # binding to that result and prohibit invented executable receipts.
        expected = patch.object(schema, 'expected_schema_receipt', return_value=self.receipt.copy())
        expected.start()
        self.addCleanup(expected.stop)
        self.output = self.root / 'evidence'

    def runner(self, body):
        path = self.root / 'synthetic-process.py'
        path.write_text(body)
        return (sys.executable, str(path))

    def invoke(self, body, timeout=5, log_limit=schema.LOG_LIMIT, initialize_attributes=False):
        return schema.run_schema_generation(self.runtime, self.receipt_path, self.exe_hash,
                                            self.output, timeout=timeout, root=self.root,
                                            runner=self.runner(body), log_limit=log_limit,
                                            initialize_attributes=initialize_attributes)

    def output_script(self, completion=True):
        paths = [f'data/server/db/templates/{n}.template' for n in generation.TEMPLATES]
        paths += [f'data/server/db/templates/{n}.attribute' for n in generation.ATTRIBUTES]
        paths += [f'data/server/db/schemas/{n}.schema.html' for n in generation.SCHEMAS]
        paths += ['data/defs/powers.dbidmap']
        body = ('from pathlib import Path\n'
                f'for name in {paths!r}:\n'
                '    path = Path(name)\n'
                '    path.parent.mkdir(parents=True, exist_ok=True)\n'
                '    path.write_text("synthetic output\\n")\n'
                'cache = Path("data/bin/incidental.bin")\n'
                'cache.parent.mkdir(parents=True, exist_ok=True)\n'
                f'cache.write_bytes({parse6()!r})\n'
                'print("Warning: synthetic nonfatal warning")\n')
        if completion:
            body += f'print({(schema.COMPLETION + " queued_errors=0")!r})\n'
        return body

    def test_fresh_complete_outputs_are_archived_but_never_gameplay_caches(self):
        report = self.invoke(self.output_script())
        self.assertEqual(report['status'], schema.SUCCESS)
        self.assertFalse(report['gameplay_validated'])
        self.assertEqual(report['serializer_equivalence'], 'unverified')
        self.assertTrue(report['warning_lines'])
        archive = self.output / 'schema-outputs.zip'
        with zipfile.ZipFile(archive) as contents:
            self.assertEqual(len(contents.namelist()), 52)
            self.assertIn('data/defs/powers.dbidmap', contents.namelist())
            self.assertNotIn('data/bin/incidental.bin', contents.namelist())
        self.assertEqual(report['schema_outputs_archive']['sha256'], generation.sha256(archive))
        self.assertEqual(len(report['cache_envelopes']), 1)
        self.assertEqual(self.input_path.read_bytes(), self.original_manifest)
        self.assertTrue((self.output / 'schema-generation-report.json').is_file())

    def test_zero_exit_without_outputs_and_missing_marker_fail(self):
        report = self.invoke('print("done")\n')
        self.assertEqual(report['exit_code'], 0)
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertTrue(any('missing expected output' in failure for failure in report['failures']))
        self.assertTrue(any('completion marker' in failure for failure in report['failures']))
        self.assertFalse((self.output / 'schema-outputs.zip').exists())

    def test_fresh_outputs_without_schema_marker_do_not_pass(self):
        report = self.invoke(self.output_script(completion=False))
        self.assertEqual(len(report['written_outputs']), 53)
        self.assertTrue(any('completion marker' in failure for failure in report['failures']))
        self.assertFalse((self.output / 'schema-outputs.zip').exists())

    def test_stale_outputs_cannot_pass_with_success_marker(self):
        exec(self.output_script().replace('from pathlib import Path\n', ''),
             {'Path': lambda name: self.runtime / name})
        report = self.invoke(f'print({(schema.COMPLETION + " queued_errors=0")!r})\n')
        stale = [f for f in report['failures'] if 'not written during' in f]
        self.assertEqual(len(stale), 51)
        self.assertFalse((self.output / 'schema-outputs.zip').exists())

    def bootstrap_script(self, extra_first='', extra_second='', always_missing=False):
        prelude = ('from pathlib import Path\n'
                   'had_attributes = Path("data/server/db/templates/vars.attribute").exists()\n'
                   f'for name in {schema.ATTRIBUTE_PATHS!r}:\n'
                   f'    if {always_missing!r} or not Path(name).exists():\n'
                   '        prefix = "loading badges.. " if name.endswith("/badgestats.attribute") else ""\n'
                   '        print(prefix + "ERROR: Can\'t open " + name.removeprefix("data/"))\n')
        if extra_first:
            prelude += 'if not had_attributes:\n    ' + extra_first + '\n'
        body = prelude + self.output_script()
        if extra_second:
            body += 'if had_attributes:\n    ' + extra_second + '\n'
        return body

    def test_explicit_bootstrap_then_clean_reload_preserves_all_attribute_bytes(self):
        report = self.invoke(self.bootstrap_script(), initialize_attributes=True)
        self.assertEqual(report['status'], schema.SUCCESS)
        self.assertTrue(report['strict_reload_executed'])
        self.assertTrue(report['attribute_files_stable'])
        self.assertEqual(len(report['bootstrap_evidence']['attribute_sha256']), 6)
        self.assertEqual(len(report['bootstrap_evidence']['classified_diagnostic_lines']), 6)
        self.assertEqual(report['failure_diagnostic_lines'], [])
        bootstrap = self.output.with_name(self.output.name + '-bootstrap')
        first = json.loads((bootstrap / 'schema-generation-report.json').read_text())
        self.assertEqual(first['status'], schema.BOOTSTRAP_READY)
        self.assertTrue(first['failures'])  # Original strict diagnostics retained.
        self.assertFalse((bootstrap / 'schema-outputs.zip').exists())
        self.assertTrue((self.output / 'schema-outputs.zip').exists())

    def test_default_run_never_excuses_first_initialization_errors(self):
        report = self.invoke(self.bootstrap_script())
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertEqual(len(report['failure_diagnostic_lines']), 6)
        self.assertFalse(self.output.with_name(self.output.name + '-bootstrap').exists())

    def test_bootstrap_does_not_excuse_unreadable_preexisting_map(self):
        path = self.runtime / schema.ATTRIBUTE_PATHS[0]
        path.parent.mkdir(parents=True)
        path.write_bytes(b'preexisting map')
        report = self.invoke(self.bootstrap_script(always_missing=True), initialize_attributes=True)
        self.assertFalse(report['strict_reload_executed'])
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertFalse((self.output / 'schema-outputs.zip').exists())

    def test_bootstrap_rejects_unrelated_errors_and_nonexact_prefixed_line(self):
        body = self.bootstrap_script(extra_first='print("unrelated ERROR: bad data")')
        report = self.invoke(body, initialize_attributes=True)
        self.assertFalse(report['strict_reload_executed'])
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertFalse((self.output / 'schema-outputs.zip').exists())
        before = {}
        after = {name: {'sha256': 'a', 'bytes': 1, 'mtime_ns': 1} for name in schema.ATTRIBUTE_PATHS}
        text = "\n".join("ERROR: Can't open " + n.removeprefix('data/') for n in schema.ATTRIBUTE_PATHS)
        text = text.replace("ERROR: Can't open server/db/templates/vars", "Error: hidden failure; ERROR: Can't open server/db/templates/vars")
        self.assertFalse(schema.classify_attribute_bootstrap(before, after, text)['eligible'])

    def test_reload_requires_clean_diagnostics(self):
        body = self.bootstrap_script(extra_second='print("loading badges.. ERROR: unexpected reload failure")')
        report = self.invoke(body, initialize_attributes=True)
        self.assertTrue(report['strict_reload_executed'])
        self.assertTrue(report['attribute_files_stable'])
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertFalse((self.output / 'schema-outputs.zip').exists())

    def test_reload_attribute_byte_changes_remove_archive_and_fail(self):
        change = 'Path("data/server/db/templates/vars.attribute").write_text("changed IDs\\n")'
        report = self.invoke(self.bootstrap_script(extra_second=change), initialize_attributes=True)
        self.assertTrue(report['strict_reload_executed'])
        self.assertFalse(report['attribute_files_stable'])
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertTrue(any('attribute file bytes changed' in f for f in report['failures']))
        self.assertFalse((self.output / 'schema-outputs.zip').exists())
        self.assertNotIn('schema_outputs_archive', report)

    def test_source_receipt_or_executable_hash_mismatch_blocks_launch(self):
        changed = {**self.receipt, 'source_commit': 'wrong'}
        self.receipt_path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, 'source receipt differs'):
            self.invoke('raise SystemExit("must not execute")')
        self.assertFalse(self.output.exists())
        self.receipt_path.write_text(json.dumps(self.receipt))
        self.exe.write_bytes(self.exe.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'executable SHA-256 mismatch'):
            self.invoke('raise SystemExit("must not execute")')
        self.assertFalse(self.output.exists())

    def test_gameplay_manifest_is_not_repurposed_or_rewritten(self):
        self.inputs['executables_supplied'] = True
        self.inputs['build_file_sha256'] = {'MapServer.exe': self.exe_hash}
        self.input_path.write_text(json.dumps(self.inputs))
        before = self.input_path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'text-only staged runtime'):
            self.invoke('print("must not execute")')
        self.assertEqual(self.input_path.read_bytes(), before)
        self.assertFalse(self.output.exists())

    def test_symlink_output_directory_is_rejected_before_launch(self):
        outside = self.root / 'outside'
        outside.mkdir()
        target = self.runtime / 'data/server'
        try:
            target.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('Host does not permit symlinks')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            self.invoke('print("must not execute")')
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse(self.output.exists())

    def test_queued_errors_fail_even_with_zero_exit_and_complete_outputs(self):
        body = self.output_script().replace('queued_errors=0', 'queued_errors=2')
        body += 'print("COH_DB_TEMPLATES_ONLY_DIAGNOSTIC: missing definition")\n'
        report = self.invoke(body)
        self.assertEqual(report['exit_code'], 0)
        self.assertEqual(report['queued_error_counts'], [2])
        self.assertTrue(report['schema_diagnostic_lines'])
        self.assertTrue(any('queued data errors' in failure for failure in report['failures']))
        self.assertNotEqual(report['status'], schema.SUCCESS)

    def test_direct_helpers_accept_ancestor_alias_for_same_runtime(self):
        alias = self.root / 'ancestor-alias'
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('Host does not permit symlink creation')
        aliased_runtime = alias / 'runtime'
        inputs, _, _, _ = schema.check_inputs(aliased_runtime, self.receipt_path,
                                              self.exe_hash, self.root)
        self.assertEqual(inputs, self.inputs)
        path = self.runtime / 'data/server/db/templates/ents.template'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'AuthId int\n')
        record = generation.file_record(path, aliased_runtime)
        self.output.mkdir()
        result = schema.archive_schema_outputs(aliased_runtime, self.output, [record])
        self.assertEqual(result['files'][0]['path'], 'data/server/db/templates/ents.template')
        with zipfile.ZipFile(self.output / result['path']) as archive:
            self.assertEqual(archive.namelist(), ['data/server/db/templates/ents.template'])

    def test_timeout_keeps_bounded_failure_evidence(self):
        report = self.invoke('import time\nprint("started", flush=True)\ntime.sleep(30)\n', timeout=0.2)
        self.assertTrue(report['timed_out'])
        self.assertLess(report['elapsed_seconds'], 10)
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertIn('started', (self.output / 'stdout.log').read_text())

    def test_log_overflow_fails_and_does_not_grow_capture(self):
        report = self.invoke('import sys\nsys.stdout.write("x" * 100000)\nsys.stdout.flush()\n', log_limit=1024)
        self.assertTrue(report['log_limit_exceeded'])
        self.assertLessEqual((self.output / 'stdout.log').stat().st_size, 1024)
        self.assertNotEqual(report['status'], schema.SUCCESS)

    def test_explicit_failure_diagnostic_blocks_complete_outputs(self):
        report = self.invoke(self.output_script() + 'print("Error: synthetic failure")\n')
        self.assertTrue(report['failure_diagnostic_lines'])
        self.assertNotEqual(report['status'], schema.SUCCESS)
        self.assertFalse((self.output / 'schema-outputs.zip').exists())


if __name__ == '__main__':
    unittest.main()
