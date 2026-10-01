"""Reject provisional, foreign, stale and crash-only graphical save evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server


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


LOGOUT = '261001 01:30:00 1 "THORHERO:COHLOCAL" 0 [Disconnect:Logout timer expired] Science Class_Blaster, Level:1\n'
CONNECTED = '42 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 1 SmapId 1\n'


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
    def test_only_complete_owned_entity_live_logout_record_counts(self):
        good = [('logs/entity_261001.log', LOGOUT)]
        self.assertEqual(server.logout_record(good)['reason'], 'Logout timer expired')
        for name, line in [('logs/chat_261001.log', LOGOUT), ('logs/entity_261001.log', LOGOUT.rstrip('\n')),
                ('logs/entity_261001.log', LOGOUT.replace('THORHERO','OTHER')),
                ('logs/entity_261001.log', LOGOUT.replace('COHLOCAL','OTHER')),
                ('logs/entity_261001.log', LOGOUT.replace('Logout timer expired','NetLink was closed')),
                ('logs/entity_261001.log', 'chat says: ' + LOGOUT)]:
            with self.subTest(name=name, line=line): self.assertIsNone(server.logout_record([(name,line)]))


class CharacterLifecycleTests(unittest.TestCase):
    def instance(self):
        owner = SimpleNamespace(ctx=SimpleNamespace(report={}), root=Path('/private'),
                                args=SimpleNamespace(session_id='0123456789abcdef0123456789abcdef'))
        value = server.LocalCharacterServer(owner)
        rows, inventory, attributes = fixture()
        value.schema = {'expected_attributes': attributes}
        value.baseline = []; value.auth_id = 77
        value.health = Mock(); value.sample_progress = Mock(return_value={
            'available': True, 'tick_completed': 7, 'unchanged_seconds': 0})
        value.inventory = Mock(return_value=inventory)
        value.query = Mock(return_value=CONNECTED)
        value.current_logs = Mock(return_value=[('logs/entity_261001.log',LOGOUT)])
        value.sql_rows = Mock(side_effect=lambda table, *_args: rows[table])
        return value

    @patch.object(server.progress, 'compare_records')
    def test_save_requires_previous_connection_logout_record_and_committed_children(self, _compare):
        value = self.instance()
        value.query.return_value = 'invalid container request\n'
        self.assertIsNone(value.character_evidence())
        value.sql_rows.assert_not_called()
        value.character_next = 0; value.query.return_value = CONNECTED
        self.assertIsNone(value.character_evidence())
        self.assertTrue(value.creation_report['connected_on_atlas'])
        value.character_next = 0; value.query.return_value = 'invalid container request\n'
        proof = value.character_evidence()
        self.assertTrue(proof['verified']); self.assertTrue(proof['protocol_logout_verified'])
        self.assertTrue(proof['committed_sql_verified']); self.assertEqual(proof['character_id'],42)
        self.assertFalse(proof['forced_stop_before_save']); self.assertFalse(proof['reopen_verified'])

    @patch.object(server.progress, 'compare_records')
    def test_crash_or_network_disconnect_cannot_pass(self, _compare):
        value = self.instance(); value.character_evidence(); value.character_next = 0
        value.query.return_value = 'invalid container request\n'
        value.current_logs.return_value = [('logs/entity_261001.log',LOGOUT.replace('Logout timer expired','NetLink was closed'))]
        self.assertIsNone(value.character_evidence()); value.sql_rows.assert_not_called()
        self.assertFalse(value.creation_report['verified'])

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

    def test_map_manifest_must_match_qualified_donor(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory); (path/'game-package.json').write_text('{}')
            with self.assertRaises(server.base.DiagnosticError): server.LocalCharacterServer.verify_map_payload(path)


if __name__ == '__main__': unittest.main()
