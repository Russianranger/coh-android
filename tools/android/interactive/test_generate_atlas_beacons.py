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
from unittest import mock
import copy
import hashlib
import zipfile

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
            self.assertEqual(record['cold_difference']['missing_count'],2)
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

    def test_recovered_output_capture_precedes_native_crc_validation_in_actual_producer(self):
        import inspect
        source=inspect.getsource(generator.generate)
        self.assertLess(source.index('record_native_output(evidence, runtime,'),
                        source.index('witness = native_evidence'))
        self.assertIn("require(recovering, 'This qualification lane requires the exact retained real primary graph')",source)
        self.assertNotIn("for role, flags in roles",source)



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


class AtlasPrimaryRecoveryTests(unittest.TestCase):
    """Synthetic receipts test strict recovery gates, never native acceptance."""

    def metadata(self):
        source = copy.deepcopy(generator.PRIMARY_RECOVERY)
        return {'format': 1, 'status': 'authenticated_failed_run_primary_candidate', 'source': source,
            'run': {'id': source['run_id'], 'head_sha': source['repository_commit'],
                'head_branch': 'codex/character-persistence-continuation',
                'path': '.github/workflows/android-atlas-beacon-generation.yml',
                'status': 'completed', 'conclusion': 'failure', 'run_attempt': 1},
            'job': {'id': source['job_id'], 'name': 'generate', 'conclusion': 'failure',
                'source_stage_conclusion': 'success', 'compile_conclusion': 'success'},
            'artifact': {'id': source['artifact']['id'], 'name': 'coh-ui-beacon-generation-evidence',
                'expired': False, 'size_in_bytes': source['artifact']['bytes'],
                'digest': 'sha256:' + source['artifact']['sha256'],
                'run_id': source['run_id'], 'head_sha': source['repository_commit']}}

    def test_original_failure_is_authenticated_without_relabeling_success(self):
        value = self.metadata()
        self.assertEqual(generator.validate_recovery_metadata(value), value)
        for scope, key, wrong in (('run','conclusion','success'), ('run','head_sha','a'*40),
                ('run','run_attempt',2), ('job','compile_conclusion','failure'),
                ('artifact','expired',True), ('artifact','run_id',1),
                ('artifact','digest','sha256:'+'b'*64), ('source','run_conclusion','success')):
            changed = copy.deepcopy(value); changed[scope][key] = wrong
            with self.subTest(scope=scope,key=key), self.assertRaises(ValueError):
                generator.validate_recovery_metadata(changed)

    def test_none_geometry_profile_is_no_longer_an_accepted_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            common = {'data/maps/a.txt': {'bytes':1,'sha256':'a'*64}}
            required = {'data/object_library/a.geo': {'bytes':1,'sha256':'b'*64}}
            with contextlib.redirect_stdout(io.StringIO()):
                failed = generator.record_profile_inventory(Path(temporary),common,required,{**common,**required},common)
                passed = generator.record_profile_inventory(Path(temporary),common,required,{**common,**required},{**common,**required})
            self.assertEqual(failed['status'],'mismatch')
            self.assertEqual(failed['cold_difference']['missing_count'],1)
            self.assertEqual(passed['status'],'passed')
            self.assertEqual(generator.PROFILES,('required_geometry_cold','client_visual_reopen'))

    def fixture(self, root, *, mutation=None, mutate_source=False):
        source_root = root/'source'; source_root.mkdir()
        sources = {}
        for name in generator.GENERATION_SOURCES:
            raw = ('synthetic unchanged input: '+name).encode()
            target = source_root/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
            sources[name] = generator.pin(target)
        original = root/'original-generation-source.py'
        original.write_bytes(b'synthetic historical original producer')
        sources['tools/android/interactive/generate_atlas_beacons.py'] = generator.pin(original)
        graph = b'synthetic graph bytes; no native proof claim'
        date = struct.pack('<iII',9,0,0x10203040)
        marker = AtlasNativeEvidenceTests.MARKER
        expected = {'synthetic_native_source': 'a'*64}
        build = generator.canonical(expected)
        binary = bytearray(512); binary[:2]=b'MZ'; struct.pack_into('<I',binary,0x3c,128)
        binary[128:132]=b'PE\0\0'; struct.pack_into('<H',binary,132,0x14c)
        binary = bytes(binary)
        source = copy.deepcopy(generator.PRIMARY_RECOVERY)
        source.update(graph={'bytes':len(graph),'sha256':hashlib.sha256(graph).hexdigest()},
            date={'bytes':len(date),'sha256':hashlib.sha256(date).hexdigest()},
            generator={'bytes':len(binary),'sha256':hashlib.sha256(binary).hexdigest()},
            build_input={'bytes':len(build),'sha256':hashlib.sha256(build).hexdigest()},
            native=generator.native_evidence(marker,date))
        capture = {'format':1,'status':'unqualified_native_output','native_generation_server_returncode':0,
            'both_fresh_profile_proofs_required':True,
            'files':{'unqualified-native-graph.bcn':source['graph'],'unqualified-native-graph.bcn.date':source['date']}}
        failure = {'status':'failed','cleanup_complete':True,
            'roles':{'server':{'returncode':0},'base_world':{'returncode':3}}}
        inventory = {'status':'passed','common_files':5231,'optional_files':406,
            'common_sha256':generator.COMMON_INPUT_SHA256,'warm_sha256':generator.REQUIRED_INPUT_SHA256,
            'optional_physical_geometry_sha256':generator.VISUAL_OBJECT_SOURCE_SHA256}
        members = {'unqualified-native-graph.bcn':graph,'unqualified-native-graph.bcn.date':date,
            'unqualified-native-output.json':generator.canonical(capture),'server.log':marker,
            'native-role-failure.json':generator.canonical(failure),
            'atlas-beacon-generator-build-input.json':build,'host-only-beacon-generator.exe':binary,
            'host-only-beacon-generator.pdb':b'synthetic retained symbols',
            'native-input-profiles.json':generator.canonical(inventory)}
        if mutation is not None: mutation(members)
        archive = root/'primary.zip'
        with zipfile.ZipFile(archive,'w') as target:
            for name,raw in members.items(): target.writestr('evidence/'+name,raw)
        source['artifact'] = {**source['artifact'], **generator.pin(archive)}
        evidence = root/'evidence'; evidence.mkdir()
        build_path = root/'staged-build.json'; build_path.write_bytes(build)
        patches = [mock.patch.object(generator,'ROOT',source_root),
            mock.patch.object(generator,'PRIMARY_GENERATION_SOURCES',sources),
            mock.patch.object(generator,'PRIMARY_RECOVERY',source),
            mock.patch.object(generator.producer,'expected',return_value=expected)]
        with contextlib.ExitStack() as stack:
            for patch in patches: stack.enter_context(patch)
            if mutate_source:
                (source_root/'android/guest/atlas_world_assets.py').write_bytes(b'changed source implementation')
            metadata = root/'metadata.json'; metadata.write_bytes(generator.canonical(self.metadata()))
            result = generator.recover_primary_artifact(archive,metadata,root/'owned/MapServer.exe',
                build_path,evidence,original)
            origin,recovered_graph,recovered_date = result
            self.assertEqual(origin['original_run_conclusion'],'failure')
            self.assertEqual(origin['primary_generation_server_returncode'],0)
            self.assertTrue(origin['fresh_qualification_still_required'])
            self.assertEqual(origin['original_owned_roles'],4)
            self.assertEqual(recovered_graph,graph); self.assertEqual(recovered_date,date)
            self.assertFalse((evidence/generator.REPORT).exists())
            self.assertEqual(origin['native'],source['native'])
        return result

    def test_exact_primary_recovery_still_requires_new_fresh_profile_proofs(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.fixture(Path(temporary))

    def test_primary_recovery_refuses_wrong_output_native_witness_compile_or_cleanup(self):
        def change_json(name, key, value):
            def mutation(members):
                record=json.loads(members[name]); record[key]=value; members[name]=generator.canonical(record)
            return mutation
        mutations = [
            lambda files: files.__setitem__('unqualified-native-graph.bcn',b'foreign graph'),
            lambda files: files.__setitem__('unqualified-native-graph.bcn.date',struct.pack('<iII',9,0,0x10203041)),
            lambda files: files.__setitem__('server.log',files['server.log'].replace(b'paths=32',b'paths=31')),
            lambda files: files.__setitem__('host-only-beacon-generator.exe',b'foreign executable'),
            lambda files: files.__setitem__('atlas-beacon-generator-build-input.json',b'{}'),
            change_json('unqualified-native-output.json','native_generation_server_returncode',2),
            change_json('native-role-failure.json','cleanup_complete',False),
            change_json('native-input-profiles.json','warm_sha256','f'*64),
        ]
        for index,mutation in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary, self.assertRaises(ValueError):
                self.fixture(Path(temporary),mutation=mutation)

    def test_recovery_refuses_changed_importer_or_authoritative_path_resolver(self):
        with tempfile.TemporaryDirectory() as temporary, self.assertRaisesRegex(ValueError,'implementation changed'):
            self.fixture(Path(temporary),mutate_source=True)

    def test_fresh_private_geometry_cleanup_keeps_definition_bins_and_immutable_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime=Path(temporary)
            files={'data/geobin/maps/city_zones/city_01_01/a.bin':b'stale generated map',
                'data/geobin/object_library/a.bounds':b'stale bounds',
                'data/bin/powers.bin':b'retained definition cache',
                'data/object_library/a.geo':b'original required geometry',
                'data/geobin/readme.txt':b'owned source text'}
            for name,raw in files.items():
                path=runtime/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            record=generator.clear_private_geometry_caches(runtime)
            self.assertEqual(record['remaining_geometry_cache_files'],0)
            self.assertEqual(len(record['removed_files']),2)
            for name in ('data/bin/powers.bin','data/object_library/a.geo','data/geobin/readme.txt'):
                self.assertEqual((runtime/name).read_bytes(),files[name])
            for name in ('data/geobin/maps/city_zones/city_01_01/a.bin','data/geobin/object_library/a.bounds'):
                self.assertFalse((runtime/name).exists())

    def test_fresh_private_geometry_cleanup_refuses_linked_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime=Path(temporary);cache=runtime/'data/geobin';cache.mkdir(parents=True)
            donor=runtime/'source';donor.write_bytes(b'source')
            (cache/'unsafe.bin').symlink_to(donor)
            with self.assertRaises(ValueError):generator.clear_private_geometry_caches(runtime)

    def test_recovery_contract_pins_match_exact_unchanged_production_sources(self):
        generator.validate_primary_implementation_inputs()
        self.assertEqual(generator.PRIMARY_RECOVERY['generator']['bytes'],6880256)
        self.assertEqual(generator.PRIMARY_RECOVERY['native']['full_world_crc'],'0xb0c21ded')


if __name__ == '__main__': unittest.main()
