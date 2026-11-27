"""0.13.87: several heroes in the one local account, chosen (or made) in the game's own character list.

Owner, 2026-11-25: "every account can create multiple characters - I don't like the whole
'switch hero' method". Until now a session followed exactly container 1 of the account; a second
hero made in the character list stopped the session and the saved game was refused afterwards.
A Play session now reads every saved hero before login, expects the one played last, and follows
whichever hero enters the game: another saved hero keeps the reopen's checks under its own ID, a
new hero turns the session into a creation.
"""
import copy
from pathlib import Path
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_reopen_diagnostic as reopen
import character_session_budget as budget
import character_zoning as zoning
import local_character_server as server
import zone_travel
import test_dynamic_initial_map as dynamic_tests
import test_saved_map_startup as saved
import test_stock_travel as stock
from test_character_server import fixture

SESSION = saved.SESSION


def ready_line(name, map_id, utc_ms, port=7001):
    return ('ARMPORT_CLIENT_READY_V1 utc_ms=%d map_id=%d port=%d name="%s" auth="COHLOCAL"\r\n'
            % (utc_ms, map_id, port, name)).encode()


class SeveralHeroesTests(unittest.TestCase):
    def test_the_save_proof_names_the_hero_s_class(self):
        # 0.13.88: for the report (and CI's Primalist probe); never a reason to fail a save.
        owner = SimpleNamespace(schema={'expected_attributes': {'attributes': [
            {'id': 1, 'name': 'race'}, {'id': 2, 'name': 'class_scrapper'}, {'id': 3, 'name': 'class_primalist'}]}})
        name = lambda rows: server.LocalCharacterServer.saved_class_name(owner, rows)
        self.assertEqual(name({'ents': [{'class': 3}]}), 'class_primalist')
        self.assertEqual(name({'ents': [{'class': 2}]}), 'class_scrapper')
        for rows in ({'ents': [{'class': 9}]}, {'ents': [{}]}, {'ents': []}, {}, None):
            self.assertIsNone(name(rows))

    instance = saved.SavedMapStartupTests.instance
    dynamic = dynamic_tests.DynamicInitialMapTests.dynamic
    layer = dynamic_tests.DynamicInitialMapTests.layer
    serve = dynamic_tests.DynamicInitialMapTests.serve

    def setUp(self):
        self.addCleanup(server.reset_character)
        waiting = patch.object(zoning, 'NEW_HERO_ROW_SECONDS', 0)
        waiting.start()
        self.addCleanup(waiting.stop)

    def tearDown(self):
        for map_id in [m for m in zoning.MAPS if m not in (1, 5, 101)]:
            del zoning.MAPS[map_id]

    def heroes(self, value, *, second_map=1, second_last='2026-11-20 10:00:00', first_last='2026-11-25 10:00:00'):
        """Hero 1 (THORHERO) keeps the fixture's zone; hero 2 (Second Hero) is saved in second_map."""
        rows2 = copy.deepcopy(self.rows)
        for values in rows2.values():
            for row in values:
                row['containerid'] = 2
        rows2['ents'][0]['name'] = 'Second Hero'
        self.all_rows = {1: self.rows, 2: rows2}
        self.inventory.append({key: rows2['ents'][0][key] for key in server.evidence.IDENTITY_FIELDS})
        self.positions = {1: self.saved_position,
                          2: dict(containerid=2, mapid=None, staticmapid=second_map, posx=1.0, posy=2.0, posz=3.0)}
        self.last = {1: first_last, 2: second_last}
        value.schema['expected_tables'] = {'ents': ['containerid', 'active', 'lastactive', 'staticmapid', 'authname']}

        def selected(table, fields, keys, where='TRUE'):
            ids = [int(part) for part in where.replace('containerid IN (', '').replace('containerid=', '')
                   .rstrip(')').split(',')] if where != 'TRUE' else sorted(self.all_rows)
            if fields == ('containerid', 'mapid', 'staticmapid', 'posx', 'posy', 'posz'):
                return [copy.deepcopy(self.positions[i]) for i in ids]
            if fields == ('containerid', 'lastactive'):
                return [{'containerid': i, 'lastactive': self.last[i]} for i in ids]
            if fields == ('containerid', 'authname', 'staticmapid'):
                return [{'containerid': row['containerid'], 'authname': row['authname'],
                         'staticmapid': self.positions[row['containerid']]['staticmapid']} for row in self.inventory]
            return [copy.deepcopy(row) for i in ids for row in self.all_rows[i][table]]
        value.sql_rows = Mock(side_effect=selected)
        return rows2

    def test_every_saved_hero_is_read_before_login_and_the_one_played_last_is_expected(self):
        value = self.instance(5)
        self.heroes(value)
        value.capture_baseline()
        self.assertEqual(sorted(value.hero_baselines), [1, 2])
        self.assertEqual((value.CHARACTER_ID, server.HERO_ID, server.CHARACTER), (1, 1, 'THORHERO'))
        heroes = value.creation_report['heroes']
        self.assertEqual((heroes['count'], heroes['order'], heroes['expected_character_id']), (2, [1, 2], 1))
        self.assertEqual(value.active_map_id, 5)
        self.assertEqual(value.creation_report['baseline']['character_id'], 1)
        ready = [call.kwargs for call in value.ctx.event.call_args_list if call.args == ('existing_character_ready',)]
        self.assertEqual((ready[0]['character_id'], ready[0]['hero_count']), (1, 2))
        # Played last: the other hero is expected and its zone is the one prepared.
        other = self.instance(5)
        self.heroes(other, second_last='2026-11-26 09:00:00')
        other.capture_baseline()
        self.assertEqual((other.CHARACTER_ID, server.HERO_ID, server.CHARACTER), (2, 2, 'Second Hero'))
        self.assertEqual(other.active_map_id, 1)
        self.assertEqual(other.creation_report['before_character_id'], 2)
        self.assertEqual(other.creation_report['heroes']['order'], [2, 1])

    def test_two_heroes_with_one_name_or_another_account_are_refused(self):
        value = self.instance(5)
        rows2 = self.heroes(value)
        self.inventory[1]['name'] = rows2['ents'][0]['name'] = 'THORHERO'
        with self.assertRaisesRegex(server.base.DiagnosticError, 'differs from the accepted local account'):
            value.capture_baseline()
        value = self.instance(5)
        rows2 = self.heroes(value)
        self.inventory[1]['authname'] = 'OTHER'
        with self.assertRaisesRegex(server.base.DiagnosticError, 'saved heroes of the one COHLOCAL account'):
            value.capture_baseline()

    def chosen(self, *, second_map=1):
        """A launch that expects hero 1 (King's Row); the game asks for hero 2's zone and hero 2 enters it."""
        value = self.dynamic(5)
        self.heroes(value, second_map=second_map)
        value.capture_baseline()
        sup = self.layer(value)
        value._activate = Mock(wraps=lambda map_id: setattr(value, 'active_map_id', map_id)
                               or value.creation_report.update(map_id=map_id))
        return value, sup

    def test_the_game_may_start_another_saved_hero_s_zone_and_nothing_else(self):
        value, sup = self.chosen()
        # A zone no saved hero is in stays refused (owner: no Atlas Park unless the character is there).
        value.created_hero_supported = Mock(return_value=False)
        self.assertEqual(value.zone_policy.decide(stock.record(101, 3, 1))[0], 'start')   # Atlas Park instance 2: hero 2's zone
        value, sup = self.chosen()
        value.created_hero_supported = Mock(return_value=False)
        self.assertEqual(value.zone_policy.decide(stock.record(5, 3, 1))[0], 'start')     # the expected hero's own
        value, sup = self.chosen(second_map=5)
        value.created_hero_supported = Mock(return_value=False)
        self.assertEqual(value.zone_policy.decide(stock.record(1, 3, 1)), ('delink', 'not_the_saved_zone'))

    def test_another_saved_hero_entering_the_game_becomes_the_session_s_hero(self):
        value, sup = self.chosen()
        launched = self.serve(value, sup, 1, 9, 3, ready=True)
        initial = value.dynamic_initial()
        self.assertEqual((initial['zone_choice'], initial['launch_expected_map_id'], initial['expected_map_id']),
                         ('another_saved_hero', 5, 1))
        value.tick_dynamic_initial()
        self.assertEqual(value.active_map_id, 1)
        # Nobody has resumed yet: nothing changes.
        self.assertFalse(value.observe_chosen_hero())
        value.maps[1]['process'].output = bytearray(ready_line('Second Hero', 1, launched + 5000))
        value.current_logs = Mock(return_value=[])
        self.assertEqual(value.entered_heroes(), [('Second Hero', 1)])
        self.assertTrue(value.observe_chosen_hero())
        self.assertEqual((value.CHARACTER_ID, server.HERO_ID, server.CHARACTER), (2, 2, 'Second Hero'))
        proof = value.creation_report
        self.assertEqual((proof['before_character_id'], proof['baseline_character_id'], proof['name']),
                         (2, 2, 'Second Hero'))
        self.assertEqual(proof['baseline']['saved_position'], self.positions[2])
        self.assertIs(value.baseline_snapshot, value.hero_baselines[2]['snapshot'])
        self.assertEqual((proof['heroes']['chosen_character_id'], proof['heroes']['choice']), (2, 'another_saved_hero'))
        self.assertEqual(value.active_map_id, 1)        # the zone the game started is kept
        self.assertEqual(value.zoning_report['saved_startup']['map_id'], 1)
        events = [call.kwargs for call in value.ctx.event.call_args_list if call.args == ('session_hero',)]
        self.assertEqual([(row['character_id'], row['name'], row['created_in_session']) for row in events],
                         [(2, 'Second Hero', False)])
        # The session's row among the two, and the unchanged inventory, are what the reopen checks.
        identity = value.session_identity(copy.deepcopy(self.inventory))
        self.assertEqual(identity['containerid'], 2)
        value.auth_id = identity['authid']
        value.verify_current_identity(identity, copy.deepcopy(self.inventory))
        # It cannot change again, and not after the hero is in the game.
        self.assertFalse(value.observe_chosen_hero())
        proof['connected_on_atlas'] = True
        with self.assertRaisesRegex(server.base.DiagnosticError, 'cannot change after it entered the game'):
            value.use_hero_baseline(1, chosen=True)

    def test_a_hero_in_a_zone_it_is_not_saved_in_is_refused(self):
        value, sup = self.chosen()
        launched = self.serve(value, sup, 1, 9, 3, ready=True)
        value.tick_dynamic_initial()
        # The expected hero (saved in King's Row) resumes in Atlas Park: nothing of this is accepted.
        value.baseline_snapshot = value.hero_baselines[1]['snapshot']
        value.creation_report['existing_character_verified'] = True
        with self.assertRaisesRegex(server.base.DiagnosticError, 'not the saved zone'):
            value.connection_metadata()

    def test_the_zone_started_beside_the_client_makes_way_for_the_chosen_hero_s_zone(self):
        with patch.dict('os.environ', {zoning.EARLY_ZONE_ENV: '1'}):
            value, sup = self.chosen()
            process = Mock(); process.poll.return_value = None

            def spawn(target, **keywords):
                value.maps[target] = dict(stock.owned(ready=False), launch_utc_ms=int(time.time() * 1000),
                                          launch_monotonic=time.monotonic())
                value.maps[target]['process'].process = process
            value._spawn_map = Mock(side_effect=spawn)
            with patch.object(zoning, 'available_memory_mib', return_value=9000):
                record = value.start_early_zone()
            self.assertTrue(record['started'])
            self.assertEqual(sorted(value.maps), [5])
            # The game asks for hero 2's Atlas Park: King's Row, never asked for, is stopped.
            self.assertEqual(value.admit_zone_request(1), None)
            self.assertEqual(sorted(value.maps), [])
            process.terminate.assert_called_once_with()
            self.assertEqual((record['ended'], record['stopped_for_map_id']), (True, 1))
            self.assertEqual(value.dynamic_initial()['zone_servers_before_enter_game'], 0)

    def test_a_loaded_zone_beside_the_client_stays_and_the_chosen_hero_s_zone_becomes_the_session_s(self):
        with patch.dict('os.environ', {zoning.EARLY_ZONE_ENV: '1'}):
            value, sup = self.chosen()

            def spawn(target, **keywords):
                value.maps[target] = dict(stock.owned(ready=False), launch_utc_ms=int(time.time() * 1000),
                                          launch_monotonic=time.monotonic())
            value._spawn_map = Mock(side_effect=spawn)
            with patch.object(zoning, 'available_memory_mib', return_value=9000):
                self.assertTrue(value.start_early_zone()['started'])
            # King's Row is ready before anyone pressed Enter Game: it is the session's zone for now.
            value.maps[5]['ready'] = True
            value.tick_dynamic_initial()
            initial = value.dynamic_initial()
            self.assertEqual((initial['activated'], value.active_map_id), (True, 5))
            # A zone no hero is saved in is still refused; hero 2's Atlas Park starts beside King's Row.
            value.created_hero_supported = Mock(return_value=False)
            self.assertEqual(value.admit_zone_request(36), 'not_the_saved_zone')
            self.assertEqual(value.admit_zone_request(5), None)
            self.assertEqual(value.admit_zone_request(1), None)
            self.assertEqual((initial['zone_choice'], initial['chosen_zone_map_id'], sorted(value.maps)),
                             ('another_saved_hero', 1, [5]))
            launched = int(time.time() * 1000)
            value.maps[1] = dict(stock.owned(ready=True), launch_utc_ms=launched, launch_monotonic=time.monotonic())
            value.maps[1]['process'].output = bytearray(ready_line('Second Hero', 1, launched + 4000))
            value.maps[5]['process'].output = bytearray()
            value.current_logs = Mock(return_value=[])
            self.assertTrue(value.observe_chosen_hero())
            self.assertEqual((value.CHARACTER_ID, value.active_map_id, sorted(value.maps)), (2, 1, [1, 5]))
            self.assertEqual((initial['map_id'], initial['expected_map_id'], initial['left_loaded_zone_map_id']), (1, 1, 5))
            value.verify_initial_connection(initial)
            self.assertEqual(value.ready_floor_ms, launched - 999)

    def test_a_hero_made_in_the_character_list_turns_the_session_into_its_creation(self):
        value, sup = self.chosen(second_map=5)        # both saved heroes are in King's Row
        created = dict(self.inventory[0], containerid=3, name='New Hero')
        # The game asks for Atlas Park before the new row is visible: refused; once it is there, started.
        with patch.object(zoning, 'NEW_HERO_ROW_SECONDS', 0):
            self.assertEqual(value.zone_policy.decide(stock.record(1, 3, 1)), ('delink', 'not_the_saved_zone'))
        self.inventory.append(created)
        self.positions[3] = dict(containerid=3, mapid=1, staticmapid=1, posx=0.0, posy=0.0, posz=0.0)
        launched = self.serve(value, sup, 1, 9, 3, ready=True)
        self.assertEqual(value.dynamic_initial()['zone_choice'], 'new_hero')
        value.tick_dynamic_initial()
        value.maps[1]['process'].output = bytearray(ready_line('New Hero', 1, launched + 5000))
        value.current_logs = Mock(return_value=[])
        self.assertTrue(value.observe_chosen_hero())
        self.assertIsInstance(value, zoning.LocalCharacterZoningCreatedHeroServer)
        self.assertEqual((value.CHARACTER_ID, server.HERO_ID, server.CHARACTER), (3, 3, 'New Hero'))
        proof = value.creation_report
        self.assertIs(value.ctx.report['character_reopen'], proof)
        self.assertEqual((proof['created_in_session'], proof['operation'], proof['saved_heroes_at_start']),
                         (True, 'hero_created_in_the_character_list', 2))
        for key in ('before_character_id', 'baseline_character_id', 'existing_character_verified', 'baseline'):
            self.assertNotIn(key, proof)
        self.assertFalse(value.requires_saved_character)
        # A creation's checks: the new row is the only change, and the saved heroes are the baseline.
        identity = value.session_identity(copy.deepcopy(self.inventory))
        self.assertEqual(identity, created)
        value.auth_id = created['authid']
        value.verify_current_identity(identity, copy.deepcopy(self.inventory))
        metadata = value.connection_metadata()
        self.assertEqual((metadata['created_in_session'], metadata['stock_travel'], metadata['starting_zone_map_id']),
                         (True, True, 1))
        with self.assertRaisesRegex(server.base.DiagnosticError, 'More than one character exists'):
            value.session_identity(self.inventory + [dict(created, containerid=4, name='Fourth')])
        events = [call.kwargs for call in value.ctx.event.call_args_list if call.args == ('session_hero',)]
        self.assertEqual([(row['character_id'], row['created_in_session']) for row in events], [(3, True)])

    def test_the_orchestrator_reads_a_created_hero_s_proof_as_a_creation(self):
        server.bind_hero('New Hero', 3)
        proof = {'session_id': SESSION, 'name': 'New Hero', 'account': 'COHLOCAL', 'character_id': 3,
                 'auth_id': 77, 'map_id': 1, 'connected_on_atlas': True, 'connected_on_supported_map': True,
                 'zoning_enabled': True, 'stock_travel': True, 'created_in_session': True}
        diagnostic = reopen.ZoningCharacterReopenDiagnostic
        self.assertTrue(diagnostic.identity_verified(proof, SESSION))
        self.assertFalse(diagnostic.identity_verified(dict(proof, character_id=1), SESSION))
        self.assertFalse(diagnostic.identity_verified(dict(proof, created_in_session=False), SESSION))
        self.assertFalse(diagnostic.proof_verified(proof, SESSION))
        saved_proof = dict(proof, verified=True, committed_sql_verified=True, requested_logout_observed=True,
                           logout_timer_observed=True, disconnected_before_sql=True, forced_stop_before_save=False)
        self.assertTrue(diagnostic.proof_verified(saved_proof, SESSION))
        data = diagnostic.connected_event_data(SimpleNamespace(), proof)
        self.assertEqual((data['created_in_session'], data['stock_travel'], data['map_name']), (True, True, 'Atlas Park'))
        self.assertNotIn('reopen_verified', data)
        self.assertEqual(diagnostic.saved_event_data(SimpleNamespace(), saved_proof)['map_id'], 1)

    def test_a_first_creation_follows_the_one_new_row_not_a_saved_hero(self):
        # Heroes probe 45784712557: the zoning creation inherited the reopen's rule (the session's
        # saved hero among an unchanged inventory) and refused the first hero ever created.
        first = {'containerid': 1, 'authid': 77, 'authname': 'COHLOCAL', 'name': 'THORHERO'}
        second = dict(first, containerid=2, name='HEROTWO')
        for cls in (zoning.LocalCharacterZoningCreationServer, zoning.LocalCharacterZoningCreatedHeroServer):
            value = SimpleNamespace(baseline=[], CHARACTER_ID=1)
            self.assertIsNone(cls.session_identity(value, []))
            self.assertEqual(cls.session_identity(value, [first]), first)
            self.assertIs(cls.observe_chosen_hero(value), False)
            value.baseline = [first]
            self.assertEqual(cls.session_identity(value, [first, second]), second)
            with self.assertRaisesRegex(server.base.DiagnosticError, 'More than one character'):
                cls.session_identity(value, [first, second, dict(first, containerid=3, name='THREE')])
        # A reopen keeps its own rule.
        self.assertIsNot(zoning.LocalCharacterZoningServer.session_identity,
                         zoning.LocalCharacterZoningCreationServer.session_identity)

    def test_every_check_of_the_hero_s_id_follows_the_session_s_hero(self):
        server.bind_hero('Second Hero', 2)
        proof = {'session_id': SESSION, 'name': 'Second Hero', 'account': 'COHLOCAL', 'character_id': 2,
                 'auth_id': 77, 'map_id': 1, 'before_character_id': 2, 'baseline_character_id': 2,
                 'zoning_enabled': True, 'connected_on_atlas': True, 'connected_on_supported_map': True,
                 'existing_character_verified': True, 'reopen_verified': True, 'preserved_existing_identity': True,
                 'native_client_ready_observed': True}
        self.assertTrue(zoning.character_identity(proof, SESSION))
        self.assertFalse(zoning.character_identity(dict(proof, character_id=1), SESSION))
        self.assertFalse(zoning.character_identity(dict(proof, baseline_character_id=1), SESSION))
        server.reset_character()
        self.assertEqual(server.HERO_ID, 1)
        self.assertFalse(zoning.character_identity(proof, SESSION))
        # The first name binds the session; a different hero needs the explicit replacement.
        server.bind_hero('THORHERO', 1)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'changed during this session'):
            server.bind_hero('THORHERO', 2)
        server.bind_hero('Second Hero', 2, replace=True)
        self.assertEqual((server.CHARACTER, server.HERO_ID), ('Second Hero', 2))


