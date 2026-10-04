"""Reject provisional, foreign, stale and crash-only graphical save evidence."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import atlas_world_assets as world_assets
import character_avatar_assets as avatar_assets


def fixture():
    rows = {table: [{field: 1 for field in fields}] for table, fields in server.evidence.SELECTED.items()}
    for table, values in rows.items():
        values[0]['containerid'] = 42
        if table != 'ents': values[0]['subid'] = 0
    rows['ents'][0].update(authid=77, authname='COHLOCAL', name='THORHERO', logincount=1,
                         influencepoints=0, description='', motto='', datecreated='2026-10-01')
    inventory = [{key: rows['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
    attributes = {name: [{'id': 1, 'name': 'accepted'}]
                  for name in ('attributes', 'badgestatsattributes', 'pophelpattributes')}
    return rows, inventory, attributes


LOGOUT = '261001 01:30:00 0 "THORHERO:COHLOCAL" 0 [Disconnect:Logout timer expired] Science Class_Blaster, Level:1\n'
READY = '261001 01:29:50 0 "THORHERO:COHLOCAL" 0 Connection:ResumeCharacter from 127.0.0.1:41001 AuthName "COHLOCAL" ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0\n'
CONNECTED = '42 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 1 SmapId 1\n'
CLOCK = time.mktime(time.strptime('261001 01:30:00', '%y%m%d %H:%M:%S'))
SESSION = '0123456789abcdef0123456789abcdef'


class CharacterSnapshotTests(unittest.TestCase):
    def test_full_first_character_without_influence_mutation_passes(self):
        rows, inventory, attributes = fixture()
        before = copy.deepcopy(rows)
        proof = server.validate_character_rows(rows, [], inventory, attributes, 77)
        self.assertEqual(proof['identity']['containerid'], 42)
        self.assertEqual(proof['login_count'], 1)
        self.assertEqual(rows, before)

    def test_old_characters_preserved_but_new_name_must_be_new(self):
        rows, inventory, attributes = fixture()
        baseline = [dict(inventory[0], containerid=2, name='OLDER')]
        proof = server.validate_character_rows(rows, baseline, baseline + inventory, attributes, 77)
        self.assertEqual(proof['identity']['name'], 'THORHERO')
        with self.assertRaises(server.base.DiagnosticError):
            server.validate_character_rows(rows, inventory, inventory, attributes, 77)
        with self.assertRaises(server.base.DiagnosticError):
            server.validate_character_rows(rows, baseline, inventory, attributes, 77)

    def test_provisional_rows_and_missing_children_wait(self):
        for field in ('class', 'origin', 'logincount'):
            rows, inventory, attributes = fixture(); rows['ents'][0][field] = None
            self.assertIsNone(server.validate_character_rows(rows, [], inventory, attributes, 77))
        for table in server.evidence.SELECTED:
            rows, inventory, attributes = fixture(); rows[table] = []
            self.assertIsNone(server.validate_character_rows(rows, [], inventory, attributes, 77))

    def test_foreign_identity_child_wrong_attribute_and_second_login_fail(self):
        for table, field, value in [('ents','authid',78), ('ents','authname','OTHER'),
                ('ents','name','OTHER'), ('ents','logincount',2), ('ents','class',999),
                ('powers','containerid',3), ('costumeparts','geom',999), ('ents2','subid',1)]:
            rows, inventory, attributes = fixture(); rows[table][0][field] = value
            with self.subTest(table=table, field=field), self.assertRaises(server.base.DiagnosticError):
                server.validate_character_rows(rows, [], inventory, attributes, 77)

    def test_duplicate_children_and_extra_character_are_rejected(self):
        rows, inventory, attributes = fixture()
        rows['powers'] *= 2
        with self.assertRaises(server.base.DiagnosticError):
            server.validate_character_rows(rows, [], inventory, attributes, 77)
        rows, inventory, attributes = fixture()
        inventory.append(dict(inventory[0], containerid=43))
        with self.assertRaises(server.base.DiagnosticError):
            server.validate_character_rows(rows, [], inventory, attributes, 77)


class LogoutTests(unittest.TestCase):
    def test_routed_atlas_records_and_local_fallback_match_stock_logger_formats(self):
        for parser, line in ((server.ready_record, READY), (server.logout_record, LOGOUT)):
            local = parser([('logs/mapserver/entity.log', line)])
            self.assertEqual(local['log_route'], 'local_mapserver')
            routed = line[:16] + 'City_01_01_1:127.0.0.1:127.0.0.1 ' + line[18:].rstrip('\n') + ' BuildNumber: dev\n'
            good = parser([('logs/dbserver/entity_2026-10-01-01-00-00.log', routed)])
            self.assertEqual(good['log_route'], 'embedded_dbserver_logserver')
            self.assertEqual(good['map_instance'], 'City_01_01_1')
            for name, bad in [('logs/mapserver/entity.log', routed),
                    ('logs/dbserver/entity_2026-10-01-01-00-00.log', line),
                    ('other/entity_2026-10-01-01-00-00.log', routed),
                    ('logs/dbserver/entity_2026-10-01-01-00-00.log', routed.replace('City_01_01', 'City_02_01')),
                    ('logs/dbserver/entity_2026-10-01-01-00-00.log', routed.replace('City_01_01_1:', 'City_01_01_2:')),
                    ('logs/dbserver/entity_2026-10-01-01-00-00.log', routed.replace('127.0.0.1:', '192.0.2.1:', 1)),
                    ('logs/dbserver/entity_2026-10-01-01-00-00.log', routed.replace(':127.0.0.1 ', ':192.0.2.1 ', 1)),
                    ('logs/mapserver/entity.log', line.replace(' 0 "THORHERO', ' 1 "THORHERO', 1))]:
                with self.subTest(parser=parser.__name__, name=name, bad=bad):
                    self.assertIsNone(parser([(name, bad)]))

    def receipt(self):
        return {'format': 1, 'session_id': SESSION, 'client_pid': 123, 'character_id': 42,
                'action': 'quittologin', 'sent_utc_ms': 90000}

    def test_delivery_is_current_ready_client_and_exact_action(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            self.assertIsNone(server.read_logout_delivery(path, SESSION, 123, 42, 10000, 100000))
            value = self.receipt(); path.write_text(json.dumps(value))
            self.assertEqual(server.read_logout_delivery(path, SESSION, 123, 42, 10000, 100000), value)
            for field, changed in [('format', True), ('session_id', 'f'*32), ('client_pid', 124),
                    ('client_pid', True), ('character_id', 43), ('character_id', True), ('action', 'quit'),
                    ('sent_utc_ms', 9999), ('sent_utc_ms', 100001), ('sent_utc_ms', True), ('extra', 1)]:
                path.write_text(json.dumps(dict(value, **{field: changed})))
                with self.subTest(field=field, changed=changed), self.assertRaises(server.base.DiagnosticError):
                    server.read_logout_delivery(path, SESSION, 123, 42, 10000, 100000)
            path.write_text(json.dumps(value))
            with self.assertRaises(server.base.DiagnosticError):
                server.read_logout_delivery(path, SESSION, 123, 42, 10000, 210001)

    def test_delivery_refuses_symlink_hardlink_nonregular_and_oversize_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); actual = root/'actual'; path = root/'receipt.json'
            actual.write_text(json.dumps(self.receipt())); path.symlink_to(actual)
            with self.assertRaises(OSError): server.read_logout_delivery(path, SESSION, 123, 42, 10000, 100000)
            path.unlink(); os.link(actual, path)
            with self.assertRaises(server.base.DiagnosticError):
                server.read_logout_delivery(path, SESSION, 123, 42, 10000, 100000)
            path.unlink(); path.mkdir()
            with self.assertRaises(server.base.DiagnosticError):
                server.read_logout_delivery(path, SESSION, 123, 42, 10000, 100000)
            path.rmdir(); path.write_bytes(b'x' * 513)
            with self.assertRaises(server.base.DiagnosticError):
                server.read_logout_delivery(path, SESSION, 123, 42, 10000, 100000)

    def test_timer_must_follow_delivered_command_with_second_precision(self):
        logout = server.logout_record([('logs/mapserver/entity.log', LOGOUT)])
        for offset, expected in [(-120001, False), (-120000, True), (-5000, True), (999, True), (1000, False)]:
            delivery = dict(self.receipt(), sent_utc_ms=int(CLOCK*1000) + offset)
            self.assertEqual(server.logout_follows_delivery(logout, delivery), expected)

    def test_client_ready_requires_own_character_loopback_and_complete_entity_line(self):
        good = server.ready_record([('logs/mapserver/entity.log', READY)])
        self.assertEqual(good['log_timestamp'], '261001 01:29:50')
        self.assertTrue(good['loaded_world_assets'])
        for name, line in [('logs/chat_261001.log', READY), ('logs/mapserver/entity.log', READY.rstrip('\n')),
                ('logs/mapserver/entity.log', READY.replace('THORHERO', 'OTHER')),
                ('logs/mapserver/entity.log', READY.replace('COHLOCAL', 'OTHER')),
                ('logs/mapserver/entity.log', READY.replace('127.0.0.1', '192.0.2.1')),
                ('logs/mapserver/entity.log', READY.replace('41001', '65536')),
                ('logs/mapserver/entity.log', 'chat says: ' + READY)]:
            with self.subTest(name=name, line=line): self.assertIsNone(server.ready_record([(name, line)]))

    def test_only_complete_owned_entity_live_logout_record_counts(self):
        good = [('logs/mapserver/entity.log', LOGOUT)]
        self.assertEqual(server.logout_record(good)['reason'], 'Logout timer expired')
        for name, line in [('logs/chat_261001.log', LOGOUT), ('logs/mapserver/entity.log', LOGOUT.rstrip('\n')),
                ('logs/mapserver/entity.log', LOGOUT.replace('THORHERO','OTHER')),
                ('logs/mapserver/entity.log', LOGOUT.replace('COHLOCAL','OTHER')),
                ('logs/mapserver/entity.log', LOGOUT.replace('Logout timer expired','NetLink was closed')),
                ('logs/mapserver/entity.log', 'chat says: ' + LOGOUT)]:
            with self.subTest(name=name, line=line): self.assertIsNone(server.logout_record([(name,line)]))


class CharacterLifecycleTests(unittest.TestCase):
    def instance(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.clock = self.enterContext(patch.object(server.time, 'time', return_value=CLOCK - 15))
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}), root=Path('/private'),
                                args=SimpleNamespace(session_id=SESSION, state=Path(directory)))
        value = server.LocalCharacterServer(owner)
        rows, inventory, attributes = fixture()
        value.schema = {'expected_attributes': attributes}
        value.baseline = []; value.auth_id = 77
        value.health = Mock(); value.sample_progress = Mock(return_value={
            'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        value.inventory = Mock(return_value=inventory)
        value.query = Mock(return_value=CONNECTED)
        value.current_logs = Mock(return_value=[('logs/mapserver/entity.log', READY + LOGOUT)])
        value.sql_rows = Mock(side_effect=lambda table, *_args: rows[table])
        return value

    def test_character_map_uses_native_production_grouping_and_retains_live_readiness_guards(self):
        value = self.instance()
        value.runtime = value.owner.args.state / 'runtime'
        value.owner.args.wine = Path('/wine')
        value.owner.wine_env = {'DISPLAY': ':1', 'PRIVATE_SESSION': SESSION}
        value.ctx.check = Mock(); value.ctx.stage = Mock(); value.ctx.event = Mock(); value.ctx.passed = Mock()
        value.ctx.deadline = 10000
        child = Mock(); value.ctx.start = Mock(return_value=child)
        value.inventory.return_value = []
        status = f'1 {server.evidence.MAP_PATH} S: 0/0 Ip: 127.0.0.1:7001 Mem: 0\n'
        value.query.side_effect = ['invalid container request\n', status.rstrip('\n') + ' NotReady 1\n', status]
        def tick(number):
            return {'available': True, 'tick_completed': number, 'unchanged_seconds': 0}
        value.sample_progress.side_effect = [None, tick(0), None, tick(1), tick(2), None, tick(3), tick(4)]
        bindings = {'loopback_only': True, 'udp_port': 7001}
        with patch.object(server.login.LocalLoginServer, 'start') as parent, \
                patch.object(server.game, 'check_game_port') as port, \
                patch.object(server.evidence, 'game_listener_bindings', return_value=bindings), \
                patch.object(server.progress, 'compare_records') as compare, \
                patch.object(server.time, 'monotonic', side_effect=[0, 1, 7, 68]), \
                patch.object(server.time, 'sleep'):
            value.start()
        parent.assert_called_once_with()
        port.assert_called_once_with(7001, server.socket.SOCK_DGRAM)
        value.ctx.start.assert_called_once_with('local-character-atlas', ['/usr/bin/env',
            '--chdir=' + str(value.runtime), Path('/wine'), server.base.windows_path(value.runtime / 'MapServer.exe'),
            '-nogui', '-db', '127.0.0.1', '-nosharedmemory', '-nostats', '-udp', '7001', '-tcp', '0', '-map_id', '1',
            '-donotautogroup'], env=dict(value.owner.wine_env, **{server.evidence.GAME_LOOPBACK_ENV: '1',
                server.progress.ENVIRONMENT: server.base.windows_path(value.runtime / 'character-atlas-progress.bin')}))
        self.assertIs(value.map_process, child)
        self.assertEqual(value.creation_report['map_autogroup_policy'], {'native_option': '-donotautogroup',
            'configured_do_not_auto_group': True, 'policy_basis': 'native_production_default'})
        self.assertEqual(value.query.call_args_list, [call(['-getstatus', '1', '1'], 'atlas-baseline'),
            call(['-getstatus', '1', '1'], 'atlas-ready'), call(['-getstatus', '1', '1'], 'atlas-ready')])
        self.assertEqual([sample['ready'] for sample in value.creation_report['map_samples']], [False, True])
        self.assertTrue(value.creation_report['map_startup_guard']['requires_completed_tick_before_protocol'])
        self.assertTrue(value.creation_report['map_startup_guard']['passed'])
        compare.assert_called_once_with(tick(4), tick(3))
        self.assertTrue(value.creation_report['map_ready'])
        self.assertTrue(value.ctx.report['mapserver_started'])
        self.assertTrue(value.report['mapserver_started'])
        value.ctx.passed.assert_called_once_with(atlas_ready=True,
            map=server.evidence.parse_map_status(status), loopback_only=True)

    def deliver(self, value):
        self.clock.return_value = CLOCK + 1
        value.creation_report['client_pid'] = 123
        receipt = {'format': 1, 'session_id': SESSION, 'client_pid': 123, 'character_id': 42,
                   'action': 'quittologin', 'sent_utc_ms': int((CLOCK-5)*1000)}
        (value.owner.args.state/'character-logout.json').write_text(json.dumps(receipt))
        return receipt

    @patch.object(server.progress, 'compare_records')
    def test_save_requires_previous_connection_logout_record_and_committed_children(self, _compare):
        value = self.instance()
        value.query.return_value = 'invalid container request\n'
        self.assertIsNone(value.character_evidence())
        value.sql_rows.assert_not_called()
        value.character_next = 0; value.query.return_value = CONNECTED
        self.assertIsNone(value.character_evidence())
        self.assertTrue(value.creation_report['connected_on_atlas'])
        receipt = self.deliver(value)
        value.character_next = 0; value.query.return_value = 'invalid container request\n'
        proof = value.character_evidence()
        self.assertTrue(proof['verified']); self.assertTrue(proof['requested_logout_observed'])
        self.assertTrue(proof['logout_timer_observed']); self.assertEqual(proof['logout_delivery'], receipt)
        self.assertNotIn('protocol_logout_verified', proof)
        self.assertTrue(proof['committed_sql_verified']); self.assertEqual(proof['character_id'],42)
        self.assertFalse(proof['forced_stop_before_save']); self.assertFalse(proof['reopen_verified'])

    @patch.object(server.progress, 'compare_records')
    def test_db_map_assignment_is_insufficient_without_client_ready(self, _compare):
        value = self.instance(); value.current_logs.return_value = []
        self.assertIsNone(value.character_evidence())
        self.assertTrue(value.creation_report['db_map_assignment_observed'])
        self.assertFalse(value.creation_report['connected_on_atlas'])
        value.character_next = 0; value.current_logs.return_value = [('logs/mapserver/entity.log', READY)]
        self.assertIsNone(value.character_evidence())
        self.assertTrue(value.creation_report['connected_on_atlas'])
        self.assertEqual(value.creation_report['client_ready_evidence']['log_timestamp'], '261001 01:29:50')
        ready_ms = value.creation_report['client_ready_observed_utc_ms']
        value.character_next = 0; self.clock.return_value += 15
        value.character_evidence()
        self.assertEqual(value.creation_report['client_ready_observed_utc_ms'], ready_ms)

    @patch.object(server.progress, 'compare_records')
    def test_live_timeout_without_delivered_command_cannot_pass(self, _compare):
        value = self.instance(); value.character_evidence(); value.character_next = 0
        value.creation_report['client_pid'] = 123
        value.query.return_value = 'invalid container request\n'
        self.assertIsNone(value.character_evidence()); value.sql_rows.assert_not_called()
        self.assertFalse(value.creation_report['verified'])

    @patch.object(server.progress, 'compare_records')
    def test_save_rechecks_delivery_age_after_sql_reads(self, _compare):
        value = self.instance(); value.character_evidence(); value.character_next = 0
        receipt = self.deliver(value); value.query.return_value = 'invalid container request\n'
        rows, _, _ = fixture()
        def delayed_sql(table, *_args):
            self.clock.return_value = receipt['sent_utc_ms']/1000 + 121
            return rows[table]
        value.sql_rows.side_effect = delayed_sql
        with self.assertRaises(server.base.DiagnosticError): value.character_evidence()
        self.assertFalse(value.creation_report['verified'])

    @patch.object(server.progress, 'compare_records')
    def test_crash_or_network_disconnect_cannot_pass(self, _compare):
        value = self.instance(); value.character_evidence(); value.character_next = 0
        self.deliver(value)
        value.query.return_value = 'invalid container request\n'
        value.current_logs.return_value = [('logs/mapserver/entity.log',LOGOUT.replace('Logout timer expired','NetLink was closed'))]
        self.assertIsNone(value.character_evidence()); value.sql_rows.assert_not_called()
        self.assertFalse(value.creation_report['verified'])

    @patch.object(server.login.LocalLoginServer, 'health')
    def test_map_crash_is_reported_before_secondary_crash_listener(self, _health):
        value = self.instance()
        value.health = server.LocalCharacterServer.health.__get__(value)
        value.map_process = Mock()
        value.map_process.text.return_value = ('defs/powers does not exist\n[ERROR] Program crash detected\n'
            'Exception caught: EXCEPTION_ACCESS_VIOLATION\n'
            'COH_GAME_LOOPBACK_ONLY bind verified: protocol=tcp address=127.0.0.1 port=52015\n')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Atlas crashed: Program crash detected'):
            value.health()
        self.assertIn('defs/powers', value.creation_report['mapserver_crash']['context'])
        value.map_process.process.poll.assert_not_called()

    def test_stale_progress_and_poll_throttle_do_not_query(self):
        value = self.instance(); value.sample_progress.return_value['unchanged_seconds'] = 21
        self.assertIsNone(value.character_evidence()); value.inventory.assert_not_called()
        value.sample_progress.return_value['unchanged_seconds'] = 0
        self.assertIsNone(value.character_evidence()); value.inventory.assert_not_called()

    def test_private_server_copy_preserves_accepted_schema_and_import_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); work = root/'work'; imported = root/'import'; runtime=root/'runtime'
            work.mkdir(); imported.mkdir(); runtime.mkdir()
            source = work/'server'; source.mkdir()
            raw = imported/'source.txt'; raw.write_text('immutable')
            (source/'source.txt').symlink_to(raw)
            (source/'schema.txt').write_text('not the accepted schema')
            target = runtime/'server'; target.mkdir(); (target/'schema.txt').write_text('accepted')
            value = self.instance(); value.owner.work=work; value.owner.args.game_data=imported
            value.ctx.check=Mock()
            value.copy_private_data(source,target)
            self.assertEqual(raw.read_text(),'immutable')
            self.assertEqual((target/'schema.txt').read_text(),'accepted')
            self.assertFalse((target/'source.txt').is_symlink())
            (target/'source.txt').write_text('private changed')
            self.assertEqual(raw.read_text(),'immutable')

    def map_staging_fixture(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        root = Path(directory); work = root/'work'; imported = root/'import'
        work.mkdir(); imported.mkdir()
        source = work/'data'; source.mkdir()
        value = self.instance(); value.owner.work = work; value.owner.args.game_data = imported
        value.ctx.check = Mock(); value.ctx.event = Mock()
        self.enterContext(patch.object(server.device, 'DATA_COUNT', 1))
        self.enterContext(patch.object(server.device, 'DATA_BYTES', 1))
        self.enterContext(patch.object(world_assets, 'FILE_COUNT', 3))
        self.enterContext(patch.object(world_assets, 'PAYLOAD_BYTES', 32))
        self.enterContext(patch.object(avatar_assets, 'ALLOWED', frozenset({'avatar-a', 'avatar-b'})))
        self.enterContext(patch.object(avatar_assets, 'PAYLOAD_BYTES', 8))
        return value, source, root

    @staticmethod
    def readonly_map_file(source, name, content=b'x'):
        path = source/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content); path.chmod(0o400)
        return path

    def map_count_inputs(self, source):
        self.readonly_map_file(source, 'imported.txt')
        # Exhaust the existing prerequisite/generated-cache allowance first.
        # The verified supplements must still have their own finite allowance.
        for index in range(4096):
            self.readonly_map_file(source, f'bin/cache-{index}.bin')
        for index in range(3):
            self.readonly_map_file(source, f'textures/world-{index}.texture')
        for index in range(2):
            self.readonly_map_file(source, f'costumes/avatar-{index}.geo')

    def test_verified_world_and_avatar_fit_above_previous_map_file_allowance(self):
        value, source, root = self.map_staging_fixture()
        self.map_count_inputs(source)
        result = value.stage_map_data(source, root/'staged')
        self.assertGreater(result['files'], 1 + 4096)
        self.assertEqual(result['files'], 1 + 4096 + 3 + 2)
        self.assertEqual(result['copied_private_files'], 4096)
        self.assertEqual(result['linked_immutable_files'], 6)
        self.assertTrue((root/'staged/textures/world-0.texture').is_symlink())
        self.assertEqual((source/'textures/world-0.texture').read_bytes(), b'x')
        self.assertFalse((root/'staged/bin/cache-0.bin').is_symlink())
        (root/'staged/bin/cache-0.bin').write_bytes(b'private regenerated cache')
        self.assertEqual((source/'bin/cache-0.bin').read_bytes(), b'x')

    def test_map_file_limit_accepts_exact_known_inputs_and_rejects_one_extra(self):
        value, source, root = self.map_staging_fixture()
        self.map_count_inputs(source)
        self.assertEqual(value.stage_map_data(source, root/'at-limit')['files'], 4102)
        self.readonly_map_file(source, 'unaccounted.texture')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Private map data exceeded bound'):
            value.stage_map_data(source, root/'over-limit')

    def test_map_byte_limit_accepts_exact_supplement_allowance_and_rejects_one_extra(self):
        value, source, root = self.map_staging_fixture()
        # A read-only sparse input exercises real stat/containment/staging without
        # allocating or copying the one-GiB generated-cache byte allowance.
        path = source/'world.geometry'
        old_limit = 1 + 1024**3
        new_limit = old_limit + 32 + 8
        with path.open('wb') as stream:
            stream.truncate(new_limit)
        path.chmod(0o400)
        staged = value.stage_map_data(source, root/'at-byte-limit')
        self.assertEqual(staged['bytes'], new_limit)
        self.assertGreater(staged['bytes'], old_limit)
        self.assertTrue((root/'at-byte-limit/world.geometry').is_symlink())
        path.chmod(0o600)
        with path.open('r+b') as stream:
            stream.truncate(new_limit + 1)
        path.chmod(0o400)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Private map data exceeded bound'):
            value.stage_map_data(source, root/'over-byte-limit')

    def test_map_manifest_must_match_qualified_donor(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory); (path/'game-package.json').write_text('{}')
            with self.assertRaises(server.base.DiagnosticError): server.LocalCharacterServer.verify_map_payload(path)


if __name__ == '__main__': unittest.main()
