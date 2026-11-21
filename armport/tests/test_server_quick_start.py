"""0.13.74: the zone servers' config file with two of the game's own developer switches.

Thor 0.13.73, launch B (20261118-170550): a zone server took 148 s to start; attaching every
animation of every sequencer was 64.6 s of it (CI run 44144475202: 39.7 of 92.8 s).
`quickLoadAnims 1` attaches an animation when an entity first uses it, and
`nofilechangecheck_server 1` stops the look-ups of source files' dates.
"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import local_character_server as server
import interactive_host as host

UPSTREAM = ROOT / 'upstream/ouroboros'


class QuickStart(unittest.TestCase):
    def test_not_requested_adds_nothing_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            for value in ({}, {'COH_SERVER_QUICK_START': '0'}, {'COH_SERVER_QUICK_START': ''}):
                with mock.patch.dict(os.environ, value, clear=True):
                    self.assertEqual(server.mapserver_quick_start_arguments(directory), [])
                    self.assertEqual(server.server_quick_start_record()['requested'], False)
                    self.assertEqual(server.server_quick_start_record()['commands'], [])
            self.assertEqual(os.listdir(directory), [])

    def test_requested_writes_the_config_once_and_names_it_as_a_windows_path(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.dict(os.environ, {'COH_SERVER_QUICK_START': '1'}):
            folder = Path(directory).resolve()
            arguments = server.mapserver_quick_start_arguments(folder)
            path = folder / 'armport-svrconfig.txt'
            self.assertEqual(arguments, ['-svrconfig', 'Z:' + str(path).replace('/', '\\')])
            self.assertEqual(path.read_bytes(), b'nofilechangecheck_server 1\nquickLoadAnims 1\n')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            before = path.stat().st_mtime_ns
            self.assertEqual(server.mapserver_quick_start_arguments(folder), arguments)
            self.assertEqual(path.stat().st_mtime_ns, before)       # unchanged content is not rewritten
            path.write_text('something else\n')
            server.mapserver_quick_start_arguments(folder)
            self.assertEqual(path.read_bytes(), b'nofilechangecheck_server 1\nquickLoadAnims 1\n')
            self.assertEqual(sorted(os.listdir(folder)), ['armport-svrconfig.txt'])
            record = server.server_quick_start_record()
            self.assertEqual((record['requested'], record['commands']),
                             (True, ['nofilechangecheck_server 1', 'quickLoadAnims 1']))

    def test_never_with_the_shared_memory_experiment(self):
        # The first-use attach is skipped for sequencers in shared memory (seqsequence.c:
        # !isSharedMemory), so skipping the start-up attach there would leave moves without one.
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.dict(os.environ, {'COH_SERVER_QUICK_START': '1', 'COH_SHARED_HEAP': '1'}):
            self.assertEqual(server.mapserver_quick_start_arguments(directory), [])
            self.assertEqual(server.mapserver_memory_arguments(), [])
            record = server.server_quick_start_record()
            self.assertEqual((record['requested'], record['refused_with_shared_memory']), (False, True))
            self.assertEqual(os.listdir(directory), [])
        sequence = (UPSTREAM / 'Common/seq/seqsequence.c')
        if sequence.is_file():
            self.assertEqual(sequence.read_text(errors='replace').count('isDevelopmentMode() && !isSharedMemory(anim->typeGfx)'), 3)
        producer = (ROOT / 'armport/scripts/server_metrics_producer.py').read_text()
        self.assertIn("'--config', 'OptDebug'", producer)      # not FINAL: development mode exists

    def test_a_link_or_an_unusable_path_is_refused(self):
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.dict(os.environ, {'COH_SERVER_QUICK_START': '1'}):
            folder = Path(directory).resolve()
            (folder / 'armport-svrconfig.txt').symlink_to(folder / 'elsewhere')
            with self.assertRaises(Exception):
                server.mapserver_quick_start_arguments(folder)
            spaced = folder / 'with space'
            spaced.mkdir()
            with self.assertRaises(Exception):
                server.mapserver_quick_start_arguments(spaced)

    def test_every_map_server_start_passes_it(self):
        base = (ROOT / 'android/guest/local_character_server.py').read_text()
        zoning = (ROOT / 'android/guest/character_zoning.py').read_text()
        self.assertEqual(base.count('*mapserver_quick_start_arguments(self.runtime)'), 1)             # Atlas
        self.assertEqual(zoning.count('*character.mapserver_quick_start_arguments(self.runtime)'), 2)  # zones, spare
        # Beside the three places that already take the session's own options.
        self.assertEqual((base + zoning).count('*self.session_map_options()'), 3)

    @unittest.skipUnless((UPSTREAM / 'MapServer/src/cmdparse/cmdserver.c').is_file(), 'needs the upstream source')
    def test_the_server_source_has_the_switches_and_reads_the_file_before_the_sequencers(self):
        commands = (UPSTREAM / 'MapServer/src/cmdparse/cmdserver.c').read_text(errors='replace')
        self.assertIn('{ 9, "quickLoadAnims",  0, {{ CMDINT(server_state.quickLoadAnims) }}', commands)
        self.assertIn('{ 9, "nofilechangecheck_server",  0, {{ CMDINT(global_state.no_file_change_check) }}', commands)
        self.assertIn('file = fileOpen(config_file, "rt");', commands)
        start = (UPSTREAM / 'MapServer/src/svr/svr_init.c').read_text(errors='replace')
        self.assertIn('svr_config = argv[++i];', start)
        self.assertLess(start.index('serverStateInit(argc,argv);'), start.index('seqPreloadSeqInfos(); // Must be *before* groupLoadMap'))
        load = (UPSTREAM / 'Common/seq/seqload.c').read_text(errors='replace')
        self.assertIn('if( !STATE_STRUCT.quickLoadAnims )', load)
        # Every reader of a move's last frame attaches the animation first when the switch is on.
        sequence = (UPSTREAM / 'Common/seq/seqsequence.c').read_text(errors='replace')
        self.assertEqual(sequence.count('STATE_STRUCT.quickLoadAnims &&'), 3)
        self.assertEqual(sequence.count('->animP[0]->lastFrame'), 3)
        # Development mode is "no ./piggs/texts.pigg"; the animation pack has another name.
        self.assertIn('stat("./piggs/texts.pigg", &statbuf)', (UPSTREAM / 'libs/UtilitiesLib/src/utils/file.c').read_text(errors='replace'))
        sys.path.insert(0, str(ROOT / 'android/guest'))
        import server_animation_package
        self.assertNotEqual(server_animation_package.PIGG, 'texts.pigg')


class Host(unittest.TestCase):
    def test_ci_sessions(self):
        with mock.patch.object(host, 'stock_travel_requested', return_value=True):
            self.assertEqual(host.start_options_sessions(), ('creation', 'reopen'))
        with mock.patch.object(host, 'stock_travel_requested', return_value=False):
            self.assertEqual(host.start_options_sessions(), ('reopen',))    # creation stays the comparison
        self.assertEqual(host.START_OPTIONS, ('COH_SERVER_QUICK_START=1', 'COH_WINESERVER_PATH_CACHE=1'))
        source = (ROOT / 'armport/app/interactive_host.py').read_text()
        self.assertIn("if 'creation' in start_options_sessions():", source)
        self.assertIn("if 'reopen' in start_options_sessions():", source)

    def test_log_line(self):
        report = {'character_zoning': {'server_quick_start': {'requested': True, 'commands': [
                      'nofilechangecheck_server 1', 'quickLoadAnims 1']}},
                  'wineserver_path_cache': {'requested': True, 'installed': True, 'reason': None, 'servers': 1,
                                            'sha256': 'f' * 64, 'counters': {'calls': 9, 'fast': 8}}}
        line = host.start_options_line(report, 'reopen')
        self.assertTrue(line.startswith('START_OPTIONS_V1 {'))
        import json
        value = json.loads(line.split(' ', 1)[1])
        self.assertEqual(value['server_quick_start'], {'requested': True, 'commands': [
            'nofilechangecheck_server 1', 'quickLoadAnims 1']})
        self.assertEqual(value['wineserver_path_cache'], {'requested': True, 'installed': True, 'reason': None,
                                                          'error_type': None, 'servers': 1,
                                                          'counters': {'calls': 9, 'fast': 8}})
        empty = json.loads(host.start_options_line({}, 'creation').split(' ', 1)[1])
        self.assertEqual((empty['server_quick_start'], empty['wineserver_path_cache']), (None, None))
        self.assertTrue(host.start_options_line(None, 'creation').startswith('START_OPTIONS_V1 '))

    def test_app_option(self):
        java = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
        runtime = (java / 'ClientRuntime.java').read_text()
        self.assertIn('.getBoolean("server-quick-start", true)', runtime)
        self.assertIn('"COH_SERVER_QUICK_START="+(serverQuickStartRequested?"1":"0")', runtime)
        self.assertIn('.put("server_quick_start_requested", serverQuickStartRequested)', runtime)
        self.assertIn('ClientRuntime.setServerQuickStartEnabled(this,checked)', (java / 'ClientActivity.java').read_text())


if __name__ == '__main__':
    unittest.main()
