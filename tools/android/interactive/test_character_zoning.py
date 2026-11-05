"""Finite native zoning: owned routes, fresh receipts, ordinary saves and async guards."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_zoning as zoning

SESSION = 'a' * 32
LOG_NAME = 'logs/dbserver/entity_2026-10-10-18-00-00.log'
STAMP = '261010 18:30:10'
NOW = int(time.mktime(time.strptime(STAMP, '%y%m%d %H:%M:%S')) * 1000)
ERROR = zoning.base.DiagnosticError


def request(action='prepare', **changes):
    value = dict(format=1, session_id=SESSION, client_pid=44, character_id=1, epoch=1,
                 action=action, from_map_id=1, to_map_id=101)
    value['requested_utc_ms' if action == 'prepare' else 'sent_utc_ms'] = NOW
    value.update(changes)
    return value


def status(map_id=101, **changes):
    value = dict(loaded=True, connected=True, in_map_transfer=False, map_id=map_id,
                 static_map_id=map_id, address='127.0.0.1')
    value.update(changes)
    return value


def map_status(map_id=101):
    return f'{map_id} maps/City_Zones/City_01_01/City_01_01.txt S: 1 / 2 Ip: 127.0.0.1:{zoning.MAPS[map_id]["port"]} Mem: 100\n'


def native(message, map_id=101, timestamp=STAMP):
    return f'{timestamp} City_01_01_{zoning.MAPS[map_id]["instance"]}:127.0.0.1:127.0.0.1 "THORHERO:COHLOCAL" 0 {message}\n'


def resume(map_id=101, timestamp=STAMP):
    return native('Connection:ResumeCharacter from 127.0.0.1:41001 AuthName "COHLOCAL" ExpLevel:1', map_id, timestamp)


def logs(text, path=LOG_NAME):
    return [(path, text)]


class FiniteMapTests(unittest.TestCase):
    def test_finite_maps_and_owned_loopback_endpoints(self):
        for map_id in (1, 101):
            sample = zoning.parse_map_status(map_status(map_id), map_id)
            self.assertTrue(zoning.ready(sample, map_id))
            self.assertTrue(zoning.connected(status(map_id), map_id))
        for map_id in (True, False, '1', 2, 100, 102, None):
            self.assertFalse(zoning.supported(map_id))
            self.assertFalse(zoning.ready({}, map_id))
            self.assertFalse(zoning.connected({}, map_id))
            with self.assertRaises(ERROR):
                zoning.parse_map_status(map_status(1), map_id)

    def test_map_status_refuses_foreign_ambiguous_and_wrong_world(self):
        original = map_status()
        for text in (original.replace('101 ', '1 ', 1), original * 2,
                     original.replace('127.0.0.1', '192.168.1.10'),
                     original.replace(':7002', ':7001'), original.replace('City_01_01.txt', 'City_02_01.txt'),
                     original.replace('S: 1 / 2', 'S: bad'), '', 'invalid container request\n' + original):
            with self.subTest(text=text), self.assertRaises(ERROR):
                zoning.parse_map_status(text, 101, allow_missing=True)

    def test_missing_is_not_readiness_or_permission_to_spawn(self):
        sample = zoning.parse_map_status('invalid container request\n', 101, allow_missing=True)
        self.assertEqual(sample, {'map_id': 101, 'ready': False, 'missing': True})
        self.assertFalse(zoning.ready(sample, 101))
        with self.assertRaises(ERROR):
            zoning.parse_map_status('invalid container request\n', 101)
        sample = zoning.parse_map_status('101 maps/City_01_01.txt NotReady 1 (Not started) Info\n', 101)
        self.assertTrue(sample['not_started'])
        self.assertFalse(zoning.ready(sample, 101))

    def test_ready_demands_recent_typed_protocol_ages(self):
        sample = zoning.parse_map_status(map_status(), 101)
        for field in ('network_age_seconds', 'stats_age_seconds'):
            for value in (-1, 21, True, 1.0, '1', None):
                with self.subTest(field=field, value=value):
                    self.assertFalse(zoning.ready(dict(sample, **{field: value}), 101))
        for changes in ({'loaded': 1}, {'connected': 1}, {'in_map_transfer': 0},
                        {'in_map_transfer': True}, {'address': 'localhost'}, {'static_map_id': 1}):
            self.assertFalse(zoning.connected(status(**changes), 101))

    def test_bool_is_not_a_native_map_identity(self):
        self.assertFalse(zoning.connected(dict(status(1), map_id=True), 1))
        self.assertFalse(zoning.connected(status(1, static_map_id=True), 1))
        sample = zoning.parse_map_status(map_status(1), 1)
        self.assertFalse(zoning.ready(dict(sample, map_id=True), 1))


class ReceiptTests(unittest.TestCase):
    def validate(self, value, action='prepare'):
        return zoning.validate_request(value, session=SESSION, client_pid=44, epoch=1,
                                       origin=1, action=action, now_ms=NOW)

    def test_exact_prepare_and_delivery_receipts(self):
        for action in ('prepare', 'mapmove'):
            value = request(action)
            self.assertEqual(self.validate(value, action), value)

    def test_foreign_stale_future_duplicate_and_malformed_receipts(self):
        changes = ({'session_id': 'b'*32}, {'client_pid': 45}, {'client_pid': True},
            {'character_id': 2}, {'character_id': True}, {'epoch': 0}, {'epoch': 2}, {'epoch': True},
            {'action': 'mapmove'}, {'from_map_id': 101}, {'to_map_id': 1}, {'to_map_id': 2},
            {'format': True}, {'requested_utc_ms': NOW-zoning.REQUEST_AGE_MS-1},
            {'requested_utc_ms': NOW+1}, {'requested_utc_ms': True}, {'extra': 'unreviewed'})
        for changed in changes:
            with self.subTest(changed=changed), self.assertRaises(ERROR):
                self.validate(request(**changed))
        for value in (None, [], {}, {k:v for k,v in request().items() if k != 'session_id'}):
            with self.subTest(value=value), self.assertRaises(ERROR):
                self.validate(value)

    def test_read_receipt_rejects_nonfiles_aliases_oversize_and_nonobject(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'request.json'
            self.assertIsNone(zoning.read_request(path))
            path.write_text(json.dumps(request()))
            self.assertEqual(zoning.read_request(path), request())
            link = root/'alias.json'
            link.symlink_to(path)
            with self.assertRaises(OSError):
                zoning.read_request(link)
            link.unlink()
            os.link(path, link)
            with self.assertRaises(ERROR):
                zoning.read_request(path)
            link.unlink()
            for raw in ('', ' '*2049, '[]'):
                path.write_text(raw)
                with self.subTest(raw=raw[:20]), self.assertRaises(ERROR):
                    zoning.read_request(path)
            path.write_text('{')
            with self.assertRaises(ValueError):
                zoning.read_request(path)


class PreparationObservationTests(unittest.TestCase):
    def test_budget_reserves_full_cold_preparation_arrival_and_ordinary_save(self):
        window = zoning.travel_window(2000, 100, NOW, 600)
        self.assertEqual(window['departure_deadline_utc_ms'], NOW + 1480000)
        self.assertEqual(window['session_deadline_utc_ms'], NOW + 1900000)
        self.assertFalse(window['session_budget_extended'])
        for deadline in (None, float('inf'), True, 1120, 1119):
            with self.subTest(deadline=deadline), self.assertRaises(ERROR):
                zoning.travel_window(deadline, 100, NOW, 600)
        self.assertEqual(zoning.travel_window(1000, 100, NOW, 90)['preparation_budget_seconds'], 90)

    def test_static_console_work_is_bounded_and_retains_every_split_crash_marker(self):
        for marker in (b'Program crash detected', b'Exception caught: EXCEPTION_ACCESS_VIOLATION'):
            for split in range(1, len(marker)):
                process = SimpleNamespace(output=bytearray(b'x' * 133000))
                owned = {'process': process}
                zoning.scan_new_console(owned)
                for _ in range(20):
                    zoning.scan_new_console(owned)
                self.assertEqual(owned['console_bytes_scanned'], 133000 + 20*64)
                process.output.extend(marker[:split])
                if b'Program crash detected' in marker[:split] or b'EXCEPTION_A' in marker[:split]:
                    with self.assertRaises(ERROR): zoning.scan_new_console(owned)
                else:
                    zoning.scan_new_console(owned)
                process.output.extend(marker[split:])
                with self.subTest(marker=marker, split=split), self.assertRaises(ERROR):
                    zoning.scan_new_console(owned)

    def test_incremental_active_console_decodes_only_on_crash_with_retained_proof(self):
        instance = zoning.LocalCharacterZoningServer.__new__(zoning.LocalCharacterZoningServer)
        process = Mock()
        process.output = bytearray('unchanged utf8 é '.encode() * 1000)
        process.text.side_effect = lambda: bytes(process.output).decode()
        instance.map_process = process
        for _ in range(20):
            self.assertIsNone(instance.map_crash_observation())
        process.text.assert_not_called()
        process.output.extend(b'Program crash detected')
        evidence = instance.map_crash_observation()
        process.text.assert_called_once()
        self.assertEqual(evidence['marker'], 'Program crash detected')
        self.assertEqual(evidence['console_sha256'], zoning.hashlib.sha256(bytes(process.output)).hexdigest())

    def test_console_truncation_is_never_treated_as_clean_history(self):
        process = SimpleNamespace(output=bytearray(b'known console'))
        owned = {'process': process}
        zoning.scan_new_console(owned)
        process.output.clear()
        with self.assertRaises(ERROR): zoning.scan_new_console(owned)


class NativeEvidenceTests(unittest.TestCase):
    def test_ready_binds_exact_instance_character_account_route_and_time(self):
        good = resume()
        record = zoning.stock_ready(logs(good), 101, NOW, NOW)
        self.assertEqual(record['map_id'], 101)
        self.assertEqual(record['map_instance'], 'City_01_01_2')
        self.assertFalse(record['native_log_contains_session_or_client_pid'])
        for bad in (good.replace('THORHERO', 'OTHER'), good.replace('COHLOCAL', 'OTHER'),
                    good.replace('City_01_01_2', 'City_01_01_1'), good.replace('127.0.0.1:127.0.0.1', '127.0.0.2:127.0.0.1'),
                    good.replace(':41001', ':65536'), good.rstrip('\n')):
            with self.subTest(bad=bad):
                self.assertIsNone(zoning.stock_ready(logs(bad), 101, NOW, NOW))
        for path in ('logs/mapserver/entity.log', 'logs/foreign/entity_2026-10-10.log', 'logs/dbserver/notentity.log'):
            self.assertIsNone(zoning.stock_ready(logs(good, path), 101, NOW, NOW))
        self.assertIsNone(zoning.stock_ready(logs(good), 101, NOW+1, NOW+1000))
        self.assertIsNone(zoning.stock_ready(logs(good), 101, NOW-10000, NOW-1000))

    def test_round_trip_does_not_reuse_initial_atlas_ready(self):
        old = resume(1, '261010 18:30:00')
        second = resume(101, '261010 18:30:05')
        self.assertIsNone(zoning.stock_ready(logs(old+second), 1, NOW, NOW))
        fresh = resume(1)
        self.assertEqual(zoning.stock_ready(logs(old+second+fresh), 1, NOW, NOW)['utc_ms'], NOW)

    def test_periodic_positions_require_exact_route_complete_lines_and_agreement(self):
        row = native('PeriodicInfo pos=<12.5,-768,90> ExpLevel:1')
        positions = zoning.stock_positions(logs(row+row), 101, NOW, NOW)
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['position'], [12.5, -768, 90])
        self.assertEqual(zoning.stock_positions(logs(row.rstrip('\n')), 101, NOW, NOW), [])
        self.assertEqual(zoning.stock_positions(logs(row), 1, NOW, NOW), [])
        with self.assertRaisesRegex(ERROR, 'Conflicting'):
            zoning.stock_positions(logs(row+row.replace('12.5', '13.5')), 101, NOW, NOW)
        for bad in ('1e999', '1000001'):
            with self.subTest(bad=bad), self.assertRaises(ERROR):
                zoning.stock_positions(logs(row.replace('12.5', bad)), 101, NOW, NOW)

    def test_stock_logout_terminal_uses_actual_upstream_space_separated_syntax(self):
        fixture = (Path(__file__).with_name('fixtures')/'thor-contact-save-0.12.1-20261003.log').read_text()
        raw = fixture.replace('City_01_01_1', 'City_01_01_2').replace('map 1 (', 'map 101 (')
        timer = int(time.mktime(time.strptime('261003 11:06:37', '%y%m%d %H:%M:%S'))*1000)
        result = zoning.terminal_position(logs(raw), 101, {'sent_utc_ms': timer-6000}, timer-100000, timer+5000)
        self.assertIsNotNone(result)
        self.assertEqual(result['position'], [112.468750, -768, -660.765625])
        self.assertEqual(result['logout_timer_evidence']['utc_ms'], timer)
        self.assertEqual(zoning.stock_logout(logs(raw), 101, timer-1000, timer+5000)['utc_ms'], timer)
        for changed in (raw.replace('map 101 (', 'map 1 ('), raw.rstrip('\n'),
                        raw.replace('Logout timer expired', 'NetLink was closed'),
                        raw.replace('THORHERO', 'OTHER'), raw.replace('City_01_01_2', 'City_01_01_1')):
            self.assertIsNone(zoning.terminal_position(logs(changed), 101,
                {'sent_utc_ms': timer-6000}, timer-100000, timer+5000))

    def test_stock_travel_maps_skip_the_two_stage_transfer_so_the_loading_screen_comes_at_once(self):
        instance = zoning.LocalCharacterZoningServer.__new__(zoning.LocalCharacterZoningServer)
        instance.stock = {'requested': True}
        instance.manual_atlas_startup = {'external_maps': {'build_input_sha256': 'b' * 64}}
        self.assertEqual(instance.session_map_options(), ['-notwostagemapxfer'])
        instance.manual_atlas_startup = {}
        self.assertEqual(instance.session_map_options(), [])
        instance.manual_atlas_startup = {'external_maps': {}}
        instance.stock = {'requested': False}
        self.assertEqual(instance.session_map_options(), [])
        base = zoning.character.LocalCharacterServer.__new__(zoning.character.LocalCharacterServer)
        self.assertEqual(base.session_map_options(), [])
        source = (Path(__file__).parents[3] / 'upstream/ouroboros/MapServer/src/svr/svr_init.c').read_text()
        self.assertIn('strcmp(argv[i], "-notwostagemapxfer")==0', source)
        guest = Path(zoning.__file__).read_text() + Path(zoning.character.__file__).read_text()
        self.assertEqual(guest.count('*self.session_map_options()'), 2)   # Atlas and every zoning spawn

    def test_legacy_atlas_ready_is_the_newest_after_the_launch_on_either_route(self):
        # Retained legacy MapServer (CI donor): no events contract, second-resolution log times.
        line = '%s %s "THORHERO:COHLOCAL" 7 Connection:ResumeCharacter from 127.0.0.1:%d AuthName "COHLOCAL"\n'
        early = time.strftime('%y%m%d %H:%M:%S', time.localtime((NOW - 60000) / 1000))
        raw = (line % (early, 'City_01_01_1:127.0.0.1:127.0.0.1', 5001)
               + line % (STAMP, 'City_01_01_1:127.0.0.1:127.0.0.1', 5002))
        record = zoning.legacy_ready(logs(raw), NOW - 999, NOW + 5000)
        self.assertEqual((record['port'], record['utc_ms'], record['log_route']),
                         (5002, NOW, 'embedded_dbserver_logserver'))
        self.assertEqual(zoning.legacy_ready(logs(raw), NOW - 120000, NOW + 5000)['port'], 5002)
        self.assertIsNone(zoning.legacy_ready(logs(raw), NOW + 1000, NOW + 5000))
        self.assertIsNone(zoning.legacy_ready(logs(raw.replace('City_01_01_1', 'City_01_01_2')), 0, NOW + 5000))
        local = line % (STAMP, '0', 5003)
        self.assertEqual(zoning.legacy_ready(logs(local, 'logs/mapserver/entity.log'), 0, NOW + 5000)['port'], 5003)
        instance = zoning.LocalCharacterZoningServer.__new__(zoning.LocalCharacterZoningServer)
        instance.active_map_id, instance.ready_floor_ms = 1, NOW - 999
        with patch.object(zoning.LocalCharacterZoningServer, 'current_logs', return_value=logs(raw)), \
                patch.object(zoning.LocalCharacterZoningServer, 'monorail_enabled', return_value=False):
            self.assertEqual(instance.native_ready_record()['port'], 5002)

    def test_native_immediate_ready_on_return_must_be_newer_than_delivery(self):
        instance = zoning.LocalCharacterZoningServer.__new__(zoning.LocalCharacterZoningServer)
        instance.active_map_id = 1
        instance.ready_floor_ms = NOW
        instance.map_package = {'inputs': {'mapserver_progress': {'events_contract': {'format': 1}}}}
        parent = zoning.character.LocalCharacterReopenServer
        with patch.object(parent, 'native_ready_record', return_value={'utc_ms': NOW-1}):
            self.assertIsNone(instance.native_ready_record())
        with patch.object(parent, 'native_ready_record', return_value={'utc_ms': NOW}):
            self.assertEqual(instance.native_ready_record(), {'utc_ms': NOW})


class ZoningServerTests(unittest.TestCase):
    def instance(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        instance = zoning.LocalCharacterZoningServer.__new__(zoning.LocalCharacterZoningServer)
        instance.owner = SimpleNamespace(args=SimpleNamespace(state=Path(temporary.name), session_id=SESSION))
        instance.owner.session_budget = SimpleNamespace(deadline=time.monotonic() + 2000)
        instance.ctx = SimpleNamespace(event=Mock(), report={'client_launch': {'pid': 44}})
        instance.owner.client = SimpleNamespace(process=Mock())
        instance.owner.client.process.poll.return_value = None
        instance.active_map_id = 1
        instance.creation_report = {'client_pid': 44, 'connected_on_atlas': True, 'recovery_requested': False}
        instance.zoning_report = {'events': [], 'transfers': [], 'preparation_stage_observations': []}
        instance.pending = None
        instance.epoch = 0
        instance.maps = {1: {'ready': True}}
        instance.request_history = {}
        instance.delivery_history = {}
        instance.zoning_next = 0
        instance.zoning_query = None
        instance.enabled_announced = False
        instance._spawn_map = Mock()
        instance._map_progress = Mock(return_value={'windows_pid': 55, 'tick_completed': 5})
        instance.live_progress = Mock(return_value=True)
        instance._query_start = Mock()
        instance._query_poll = Mock(return_value=None)
        instance.current_logs = Mock(return_value=[])
        return instance

    def test_saved_instance_101_with_unassigned_map_resumes_without_sql_writes(self):
        instance = self.instance()
        row = dict(containerid=1, mapid=None, staticmapid=101, posx=12.5, posy=-768, posz=90)
        instance.sql_rows = Mock(return_value=[row])
        instance.sql = Mock(side_effect=AssertionError('SQL mutation forbidden'))
        self.assertEqual(instance.character_position(allow_unassigned_active_map=True), row)
        self.assertEqual(instance.active_map_id, 101)
        self.assertEqual(instance.creation_report['map_id'], 101)
        self.assertEqual(instance.zoning_report['saved_destination_map_id'], 101)
        instance.sql.assert_not_called()
        with self.assertRaises(ERROR):
            instance.character_position()
        row['mapid'] = 101
        self.assertEqual(instance.character_position(), row)

    def test_unknown_saved_map_and_invalid_position_cannot_mutate_sql_or_activate(self):
        for changes in ({'staticmapid': 2, 'mapid': 2}, {'staticmapid': True, 'mapid': True},
                        {'mapid': 1}, {'posx': float('nan')}, {'posz': float('inf')}, {'posy': True}):
            instance = self.instance()
            row = dict(containerid=1, mapid=101, staticmapid=101, posx=12.5, posy=-768, posz=90)
            row.update(changes)
            instance.sql_rows = Mock(return_value=[row])
            instance.sql = Mock(side_effect=AssertionError('SQL mutation forbidden'))
            with self.subTest(changes=changes), self.assertRaises(ERROR):
                instance.character_position(allow_unassigned_active_map=True)
            self.assertEqual(instance.active_map_id, 1)
            instance.sql.assert_not_called()

    def test_saved_instance_startup_preserves_android_stage_with_exact_map101_proof(self):
        instance = self.instance()
        instance.active_map_id = 101
        instance.maps = {}
        instance.report = {}
        instance.ctx.stage, instance.ctx.passed, instance.ctx.check = Mock(), Mock(), Mock()
        instance.ctx.deadline = 1000
        instance.query = Mock(side_effect=[
            '101 City_01_01.txt NotReady 1 (Not started) Info\n', map_status(101)])
        instance._spawn_map.side_effect = lambda map_id: instance.maps.update({map_id: {'ready': False}})
        def activate(map_id):
            instance.map_launch_utc_ms = NOW
            instance.active_map_id = map_id
        instance._activate = Mock(side_effect=activate)
        instance.sample_startup_observation = Mock()
        with patch.object(zoning.time, 'monotonic', return_value=100), \
                patch.object(zoning.character.progress, 'compare_records') as compare:
            instance.start_map()
        compare.assert_called_once()
        instance.ctx.stage.assert_called_once_with('local_atlas_startup')
        instance._spawn_map.assert_called_once_with(101)
        instance._activate.assert_called_once_with(101)
        self.assertTrue(instance.creation_report['map_ready'])
        self.assertTrue(instance.ctx.report['mapserver_started'])
        self.assertEqual(instance.creation_report['map_startup_guard']['protocol']['map_id'], 101)
        ready_event = instance.ctx.passed.call_args.kwargs
        self.assertTrue(ready_event['atlas_ready'])
        self.assertTrue(ready_event['loopback_only'])
        self.assertEqual(ready_event['map']['map_id'], 101)
        self.assertEqual(ready_event['map']['port'], 7002)

    def test_prepare_only_queries_baseline_and_refuses_duplicate_overlap(self):
        instance = self.instance()
        instance._accept_prepare(request(), NOW)
        instance._query_start.assert_called_once_with(['-getstatus', '1', '101'], 'baseline')
        instance._spawn_map.assert_not_called()
        with self.assertRaises(ERROR):
            instance._accept_prepare(request(), NOW)
        with self.assertRaises(ERROR):
            instance._accept_prepare(request(epoch=2), NOW)
        self.assertEqual(instance.epoch, 1)
        instance._spawn_map.assert_not_called()

    def test_cold_admission_preserves_save_budget_and_does_not_start_work_when_late(self):
        instance = self.instance()
        instance.owner.session_budget.deadline = 1120
        with patch.object(zoning.time, 'monotonic', return_value=100), self.assertRaises(ERROR):
            instance._accept_prepare(request(), NOW)
        instance._spawn_map.assert_not_called()
        instance._query_start.assert_not_called()
        self.assertEqual(instance.epoch, 0)
        self.assertEqual(instance.request_history, {})

    def test_resident_return_has_truthful_shorter_preparation_allowance(self):
        instance = self.instance()
        instance.maps[101] = {'ready': True}
        instance.owner.session_budget.deadline = 700
        with patch.object(zoning.time, 'monotonic', return_value=100):
            instance._accept_prepare(request(), NOW)
        self.assertEqual(instance.pending['preparation_kind'], 'resident_warm')
        self.assertEqual(instance.pending['preparation_budget_seconds'], 90)
        self.assertEqual(instance.pending['phase'], 'map_ready')
        self.assertEqual(instance.owner.session_budget.deadline, 700)
        instance._spawn_map.assert_not_called()

    def test_prepared_delivery_after_departure_cutoff_never_enters_arrival(self):
        instance = self.instance()
        instance._accept_prepare(request(), NOW)
        instance.pending.update(phase='ready', ready_utc_ms=NOW, departure_deadline_utc_ms=NOW+100)
        with self.assertRaises(ERROR):
            instance._accept_delivery(request('mapmove', sent_utc_ms=NOW+100), NOW+100)
        self.assertFalse(instance.pending['transfer_requested'])
        self.assertEqual(instance.delivery_history, {})

    def test_preparation_cancellation_restores_scheduler_then_preserves_ordinary_save(self):
        instance = self.instance()
        instance._accept_prepare(request(), NOW)
        pacing = Mock()
        instance.maps[101] = {'ready': False, 'scheduler': pacing}
        (instance.owner.args.state/'character-logout.json').write_text('{}')
        with patch.object(zoning.time, 'time', return_value=NOW/1000):
            instance.tick_zoning()
        pacing.restore.assert_called_once()
        self.assertIsNone(instance.pending)
        self.assertEqual(instance.zoning_report['events'][-1]['status'], 'failed')
        self.assertTrue(instance.zoning_report['events'][-1]['current_map_verified'])
        self.assertFalse(instance.zoning_report['events'][-1]['transfer_requested'])

    def test_ready_requires_scheduler_restore_and_retains_request_to_ready_timing(self):
        instance = self.instance()
        instance._accept_prepare(request(), NOW)
        pacing = Mock()
        instance.maps[101] = {'ready': False, 'scheduler': pacing}
        instance.pending['phase'] = 'map_ready'
        instance._query_poll.return_value = ('prepared_map', map_status())
        with patch.object(zoning.time, 'time', return_value=(NOW+15000)/1000):
            instance.tick_zoning()
        pacing.restore.assert_called_once()
        ready = instance.zoning_report['events'][-1]
        self.assertEqual(ready['status'], 'ready')
        self.assertEqual(ready['requested_utc_ms'], NOW)
        self.assertEqual(ready['preparation_elapsed_ms'], 15000)
        self.assertEqual(ready['preparation_kind'], 'cold')
        self.assertEqual(ready['preparation_ready_utc_ms'], NOW+15000)

    def test_unverifiable_restore_cannot_publish_ready_or_claim_recoverable_prepare_failure(self):
        instance = self.instance()
        instance._accept_prepare(request(), NOW)
        pacing = Mock()
        pacing.restore.side_effect = ERROR('restore unavailable')
        instance.maps[101] = {'ready': False, 'scheduler': pacing}
        instance.pending['phase'] = 'map_ready'
        instance._query_poll.return_value = ('prepared_map', map_status())
        with patch.object(zoning.time, 'time', return_value=NOW/1000), self.assertRaises(ERROR):
            instance.tick_zoning()
        self.assertNotIn('ready', [row['status'] for row in instance.zoning_report['events']])
        self.assertNotIn('preparation_failed', instance.zoning_report)

    def test_premature_stale_and_duplicate_delivery_cannot_begin_transfer(self):
        instance = self.instance()
        instance._accept_prepare(request(), NOW)
        with self.assertRaises(ERROR):
            instance._accept_delivery(request('mapmove'), NOW)
        instance.pending.update(phase='ready', ready_utc_ms=NOW)
        with self.assertRaises(ERROR):
            instance._accept_delivery(request('mapmove', sent_utc_ms=NOW-1), NOW)
        self.assertFalse(instance.pending['transfer_requested'])
        instance._accept_delivery(request('mapmove'), NOW)
        self.assertEqual(instance.pending['phase'], 'arrival')
        with self.assertRaises(ERROR):
            instance._accept_delivery(request('mapmove'), NOW)
        self.assertEqual(len(instance.delivery_history), 1)
        instance._spawn_map.assert_not_called()

    def test_async_duplicate_files_spawn_once_and_accept_delivery_once(self):
        instance = self.instance()
        state = instance.owner.args.state
        (state/'character-zoning-request.json').write_text(json.dumps(request()))
        replies = [('baseline', '101 maps/City_01_01.txt NotReady 1 (Not started) Info\n'),
                   ('prepared_map', map_status()), None, None]
        instance._query_poll.side_effect = replies
        instance._spawn_map.side_effect = lambda map_id: instance.maps.update({map_id: {'ready': False}})
        with patch.object(zoning.time, 'monotonic', return_value=100) as clock, \
             patch.object(zoning.time, 'time', return_value=NOW/1000):
            instance.tick_zoning()
            self.assertEqual(instance.pending['phase'], 'map_ready')
            clock.return_value += 2
            instance.tick_zoning()
            self.assertEqual(instance.pending['phase'], 'ready')
            (state/'character-zoning-delivery.json').write_text(json.dumps(request('mapmove')))
            clock.return_value += 2
            instance.tick_zoning()
            clock.return_value += 2
            instance.tick_zoning()
        instance._spawn_map.assert_called_once_with(101)
        self.assertEqual(len(instance.request_history), 1)
        self.assertEqual(len(instance.delivery_history), 1)
        self.assertEqual(instance.pending['phase'], 'arrival')
        self.assertEqual([e['status'] for e in instance.zoning_report['events']].count('transferring'), 1)

    def test_missing_or_already_live_foreign_destination_never_spawns(self):
        for text in ('invalid container request\n', map_status()):
            instance = self.instance()
            (instance.owner.args.state/'character-zoning-request.json').write_text(json.dumps(request()))
            instance._query_poll.return_value = ('baseline', text)
            with patch.object(zoning.time, 'time', return_value=NOW/1000):
                instance.tick_zoning()
            instance._spawn_map.assert_not_called()
            self.assertEqual(instance.zoning_report['status'], 'failed')
            self.assertTrue(instance.zoning_report['preparation_failed'])
            self.assertEqual(instance.active_map_id, 1)

    def test_round_trip_arrival_refuses_stale_native_ready_then_accepts_fresh(self):
        instance = self.instance()
        instance.active_map_id = 101
        instance.epoch = 2
        instance.pending = dict(to_map_id=1, phase='arrival', delivery=request('mapmove', epoch=2,
            from_map_id=101, to_map_id=1), arrival_character=status(1), next_query=0)
        instance.current_logs = Mock(return_value=logs(resume(1, '261010 18:30:00')+resume(101, '261010 18:30:05')))
        instance._activate = Mock()
        instance._observe_arrival(('arrival_map', map_status(1)), NOW)
        instance._activate.assert_not_called()
        self.assertEqual(instance.zoning_report['transfers'], [])
        instance.current_logs.return_value = logs(resume(1))
        instance._observe_arrival(('arrival_map', map_status(1)), NOW+500)
        instance._activate.assert_not_called()
        instance._query_start.assert_called_with(['-getstatus', '3', '1'], 'arrival_final_character')
        instance._observe_arrival(('arrival_final_character',
            '1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 1 SmapId 1\n'), NOW+500)
        instance._activate.assert_called_once_with(1)
        self.assertEqual(instance.ready_floor_ms, NOW)
        self.assertEqual(instance.zoning_report['transfers'][0]['from_map_id'], 101)
        self.assertEqual(instance.zoning_report['transfers'][0]['to_map_id'], 1)
        self.assertEqual(instance.zoning_report['transfers'][0]['elapsed_ms'], 500)
        self.assertIsNone(instance.pending)


    def pending_arrival(self, target=101, sent_ms=NOW+500):
        instance = self.instance()
        origin = 1 if target == 101 else 101
        instance.active_map_id = origin
        instance.epoch = 1
        instance.pending = dict(to_map_id=target, phase='arrival', delivery=request('mapmove',
            from_map_id=origin, to_map_id=target, sent_utc_ms=sent_ms), next_query=0,
            transfer_requested=True)
        instance._activate = Mock(side_effect=lambda map_id: setattr(instance, 'active_map_id', map_id))
        return instance

    def test_full_arrival101_accepts_new_same_second_ready_after_final_identity_query(self):
        instance = self.pending_arrival()
        instance.current_logs.return_value = logs(resume(1, '261010 18:29:59')+resume(101))
        text = '1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 101 SmapId 101\n'
        instance._observe_arrival(('arrival_character', text), NOW+600)
        instance._query_start.assert_called_with(['-getstatus', '1', '101'], 'arrival_map')
        instance._observe_arrival(('arrival_map', map_status(101)), NOW+650)
        instance._activate.assert_not_called()
        instance._query_start.assert_called_with(['-getstatus', '3', '1'], 'arrival_final_character')
        instance._observe_arrival(('arrival_final_character', text), NOW+700)
        instance._activate.assert_called_once_with(101)
        self.assertEqual(instance.zoning_report['transfers'][0]['elapsed_ms'], 200)
        self.assertEqual(instance.zoning_report['transfers'][0]['native_ready']['utc_ms'], NOW)
        self.assertEqual(instance.zoning_report['transfers'][0]['same_client_pid'], 44)
        self.assertEqual(instance.zoning_report['events'][-1]['current_map_id'], 101)
        self.assertEqual(instance.creation_report['map_id'], 101)
        self.assertIsNone(instance.pending)

    def test_same_second_ready_present_before_prepare_is_excluded_by_hash(self):
        instance = self.pending_arrival()
        raw = resume(101)
        instance.current_logs.return_value = logs(raw)
        old = zoning.stock_ready(logs(raw), 101, 0, NOW+500)
        instance.pending['prior_ready_hashes'] = [old['line_sha256']]
        instance._observe_arrival(('arrival_map', map_status(101)), NOW+700)
        instance._query_start.assert_not_called()
        instance._activate.assert_not_called()
        # A separately witnessed resume in that same coarse log second is new.
        instance.current_logs.return_value = logs(raw+raw.replace(':41001', ':41002'))
        instance._observe_arrival(('arrival_map', map_status(101)), NOW+800)
        instance._query_start.assert_called_once_with(['-getstatus', '3', '1'], 'arrival_final_character')
        self.assertNotEqual(instance.pending['arrival_native']['line_sha256'], old['line_sha256'])
        self.assertEqual(instance.zoning_report['transfers'], [])

    def test_final_arrival_query_requires_same_live_client_and_target_identity(self):
        text = '1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 101 SmapId 101\n'
        for altered in ('client_pid', 'client_exit', 'foreign_character', 'wrong_map', 'transferring'):
            instance = self.pending_arrival()
            instance.current_logs.return_value = logs(resume(101))
            instance._observe_arrival(('arrival_character', text), NOW+600)
            instance._observe_arrival(('arrival_map', map_status(101)), NOW+650)
            final = text
            if altered == 'client_pid': instance.ctx.report['client_launch']['pid'] = 45
            if altered == 'client_exit': instance.owner.client.process.poll.return_value = 0
            if altered == 'foreign_character': final = text.replace('THORHERO', 'OTHER')
            if altered == 'wrong_map': final = text.replace('101', '1')
            if altered == 'transferring': final = text.rstrip()+' InMapXfer\n'
            with self.subTest(altered=altered):
                if altered in ('client_pid', 'client_exit', 'foreign_character'):
                    with self.assertRaises(ERROR):
                        instance._observe_arrival(('arrival_final_character', final), NOW+700)
                else:
                    instance._observe_arrival(('arrival_final_character', final), NOW+700)
            instance._activate.assert_not_called()
            self.assertEqual(instance.zoning_report['transfers'], [])
            self.assertIsNotNone(instance.pending)

    def test_invalid_sent_receipt_is_uncertain_even_before_delivery_acceptance(self):
        for raw in (json.dumps(request('mapmove', client_pid=999)), '{', '[]'):
            instance = self.instance()
            (instance.owner.args.state/'character-zoning-delivery.json').write_text(raw)
            with self.subTest(raw=raw), patch.object(zoning.time, 'time', return_value=NOW/1000):
                with self.assertRaises((ERROR, ValueError)):
                    instance.tick_zoning()
            self.assertTrue(instance.zoning_report['failure']['transfer_requested'])
            self.assertFalse(instance.zoning_report['events'][-1]['current_map_verified'])
            self.assertNotIn('preparation_failed', instance.zoning_report)
            instance._spawn_map.assert_not_called()

    def test_changed_historical_delivery_is_uncertain_after_completed_transfer(self):
        instance = self.instance()
        instance.epoch = 1
        instance.delivery_history[1] = request('mapmove')
        (instance.owner.args.state/'character-zoning-delivery.json').write_text(
            json.dumps(request('mapmove', client_pid=999)))
        with patch.object(zoning.time, 'time', return_value=NOW/1000), self.assertRaises(ERROR):
            instance.tick_zoning()
        self.assertTrue(instance.zoning_report['failure']['transfer_requested'])
        self.assertFalse(instance.zoning_report['events'][-1]['current_map_verified'])
        instance._spawn_map.assert_not_called()

    def test_new_delivery_cannot_be_hidden_by_malformed_prepare(self):
        instance = self.instance()
        state = instance.owner.args.state
        (state/'character-zoning-request.json').write_text('{')
        (state/'character-zoning-delivery.json').write_text(json.dumps(request('mapmove')))
        with patch.object(zoning.time, 'time', return_value=NOW/1000), self.assertRaises(ValueError):
            instance.tick_zoning()
        self.assertTrue(instance.zoning_report['failure']['transfer_requested'])
        self.assertFalse(instance.zoning_report['events'][-1]['current_map_verified'])
        instance._spawn_map.assert_not_called()

    def test_recovery_or_completed_logout_cannot_start_zoning(self):
        for kind in ('recovery_flag', 'relocation_receipt', 'logout_receipt', 'saved'):
            instance = self.instance()
            if kind == 'recovery_flag': instance.creation_report['recovery_requested'] = True
            if kind == 'relocation_receipt': (instance.owner.args.state/'character-relocation.json').write_text('{}')
            if kind == 'logout_receipt': (instance.owner.args.state/'character-logout.json').write_text('{}')
            if kind == 'saved': instance.creation_report['verified'] = True
            with self.subTest(kind=kind), self.assertRaises(ERROR):
                instance._accept_prepare(request(), NOW)
            instance._spawn_map.assert_not_called()
            instance._query_start.assert_not_called()
            self.assertIsNone(instance.pending)


class IdleResidentMapTests(unittest.TestCase):
    """Optional: a resident map the player left is weighted down, restored before return."""
    def instance(self, requested=True):
        instance = ZoningServerTests.instance(self)
        instance.ctx.secrets = []
        instance.idle_capability = None
        instance.zoning_report['idle_resident_maps'] = {'requested': requested, 'periods': []}
        instance.maps = {1: {'ready': True, 'idle_token': 'b' * 64}, 5: {'ready': True, 'idle_token': 'c' * 64}}
        instance.active_map_id = 5
        self.made = []
        test = self
        class Fake:
            def __init__(self, owner, map_id, **options):
                self.options, self.map_id = options, map_id
                self.capability = {'supported': True}
                self.report = {'changed_threads': 0, 'restored_threads': 0}
                self.samples = self.restores = 0
                test.made.append(self)
            def sample(self):
                self.samples += 1; self.report['changed_threads'] = 3
            def restore(self):
                self.restores += 1; self.report['restored_threads'] = 3
        self.patch = patch.object(zoning.scheduler, 'PreparationScheduler', Fake)
        self.patch.start(); self.addCleanup(self.patch.stop)
        return instance

    def test_disabled_by_default_never_weights(self):
        instance = self.instance(requested=False)
        instance.idle_lower(1, 'player_left')
        self.assertEqual(self.made, [])
        self.assertIsNone(instance.idle_token())      # the default launch environment is unchanged
        self.assertEqual(instance.ctx.secrets, [])

    def test_requested_launch_token_is_unique_and_redacted(self):
        instance = self.instance()
        first, second = instance.idle_token(), instance.idle_token()
        self.assertTrue(len(first) == len(second) == 64 and first != second)
        self.assertEqual(instance.ctx.secrets, [first, second])

    def test_left_map_is_weighted_with_its_spawn_token_then_restored_on_travel_back(self):
        instance = self.instance()
        instance.idle_lower(1, 'player_left')
        instance.idle_lower(5, 'player_left')            # the active map is never weighted
        instance.idle_lower(1, 'player_left')            # already idle: no second scheduler
        self.assertEqual(len(self.made), 1)
        idle = self.made[0]
        self.assertEqual((idle.map_id, idle.options['token'], idle.options['environment_name'], idle.options['increment']),
                         (1, 'b' * 64, 'COH_ZONING_IDLE_OWNER', 10))
        instance.tick_idle()
        self.assertEqual(idle.samples, 2)
        instance.active_map_id = 5
        instance._accept_prepare(request(to_map_id=1, from_map_id=5, epoch=1), NOW)
        self.assertEqual(idle.restores, 1)
        self.assertIsNone(instance.maps[1]['idle'])
        period = instance.zoning_report['idle_resident_maps']['periods'][0]
        self.assertEqual((period['status'], period['restore_reason'], period['restored_threads']),
                         ('restored', 'travel_requested', 3))

    def test_restore_failure_is_reported_and_cleanup_restores_every_idle_map(self):
        instance = self.instance()
        instance.idle_lower(1, 'player_left')
        self.made[0].restore = Mock(side_effect=zoning.base.DiagnosticError('readback differs'))
        self.assertFalse(instance.restore_idle_maps('cleanup'))
        period = instance.zoning_report['idle_resident_maps']['periods'][0]
        self.assertEqual((period['status'], period['failure_type']), ('restore_failed', 'DiagnosticError'))
        self.assertTrue(instance.restore_idle_maps('cleanup'))   # nothing left to restore

    def test_observation_error_restores_and_a_map_that_became_active_is_restored(self):
        instance = self.instance()
        instance.idle_lower(1, 'player_left')
        instance.active_map_id = 1
        instance.tick_idle()
        self.assertEqual(self.made[0].restores, 1)
        instance.active_map_id = 5
        instance.idle_lower(1, 'player_left')
        self.made[1].sample = Mock(side_effect=OSError('gone'))
        instance.tick_idle()
        self.assertEqual(self.made[1].restores, 1)
        self.assertEqual(instance.zoning_report['idle_resident_maps']['periods'][1]['restore_reason'], 'observation_error')


class BackgroundPrestartTests(unittest.TestCase):
    """Optional King's Row start beside Atlas: low-priority Python preparation, then native load."""
    def setUp(self):
        self.real_available = zoning.available_memory_mib
        patcher = patch.object(zoning, 'available_memory_mib', return_value=8192)
        self.memory = patcher.start(); self.addCleanup(patcher.stop)

    def instance(self, requested=True):
        instance = ZoningServerTests.instance(self)
        events = []
        instance.ctx.check = Mock()
        instance.ctx.event = lambda kind, **fields: events.append((kind, threading.current_thread().name))
        instance.ctx.cancelled = Mock(return_value=False)
        instance.events = events
        instance.monorail_qualified = True
        instance.prestart = None
        instance.zoning_report['background_prestart'] = {'requested': requested, 'status': 'not_started'}
        progress = Path(instance.owner.args.state) / 'character-zoning-5-progress.bin'
        def spawn(map_id):
            progress.write_bytes(b'x')
            process = SimpleNamespace(process=Mock())
            process.process.poll.return_value = None
            instance.maps[map_id] = {'process': process, 'progress_path': progress, 'ready': False}
        instance._spawn_map = Mock(side_effect=spawn)
        instance.prepared = []
        def prepare():
            instance.ctx.event('stage', status='running')
            instance.ctx.event('character_zoning_preparation')
            instance.prepared.append(threading.current_thread().name)
            instance.kings_row_prepared = {'runtime': Path('/kings')}
            return instance.kings_row_prepared
        instance.prepare_kings_row_runtime = prepare
        return instance

    def run_until(self, instance, status, start=None):
        # Fake clocks stay behind the real monotonic clock, which also stamps
        # timing points: a CI runner booted under 2 minutes ago saw "reversed".
        now = time.monotonic() - 100000 if start is None else start
        for _ in range(200):
            instance.tick_prestart(now)
            if instance.prestart is not None and instance.prestart['thread'] is not None:
                instance.prestart['thread'].join(5)
            if instance.zoning_report['background_prestart']['status'] == status:
                return now
            now += 6
        self.fail('pre-start never reached ' + status + ': ' + str(instance.zoning_report['background_prestart']))

    def test_disabled_by_default_and_waits_for_the_settle_delay(self):
        instance = self.instance(requested=False)
        instance.tick_prestart(1000)
        self.assertIsNone(instance.prestart)
        instance = self.instance()
        instance.tick_prestart(100)
        instance.tick_prestart(100 + zoning.PRESTART_DELAY_SECONDS - 1)
        self.assertIsNone(instance.prestart)
        instance.tick_prestart(100 + zoning.PRESTART_DELAY_SECONDS)
        self.assertIsNotNone(instance.prestart)

    def test_low_or_unknown_available_memory_skips_without_preparing(self):
        for value in (1024, None):
            with self.subTest(value=value):
                self.memory.return_value = value
                instance = self.instance()
                instance.tick_prestart(100); instance.tick_prestart(1000); instance.tick_prestart(2000)
                self.assertIsNone(instance.prestart)
                report = instance.zoning_report['background_prestart']
                self.assertEqual((report['status'], report['available_memory_mib_at_start']), ('skipped_low_memory', value))
        with tempfile.TemporaryDirectory() as temporary:
            meminfo = Path(temporary) / 'meminfo'
            meminfo.write_text('MemTotal:       16000000 kB\nMemAvailable:    4194304 kB\n')
            self.assertEqual(self.real_available(meminfo), 4096)
            meminfo.write_text('MemTotal:       16000000 kB\n')
            self.assertIsNone(self.real_available(meminfo))
            self.assertIsNone(self.real_available(Path(temporary) / 'missing'))

    def test_never_starts_beside_a_pending_trip_or_away_from_atlas(self):
        for change in ({'pending': {'to_map_id': 5}}, {'active_map_id': 5}, {'monorail_qualified': False},
                       {'kings_row_prepared': {'runtime': Path('/kings')}}):
            with self.subTest(change=change):
                instance = self.instance()
                for name, value in change.items():
                    setattr(instance, name, value)
                instance.tick_prestart(100); instance.tick_prestart(1000)
                self.assertIsNone(instance.prestart)

    def test_prepares_off_thread_then_spawns_and_observes_first_tick(self):
        instance = self.instance()
        self.run_until(instance, 'native_ticking')
        self.assertEqual(instance.prepared, ['kings-row-prestart'])
        instance._spawn_map.assert_called_once_with(5)
        self.assertTrue(instance.maps[5]['prestarted'] and instance.maps[5]['native_ticking'])
        # Background 'stage' progress never reaches the Android stage stream.
        self.assertEqual([kind for kind, name in instance.events if name == 'kings-row-prestart'],
                         ['character_zoning_preparation'])
        row = instance.prestart_timing
        self.assertEqual((row['kind'], row['map_id']), ('background_prestart', 5))
        self.assertIn('first_completed_tick_observed', row['points'])
        self.assertEqual(instance.zoning_next, 0)

    def test_trip_during_native_loading_uses_native_budget_then_warm_once_ticking(self):
        instance = self.instance()
        instance.live_progress = Mock(return_value=False)
        self.run_until(instance, 'native_loading')
        instance.owner.session_budget.deadline = time.monotonic() + 5000
        instance._accept_prepare(request(to_map_id=5), NOW)
        self.assertEqual(instance.pending['preparation_kind'], 'prestarted_loading')
        self.assertEqual(instance.pending['preparation_budget_seconds'], zoning.KINGS_NATIVE_READY_SECONDS)
        self.assertEqual(instance.pending['python_preparation_budget_seconds'], 0)
        self.assertEqual(instance.pending['phase'], 'map_ready')
        instance._query_start.assert_not_called()
        self.assertEqual(instance._spawn_map.call_count, 1)
        warm = self.instance()
        self.run_until(warm, 'native_ticking')
        warm._accept_prepare(request(to_map_id=5), NOW)
        self.assertEqual(warm.pending['preparation_kind'], 'resident_warm')

    def test_zoning_request_while_preparing_waits_and_reuses_or_reraises(self):
        instance = self.instance()
        gate = threading.Event()
        original = instance.prepare_kings_row_runtime
        instance.prepare_kings_row_runtime = lambda: (gate.wait(5), original())[1]
        instance.tick_prestart(100); instance.tick_prestart(200)
        self.assertTrue(instance.prestart['thread'].is_alive())
        threading.Timer(.2, gate.set).start()
        instance.wait_background_prestart()
        self.assertEqual(instance.prepared, ['kings-row-prestart'])
        self.assertTrue(instance.zoning_report['background_prestart']['joined_by_zoning_request'])
        failing = self.instance()
        failing.prepare_kings_row_runtime = Mock(side_effect=ERROR('collision package differs'))
        failing.tick_prestart(100); failing.tick_prestart(200); failing.prestart['thread'].join(5)
        with self.assertRaisesRegex(ERROR, 'collision package differs'):
            failing.wait_background_prestart()

    def test_preparation_failure_is_reported_without_disabling_zoning(self):
        instance = self.instance()
        instance.prepare_kings_row_runtime = Mock(side_effect=ERROR('beacon graph differs'))
        self.run_until(instance, 'failed')
        report = instance.zoning_report['background_prestart']
        self.assertEqual((report['failure_phase'], report['failure']), ('preparing', 'beacon graph differs'))
        instance._spawn_map.assert_not_called()
        self.assertEqual(instance.zoning_next, 0)
        self.assertIsNone(instance.pending)

    def test_native_crash_while_loading_discards_the_map_for_a_later_cold_trip(self):
        instance = self.instance()
        instance.live_progress = Mock(return_value=False)
        self.run_until(instance, 'native_loading')
        owned = instance.maps[5]
        instance._map_progress = Mock(side_effect=ERROR('Owned zoning MapServer crashed'))
        self.run_until(instance, 'failed', start=1000)
        self.assertNotIn(5, instance.maps)
        owned['process'].process.terminate.assert_called_once_with()
        self.assertFalse(owned['progress_path'].exists())
        self.assertTrue(owned['progress_path'].with_name(owned['progress_path'].name + '.prestart-failed').exists())

    def test_cleanup_stops_the_thread_and_never_returns_a_tree_it_may_still_write(self):
        instance = self.instance()
        started, release = threading.Event(), threading.Event()
        def prepare():
            started.set()
            while not release.is_set():
                instance.ctx.check()      # the private stop flag applies only to this thread
                time.sleep(.01)
        instance.prepare_kings_row_runtime = prepare
        instance.tick_prestart(100); instance.tick_prestart(200)
        self.assertTrue(started.wait(5))
        instance.ctx.check()              # foreground check is unaffected
        self.assertTrue(instance.stop_background_prestart(timeout=5))
        self.assertIsInstance(instance.prestart['error'], zoning.base.Cancelled)
        stuck = self.instance()
        stuck.kings_row_data_cache = object()
        stuck.prepare_kings_row_runtime = lambda: release.wait(5)
        stuck.tick_prestart(100); stuck.tick_prestart(200)
        self.assertFalse(stuck.stop_background_prestart(timeout=.1))
        self.assertFalse(hasattr(stuck, 'kings_row_data_cache'))
        release.set(); stuck.prestart['thread'].join(5)


