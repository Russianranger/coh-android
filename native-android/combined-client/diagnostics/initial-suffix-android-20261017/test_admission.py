"""Authored ELF identity fixtures test admission only; no Android execution."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import run as driver
from prepare import HERE, ROOT, sha


class AdmissionTests(unittest.TestCase):
    def fixture(self, root):
        host = json.loads((ROOT / 'native-android/combined-client/evidence/20261017/emergency-recovery/integrated-suffix-2cdb/host-proof.json').read_text())
        (root / 'host.json').write_text(json.dumps(host))
        (root / 'fixtures.h').write_text('authored fixture identity; not compiled\n')
        host['fixtures_sha256'] = sha(root / 'fixtures.h')
        (root / 'host.json').write_text(json.dumps(host))
        sources = {**host['source_sha256'], **host['provider_sha256']}
        for name in ('prepare.py', 'run.py'):
            path = HERE / name
            sources[path.relative_to(ROOT).as_posix()] = sha(path)
        path = ROOT / 'native-android/engine/entities/run_character_android.py'
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
        package = dict(schema='coh-initial-suffix-android-package-v1', passed=True,
                       actor_publication=False, acknowledgments_enabled=False,
                       android_executed=False, physical_thor=False,
                       host_sha256=sha(root / 'host.json'), source_sha256=sources,
                       source_revision=host['source_revision'],
                       fixture_sha256=host['fixtures_sha256'], builds={})
        for abi, machine in [('arm64-v8a', 183), ('x86_64', 62)]:
            directory = root / abi
            directory.mkdir()
            binary = directory / 'coh_initial_suffix_test'
            header = bytearray(64)
            header[:6] = b'\x7fELF\x02\x01'
            struct.pack_into('<H', header, 18, machine)
            binary.write_bytes(header)
            build = dict(built=True, executed=False, abi=abi, api=26, machine=machine,
                         compiler_sha256='0' * 64, binary_sha256=sha(binary),
                         fixture_sha256=host['fixtures_sha256'],
                         linked_android_platform_zlib=True,
                         external_dependency_stack_and_sanitizer_closure=False)
            (directory / 'build.json').write_text(json.dumps(build))
            package['builds'][abi] = build
        (root / 'package.json').write_text(json.dumps(package))
        return package

    def test_complete_authored_identity_fixture_admitted(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self.fixture(root)
            expected, binaries = driver.admit(root)
            self.assertEqual(expected['checks'], 9991)
            self.assertEqual(set(binaries), {'arm64-v8a', 'x86_64'})

    def test_mutations_refuse(self):
        mutations = [lambda p: p.update(actor_publication=True),
                     lambda p: p.update(android_executed=True),
                     lambda p: p['builds'].pop('arm64-v8a'),
                     lambda p: p['source_sha256'].pop('native-android/engine/initial-suffix/coh_initial_suffix.c'),
                     lambda p: p.update(host_sha256='0' * 64),
                     lambda p: p.update(fixture_sha256='0' * 64)]
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                package = self.fixture(root)
                mutation(package)
                (root / 'package.json').write_text(json.dumps(package))
                with self.assertRaises(ValueError):
                    driver.admit(root)

    def test_changed_binary_refuses(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self.fixture(root)
            (root / 'x86_64/coh_initial_suffix_test').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                driver.admit(root)

    def test_contradictory_host_scope_refuses(self):
        for key in ('whole_initial_update_complete', 'actor_publication', 'acknowledgments_enabled', 'dependency_stack_and_sanitizer_closure'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as name:
                root = Path(name)
                package = self.fixture(root)
                host = json.loads((root / 'host.json').read_text())
                host[key] = True
                (root / 'host.json').write_text(json.dumps(host))
                package['host_sha256'] = sha(root / 'host.json')
                (root / 'package.json').write_text(json.dumps(package))
                with self.assertRaisesRegex(ValueError, 'host authority'):
                    driver.admit(root)

    def test_mkdir_error_still_removes_owned_uuid_path(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            command = Mock(side_effect=['33', 'x86_64', '1', ValueError('partial mkdir'), '', ''])
            output = root / 'execution/receipt.json'
            arguments = ['run.py', '--artifacts', str(root), '--output', str(output),
                         '--adb', '/fake/adb', '--serial', 'emulator-5554']
            with patch.object(driver, 'helper', return_value=SimpleNamespace(command=command)), \
                 patch.object(driver, 'admit', return_value=({}, {})), \
                 patch('sys.argv', arguments), patch('builtins.print'):
                self.assertEqual(driver.main(), 1)
            result = json.loads(output.read_text())
            self.assertTrue(result['temporary_files_removed'])
            self.assertFalse(result['native_execution_attempted'])
            self.assertEqual(command.call_count, 6)
            commands = [row.args[0] for row in command.call_args_list]
            self.assertEqual(commands[-2][-3:-1], ['rm', '-rf'])
            self.assertEqual(commands[-1][-3:-1], ['!', '-e'])


if __name__ == '__main__':
    unittest.main()
