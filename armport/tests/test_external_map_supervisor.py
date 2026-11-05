"""On-demand zone requests: the guest supervisor reads exactly what the DbServer layer writes."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'android/guest'), str(ROOT / 'armport/tests'), str(ROOT / 'armport/app')]
import external_map_supervisor as supervisor  # noqa: E402

OVERLAY = ROOT / 'database/external-maps/overlay/DBServer/src'
COMMAND = '.\\mapserver.exe -db 127.0.0.1 -udp -1 -map_id {map_id} -launcher -cookie {cookie}'


def record(map_id=7, cookie=3, sequence=1, **changes):
    value = {'format': 1, 'sequence': sequence, 'map_id': map_id, 'cookie': cookie, 'base_map_id': 0,
             'is_static': 1, 'transient': 0, 'dont_auto_start': 0, 'preload_transient': 0, 'db_process_id': 300,
             'map_name': 'maps/City_Zones/City_02_01/City_02_01.txt', 'mission_info': '',
             'command': COMMAND.format(map_id=map_id, cookie=cookie) + ' -aggrocap 17 -locale 0'}
    value.update(changes)
    return value


def encoded(value):
    return (json.dumps(value, separators=(',', ':')) + '\n').encode()


def marker(map_id, cookie, static=1):
    return '%s map_id=%d cookie=%d static=%d\n' % (supervisor.MARKER, map_id, cookie, static)


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class SourceAgreement(unittest.TestCase):
    def test_strings_fields_and_limits_are_the_overlays_own(self):
        header = (OVERLAY / 'wine_external_maps.h').read_text()
        source = (OVERLAY / 'wine_external_maps.c').read_text()
        self.assertIn('#define COH_DB_EXTERNAL_MAPS_ACK "' + supervisor.ACK + '"', header)
        self.assertIn('#define COH_DB_EXTERNAL_MAPS_REQUEST_MARKER "' + supervisor.MARKER + '"', header)
        self.assertIn('#define COH_DB_EXTERNAL_MAPS_ENVIRONMENT "' + supervisor.DB_ENVIRONMENT + '"', header)
        self.assertIn('#define COH_DB_EXTERNAL_MAPS_DIRECTORY "' + supervisor.DB_DIRECTORY_ENVIRONMENT + '"', header)
        self.assertIn('#define REQUEST_BYTES %d' % supervisor.RECORD_BYTES, source)
        self.assertIn('length >= %d' % (supervisor.DIRECTORY_LIMIT + 1), source)
        self.assertEqual(tuple(re.findall(r'putInt\(record, &used, "(\w+)"', source)), supervisor.INT_FIELDS)
        self.assertEqual(dict((name, int(limit)) for name, limit in
                              re.findall(r'putString\(record, &used, "(\w+)", \w+, (\d+)\)', source)),
                         supervisor.STRING_LIMITS)
        self.assertIn('"%s map_id=%d cookie=%d static=%d\\n", COH_DB_EXTERNAL_MAPS_REQUEST_MARKER', source)

    @unittest.skipUnless(shutil.which('cc') and os.name != 'nt', 'needs a POSIX C compiler')
    def test_records_written_by_the_overlay_are_read_and_decided(self):
        import external_map_requests as harness
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            exe = harness.build(work)
            requests = work / 'requests'
            requests.mkdir()
            console = harness.run(exe, {'PATH': os.environ.get('PATH', '/usr/bin:/bin'),
                'COH_WINE_DB_EXTERNAL_MAPS': '1', 'COH_WINE_DB_MANUAL_ATLAS': '1',
                'COH_WINE_DB_EXTERNAL_MAPS_DIR': str(requests)}, 'publish')
            value = supervisor.ExternalMapSupervisor(requests, session_maps={1})
            added = value.poll(console)
            self.assertTrue(value.ack_observed)
            self.assertIsNone(value.stopped)
            self.assertEqual([(entry['map_id'], entry['decision'], entry['reason']) for entry in added],
                             [(5, 'delink', 'zone_not_served_yet'), (915, 'delink', 'command_prefix')])
            self.assertEqual(added[0]['options'], {'kept': [], 'dropped': ['-locale']})
            self.assertEqual(added[1]['map_name'], 'maps/Missions/Office/"quoted"\\path\t.txt')
            self.assertEqual([value.next_delink()['map_id'], value.next_delink()['map_id']], [5, 915])
            self.assertEqual(value.poll(console), [])


class ShippedServerConfig(unittest.TestCase):
    """The command the device's DbServer builds from the shipped servers.cfg (CI r56z refused it)."""
    def test_shipped_map_server_params_are_known_options(self):
        import shlex
        config = (ROOT / 'upstream/ouroboros/data/server/db/servers.cfg').read_text()
        params = [shlex.split(line)[1] for line in config.splitlines()
                  if line.split() and line.split()[0].lower() == 'mapserverparams']
        self.assertEqual(params, ['-productionmode'])
        known = (supervisor.PASS_FLAGS | supervisor.DROP_FLAGS | supervisor.PASS_INTEGER | supervisor.PASS_DECIMAL
                 | set(supervisor.PASS_PATTERN) | supervisor.DROP_VALUE)
        for token in ' '.join(params).split():
            if token.startswith('-'):
                self.assertIn(token, known)
        # launchercomm.c order with AssertMode, NoStats 1, MapServerParams, MaxLevel 50, aggrocap 17, Locale en.
        value = record(command=COMMAND.format(map_id=7, cookie=3) + ' -assertmode 2 -nostats -productionmode'
                       ' -maxLevel 50 -aggrocap 17 -locale 0')
        options = supervisor.command_options(value)
        self.assertEqual(options['kept'], ['-maxLevel', '50', '-aggrocap', '17'])
        self.assertEqual(options['dropped'], ['-assertmode', '-nostats', '-productionmode', '-locale'])


