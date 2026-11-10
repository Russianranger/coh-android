"""Exercise real creation/reopen inheritance without starting any runtime."""
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest')]
import armport_interactive as armport
from character_creation_diagnostic import CharacterCreationDiagnostic
from character_reopen_diagnostic import CharacterReopenDiagnostic
from test_client_package import pe


class ClientRoutingTests(unittest.TestCase):
    def test_client_evidence_uses_arm64_tree_and_restores_server_root_on_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            class ExistingGuest:
                def save_evidence(self):
                    self.observed_root = self.work
                    raise RuntimeError('capture failed')
            class Selected(armport.ArmPortClient, ExistingGuest): pass
            value = Selected()
            value.work = root / 'server'
            value.armport_work = root / 'arm64'
            value.armport_work.mkdir()
            with self.assertRaisesRegex(RuntimeError, 'capture failed'):
                value.save_evidence()
            self.assertEqual(value.observed_root, value.armport_work)
            self.assertEqual(value.work, root / 'server')

    def test_server_helper_only_does_not_activate_optional_visuals(self):
        with tempfile.TemporaryDirectory() as temporary:
            _, value = self.instance(CharacterCreationDiagnostic, 'arm64')
            value.args.assets = Path(temporary)
            (value.args.assets / 'client_visual_assets.py').write_text('server dependency')
            value.prepare_client_visual_inputs()
            (value.args.assets / 'client-visual-assets.zip').write_bytes(b'incomplete')
            with self.assertRaisesRegex(armport.base.DiagnosticError, 'Incomplete client visual'):
                value.prepare_client_visual_inputs()

    def instance(self, base, architecture):
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': architecture}):
            selected = armport.select(base)
        value = selected.__new__(selected)
        value.args = SimpleNamespace(wine=Path('/opt/wine/bin/wine'), assets=Path('/assets'),
                                     session_id='a' * 32)
        value.work = Path('/state/x86-data')
        value.armport_work = Path('/state/arm64-client')
        return selected, value

    def test_default_keeps_existing_classes(self):
        with patch.dict(os.environ, {}, clear=True):
            for base in (CharacterCreationDiagnostic, CharacterReopenDiagnostic):
                self.assertIs(armport.select(base), base)

    def test_actual_create_and_reopen_commands_select_separate_arm64_tree(self):
        for base, mode in ((CharacterCreationDiagnostic, '--character-creation'),
                           (CharacterReopenDiagnostic, '--character-manual')):
            _, value = self.instance(base, 'arm64')
            command = value.launcher_command()
            self.assertEqual(command, [value.args.wine,
                armport.base.windows_path(value.armport_work / 'armport-launcher.exe'), 'a' * 32,
                armport.base.windows_path(value.armport_work / 'CityOfHeroes.exe'),
                armport.base.windows_path(value.armport_work), mode])
            self.assertNotIn('x86-data', ' '.join(map(str, command)))

    def test_x86_commands_remain_original(self):
        for base, mode in ((CharacterCreationDiagnostic, '--character-creation'),
                           (CharacterReopenDiagnostic, '--character-manual')):
            selected, value = self.instance(base, 'x86')
            self.assertIs(selected, base)
            command = value.launcher_command()
            self.assertEqual(command[1], armport.base.windows_path(value.args.assets / 'client-launcher.exe'))
            self.assertEqual(command[3], armport.base.windows_path(value.work / 'CityOfHeroes.exe'))
            self.assertEqual(command[-1], mode)

    def test_unknown_architecture_rejected_and_zoning_reopen_selected(self):
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': 'guess'}):
            with self.assertRaisesRegex(armport.base.DiagnosticError, 'Unknown graphical client architecture'):
                armport.select(CharacterCreationDiagnostic)
        class Zoning(CharacterReopenDiagnostic):
            ZONING = True
        with patch.dict(os.environ, {'COH_CLIENT_ARCH': 'arm64'}):
            selected = armport.select(Zoning)
        self.assertTrue(issubclass(selected, armport.ArmPortClient) and issubclass(selected, Zoning))

    def test_arm64_texture_index_worker_starts_and_its_environment_reaches_launch(self):
        import character_creation_diagnostic as creation
        started = []
        class Worker:
            def __init__(self, owner): self.owner = owner
            def start(self): started.append(self.owner)
        class Probe(armport.ArmPortClient, CharacterCreationDiagnostic):
            def __init__(self):
                self.ctx = SimpleNamespace(report={'import_identity': {}, 'client_worktree': {}})
                self.texture_header_preparation = None
                self.wine_env = {}
        probe = Probe()
        with patch.object(creation, 'TextureHeaderPreparation', Worker):
            probe.start_texture_header_index()
            probe.start_texture_header_index()
        self.assertEqual(started, [probe])
        def joined():
            probe.wine_env['COH_TEXTURE_HEADER_PACK'] = 'Z:\\pack'
            probe.texture_header_preparation = None
        probe.join_texture_header_preparation = joined
        with patch.object(armport.base, 'windows_path', str):
            probe.query_client_progress = lambda: ''
            probe.ctx.run = lambda *a, **k: {'output': ''}
            probe.args = SimpleNamespace(wine='wine')
            with tempfile.TemporaryDirectory() as temporary:
                probe.armport_work = Path(temporary)
                probe.root = Path(temporary)
                probe.reset_client_startup_inputs()
                # 0.13.67: the worker is joined after the GPU probes, at the launch itself
                # (Thor 0.13.66 waited 19.7 s for it and then 30.9 s for the probes).
                self.assertNotIn('COH_TEXTURE_HEADER_PACK', probe.wine_env)
                order, captured = [], {}
                probe.wine_env['COH_TEXTURE_HEADER_ID'] = 'stale'
                def probes(environment, label):
                    order.append(('gpu', probe.texture_header_preparation is not None)); return environment
                probe.armport_gpu_environment = probes
                probe.armport_gameplay_fps = lambda environment: environment
                probe.launcher_command = lambda: ['launcher']
                probe.texture_header_preparation = object()
                def joined():
                    order.append(('join', True)); probe.wine_env.pop('COH_TEXTURE_HEADER_ID', None)
                    probe.wine_env['COH_TEXTURE_HEADER_PACK'] = 'Z:\\pack'
                    probe.texture_header_preparation = None
                probe.join_texture_header_preparation = joined
                probe.ctx.start = lambda label, command, env: captured.setdefault('env', env)
                with patch.object(armport, 'LoggedClient', lambda child, log: child):
                    probe.launch_client_attempt()
                self.assertEqual(order, [('gpu', True), ('join', True)])
                self.assertEqual(captured['env']['COH_TEXTURE_HEADER_PACK'], 'Z:\\pack')
                self.assertNotIn('COH_TEXTURE_HEADER_ID', captured['env'])   # only what the join published
        self.assertEqual(probe.wine_env['COH_TEXTURE_HEADER_PACK'], 'Z:\\pack')
        empty = Probe(); empty.ctx.report = {}
        with patch.object(creation, 'TextureHeaderPreparation', Worker):
            empty.start_texture_header_index()
        self.assertIsNone(empty.texture_header_preparation)

    def test_arm64_gameplay_cap_is_30_only_with_the_selected_gpu_renderer(self):
        class Probe(armport.ArmPortClient, CharacterCreationDiagnostic):
            def __init__(self, gpu):
                self.ctx = SimpleNamespace(report={} if gpu is None else {'client_gpu_profile': {'selected': gpu}})
        # 0.13.67: the app's 60 FPS option starts the GPU renderer's gameplay at 60 (patch 0128).
        for gpu, option, fps in (('turnip', None, '30'), ('software', None, '10'), (None, None, '10'),
                                 ('turnip', '0', '30'), ('turnip', '1', '60'), ('software', '1', '10'), (None, '1', '10')):
            with self.subTest(gpu=gpu, option=option):
                probe = Probe(gpu)
                with patch.dict(os.environ, {} if option is None else {'COH_CLIENT_GAMEPLAY_60': option}):
                    if option is None:
                        os.environ.pop('COH_CLIENT_GAMEPLAY_60', None)
                    env = probe.armport_gameplay_fps({'WINEDEBUG': 'x'})
                self.assertEqual((env['COH_CLIENT_GAMEPLAY_FPS'], env['WINEDEBUG']), (fps, 'x'))
                self.assertEqual(probe.ctx.report['armport_gameplay_fps']['requested_cap'], int(fps))
        patch_text = (Path(armport.__file__).resolve().parents[1]
                      / 'patches/0128-armport-gameplay-cap-60-from-launch.patch').read_text()
        self.assertIn('strcmp(value, "60") == 0) requested = 60;', patch_text)

    def test_arm64_requests_overlap_only_from_a_server_that_supervises_it(self):
        class Server:
            pass
        class Overlap(Server):
            def client_startup_assets_allowed(self): return False
        class Existing:
            def start_wine(self): self.flag = getattr(self.local_server, 'overlap_client_initialization', None)
        class Probe(armport.ArmPortClient, Existing):
            def prepare_client_visual_inputs(self): raise StopIteration
        for server, expected in ((Server(), None), (Overlap(), True)):
            probe = Probe.__new__(Probe)
            probe.local_server = server
            with self.assertRaises(StopIteration):
                probe.start_wine()
            self.assertEqual(probe.flag, expected)

    def test_arm64_copy_includes_visuals_installed_after_server_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            assets, binary, bins, shaders = (root / name for name in ('assets', 'binary', 'bins', 'shaders'))
            for path in (assets, binary, bins, shaders): path.mkdir()
            for name in armport.package.BINARIES - {'armport-launcher.exe'}:
                (binary / name).write_bytes(pe())
            launcher = root / 'launcher.exe'
            launcher.write_bytes(pe())
            (bins / 'BodyParts.bin').write_bytes(b'arm64')
            (shaders / 'test.arb').write_bytes(b'ARB')
            armport.package.package(binary, bins, shaders, launcher,
                                    assets / armport.package.ARCHIVE, 123, 122)
            class ExistingGuest:
                def initialize(self): pass
                def start_wine(self): self.server_prepared = True
                def prepare_client_visual_inputs(self):
                    if not self.server_prepared: raise AssertionError('server not prepared')
                    (self.work / 'data/visual.texture').write_bytes(b'late visual input')
            class Selected(armport.ArmPortClient, ExistingGuest): pass
            value = Selected()
            value.root, value.work = root, root / 'x86'
            (value.work / 'data').mkdir(parents=True)
            value.args = SimpleNamespace(assets=assets, session_id='a' * 32)
            value.ctx = SimpleNamespace(report={'asset_sha256': dict.fromkeys(
                ('armport-client.zip', 'armport_client_package.py', 'armport_interactive.py', 'client_stdio.py')),
                'client_worktree': {}, 'native_responsiveness_candidate': {'x86': True}},
                stage=lambda name: None, passed=lambda **kwargs: None)
            value.initialize()
            self.assertFalse(value.armport_work.exists())
            self.assertNotIn('native_responsiveness_candidate', value.ctx.report)
            value.start_wine()
            self.assertEqual((value.armport_work / 'data/visual.texture').read_bytes(), b'late visual input')
            self.assertEqual((value.armport_work / 'data/bin/BodyParts.bin').read_bytes(), b'arm64')
            self.assertFalse(value.ctx.report['armport_client']['x86_bins_reused'])


