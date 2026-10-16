#!/usr/bin/env python3
"""Original producer fixtures, ZIP bounds, attribution and privacy controls."""
import ast
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import time
import types
import unittest
import warnings
from unittest import mock
import zipfile

import read_startup_receipts as r

ROOT = Path(__file__).resolve().parents[3]
PINNED = 'cda93d96f8696e6a0f2ec6940a0c96e5b852f281'
SID = 'a' * 32
SECRET = 'PRIVATE_ACCOUNT_PATH_OR_PASSWORD'
SOURCE_PINS = {
    'android/guest/local_character_server.py': '82915cdab3573843c32961478f4e015c27a72e180d75db177e439a081305e180',
    'android/guest/diagnostic.py': '748975acf9b0c01b094166150112306edfc12c18656bc4b1926e00ea9460dbaf'}


def original(path, names, namespace):
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', PINNED + ':' + path])
    assert hashlib.sha256(raw).hexdigest() == SOURCE_PINS[path]
    tree = ast.parse(raw)
    found = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names]
    assert len(found) == len(names)
    exec(compile(ast.fix_missing_locations(ast.Module(body=found, type_ignores=[])), path, 'exec'), namespace)
    return {name: namespace[name] for name in names}


def original_file_fixture():
    """Execute unchanged original record + persistence functions on fake inputs.

    Files are disposable. Fake MapServer bytes, graph status and clock are
    intentionally synthetic; this qualifies source field/file handling only.
    """
    with tempfile.TemporaryDirectory() as directory:
        state = Path(directory); runtime = state / SECRET; runtime.mkdir()
        binary = runtime / 'MapServer.exe'; binary.write_bytes(b'fixture-not-executable')
        pin = lambda p: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        base = types.SimpleNamespace(redacted_value=lambda value, secrets: copy.deepcopy(value),
            private_write=lambda path, data: Path(path).write_text(data), DiagnosticError=ValueError)
        env = {'Path': Path, 'os': os, 'stat': stat, 'json': json,
            'time': types.SimpleNamespace(time=lambda: 1792108800),
            'require': r.base.need, 'base': base,
            'server_cache_package': types.SimpleNamespace(file_pin=pin),
            'server_fx_catalog': types.SimpleNamespace(TARGET='data/bin/fxinfo.bin', PROJECTED={})}
        methods = original('android/guest/local_character_server.py',
            ['record_startup_preparation', 'persist_startup_observation'], env)
        owner = types.SimpleNamespace(args=types.SimpleNamespace(session_id=SID))
        ctx = types.SimpleNamespace(state=state, secrets=[], report={'session_id': SID, 'account': SECRET})
        server = types.SimpleNamespace(owner=owner, ctx=ctx, creation_report={},
            map_package={'files': {'MapServer.exe': pin(binary)}})
        server.persist_startup_observation = types.MethodType(methods['persist_startup_observation'], server)
        record = types.MethodType(methods['record_startup_preparation'], server)
        record(1, runtime, {}, {}, {'status': 'reused_verified_graph',
            'input_files_checked': 777, 'input_payload_bytes_hashed': 0,
            'input_validation': SECRET}, 1.25, {'atlas_beacon_graph': 1.25})
        receipt = (state / 'map-startup-observation.json').read_bytes()
        assert (state / 'latest-report.json').is_file()
        return receipt


def original_stage_fixture():
    counter = iter(range(20))
    utc = lambda: '2026-10-16T00:00:%02d+00:00' % next(counter)
    env = {'json': json, 'utc': utc, 'redacted_value': lambda fields, secrets: fields}
    methods = original('android/guest/diagnostic.py', ['event', 'stage', 'passed'], env)
    ctx = types.SimpleNamespace(secrets=[], report={'stages': []}, check=lambda: None)
    for name, method in methods.items(): setattr(ctx, name, types.MethodType(method, ctx))
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        ctx.stage('local_dbserver_startup'); ctx.passed(private_value=SECRET)
        ctx.stage('local_atlas_startup'); ctx.passed()
    return ctx.report['stages'], stdout.getvalue().encode()



