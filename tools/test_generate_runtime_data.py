"""Generation state/output gates; synthetic subprocesses do not simulate CoH."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import generate_runtime_data as generation


def cache(signature=b'Parse6', body=b'\x00\x00\x00\x00'):
    def pascal(value):
        raw = struct.pack('<H', len(value)) + value
        return raw + b'\0' * ((-len(raw)) % 4)
    return (b'CrypticS' + struct.pack('<I', 123) + pascal(signature) +
            pascal(b'Files1') + struct.pack('<III', 4, 0, len(body)) + body)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / 'runtime'
        (self.runtime / 'data').mkdir(parents=True)
        self.executable = self.runtime / 'MapServer.exe'
        self.executable.write_bytes(b'MZ synthetic test executable; never executed')
        self.inputs = {
            'source_commit': generation.SOURCE_COMMIT,
            'data_commit': generation.DATA_COMMIT,
            'build_file_sha256': {'MapServer.exe': generation.sha256(self.executable)},
        }
        self.write_inputs()

    def write_inputs(self):
        (self.runtime / 'runtime-inputs.json').write_text(json.dumps(self.inputs))

    def all_template_outputs(self):
        for name in generation.TEMPLATES:
            path = self.runtime / f'data/server/db/templates/{name}.template'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('AuthId int\n')
        for name in generation.ATTRIBUTES:
            (self.runtime / f'data/server/db/templates/{name}.attribute').write_text('1 "Example"\n')
        for name in generation.SCHEMAS:
            path = self.runtime / f'data/server/db/schemas/{name}.schema.html'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<html>schema</html>')

    def subprocess_fixture(self, body):
        path = self.root / 'fixture.py'
        path.write_text(body)
        return [sys.executable, str(path)]

    def test_zero_exit_without_outputs_cannot_pass(self):
        runner = self.subprocess_fixture('print("done")\n')
        report = generation.run_generation(self.runtime, self.root / 'evidence', runner=runner)
        self.assertEqual(report['status'], 'generation_failed')
        self.assertEqual(report['phases'][0]['exit_code'], 0)
        self.assertTrue(any('missing expected' in e for e in report['phases'][0]['failures']))
        self.assertTrue((self.root / 'evidence/generation-report.json').is_file())

    def test_stale_output_set_cannot_pass(self):
        self.all_template_outputs()
        before = generation.output_snapshot(self.runtime)
        checks = generation.validate_outputs('templates', self.runtime, before, before, '')
        self.assertEqual(len(checks['failures']), 51)
        self.assertTrue(all('not written during' in e for e in checks['failures']))

    def test_every_expected_template_output_is_required(self):
        self.all_template_outputs()
        after = generation.output_snapshot(self.runtime)
        self.assertEqual(generation.validate_outputs('templates', self.runtime, {}, after, '')['failures'], [])
        (self.runtime / 'data/server/db/templates/ents.template').unlink()
        checks = generation.validate_outputs('templates', self.runtime, {},
                                             generation.output_snapshot(self.runtime), '')
        self.assertTrue(any('ents.template' in e for e in checks['failures']))

    def test_timeout_is_failure_and_evidence_is_kept(self):
        runner = self.subprocess_fixture('import time\nprint("started", flush=True)\ntime.sleep(60)\n')
        report = generation.run_generation(self.runtime, self.root / 'evidence',
                                           runner=runner, timeout=0.2)
        self.assertTrue(report['phases'][0]['timed_out'])
        self.assertEqual(report['status'], 'generation_failed')
        self.assertLess(report['phases'][0]['elapsed_seconds'], 10)

    def test_binary_or_source_pin_mismatch_prevents_launch(self):
        self.executable.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            generation.run_generation(self.runtime, self.root / 'evidence')
        self.assertFalse((self.root / 'evidence').exists())
        self.inputs['source_commit'] = 'wrong'
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'Wrong source'):
            generation.check_runtime(self.runtime, ['templates'])

    def test_parse7_and_truncated_parse6_fail(self):
        path = self.root / 'cache.bin'
        path.write_bytes(cache())
        self.assertEqual(generation.parse6_envelope(path)['format'], 'Parse6')
        path.write_bytes(cache(b'Parse7'))
        with self.assertRaisesRegex(ValueError, 'unexpected serialized'):
            generation.parse6_envelope(path)
        path.write_bytes(cache()[:-1])
        with self.assertRaisesRegex(ValueError, 'data block length'):
            generation.parse6_envelope(path)

    def test_server_bins_needs_parser_cache_geometry_and_completion(self):
        path = self.runtime / 'data/bin/example.bin'
        path.parent.mkdir(parents=True)
        path.write_bytes(cache())
        checks = generation.validate_outputs('server-bins', self.runtime, {},
                                             generation.output_snapshot(self.runtime), '')
        self.assertTrue(any('completion marker' in e for e in checks['failures']))
        self.assertTrue(any('no geometry' in e for e in checks['failures']))
        geom = self.runtime / 'data/geobin/example.bin'
        geom.parent.mkdir(parents=True)
        geom.write_bytes(cache())
        checks = generation.validate_outputs('server-bins', self.runtime, {},
                                             generation.output_snapshot(self.runtime), 'Removing old bins..')
        self.assertEqual(checks['failures'], [])
        checks = generation.validate_outputs('server-bins', self.runtime, {},
                                             generation.output_snapshot(self.runtime),
                                             'Removing old bins..\nParserWriteBinaryFile: could not write file')
        self.assertTrue(checks['failures'])

    def test_progress_prefix_does_not_hide_error_diagnostics(self):
        self.all_template_outputs()
        line = "loading badges.. ERROR: Can't open server/db/templates/badgestats.attribute"
        result = generation.validate_outputs('templates', self.runtime, {},
                                             generation.output_snapshot(self.runtime), line)
        self.assertEqual(result['failure_diagnostic_lines'], [line])
        self.assertIn('explicit failure diagnostics appeared in captured output', result['failures'])

    def test_nonzero_exit_stops_later_phases(self):
        runner = self.subprocess_fixture('import sys\nsys.exit(7)\n')
        report = generation.run_generation(self.runtime, self.root / 'evidence',
                                           phases=('templates', 'server-bins'), runner=runner)
        self.assertEqual(len(report['phases']), 1)
        self.assertEqual(report['phases'][0]['exit_code'], 7)
        self.assertFalse((self.root / 'evidence/server-bins').exists())

    def test_gamedatadir_cannot_redirect_generation(self):
        (self.runtime / 'gamedatadir.txt').write_text('C:/unrelated/data')
        with self.assertRaisesRegex(ValueError, 'External data roots'):
            generation.check_runtime(self.runtime, ['templates'])

    def test_ancestor_alias_uses_canonical_containment_but_leaf_symlinks_fail(self):
        alias = self.root / 'ancestor-alias'
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('Host does not permit symlink creation')
        relative = 'data/server/db/templates/ents.template'
        path = self.runtime / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(b'AuthId int\n')
        aliased_runtime = alias / 'runtime'
        expected = generation.file_record(path, self.runtime)
        self.assertEqual(expected['path'], relative)
        self.assertEqual(generation.file_record(aliased_runtime / relative, aliased_runtime), expected)
        self.assertEqual(generation.file_record(path, aliased_runtime), expected)
        self.assertEqual(generation.file_record(aliased_runtime / relative, self.runtime), expected)
        self.assertEqual(generation.output_snapshot(aliased_runtime), generation.output_snapshot(self.runtime))
        self.assertEqual(generation.check_runtime(aliased_runtime, ['templates']), self.inputs)
        link = self.runtime / 'linked-output'
        link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'Symlink output'):
            generation.file_record(aliased_runtime / link.name, aliased_runtime)
        outside = self.root / 'outside'
        outside.write_bytes(b'outside runtime')
        with self.assertRaisesRegex(ValueError, 'Output escaped runtime'):
            generation.file_record(alias / outside.name, aliased_runtime)

    def test_replaced_log_does_not_hide_new_failure_diagnostics(self):
        path = self.runtime / 'run.log'
        path.write_bytes(b'old completed run\n')
        previous = generation.file_record(path, self.runtime)
        path.write_bytes(b'old completed run\nnew output\n')
        self.assertEqual(generation.new_log_text(path, previous), 'new output\n')
        path.write_bytes(b'Error: replacement log contains a failure\n')
        self.assertIn('Error: replacement', generation.new_log_text(path, previous))


if __name__ == '__main__':
    unittest.main()