class MemorySampleLineTests(unittest.TestCase):
    """0.13.90: every memory sample is also an output line (the app logs lines as they arrive)."""

    def subject(self):
        events = []
        ctx = SimpleNamespace(event=lambda kind, **fields: events.append((kind, fields)))
        return SimpleNamespace(
            zoning_report={'memory_trace': {'samples': []}}, memory_trace_next=0, maps={71: {}, 1: {}},
            creation_report={}, ctx=ctx, owner=SimpleNamespace(args=SimpleNamespace(session_id='s' * 32))), events

    def test_a_sample_is_recorded_and_sent(self):
        subject, events = self.subject()
        figures = {'MemTotal': 15255, 'MemAvailable': 8076, 'SwapFree': 3342, 'pressure': 'some avg10=0.20'}
        with patch.object(zoning.scheduler, 'memory_snapshot', return_value=dict(figures)):
            zoning.LocalCharacterZoningServer.tick_memory_trace(subject, 100.0)
            zoning.LocalCharacterZoningServer.tick_memory_trace(subject, 105.0)      # inside the interval
            zoning.LocalCharacterZoningServer.tick_memory_trace(subject, 100.0 + zoning.MEMORY_TRACE_INTERVAL_SECONDS)
        samples = subject.zoning_report['memory_trace']['samples']
        self.assertEqual(len(samples), 2)
        self.assertEqual([kind for kind, _ in events], ['guest_memory_sample'] * 2)
        sent = events[0][1]
        self.assertEqual({key: sent[key] for key in figures}, figures)
        self.assertEqual((sent['zone_servers'], sent['client_connected'], sent['session_id'], sent['is_success_proof']),
                         ([1, 71], False, 's' * 32, False))
        self.assertEqual(sent['utc_ms'], samples[0]['utc_ms'])

    def test_a_missing_output_channel_does_not_stop_the_sample(self):
        subject, _ = self.subject()
        subject.ctx = SimpleNamespace()
        with patch.object(zoning.scheduler, 'memory_snapshot', return_value={'MemAvailable': 1}):
            zoning.LocalCharacterZoningServer.tick_memory_trace(subject, 1.0)
        self.assertEqual(len(subject.zoning_report['memory_trace']['samples']), 1)


if __name__ == '__main__':
    unittest.main()
