"""Native contact logs prove initiation only; invalid optional evidence is ignored."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import stationary_contact_evidence as evidence

SESSION = '0123456789abcdef0123456789abcdef'
PID = 44
LOCAL = 'logs/mapserver/entity.log'
EMBEDDED = 'logs/dbserver/entity_2026-10-02-01-00-00.log'


def stamp(seconds):
    return int(time.mktime(time.strptime('261002 21:40:' + f'{seconds:02d}', '%y%m%d %H:%M:%S')) * 1000)


def proof():
    return {'session_id': SESSION, 'client_pid': PID, 'character_id': 1, 'auth_id': 77,
        'map_id': 1, 'name': 'THORHERO', 'account': 'COHLOCAL', 'connected_on_atlas': True,
        'existing_character_verified': True, 'preserved_existing_identity': True,
        'reopen_verified': True, 'native_client_ready_observed': True,
        'client_ready_observed_utc_ms': stamp(10),
        'client_ready_evidence': {'source': 'current_owned_mapserver_immediate_ready',
            'kind': 'ready', 'session_id': SESSION, 'map_id': 1, 'db_id': 1,
            'auth_id': 77, 'name': 'THORHERO', 'account': 'COHLOCAL',
            'windows_pid': 90, 'main_thread_id': 91, 'utc_ms': stamp(9), 'loaded_world_assets': True}}


def message(kind='open', handle='173', name='Ms. Liberty', link='3'):
    suffix = ' ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0'
    if kind == 'open':
        body = f'ContactInteract:GenericOpen Initiating interaction with contact {handle} ({name})'
    else:
        body = f'ContactInteract:Response Received response {link} to contact {handle}'
    return '"THORHERO:COHLOCAL" 0 ' + body + suffix


def line(seconds=12, body=None, *, local=False):
    route = '0' if local else 'City_01_01_1:127.0.0.1:127.0.0.1'
    return f'261002 21:40:{seconds:02d} {route} {body or message()}\n'


def collect(logs, value=None, **changes):
    kwargs = {'session': SESSION, 'client_pid': PID, 'now_utc_ms': stamp(55)}
    kwargs.update(changes)
    return evidence.collect(logs, proof() if value is None else value, **kwargs)


class StationaryContactEvidenceTests(unittest.TestCase):
    def test_actual_native_open_and_following_response_are_bound_without_visual_claims(self):
        raw = line(12) + line(15, message('response'))
        result = collect([(EMBEDDED, raw)])
        self.assertEqual(result['status'], 'native_initiation_observed')
        self.assertTrue(result['native_initiation_observed'])
        self.assertTrue(result['native_response_observed'])
        self.assertEqual([r['kind'] for r in result['records']], ['initiation', 'response'])
        record = result['records'][0]
        self.assertEqual(record['npc_name'], 'Ms. Liberty')
        self.assertEqual(record['contact_runtime_handle'], 173)
        self.assertEqual(record['native_teamup_id'], 0)
        self.assertEqual(record['line_sha256'], hashlib.sha256(raw.splitlines()[0].encode()).hexdigest())
        self.assertEqual(result['records'][1]['matching_initiation_utc_ms'], stamp(12))
        self.assertFalse(result['connection']['native_log_contains_character_db_id'])
        self.assertFalse(result['connection']['native_log_contains_session_or_client_pid'])
        for key in ('dialogue_visual_verified', 'npc_pathing_verified', 'mission_acceptance_verified',
                    'combat_verified', 'sql_game_mutations_performed'):
            self.assertFalse(result[key])

    def test_local_and_embedded_logger_duplicates_do_not_count_as_two_interactions(self):
        raw = line(12) + line(15, message('response'))
        local = line(12, local=True) + line(15, message('response'), local=True)
        result = collect([(LOCAL, local), (EMBEDDED, raw)])
        self.assertEqual(len(result['records']), 2)
        self.assertEqual(result['records'][0]['log_route'], 'local_mapserver')
        self.assertEqual(result['records'][1]['log_route'], 'local_mapserver')

    def test_foreign_routes_map_peer_account_name_and_incomplete_lines_are_rejected(self):
        raw = line()
        candidates = [
            ('logs/foreign/entity.log', raw),
            ('../logs/mapserver/entity.log', line(local=True)),
            (LOCAL, raw),  # embedded envelope at the local route
            (EMBEDDED, line(local=True)),
            (EMBEDDED, raw.replace('City_01_01_1', 'City_02_01_1')),
            (EMBEDDED, raw.replace(':127.0.0.1:', ':192.168.1.1:')),
            (EMBEDDED, raw.replace('THORHERO', 'OTHER')),
            (EMBEDDED, raw.replace('COHLOCAL', 'OTHER')),
            (EMBEDDED, raw.rstrip('\n')),
        ]
        for logs in candidates:
            with self.subTest(logs=logs):
                self.assertEqual(collect([logs])['records'], [])

    def test_connection_and_native_ready_identity_must_match_the_validated_session(self):
        edits = [('session_id', 'f' * 32), ('client_pid', True), ('client_pid', PID + 1),
            ('character_id', True), ('character_id', 2), ('map_id', True), ('map_id', 2),
            ('name', 'OTHER'), ('account', 'OTHER'), ('auth_id', 0),
            ('connected_on_atlas', 1), ('existing_character_verified', False),
            ('preserved_existing_identity', False), ('reopen_verified', False),
            ('native_client_ready_observed', False), ('client_ready_observed_utc_ms', stamp(56))]
        for field, value in edits:
            current = proof(); current[field] = value
            with self.subTest(field=field, value=value), patch.object(evidence.server, 'entity_records') as parser:
                self.assertEqual(collect([(EMBEDDED, line())], current)['status'], 'unavailable')
                parser.assert_not_called()
        for field, value in [('session_id', 'f' * 32), ('db_id', 2), ('map_id', 2),
                ('auth_id', 78), ('kind', 'position'), ('source', 'unowned'),
                ('loaded_world_assets', 1), ('windows_pid', 0), ('main_thread_id', 0),
                ('utc_ms', stamp(11)), ('name', 'OTHER')]:
            current = proof(); current['client_ready_evidence'][field] = value
            with self.subTest(ready_field=field, value=value):
                self.assertEqual(collect([(EMBEDDED, line())], current)['status'], 'unavailable')
        self.assertEqual(collect([(EMBEDDED, line())], session='bad')['status'], 'unavailable')
        self.assertEqual(collect([(EMBEDDED, line())], client_pid=45)['status'], 'unavailable')

    def test_no_contact_in_old_style_connection_physics_logs_remains_optional(self):
        raw = line(9, '"THORHERO:COHLOCAL" 0 Connection:ResumeCharacter from 127.0.0.1:41001 '
                   'AuthName "COHLOCAL" ExpLevel:1')
        ready = evidence.server.ready_record([(EMBEDDED, raw)])
        current = proof(); current['client_ready_evidence'] = ready
        raw += line(20, '"THORHERO:COHLOCAL" 0 PeriodicInfo pos=<104.47,31.95,-531.55> '
                    'ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0')
        result = collect([(EMBEDDED, raw)], current)
        self.assertEqual(result['status'], 'not_observed')
        self.assertFalse(result['native_initiation_observed'])
        self.assertEqual(result['records'], [])
        self.assertEqual(collect([], current)['status'], 'not_observed')

    def test_stale_future_and_invalid_calendar_times_cannot_supply_contact_evidence(self):
        raw = line(9) + line(56) + line(12).replace('261002', '261032')
        self.assertEqual(collect([(EMBEDDED, raw)])['records'], [])
        # A one-second native timestamp is not rounded forward across readiness.
        current = proof(); current['client_ready_observed_utc_ms'] = stamp(12) + 1
        self.assertEqual(collect([(EMBEDDED, line(12))], current)['records'], [])

    def test_malformed_or_foreign_contacts_handles_and_native_integer_fields_are_ignored(self):
        candidates = [message(handle='0'), message(handle='-1'), message(handle='2147483648'),
            message(handle='999999999999999999999'), message(name='NULL'), message(name='Azuria'),
            message().replace('" 0 ', '" 2147483648 '),
            message().replace('Archetype:Class_Blaster', 'Archetype:<script>'),
            message().replace('Incarnate:0', 'Incarnate:2'),
            message().replace('GenericOpen', 'Debug'), message() + ' unexpected',
            message().replace('Ms. Liberty', 'Ms. Liberty\nInjected')]
        for body in candidates:
            with self.subTest(body=body):
                self.assertEqual(collect([(EMBEDDED, line(body=body))])['records'], [])
        result = collect([(EMBEDDED, line(body=message(name='City Representative')))])
        self.assertEqual(result['records'][0]['npc_name'], 'City Representative')

    def test_response_requires_a_preceding_same_route_file_handle_and_recognized_open(self):
        response = line(15, message('response'))
        raw = response + line(20) + line(21, message('response', handle='174'))
        self.assertFalse(collect([(EMBEDDED, raw)])['native_response_observed'])
        raw = line(12) + line(13, message(name='Unknown NPC')) + response
        self.assertFalse(collect([(EMBEDDED, raw)])['native_response_observed'])
        self.assertFalse(collect([(EMBEDDED, line(12)),
            ('logs/dbserver/entity_2026-10-02-02-00-00.log', response)])['native_response_observed'])
        self.assertFalse(collect([(EMBEDDED, line(12) + line(11, message('response')))])['native_response_observed'])
        self.assertFalse(collect([(EMBEDDED, line(12) + line(15, message('response', link='2147483648')))])
            ['native_response_observed'])

    def test_retained_output_is_bounded_and_never_mutates_input_proof(self):
        current = proof(); before = copy.deepcopy(current)
        raw = ''.join(line(12 + index, message(handle=str(173 + index))) for index in range(30))
        result = collect([(EMBEDDED, raw)], current)
        self.assertEqual(len(result['records']), evidence.RECORD_LIMIT)
        self.assertTrue(result['records_truncated'])
        self.assertEqual(current, before)
        for logs in (None, [('bad', 3)], [('bad', 'x')] * 129):
            self.assertEqual(collect(logs)['status'], 'unavailable')
        with patch.object(evidence.server, 'SERVER_LOG_FILE_LIMIT', 10):
            self.assertEqual(collect([(EMBEDDED, line())])['status'], 'unavailable')

    def test_matching_native_source_and_authored_stationary_data_contracts_are_pinned(self):
        source = json.loads((ROOT / 'docs/source-manifest.json').read_text())
        data = json.loads((ROOT / 'docs/data-manifest.json').read_text())
        source_pins = {item['path']: item for item in source['entries']}
        data_pins = {item['path']: item for item in data['entries']}
        texts = {}
        for prefix, paths, pins in [('upstream/ouroboros', evidence.NATIVE_CONTRACT_FILES, source_pins),
                                  ('upstream/i24', evidence.DATA_CONTRACT_FILES, data_pins)]:
            for path in paths:
                raw = (ROOT / prefix / path).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), pins[path]['sha256'], path)
                self.assertEqual(len(raw), pins[path]['size'], path)
                texts[path] = raw.decode()
        contact = texts['MapServer/src/storyarc/contactInteraction.c']
        self.assertIn('"ContactInteract:GenericOpen Initiating interaction with contact %d (%s)"', contact)
        self.assertIn('"ContactInteract:Response Received response %d to contact %d"', contact)
        self.assertIn('START_PACKET(pak, player, SERVER_CONTACT_DIALOG_OPEN)', contact)
        self.assertLess(contact.index('"ContactInteract:GenericOpen'), contact.index('ContactGeneralInteract(player, handle, CONTACTLINK_HELLO)'))
        writer = texts['MapServer/src/dbcomm/logcomm.c']
        self.assertIn('e->teamup_id', writer)
        self.assertIn(' ExpLevel:%d, AlignmentNum:%d, Archetype:%s, Incarnate:%d', writer)
        self.assertIn('PNPCTouched(client, npc)', texts['MapServer/src/player/parseClientInput.c'])
        self.assertIn('ContactOpen(client->entity, ENTPOS(npc)', texts['MapServer/src/storyarc/pnpc.c'])
        self.assertIn('START_INPUT_PACKET(pak, CLIENTINP_TOUCH_NPC)', texts['Game/src/UI/uiCursor.c'])
        self.assertRegex(texts['Common/gameComm/dooranimcommon.h'], r'#define\s+INTERACT_DISTANCE\s+15\b')
        for path in evidence.DATA_CONTRACT_FILES[1:3]:
            self.assertRegex(texts[path], r'\bAI\s+PL_StandStill\b')
            self.assertRegex(texts[path], r'\bContact\s+[^\r\n]+\.contact\b')
        self.assertRegex(texts['data/menu/defaultkey/defaultkeybindings.kb'], r'key\s+f\s+command\s+follow')


if __name__ == '__main__':
    unittest.main()