class RecordAndCommand(unittest.TestCase):
    def test_exact_record_is_accepted_and_anything_else_refused(self):
        self.assertEqual(supervisor.parse_record(encoded(record()))['map_id'], 7)
        bad = [b'', b'{}\n', encoded(record())[:-1], encoded(record(format=2)), encoded(record(map_id=0)),
               encoded(record(cookie=-1)), encoded(record(transient=2)), encoded(record(is_static=True)),
               encoded(record(map_name='x' * 1024)), encoded(record(sequence=1.5)),
               encoded(dict(record(), extra=1)), encoded(record(map_name='caf\u00e9')).replace(b'\\u00e9', b'\xc3\xa9'),
               encoded(record())[:-2] + b',"map_id":7}\n', b'x' * 8193]
        for index, data in enumerate(bad):
            with self.subTest(index=index), self.assertRaises(supervisor.RequestRefused):
                supervisor.parse_record(data)

    def test_game_options_are_kept_and_process_options_replaced(self):
        value = record(command=COMMAND.format(map_id=7, cookie=3) + ' -nostats -logserver 10.0.0.2 -aggrocap 17'
                       ' -xpscale 2.000000 -blockedmapkeys A_B,C -WeeklyTFTokens 1700000000:none -locale 0')
        options = supervisor.command_options(value)
        self.assertEqual(options['kept'], ['-aggrocap', '17', '-xpscale', '2.000000', '-blockedmapkeys', 'A_B,C',
                                           '-WeeklyTFTokens', '1700000000:none'])
        self.assertEqual(options['dropped'], ['-nostats', '-logserver', '-locale'])
        argv = supervisor.start_arguments(value, 7004, options)
        # Memory and link options are the owner's own (mapserver_memory_arguments, client link options).
        self.assertEqual(argv[:12], ['-nogui', '-db', '127.0.0.1', '-nostats', '-udp', '7004',
                                     '-tcp', '0', '-map_id', '7', '-cookie', '3'])
        self.assertNotIn('-launcher', argv)
        mission = record(transient=1, preload_transient=1,
                         command=COMMAND.format(map_id=7, cookie=3) + ' -transient -preloadtransient -locale 0')
        self.assertEqual(supervisor.command_options(mission)['kept'], ['-transient', '-preloadtransient'])
        refused = {'unrecognized_option': ' -locale 0 -mystery', 'unsupported_locale': ' -locale 5',
                   'transient_mismatch': ' -transient -locale 0', 'option_value': ' -aggrocap x -locale 0',
                   'command_shape': '  -locale 0'}
        for reason, suffix in refused.items():
            with self.subTest(reason=reason), self.assertRaisesRegex(supervisor.RequestRefused, reason):
                supervisor.command_options(record(command=COMMAND.format(map_id=7, cookie=3) + suffix))
        try:
            supervisor.command_options(record(command=COMMAND.format(map_id=7, cookie=3) + ' -locale 0 -my"st'))
        except supervisor.RequestRefused as failure:
            self.assertEqual((failure.reason, failure.detail), ('unrecognized_option', '-my?st'))
        with self.assertRaisesRegex(supervisor.RequestRefused, 'command_prefix'):
            supervisor.command_options(record(command=COMMAND.format(map_id=8, cookie=3) + ' -locale 0'))


