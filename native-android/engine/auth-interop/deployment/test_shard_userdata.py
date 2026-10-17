import copy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import shard_userdata_fixture as fixture
import hosted_shard_userdata as stage

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def valid_result():
    keys = ('passed sql_connected shard_sql_loaded source_address_lookup unknown_address_refused '
            'full_auth_sql_to_wire full_game_sql_to_wire missing_userdata_guard null_userdata_guard '
            'source_missing_userdata_zero_filled source_game_missing_zero_filled source_queue_disabled').split()
    value = dict.fromkeys(keys, True)
    value.update(schema='coh-original-shard-userdata-odbc-v1', pointer_bytes=4, source_sql_errors=0,
                 network_registration_verified=False, authentication_grant_generated=False,
                 authenticated_db_map_handoff_verified=False)
    return value


class ShardUserdataTests(unittest.TestCase):
    def test_exact_original_source_and_fixture_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            proof = fixture.prepare(ROOT, directory)
            source = (directory / 'original-shard-userdata.cpp').read_text()
            values, identities = fixture.inputs(ROOT)
            self.assertEqual(proof['source_sha256'], identities)
            for filename, name in (
                    ('ServerList.cpp', 'CServerList::Load'),
                    ('AccountDB.cpp', 'AccountDB::AboutToPlay'),
                    ('CSocketServer.cpp', 'ServerReadGameData')):
                original = fixture.exact_function(values[fixture.AUTH + filename], name)
                self.assertEqual(source.count(original), 1)
                self.assertEqual(proof['function_sha256'][name], fixture.sha(original.encode()))
            sql = fixture.fixture_sql()
            self.assertIn(bytes(range(16)).hex(), sql)
            self.assertIn(bytes(range(16,128)).hex(), sql)
            self.assertIn(bytes(255-i for i in range(16)).hex(), sql)
            self.assertNotIn('user_auth', sql)
            self.assertNotIn('password', sql)
            self.assertFalse(proof['network_registration_verified'])

    def test_scope_mutations_and_smallint_port(self):
        good = valid_result()
        self.assertEqual(fixture.admit_result(good), good)
        for key in good:
            bad = copy.deepcopy(good)
            if type(bad[key]) is bool:
                bad[key] = not bad[key]
            elif type(bad[key]) is int:
                bad[key] = True
            else:
                bad[key] = 'wrong'
            with self.subTest(key=key), self.assertRaises(ValueError):
                fixture.admit_result(bad)
        for port in (True, 19999, 32768, 65535, '23000'):
            with self.assertRaises(ValueError): fixture.fixture_sql(port)

    def test_host_original_bodies_with_explicit_synthetic_sql_api(self):
        # This host-only shim checks original control flow and generated fixture
        # comparisons. It deliberately does not qualify SQL, ODBC or x86 ABI.
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            fixture.prepare(ROOT, directory)
            generated = directory / 'original-shard-userdata.cpp'
            source = generated.read_text()
            for header in ('winsock2.h', 'windows.h', 'sql.h', 'sqlext.h'):
                source = source.replace('#include <' + header + '>', '')
            source = source.replace('static_assert(sizeof(void*) == 4, "actual x86 ODBC required");', '')
            source = '#include "test_userdata_host_api.h"\n' + source
            generated.write_text(source)
            for mode, flags in (('release', ['-O2']), ('asan_ubsan', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-pie', '-no-pie'])):
                binary = directory / mode
                build = subprocess.run(['c++', '-std=c++17', *flags, '-I', str(HERE), generated, '-o', binary],
                                       capture_output=True, text=True, timeout=60)
                self.assertEqual(build.returncode, 0, build.stderr)
                result = subprocess.run([binary, 'cohauth-ci-' + 'a'*24, 'ODBC Driver 17 for SQL Server'],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, GITHUB_ACTIONS='true', RUNNER_ENVIRONMENT='github-hosted',
                             ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1'))
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                value = json.loads(result.stdout)
                self.assertEqual(value['pointer_bytes'], 8)
                self.assertTrue(value['passed'])
                # A successful host shim must never pass actual x86 admission.
                with self.assertRaises(ValueError): fixture.admit_result(value)

    def test_disposable_stage_orchestration_and_cleanup(self):
        # API calls are mocked here; Windows/SQL acceptance comes only from the
        # real stage receipt. This verifies new build ordering and every cleanup.
        @dataclass(frozen=True)
        class Prerequisite:
            fresh_authentication_required: bool = True
            authenticated_db_map_handoff_verified: bool = False
        for broken in (None, 'load-shard-userdata-fixture', 'original-shard-userdata'):
            with self.subTest(broken=broken), tempfile.TemporaryDirectory() as temp:
                base = Path(temp);calls=[]
                args = type('Args', (), dict(source_root=ROOT, expected_commit='a'*40,
                    output=base/'output', auth_success_archive=base/'unused.zip'))()
                class Commands:
                    def __init__(self, output): self.output=output;self.records=[]
                    def run(self, name, argv, **kwargs):
                        calls.append(name)
                        self.records.append({'name':name})
                        if name == broken: raise ValueError('test_controlled_failure')
                        if name == 'build-shard-userdata':
                            build=Path(argv[2]);(build/'Release').mkdir(parents=True)
                            (build/'Release/original-shard-userdata.exe').write_bytes(b'public-test-pe')
                            (build/'CMakeCache.txt').write_text('public-test-cache')
                        if name == 'original-shard-userdata':
                            (self.output/(name+'.log')).write_text(json.dumps(valid_result()))
                        return 0
                class SQL:
                    def __init__(self, records, private): self.records=records
                    def run(self, name, argv, **kwargs):
                        calls.append(name);self.records.append({'name':name})
                        if name == broken: raise ValueError('test_controlled_failure')
                        return 0
                    def numeric(self, name, argv, kind):
                        calls.append(name);return '17.0.4025.3' if kind=='version' else 123
                def capture(argv):
                    if argv[-1] == 'HEAD':return 'a'*40
                    return ''
                with mock.patch.dict(os.environ, RUNNER_TEMP=temp), \
                     mock.patch.object(stage.prior, 'require_hosted', return_value={'repository_commit':'a'*40}), \
                     mock.patch.object(stage, 'authenticated_handoff_prerequisite', return_value=Prerequisite()), \
                     mock.patch.object(stage.service, 'tools', return_value=(Path('LocalDB.exe'),Path('SQLCMD.EXE'),{})), \
                     mock.patch.object(stage.prior, 'Commands', Commands), \
                     mock.patch.object(stage, 'RedactedCommands', SQL), \
                     mock.patch.object(stage.prior, 'pe_identity', return_value={'sha256':'b'*64}), \
                     mock.patch.object(stage.prior, 'capture', side_effect=capture), \
                     mock.patch.object(stage.auth_readiness, 'observe', return_value={'healthy':True}):
                    result=stage.run(args)
                self.assertEqual(result['passed'], broken is None)
                self.assertTrue(result['owned_localdb_cleanup_complete'])
                self.assertTrue(result['private_files_removed'])
                self.assertEqual(calls[-3:], ['localdb-drop-owned-schema','localdb-stop-owned-instance','localdb-delete-owned-instance'])
                self.assertLess(calls.index('build-shard-userdata'), calls.index('localdb-create'))
                self.assertFalse(result['real_selected_shard_play_verified'])
                self.assertFalse(result['authenticated_db_map_handoff_verified'])
                self.assertFalse(result['auth_only_login_repeated'])

    def test_nonhost_refuses_before_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'never-created'
            args=type('Args', (), dict(source_root=ROOT, expected_commit='a'*40,
                    output=output,auth_success_archive=Path(temp)/'absent.zip'))()
            with self.assertRaisesRegex(ValueError, 'fresh_github_hosted_windows_required'):
                stage.run(args)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
