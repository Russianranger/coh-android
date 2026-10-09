"""Closed GPU archive policy and real ELF/version-provider regressions.

Archive-policy fixtures replace binary/build qualification explicitly; they do
not qualify a production GPU package. ELF tests compile and inspect real source
libraries and show the loader rejection that the ABI gate must also reject.
Hosted packaging independently rebuilds/inspects actual ARM64 and PE32 products.
"""
import argparse
import copy
import ctypes
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import package_client_gpu_runtime as gpu

BUILD_SPEC = importlib.util.spec_from_file_location('coh_gpu_source_builder',
    gpu.ROOT / 'tools/android/gpu-runtime/build.py')
source_build = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(source_build)

COMMIT = '1' * 40
RUN = 'https://github.com/Russianranger/coh-android/actions/runs/123456'


def write_zip(path, contents, changed_modes=None):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            entry = zipfile.ZipInfo(name)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | gpu.MODES.get(name, 0o644)) << 16
            if changed_modes and name in changed_modes:
                entry.external_attr = changed_modes[name] << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)


class ArchivePolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-gpu-policy-')
        self.directory = Path(self.temporary.name)
        self.output = self.directory / 'product'
        self.container = self.directory / 'container'; self.container.mkdir()
        self.checks = {'archive_policy_fixture_not_production': True}
        self.binary_patch = mock.patch.object(gpu, 'binary_checks', return_value=self.checks)
        self.guard_patch = mock.patch.object(gpu, 'validate_pe32_checks')
        self.helpers_patch = mock.patch.object(gpu, 'validate_pe32_helpers',
            side_effect=lambda checks, directory: gpu.pe32_helper_pins(checks))
        self.binary_patch.start(); self.guard_patch.start(); self.helpers_patch.start()
        self.addCleanup(self.binary_patch.stop); self.addCleanup(self.guard_patch.stop)
        self.addCleanup(self.helpers_patch.stop)
        self.addCleanup(self.temporary.cleanup)
        lock = gpu.lock()
        container_receipt = {'format': 1, 'architecture': 'aarch64', 'platform': 'linux',
            'debian_image': lock['debian_image'], 'mesa_options': lock['mesa_options'],
            'probe_compile_args': lock['probe_compile_args'],
            'native_probe_source_sha256': gpu.digest(gpu.ROOT / 'android/native/coh-vulkan-gpu-probe.c'),
            'compiler': 'cc (Debian 12.2.0-14) 12.2.0', 'dpkg_packages': ['fixture-policy-only=1'],
            'build_tools': {'meson': lock['meson'], 'cmake': 'cmake version ' + lock['cmake']},
            'hardware_execution_validated': False, 'performance_validated': False,
            'source_archives': {name: {'url': lock[name]['url'], 'sha256': lock[name]['sha256'],
                'bytes': lock[name].get('bytes', 3915238)} for name in ('mesa', 'glslang')}}
        (self.container / 'container-build.json').write_bytes(gpu.encoded(container_receipt))
        for name in (gpu.DRIVER, gpu.VULKAN_PROBE, gpu.NOTICES):
            (self.container / name).write_bytes(('archive-policy-only:' + name).encode())
        self.pe = self.directory / 'production.exe'
        self.pe.write_bytes(b'archive-policy-only:COH_GPU_PROBE_BUILD:production')
        self.win = self.directory / 'checks.json'; self.win.write_text('{"fixture":true}')
        gpu.package(argparse.Namespace(directory=self.container, output=self.output,
            repository_commit=COMMIT, run_url=RUN, pe32_probe=self.pe, pe32_checks=self.win))

    def validate(self):
        return gpu.validate_package(self.output, COMMIT)

    def reseal(self, receipt=None, inner=None, contents=None):
        # Recompute byte receipts only. Qualification fields remain independently
        # checked by validate_package and cannot be authorized by these hashes.
        outer = gpu.read_json(self.output / gpu.MANIFEST)
        receipt = receipt or gpu.read_json(self.output / gpu.RECEIPT)
        contents = contents or gpu.archive_contents(self.output / gpu.ARCHIVE)
        inner = inner or gpu.json_value(contents[gpu.INNER_MANIFEST])
        contents[gpu.INNER_RECEIPT] = gpu.encoded(receipt)
        inner['files'] = {name: dict(gpu.pin(contents[name]), mode=mode) for name, mode in gpu.MODES.items()}
        contents[gpu.INNER_MANIFEST] = gpu.encoded(inner)
        write_zip(self.output / gpu.ARCHIVE, contents)
        (self.output / gpu.RECEIPT).write_bytes(gpu.encoded(receipt))
        outer['files'] = {gpu.ARCHIVE: gpu.file_pin(self.output / gpu.ARCHIVE)}
        outer['hardware_manifest'] = inner; outer['source_build'] = receipt
        (self.output / gpu.MANIFEST).write_bytes(gpu.encoded(outer))

    def test_finite_archive_policy_fixture_closes_all_current_source_pins(self):
        manifest = self.validate()
        self.assertEqual(set(manifest['hardware_manifest']['files']), set(gpu.MODES))
        self.assertEqual(set(manifest['source_build']['source_files']), set(gpu.SOURCE_FILES))
        self.assertFalse(manifest['physical_hardware_validated'])
        self.assertFalse(manifest['physical_performance_validated'])
        self.assertTrue(manifest['hardware_manifest']['software_default'])

    def test_archive_inventory_rejects_duplicate_extra_and_traversal_members(self):
        original = (self.output / gpu.ARCHIVE).read_bytes()
        for name in (gpu.DRIVER, 'extra.so', '../escape'):
            (self.output / gpu.ARCHIVE).write_bytes(original)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(self.output / gpu.ARCHIVE, 'a') as archive:
                    archive.writestr(name, b'not allowed')
            with self.assertRaisesRegex(ValueError, 'exact six'):
                self.validate()

    def test_member_modes_symlinks_and_empty_products_are_rejected(self):
        contents = gpu.archive_contents(self.output / gpu.ARCHIVE)
        for mode in (stat.S_IFLNK | 0o644, stat.S_IFREG | 0o777):
            write_zip(self.output / gpu.ARCHIVE, contents, {gpu.DRIVER: mode})
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                self.validate()
        contents[gpu.DRIVER] = b''
        write_zip(self.output / gpu.ARCHIVE, contents)
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.validate()

    def test_archive_compressed_expanded_and_member_bounds_match_guest(self):
        self.assertEqual(gpu.MAX_ARCHIVE, 64 * 1024 * 1024)
        for name, message in (('MAX_ARCHIVE', 'archive size'), ('MAX_TOTAL', 'expansion'), ('MAX_MEMBER', 'Unsafe')):
            with mock.patch.object(gpu, name, 1):
                with self.assertRaisesRegex(ValueError, message):
                    gpu.archive_contents(self.output / gpu.ARCHIVE)

    def test_changed_binary_bytes_fail_inner_pin_even_if_zip_crc_is_valid(self):
        contents = gpu.archive_contents(self.output / gpu.ARCHIVE)
        contents[gpu.DRIVER] += b'changed'
        write_zip(self.output / gpu.ARCHIVE, contents)
        with self.assertRaisesRegex(ValueError, 'member bytes'):
            self.validate()

    def test_current_source_and_base_receipts_cannot_be_self_resealed(self):
        original = gpu.read_json(self.output / gpu.RECEIPT)
        for field in ('source_files', 'base_archive', 'base_abi', 'lock'):
            changed = copy.deepcopy(original); changed[field] = {}
            self.reseal(receipt=changed)
            with self.assertRaisesRegex(ValueError, 'current source/build'):
                self.validate()

    def test_exact_commit_and_run_bind_archive_and_receipt(self):
        with self.assertRaisesRegex(ValueError, 'inner manifest'):
            gpu.validate_package(self.output, '2' * 40)
        receipt = gpu.read_json(self.output / gpu.RECEIPT)
        receipt['run_url'] = RUN + '7'
        self.reseal(receipt=receipt)
        with self.assertRaisesRegex(ValueError, 'current source/build'):
            self.validate()

    def test_physical_claims_typed_fields_and_software_default_cannot_change(self):
        original = gpu.read_json(self.output / gpu.MANIFEST)['hardware_manifest']
        for key, value in (('physical_hardware_validated', True), ('software_default', False), ('format', True)):
            inner = copy.deepcopy(original); inner[key] = value
            self.reseal(inner=inner)
            with self.assertRaisesRegex(ValueError, 'inner manifest'):
                self.validate()
        self.reseal(inner=original)
        outer = gpu.read_json(self.output / gpu.MANIFEST)
        outer['physical_performance_validated'] = True
        (self.output / gpu.MANIFEST).write_bytes(gpu.encoded(outer))
        with self.assertRaisesRegex(ValueError, 'outer producer'):
            self.validate()

    def test_producer_directory_and_json_are_closed(self):
        (self.output / 'unexpected').write_text('extra')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.validate()
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                gpu.json_value(data)

    def test_arm64_container_proof_cannot_claim_execution_or_change_tool_source(self):
        original = gpu.read_json(self.container / 'container-build.json')
        for key, value in (('architecture', 'x86_64'), ('hardware_execution_validated', True),
                ('performance_validated', True), ('compiler', 'cc (Ubuntu 14)')):
            receipt = copy.deepcopy(original); receipt[key] = value
            with self.assertRaisesRegex(ValueError, 'Actual ARM64'):
                gpu.validate_container_receipt(receipt)
        receipt = copy.deepcopy(original); receipt['source_archives']['mesa']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source bytes'):
            gpu.validate_container_receipt(receipt)


class RealElfClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-gpu-elf-')
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def compile(self, name, source, version_map=None, libraries=()):
        c = self.directory / (name + '.c'); c.write_text(source)
        command = ['cc', '-shared', '-fPIC', '-Wall', '-Wextra', '-Werror',
            '-Wl,-soname,' + name, str(c), '-o', str(self.directory / name)]
        if version_map:
            script = self.directory / (name + '.map'); script.write_text(version_map)
            command += ['-Wl,--version-script=' + str(script)]
        if libraries:
            command += ['-L' + str(self.directory), *('-l:' + library for library in libraries)]
        subprocess.run(command, check=True, capture_output=True)
        return self.directory / name

    def record(self, path):
        return {'path': str(path), 'resolved_path': str(path), **gpu.file_pin(path),
            'elf': gpu.inspect_elf(path)}

    def load(self, path):
        env = dict(os.environ, LD_LIBRARY_PATH=str(self.directory))
        return subprocess.run([sys.executable, '-c', 'import ctypes,sys;ctypes.CDLL(sys.argv[1])', str(path)],
            env=env, capture_output=True, text=True, timeout=15)

    def test_real_loader_and_gate_reject_wrong_declared_version_provider(self):
        a = self.compile('liba.so', 'int f(void){return 7;}', 'V1 { global: f; local: *; };')
        consumer = self.compile('consumer.so', 'extern int f(void); int consume(void){return f();}', libraries=('liba.so',))
        self.assertEqual(self.load(consumer).returncode, 0)
        initial = {'libraries': {'liba.so': self.record(a)}}
        self.assertEqual(set(gpu.dependency_closure(gpu.inspect_elf(consumer), initial)), {'liba.so'})
        b = self.compile('libb.so', 'int f(void){return 7;} int anchor(void){return 1;}',
            'V1 { global: f; anchor; local: *; };')
        a = self.compile('liba.so', 'extern int anchor(void); int g(void){return anchor();}',
            'V2 { global: g; local: *; };', libraries=('libb.so',))
        result = self.load(consumer)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version `V1' not found", result.stderr)
        elf = gpu.inspect_elf(consumer)
        self.assertEqual(elf['version_needs'], {'liba.so': ['V1']})
        snapshot = {'libraries': {'liba.so': self.record(a), 'libb.so': self.record(b)}}
        with self.assertRaisesRegex(ValueError, 'declared SONAME: liba.so'):
            gpu.dependency_closure(elf, snapshot)

    def test_real_dynamic_export_visibility_and_default_version_are_recorded(self):
        path = self.compile('exports.so', '__attribute__((visibility("hidden"))) int hidden(void){return 1;}\n'
            '__attribute__((visibility("protected"))) int protected_symbol(void){return 2;}\n'
            'int public_symbol(void){return 3;}', 'V1 { global: public_symbol; protected_symbol; local: *; };')
        elf = gpu.inspect_elf(path)
        self.assertNotIn('hidden', elf['default_symbols'])
        self.assertIn('public_symbol', elf['default_symbols'])
        self.assertIn('protected_symbol', elf['default_symbols'])
        self.assertIn('public_symbol@V1', elf['exported_symbols'])
        self.assertIn('V1', elf['version_definitions'])

    def test_missing_strong_symbol_new_dependency_and_search_path_fail_closed(self):
        path = self.compile('requires.so', 'extern int absent(void); int invoke(void){return absent();}')
        elf = gpu.inspect_elf(path)
        self.assertIn('absent', elf['required_symbols'])
        with self.assertRaisesRegex(ValueError, 'dynamic symbol/version'):
            gpu.dependency_closure(elf, {'libraries': {}})
        elf['needed'] = ['unbundled-new-core.so']
        with self.assertRaisesRegex(ValueError, 'absent from the exact base'):
            gpu.dependency_closure(elf, {'libraries': {}})
        subprocess.run(['cc', '-shared', '-fPIC', str(self.directory / 'requires.so.c'), '-Wl,-rpath,/unreviewed',
            '-o', str(path)], check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, 'search path'):
            gpu.inspect_elf(path)

    def test_retained_snapshot_carries_exact_arm64_byte_and_provider_records(self):
        snapshot = gpu.abi_snapshot()
        self.assertEqual(len(snapshot['libraries']), 27)
        self.assertEqual(snapshot['base_archive']['sha256'], gpu.base_pin()['sha256'])
        for name, record in snapshot['libraries'].items():
            self.assertEqual(record['elf']['machine'], 183)
            self.assertEqual(record['elf']['soname'], name)
            self.assertIn('version_needs', record['elf'])
            self.assertIn('version_definitions', record['elf'])
            self.assertGreater(record['bytes'], 0)


class ProductionPeBindingTests(unittest.TestCase):
    def test_actual_production_pe_pin_is_bound_to_current_win32_source_and_run(self):
        import test_coh_gpu_probe_native as probe
        production = b'actual-produced-PE32-bytes'
        checks = {'commit': COMMIT, 'github_run_url': RUN,
            'production_probe': dict(gpu.pin(production), pe_machine=332,
                build_marker='COH_GPU_PROBE_BUILD:production')}
        # This unit fixture checks the additional producer binding. The real
        # Win32 receipt validator is separately run against actual host outputs.
        with mock.patch.object(probe, 'validate_windows_checks', create=True):
            gpu.validate_pe32_checks(checks, COMMIT, RUN, production)
            for commit, run_url, data in ((COMMIT, RUN, production+b'changed'),
                    ('2'*40, RUN, production), (COMMIT, RUN+'7', production)):
                with self.assertRaisesRegex(ValueError, 'production PE32 bytes/current source/run'):
                    gpu.validate_pe32_checks(checks, commit, run_url, data)

    def test_actual_helper_source_template_and_pe32_bytes_must_match_receipt(self):
        import test_coh_gpu_probe_native as probe
        from test_package_reference_runtime import pe_file
        with tempfile.TemporaryDirectory(prefix='coh-win-helper-pins-') as temporary:
            directory = Path(temporary)
            positive = '\n'.join(f'r->{field} = 1;' for field in probe.BOOL_FIELDS)
            rejected = '\n'.join(f'positive(&r); r.{field} = 0; printf("%d",result_passes(&r));'
                for field in probe.BOOL_FIELDS)
            source = probe.FIXTURE.replace('SOURCE_PATH', '"D:/a/coh-android/coh-android/android/native/coh-gpu-probe.c"').replace(
                'POSITIVE_FIELDS', positive).replace('REJECT_FIELDS', rejected).encode()
            raw = pe_file(('KERNEL32.dll',)) + b'COH_GPU_PROBE_BUILD:host_fixture'
            (directory / gpu.PE32_HELPER_SOURCE).write_bytes(source)
            (directory / gpu.PE32_HELPER_EXE).write_bytes(raw)
            checks = {'fixture_bytes': len(source), 'fixture_sha256': hashlib.sha256(source).hexdigest(),
                'executable_bytes': len(raw), 'executable_sha256': hashlib.sha256(raw).hexdigest()}
            self.assertEqual(gpu.validate_pe32_helpers(checks, directory), gpu.pe32_helper_pins(checks))
            for name in (gpu.PE32_HELPER_SOURCE, gpu.PE32_HELPER_EXE):
                original = (directory / name).read_bytes()
                (directory / name).write_bytes(original + b'changed')
                with self.assertRaisesRegex(ValueError, 'file pin differs'):
                    gpu.validate_pe32_helpers(checks, directory)
                (directory / name).write_bytes(original)
            (directory / gpu.PE32_HELPER_SOURCE).write_bytes(source.replace(b'return 2;', b'return 3;'))
            changed = (directory / gpu.PE32_HELPER_SOURCE).read_bytes()
            checks['fixture_bytes'] = len(changed); checks['fixture_sha256'] = hashlib.sha256(changed).hexdigest()
            with self.assertRaisesRegex(ValueError, 'helper code differs'):
                gpu.validate_pe32_helpers(checks, directory)


class SourceExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-source-tar-')
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def archive(self, members):
        path = self.directory / 'source.tar'
        with tarfile.open(path, 'w') as archive:
            for name, kind, value in members:
                member = tarfile.TarInfo(name)
                member.mode = 0o7777  # source extraction strips special/write bits
                member.type = kind
                if kind == tarfile.REGTYPE:
                    member.size = len(value)
                    archive.addfile(member, io.BytesIO(value))
                else:
                    if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                        member.linkname = value
                    archive.addfile(member)
        return path

    def extract(self, members):
        source_build.unpack(self.archive(members), self.directory, 'source-1')

    def test_actual_tar_data_and_confined_early_symlink_are_staged_on_bookworm_path(self):
        with mock.patch.object(tarfile.TarFile, 'extractall', side_effect=AssertionError('Unsupported API')):
            self.extract([('source-1/alias', tarfile.SYMTYPE, 'sub/data'),
                ('source-1', tarfile.DIRTYPE, ''), ('source-1/sub', tarfile.DIRTYPE, ''),
                ('source-1/sub/data', tarfile.REGTYPE, b'actual tar bytes')])
        self.assertEqual((self.directory / 'source-1/alias').read_bytes(), b'actual tar bytes')
        self.assertTrue((self.directory / 'source-1/alias').is_symlink())
        self.assertEqual(stat.S_IMODE((self.directory / 'source-1/sub/data').stat().st_mode), 0o755)
        with self.assertRaisesRegex(ValueError, 'Fresh'):
            self.extract([('source-1/a', tarfile.REGTYPE, b'x')])

    def test_unsafe_paths_duplicates_special_files_and_hardlinks_fail_before_writes(self):
        cases = [('../escape', tarfile.REGTYPE, b'x'), ('/source-1/abs', tarfile.REGTYPE, b'x'),
            ('source-1/a/../b', tarfile.REGTYPE, b'x'), ('different-root/a', tarfile.REGTYPE, b'x'),
            ('source-1/a\\b', tarfile.REGTYPE, b'x'), ('source-1/a//b', tarfile.REGTYPE, b'x'),
            ('source-1/fifo', tarfile.FIFOTYPE, ''), ('source-1/hard', tarfile.LNKTYPE, 'source-1/data')]
        for member in cases:
            with self.subTest(member=member):
                with self.assertRaisesRegex(ValueError, 'Unsafe'):
                    self.extract([('source-1/data', tarfile.REGTYPE, b'first'), member])
                self.assertFalse((self.directory / 'source-1').exists())
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            self.extract([('source-1/data', tarfile.REGTYPE, b'a'), ('source-1/data', tarfile.REGTYPE, b'b')])

    def test_link_escape_missing_target_and_parent_link_descent_fail_before_writes(self):
        for target in ('../../escape', '/outside', 'missing', '../different-root/data'):
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'Escaping or missing'):
                self.extract([('source-1/data', tarfile.REGTYPE, b'x'), ('source-1/link', tarfile.SYMTYPE, target)])
            self.assertFalse((self.directory / 'source-1').exists())
        with self.assertRaisesRegex(ValueError, 'descends'):
            self.extract([('source-1/dir', tarfile.DIRTYPE, ''), ('source-1/link', tarfile.SYMTYPE, 'dir'),
                ('source-1/link/child', tarfile.REGTYPE, b'x')])
        self.assertFalse((self.directory / 'source-1').exists())

    def test_mesa26_finite_license_catalog_is_preserved_as_deterministic_bytes(self):
        source = self.directory / 'mesa-26.0.0'
        originals = {}
        for name in source_build.MESA_LICENSE_FILES:
            path = source / name; path.parent.mkdir(parents=True, exist_ok=True)
            originals[name] = ('Exact upstream text: ' + name + '\n').encode()
            path.write_bytes(originals[name])
        self.assertFalse((source / 'COPYING').exists())
        url = gpu.lock()['mesa']['url']
        first = source_build.mesa_notices(source, url)
        self.assertEqual(first, source_build.mesa_notices(source, url))
        for name, original in originals.items():
            self.assertIn(('## Upstream ' + name + '\n\n').encode() + original, first)
        extra = source / 'licenses/unexpected'; extra.write_bytes(b'new license')
        with self.assertRaisesRegex(ValueError, 'catalog differs'):
            source_build.mesa_notices(source, url)
        extra.unlink()
        (source / 'licenses/MIT').unlink()
        with self.assertRaisesRegex(ValueError, 'catalog differs'):
            source_build.mesa_notices(source, url)

    def test_source_member_and_total_expansion_bounds_fail_without_materializing_payload(self):
        archive = self.archive([('source-1/a', tarfile.REGTYPE, b'x')])
        oversized = tarfile.TarInfo('source-1/a'); oversized.size = 64 * 1024 * 1024 + 1
        for members, message in (([oversized], 'Unsafe'), ([oversized] * 9, 'expansion'),
                ([tarfile.TarInfo('source-1')] * 25001, 'expansion')):
            with mock.patch.object(tarfile.TarFile, 'getmembers', return_value=members):
                with self.assertRaisesRegex(ValueError, message):
                    source_build.unpack(archive, self.directory, 'source-1')
            self.assertFalse((self.directory / 'source-1').exists())


if __name__ == '__main__':
    unittest.main()
