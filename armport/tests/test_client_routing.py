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
                probe.reset_client_startup_inputs()
        self.assertEqual(probe.wine_env['COH_TEXTURE_HEADER_PACK'], 'Z:\\pack')
        empty = Probe(); empty.ctx.report = {}
        with patch.object(creation, 'TextureHeaderPreparation', Worker):
            empty.start_texture_header_index()
        self.assertIsNone(empty.texture_header_preparation)

    def test_arm64_gameplay_cap_is_30_only_with_the_selected_gpu_renderer(self):
        class Probe(armport.ArmPortClient, CharacterCreationDiagnostic):
            def __init__(self, gpu):
                self.ctx = SimpleNamespace(report={} if gpu is None else {'client_gpu_profile': {'selected': gpu}})
        for gpu, fps in (('turnip', '30'), ('software', '10'), (None, '10')):
            with self.subTest(gpu=gpu):
                probe = Probe(gpu)
                env = probe.armport_gameplay_fps({'WINEDEBUG': 'x'})
                self.assertEqual((env['COH_CLIENT_GAMEPLAY_FPS'], env['WINEDEBUG']), (fps, 'x'))
                self.assertEqual(probe.ctx.report['armport_gameplay_fps']['requested_cap'], int(fps))

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
        for change in ({'tree_sha256': '6' * 64}, {'targets_sha256': '6' * 64}, {'links': 4},
                       {'archive_sha256': '6' * 64}, {'executable_sha256': '6' * 64}):
            self.assertNotEqual(identity(self.client(**change), 'scripts.loc,server'), base, change)
        self.assertNotEqual(identity(self.client(), ''), base)
        self.assertNotEqual(identity(self.client(), 'scripts.loc,server', 'geobin'), base)
        with patch.object(armport.package, 'digest', side_effect=lambda path: '7' * 64
                          if Path(path).name == 'armport_client_package.py' else armport.package.digest(path)):
            self.assertNotEqual(identity(self.client(), 'scripts.loc,server'), base)   # view code changed
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
        self.assertEqual(series[-1], '0123-armport-entity-interpolation-clock-wrap.patch')


if __name__ == '__main__':
    unittest.main()
