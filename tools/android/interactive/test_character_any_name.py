"""0.13.62: the one local character may have any name the game accepts.

Owner, 2026-11-08, after Thor 0.13.61 created the villain Ralakar (Mastermind,
Mercy Island): "please make it so controls arent locked and that i can name them
something other than Thorhero". The guest recognized only THORHERO, so it never
proved Ralakar's connection and the app kept walking and Save disabled. The
character is now the account's container ID 1 under the name its SQL row holds;
every log reader follows that name, and the THORHERO-only native console
producers are replaced by the stock entity logs for any other name.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'android/guest'), str(Path(__file__).resolve().parent)]
import local_character_server as server
import character_zoning as zoning
import stationary_contact_evidence as contact
import task_gate_evidence as task
import native_training_save as training
import test_character_server as lifecycle

NAME = "Dr. O'Malley"           # a period, a space and an apostrophe: regex and SQL metacharacters
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
# Thor 0.13.61 (export 20261108-202611): Ralakar's own stock lines in Mercy Island.
MERCY = 'V_City_01_01_1:127.0.0.1:127.0.0.1'
RALAKAR_READY = ('261108 20:10:43 ' + MERCY + ' "Ralakar:COHLOCAL" 0 Connection:ResumeCharacter from '
                 '127.0.0.1:41958 AuthName "COHLOCAL" ExpLevel:1, AlignmentNum:2, Archetype:Class_Mastermind, '
                 'Incarnate:0 BuildNumber: dev: 0000-00-00 00:00:00\n')
RALAKAR_POSITION = ('261108 20:10:57 ' + MERCY + ' "Ralakar:COHLOCAL" 0 PeriodicInfo pos=<-1131.00,238.50,-181.00> '
                    'ExpLevel:1, AlignmentNum:2, Archetype:Class_Mastermind, Incarnate:0 BuildNumber: dev: '
                    '11316-14643-12341 11312:14134:11830\n')


def named(text, name=NAME):
    return text.replace('THORHERO', name)


def stamp(text):
    return int(time.mktime(time.strptime(text, '%y%m%d %H:%M:%S')) * 1000)


class NameRuleTests(unittest.TestCase):
    def tearDown(self):
        server.reset_character()

    def test_the_game_s_name_rules(self):
        for name in ('THORHERO', 'Ralakar', NAME, 'Wolf-Spider X', 'abc', 'a' * 20, 'Agent 47'):
            self.assertTrue(server.valid_character_name(name), name)
        for name in ('ab', 'a' * 21, ' Ralakar', 'Ralakar ', 'Two  Spaces', 'Tab\tName', 'Ünïcode', '', None, 7):
            self.assertFalse(server.valid_character_name(name), name)

    def test_a_session_binds_one_name_once(self):
        server.reset_character()
        self.assertEqual((server.CHARACTER, server.CHARACTER_BOUND, server.character_label()),
                         ('THORHERO', False, 'your character'))
        self.assertEqual(server.bind_character('Ralakar'), 'Ralakar')
        self.assertEqual(server.bind_character('Ralakar'), 'Ralakar')          # idempotent
        self.assertEqual(server.character_label(), 'Ralakar')
        with self.assertRaisesRegex(server.base.DiagnosticError, 'changed during this session'):
            server.bind_character('THORHERO')
        server.reset_character()
        for name in ('ab', 'Two  Spaces', None):
            with self.subTest(name=name), self.assertRaisesRegex(server.base.DiagnosticError, 'not one the game accepts'):
                server.bind_character(name)
        self.assertFalse(server.CHARACTER_BOUND)

    def test_the_entity_log_prefix_escapes_the_name(self):
        server.bind_character(NAME)
        prefix = server.entity_name_prefix()
        import re
        self.assertIsNotNone(re.fullmatch(prefix, '"' + NAME + ':COHLOCAL"'))
        self.assertIsNone(re.fullmatch(prefix, '"Dr. OXMalley:COHLOCAL"'))
        self.assertIsNone(re.fullmatch(prefix, '"DrX O\'Malley:COHLOCAL"'))


class LogReaderTests(unittest.TestCase):
    """Every log reader follows the session's name and ignores any other."""
    def setUp(self):
        server.reset_character()
        server.bind_character(NAME)
        self.addCleanup(server.reset_character)

    def test_owned_atlas_readers(self):
        own = [('logs/mapserver/entity.log', named(lifecycle.READY) + named(lifecycle.LOGOUT))]
        other = [('logs/mapserver/entity.log', lifecycle.READY + lifecycle.LOGOUT)]
        ready = server.ready_record(own)
        self.assertEqual((ready['name'], ready['log_route']), (NAME, 'local_mapserver'))
        self.assertIsNone(server.ready_record(other))
        self.assertEqual(server.logout_record(own)['name'], NAME)
        self.assertIsNone(server.logout_record(other))
        position = '261001 01:29:55 0 "THORHERO:COHLOCAL" 0 PeriodicInfo pos=<1.00,2.00,3.00> Science Class_Blaster\n'
        self.assertEqual([p['position'] for p in server.native_position_records(
            [('logs/mapserver/entity.log', named(position))])], [[1.0, 2.0, 3.0]])
        self.assertEqual(server.native_position_records([('logs/mapserver/entity.log', position)]), [])
        location = '261001 01:30:00 0 "THORHERO:COHLOCAL" 0 Logout location : map 1 (1.00 2.00 3.00) Science\n'
        delivery = {'sent_utc_ms': stamp('261001 01:29:58')}
        logs = [('logs/mapserver/entity.log', named(lifecycle.LOGOUT + location))]
        found = server.native_logout_position(logs, delivery, stamp('261001 01:29:50'), stamp('261001 01:30:05'))
        self.assertEqual((found['name'], found['position']), (NAME, [1.0, 2.0, 3.0]))
        self.assertIsNone(server.native_logout_position([('logs/mapserver/entity.log', lifecycle.LOGOUT + location)],
                          delivery, stamp('261001 01:29:50'), stamp('261001 01:30:05')))

    def test_zone_readers_with_ralakar_s_own_mercy_island_lines(self):
        server.reset_character(); server.bind_character('Ralakar')
        zoning.register_zone(71)
        self.addCleanup(zoning.MAPS.pop, 71, None)
        logs = [('logs/dbserver/entity_2026-11-08-20-00-00.log', RALAKAR_READY + RALAKAR_POSITION)]
        start, end = stamp('261108 20:10:00'), stamp('261108 20:20:00')
        ready = zoning.stock_ready(logs, 71, start, end)
        self.assertEqual((ready['name'], ready['map_id'], ready['port'], ready['source']),
                         ('Ralakar', 71, 41958, 'current_target_stock_CLIENT_READY_resumeCharacter_success'))
        self.assertEqual([p['position'] for p in zoning.stock_positions(logs, 71, start, end)],
                         [[-1131.0, 238.5, -181.0]])
        moving = '261108 20:12:00 ' + MERCY + ' "Ralakar:COHLOCAL" 0 Step 1: Ent Ralakar moving to map 73, x\n'
        self.assertEqual([row['to_map_id'] for row in zoning.stock_transfers_begun(
            [('logs/dbserver/entity_2026-11-08-20-00-00.log', moving)], 71, start, end)], [73])
        timer = '261108 20:13:00 ' + MERCY + ' "Ralakar:COHLOCAL" 0 [Disconnect:Logout timer expired] Mastermind\n'
        self.assertEqual(zoning.stock_logout([('logs/dbserver/entity_2026-11-08-20-00-00.log', timer)],
                                             71, start, end)['name'], 'Ralakar')
        # The same lines under THORHERO (the earlier fixed name) are not Ralakar's.
        server.reset_character()
        self.assertIsNone(zoning.stock_ready(logs, 71, start, end))
        self.assertEqual(zoning.stock_positions(logs, 71, start, end), [])

    def test_contact_task_and_training_patterns_follow_the_name(self):
        suffix = ' ExpLevel:1, AlignmentNum:0, Archetype:Class_Blaster, Incarnate:0'
        reward = '"' + NAME + '" 0 [Tbl]:Rcv:Points XP: 5, Debt: 0, Inf: 3, Pres: 0 (SGMode off (0))' + suffix
        reward = reward.replace('"' + NAME + '"', '"' + NAME + ':COHLOCAL"')
        self.assertIsNotNone(task.patterns()['reward'].fullmatch(reward))
        self.assertIsNone(task.patterns()['reward'].fullmatch(reward.replace(NAME, 'THORHERO')))
        purchase = '"' + NAME + ':COHLOCAL" 0 BuyPower Click Blaster_Ranged.Archery.Snap_Shot' + suffix
        self.assertIsNotNone(training.purchase_pattern().fullmatch(purchase))
        opening = ('"' + NAME + ':COHLOCAL" 0 ContactInteract:GenericOpen Initiating interaction with contact 12 '
                   '(Matthew Habashy)' + suffix)
        self.assertIsNotNone(contact.patterns()[0].fullmatch(opening))
        server.reset_character()   # back to THORHERO: the patterns follow the name
        self.assertIsNone(task.patterns()['reward'].fullmatch(reward))
        self.assertIsNone(training.purchase_pattern().fullmatch(purchase))


