#!/usr/bin/env python3
"""Fixture-only driver admission/failure tests; no Android execution occurs."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import run_wire_android as runner
import check_teammate_buffs as original


class Artifacts:
    def __init__(self, root, module):
        self.root = root
        self.repo = root / 'source'
        self.artifacts = root / 'artifacts'
        self.module = module
        self.config = runner.MODULES[module]
        required, pins = runner.required_sources(module)
        self.repo.mkdir()
        for name in required:
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original.ROOT / name, target)
        self.original = runner.c.read(self.repo / 'native-android/engine/entities' / pins)
        for name in self.original:
            target = self.repo / 'upstream/ouroboros' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(original.source(name))
        self.git('init', '-q')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'synthetic driver fixture')
        self.sources = {name: runner.c.digest(self.repo / name) for name in required}
        self.expected = {'fixtures': 2, 'checks': 7, self.config['scope']: False}
        fixture = self.artifacts / 'android' / self.config['fixture']
        fixture.parent.mkdir(parents=True)
        fixture.write_text('/* Synthetic driver admission fixture; not original server data. */\n')
        self.proof = {'schema': self.config['schema'], 'passed': True,
                      'source_unchanged_before_after': True, 'actor_publication': False,
                      'acknowledgments_enabled': False, self.config['scope']: False,
                      self.config['sources']: self.sources,
                      self.config['fixture_key']: runner.c.digest(fixture),
                      self.config['original']: self.original,
                      'checks': {mode: dict(self.expected) for mode in ('release', 'asan', 'ubsan')},
                      'android': {}, 'android_built': list(runner.c.ABIS), 'android_executed': False,
                      'wire_runner_host_controls': {'passed': True, 'test_methods': 9, 'failures': 0, 'errors': 0, 'android_executed': False, 'emulator_qualified': False, 'actor_publication': False, 'acknowledgments_enabled': False}}
        self.refresh_source_state()
        for abi, machine in runner.c.ABIS.items():
            dest = self.artifacts / 'android' / abi
            dest.mkdir()
            name = 'coh_' + self.config['stem'] + '_test'
            binary = dest / name
            # Only ELF identity admission is under test: fake executor below
            # never invokes these deliberately non-executable fixture headers.
            data = bytearray(64)
            data[:7] = b'\x7fELF\x02\x01\x01'
            struct.pack_into('<HHI', data, 16, 3, machine, 1)
            binary.write_bytes(data)
            self.proof['android'][abi] = {'built': True, 'executed': False,
                'abi': abi, 'api_level': 26, 'binary': name,
                'binary_sha256': runner.c.digest(binary),
                'fixtures_sha256': self.proof[self.config['fixture_key']],
                'source_revision': self.proof['source_revision'],
                'source_tree': self.proof['source_tree'], 'source_sha256': self.sources,
                self.config['build_original']: self.original,
                'expected_native_result': dict(self.expected),
                'actor_publication': False, 'acknowledgments_enabled': False,
                self.config['scope']: False}
        self.write()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def refresh_source_state(self):
        self.proof['source_revision'] = self.git('rev-parse', 'HEAD')
        self.proof['source_tree'] = self.git('rev-parse', 'HEAD^{tree}')

    def write(self):
        runner.c.write(self.artifacts / 'qualification.json', self.proof)
        for abi, receipt in self.proof['android'].items():
            runner.c.write(self.artifacts / 'android' / abi / 'receipt.json', receipt)

    def execute(self, behavior='normal'):
        fake = FakeADB(self, behavior)
        output = self.root / ('execution-' + behavior) / 'result.json'
        code = runner.main(['--module', self.module, '--source-root', str(self.repo),
            '--adb', '/synthetic/adb', '--serial', 'emulator-fixture',
            '--artifacts', str(self.artifacts), '--output', str(output)], executor=fake)
        return code, runner.c.read(output), fake


class FakeADB:
    """Explicit dependency injection for control flow only; never real adb."""
    def __init__(self, artifacts, behavior):
        self.artifacts, self.behavior = artifacts, behavior
        self.commands = []
        self.pushed_hash = None
        self.deleted = False

    def __call__(self, command, log, timeout):
        command = list(map(str, command))
        self.commands.append(command)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text('Synthetic command executor: no Android device or native binary invoked.\n')
        args = command[3:]
        if args == ['wait-for-device']:
            return ''
        if args[:2] == ['shell', 'getprop']:
            values = {'ro.build.version.sdk': '33', 'ro.kernel.qemu': '1',
                      'ro.product.cpu.abilist': 'x86_64,x86',
                      'ro.build.fingerprint': 'synthetic/admission-only'}
            if self.behavior == 'wrong_device':
                values['ro.build.version.sdk'] = '34'
            return values[args[2]]
        if args[:2] == ['shell', 'mktemp']:
            return '/data/local/tmp/coh-wire.Fixture123'
        if args[0] == 'push':
            self.pushed_hash = runner.c.digest(Path(args[1]))
            return 'synthetic push'
        if args[:2] == ['shell', 'sha256sum']:
            digest = '0' * 64 if self.behavior == 'push_mutation' else self.pushed_hash
            return digest + '  ' + args[2]
        if args[:2] == ['shell', 'chmod']:
            return ''
        if args[:2] == ['shell', 'timeout']:
            if self.behavior == 'command_failure':
                raise runner.adapter.CommandFailure(log, 126)
            if self.behavior == 'timeout':
                raise RuntimeError('synthetic timeout')
            result = dict(self.artifacts.expected)
            if self.behavior == 'native_mismatch':
                result['checks'] += 1
            if self.behavior == 'native_overclaim':
                result[self.artifacts.config['scope']] = True
            if self.behavior == 'source_drift_during':
                source = self.artifacts.repo / runner.RUNNER_PATH
                source.write_text(source.read_text() + '\n# Synthetic drift\n')
            return json.dumps(result)
        if args[:3] == ['shell', 'rm', '-rf']:
            if self.behavior == 'cleanup_failure':
                raise RuntimeError('synthetic cleanup failed')
            self.deleted = True
            return ''
        if args[:4] == ['shell', 'test', '!', '-e']:
            if not self.deleted or self.behavior == 'cleanup_verify_failure':
                raise RuntimeError('synthetic temp directory still exists')
            return ''
        raise AssertionError('Unexpected fixture command ' + repr(args))


class DriverControls(unittest.TestCase):
    def fixture(self, module):
        tmp = tempfile.TemporaryDirectory(prefix='coh-wire-runner-control-')
        self.addCleanup(tmp.cleanup)
        return Artifacts(Path(tmp.name), module)

    def test_both_modules_and_clean_owned_cleanup(self):
        for module in runner.MODULES:
            with self.subTest(module=module):
                fixture = self.fixture(module)
                expected, entries = runner.validate(fixture.artifacts, fixture.proof, module)
                self.assertEqual(expected, fixture.expected)
                self.assertEqual(set(entries), set(runner.c.ABIS))
                code, result, fake = fixture.execute()
                self.assertEqual(code, 0)
                for key in ('passed', 'android_executed', 'emulator_qualified', 'native_match',
                            'native_result_validated', 'temporary_files_removed'):
                    self.assertIs(result[key], True)
                self.assertTrue(fake.deleted)
                self.assertIs(result['actor_publication'], False)
                self.assertIs(result['acknowledgments_enabled'], False)

    def test_wrong_elf_abi_and_missing_binary(self):
        for module in runner.MODULES:
            for case in ('wrong_abi', 'missing'):
                with self.subTest(module=module, case=case):
                    fixture = self.fixture(module)
                    receipt = fixture.proof['android']['x86_64']
                    binary = fixture.artifacts / 'android/x86_64' / receipt['binary']
                    if case == 'missing':
                        binary.unlink()
                    else:
                        raw = bytearray(binary.read_bytes())
                        struct.pack_into('<H', raw, 18, 183)
                        binary.write_bytes(raw)
                        receipt['binary_sha256'] = runner.c.digest(binary)
                        fixture.write()
                    code, result, fake = fixture.execute(case)
                    self.assertEqual(code, 1)
                    self.assertFalse(fake.commands)
                    self.assertIs(result['device_test_command_attempted'], False)
                    self.assertIs(result['android_executed'], False)

    def test_overclaims_host_mismatch_fixture_and_receipt_drift(self):
        for case in ('overclaim', 'host_mismatch', 'fixture', 'receipt', 'build_executed'):
            with self.subTest(case=case):
                fixture = self.fixture('prefix')
                if case == 'overclaim':
                    fixture.proof['actor_publication'] = True
                elif case == 'host_mismatch':
                    fixture.proof['checks']['asan']['checks'] += 1
                elif case == 'fixture':
                    (fixture.artifacts / 'android/prefix_fixtures.h').write_text('mutated')
                elif case == 'receipt':
                    fixture.proof['android']['arm64-v8a']['expected_native_result']['checks'] += 1
                else:
                    fixture.proof['android']['arm64-v8a']['executed'] = True
                fixture.write()
                code, result, fake = fixture.execute(case)
                self.assertEqual(code, 1)
                self.assertFalse(fake.commands)
                self.assertIs(result['android_executed'], False)

    def test_source_drift_before_execution(self):
        fixture = self.fixture('ranges')
        path = fixture.repo / 'native-android/engine/entities/coh_power_ranges.c'
        path.write_text(path.read_text() + '\n/* drift */\n')
        code, result, fake = fixture.execute('source_drift')
        self.assertEqual(code, 1)
        self.assertFalse(fake.commands)
        self.assertIs(result['android_executed'], False)

    def test_driver_mutation_cannot_be_admitted_by_repinning(self):
        fixture = self.fixture('prefix')
        path = fixture.repo / runner.RUNNER_PATH
        path.write_text(path.read_text() + '\n# synthetic changed driver\n')
        fixture.git('add', '.')
        fixture.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'driver mutation')
        fixture.refresh_source_state()
        fixture.sources[runner.RUNNER_PATH] = runner.c.digest(path)
        for receipt in fixture.proof['android'].values():
            receipt['source_revision'] = fixture.proof['source_revision']
            receipt['source_tree'] = fixture.proof['source_tree']
        fixture.write()
        code, result, fake = fixture.execute('driver_mutation')
        self.assertEqual(code, 1)
        self.assertIn('Running Android driver', result['errors']['execution'])
        self.assertFalse(fake.commands)

    def test_cleanup_failure_cannot_be_an_acceptance(self):
        for case in ('cleanup_failure', 'cleanup_verify_failure'):
            with self.subTest(case=case):
                code, result, _ = self.fixture('ranges').execute(case)
                self.assertEqual(code, 1)
                self.assertIs(result['android_executed'], True)
                self.assertIs(result['native_match'], True)
                self.assertIs(result['passed'], False)
                self.assertIs(result['emulator_qualified'], False)
                self.assertIs(result['temporary_files_removed'], False)
                self.assertIn('cleanup', result['errors'])

    def test_attempt_execution_match_are_separate(self):
        for case, attempted, executed, matched in (
                ('wrong_device', False, False, False),
                ('push_mutation', False, False, False),
                ('command_failure', True, False, False),
                ('timeout', True, False, False),
                ('native_overclaim', True, False, False),
                ('native_mismatch', True, True, False)):
            with self.subTest(case=case):
                code, result, _ = self.fixture('prefix').execute(case)
                self.assertEqual(code, 1)
                self.assertIs(result['device_test_command_attempted'], attempted)
                self.assertIs(result['android_executed'], executed)
                self.assertIs(result['native_match'], matched)
                self.assertIs(result['passed'], False)
                if case == 'command_failure':
                    self.assertEqual(result['device_test_command_exit_code'], 126)

    def test_source_drift_after_native_result(self):
        code, result, _ = self.fixture('ranges').execute('source_drift_during')
        self.assertEqual(code, 1)
        self.assertIs(result['android_executed'], True)
        self.assertIs(result['native_match'], True)
        self.assertIs(result['emulator_qualified'], False)
        self.assertIs(result['temporary_files_removed'], True)

    def test_bounded_command_decode(self):
        with tempfile.TemporaryDirectory(prefix='coh-wire-output-limit-') as tmp:
            with self.assertRaisesRegex(ValueError, 'output exceeds'):
                runner.adapter.bounded_execute([sys.executable, '-c', 'print("x" * (1024*1024+1))'], Path(tmp) / 'large.log', timeout=10)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DriverControls)
    with contextlib.redirect_stdout(io.StringIO()):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    receipt = {'passed': result.wasSuccessful(), 'test_methods': result.testsRun,
               'failures': len(result.failures), 'errors': len(result.errors),
               'scope': 'synthetic command-executor and ELF-header controls only',
               'android_executed': False, 'emulator_qualified': False,
               'actor_publication': False, 'acknowledgments_enabled': False}
    print(json.dumps(receipt))
    if not result.wasSuccessful():
        for test, error in result.failures + result.errors:
            print(str(test) + '\n' + error, file=sys.stderr)
        raise SystemExit(1)