class StationFpsCapTests(unittest.TestCase):
    """ARM64 client cap file (patch 0121) while a trip is prepared."""
    def instance(self):
        instance = ZoningServerTests.instance(self)
        instance.owner.armport_fps_cap_file = instance.owner.args.state / 'armport-fps-cap.txt'
        instance.station_fps_cap = {'cap': zoning.STATION_FPS_CAP, 'client_supported': False,
                                    'applied': 0, 'removed': 0, 'error': None}
        return instance

    def test_cap_follows_the_preparation_phases_only(self):
        instance = self.instance(); path = instance.owner.armport_fps_cap_file
        instance._sync_station_fps_cap()
        self.assertFalse(path.exists())
        for phase, expected in (('baseline', True), ('map_ready', True), ('ready', False),
                                ('map_ready', True), ('arrival', False)):
            instance.pending = {'phase': phase}
            instance._sync_station_fps_cap()
            self.assertIs(path.exists(), expected, phase)
        self.assertEqual(path.exists(), False)
        instance.pending = {'phase': 'baseline'}; instance._sync_station_fps_cap()
        self.assertEqual(path.read_text(), str(zoning.STATION_FPS_CAP) + '\n')
        instance.pending = None; instance._sync_station_fps_cap()
        self.assertFalse(path.exists())
        record = instance.station_fps_cap
        self.assertEqual((record['applied'], record['removed'], record['client_supported']), (3, 3, True))
        instance.pending = {'phase': 'map_ready', 'transfer_requested': True}
        instance._sync_station_fps_cap()
        self.assertFalse(path.exists())

    def test_x86_client_and_write_errors_never_affect_zoning(self):
        instance = self.instance()
        del instance.owner.armport_fps_cap_file
        instance.pending = {'phase': 'baseline'}
        instance._sync_station_fps_cap()
        self.assertFalse(instance.station_fps_cap['client_supported'])
        instance = self.instance()
        instance.owner.armport_fps_cap_file = instance.owner.args.state / 'missing-directory' / 'cap.txt'
        instance.pending = {'phase': 'baseline'}
        instance._sync_station_fps_cap()
        self.assertIn('FileNotFoundError', instance.station_fps_cap['error'])
        instance._sync_station_fps_cap()   # disabled after an error
        self.assertEqual(instance.station_fps_cap['applied'], 0)

    def test_tick_zoning_writes_the_cap_before_a_blocking_preparation_and_lifts_it(self):
        instance = self.instance(); path = instance.owner.armport_fps_cap_file
        observed = []
        def accept(value, now_ms):
            instance.pending = {'phase': 'baseline', 'to_map_id': 101}
        instance._accept_prepare = accept
        instance._check_preparation_deadline = Mock(return_value=time.monotonic())
        instance._query_poll = Mock(side_effect=lambda: observed.append(path.exists()) or None)
        with patch.object(zoning, 'read_request', side_effect=lambda p: request() if p.name.endswith('request.json') else None):
            instance.tick_zoning()
        self.assertEqual(observed, [True])
        self.assertTrue(path.exists())
        instance.pending['phase'] = 'ready'; instance.zoning_next = 0
        instance.request_history = {1: request()}
        with patch.object(zoning, 'read_request', side_effect=lambda p: request() if p.name.endswith('request.json') else None):
            instance.tick_zoning()
        self.assertFalse(path.exists())


