"""Reject incomplete graph, CRC and native route evidence before packaging."""
import struct
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import generate_atlas_beacons as generator


class AtlasNativeEvidenceTests(unittest.TestCase):
    MARKER = b'COH_ATLAS_BEACON_FRESH_WORLD_V1 crc=0x10203040\n' + b'COH_ATLAS_BEACON_NATIVE_V1 crc=0x10203040 combat=2000 connected=1900 ground=5000 raised=100 blocks=100 paths=32\n'

    def test_valid_bounded_native_receipt_shape(self):
        value = generator.native_evidence(self.MARKER, struct.pack('<iII',9,1767225600,0x10203040))
        self.assertEqual(value['native_pathfinder_successes'],32)
        self.assertEqual(value['full_world_crc'],'0x10203040')

    def test_missing_duplicate_or_low_connection_witness_is_rejected(self):
        for raw in (b'', self.MARKER*2, self.MARKER.replace(b'ground=5000',b'ground=0'),
                    self.MARKER.replace(b'paths=32',b'paths=0'),
                    self.MARKER.replace(b'connected=1900',b'connected=2001')):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    generator.native_evidence(raw,struct.pack('<iII',9,1767225600,0x10203040))


    def test_fresh_loaded_world_capture_must_be_unique_and_match_final_witness(self):
        date=struct.pack('<iII',9,1767225600,0x10203040)
        main=self.MARKER.splitlines(keepends=True)[-1]
        fresh=self.MARKER.splitlines(keepends=True)[0]
        for raw in (main,main+fresh,fresh+self.MARKER,
                    fresh.replace(b'0x10203040',b'0x10203041')+main):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError,'fresh ordinary-world'):
                generator.native_evidence(raw,date)

    def test_date_crc_version_and_size_must_match_native_loaded_world(self):
        for date in (b'bad',struct.pack('<iII',8,1767225600,0x10203040),
                     struct.pack('<iII',9,1767225600,0x10203041)):
            with self.subTest(date=date):
                with self.assertRaises(ValueError): generator.native_evidence(self.MARKER,date)

    def test_owned_roles_remove_progress_request_instead_of_setting_it_empty(self):
        for request in ('', 'C:/android-observer.map'):
            value = generator.role_environment({'PATH': 'owned-path', 'COH_WINE_MAP_PROGRESS': request,
                'COH_CLIENT_DEPENDENCY_PRELOAD': '1', 'COH_MANUAL_ATLAS_DB': '1',
                'COH_WINE_GAME_LISTENERS': '1'})
            self.assertEqual(value, {'PATH': 'owned-path', 'COH_GAME_LOOPBACK_ONLY': '1'})


    def test_host_roles_override_inherited_loopback_mode_before_native_startup(self):
        for request in ('', '0', '1', 'invalid'):
            with self.subTest(request=request):
                env = generator.role_environment({'COH_GAME_LOOPBACK_ONLY': request, 'PATH': 'owned'})
                self.assertEqual(env['COH_GAME_LOOPBACK_ONLY'], '1')
                self.assertEqual(env['PATH'], 'owned')

    def test_failure_receipt_retains_exit_status_and_only_bounded_role_tail(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            (evidence/'master.log').write_bytes(b'EXCLUDED_PREFIX' + b'x'*9000 + b'FINAL_NATIVE_FAILURE')
            process = SimpleNamespace(returncode=3221225477, poll=lambda: 3221225477)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                generator.record_role_failure(evidence, {'master': process},
                    {'master': ['C:/owned/AtlasBeaconGenerator.exe', '-beaconmasterserver']},
                    ValueError('Native role startup failed: master'))
            report = json.loads((evidence/'native-role-failure.json').read_bytes())
            self.assertTrue(report['cleanup_complete'])
            self.assertEqual(report['roles']['master']['windows_exit_hex'], '0xc0000005')
            self.assertNotIn('EXCLUDED_PREFIX', output.getvalue())
            self.assertIn('FINAL_NATIVE_FAILURE', output.getvalue())
            self.assertLess(len(output.getvalue()), generator.MAX_FAILURE_TAIL + 200)

    def test_unicode_tail_is_cp1252_safe_and_json_precedes_console_rendering(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary); (evidence/'sentry.log').write_bytes(b'heap \xff\xfe FINAL')
            process = SimpleNamespace(returncode=1, poll=lambda: 1)
            class WindowsConsole(io.StringIO):
                def write(self, value):
                    self_exists = (evidence/'native-role-failure.json').exists()
                    if not self_exists: raise AssertionError('Receipt must precede rendering')
                    value.encode('cp1252', errors='strict')
                    return super().write(value)
            output = WindowsConsole()
            with contextlib.redirect_stdout(output):
                generator.record_role_failure(evidence, {'sentry': process}, {'sentry':['owned.exe']},
                    ValueError('Native role exited'), {'sentry':3221226356})
            report = json.loads((evidence/'native-role-failure.json').read_bytes())
            self.assertEqual(report['roles']['sentry']['windows_exit_before_cleanup'], '0xc0000374')
            self.assertEqual(report['roles']['sentry']['windows_exit_hex'], '0x00000001')
            self.assertIn('FINAL',output.getvalue())

    def test_cold_mirror_shares_readonly_inputs_and_isolates_mutable_native_caches(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); runtime=root/'r'; runtime.mkdir()
            fixtures = {'data/object_library/a.geo':b'exact geometry', 'data/maps/a.txt':b'exact groups',
                        'data/bin/defs.bin':b'private definitions', 'data/geobin/world.bin':b'private geometry cache',
                        'data/server/cache':b'private server cache', 'MapServer.exe':b'owned native'}
            for name, raw in fixtures.items():
                target=runtime/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
            cold=root/'c'; value=generator.mirror_cold_runtime(runtime,cold)
            self.assertTrue(value['created_before_visual_overlay_and_generation'])
            self.assertTrue(os.path.samefile(runtime/'data/object_library/a.geo',cold/'data/object_library/a.geo'))
            self.assertEqual((cold/'data/object_library/a.geo').stat().st_mode & 0o222,0)
            for name in ('data/bin/defs.bin','data/geobin/world.bin','data/server/cache','MapServer.exe'):
                self.assertFalse(os.path.samefile(runtime/name,cold/name))
                (runtime/name).write_bytes(b'generated after cold snapshot')
                self.assertEqual((cold/name).read_bytes(),fixtures[name])
            optional=runtime/'data/object_library/optional.geo';optional.write_bytes(b'visual object')
            self.assertFalse((cold/'data/object_library/optional.geo').exists())

    def test_rich_source_records_are_projected_without_weakening_byte_pins(self):
        original = {'data/object_library/a.geo': {'bytes': 17, 'sha256': 'a'*64,
            'original_client_source': {'container': 'original.pigg', 'index': 45},
            'models': ['exact-model']}}
        projected = generator.physical_pins(original)
        self.assertEqual(projected, {'data/object_library/a.geo': {'bytes': 17, 'sha256': 'a'*64}})
        self.assertIn('models', original['data/object_library/a.geo'])
        self.assertNotEqual(generator.canonical(projected), generator.canonical(original))
        for row in ({'bytes':True,'sha256':'a'*64}, {'bytes':17,'sha256':'not-a-digest'}, {'bytes':0,'sha256':'a'*64}):
            with self.subTest(row=row), self.assertRaises(ValueError):
                generator.physical_pins({'data/object_library/a.geo':row})

    def test_inventory_failure_preserves_bounded_actual_missing_extra_and_changed_differences(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence=Path(temporary)
            common={'data/maps/map.txt': {'bytes':2,'sha256':'a'*64}}
            optional={'data/object_library/optional.geo': {'bytes':3,'sha256':'b'*64}}
            warm={'data/maps/map.txt': {'bytes':4,'sha256':'c'*64}}
            warm.update({'data/object_library/extra%d.geo'%i: {'bytes':1,'sha256':'d'*64} for i in range(50)})
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                record=generator.record_profile_inventory(evidence,common,optional,warm,{})
            self.assertEqual(record['status'],'mismatch')
            self.assertEqual(record['warm_difference']['missing_count'],1)
            self.assertEqual(record['warm_difference']['extra_count'],50)
            self.assertEqual(len(record['warm_difference']['extra_first_16']),16)
            self.assertEqual(record['warm_difference']['changed_count'],1)
            self.assertEqual(record['cold_difference']['missing_count'],1)
            self.assertEqual(json.loads((evidence/'native-input-profiles.json').read_bytes()),record)
            self.assertIn('COH_ATLAS_BEACON_INPUT_PROFILES',output.getvalue())


    def test_unqualified_completed_output_is_saved_before_crc_validation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); runtime = root/'r'; runtime.mkdir()
            evidence = root/'evidence'; evidence.mkdir()
            graph = runtime/generator.GRAPH; graph.parent.mkdir(parents=True)
            graph.write_bytes(b'actual generated graph bytes')
            date = runtime/generator.DATE
            date.write_bytes(struct.pack('<iII', 9, 1767225600, 0x10203041))
            (evidence/'server.log').write_bytes(self.MARKER)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                value = generator.record_native_output(evidence, runtime, 0)
            self.assertEqual(value['status'], 'unqualified_native_output')
            self.assertTrue(value['both_fresh_profile_proofs_required'])
            self.assertEqual(value['date']['full_world_crc'], '0x10203041')
            self.assertEqual(value['native_markers'][0]['crc'], '0x10203040')
            self.assertEqual((evidence/'unqualified-native-graph.bcn').read_bytes(), graph.read_bytes())
            self.assertEqual((evidence/'unqualified-native-graph.bcn.date').read_bytes(), date.read_bytes())
            self.assertEqual(json.loads((evidence/'unqualified-native-output.json').read_bytes()), value)
            self.assertIn('COH_ATLAS_BEACON_UNQUALIFIED_OUTPUT', output.getvalue())
            with self.assertRaisesRegex(ValueError, 'marker=0x10203040 date=0x10203041'):
                generator.native_evidence(self.MARKER, date.read_bytes())
            self.assertFalse((evidence/generator.MANIFEST).exists())
            self.assertFalse((evidence/generator.ARCHIVE).exists())

    def test_unqualified_capture_preserves_native_version_instead_of_repairing_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); runtime=root/'r'; runtime.mkdir()
            evidence=root/'evidence'; evidence.mkdir()
            graph=runtime/generator.GRAPH; graph.parent.mkdir(parents=True); graph.write_bytes(b'actual native graph')
            date=runtime/generator.DATE; raw=struct.pack('<iII',8,0,0x10203040); date.write_bytes(raw)
            (evidence/'server.log').write_bytes(self.MARKER)
            with contextlib.redirect_stdout(io.StringIO()):
                value=generator.record_native_output(evidence,runtime,0)
            self.assertEqual(value['date']['version'],8)
            self.assertEqual(date.read_bytes(),raw)
            with self.assertRaisesRegex(ValueError,'Native date version differs: 8'):
                generator.native_evidence(self.MARKER,raw)

    def test_unqualified_output_refuses_symlink_and_oversize_payloads(self):
        for linked in (False,True):
            with self.subTest(linked=linked), tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary); runtime=root/'r'; runtime.mkdir()
                evidence=root/'evidence'; evidence.mkdir()
                graph=runtime/generator.GRAPH; graph.parent.mkdir(parents=True)
                if linked:
                    other=root/'unowned.bcn'; other.write_bytes(b'foreign graph'); graph.symlink_to(other)
                else:
                    with graph.open('wb') as stream: stream.truncate(generator.MAX_GRAPH+1)
                (runtime/generator.DATE).write_bytes(struct.pack('<iII',9,0,0x10203040))
                (evidence/'server.log').write_bytes(self.MARKER)
                with self.assertRaises(ValueError): generator.record_native_output(evidence,runtime,0)
                self.assertFalse((evidence/'unqualified-native-output.json').exists())

    def test_owned_role_heartbeat_is_bounded_ascii_and_not_a_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence=Path(temporary)
            (evidence/'server.log').write_bytes(b'EXCLUDED_PREFIX\n'+b'x'*9000+b'\nNative \xff final progress\n')
            process=SimpleNamespace(poll=lambda:None)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                value=generator.record_role_heartbeat(evidence,{'server':process},generator.time.monotonic()-5,'generation')
            self.assertEqual(value['status'],'native_progress_only')
            self.assertEqual(value['phase'],'generation')
            self.assertIsNone(value['roles']['server']['returncode'])
            self.assertGreaterEqual(value['elapsed_seconds'],5)
            self.assertNotIn('EXCLUDED_PREFIX',output.getvalue())
            self.assertIn('final progress',output.getvalue())
            output.getvalue().encode('ascii')
            self.assertLessEqual(len(value['roles']['server']['last_progress_line']),512)
            self.assertFalse((evidence/generator.REPORT).exists())

    def test_capture_precedes_native_crc_assertion_in_actual_producer(self):
        import inspect
        source=inspect.getsource(generator.generate)
        self.assertLess(source.index('record_native_output(evidence, runtime,'),
                        source.index('witness = native_evidence'))
        self.assertIn('next_heartbeat = time.monotonic() + HEARTBEAT_SECONDS',source)



    def test_unqualified_output_retains_failed_server_status_without_qualifying_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); runtime=root/'r'; runtime.mkdir()
            evidence=root/'evidence'; evidence.mkdir()
            graph=runtime/generator.GRAPH; graph.parent.mkdir(parents=True); graph.write_bytes(b'written before native proof failed')
            (runtime/generator.DATE).write_bytes(struct.pack('<iII',9,0,0x10203040))
            (evidence/'server.log').write_bytes(b'native graph written then qualification failed')
            with contextlib.redirect_stdout(io.StringIO()):
                value=generator.record_native_output(evidence,runtime,2)
            self.assertEqual(value['native_generation_server_returncode'],2)
            self.assertEqual(value['status'],'unqualified_native_output')
            self.assertEqual(value['native_markers'],[])
            self.assertFalse((evidence/generator.REPORT).exists())