class ClientFolderSkipTests(unittest.TestCase):
    """Patch 0120: the ARM64 client's scan skips server-only folders unless the app opts out."""
    def launch(self, value):
        captured = {}
        class Selected(armport.ArmPortClient):
            pass
        client = Selected.__new__(Selected)
        client.wine_env = {'WINEPREFIX': '/x'}
        client.armport_work = Path('/arm64')
        client.root = Path('/arm64-root-absent')
        client.launcher_command = lambda: ['launcher']
        client.armport_gpu_environment = lambda environment, label: environment
        client.armport_gameplay_fps = lambda environment: environment
        client.ctx = SimpleNamespace(start=lambda label, command, env: captured.setdefault('env', env), report={})
        with patch.dict(os.environ, {'COH_CLIENT_SKIP_SERVER_FOLDERS': value}), \
                patch.object(armport, 'LoggedClient', lambda child, log: child):
            client.launch_client_attempt()
        return captured['env']

    def test_default_and_on_skip_scripts_loc_and_server_and_off_keeps_the_full_scan(self):
        self.assertEqual(self.launch('')['ARMPORT_FOLDER_CACHE_SKIP'], 'scripts.loc,server')
        self.assertEqual(self.launch('1')['ARMPORT_FOLDER_CACHE_SKIP'], 'scripts.loc,server')
        environment = self.launch('0')
        self.assertNotIn('ARMPORT_FOLDER_CACHE_SKIP', environment)
        self.assertEqual(environment['ARMPORT_LOOSE_DATA'], '1')
        with patch.dict(os.environ, {'COH_CLIENT_SKIP_SERVER_FOLDERS': 'yes'}), self.assertRaises(Exception):
            armport.client_skips_server_folders()


