#!/usr/bin/env python3
"""Pure hosted-runner controls only; never claim local Windows/server execution."""
import json
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import capture_disposable as c
import delivery as d


class CaptureControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='coh-catalog-capture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_requires_actual_hosted_environment_before_mutations(self):
        with mock.patch.dict(os.environ, {'RUNNER_ENVIRONMENT': 'local'}, clear=True):
            with self.assertRaises(d.Refused): c.capture(None)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_inventory_dereferences_into_separate_private_files(self):
        source = self.root / 'source'; source.mkdir()
        original = self.root / 'immutable'; original.write_bytes(b'original')
        (source / 'linked').symlink_to(original)
        (source / 'real').write_bytes(b'real')
        target = self.root / 'target'
        first = c.inventory(source, target)
        self.assertEqual(first, c.inventory(source))
        self.assertEqual(first, c.inventory(target))
        self.assertFalse((target / 'linked').is_symlink())
        (target / 'linked').write_bytes(b'changed')
        self.assertEqual(original.read_bytes(), b'original')
        self.assertEqual(first, c.inventory(source))

    def test_linked_directories_refused(self):
        source = self.root / 'source'; source.mkdir()
        (source / 'linked-dir').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(d.Refused): c.inventory(source)

    def test_existing_copy_target_preserved(self):
        source = self.root / 'source'; source.mkdir()
        target = self.root / 'target'; target.mkdir()
        (target / 'keep').write_bytes(b'keep')
        with self.assertRaises(FileExistsError): c.inventory(source, target)
        self.assertEqual((target / 'keep').read_bytes(), b'keep')

    def test_file_limit_before_payload(self):
        source = self.root / 'source'; source.mkdir(); (source / 'a').write_bytes(b'a')
        with mock.patch.object(c, 'MAX_FILES', 0):
            with self.assertRaises(d.Refused): c.inventory(source)

    def test_byte_limit_before_payload(self):
        source = self.root / 'source'; source.mkdir(); (source / 'a').write_bytes(b'a')
        with mock.patch.object(c, 'MAX_BYTES', 0):
            with self.assertRaises(d.Refused): c.inventory(source)

    def test_stable_order(self):
        a = self.root / 'a'; a.mkdir(); b = self.root / 'b'; b.mkdir()
        for name in ('c', 'b', 'a'): (a / name).write_text(name)
        for name in ('a', 'b', 'c'): (b / name).write_text(name)
        self.assertEqual(c.inventory(a), c.inventory(b))

    def dispatch(self, **changes):
        value = dict(magic=b'COHDBP1\0', version=1, size=128, pid=42, tid=43,
                     seq=2, stage=1, loops=1, flags=0, count=1)
        value.update(changes)
        raw = struct.pack('<8s9I', *value.values()) + bytes(4096-44)
        path = self.root / 'dispatch'; path.write_bytes(raw)
        return path

    def test_actual_format_dispatch_admission(self):
        self.assertTrue(c.dispatch_ready(self.dispatch(), {'1': 'READY'}))
        self.assertFalse(c.dispatch_ready(self.dispatch(seq=1), {'1': 'READY'}))
        self.assertFalse(c.dispatch_ready(self.dispatch(seq=0), {'1': 'READY'}))
        self.assertFalse(c.dispatch_ready(self.dispatch(loops=0), {'1': 'READY'}))

    def test_bad_dispatch_rejected(self):
        for key, bad in (('magic', b'BADMAGIC'), ('version', 2), ('size', 127),
                         ('pid', 0), ('tid', 0), ('stage', 2), ('flags', 1), ('count', 2)):
            with self.subTest(field=key):
                with self.assertRaises(d.Refused): c.dispatch_ready(self.dispatch(**{key: bad}), {'1': 'READY'})

    def test_missing_dispatch(self):
        self.assertFalse(c.dispatch_ready(self.root/'absent', {'1': 'READY'}))

    def test_dispatch_snapshot_retains_stall_without_claiming_ready(self):
        value = c.dispatch_snapshot(self.dispatch(loops=0), {'1': 'INITIALIZED'})
        self.assertEqual(value['stage_name'], 'INITIALIZED')
        self.assertEqual(value['loop_count'], 0)
        self.assertTrue(value['present'] and value['stable'])
        self.assertEqual(c.dispatch_snapshot(self.root/'absent', {}), {'present':False,'stable':False})

    def test_wine_native_driver_floor(self):
        for raw in (b'wine-9.13\n', b'wine-10.0\n', b'wine-11.0 (Ubuntu 11.0~noble-1)\n'):
            self.assertEqual(c.wine_version(raw), raw.decode().strip())
        for raw in (b'wine-9.0 (Ubuntu 9.0~repack-4build3)', b'wine-9.12', b'wine-8.23',
                    b'wine-11', b'unknown', b'wine-11.0\nextra'):
            with self.subTest(raw=raw):
                with self.assertRaises(d.Refused): c.wine_version(raw)

    def test_private_activity_counts_exclude_sql_and_inherited_environment(self):
        cluster = SimpleNamespace(root=self.root, meta={'database':'coh_catalog_disposable',
                                                        'port':15437,'bin':'/private/bin'})
        result = SimpleNamespace(returncode=0, stdout='{"sessions":2,"active":1,"waiting_locks":0,"schema_ddl":1}')
        with mock.patch.dict(os.environ, {'PGHOST':'external','PGPASSWORD':'DO_NOT_INHERIT'}):
            with mock.patch.object(c.subprocess, 'run', return_value=result) as run:
                value = c.postgres_activity(cluster)
        self.assertEqual(value['sessions'], 2)
        self.assertFalse(value['raw_sql_included'])
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs['env']['PGHOST'], '127.0.0.1')
        self.assertNotIn('PGPASSWORD', kwargs['env'])
        self.assertEqual(kwargs['timeout'], 3)
        self.assertIn("usename='coh_game'", kwargs['input'])
        self.assertNotIn('select query', kwargs['input'].lower())

    def test_private_activity_rejects_malformed_counts_and_database(self):
        cluster = SimpleNamespace(root=self.root, meta={'database':'coh_catalog_disposable',
                                                        'port':15437,'bin':'/private/bin'})
        for value in ({'sessions':True,'active':0,'waiting_locks':0,'schema_ddl':0},
                      {'sessions':1001,'active':0,'waiting_locks':0,'schema_ddl':0},
                      {'query':'sensitive'}, {}):
            with mock.patch.object(c.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(value))):
                with self.assertRaises(d.Refused): c.postgres_activity(cluster)
        cluster.meta['database'] = "bad'identifier"
        with mock.patch.object(c.subprocess, 'run') as run:
            with self.assertRaises(d.Refused): c.postgres_activity(cluster)
            run.assert_not_called()

    def test_existing_driver_validator_selects_observed_registration(self):
        _, db, _, _ = c.fixture_modules()
        namespace = {'require':d.require, 're':c.re}
        db.load_functions('android/guest/diagnostic.py', ('validate_odbc_driver',), namespace)
        for name in ('PostgreSQL Unicode', 'PostgreSQL Unicode(x86)'):
            value = namespace['validate_odbc_driver']('COH_ODBC_DRIVER_V1 NAME '+name+'\n'
                'COH_ODBC_DRIVER_V1 DLL C:\\private\\psqlodbc35w.dll\nCOH_ODBC_DRIVER_V1 PASS bits=32\n')
            self.assertEqual(value['driver_name'], name)
            self.assertTrue(value['driver_dll_loaded'])
        with self.assertRaises(d.Refused): namespace['validate_odbc_driver']('COH_ODBC_DRIVER_V1 FAIL stage=load_driver error=126')

    def test_dispatch_reserved_tail(self):
        path = self.dispatch(); raw = bytearray(path.read_bytes()); raw[127] = 1; path.write_bytes(raw)
        with self.assertRaises(d.Refused): c.dispatch_ready(path, {'1': 'READY'})

    @staticmethod
    def sink(**changes):
        values = dict(status=1, producer_status=0, failure_file=0, failure_slot=0, files=508,
                      definitions=12000, slots=12005, children=35000, wire_bytes=1000,
                      total_bytes=2048, emitted_bytes=2048, written_bytes=2048,
                      partial_remaining=0, partial_removed=0)
        values.update(changes)
        return ('COH_NATIVE_SCENE_CATALOG_V1 ' + ' '.join('%s=%d'%row for row in values.items())+'\n').encode()

    def test_sink_observation_exact_scope(self):
        self.assertEqual(c.sink_observation(self.sink())['files'], 508)
        self.assertIsNone(c.sink_observation(b'unrelated log'))

    def test_failed_duplicate_truncated_sink(self):
        for raw in (self.sink(status=2), self.sink(producer_status=1), self.sink(partial_remaining=1),
                    self.sink(written_bytes=1), self.sink()+self.sink()):
            with self.assertRaises(d.Refused): c.sink_observation(raw)
        self.assertIsNone(c.sink_observation(self.sink()[:40]))

    def test_log_limit(self):
        path = self.root/'log'; path.write_bytes(b'123')
        with mock.patch.object(c, 'MAX_LOG', 2):
            with self.assertRaises(d.Refused): c.bounded_logs([path])

    def test_partial_pg_init_recovers_owned_cluster_and_stops(self):
        pg_root = self.root/'pg'; pg_root.mkdir()
        (pg_root/'cluster.json').write_text('{}'); (pg_root/'credentials.json').write_text('{}')
        cluster = mock.Mock(root=pg_root)
        cluster.run.side_effect = [mock.Mock(returncode=0), mock.Mock(returncode=3)]
        module = mock.Mock(); module.Cluster.return_value = cluster
        self.assertTrue(c.cleanup_postgresql(None, pg_root, module))
        module.Cluster.assert_called_once_with(pg_root); cluster.stop.assert_called_once()

    def test_partial_pg_unknown_or_running_never_passes_cleanup(self):
        pg_root = self.root/'pg'; pg_root.mkdir()
        with self.assertRaises(d.Refused): c.cleanup_postgresql(None, pg_root, mock.Mock())
        for codes in ((4,), (0, 0)):
            cluster = mock.Mock(root=pg_root)
            cluster.run.side_effect = [mock.Mock(returncode=n) for n in codes]
            with self.assertRaises(d.Refused): c.cleanup_postgresql(cluster, pg_root, mock.Mock())

    def test_exited_leader_never_proves_descendant_group_cleanup(self):
        process = mock.Mock(pid=12345)
        with mock.patch.object(os, 'killpg', return_value=None) as probe:
            self.assertFalse(c.process_group_absent(process))
            probe.assert_called_once_with(12345, 0)
        with mock.patch.object(os, 'killpg', side_effect=ProcessLookupError):
            self.assertTrue(c.process_group_absent(process))
        with mock.patch.object(os, 'killpg', side_effect=PermissionError):
            self.assertFalse(c.process_group_absent(process))

    def test_windows_path(self):
        self.assertEqual(c.windows_path(self.root/'file'), 'Z:'+str(self.root/'file').replace('/', '\\'))
        with self.assertRaises(d.Refused): c.windows_path(self.root/'ads:stream')

    def private_drive(self):
        prefix = self.root/'wine-prefix'; prefix.mkdir()
        drive = prefix/'drive_c'; drive.mkdir()
        devices = prefix/'dosdevices'; devices.mkdir()
        (devices/'c:').symlink_to('../drive_c', target_is_directory=True)
        return prefix, drive

    def test_capture_destination_is_private_c_drive_and_never_z(self):
        _, drive = self.private_drive()
        path, native = c.capture_destination(self.root)
        self.assertEqual(path, drive/'coh-native-catalog'/'catalog.cohcat')
        self.assertEqual(native, r'C:\coh-native-catalog\catalog.cohcat')
        self.assertTrue(path.parent.is_dir())
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.assertFalse(path.exists())
        with self.assertRaises(FileExistsError): c.capture_destination(self.root)

    def test_capture_destination_rejects_redirected_drive(self):
        prefix, drive = self.private_drive()
        mapping = prefix/'dosdevices'/'c:'; mapping.unlink(); mapping.symlink_to(self.root)
        with self.assertRaises(d.Refused): c.capture_destination(self.root)
        self.assertFalse((drive/'coh-native-catalog').exists())

    def test_capture_destination_rejects_linked_drive_directory(self):
        prefix, drive = self.private_drive()
        drive.rmdir(); drive.symlink_to(self.root)
        with self.assertRaises(d.Refused): c.capture_destination(self.root)
        self.assertFalse((self.root/'coh-native-catalog').exists())

    def test_path_probe_extracts_exact_readonly_original_functions(self):
        raw = (Path(c.__file__).parent/'source_sink.inc').read_bytes()
        functions = c.path_probe_builder.original_path_functions(raw)
        self.assertIn('coh_catalog_sink_path(', functions)
        self.assertIn('COH_CATALOG_SINK_PATH_MAX 240u', functions)
        self.assertEqual(functions.count('static int '), 2)
        for forbidden in ('CreateFile', 'WriteFile', 'MoveFile', 'DeleteFile', 'coh_source_catalog_export'):
            self.assertNotIn(forbidden, functions)
        with self.assertRaises(d.Refused): c.path_probe_builder.original_path_functions(raw+b'\n')

    def path_observation(self, admitted=True):
        return dict(schema='coh-win32-catalog-path-v1',read_only=True,pointer_bits=32,admitted=admitted,
                    root_attributes=16 if admitted else 1040,root_error=0,
                    target_attributes=0xffffffff,target_error=2,
                    parents=[dict(component_end=21,attributes=16,error=0)])

    def test_path_probe_requires_positive_c_and_negative_root_reparse(self):
        for admitted in (True, False):
            value = self.path_observation(admitted)
            self.assertEqual(c.validate_path_observation(json.dumps(value).encode(), admitted), value)
        for key, bad in (('admitted',False),('read_only',False),('pointer_bits',64),('root_attributes',1040),
                         ('root_error',5),('target_attributes',128),('target_error',3),('parents',[])):
            value=self.path_observation();value[key]=bad
            with self.subTest(field=key):
                with self.assertRaises(d.Refused): c.validate_path_observation(json.dumps(value).encode(), True)
        value=self.path_observation();value['parents'][0]['attributes']=1040
        with self.assertRaises(d.Refused): c.validate_path_observation(json.dumps(value).encode(), True)
        with self.assertRaises(d.Refused): c.validate_path_observation(b'{}', True)



if __name__ == '__main__': unittest.main()