def original_retry_fixture():
    # Execute the unchanged source methods with deterministic retry clocks.
    clock = {'value': '2026-10-16T00:00:00+00:00'}
    env = {'json': json, 'utc': lambda: clock['value'],
           'redacted_value': lambda fields, secrets: fields}
    methods = original('android/guest/diagnostic.py', ['event', 'stage', 'passed'], env)
    ctx = types.SimpleNamespace(secrets=[], report={'stages': []}, check=lambda: None)
    for name, method in methods.items(): setattr(ctx, name, types.MethodType(method, ctx))
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        ctx.stage('local_atlas_startup')
        clock['value'] = '2026-10-16T00:00:05+00:00'; ctx.event('stage', status='failed')
        clock['value'] = '2026-10-16T00:00:10+00:00'; ctx.stage('local_atlas_startup')
        clock['value'] = '2026-10-16T00:00:15+00:00'; ctx.passed()
    return ctx.report['stages'], stdout.getvalue().encode()


def conventional():
    return {'format': 1, 'session_id': SID, 'scope': 'actual_character_reopen_guest',
        'character_reopen': {'session_id': SID, 'private_map_data': {'server_data_cache':
            {'reused': True, 'immutable_directory_checks': 9}}, 'prepared_server_caches':
            {'status': 'preserved_existing_native_caches', 'preserved_existing_files': 4}}, 'stages': []}


