from pathlib import Path
import io
import json
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app')]
import mapserver_phases

# Shape copied from the 0.13.44 Thor Atlas console (session id replaced).
CONSOLE = """started 2026-10-28 19:41:29
ARMPORT_TRUSTED_BINS_V1 status=trusted ordinal=1 bin=bin/seqstatebits.bin
ARMPORT_TRUSTED_BINS_V1 status=trusted ordinal=2 bin=server/bin/mapsspec.bin
ARMPORT_SERVER_STARTUP_V1 status=ok map_id=1 pid=556 sequence=6 phase=sequencer_info_done elapsed_ms=96000.000 phase_ms=93930.000 scope=main_entry_to_checkpoint
Caching directory tree and misc startup...                            (0.17)
more miscellany..[2026-10-28 19:41:30.441] [DEBUG] \tParsing .statebits from seqstatebits.bin
done                                                 (1.54)
[2026-10-28 19:41:31.287] [DEBUG] \tsequencers
COH_ANIM_CERT_V1 schema=1 pack=00 opened=1024 certified=1024 fallback=0
COH_ANIM_CERT_V1 schema=1 pack=00 opened=5120 certified=5120 fallback=0
Caching relevant folders.. [2026-10-28 19:43:05.214] [DEBUG] Caching relevant folders
done                                       (11.37)
Loading story arcs.. [2026-10-28 19:44:41.615] [DEBUG] \tParsing .sc from SouvenirClues.bin
470 arcs, 957 contacts, 3528 tasks               (53.58)
loading map: maps/City_Zones/City_01_01/City_01_01.txt..[2026-10-28 19:46:30.507] [DEBUG] \tSet folder cache callback for scenes/*.txt
done          (47.67)
Loading Costume...[2026-10-28 19:46:31.000] [DEBUG] \tParsing costume.ctm from costume.bin
                                                    (0.73)
Starting novodex...[2026-10-28 19:46:42.488] [DEBUG] Loading PhysX objects
[2026-10-28 19:47:01.276] [INFO] Created 2311 PhysX objects
success                                            (18.84)
Verifying SG permission tables.. done                                 (0.00)
ARMPORT_SERVER_STARTUP_V1 status=ok map_id=1 pid=556 sequence=14 phase=ready_published elapsed_ms=330120.500 phase_ms=0.250 scope=main_entry_to_checkpoint
ARMPORT_SERVER_STARTUP_V1 status=ok map_id=1 pid=556 sequence=15 phase=main_loop_begin elapsed_ms=330200.000 phase_ms=79.500 scope=main_entry_to_checkpoint
[2026-10-28 19:50:36.000] [DEBUG] \tReading player.txt from 623e484ce0c9459aa725b497fad0329a
"""


