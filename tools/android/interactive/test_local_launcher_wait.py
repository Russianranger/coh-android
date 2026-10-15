"""Execute the native wait guard and verify its isolated local Atlas wiring."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
sys.path.insert(0, str(ROOT / 'android/guest'))
import package_startup_dbserver as supplement
if os.name != 'nt':
    # The guest service intentionally targets Linux/Android and imports fcntl.
    # MSVC qualification exercises the actual Win32 C guard independently.
    import local_character_server as character
    import local_login_server as login
from test_package_reference_runtime import pe_file

SESSION = '0123456789abcdef0123456789abcdef'
MANUAL_ATLAS_ENVIRONMENT = supplement.launcher_wait_contract()['environment_variable']
MANUAL_ATLAS_ACK = supplement.launcher_wait_contract()['startup_acknowledgement']


def staged_base(directory):
    wine = supplement.wine
    expected = wine.expected_wine_receipt()
    pg = expected['postgresql_build_input']
    for name in set(wine.WINE_FILES).union(pg['patched_sha256']):
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'upstream/ouroboros' / name, target)
    wine.apply_patch(directory, (ROOT / 'patches/postgresql/0001-dbserver-postgresql.patch')
                     .read_bytes().replace(b'\r\n', b'\n'))
    for name in pg['overlay_sha256']:
        target = directory / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'database/postgresql/overlay' / name, target)
    (directory / 'postgresql-build-input.json').write_text(json.dumps(pg))
    return wine.apply_wine_overlay(directory)


class SourceScopeTests(unittest.TestCase):
    def test_only_dbserver_wait_and_target_are_changed_from_exact_wine_stage(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            base = staged_base(source)
            before = {name: supplement.wine.sha256(source / name)
                      for name in dict(base['patched_sha256'], **base['wine_overlay_sha256'])}
            receipt = supplement.apply_overlay(source)
            self.assertEqual(receipt, supplement.expected_receipt(base_wine_build_input=base))
            self.assertEqual(json.loads((source / supplement.wine.RECEIPT).read_text()), base)
            for name, digest in before.items():
                if name not in supplement.PATCHED_FILES:
                    self.assertEqual(supplement.wine.sha256(source / name), digest)
            text = (source / 'DBServer/src/dbinit.c').read_text()
            init = text.split('void dbInit(int start_static)', 1)[1].split('int main(int argc,char **argv)', 1)[0]
            self.assertLess(init.index('launcherCommInit();'), init.index('cohDbManualAtlasLauncherWait('))
            self.assertLess(init.index('cohDbManualAtlasLauncherWait('), init.index('while(!skip_launcher_wait'))
            for preserved in ('F32 minTimeToWait=15;', 'serverAutoStartInit();',
                              'containerListLoadFile(map_list);', 'sqlFifoFinish();'):
                self.assertIn(preserved, init)
            self.assertEqual(receipt['launcher_wait'], supplement.launcher_wait_contract())
            if os.name != 'nt':
                self.assertEqual(receipt['launcher_wait'], character.manual_atlas_wait_contract())
            self.assertIn('cohDbProgressMark(COH_DB_STAGE_READY);', text)
            self.assertIn('cohDbProgressMark(COH_DB_STAGE_LOOP_DONE);', text)

    def test_changed_baseline_and_existing_overlay_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            staged_base(source)
            (source / 'DBServer/src/wine_loopback.c').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Base Wine source changed'):
                supplement.apply_overlay(source)

    def test_fixture_or_non_win32_cache_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary) / 'CMakeCache.txt'
            for text in ('COH_PG_PERSISTENCE_TESTS:BOOL=ON\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n',
                         'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=x64\n'):
                cache.write_text(text)
                with self.assertRaises(ValueError):
                    supplement.validate_cache(cache)

    def test_donor_pg_byte_profile_is_reproduced_before_supplement_without_relabeling(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            staged_base(source)
            path = ROOT / 'docs/android-evidence/dbserver-package-36460867428.json'
            donor = supplement.qualified_base_manifest(path)['wine_build_input']
            self.assertEqual(supplement.align_base_profile(source, path), donor)
            receipt = supplement.apply_overlay(source)
            self.assertEqual(receipt['base_wine_build_input'], donor)
            for name, digest in donor['postgresql_build_input']['overlay_sha256'].items():
                self.assertEqual(supplement.wine.sha256(source / name), digest)

    def test_package_verifies_actual_pe_imports_and_retained_donor_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = root / 'source'; source.mkdir()
            staged_base(source)
            base_manifest = ROOT / supplement.ACCEPTED_BASE_MANIFEST
            supplement.align_base_profile(source, base_manifest)
            supplement.apply_overlay(source)
            image = bytearray(pe_file(('odbc32.dll',)))
            image.extend(b'\0' * (4608 - len(image)))
            struct.pack_into('<4I', image, 152 + 224 + 8, 4096, 0x1000, 4096, 512)
            struct.pack_into('<I', image, 512, 0x1200)
            for index, name in enumerate(supplement.wine.REQUIRED_IMPORTS):
                rva = 0x1500 + index * 64
                struct.pack_into('<I', image, 1024 + index * 4, rva)
                offset = rva - 0x1000 + 512
                image[offset:offset + len(name) + 3] = b'\0\0' + name.encode() + b'\0'
            binary = root / 'DbServer.exe'; binary.write_bytes(image)
            cache = root / 'CMakeCache.txt'
            cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n')
            args = SimpleNamespace(source=source, binary=binary, cache=cache, base_manifest=base_manifest,
                                   output=root / 'package', repository_commit='a' * 40)
            manifest = supplement.package(args)
            self.assertEqual(supplement.validate_package(args.output, args.repository_commit), manifest)
            self.assertEqual(set(manifest['files']), {'DbServer.exe'})
            self.assertFalse(manifest['base_package_archive_changed'])
            path = args.output / supplement.MANIFEST
            manifest['base_normal_cmake_cache_sha256'] = 'f' * 64
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'relabeled the qualified donor'):
                supplement.validate_package(args.output, args.repository_commit)


class NativeManualWaitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('cl' if os.name == 'nt' else 'cc')
        if compiler is None:
            raise RuntimeError('A C compiler is required for the native Launcher wait contract')
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-launcher-wait-native-')
        cls.directory = Path(cls.temporary.name)
        source = cls.directory / 'source'
        source.mkdir()
        staged_base(source)
        supplement.apply_overlay(source)
        text = (source / 'DBServer/src/dbinit.c').read_text()
        predicate = re.search(r'while\((!skip_launcher_wait[^\n]+)\)', text).group(1)
        harness = ('#include <windows.h>\n#include <stdio.h>\n#include <stdlib.h>\n'
            '#include "wine_manual_atlas.h"\nDWORD coh_test_error;\n'
            'static float clock_seconds;\nstatic float timerElapsed(int timer) { (void)timer; return clock_seconds; }\n'
            'static int launcherCountStaticMapLaunchers(void) { return 0; }\n'
            'static int waitAt(int skip_launcher_wait, float seconds) { int timer=1; '
            'float minTimeToWait=15, minTimeToWaitPerLauncher=3; int minStaticMapLaunchers=1; '
            'clock_seconds=seconds; return ' + predicate + '; }\n'
            'int main(int argc,char **argv) { int status; DWORD error; if(argc!=8)return 2; '
            'status=cohDbManualAtlasLauncherWait(atoi(argv[1]),atoi(argv[2]),atoi(argv[3]),'
            'atoi(argv[4]),atoi(argv[5]),atoi(argv[6]),atoi(argv[7])); error=GetLastError(); '
            'printf("{\\"status\\":%d,\\"error\\":%lu,\\"wait_at_0\\":%d,\\"wait_at_14\\":%d,\\"wait_at_15\\":%d}\\n",'
            'status,error,waitAt(status==1,0),waitAt(status==1,14),waitAt(status==1,15)); return 0; }\n')
        (cls.directory / 'contract.c').write_text(harness)
        overlay = ROOT / supplement.OVERLAY / 'DBServer/src'
        cls.binary = cls.directory / ('wait-contract.exe' if os.name == 'nt' else 'wait-contract')
        if os.name == 'nt':
            command = [compiler, '/nologo', '/W4', '/WX', '/O2', '/MT', '/D_WIN32_WINNT=0x0601',
                f'/I{overlay}', str(cls.directory / 'contract.c'), str(overlay / 'wine_manual_atlas.c'),
                f'/Fe:{cls.binary}']
        else:
            shutil.copyfile(ROOT / 'database/wine-dbserver/tests/loopback_portable_windows.h',
                            cls.directory / 'windows.h')
            command = [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                '-I' + str(cls.directory), '-I' + str(overlay), str(cls.directory / 'contract.c'),
                str(overlay / 'wine_manual_atlas.c'), '-o', str(cls.binary)]
        result = subprocess.run(command, cwd=cls.directory, capture_output=True, text=True, timeout=30)
        if result.returncode:
            cls.temporary.cleanup()
            raise RuntimeError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_native(self, requested='1', values=(0, 1, 0, 0, 0, 0, 0), fixed='1', loopback='1'):
        environment = {key: value for key, value in os.environ.items()
                       if key.upper() not in {MANUAL_ATLAS_ENVIRONMENT,
                            'COH_WINE_DB_FIXED_INPUTS', 'COH_WINE_DB_LOOPBACK_ONLY'}}
        for name, value in ((MANUAL_ATLAS_ENVIRONMENT, requested),
                            ('COH_WINE_DB_FIXED_INPUTS', fixed), ('COH_WINE_DB_LOOPBACK_ONLY', loopback)):
            if value is not None:
                environment[name] = value
        result = subprocess.run([str(self.binary), *map(str, values)], env=environment,
                                capture_output=True, text=True, check=True, timeout=10)
        lines = [line for line in result.stdout.splitlines() if line]
        self.assertEqual(result.stderr, '')
        return json.loads(lines[-1]), lines[:-1]

    def test_unrequested_default_still_waits_fifteen_seconds(self):
        for values in ((0, 1, 0, 0, 0, 0, 0), (12, 0, 1, 1, 2, 3, 1)):
            result, markers = self.run_native(None, values, None, None)
            self.assertEqual(result['status'], 0)
            self.assertEqual([result['wait_at_0'], result['wait_at_14'], result['wait_at_15']], [1, 1, 0])
            self.assertEqual(markers, [])

    def test_exact_local_manual_atlas_request_skips_only_actual_wait_predicate(self):
        result, markers = self.run_native()
        self.assertEqual(result['status'], 1)
        self.assertEqual([result['wait_at_0'], result['wait_at_14'], result['wait_at_15']], [0, 0, 0])
        self.assertEqual(markers, [MANUAL_ATLAS_ACK])

    def test_every_unsafe_configuration_or_malformed_request_is_refused(self):
        cases = [{'requested': value} for value in ('', '0', '01', ' 1', '1 ', 'true', '1' * 4096)]
        for index, replacement in enumerate((-1, 0, 1, 1, 1, 1, 1)):
            values = list((0, 1, 0, 0, 0, 0, 0)); values[index] = replacement
            cases.append({'values': values})
        cases.extend([{'values': [12, 1, 0, 0, 0, 0, 0]}, {'fixed': None}, {'fixed': '0'},
                      {'loopback': None}, {'loopback': '01'}])
        for case in cases:
            with self.subTest(case=case):
                result, markers = self.run_native(**case)
                self.assertEqual(result['status'], -1)
                self.assertEqual(result['error'], 87)
                self.assertEqual(markers, [])


class GuestManualWaitTests(unittest.TestCase):
    def test_local_login_removes_inherited_request_and_unsupplemented_atlas_stays_default(self):
        stock = login.LocalLoginServer.__new__(login.LocalLoginServer)
        local = character.LocalCharacterServer.__new__(character.LocalCharacterServer)
        local.manual_atlas_startup = None
        for service in (stock, local):
            self.assertEqual(service.dbserver_environment({character.MANUAL_ATLAS_ENVIRONMENT: '1', 'OTHER': 'yes'}),
                             {'OTHER': 'yes'})
            self.assertTrue(service.dbserver_startup_policy_ready(''))
        local.manual_atlas_startup = {'native_ack_observed': False}
        self.assertEqual(local.dbserver_environment({}), {character.MANUAL_ATLAS_ENVIRONMENT: '1'})
        self.assertFalse(local.dbserver_startup_policy_ready('DbServer Ready.'))
        self.assertFalse(local.dbserver_startup_policy_ready(character.MANUAL_ATLAS_ACK))
        self.assertTrue(local.dbserver_startup_policy_ready(character.MANUAL_ATLAS_ACK + '\r\n'))
        self.assertTrue(local.manual_atlas_startup['native_ack_observed'])
        for console in (character.MANUAL_ATLAS_ACK + '\nWaiting for launchers to link up...',
                        character.MANUAL_ATLAS_ACK + '\n' + character.MANUAL_ATLAS_ACK + '\n'):
            with self.assertRaises(login.base.DiagnosticError):
                local.dbserver_startup_policy_ready(console)

    def test_native_ack_does_not_replace_dispatch_progress_or_listener_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            service = character.LocalCharacterServer.__new__(character.LocalCharacterServer)
            context = SimpleNamespace(report={}, deadline=1000, stage=Mock(), passed=Mock(), event=Mock(),
                check=Mock(), run=Mock(return_value={'output': 'driver'}), start=Mock())
            service.ctx = context
            service.owner = SimpleNamespace(args=SimpleNamespace(assets=root, wine='wine', session_id=SESSION),
                root=root, wineprefix=root, wine_env={}, credentials={'cohtest': 'secret'}, port=5432)
            service.runtime = root
            (root / 'data/server/db').mkdir(parents=True)
            (root / 'data/server/db/servers.cfg').write_text('config')
            service.package = {'wine_build_input': {'dispatch_progress': {'stages': {}}, 'normal_schema_listeners': {}}}
            service.report = {}
            service.manual_atlas_startup = {'native_ack_observed': False}
            service.prepare_runtime = Mock(); service.health = Mock()
            service.schema_snapshot = Mock(return_value={'schema': 'verified'})
            context.start.return_value = SimpleNamespace(text=Mock(return_value=character.MANUAL_ATLAS_ACK + '\n'))
            with patch.object(login.base, 'verify_pe32'), patch.object(login.base, 'private_write'), \
                 patch.object(login.base, 'validate_odbc_driver', return_value={'driver_name': 'odbc'}), \
                 patch.object(login.game, 'game_config', return_value='cfg'), \
                 patch.object(login.game, 'check_game_port'), \
                 patch.object(login.game, 'fixed_inputs_acknowledgement', side_effect=[False, True, True]), \
                 patch.object(login.game, 'loopback_acknowledgement', side_effect=[True, True, True]), \
                 patch.object(login.dbserver, 'loopback_expectations', return_value=[]), \
                 patch.object(login.dispatch, 'read_dispatch_record', side_effect=[{'loop_count': 0}, {'loop_count': 1}]) as progress_read, \
                 patch.object(login.time, 'monotonic', return_value=0), patch.object(login.time, 'sleep') as sleeping:
                login.LocalLoginServer.start(service)
            self.assertEqual(sleeping.call_count, 2)
            self.assertEqual(progress_read.call_count, 2)
            self.assertTrue(service.report['server_ready'])
            self.assertEqual(service.report['dispatch_progress']['loop_count'], 1)
            self.assertEqual(context.start.call_args.kwargs['env'][character.MANUAL_ATLAS_ENVIRONMENT], '1')
            self.assertTrue(service.manual_atlas_startup['native_ack_observed'])

    def test_supplement_install_replaces_only_fresh_executable_and_rejects_changed_donor(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); assets = root / 'assets'; runtime = root / 'runtime'
            assets.mkdir(); runtime.mkdir()
            self.assertIsNone(character.install_manual_atlas_dbserver(assets, runtime, {}))
            package = json.loads((ROOT / 'docs/android-evidence/dbserver-package-36460867428.json').read_text())
            package = copy.deepcopy(package)
            original = b'accepted donor executable'
            package['variants']['normal']['files'] = {'DbServer.exe': {'sha256': hashlib.sha256(original).hexdigest()},
                'retained.dll': {'sha256': hashlib.sha256(b'donor library').hexdigest()}}
            (runtime / 'DbServer.exe').write_bytes(original)
            (runtime / 'retained.dll').write_bytes(b'donor library')
            image = pe_file(('KERNEL32.dll',))
            (assets / 'startup-dbserver.exe').write_bytes(image)
            normal = package['variants']['normal']
            manifest = {'format': 1, 'role': 'manual_atlas_dbserver_startup_supplement', 'repository_commit': 'a' * 40,
                'source_commit': package['source_commit'], 'base_package_manifest_sha256': login.dbserver.DEVICE_PACKAGE_MANIFEST,
                'replacement_scope': 'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
                'base_package_archive_changed': False, 'architecture': 'Win32', 'configuration': 'OptDebug',
                'postgresql_persistence_fixture': False, 'android_execution_validated': False, 'gameplay_validated': False,
                'retained_normal_files': {'retained.dll': normal['files']['retained.dll']},
                'base_normal_executable': normal['files']['DbServer.exe'],
                'base_normal_cmake_cache_sha256': normal['cmake_cache_sha256'],
                'build_input': supplement.expected_receipt(base_wine_build_input=package['wine_build_input']),
                'files': {'DbServer.exe': {'bytes': len(image), 'sha256': hashlib.sha256(image).hexdigest()}},
                'dependency_report': {'unresolved': []}, 'odbc_imports': list(supplement.wine.REQUIRED_IMPORTS)}
            manifest_path = assets / 'startup-dbserver-manifest.json'
            manifest_path.write_text(json.dumps(manifest))
            (runtime / 'retained.dll').write_bytes(b'changed library')
            with self.assertRaisesRegex(login.base.DiagnosticError, 'retained runtime library differs'):
                character.install_manual_atlas_dbserver(assets, runtime, package)
            self.assertEqual((runtime / 'DbServer.exe').read_bytes(), original)
            (runtime / 'retained.dll').write_bytes(b'donor library')
            result = character.install_manual_atlas_dbserver(assets, runtime, package)
            self.assertTrue(result['enabled'])
            self.assertEqual((runtime / 'DbServer.exe').read_bytes(), image)
            self.assertEqual((runtime / 'retained.dll').read_bytes(), b'donor library')
            with self.assertRaisesRegex(login.base.DiagnosticError, 'fresh accepted DbServer'):
                character.install_manual_atlas_dbserver(assets, runtime, package)


if __name__ == '__main__':
    if '--require-windows' in sys.argv:
        sys.argv.remove('--require-windows')
        if os.name != 'nt' or not shutil.which('cl'):
            raise SystemExit('Launcher wait contracts require an initialized x86 MSVC environment')
    unittest.main(verbosity=2, defaultTest=['SourceScopeTests', 'NativeManualWaitTests'] if os.name == 'nt' else None)
