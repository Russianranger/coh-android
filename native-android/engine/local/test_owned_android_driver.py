"""Synthetic artifact admission controls; never execute a native binary or adb."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import types
import unittest

SOURCE = Path(__file__).with_name('run_owned_android.py')
RAW = SOURCE.read_bytes()
DRIVER = types.ModuleType('frozen_android_driver')
DRIVER.__file__ = str(SOURCE)
exec(compile(RAW, str(SOURCE), 'exec'), DRIVER.__dict__)


class Admission(unittest.TestCase):
    def test_artifacts(self):
        with tempfile.TemporaryDirectory(prefix='coh-owned-driver-') as td:
            root = Path(td)
            (root / 'android').mkdir()
            rows = []
            fixture_map = {n: '0' * 64 for n in ('fixtures.h', 'groups-fixtures.h', 'server-command-fixtures.h')}
            for abi, machine in (('x86_64', 62), ('arm64-v8a', 183)):
                raw = b'\x7fELF\x02\x01' + b'\0' * 12 + struct.pack('<H', machine) + b'\0' * 44
                name = 'coh-local-' + abi
                (root / 'android' / name).write_bytes(raw)
                rows.append(dict(abi=abi, file=name, built=True, executed=False,
                                 sha256=hashlib.sha256(raw).hexdigest(), fixture_sha256=fixture_map))
            expected = dict(passed=True, checks=10, socket_scenarios=9, actual_os_udp=True,
                            full_scripted_db_map_chain=True, source_layout_peer=True,
                            socket_leak_check=True, real_server_interoperability=False,
                            real_authenticated_session=False, native_live_world=False)
            host = dict(passed=True, controls_only=False, source_loader_controls=5,
                        project_helpers_frozen_before_first_import=True, cached_project_bytecode_used=False,
                        checked_helpers=['native-android/engine/local/run_owned_android.py',
                            'native-android/engine/dbclient/check.py', 'native-android/engine/mapclient/check.py',
                            'native-android/engine/replication/check.py', 'native-android/engine/replication/groups_oracle.py',
                            'native-android/tools/protocol_fixture/prepare.py'],
                        **DRIVER.source_identity(SOURCE.resolve().parents[3]),
                        integrated=dict(passed=True, sanitizers='ASan+UBSan', fixture_sha256=fixture_map,
                            implementation_sha256={n: DRIVER.source_identity(SOURCE.resolve().parents[3])['source_sha256']['native-android/' + n]
                                for n in ('engine/local/coh_local.c', 'engine/local/coh_local.h', 'engine/local/check.py',
                                          'engine/local/test_local.c', 'engine/dbclient/coh_db_session.c', 'engine/dbclient/coh_db_account_controls.c',
                                          'engine/mapclient/coh_mapclient.c', 'engine/mapclient/coh_mapclient_owned.c')},
                            checks=dict(release=expected, asan=expected, ubsan=expected), android=dict(artifacts=rows)))
            build = dict(module='local', artifacts=rows)
            def write(h=host, b=build):
                (root / 'host.json').write_text(json.dumps(h))
                (root / 'android/android-build.json').write_text(json.dumps(b))
            write()
            self.assertEqual(DRIVER.validate(root)[1], expected)
            for key, value in (('passed', False), ('controls_only', True)):
                changed = json.loads(json.dumps(host)); changed[key] = value; write(changed)
                with self.assertRaises(ValueError): DRIVER.validate(root)
            for key, value in (('source_revision', '0' * 40), ('source_tree', '0' * 40),
                               ('source_sha256', {}), ('source_loader_controls', 0),
                               ('project_helpers_frozen_before_first_import', False),
                               ('cached_project_bytecode_used', True), ('checked_helpers', [])):
                changed = json.loads(json.dumps(host)); changed[key] = value; write(changed)
                with self.assertRaises(ValueError): DRIVER.validate(root)
            changed = json.loads(json.dumps(host)); del changed['integrated']['fixture_sha256']; write(changed)
            with self.assertRaises(ValueError): DRIVER.validate(root)
            for key, value in (('passed', False), ('sanitizers', 'not requested'),
                               ('implementation_sha256', {}), ('checks', dict(release=expected))):
                changed = json.loads(json.dumps(host)); changed['integrated'][key] = value; write(changed)
                with self.assertRaises(ValueError): DRIVER.validate(root)
            changed = json.loads(json.dumps(host)); changed['integrated']['checks']['ubsan']['checks'] += 1; write(changed)
            with self.assertRaises(ValueError): DRIVER.validate(root)
            changed = json.loads(json.dumps(host)); changed['integrated']['implementation_sha256']['engine/local/coh_local.c'] = '0' * 64; write(changed)
            with self.assertRaises(ValueError): DRIVER.validate(root)
            with self.assertRaises(ValueError): DRIVER.native_source_paths(root, [b'native-android/missing.c'])
            for key in ('real_server_interoperability', 'real_authenticated_session', 'native_live_world'):
                changed = json.loads(json.dumps(host)); changed['integrated']['checks']['release'][key] = True; write(changed)
                with self.assertRaises(ValueError): DRIVER.validate(root)
            write()
            original = (root / 'android/coh-local-x86_64').read_bytes()
            (root / 'android/coh-local-x86_64').write_bytes(original + b'x')
            with self.assertRaises(ValueError): DRIVER.validate(root)
            (root / 'android/coh-local-x86_64').write_bytes(original)
            for field, value in (('abi', 'arm64-v8a'), ('file', '../outside'), ('executed', True), ('built', False), ('fixture_sha256', {})):
                changed = json.loads(json.dumps(build)); changed['artifacts'][0][field] = value; write(host, changed)
                with self.assertRaises(ValueError): DRIVER.validate(root)
            write()
            self.assertEqual(DRIVER.validate(root)[0].name, 'coh-local-x86_64')
            self.assertEqual(SOURCE.read_bytes(), RAW)


if __name__ == '__main__':
    unittest.main()