class MapServerPhaseTests(unittest.TestCase):
    def test_self_timed_labels_use_the_phase_opener(self):
        result = mapserver_phases.summary(CONSOLE)
        timed = dict(result['slowest_self_timed'])
        self.assertEqual(timed['Loading story arcs'], 53.58)
        self.assertEqual(timed['loading map: maps/City_Zones/City_01_01/City_01_01.txt'], 47.67)
        self.assertEqual(timed['Starting novodex'], 18.84)
        self.assertEqual(timed['more miscellany'], 1.54)
        self.assertEqual(timed['Loading Costume'], 0.73)
        self.assertEqual(timed['Caching directory tree and misc startup'], 0.17)
        self.assertEqual(result['slowest_self_timed'][0][0], 'Loading story arcs')
        self.assertEqual(result['animation_files_opened'], 5120)
        self.assertEqual(result['trusted_bins_reported'], 2)

    def test_untimed_animation_gap_is_reported_and_post_ready_waits_are_not(self):
        result = mapserver_phases.summary(CONSOLE)
        gap = [row for row in result['slowest_untimed_gaps'] if 'sequencers' in row[1]][0]
        self.assertEqual(gap[0], 93.93)
        self.assertIn('Caching relevant folders', gap[2])
        self.assertEqual([row[0] for row in result['slowest_untimed_gaps']],
                         sorted((row[0] for row in result['slowest_untimed_gaps']), reverse=True))
        # Startup ends at the permission check; the later client wait is excluded.
        self.assertEqual(result['stamped_span_seconds'], 330.84)
        self.assertNotIn('623e484ce0c9459aa725b497fad0329a', json.dumps(result))

    def test_native_checkpoints_are_read_even_after_ready(self):
        checkpoints = mapserver_phases.summary(CONSOLE)['native_checkpoint_seconds']
        self.assertEqual(checkpoints['sequencer_info_done'], 93.93)
        self.assertEqual(checkpoints['main_loop_begin'], 0.08)
        self.assertEqual(checkpoints['elapsed_to_main_loop'], 330.2)
        self.assertIsNone(mapserver_phases.summary('x\n')['native_checkpoint_seconds'])

    def test_bounded_on_empty_or_unstamped_text(self):
        result = mapserver_phases.summary('no timing here\n')
        self.assertIsNone(result['stamped_span_seconds'])
        self.assertEqual(result['slowest_self_timed'], [])
        self.assertEqual(result['slowest_untimed_gaps'], [])

    def test_guest_timing_summary_reads_the_atlas_console_from_report_zip(self):
        sys.path[:0] = [str(ROOT / 'armport/app')]
        import interactive_host
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            stages = [{'stage': 'guest_start', 'started_utc': '2026-11-03T08:00:00+00:00',
                       'finished_utc': '2026-11-03T08:00:30.5+00:00'},
                      {'stage': 'client_login', 'started_utc': '2026-11-03T08:01:00+00:00'},
                      {'stage': 'bad', 'started_utc': 'not a time'}]
            (evidence / 'latest-report.json').write_text(json.dumps({'proot_mode': {'format': 1}, 'stages': stages,
                'character_creation': {'prepared_server_caches': {'status': 'skipped_native_fallback',
                    'reason': 'x' * 400, 'installed_files': 0, 'archive': {'bytes': 1}}}}))
            with zipfile.ZipFile(evidence / 'report.zip', 'w') as archive:
                archive.writestr('client-evidence/character-atlas-console.txt', CONSOLE)
                archive.writestr('client-evidence/client-console.log',
                    'noise\nARMPORT_FOLDER_CACHE_V1 phase=scan files=212496 folders=9000 seconds=142.000\n')
            result = interactive_host.guest_timing_summary(evidence)
        self.assertEqual(result['stage_timeline'], [['guest_start', 0.0, 30.5], ['client_login', 60.0, None]])
        self.assertEqual(result['client_folder_cache'], ['phase=scan files=212496 folders=9000 seconds=142.000'])
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            with zipfile.ZipFile(evidence / 'report.zip', 'w') as archive:
                archive.writestr('client-evidence/client-console.log', 'no phase lines\n')
                archive.writestr('client-evidence/armport_stdio.txt',
                    'ARMPORT_FOLDER_CACHE_V1 phase=scan files=160000 folders=9000 seconds=90.000\n'
                    'ARMPORT_FOLDER_CACHE_V1 phase=skip folders=2 list=scripts.loc,server\n')
            self.assertEqual(interactive_host.guest_timing_summary(evidence)['client_folder_cache'],
                ['phase=scan files=160000 folders=9000 seconds=90.000', 'phase=skip folders=2 list=scripts.loc,server'])
        self.assertEqual(result['proot_mode'], {'format': 1})
        caches = result['character_creation']['prepared_server_caches']
        self.assertEqual((caches['status'], len(caches['reason']), caches['installed_files']),
                         ('skipped_native_fallback', 200, 0))
        self.assertNotIn('archive', caches)
        phases = result['atlas_mapserver_phases']
        self.assertIn(93.93, [row[0] for row in phases['slowest_untimed_gaps']])
        self.assertLessEqual(len(phases['slowest_self_timed']), 6)
        self.assertIsNone(result['shared_server_data'])
        self.assertEqual(result['story_arc_counts'], [[470, 957, 3528]])

    def test_serverdata_probe_and_story_arc_counts_are_reported(self):
        sys.path[:0] = [str(ROOT / 'armport/app')]
        import interactive_host
        console = CONSOLE.replace('470 arcs, 957 contacts', '0 arcs, 0 contacts', 1)
        probe = {'format': 1, 'shared_top_level': ['scripts.loc'], 'reused_shared_tree': False}
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            (evidence / 'latest-report.json').write_text(json.dumps({'character_creation': {'shared_server_data': probe}}))
            with zipfile.ZipFile(evidence / 'report.zip', 'w') as archive:
                archive.writestr('client-evidence/character-atlas-console.txt', console)
            result = interactive_host.guest_timing_summary(evidence)
        self.assertEqual(result['shared_server_data'], probe)
        self.assertEqual(result['story_arc_counts'], [[0, 0, 3528]])
        self.assertEqual(interactive_host.story_arc_counts('x\n1 arcs, 2 contacts, 3 tasks\n' * 9), [[1, 2, 3]] * 4)
        import os
        from unittest.mock import patch
        for value, expected in (('', 0), ('1', 1), ('2', 2)):
            with patch.dict(os.environ, {'COH_SERVERDATA_PROBE': value}):
                self.assertEqual(interactive_host.serverdata_probe_requested(), expected)
        with patch.dict(os.environ, {'COH_SERVERDATA_PROBE': 'on'}), self.assertRaises(Exception):
            interactive_host.serverdata_probe_requested()
        for value, expected in (('', False), ('0', False), ('1', True)):
            with patch.dict(os.environ, {'COH_SHARED_SERVER_DATA': value}):
                self.assertIs(interactive_host.shared_server_requested(), expected)

    def test_timing_notices_split_sessions_and_bin_writes_under_the_annotation_limit(self):
        sys.path[:0] = [str(ROOT / 'armport/app')]
        import interactive_host
        writes = {'1': {'files': ['data/bin/' + 'x' * 40 + str(i) + '.bin' for i in range(48)]}}
        timings = {name: {'proot_mode': {'format': 1}, 'trusted_bins': {'applied': True},
                          'character_' + ('creation' if name == 'creation' else 'reopen'): {
                              'map_startup': [], 'preparation_phase_seconds': {}, 'native_bin_writes': writes},
                          'atlas_mapserver_phases': mapserver_phases.summary(CONSOLE, top=6),
                          'stage_timeline': [['s' * 48, 1000.0, 1000.0]] * 24,
                          'client_folder_cache': ['phase=scan ' + 'x' * 140] * 8}
                   for name in ('creation', 'reopen')}
        lines = interactive_host.timing_notices(timings, True, True)
        titles = [line.split('::')[1] for line in lines]
        self.assertEqual(titles, ['notice title=ArmPort M4 guest timings creation', 'notice title=ArmPort M4 bin writes creation',
                                  'notice title=ArmPort M4 startup detail creation',
                                  'notice title=ArmPort M4 guest timings reopen', 'notice title=ArmPort M4 bin writes reopen',
                                  'notice title=ArmPort M4 startup detail reopen'])
        detail = json.loads(lines[2].split('::', 2)[2])
        self.assertEqual(len(detail['stage_timeline']), 24)
        self.assertNotIn('stage_timeline', json.loads(lines[0].split('::', 2)[2]))
        self.assertTrue(all(len(line.split('::', 2)[2]) < 4096 for line in lines))
        first = json.loads(lines[0].split('::', 2)[2])
        self.assertNotIn('native_bin_writes', first['character_creation'])
        self.assertEqual((first['session'], first['proot_seccomp'], first['trusted_bins_requested']), ('creation', True, True))
        self.assertIn('native_bin_writes', timings['creation']['character_creation'])
        self.assertEqual(interactive_host.timing_notices({'reopen': {'proot_mode': None}}, False, False)[0].count('bin writes'), 0)


if __name__ == '__main__':
    unittest.main()