class ExistingReceiptTests(unittest.TestCase):
    def test_original_file_producer_is_projected(self):
        raw = original_file_fixture(); out = r.analyze_document(r.base.parse(raw))
        self.assertEqual(out['maps'][0]['beacon_outcome'], 'hit')
        self.assertEqual(out['maps'][0]['beacon']['input_files_checked'], 777)
        self.assertFalse(out['maps'][0]['source_identities_independently_verified_by_this_reader'])
        for secret in (SECRET, SID): self.assertNotIn(secret, json.dumps(out))

    def test_original_timestamp_rows_and_log_pairs(self):
        rows, raw = original_stage_fixture()
        self.assertEqual([v['recorded_wall_interval_ms'] for v in r.stage_intervals(rows)], [2000, 2000])
        log = r.analyze_log(raw)
        self.assertEqual([v['recorded_wall_interval_ms'] for v in log['stage_intervals']], [2000, 2000])
        self.assertEqual(log['session_binding'], 'unbound_log_never_joined_to_receipts')
        self.assertNotIn(SECRET, json.dumps(log))

    def test_original_retry_does_not_reuse_failed_start(self):
        rows, raw = original_retry_fixture()
        self.assertEqual(len(rows), 2)
        self.assertIsNone(r.stage_intervals(rows)[0]['recorded_wall_interval_ms'])
        self.assertEqual(r.stage_intervals(rows)[1]['recorded_wall_interval_ms'], 5000)
        self.assertEqual([p['recorded_wall_interval_ms'] for p in r.analyze_log(raw)['stage_intervals']], [5000])

    def test_repeated_running_uses_latest_observation_with_explicit_scope(self):
        rows, raw = original_retry_fixture()
        lines = [line for line in raw.splitlines() if b'failed' not in line]
        out = r.analyze_log(b'\n'.join(lines))
        self.assertEqual(out['stage_intervals'][0]['recorded_wall_interval_ms'], 5000)
        self.assertTrue(out['running_event_may_be_progress_heartbeat'])
        self.assertIn('not_total_stage_duration', out['stage_intervals'][0]['scope'])

    def test_terminal_interruption_prevents_later_pass_pair(self):
        start = {'type':'stage','stage':'local_atlas_startup','status':'running','time_utc':'2026-10-16T00:00:00Z'}
        passed = dict(start, status='passed', time_utc='2026-10-16T00:00:15Z')
        for terminal in ({'type':'stage','status':'failed'}, {'type':'result','status':'cancelled'},
                         {'type':'error'}, {'type':'server_stopped'}, {'type':'result','status':'passed'}):
            raw = '\n'.join(json.dumps(row) for row in (start, terminal, passed)).encode()
            self.assertEqual(r.analyze_log(raw)['stage_intervals'], [])

    def test_interleaved_stage_does_not_close_previous_stage(self):
        def event(stage, status, second):
            return {'type':'stage','stage':stage,'status':status,'time_utc':'2026-10-16T00:00:%02dZ'%second}
        raw = '\n'.join(json.dumps(row) for row in (
            event('local_atlas_startup','running',0), event('local_dbserver_startup','running',5),
            event('local_atlas_startup','passed',10), event('local_dbserver_startup','passed',15))).encode()
        out = r.analyze_log(raw)
        self.assertEqual([p['stage'] for p in out['stage_intervals']], ['local_dbserver_startup'])
        self.assertEqual(out['stage_intervals'][0]['recorded_wall_interval_ms'], 10000)

    def test_no_wall_duration_without_both_timestamps(self):
        self.assertIsNone(r.stage_intervals([{'stage': 'local_atlas_startup', 'elapsed_seconds': 999}])[0]['recorded_wall_interval_ms'])

    def test_negative_wall_duration_rejected(self):
        rows, _ = original_stage_fixture(); rows[0]['finished_utc'] = '2025-01-01T00:00:00Z'
        with self.assertRaisesRegex(r.base.Rejected, 'STAGE_CLOCK'): r.stage_intervals(rows)

    def test_unzoned_clock_unknown(self):
        self.assertIsNone(r.utc_ms('2026-10-16T12:00:00'))
        self.assertIsNone(r.utc_ms('2026-10-16T12:00:00-05:00'))

    def test_cache_hits_and_refusal_are_explicit(self):
        doc = conventional(); out = r.analyze_document(doc)
        self.assertEqual(out['cache_outcomes'], {'server_data': 'hit', 'definitions': 'preserved', 'beacon': 'unknown'})
        doc['character_reopen']['private_map_data']['server_data_cache'] = {'reused': False, 'reuse_refused': SECRET}
        doc['character_reopen']['prepared_server_caches'] = {'status': 'skipped_native_fallback', 'reason': SECRET}
        out = r.analyze_document(doc)
        self.assertEqual(out['cache_outcomes']['server_data'], 'refused')
        self.assertEqual(out['cache_outcomes']['definitions'], 'refused')
        self.assertNotIn(SECRET, json.dumps(out))

    def test_cross_session_nested_receipt_rejected(self):
        doc = conventional(); doc['character_reopen']['session_id'] = 'b' * 32
        with self.assertRaisesRegex(r.base.Rejected, 'CROSS_SESSION'): r.analyze_document(doc)

    def test_combined_missing_detail_stays_unknown(self):
        doc = {'format': 1, 'app_id': r.base.APP, 'session_id': SID,
               'server_preparation_phase_seconds': {'warm_schema_restore': 1, 'atlas_beacon_graph': 23}}
        out = r.analyze_document(doc)
        self.assertEqual(set(out['cache_outcomes'].values()), {'unknown'})
        self.assertTrue(out['source_report_warm_phase_present'])

    def test_duplicate_map_id_or_unbounded_map_rejected(self):
        with self.assertRaisesRegex(r.base.Rejected, 'MAP_BOUND_OR_ID'): r.map_rows({'9': {}})
        with self.assertRaisesRegex(r.base.Rejected, 'MAP_IDENTITY'): r.map_rows({'1': {'format': 1, 'map_id': 5}})

    def test_raw_log_does_not_guess_clock_or_cache(self):
        out = r.analyze_log((SECRET+' reused_verified_graph\nMap startup took 2 seconds\n').encode())
        self.assertEqual(out['stage_intervals'], [])
        self.assertEqual(set(out['cache_outcomes'].values()), {'unknown'})
        self.assertNotIn(SECRET, json.dumps(out))

    def test_log_missing_finish_is_unknown(self):
        out = r.analyze_log(b'{"type":"stage","stage":"local_atlas_startup","status":"running","time_utc":"2026-10-16T00:00:00Z"}')
        self.assertTrue(out['unclosed_stage']); self.assertEqual(out['stage_intervals'], [])

    def test_zip_member_selected_and_hashed_without_extracting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'input.zip'; raw = original_file_fixture()
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('client-evidence/map-startup-observation.json',raw)
                z.writestr('private-ignored.txt',SECRET)
            before = path.read_bytes()
            actual,pins = r.read_input(path,['client-evidence/map-startup-observation.json'])
            self.assertEqual(actual,raw); self.assertEqual(pins[0]['sha256'],r.digest(before))
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_nested_zip_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            inner = io.BytesIO()
            with zipfile.ZipFile(inner,'w') as z:z.writestr('latest-report.json',json.dumps(conventional()))
            path=Path(directory)/'input.zip'
            with zipfile.ZipFile(path,'w') as z:z.writestr('report.zip',inner.getvalue())
            raw,pins=r.read_input(path,['report.zip','latest-report.json'])
            self.assertEqual(len(pins),3); self.assertEqual(r.analyze_document(r.base.parse(raw))['cache_outcomes']['server_data'],'hit')
            with self.assertRaisesRegex(r.base.Rejected,'NESTING_BOUND'):r.read_input(path,['a','b','c'])

    def test_zip_bad_names_duplicates_links_rejected(self):
        for bad in ('../escape','/absolute','back\\slash'):
            raw=io.BytesIO()
            with zipfile.ZipFile(raw,'w') as z:z.writestr(bad,b'{}')
            with self.assertRaisesRegex(r.base.Rejected,'MEMBER_NAME'):r.member_body(io.BytesIO(raw.getvalue()),bad,100)
        for mode in ('duplicate','link'):
            raw=io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with zipfile.ZipFile(raw,'w') as z:
                    z.writestr('a',b'{}')
                    if mode=='duplicate':z.writestr('a',b'{}')
                    else:
                        item=zipfile.ZipInfo('b');item.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(item,b'file')
            with self.assertRaises(r.base.Rejected):r.member_body(io.BytesIO(raw.getvalue()),'a',100)

    def test_forged_count_does_not_allocate_unbounded_zip_metadata(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            for index in range(257): archive.writestr('entry-%03d'%index, b'{}')
        raw = bytearray(buffer.getvalue()); end = raw.rfind(b'PK\x05\x06')
        struct.pack_into('<HH', raw, end+8, 1, 1)  # lie about actual central headers
        with mock.patch.object(r.zipfile, 'ZipFile', side_effect=AssertionError('constructed too soon')):
            with self.assertRaisesRegex(r.base.Rejected, 'DIRECTORY_ENTRY_BOUND'):
                r.member_body(io.BytesIO(raw), 'entry-000', 100)

    def test_zip64_multidisk_and_directory_bounds_admitted_before_constructor(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive: archive.writestr('entry', b'{}')
        original = buffer.getvalue()
        for mutation, error in (('zip64','ZIP64_UNSUPPORTED'),('disk','MULTIDISK_UNSUPPORTED'),
                                ('offset','DIRECTORY_BYTE_BOUND'),('size','DIRECTORY_BYTE_BOUND'),
                                ('count','DIRECTORY_COUNT_MISMATCH')):
            raw = bytearray(original); end = raw.rfind(b'PK\x05\x06')
            if mutation == 'zip64': struct.pack_into('<HH',raw,end+8,0xffff,0xffff)
            if mutation == 'disk': struct.pack_into('<H',raw,end+4,1)
            if mutation == 'offset': struct.pack_into('<I',raw,end+16,len(raw)+10)
            if mutation == 'size': struct.pack_into('<I',raw,end+12,r.MAX_DIRECTORY+1)
            if mutation == 'count': struct.pack_into('<HH',raw,end+8,0,0)
            with mock.patch.object(r.zipfile,'ZipFile',side_effect=AssertionError('constructed too soon')):
                with self.assertRaisesRegex(r.base.Rejected,error):r.member_body(io.BytesIO(raw),'entry',100)

    def test_embedded_nul_name_rejected_before_zipinfo_truncates_it(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive: archive.writestr('entryX', b'{}')
        raw = bytearray(buffer.getvalue()); central = raw.find(b'PK\x01\x02')
        raw[central+r.CENTRAL.size+5] = 0
        with mock.patch.object(r.zipfile,'ZipFile',side_effect=AssertionError('constructed too soon')):
            with self.assertRaisesRegex(r.base.Rejected,'MEMBER_NAME'):
                r.member_body(io.BytesIO(raw),'entry',100)

    def test_invalid_json_and_nonfinite_rejected(self):
        for raw in ('{"session_id":"a","session_id":"b"}', '{"clock":NaN}'):
            with self.assertRaises(r.base.Rejected):r.base.parse(raw)

    def test_cli_errors_do_not_echo_private_path(self):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):status=r.main(['/absent/'+SECRET])
        self.assertEqual(status,2);self.assertNotIn(SECRET,output.getvalue())


if __name__ == '__main__':unittest.main()
