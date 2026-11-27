"""0.13.74: the wineserver realpath cache (armport/wineserver) and how a session installs it.

Thor 0.13.73, launch B (20261118-170550): wineserver made 505,539 readlinkat calls for 27,423
opens, because Wine's server calls realpath() for every file it opens and glibc resolves a
path one readlink() at a time; each is two stops in PRoot. The library answers from a table
of folders it has already resolved, inside wineserver only.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest'), str(ROOT / 'armport/tests')]
import armport_client_package as package
from test_client_package import pe

SOURCE = ROOT / 'armport/wineserver'


def elf(machine=183):
    data = bytearray(64)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<HH', data, 16, 3, machine)
    return bytes(data)


class NativeLibrary(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc') and (SOURCE / 'realpath_cache.c').is_file(), 'needs a C compiler')
    def test_same_answers_as_glibc_and_only_inside_wineserver(self):
        with tempfile.TemporaryDirectory() as directory:
            library, check = Path(directory) / 'libarmport_realpath.so', Path(directory) / 'check_realpath'
            subprocess.run(['cc', '-O2', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
                            str(SOURCE / 'realpath_cache.c'), '-o', str(library)], check=True, timeout=120)
            subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror', str(SOURCE / 'check_realpath.c'),
                            '-o', str(check)], check=True, timeout=120)
            result = subprocess.run([sys.executable, str(SOURCE / 'check_realpath_native.py'), str(library),
                                     str(check)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            self.assertEqual(result.returncode, 0, result.stderr.decode()[-600:] + result.stdout.decode()[-600:])
            counters = json.loads(result.stdout.decode().splitlines()[-1])
            self.assertEqual(counters['fast'] + counters['passed'], counters['calls'])
            # 40 plain files in one deep folder and 40 links into a store, two forms, three rounds.
            self.assertGreaterEqual(counters['fast'], 480)
            self.assertLess(counters['probes'], 2 * counters['calls'])
            fuzz = subprocess.run([sys.executable, str(SOURCE / 'fuzz_realpath.py'), str(library), str(check),
                                   '74', '25'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            self.assertEqual(fuzz.stdout.decode().splitlines()[-1], 'rounds 25 different 0', fuzz.stdout.decode()[-600:])

    def test_the_source_answers_only_in_wineserver_and_only_when_asked(self):
        source = (SOURCE / 'realpath_cache.c').read_text()
        self.assertIn('!strcmp(name, "wineserver")', source)
        self.assertIn('getenv("ARMPORT_REALPATH_CACHE")', source)
        self.assertIn('dlsym(RTLD_NEXT, "realpath")', source)
        # Every component is probed unless its folder was resolved within the limit; anything
        # but "exists and is not a link" or a link with a plain target goes to glibc.
        self.assertIn('linked = readlink(out, target, sizeof target - 1);', source)
        self.assertIn('if (errno != EINVAL)\n            return 0;', source)
        self.assertIn('#define TTL_SECONDS 60', source)
        self.assertIn('remember(path, length, out, size, oldest);', source)
        build = (SOURCE / 'build.sh').read_text()
        self.assertIn('check_realpath_native.py /out/libarmport_realpath.so /out/check_realpath', build)
        self.assertIn('FROM debian:bookworm-slim', (SOURCE / 'realpath.Dockerfile').read_text())
        self.assertTrue(os.access(SOURCE / 'build.sh', os.X_OK))


class PackageMember(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client, self.bins, self.shaders = (self.root / name for name in ('client', 'bins', 'shaders'))
        for directory in (self.client, self.bins, self.shaders):
            directory.mkdir()
        for name in package.BINARIES - {'armport-launcher.exe'}:
            (self.client / name).write_bytes(pe())
        self.launcher = self.root / 'armport-launcher.exe'
        self.launcher.write_bytes(pe())
        (self.bins / 'BodyParts.bin').write_bytes(b'arm64 bins')
        (self.shaders / 'test.arb').write_bytes(b'!!ARBvp1.0\nEND\n')
        self.library = self.root / 'libarmport_realpath.so'
        self.library.write_bytes(elf())
        self.archive = self.root / 'armport.zip'

    def build(self, **extra):
        return package.package(self.client, self.bins, self.shaders, self.launcher, self.archive, 123, 122, **extra)

    def test_optional_member_is_packaged_unpacked_and_extracted_alone(self):
        document = self.build(realpath_cache=self.library)
        self.assertEqual(document['files'][package.REALPATH_CACHE]['sha256'], hashlib.sha256(elf()).hexdigest())
        package.unpack(self.archive, self.root / 'output')
        self.assertEqual((self.root / 'output' / package.REALPATH_CACHE).read_bytes(), elf())
        target = self.root / 'native/lib.so'
        target.parent.mkdir()
        member = package.extract_member(self.archive, package.REALPATH_CACHE, target)
        self.assertEqual(member, {'name': package.REALPATH_CACHE, 'size': 64, 'sha256': hashlib.sha256(elf()).hexdigest()})
        self.assertEqual(target.read_bytes(), elf())
        self.assertEqual(target.stat().st_mode & 0o777, 0o500)
        with self.assertRaisesRegex(ValueError, 'Fresh library destination'):
            package.extract_member(self.archive, package.REALPATH_CACHE, target)
        with self.assertRaisesRegex(ValueError, 'Not a native library'):
            package.extract_member(self.archive, 'CityOfHeroes.exe', self.root / 'native/exe')

    def test_a_package_without_it_and_a_wrong_machine(self):
        self.assertNotIn(package.REALPATH_CACHE, self.build()['files'])
        self.assertIsNone(package.extract_member(self.archive, package.REALPATH_CACHE, self.root / 'lib.so'))
        self.assertFalse((self.root / 'lib.so').exists())
        self.library.write_bytes(elf(62))       # x86-64
        with self.assertRaisesRegex(ValueError, 'AArch64'):
            package.package(self.client, self.bins, self.shaders, self.launcher, self.root / 'x86.zip', 123, 122,
                            realpath_cache=self.library)

    def test_a_member_that_differs_from_the_manifest_is_refused(self):
        self.build(realpath_cache=self.library)
        changed = self.root / 'changed.zip'
        with zipfile.ZipFile(self.archive) as source, zipfile.ZipFile(changed, 'w') as output:
            for info in source.infolist():
                data = source.read(info)
                if info.filename == package.REALPATH_CACHE:
                    data = data[:-1] + b'\x01'
                output.writestr(info, data)
        with self.assertRaisesRegex(ValueError, 'digest differs'):
            package.extract_member(changed, package.REALPATH_CACHE, self.root / 'lib.so')
        self.assertFalse((self.root / 'lib.so').exists())


class SessionInstall(unittest.TestCase):
    def setUp(self):
        import armport_interactive
        self.armport = armport_interactive
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        case = PackageMember('test_optional_member_is_packaged_unpacked_and_extracted_alone')
        case.setUp()
        self.addCleanup(case.temp.cleanup)
        case.build(realpath_cache=case.library)
        self.archive, self.plain = case.archive, case.root / 'plain.zip'
        package.package(case.client, case.bins, case.shaders, case.launcher, self.plain, 123, 122)

    def test_requested_installs_the_library_and_sets_the_wine_environment(self):
        environment = {'WINEPREFIX': '/x'}
        folder = self.root / 'armport-native-0123'
        record = self.armport.install_realpath_cache(self.archive, folder, environment, True)
        self.assertEqual((record['requested'], record['installed'], record['reason']), (True, True, None))
        self.assertEqual(record['sha256'], hashlib.sha256(elf()).hexdigest())
        self.assertEqual(environment, {'WINEPREFIX': '/x', 'LD_PRELOAD': str(folder / 'libarmport_realpath.so'),
                                       'ARMPORT_REALPATH_CACHE': '1',
                                       'ARMPORT_REALPATH_CACHE_REPORT': str(folder / 'report.txt')})
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)

    def test_everything_else_leaves_the_environment_alone(self):
        for label, archive, environment, requested, reason in (
                ('off', self.archive, {}, False, 'not_requested'),
                ('old package', self.plain, {}, True, 'not_in_package'),
                ('preload in use', self.archive, {'LD_PRELOAD': '/other.so'}, True, 'ld_preload_in_use'),
                ('no package', self.root / 'missing.zip', {}, True, 'error')):
            with self.subTest(label):
                before = dict(environment)
                folder = self.root / ('native-' + label.replace(' ', '-'))
                record = self.armport.install_realpath_cache(archive, folder, environment, requested)
                self.assertEqual((record['installed'], record['reason']), (False, reason))
                self.assertEqual(environment, before)
                self.assertFalse((folder / 'libarmport_realpath.so').exists())
        unsafe = self.armport.install_realpath_cache(self.archive, self.root / 'with space', {}, True)
        self.assertEqual(unsafe['reason'], 'unsafe_path')
        existing = self.root / 'existing'
        existing.mkdir()
        self.assertEqual(self.armport.install_realpath_cache(self.archive, existing, {}, True)['reason'], 'folder_exists')

    def test_counters_come_from_the_busiest_server_and_bad_files_are_skipped(self):
        folder = self.root / 'reports'
        folder.mkdir()
        self.assertEqual(self.armport.realpath_cache_counters(folder), {'servers': 0, 'counters': None})
        line = 'ARMPORT_REALPATH_CACHE_V2 calls=%d fast=%d folders=7 refreshed=1 passed=%d probes=9\n'
        (folder / 'report.txt.100').write_text(line % (50, 40, 10))
        (folder / 'report.txt.200').write_text(line % (27000, 26500, 500))
        (folder / 'report.txt.300').write_text('garbage\n')
        (folder / 'libarmport_realpath.so').write_bytes(b'x')
        self.assertEqual(self.armport.realpath_cache_counters(folder), {'servers': 2, 'counters': {
            'calls': 27000, 'fast': 26500, 'folders': 7, 'refreshed': 1, 'passed': 500, 'probes': 9}})
        self.assertEqual(self.armport.realpath_cache_counters(self.root / 'absent'), {'servers': 0, 'counters': None})

    def test_request_flag_and_wiring(self):
        self.assertTrue(self.armport.realpath_cache_requested({'COH_WINESERVER_PATH_CACHE': '1'}))
        self.assertFalse(self.armport.realpath_cache_requested({'COH_WINESERVER_PATH_CACHE': '0'}))
        self.assertFalse(self.armport.realpath_cache_requested({}))
        guest = (ROOT / 'armport/app/armport_interactive.py').read_text()
        # Installed in initialize(), which runs before start_wine() starts the first Wine process.
        install = guest.index("record = install_realpath_cache(self.args.assets / package.ARCHIVE")
        self.assertLess(guest.index('    def initialize(self):'), install)
        self.assertLess(install, guest.index('    def start_wine(self):'))
        workflow = (ROOT / '.github/workflows/armport-app-runtime.yml').read_text()
        self.assertIn('armport/wineserver/build.sh "$RUNNER_TEMP/realpath"', workflow)
        self.assertIn('--realpath-cache "$RUNNER_TEMP/realpath/libarmport_realpath.so"', workflow)
        self.assertLess(workflow.index('armport/wineserver/build.sh'), workflow.index('armport_client_package.py --client'))
        java = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
        runtime = (java / 'ClientRuntime.java').read_text()
        self.assertIn('.getBoolean("wineserver-path-cache", true)', runtime)
        self.assertIn('"COH_WINESERVER_PATH_CACHE="+(wineserverPathCacheRequested?"1":"0")', runtime)
        self.assertIn('ClientRuntime.setWineserverPathCacheEnabled(this,checked)', (java / 'ClientActivity.java').read_text())


if __name__ == '__main__':
    unittest.main()
