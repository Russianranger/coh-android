#!/usr/bin/env python3
"""Producer bounds and sequencing; synthetic inputs never qualify native code."""
import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/scripts'))
import server_metrics_producer as producer


class ProducerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.commit = 'a' * 40
        self.run_id = 123
        self.frozen = mock.patch.object(producer, 'baseline_root', return_value=self.work).start()
        self.addCleanup(mock.patch.stopall)

    def manifest(self, files=None):
        return {'format': 1, 'role': 'armport_server_metrics_build_input_bundle',
                'repository_commit': self.commit, 'run_id': self.run_id,
                'baseline_commit': producer.BASELINE_COMMIT,
                'variants': {name: {} for name in producer.VARIANTS},
                'files': files or {'empty.h': {'bytes': 0, 'sha256': producer.package.digest(b'')}},
                'shipping_binary_executed': False}

    def archive(self, entries):
        path = self.work / 'inputs.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            for name, raw, kind in entries:
                info = tarfile.TarInfo(name)
                if kind == 'file':
                    info.size = len(raw)
                    archive.addfile(info, io.BytesIO(raw))
                else:
                    info.type = tarfile.SYMTYPE
                    info.linkname = 'elsewhere'
                    archive.addfile(info)
        return path

    def test_bundle_identity_exact_types_and_zero_byte_sources(self):
        original = self.manifest()
        self.assertEqual(producer.validate_bundle_manifest(original, self.commit, self.run_id), original)
        for key, value in [('format', True), ('run_id', True), ('repository_commit', 'b' * 40),
                           ('shipping_binary_executed', True), ('variants', {'retained_progress': {}})]:
            changed = copy.deepcopy(original); changed[key] = value
            with self.assertRaises(ValueError):
                producer.validate_bundle_manifest(changed, self.commit, self.run_id)

    def test_bundle_unsafe_names_and_size_bounds(self):
        for name in ('../escape', '/absolute', 'C:/escape', 'a\\b', 'a//b', 'a/CON.h', 'trailing.'):
            with self.assertRaises(ValueError):
                producer.validate_bundle_manifest(self.manifest({name: {'bytes': 1, 'sha256': 'a' * 64}}),
                                                   self.commit, self.run_id)
        document = self.manifest({'large': {'bytes': producer.MAX_BUNDLE + 1, 'sha256': 'a' * 64}})
        with self.assertRaises(ValueError):
            producer.validate_bundle_manifest(document, self.commit, self.run_id)

    def test_extract_checks_complete_inventory_before_writing_payload(self):
        document = self.manifest()
        archive = self.archive([(producer.BUNDLE, json.dumps(document).encode(), 'file'),
                                ('unexpected', b'x', 'file')])
        output = self.work / 'stage'
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            producer.extract(archive, output, self.commit, self.run_id, self.work)
        self.assertEqual(list(output.iterdir()), [])

    def test_extract_rejects_duplicates_links_and_traversal(self):
        for index, entries in enumerate(( [('same', b'x', 'file'), ('same', b'x', 'file')],
                                          [('linked', b'', 'link')], [('.. /../escape', b'x', 'file')])):
            archive = self.archive(entries)
            with self.assertRaises(ValueError):
                producer.extract(archive, self.work / ('stage' + str(index)), self.commit, self.run_id, self.work)

    def test_extract_checks_bytes_and_invokes_full_source_gate(self):
        document = self.manifest()
        archive = self.archive([(producer.BUNDLE, json.dumps(document).encode(), 'file'),
                                ('empty.h', b'', 'file')])
        with mock.patch.object(producer, 'verify_bundle', return_value=document) as verify:
            output = self.work / 'stage'
            self.assertEqual(producer.extract(archive, output, self.commit, self.run_id, self.work), document)
            verify.assert_called_once_with(output.resolve(), self.commit, self.run_id, self.work)
        archive = self.archive([(producer.BUNDLE, json.dumps(document).encode(), 'file'),
                                ('empty.h', b'changed', 'file')])
        with self.assertRaisesRegex(ValueError, 'member changed'):
            producer.extract(archive, self.work / 'changed', self.commit, self.run_id, self.work)

    def test_outer_donor_is_authenticated_before_zip_parsing(self):
        apk = self.work / 'donor.apk'; apk.write_bytes(b'not an APK')
        with self.assertRaisesRegex(ValueError, 'outer donor'):
            producer.extract_donor(apk, {'bytes': 99, 'sha256': '0' * 64}, self.work,
                                   'thor_certified_startup')

    def test_immutable_output_and_existing_directory_refused(self):
        with self.assertRaises(ValueError):
            producer.fresh(producer.ROOT / 'upstream' / 'new-output')
        with self.assertRaises(ValueError):
            producer.fresh(self.work)

    def test_windows_builds_are_serial_and_every_command_has_compiler_bound(self):
        inputs = self.work / 'input'; inputs.mkdir()
        manifest = self.manifest()
        for variant in producer.VARIANTS:
            base = inputs / variant
            manifest['variants'][variant] = {'donor': {'manifest': {'bytes': 1, 'sha256': 'a' * 64}}}
            for name in ('source/out/build/vs2026/bin/OptDebug/MapServer.pdb',
                         'source/out/build/vs2026/CMakeCache.txt', 'source/' + producer.source.RECEIPT,
                         producer.package.CHECKS, 'source-checks.log'):
                target = base / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('fixture')
        calls = []
        def command(argv, _log, **kwargs):
            calls.append(tuple(map(str, argv)))
            self.assertEqual(kwargs['env']['_CL_'], '/MP1')
            self.assertEqual(kwargs['env']['CMAKE_BUILD_PARALLEL_LEVEL'], '1')
            self.assertEqual(kwargs['env']['CL'], '')
        def package(*_args, **kwargs):
            calls.append(('package', kwargs['variant']))
            return {'files': {'MapServer.exe': {'bytes': 1, 'sha256': 'f' * 64}}}
        # Native compiler/package execution is deliberately mocked here. Real
        # native execution belongs to the Windows Actions job, never this test.
        with mock.patch.object(producer, 'os', SimpleNamespace(name='nt', environ={})), \
             mock.patch.object(producer.shutil, 'which', return_value='cl.exe'), \
             mock.patch.object(producer, 'verify_bundle', return_value=manifest), \
             mock.patch.object(producer, 'run', side_effect=command), \
             mock.patch.object(producer.package, 'package', side_effect=package), \
             mock.patch.object(producer, 'pin', return_value={'bytes': 1, 'sha256': 'f' * 64}):
            result = producer.build(inputs, self.work / 'output', self.commit, self.run_id, self.work)
        self.assertEqual(result['variants_built_in_order'], list(producer.VARIANTS))
        self.assertFalse(result['shipping_binary_executed'])
        self.assertEqual([c[:2] for c in calls if c[0] == 'package'],
                         [('package', 'retained_progress'), ('package', 'thor_certified_startup')])
        builds = [c for c in calls if c[0] == 'cmake' and c[1] == '--build']
        self.assertEqual(len(builds), 2)
        self.assertTrue(all(c[c.index('--parallel') + 1] == '1' and c[c.index('--target') + 1] == 'MapServer'
                            for c in builds))
        self.assertLess(calls.index(('package', 'retained_progress')), len(calls) - 2)

    @staticmethod
    def lua_tarball(entries=None):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, raw, kind in entries or [('lua-5.1.5', b'', 'dir'), ('lua-5.1.5/src', b'', 'dir'),
                                               ('lua-5.1.5/src/lua.c', b'int main(void) { return 0; }\n', 'file'),
                                               ('lua-5.1.5/Makefile', b'all:\n', 'file')]:
                info = tarfile.TarInfo(name)
                if kind == 'dir':
                    info.type = tarfile.DIRTYPE
                    archive.addfile(info)
                elif kind == 'link':
                    info.type = tarfile.SYMTYPE; info.linkname = '/etc/passwd'
                    archive.addfile(info)
                else:
                    info.size = len(raw)
                    archive.addfile(info, io.BytesIO(raw))
        return stream.getvalue()

    def lua_build(self, tarball, *, download=None, cache=None, declaration=None):
        """Run build() with mocked native commands; the first configure 'downloads' `download`."""
        digest = producer.package.digest(tarball)
        mock.patch.object(producer, 'LUA_SHA256', digest).start()
        inputs = self.work / 'input'; inputs.mkdir()
        manifest = self.manifest()
        for variant in producer.VARIANTS:
            base = inputs / variant
            manifest['variants'][variant] = {'donor': {'manifest': {'bytes': 1, 'sha256': 'a' * 64}}}
            for name in ('source/out/build/vs2026/bin/OptDebug/MapServer.pdb',
                         'source/out/build/vs2026/CMakeCache.txt', 'source/' + producer.source.RECEIPT,
                         producer.package.CHECKS, 'source-checks.log'):
                target = base / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text('fixture')
            lua = base / 'source' / producer.LUA_DECLARATION; lua.parent.mkdir(parents=True)
            lua.write_text(declaration or ('CPMAddPackage(\n\tNAME lua51\n\tVERSION 5.1.5\n\tURL "' + producer.LUA_URL
                           + '"\n\tURL_HASH\n\t\t"SHA256=' + digest + '"\n\tPATCHES "lua-cmake.patch"\n)\n'))
        configures = []
        def command(argv, _log, **kwargs):
            argv = list(map(str, argv))
            if argv[:2] == ['cmake', '--preset']:
                seeded = [a for a in argv if a.startswith('-DCPM_lua51_SOURCE=')]
                configures.append((Path(kwargs['cwd']).parent.name, seeded))
                archive = Path(kwargs['cwd']) / producer.LUA_DOWNLOAD
                self.assertFalse(archive.exists())
                if not seeded and download is not None:
                    archive.parent.mkdir(parents=True); archive.write_bytes(download)
        with mock.patch.object(producer, 'os', SimpleNamespace(name='nt', environ={})), \
             mock.patch.object(producer.shutil, 'which', return_value='cl.exe'), \
             mock.patch.object(producer, 'verify_bundle', return_value=manifest), \
             mock.patch.object(producer, 'run', side_effect=command), \
             mock.patch.object(producer.package, 'package',
                               return_value={'files': {'MapServer.exe': {'bytes': 1, 'sha256': 'f' * 64}}}), \
             mock.patch.object(producer, 'pin', return_value={'bytes': 1, 'sha256': 'f' * 64}):
            result = producer.build(inputs, self.work / 'output', self.commit, self.run_id, self.work, cache)
        return result['lua_archive'], configures

    def test_second_variant_reuses_the_lua_archive_the_first_verified(self):
        tarball = self.lua_tarball()
        cache = self.work / 'lua-cache'
        record, configures = self.lua_build(tarball, download=tarball, cache=cache)
        source = (self.work / 'output/lua-sources/thor_certified_startup').resolve()
        self.assertEqual(configures, [('retained_progress', []),
                                      ('thor_certified_startup', ['-DCPM_lua51_SOURCE=' + source.as_posix()])])
        # ExternalProject's layout: the top directory's contents, unpatched (CPM applies the variant's patch).
        self.assertEqual(sorted(str(p.relative_to(source)) for p in source.rglob('*')),
                         ['Makefile', 'src', 'src/lua.c'])
        self.assertEqual((source / 'src/lua.c').read_bytes(), b'int main(void) { return 0; }\n')
        self.assertEqual(record, {'archive_sha256': producer.package.digest(tarball), 'from_job_cache': False,
                                  'downloaded_by_cmake': ['retained_progress'],
                                  'extracted_for': ['thor_certified_startup']})
        self.assertEqual((cache / producer.LUA_ARCHIVE_NAME).read_bytes(), tarball)

    def test_job_cache_serves_both_variants_and_no_other_archive_is_reused(self):
        tarball = self.lua_tarball()
        cache = self.work / 'lua-cache'; cache.mkdir()
        (cache / producer.LUA_ARCHIVE_NAME).write_bytes(tarball)
        record, configures = self.lua_build(tarball, download=None, cache=cache)
        self.assertEqual([variant for variant, seeded in configures if seeded], list(producer.VARIANTS))
        self.assertEqual(record['downloaded_by_cmake'], [])
        self.assertTrue(record['from_job_cache'])

    def test_a_different_archive_or_declaration_is_never_reused(self):
        tarball = self.lua_tarball()
        for case in ('download', 'declaration'):
            with self.subTest(case=case):
                self.work = Path(tempfile.mkdtemp(dir=self.temporary.name))
                cache = self.work / 'lua-cache'
                record, configures = self.lua_build(
                    tarball, download=tarball + b'x' if case == 'download' else tarball, cache=cache,
                    declaration='CPMAddPackage(NAME lua51 URL "https://example.invalid/lua-5.1.5.tar.gz")\n'
                    if case == 'declaration' else None)
                self.assertEqual([seeded for _, seeded in configures], [[], []])
                self.assertEqual((record['downloaded_by_cmake'], record['extracted_for']), ([], []))
                self.assertFalse((cache / producer.LUA_ARCHIVE_NAME).exists())
        # A damaged cache entry is ignored, then replaced by CMake's own verified download.
        self.work = Path(tempfile.mkdtemp(dir=self.temporary.name))
        cache = self.work / 'lua-cache'; cache.mkdir()
        (cache / producer.LUA_ARCHIVE_NAME).write_bytes(tarball + b'x')
        record, configures = self.lua_build(tarball, download=tarball, cache=cache)
        self.assertEqual([variant for variant, seeded in configures if seeded], ['thor_certified_startup'])
        self.assertFalse(record['from_job_cache'])
        self.assertEqual((cache / producer.LUA_ARCHIVE_NAME).read_bytes(), tarball)

    def test_lua_extraction_refuses_unsafe_or_unpinned_archives(self):
        for entries in ([('lua-5.1.5/../escape', b'x', 'file')], [('lua-5.1.5/link', b'', 'link')],
                        [('other/lua.c', b'x', 'file')], [('lua-5.1.5', b'x', 'file')],
                        [('/lua-5.1.5/abs', b'x', 'file')]):
            raw = self.lua_tarball(entries)
            with self.subTest(entries=entries[0][0]), \
                 mock.patch.object(producer, 'LUA_SHA256', producer.package.digest(raw)):
                with self.assertRaises(ValueError):
                    producer.extract_lua(raw, self.work / ('bad-' + str(len(list(self.work.iterdir())))))
        with self.assertRaisesRegex(ValueError, 'differs from its pin'):
            producer.extract_lua(self.lua_tarball(), self.work / 'unpinned')


if __name__ == '__main__':
    unittest.main()