class TickGapProbeTests(unittest.TestCase):
    def test_gaps_between_completed_ticks_and_overruns(self):
        clock = [0.0]
        # tick_completed observed at each 20 ms read: steady, then one 200 ms tick.
        ticks = iter([1, 1, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 5, 6, 6, 6])
        def read(path, previous):
            value = next(ticks, None)
            if value is None:
                raise zoning.character.progress.PublicationPending('changing')
            return {'tick_completed': value}
        def sleep(seconds):
            clock[0] += seconds
        result = zoning.tick_gap_probe(Path('/nonexistent'), seconds=0.5, period=0.02,
                                       clock=lambda: clock[0], sleep=sleep, read=read)
        self.assertEqual(result['ticks'], 5)
        self.assertEqual(result['gaps'], 5)
        self.assertAlmostEqual(result['max_gap_ms'], 200.0, places=0)
        self.assertEqual((result['gaps_over_67ms'], result['gaps_over_150ms'], result['gaps_over_300ms']), (1, 1, 0))
        self.assertGreater(result['read_errors'], 0)

    def test_no_progress_reports_no_gap(self):
        result = zoning.tick_gap_probe(Path('/nonexistent'), seconds=0.05, period=0.01)
        self.assertIsNone(result['max_gap_ms'])
        self.assertEqual(result['reads'], 0)

    def test_probe_thread_skips_trips_and_stops_for_cleanup(self):
        instance = ZoningServerTests.instance(self)
        instance.zoning_report['tick_probe'] = {'samples': [], 'skipped_busy': 0, 'error': None}
        instance.map_progress_path = Path('/nonexistent')
        instance.pending = {'phase': 'baseline'}
        with patch.object(zoning, 'TICK_PROBE_INTERVAL_SECONDS', 0.01), \
             patch.object(zoning, 'tick_gap_probe', return_value={'ticks': 1}) as probe:
            instance.start_tick_probe()
            deadline = time.monotonic() + 5
            while instance.zoning_report['tick_probe']['skipped_busy'] < 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            probe.assert_not_called()
            instance.pending = None
            while not instance.zoning_report['tick_probe']['samples'] and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(instance.stop_tick_probe(timeout=5))
        sample = instance.zoning_report['tick_probe']['samples'][0]
        self.assertEqual((sample['ticks'], sample['map_id']), (1, 1))
        self.assertIsNotNone(sample['seconds_since_map_active'])