class AtlasNativeInputCaseTests(unittest.TestCase):
    """Actual imported directory case is reused; immutable leaf case stays exact."""

    def mixed_runtime(self, root):
        runtime = root / 'r'
        files = {'Data/Object_Library/Furniture/UpperExact.geo': b'exact upper leaf',
                 'Data/Maps/City_Zones/City_01_01/map.txt': b'exact Atlas groups',
                 'Data/Tricks/trick.txt': b'exact tricks'}
        files.update({'Data/Object_Library/Furniture/base%03d.geo' % index:
                      ('exact geometry %d' % index).encode() for index in range(100)})
        for name, raw in files.items():
            target = runtime / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        return runtime, files

    def test_inventory_canonicalizes_only_directories_and_resolves_real_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime, files = self.mixed_runtime(Path(temporary))
            before = {path.relative_to(runtime).as_posix() for path in runtime.rglob('*')}
            records = generator.geometry_inputs(runtime)
            expected = {generator.canonical_input_name(name): generator.pin(runtime / name)
                        for name in files}
            self.assertEqual(records, expected)
            self.assertIn('data/object_library/furniture/UpperExact.geo', records)
            self.assertNotIn('data/object_library/furniture/upperexact.geo', records)
            targets = generator.resolve_world_targets(runtime, records)
            for name, target in targets.items():
                self.assertEqual(target.name, Path(name).name)
                self.assertEqual(generator.pin(target), records[name])
            self.assertEqual({path.relative_to(runtime).as_posix() for path in runtime.rglob('*')}, before)
            self.assertFalse((runtime / 'data').exists())
            self.assertIn('android/guest/atlas_world_assets.py', generator.GENERATION_SOURCES)
            self.assertEqual(generator._WORLD_RESOLVE_TARGETS.__code__.co_filename,
                             str(generator.WORLD_CASE_SOURCE))

    def test_case_colliding_directories_and_leaves_are_rejected(self):
        for collision in ('Data/Object_Library/furniture/extra.geo',
                          'Data/Object_Library/Furniture/upperexact.geo'):
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as temporary:
                runtime, _ = self.mixed_runtime(Path(temporary))
                target = runtime / collision
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'conflicting immutable input')
                with self.assertRaisesRegex(ValueError, 'case-conflicting'):
                    generator.geometry_inputs(runtime)

    def test_exact_leaf_case_and_linked_owned_roots_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime, _ = self.mixed_runtime(root)
            with self.assertRaisesRegex(ValueError, 'leaf'):
                generator.resolve_world_targets(runtime, ['data/object_library/furniture/upperexact.geo'])
            linked = root / 'linked'
            linked.symlink_to(runtime, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Owned native input'):
                generator.geometry_inputs(linked)
            with self.assertRaisesRegex(ValueError, 'Owned native input'):
                generator.resolve_world_targets(linked, ['data/tricks/trick.txt'])

    def test_mixed_case_cache_roots_are_private_in_cold_mirror(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime, _ = self.mixed_runtime(root)
            private = ('Data/Bin/defs.bin', 'Data/GeoBin/world.bin', 'Data/Server/cache.bin')
            for name in private:
                target = runtime / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'private native cache')
            cold = root / 'c'
            generator.mirror_cold_runtime(runtime, cold)
            self.assertTrue(os.path.samefile(runtime / 'Data/Tricks/trick.txt',
                                            cold / 'Data/Tricks/trick.txt'))
            for name in private:
                self.assertFalse(os.path.samefile(runtime / name, cold / name))
                (runtime / name).write_bytes(b'changed native cache')
                self.assertEqual((cold / name).read_bytes(), b'private native cache')
            self.assertEqual(generator.geometry_inputs(runtime), generator.geometry_inputs(cold))

    def test_optional_overlay_reuses_imported_parent_case_and_strict_leafs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runtime, _ = self.mixed_runtime(root)
            archive = root / 'visual.zip'
            files = {'data/object_library/furniture/optional%03d.geo' % index:
                     ('original optional %d' % index).encode()
                     for index in range(generator.VISUAL_OBJECT_GEOS)}
            with generator.zipfile.ZipFile(archive, 'w') as target:
                for name, raw in files.items():
                    target.writestr(name, raw)
            pins = {name: {'bytes': len(raw), 'sha256': generator.hashlib.sha256(raw).hexdigest()}
                    for name, raw in files.items()}
            manifest = root / 'visual.json'
            manifest.write_bytes(generator.canonical({'archive': generator.pin(archive), 'files': pins}))
            _, selected = generator.overlay_object_geometry(archive, manifest, runtime)
            self.assertEqual(selected, pins)
            targets = generator.resolve_world_targets(runtime, selected)
            self.assertTrue(all(path.parent == runtime / 'Data/Object_Library/Furniture'
                                for path in targets.values()))
            self.assertFalse((runtime / 'data').exists())
            self.assertEqual({name: generator.pin(path) for name, path in targets.items()}, pins)
            exact = targets['data/object_library/furniture/optional000.geo']
            exact.rename(exact.with_name('OPTIONAL000.geo'))
            with self.assertRaisesRegex(ValueError, 'leaf'):
                generator.overlay_object_geometry(archive, manifest, runtime)

    def test_retained_compile_requires_exact_source_binary_and_fixed_artifact(self):
        build_input = {'source_commit': 'a' * 40, 'active_algorithms': {'actual.c': 'b' * 64}}
        binary = {'bytes': 300, 'sha256': 'c' * 64}
        value = {'format': 1, 'status': 'reused_exact_compatible_native_compile',
                 'compile': generator.HOST_COMPILE_REUSE,
                 'build_input': build_input, 'generator': binary}
        self.assertEqual(generator.validate_compile_reuse_receipt(value, build_input, binary), value)
        for changed in ({**value, 'status': 'native_graph_qualified'},
                        {**value, 'compile': {**generator.HOST_COMPILE_REUSE, 'run_id': 1}},
                        {**value, 'build_input': {'different.c': 'd' * 64}},
                        {**value, 'generator': {**binary, 'sha256': 'd' * 64}}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                generator.validate_compile_reuse_receipt(changed, build_input, binary)


if __name__ == '__main__': unittest.main()