class StationFpsCapFileTests(unittest.TestCase):
    """Patch 0121: the launcher names the cap file and clears a stale one."""
    def test_cap_file_is_relative_to_the_client_and_stale_caps_are_removed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            captured = {}
            client = armport.ArmPortClient.__new__(armport.ArmPortClient)
            client.wine_env = {'WINEPREFIX': '/x'}
            client.armport_work = Path(temporary)
            client.root = Path(temporary)
            (client.armport_work / armport.FPS_CAP_FILE).write_text('10\n')
            client.launcher_command = lambda: ['launcher']
            client.armport_gpu_environment = lambda environment, label: environment
            client.armport_gameplay_fps = lambda environment: environment
            client.ctx = SimpleNamespace(start=lambda label, command, env: captured.setdefault('env', env), report={})
            with patch.object(armport, 'LoggedClient', lambda child, log: child):
                client.launch_client_attempt()
            self.assertEqual(captured['env']['ARMPORT_FPS_CAP_FILE'], 'armport-fps-cap.txt')
            # Patch 0123: the interpolation clock is logged for device exports.
            self.assertEqual(captured['env']['ARMPORT_NET_CLOCK_LOG'], '1')
            self.assertEqual(client.armport_fps_cap_file, Path(temporary) / 'armport-fps-cap.txt')
            self.assertFalse(client.armport_fps_cap_file.exists())
        series = (Path(armport.__file__).resolve().parents[1] / 'patches/series').read_text().split()
        self.assertIn('0121-armport-station-fps-cap-file.patch', series)