class WinePriorityTickTests(unittest.TestCase):
    """A few read-only priority samples during play; nothing is changed."""
    def test_samples_are_spaced_bounded_and_errors_recorded(self):
        instance = ZoningServerTests.instance(self)
        instance.priority_next = 0
        instance.zoning_report['wine_priorities'] = {'samples': []}
        instance.maps, instance.active_map_id = {1: {'ready': True}}, 1
        calls = []
        def snapshot():
            calls.append(1)
            if len(calls) == 2:
                raise OSError('proc vanished')
            return {'programs': {'CityOfHeroes.exe': {'processes': 1, 'threads': 2, 'nice': {'11': 2}}}}
        with patch.object(zoning.scheduler, 'wine_priority_snapshot', snapshot):
            instance.tick_priorities(100.0)
            instance.tick_priorities(101.0)     # inside the interval: no sample
            for step in range(1, 12):
                instance.tick_priorities(100.0 + step * zoning.PRIORITY_INTERVAL_SECONDS)
        samples = instance.zoning_report['wine_priorities']['samples']
        self.assertEqual(len(samples), zoning.PRIORITY_SAMPLES)
        self.assertEqual(samples[0]['programs']['CityOfHeroes.exe']['nice'], {'11': 2})
        self.assertEqual((samples[0]['active_map_id'], samples[0]['resident_maps']), (1, [1]))
        self.assertEqual(samples[1]['error_type'], 'OSError')

    def test_missing_report_is_a_no_op(self):
        instance = ZoningServerTests.instance(self)
        instance.zoning_report.pop('wine_priorities', None)
        instance.priority_next = 0
        with patch.object(zoning.scheduler, 'wine_priority_snapshot', side_effect=AssertionError):
            instance.tick_priorities(1.0)


if __name__ == '__main__':
    unittest.main()