class Polling(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.clock = Clock()
        self.value = supervisor.ExternalMapSupervisor.create(self.root, 'requests', session_maps={1, 5},
                                                             clock=self.clock)
        self.console = '\n' + supervisor.ACK + '\n'

    def tearDown(self):
        self.temporary.cleanup()

    def publish(self, value, *, announce=True):
        (self.value.directory / ('map-%d-%d.json' % (value['map_id'], value['cookie']))).write_bytes(encoded(value))
        if announce:
            self.console += marker(value['map_id'], value['cookie'], value['is_static'])

    def test_directory_is_fresh_and_private(self):
        self.assertEqual(self.value.directory.stat().st_mode & 0o777, 0o700)
        with self.assertRaisesRegex(supervisor.RequestRefused, 'stale_directory'):
            supervisor.ExternalMapSupervisor.create(self.root, 'requests', session_maps=set())

    def test_each_request_is_decided_once_and_session_maps_are_left_alone(self):
        self.publish(record(map_id=5, cookie=1, sequence=1))
        self.publish(record(map_id=7, cookie=2, sequence=2))
        (self.value.directory / 'map-9-9.json.tmp').write_text('partial')
        added = self.value.poll(self.console)
        self.assertEqual([(e['map_id'], e['decision']) for e in added], [(5, 'session_flow'), (7, 'delink')])
        self.assertEqual(self.value.poll(self.console), [])
        entry = self.value.next_delink()
        self.assertEqual(entry['map_id'], 7)
        self.assertIsNone(self.value.next_delink())
        self.value.delink_finished(entry, exit_code=0, elapsed_seconds=3.2)
        report = self.value.report()
        self.assertEqual(report['counts']['delink_finished'], 1)
        self.assertFalse(report['map_starts_executed'])
        self.assertEqual(report['db_process_id'], 300)
        json.dumps(report)

    def test_start_policy_starts_served_maps_and_delinks_failed_starts(self):
        decisions = {7: ('start', {'port': 7004, 'tree': 'zones'}), 8: ('delink', 'zone_not_served')}
        self.value.policy = lambda value, options: decisions[value['map_id']]
        self.value.session_maps = lambda map_id: map_id == 5
        self.publish(record(map_id=5, cookie=1, sequence=1))
        self.publish(record(map_id=7, cookie=2, sequence=2))
        self.publish(record(map_id=8, cookie=3, sequence=3))
        added = self.value.poll(self.console)
        self.assertEqual([(e['map_id'], e['decision'], e['reason']) for e in added],
                         [(5, 'session_flow', 'started_by_session_flow'), (7, 'start', 'served'),
                          (8, 'delink', 'zone_not_served')])
        entry = self.value.next_start()
        self.assertEqual((entry['map_id'], entry['plan']['port']), (7, 7004))
        self.assertIsNone(self.value.next_start())
        self.assertEqual(self.value.next_delink()['map_id'], 8)
        self.value.start_launched(entry, port=7004)
        self.assertTrue(self.value.report()['map_starts_executed'])
        self.value.start_failed(entry, 'not ready in time', elapsed_seconds=900.5)
        again = self.value.next_delink()
        self.assertEqual((again['map_id'], again['decision'], again['reason']), (7, 'delink', 'start_failed'))
        self.assertEqual(again['start']['failed_seconds'], 900.5)
        counts = self.value.report()['counts']
        self.assertEqual((counts['start'], counts['started'], counts['start_failed'], counts['delink']), (1, 1, 1, 2))
        self.assertEqual(self.value.report()['session_maps'], 'dynamic')

    def test_start_budget_falls_back_to_delink(self):
        self.value.policy = lambda value, options: ('start', {})
        for index in range(supervisor.MAX_STARTS + 1):
            self.publish(record(map_id=20 + index, cookie=1, sequence=index + 1))
        added = self.value.poll(self.console)
        self.assertEqual([e['decision'] for e in added].count('start'), supervisor.MAX_STARTS)
        self.assertEqual(added[-1]['reason'], 'start_budget')

    def test_unannounced_file_is_never_acted_on(self):
        self.publish(record(), announce=False)
        self.assertEqual(self.value.poll(self.console), [])
        self.clock.now += supervisor.MARKER_GRACE_SECONDS + 1
        self.assertEqual(self.value.poll(self.console), [])
        self.assertIsNone(self.value.next_delink())
        self.assertEqual(self.value.report()['requests'][0]['reason'], 'unconfirmed_request')
        # A marker printed before the record is renamed into place is read on the next poll.
        self.console += marker(8, 4)
        self.assertEqual(self.value.poll(self.console), [])
        self.publish(record(map_id=8, cookie=4, sequence=2), announce=False)
        self.assertEqual([e['map_id'] for e in self.value.poll(self.console)], [8])

    def test_partial_console_line_waits_for_its_newline(self):
        self.publish(record(), announce=False)
        self.assertEqual(self.value.poll(self.console + marker(7, 3)[:-1]), [])
        self.assertEqual(len(self.value.poll(self.console + marker(7, 3))), 1)

    def test_unreadable_record_with_a_marker_is_still_delinked_by_the_marker_id(self):
        (self.value.directory / 'map-7-3.json').write_bytes(b'{"broken"\n')
        self.console += marker(7, 3)
        entry, = self.value.poll(self.console)
        self.assertEqual((entry['decision'], entry['reason']), ('delink', 'record_bounds'))
        self.assertEqual(self.value.next_delink()['map_id'], 7)

    def test_session_map_is_never_delinked_even_when_unreadable(self):
        (self.value.directory / 'map-1-3.json').write_bytes(b'not json\n')
        self.console += marker(1, 3)
        entry, = self.value.poll(self.console)
        self.assertEqual(entry['decision'], 'session_flow')
        self.assertIsNone(self.value.next_delink())

    def test_stops_on_anything_that_is_not_the_owned_dbserver(self):
        cases = {
            'marker_without_acknowledgement': lambda: setattr(self, 'console', marker(7, 3)),
            'repeated_acknowledgement': lambda: setattr(self, 'console', self.console + supervisor.ACK + '\n'),
            'other_dbserver': lambda: self.publish(record(map_id=8, cookie=4, sequence=2, db_process_id=301)),
        }
        for reason, change in cases.items():
            with self.subTest(reason=reason):
                self.tearDown(); self.setUp()
                self.publish(record())
                change()
                self.value.poll(self.console)
                self.assertEqual(self.value.stopped, reason)
                self.assertTrue(reason == 'other_dbserver' or self.value.next_delink() is None)

    def test_symlink_and_foreign_entries(self):
        target = self.root / 'elsewhere.json'
        target.write_bytes(encoded(record()))
        os.symlink(target, self.value.directory / 'map-7-3.json')
        (self.value.directory / 'notes.txt').write_text('x')
        self.console += marker(7, 3)
        entry, = self.value.poll(self.console)
        self.assertEqual(entry['reason'], 'not_regular_file')
        self.assertIn('foreign_entry', [item['reason'] for item in self.value.report()['anomalies']])

    def test_budgets_bound_delinks(self):
        for index in range(supervisor.MAX_DELINKS + 1):
            self.publish(record(map_id=10 + index, cookie=1, sequence=index + 1))
        added = self.value.poll(self.console)
        self.assertEqual(sum(entry['decision'] == 'delink' for entry in added), supervisor.MAX_DELINKS)
        self.assertEqual(self.value.stopped, 'delink_budget')
        self.assertIsNone(self.value.next_delink())


class ServerIntegration(unittest.TestCase):
    """LocalCharacterServer: off unless asked and the exact DbServer layer is installed."""
    def server(self, root, layer):
        import local_character_server as character
        server = object.__new__(character.LocalCharacterServer)
        server.owner = SimpleNamespace(args=SimpleNamespace(state=root, session_id='s1', wine='/usr/bin/wine'),
                                       wine_env={'WINEPREFIX': '/p'})
        server.manual_atlas_startup = {'external_maps': {'build_input_sha256': 'b' * 64}} if layer else {}
        server.creation_report = {}
        server.external_maps = server.external_maps_query = None
        server.external_maps_next = 0
        server.query_count = 0
        server.runtime = root / 'runtime'
        (server.runtime / 'data/server/db').mkdir(parents=True)
        return character, server

    def test_environment_only_with_the_option_and_the_layer(self):
        for requested, layer, enabled in ((False, True, False), (True, False, False), (True, True, True)):
            with self.subTest(requested=requested, layer=layer), tempfile.TemporaryDirectory() as temporary:
                character, server = self.server(Path(temporary), layer)
                environment = {supervisor.DB_ENVIRONMENT: 'stale'}
                with unittest.mock.patch.dict(os.environ, {supervisor.ENABLE_ENVIRONMENT: '1' if requested else '0'}):
                    environment = self.environment(character, server, environment)
                self.assertEqual(server.creation_report['external_maps']['enabled'], enabled)
                self.assertEqual(environment.get(supervisor.DB_ENVIRONMENT), '1' if enabled else None)
                self.assertEqual((Path(temporary) / 'external-map-requests-s1').is_dir(), enabled)
                self.assertEqual((server.runtime / 'data/server/db/weeklyTF.cfg').is_file(), enabled)
                if enabled:
                    self.assertTrue(server.creation_report['external_maps']['weekly_tf_config']['written'])
                    self.assertTrue(environment[supervisor.DB_DIRECTORY_ENVIRONMENT].endswith('external-map-requests-s1'))
                    server.cleanup_external_maps()
                    self.assertFalse((Path(temporary) / 'external-map-requests-s1').exists())

    @staticmethod
    def environment(character, server, environment):
        # The login parent only removes the manual Atlas switch; call this layer's part directly.
        with unittest.mock.patch.object(character.login.LocalLoginServer, 'dbserver_environment',
                                        lambda self, value: value):
            return character.LocalCharacterServer.dbserver_environment(server, environment)

    def test_tick_delinks_one_request_at_a_time_through_the_owned_query(self):
        with tempfile.TemporaryDirectory() as temporary:
            character, server = self.server(Path(temporary), True)
            with unittest.mock.patch.dict(os.environ, {supervisor.ENABLE_ENVIRONMENT: '1'}):
                self.environment(character, server, {})
            directory = server.external_maps.directory
            for map_id, cookie in ((7, 1), (8, 2)):
                (directory / ('map-%d-%d.json' % (map_id, cookie))).write_bytes(
                    encoded(record(map_id=map_id, cookie=cookie, sequence=map_id)))
            console = '\n' + supervisor.ACK + '\n' + marker(7, 1) + marker(8, 2)
            started = []
            child = SimpleNamespace(process=SimpleNamespace(poll=lambda: None), reader=SimpleNamespace(is_alive=lambda: True),
                                    started=0)
            server.process = SimpleNamespace(text=lambda: console)
            server.ctx = SimpleNamespace(start=lambda label, argv, env=None: started.append((label, argv)) or child,
                                         record=lambda value: None)
            server.tick_external_maps()
            self.assertEqual([label for label, _ in started], ['external-map-delink-7'])
            self.assertEqual(started[0][1][-2:], ['-delink', '7'])
            server.external_maps_next = 0
            server.tick_external_maps()          # query still running: nothing new is started
            self.assertEqual(len(started), 1)
            child.process.poll = lambda: 0
            child.reader.is_alive = lambda: False
            server.external_maps_next = 0
            server.tick_external_maps()
            self.assertEqual([label for label, _ in started], ['external-map-delink-7', 'external-map-delink-8'])
            report = server.creation_report['external_maps']['supervisor']
            self.assertEqual(report['counts']['delink_finished'], 1)
            self.assertTrue(report['requests'][0]['delink']['passed'])


if __name__ == '__main__':
    unittest.main()