class ClientAudioTests(unittest.TestCase):
    """0.13.53: Wine's ALSA driver plays through the overlay's plugin to the app bridge."""
    def client(self, root):
        client = armport.ArmPortClient.__new__(armport.ArmPortClient)
        client.armport_work = root / 'work'
        (client.armport_work / 'armport-audio').mkdir(parents=True)
        client.ctx = SimpleNamespace(report={})
        return client

    def test_environment_needs_the_listening_bridge_and_the_plugin(self):
        import socket
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            client = self.client(root)
            system = root / 'alsa.conf'
            system.write_text('# system\n')
            path = root / 'audio.sock'
            base = {'WINEDLLOVERRIDES': 'mscoree=;winedbg.exe='}
            with patch.object(armport, 'ALSA_SYSTEM_CONFIG', system):
                with patch.dict(os.environ, {'COH_CLIENT_AUDIO': '0'}):
                    self.assertEqual(client.client_audio_environment(base), {})
                self.assertEqual(client.ctx.report['client_audio'], {'format': 1, 'requested': False, 'enabled': False})
                request = {'COH_CLIENT_AUDIO': '1', 'COH_CLIENT_AUDIO_SOCKET': str(path)}
                with patch.dict(os.environ, request):
                    # No listener yet: the client starts without audio and says why.
                    self.assertEqual(client.client_audio_environment(base), {})
                    self.assertIn('FileNotFoundError', client.ctx.report['client_audio']['error'])
                    with socket.socket(socket.AF_UNIX) as server:
                        server.bind(str(path))
                        self.assertEqual(client.client_audio_environment(base), {})
                        self.assertIn('no audio plugin', client.ctx.report['client_audio']['error'])
                        plugin = client.armport_work / armport.package.AUDIO_PLUGIN
                        plugin.write_bytes(b'\x7fELF')
                        environment = client.client_audio_environment(base)
                record = client.ctx.report['client_audio']
                self.assertTrue(record['enabled'])
                self.assertEqual(environment['TRASC_AUDIO_SOCKET'], str(path))
                self.assertEqual(environment['WINEDLLOVERRIDES'], 'mscoree=;winedbg.exe=;winepulse.drv=d')
                config = Path(environment['ALSA_CONFIG_PATH']).read_text()
                self.assertTrue(config.startswith('<' + str(system) + '>\n'))
                self.assertIn('pcm_type.trasc { lib "' + str(plugin) + '" }', config)
                self.assertIn('pcm.!default { type plug slave { pcm "trasc" format S16_LE rate 48000 channels 2 } }', config)
        with patch.dict(os.environ, {'COH_CLIENT_AUDIO': 'yes'}), self.assertRaises(Exception):
            armport.client_audio_requested()

    def test_boot_tone_probe_uses_the_client_settings_and_needs_sound_on_both_channels(self):
        """CI has no sound files: a DirectSound tone proves the Wine, ALSA and plugin path."""
        import runtime_host
        import runtime_guest
        with patch.object(armport, 'ALSA_SYSTEM_CONFIG', Path('/usr/share/alsa/alsa.conf')):
            self.assertEqual(runtime_host.probe_alsa_config(),
                             armport.alsa_config(Path(runtime_host.GUEST_AUDIO_PLUGIN)))
        self.assertEqual(runtime_host.GUEST_AUDIO_PLUGIN, '/opt/armport-client/' + armport.package.AUDIO_PLUGIN)
        java = next((ROOT / 'android/interactive').rglob('ClientAudio.java')).read_text()
        self.assertIn('GUEST_SOCKET = "' + str(runtime_guest.AUDIO_SOCKET) + '"', java)
        tone = {'frames': 72000, 'nonzero_samples': 143000, 'left_nonzero': 71500, 'right_nonzero': 71500}
        accepted = runtime_host.probe_summary({'streams': [tone], 'errors': []})
        self.assertTrue(accepted['passed'])
        self.assertEqual((accepted['streams'], accepted['left_nonzero']), (1, 71500))
        for snapshot in ({'streams': [dict(tone, nonzero_samples=0, left_nonzero=0, right_nonzero=0)], 'errors': []},
                         {'streams': [dict(tone, right_nonzero=0)], 'errors': []},
                         {'streams': [tone], 'errors': ['unknown command']},
                         {'streams': [], 'errors': []}):
            self.assertFalse(runtime_host.probe_summary(snapshot)['passed'], snapshot)