class CreationBindingTests(unittest.TestCase):
    """A character created under another name connects (stock log) and saves."""
    instance = lifecycle.CharacterLifecycleTests.instance
    deliver = lifecycle.CharacterLifecycleTests.deliver

    def setUp(self):
        self.addCleanup(server.reset_character)

    def named_instance(self, name=NAME):
        value = self.instance()                      # resets the module's character name
        rows = {table: [dict(row) for row in values] for table, values in lifecycle.fixture()[0].items()}
        rows['ents'][0]['name'] = name
        inventory = [{key: rows['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS}]
        value.inventory = Mock(return_value=inventory)
        value.sql_rows = Mock(side_effect=lambda table, *_args: rows[table])
        value.query = Mock(return_value=named(lifecycle.CONNECTED, name))
        value.current_logs = Mock(return_value=[('logs/mapserver/entity.log',
                                                 named(lifecycle.READY + lifecycle.LOGOUT, name))])
        # The package declares the THORHERO-only producer; another name never uses it.
        value.map_package = {'inputs': {'mapserver_progress': {'events_contract': {'format': 1}}}}
        return value

    @patch.object(server.progress, 'compare_records')
    def test_a_new_character_named_by_its_player_connects_and_saves(self, _compare):
        value = self.named_instance()
        self.assertEqual(value.creation_report['name'], 'THORHERO')   # unknown until the row exists
        self.assertIsNone(value.character_evidence())
        self.assertTrue(value.creation_report['connected_on_atlas'])
        self.assertEqual((server.CHARACTER, value.creation_report['name']), (NAME, NAME))
        self.assertEqual(value.creation_report['client_ready_evidence']['name'], NAME)
        self.assertIsNone(value.immediate_event_contract())
        receipt = self.deliver(value)
        value.character_next = 0; value.query.return_value = 'invalid container request\n'
        proof = value.character_evidence()
        self.assertTrue(proof['verified'] and proof['committed_sql_verified'])
        self.assertEqual((proof['name'], proof['logout_delivery']), (NAME, receipt))

    @patch.object(server.progress, 'compare_records')
    def test_thorhero_keeps_the_native_producer_and_a_second_row_is_refused(self, _compare):
        value = self.named_instance('THORHERO')
        self.assertEqual(value.immediate_event_contract(), {'format': 1})
        value = self.named_instance()
        second = dict(value.inventory.return_value[0], containerid=43, name='Other Hero')
        value.inventory.return_value = value.inventory.return_value + [second]
        with self.assertRaisesRegex(server.base.DiagnosticError, 'More than one character'):
            value.character_evidence()
        self.assertFalse(server.CHARACTER_BOUND)

    def test_station_travel_follows_only_thorhero(self):
        value = self.named_instance()
        value.monorail_enabled = lambda: True
        with self.assertRaisesRegex(server.base.DiagnosticError, "Turn Game's own zone travel back on"):
            value.bind_session_character({'containerid': 1, 'authname': 'COHLOCAL', 'name': 'Ralakar'})


class StockZoneBindingTests(unittest.TestCase):
    """A reopen in a zone the game's own travel started can bind its ordinary-play save."""
    def setUp(self):
        server.reset_character(); server.bind_character('Ralakar')
        self.addCleanup(server.reset_character)

    def proof(self):
        ready = {'name': 'Ralakar', 'account': 'COHLOCAL', 'loaded_world_assets': True, 'map_id': 71,
                 'log_route': 'embedded_dbserver_logserver', 'utc_ms': 1000, 'line_sha256': 'a' * 64,
                 'source': 'current_target_stock_CLIENT_READY_resumeCharacter_success'}
        return {'session_id': 'c' * 32, 'client_pid': 7, 'character_id': 1, 'map_id': 71, 'auth_id': 77,
                'name': 'Ralakar', 'account': 'COHLOCAL', 'client_ready_observed_utc_ms': 2000,
                'client_ready_evidence': ready, **{key: True for key in (
                    'connected_on_atlas', 'connected_on_supported_map', 'zoning_enabled', 'stock_travel',
                    'existing_character_verified', 'preserved_existing_identity', 'reopen_verified',
                    'native_client_ready_observed')}}

    def test_mercy_island_binding(self):
        binding = server.reopen_connection_binding(self.proof(), 'c' * 32, 7, 3000)
        self.assertEqual((binding['map_id'], binding['name'], binding['scope']),
                         (71, 'Ralakar', 'previously_validated_current_session_stock_zone_connection'))
        for change in ({'name': 'THORHERO'}, {'stock_travel': False}, {'client_pid': 8}, {'map_id': 73},
                       {'client_ready_observed_utc_ms': 4000}):
            proof = self.proof(); proof.update(change)
            with self.subTest(change=change):
                self.assertIsNone(server.reopen_connection_binding(proof, 'c' * 32, 7, 3000))
        proof = self.proof(); proof['client_ready_evidence']['log_route'] = 'local_mapserver'
        self.assertIsNone(server.reopen_connection_binding(proof, 'c' * 32, 7, 3000))
        # A stock-zone binding offers no Atlas reward-credit route (task.records serves 1 and 5).
        self.assertIsNone(task.records([], 1000, 3000, map_id=71))

    def test_zoning_identities_follow_the_bound_name(self):
        creation = {'session_id': 'c' * 32, 'name': 'Ralakar', 'account': 'COHLOCAL', 'character_id': 1,
                    'auth_id': 77, 'map_id': 1, **{key: True for key in (
                        'connected_on_atlas', 'connected_on_supported_map', 'zoning_enabled', 'stock_travel')}}
        self.assertTrue(zoning.creation_identity(creation, 'c' * 32))
        self.assertFalse(zoning.creation_identity(dict(creation, name='THORHERO'), 'c' * 32))
        server.reset_character()
        self.assertFalse(zoning.creation_identity(creation, 'c' * 32))


class AppNameRuleTests(unittest.TestCase):
    """The app's events and budget accept the character's own name (ClientAcceptance.characterName)."""
    HOST = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class NameHost {
    static void check(boolean condition, String detail) { if (!condition) throw new AssertionError(detail); }
    public static void main(String[] args) {
        for (String name : new String[]{"THORHERO", "Ralakar", "Dr. O'Malley", "Wolf-Spider X", "abc"})
            check(ClientAcceptance.characterName(name), "valid " + name);
        for (Object name : new Object[]{"ab", " Ralakar", "Ralakar ", "Two  Spaces", "TooLongNameForTheGame1",
                "Tab\tName", "Ünïcode", null, 7})
            check(!ClientAcceptance.characterName(name), "invalid " + name);
        String session = "0123456789abcdef0123456789abcdef";
        Map<String,Object> event = new LinkedHashMap<>();
        event.put("type", "character_connected"); event.put("session_id", session); event.put("client_pid", 7L);
        event.put("character_id", 1L); event.put("name", "Ralakar"); event.put("account", "COHLOCAL");
        event.put("map_id", 1L);
        check(ClientAcceptance.characterConnectedEvent(event, session, 7L), "connected Ralakar");
        event.put("name", "x"); check(!ClientAcceptance.characterConnectedEvent(event, session, 7L), "connected x");
        Map<String,Object> saved = new LinkedHashMap<>();
        saved.put("type", "character_saved"); saved.put("session_id", session); saved.put("client_pid", 7L);
        saved.put("character_id", 1L); saved.put("name", "Dr. O'Malley"); saved.put("committed_sql_verified", true);
        check(ClientAcceptance.characterSavedEvent(saved, session, 7L), "saved");
        System.out.println("names ok");
    }
}
'''

    @unittest.skipUnless(shutil.which('javac') and shutil.which('java'), 'needs a JDK')
    def test_names_and_events(self):
        with tempfile.TemporaryDirectory(prefix='coh-any-name-') as directory:
            path = Path(directory)
            (path / 'NameHost.java').write_text(self.HOST)
            subprocess.run(['javac', '-d', str(path), str(JAVA / 'ClientAcceptance.java'), str(path / 'NameHost.java')],
                           check=True, capture_output=True, text=True)
            result = subprocess.run(['java', '-cp', str(path), 'io.github.russianranger.cohclientinteractive.NameHost'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('names ok', result.stdout)

    def test_walking_no_longer_waits_for_the_connection_proof(self):
        text = (JAVA / 'ClientActivity.java').read_text()
        start = text.index('private boolean canWalk()')
        body = text[start:text.index('\n', start)]
        self.assertNotIn('canSaveLogout', body)
        for gate in ('!state.characterSaved', '!movementSuppressed', '!textDialogVisible', '!commandInputBusy()',
                     'hasWindowFocus()', 'movementWindowOpen()'):
            self.assertIn(gate, body)


if __name__ == '__main__':
    unittest.main()