class ClientFolderIndexTests(unittest.TestCase):
    """Patch 0122: the saved file list is keyed by the verified data view and the overlay."""
    def tree(self, root):
        source = root / 'source'
        for name in ('maps/City', 'texts'):
            (source / name).mkdir(parents=True)
        (source / 'texts/a.ms').write_text('a')
        imports = root / 'imports'; imports.mkdir()
        (imports / 'geo.txt').write_text('g')
        (source / 'maps/City/geo.txt').symlink_to(imports / 'geo.txt')
        return source

    def test_link_validation_reports_the_same_digests_whether_it_checks_or_reuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); source = self.tree(root); receipt = root / 'receipt.json'
            first = armport.package.merge_links(source, root / 'view-1', receipt)['validation']
            second = armport.package.merge_links(source, root / 'view-2', receipt)['validation']
            self.assertEqual((first['mode'], second['mode']), ('complete_link_check', 'unchanged_directory_receipt'))
            for key in ('tree_sha256', 'targets_sha256', 'links'):
                self.assertEqual(first[key], second[key])
            (root / 'imports/new.txt').write_text('n')          # a link target directory changed
            third = armport.package.merge_links(source, root / 'view-3', receipt)['validation']
            self.assertNotEqual(third['targets_sha256'], first['targets_sha256'])
            (source / 'texts/b.ms').write_text('b')               # a source directory changed
            fourth = armport.package.merge_links(source, root / 'view-4', receipt)['validation']
            self.assertNotEqual(fourth['tree_sha256'], third['tree_sha256'])

    def client(self, **changes):
        validation = {'tree_sha256': '1' * 64, 'targets_sha256': '2' * 64, 'links': 3}
        value = {'data_validation': validation, 'archive_sha256': '4' * 64, 'executable_sha256': '5' * 64}
        for key, item in changes.items():
            (validation if key in validation else value)[key] = item
        return value

    def test_identity_changes_with_every_input_and_needs_every_digest(self):
        identity = armport.package.folder_cache_identity
        base = identity(self.client(), 'scripts.loc,server')
        self.assertRegex(base, '^[0-9a-f]{64}$')
        self.assertEqual(identity(self.client(), 'scripts.loc,server'), base)
        for change in ({'tree_sha256': '6' * 64}, {'targets_sha256': '6' * 64}, {'links': 4}):
            self.assertNotEqual(identity(self.client(**change), 'scripts.loc,server'), base, change)
        self.assertNotEqual(identity(self.client(), ''), base)
        self.assertNotEqual(identity(self.client(), 'scripts.loc,server', 'geobin'), base)
        # Thor 0.13.66: a new client build (every APK) must keep the list: the archive's only
        # data is bin/, which the client scans live.
        for change in ({'archive_sha256': '6' * 64}, {'executable_sha256': '6' * 64}):
            self.assertEqual(identity(self.client(**change), 'scripts.loc,server'), base, change)
        self.assertTrue(all(armport.package.allowed(name) == expected for name, expected in
                            (('data/bin/powers.bin', True), ('data/texts/a.ms', False), ('data/bin/sub/a.bin', False))))
        with patch.object(armport.package, 'VIEW_LAYOUT', armport.package.VIEW_LAYOUT + 1):
            self.assertNotEqual(identity(self.client(), 'scripts.loc,server'), base)   # the view's layout changed
        with self.assertRaises(ValueError):
            identity(self.client(tree_sha256=None), '')

    def environment(self, value, report, root):
        client = armport.ArmPortClient.__new__(armport.ArmPortClient)
        client.root = root
        client.ctx = SimpleNamespace(report=report)
        with patch.dict(os.environ, {'COH_CLIENT_FOLDER_INDEX': value}):
            return client.client_folder_index_environment('scripts.loc,server')

    def test_launch_names_the_index_and_identity_unless_turned_off(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = {'armport_client': self.client()}
            environment = self.environment('', report, root)
            self.assertEqual(environment['ARMPORT_FOLDER_CACHE_ID'],
                             armport.package.folder_cache_identity(self.client(), 'scripts.loc,server',
                                                                   'geobin,server'))
            self.assertTrue(environment['ARMPORT_FOLDER_CACHE_INDEX'].endswith('armport-folder-cache-index.bin'))
            # The writable cache roots are scanned live beside the saved list.
            self.assertEqual(environment['ARMPORT_FOLDER_CACHE_LIVE'], 'geobin,server')
            self.assertEqual(report['client_folder_index']['present_before_launch'], False)
            (root / armport.package.FOLDER_INDEX).write_bytes(b'x')
            self.assertEqual(self.environment('1', report, root).keys(), environment.keys())
            self.assertTrue(report['client_folder_index']['present_before_launch'])
            self.assertEqual(self.environment('0', report, root), {})
            self.assertFalse(report['client_folder_index']['requested'])
            # An incomplete identity scans as before and says why.
            incomplete = {'armport_client': {'archive_sha256': '4' * 64}}
            self.assertEqual(self.environment('1', incomplete, root), {})
            self.assertEqual(incomplete['client_folder_index']['error'], 'KeyError')
            (root / armport.package.FOLDER_INDEX).unlink()
            (root / armport.package.FOLDER_INDEX).symlink_to(root / 'elsewhere')
            with self.assertRaises(Exception):
                self.environment('1', report, root)
            with patch.dict(os.environ, {'COH_CLIENT_FOLDER_INDEX': 'yes'}), self.assertRaises(Exception):
                armport.client_uses_folder_index()
        series = (Path(armport.__file__).resolve().parents[1] / 'patches/series').read_text().split()
        self.assertIn('0122-armport-folder-cache-index.patch', series)
        self.assertIn('0123-armport-entity-interpolation-clock-wrap.patch', series)

    def test_sound_script_errors_are_logged_not_a_modal_dialog(self):
        """Patch 0124: with audio on, a script naming a missing sound opened a modal
        "Sound Script Errors" dialog that stopped the game's input (runtimes
        41832716509 and 41838960420: logout never processed). It is logged, bounded."""
        root = Path(armport.__file__).resolve().parents[1]
        series = (root / 'patches/series').read_text().split()
        self.assertIn('0124-armport-sound-script-errors-logged.patch', series)
        text = (root / 'patches' / '0124-armport-sound-script-errors-logged.patch').read_text()
        removed = [line for line in text.splitlines() if line.startswith('-') and not line.startswith('---')]
        added = [line for line in text.splitlines() if line.startswith('+') and not line.startswith('+++')]
        self.assertTrue(any('winErrorDialog(errorMsg,"Sound Script Errors"' in line for line in removed))
        self.assertFalse(any('winErrorDialog' in line for line in added))
        self.assertEqual(sum('sprintf(errors+strlen(errors)' in line for line in removed), 4)
        self.assertFalse(any('sprintf(errors+strlen(errors)' in line for line in added))
        self.assertTrue(any('ARMPORT_SOUND_SCRIPT_ERRORS_V1' in line for line in added))
        upstream = (root.parent / 'upstream/ouroboros/Game/src/sound/sound_ambient.c').read_text(encoding='latin-1')
        self.assertEqual(upstream.count('winErrorDialog('), 1)   # the only dialog in this file


    def test_map_loading_notice_does_not_outlive_the_load_screen(self):
        """Patch 0125: with -notwostagemapxfer the load screen comes first and the
        DbServer's "loading" notice arrives during it; nothing turned it off, so
        "Map loading, please wait..." stayed over King's Row (Thor 0.13.56)."""
        root = Path(armport.__file__).resolve().parents[1]
        series = (root / 'patches/series').read_text().split()
        self.assertIn('0125-armport-map-loading-notice-after-load-screen.patch', series)
        text = (root / 'patches' / '0125-armport-map-loading-notice-after-load-screen.patch').read_text()
        self.assertEqual(text.count('+++ b/'), 1)
        self.assertIn('+++ b/Game/src/clientcomm/clientcomm.c', text)
        added = [line for line in text.splitlines() if line.startswith('+') and not line.startswith('+++')]
        self.assertIn('+    if (on && game_state.game_mode == SHOW_LOAD_SCREEN)', added)
        self.assertIn('+    g_showMapLoadingMessage = on;', added)
        self.assertTrue(any(line.startswith('+    g_showMapLoadingMessage = false;') for line in added))
        upstream = root.parent / 'upstream/ouroboros'
        client = (upstream / 'Game/src/clientcomm/clientcomm.c').read_text(encoding='latin-1')
        self.assertEqual(client.count('g_showMapLoadingMessage = pktGetBits(pak_in, 1);'), 1)
        self.assertIn('g_showMapLoadingMessage = false;\n    game_state.game_mode = SHOW_LOAD_SCREEN;', client)
        # The DbServer only ever sends "on" (a new map starting for the player).
        dbserver = (upstream / 'DBServer/src/mapxfer.c').read_text(encoding='latin-1')
        self.assertEqual(dbserver.count('sendMapLoadingMessage(link, ent_con->is_gameclient, ent_con->id, 1);'), 2)
        self.assertNotIn('ent_con->id, 0);', dbserver)


    def test_enter_game_waits_for_the_dbserver_to_start_the_saved_zone(self):
        """Patch 0126: with the game's own travel a session prepares Atlas Park and
        a hero saved in another zone is started by the DbServer at Enter Game
        (handleChoosePlayer -> setNewMap -> startMapIfStatic), minutes on the Thor;
        the client gave up after 90 s. The test client and -notimeout are unchanged."""
        root = Path(armport.__file__).resolve().parents[1]
        series = (root / 'patches/series').read_text().split()
        self.assertIn('0126-armport-enter-game-waits-for-zone-start.patch', series)
        text = (root / 'patches' / '0126-armport-enter-game-waits-for-zone-start.patch').read_text()
        self.assertEqual(text.count('+++ b/'), 1)
        self.assertIn('+++ b/Game/src/gameComm/initClient.c', text)
        removed = [line for line in text.splitlines() if line.startswith('-') and not line.startswith('---')]
        added = [line for line in text.splitlines() if line.startswith('+') and not line.startswith('+++')]
        self.assertEqual(removed, ['-    return dbChoosePlayer( player_slot, ip, createLocation, '
                                   'control_state.notimeout?NO_TIMEOUT:90);'])
        self.assertIn('+    return dbChoosePlayer( player_slot, ip, createLocation, '
                      'control_state.notimeout?NO_TIMEOUT:900);', added)
        upstream = root.parent / 'upstream/ouroboros'
        client = (upstream / 'Game/src/gameComm/initClient.c').read_text(encoding='latin-1')
        self.assertEqual(client.count('dbChoosePlayer('), 2)       # TEST_CLIENT (240 s) and the game
        # The game client gets no loading message from the DbServer at login; it waits.
        dbserver = (upstream / 'DBServer/src/mapxfer.c').read_text(encoding='latin-1')
        self.assertIn('if (is_gameclient)\n        return;', dbserver)
        self.assertIn('ret = setNewMap(ent_con,ent_con->map_id,link,1,errmsg,client->char_id != 0);',
                      (upstream / 'DBServer/src/clientcomm.c').read_text(encoding='latin-1'))

    def test_logout_is_kept_through_the_enter_that_sent_it(self):
        """Patch 0127: the chat acts on /quittologin's Enter (WM_KEYDOWN) in one frame
        and Wine's DirectInput edge for it comes the next; at 2 FPS the server's
        logout timer is back by then and "Press any key to abort" cancelled the
        logout (r58t 42322788540 attempt 1, r59zc 42397533053: client left in the
        zone, no save). Keys pressed after the request still cancel. The native
        behaviour check is armport/tests/logout_abort_keys.py (build workflow)."""
        root = Path(armport.__file__).resolve().parents[1]
        name = '0127-armport-logout-kept-through-the-key-that-sent-it.patch'
        series = (root / 'patches/series').read_text().split()
        self.assertIn(name, series)   # 0128 (0.13.67) follows it
        text = (root / 'patches' / name).read_text()
        self.assertEqual(sorted(line[6:] for line in text.splitlines() if line.startswith('+++ b/')), [
            'Game/src/clientcomm/clientcomm.c', 'Game/src/game.c', 'Game/src/win/input.c', 'Game/src/win/input.h'])
        removed = [line for line in text.splitlines() if line.startswith('-') and not line.startswith('---')]
        added = [line for line in text.splitlines() if line.startswith('+') and not line.startswith('+++')]
        # Only the abort condition changes; the stock message, cancel packet and dialog stay.
        self.assertEqual(removed, ['-                if (inpEdge(i))'])
        self.assertIn('+                if (inpEdge(i) && !armportKeyPressedBeforeQuit(i))', added)
        self.assertIn('+    armportNoteQuitRequest(abort_quit);', added)
        self.assertIn('+        g_armport_quit_request_ms = timeGetTime();', added)
        self.assertEqual(sum(line == '+            inp_edge_times[keyIndex] = timeStamp;' for line in added), 2)
        self.assertIn('+    if (!g_armport_quit_request_ms || before < 0)', added)
        self.assertTrue(any('ARMPORT_LOGOUT_KEY_V1' in line for line in added))
        upstream = root.parent / 'upstream/ouroboros'
        game = (upstream / 'Game/src/game.c').read_text(encoding='latin-1')
        # The stock loop: any key edge during the countdown cancels the logout.
        self.assertEqual(game.count('                if (inpEdge(i))\n                {\n'
                                    '                    printf("aborted by key: %d\\n",i);\n'
                                    '                    commSendQuitGame(1);'), 1)
        self.assertLess(game.index('inpUpdate();'), game.index('windowProcessMessages();'))
        self.assertLess(game.index('windowProcessMessages();'), game.index('engine_update_net();'))
        source = (upstream / 'Game/src/win/input.c').read_text(encoding='latin-1')
        self.assertIn('inpUpdateKey(keyboardData[i].dwOfs, keyboardData[i].dwData, keyboardData[i].dwTimeStamp);',
                      source)
        self.assertEqual(source.count('            inp_edges[keyIndex] = 1;\n'), 2)
        comm = (upstream / 'Game/src/clientcomm/clientcomm.c').read_text(encoding='latin-1')
        self.assertIn('pktSendBitsPack(pak,1,abort_quit);    // 0 means do it, 1 means abort from disconnect', comm)
        self.assertIn('timeGetTime()', comm)
        workflow = (root.parent / '.github/workflows/armport-build.yml').read_text()
        self.assertIn('python3 armport/tests/logout_abort_keys.py --source "$RUNNER_TEMP/armport/src" '
                      '--original upstream/ouroboros', workflow)
        self.assertIn("FAIL: the Enter that sent /quittologin cancelled the logout",
                      (root / 'tests/logout_abort_keys.py').read_text())


if __name__ == '__main__':
    unittest.main()
