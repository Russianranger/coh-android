"""Saved-Kings critical-path preparation; native gameplay remains a device gate.

Production private-tree, dependency, cache and log methods execute against a
small owned fixture. Only binary/package producer boundaries are controlled.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import local_character_server as server
import character_server_data_cache as cache
import character_creation_diagnostic as creation
import character_zoning as zoning
import test_character_map_data as mirror_fixture
import test_saved_map_startup as startup_fixture
import test_server_worktree_reuse as reuse_fixture
import test_kings_preparation_budgets as budget_fixture


class SavedMapPreparationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = reuse_fixture.ServerWorktreeReuseTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def kings_db(self, sequence=1):
        value = self.fixture.make(sequence)
        value.initial_map_preparation = Mock(return_value=5)
        with patch.object(server.login.LocalLoginServer, 'prepare_runtime',
                          lambda actual: self.fixture.base_prepare(actual)):
            value.prepare_runtime()
        return value

    def copy_native(self, target):
        shutil.copyfile(self.fixture.map_dir / 'MapServer.exe', target / 'MapServer.exe')
        return {'MapServer.exe': {'source': 'controlled_qualified_fixture'}}

    def test_saved_kings_db_keeps_schema_and_native_without_atlas_mirror_or_graph(self):
        value = self.fixture.make(1)
        value.initial_map_preparation = Mock(return_value=5)
        with patch.object(server.login.LocalLoginServer, 'prepare_runtime',
                          lambda actual: self.fixture.base_prepare(actual)), \
                patch.object(value, 'stage_map_data', side_effect=AssertionError('unnecessary Atlas mirror')), \
                patch.object(server.server_cache_package, 'install', side_effect=AssertionError('Atlas BIN install')), \
                patch.object(server.server_fx_catalog, 'install', side_effect=AssertionError('Atlas FX install')), \
                patch.object(server.server_data_cache.ServerDataCache, 'checkout',
                             side_effect=AssertionError('Atlas checkout')):
            value.prepare_runtime()
        value.initial_map_preparation.assert_called_once()
        self.assertFalse(hasattr(value, 'data_cache'))
        self.assertTrue(value.atlas_preparation_deferred)
        self.assertEqual((value.runtime / 'MapServer.exe').read_bytes(), b'qualified binary')
        for name in self.fixture.schema_files:
            self.assertEqual((value.runtime / name).read_bytes(), (self.fixture.schema_dir / name).read_bytes())
        self.assertFalse((value.runtime / 'data/maps').exists())
        self.assertEqual(value.creation_report['atlas_preparation_deferred']['map_id'], 5)
        self.assertNotIn('1', value.creation_report.get('map_startup_observation', {}))
        self.assertEqual(value.server_data_identity['source_data'], str(self.fixture.data))

    def test_saved_atlas_uses_minimal_db_and_same_closed_cache_as_prior_return_trip(self):
        # First build the actual deferred Atlas generation used by Kings→Atlas.
        previous = self.kings_db()
        previous_config = previous.runtime / 'data/server/db/servers.cfg'
        previous_config.write_text('current connection')
        previous.config = previous_config
        with patch.object(previous, 'copy_kings_native_dependencies', side_effect=self.copy_native):
            previous.prepare_atlas_runtime()
        previous.owner.cleanup_status = {'wine_prefix_stopped': True, 'owned_processes_reaped': True}
        previous.cleanup_config()
        saved = self.fixture.make(2)
        saved.requires_saved_character = True
        saved.overlap_client_initialization = True
        saved.initial_map_preparation = Mock(return_value=1)
        with patch.object(server.login.LocalLoginServer, 'prepare_runtime',
                          lambda actual: self.fixture.base_prepare(actual)), \
                patch.object(saved, 'stage_map_data', side_effect=AssertionError('duplicate Atlas mirror')):
            saved.prepare_runtime()
            self.assertTrue(saved.atlas_preparation_deferred)
            self.assertFalse((saved.runtime / 'data/maps').exists())
            config = saved.runtime / 'data/server/db/servers.cfg'
            config.write_text('new owned connection')
            original = {name: ((saved.runtime / name).stat().st_ino, (saved.runtime / name).read_bytes())
                        for name in self.fixture.schema_files}
            with patch.object(saved, 'copy_kings_native_dependencies', side_effect=self.copy_native):
                atlas = saved.prepare_atlas_runtime()
        self.assertTrue(saved.creation_report['private_map_data']['server_data_cache']['reused'])
        self.assertEqual(saved.data_cache.identity, previous.data_cache.identity)
        self.assertNotEqual(atlas, saved.runtime)
        self.assertEqual((atlas / 'data/server/db/servers.cfg').read_text(), 'new owned connection')
        for name, expected in original.items():
            self.assertEqual(((saved.runtime / name).stat().st_ino, (saved.runtime / name).read_bytes()), expected)
        self.assertFalse(hasattr(saved, 'kings_row_runtime'))
        self.assertEqual(saved.creation_report['atlas_preparation_deferred']['map_id'], 1)

    def test_saved_atlas_retains_complete_original_preparation(self):
        value = self.fixture.make(1)
        with patch.object(value, 'stage_map_data', wraps=value.stage_map_data) as mirror:
            report = self.fixture.prepare(value)
        mirror.assert_called_once()
        self.assertFalse(getattr(value, 'atlas_preparation_deferred', False))
        self.assertTrue((value.runtime / 'data/maps/Atlas/a.txt').is_file())
        self.assertGreater(report['linked_immutable_files'], 0)
        self.assertIs(value.prepare_atlas_runtime(), value.runtime)

    def test_deferred_atlas_is_separate_and_preserves_live_db_schema_and_credentials(self):
        value = self.kings_db()
        config = value.runtime / 'data/server/db/servers.cfg'
        config.write_text('current owned Db connection; Password=private')
        before = {name: ((value.runtime / name).stat().st_ino, (value.runtime / name).read_bytes())
                  for name in self.fixture.schema_files}
        with patch.object(value, 'copy_kings_native_dependencies', side_effect=self.copy_native), \
                patch.object(value, 'stage_map_data', wraps=value.stage_map_data) as mirror:
            target = value.prepare_atlas_runtime()
            self.assertEqual(value.prepare_atlas_runtime(), target)
        self.assertNotEqual(target, value.runtime)
        mirror.assert_called_once()
        self.assertTrue((target / 'data/maps/Atlas/a.txt').is_file())
        self.assertEqual((target / 'data/server/db/servers.cfg').read_bytes(), config.read_bytes())
        self.assertNotEqual((target / 'data/server/db/servers.cfg').stat().st_ino, config.stat().st_ino)
        for name, expected in before.items():
            self.assertEqual(((value.runtime / name).stat().st_ino, (value.runtime / name).read_bytes()), expected)
        self.assertTrue(value.creation_report['atlas_preparation_deferred']['completed_on_demand'])
        self.assertEqual(value.creation_report['map_startup_observation']['1']['runtime'], target.name)
        self.assertFalse(value.creation_report['map_startup_observation']['1']['launched'])

    def test_incomplete_deferred_atlas_cannot_be_reused_or_returned_without_cleanup(self):
        value = self.kings_db()
        with patch.object(value, 'copy_kings_native_dependencies', side_effect=self.copy_native), \
                patch.object(value, 'prepare_atlas_data', side_effect=server.base.DiagnosticError('missing graph')):
            with self.assertRaisesRegex(server.base.DiagnosticError, 'missing graph'):
                value.prepare_atlas_runtime()
        self.assertTrue(value.atlas_map_runtime.is_dir())
        with self.assertRaisesRegex(server.base.DiagnosticError, 'did not complete'):
            value.prepare_atlas_runtime()
        self.assertFalse(value.creation_report['atlas_preparation_deferred']['atlas_graph_prepared'])

    def test_deferred_atlas_cache_return_uses_its_owned_runtime(self):
        value = self.kings_db()
        config = value.runtime / 'data/server/db/servers.cfg'; config.write_text('Password=secret')
        value.config = config
        with patch.object(value, 'copy_kings_native_dependencies', side_effect=self.copy_native):
            target = value.prepare_atlas_runtime()
        value.owner.cleanup_status = {'wine_prefix_stopped': False, 'owned_processes_reaped': False}
        with self.assertRaises(server.base.DiagnosticError):
            value.cleanup_config()
        self.assertEqual(value.data_cache.record['status'], 'checked_out')
        self.assertTrue((target / 'data').is_dir())
        value.owner.cleanup_status = {'wine_prefix_stopped': True, 'owned_processes_reaped': True}
        value.cleanup_config()
        self.assertFalse((target / 'data').exists())
        self.assertEqual(value.data_cache.record['status'], 'closed')
        self.assertFalse((value.data_cache.path / 'data/server/db/servers.cfg').exists())

    def test_full_saved_identity_selects_map_before_world_preparation_and_detects_change(self):
        fixture = startup_fixture.SavedMapStartupTests()
        self.addCleanup(fixture.doCleanups)
        value = fixture.instance(5, None)
        value.qualify_monorail_preparation = Mock()
        before = copy.deepcopy((fixture.rows, fixture.saved_position))
        self.assertEqual(value.initial_map_preparation(), 5)
        self.assertEqual(value.startup_preparation_map_id, 5)
        self.assertEqual((fixture.rows, fixture.saved_position), before)
        self.assertTrue(value.creation_report['existing_character_verified'])
        value.ctx.start.assert_not_called()
        fixture.saved_position.update(staticmapid=1, mapid=None)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'destination changed'):
            value.capture_baseline()
        value.ctx.start.assert_not_called()

    def test_deferred_atlas_fx_namespace_keeps_native_and_payload_validation(self):
        assets = self.fixture.root / 'fx-assets'; assets.mkdir()
        (assets / server.server_fx_catalog.PAYLOAD).write_bytes(b'present fixture')
        allowed = self.fixture.root / ('local-login-server-' + '1' * 32 + '-atlas-park')
        with patch.object(server.server_fx_catalog, 'verify_package',
                          side_effect=ValueError('real package verification reached')) as verify:
            with self.assertRaisesRegex(ValueError, 'package verification reached'):
                server.server_fx_catalog.install(assets, allowed)
            verify.assert_called_once_with(assets)
        for suffix in ('-unknown', '-atlas-park/escape', '-atlas-park-other'):
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'server namespace'):
                server.server_fx_catalog.install(assets, self.fixture.root / ('local-login-server-' + '1' * 32 + suffix))

    def test_owned_map_logs_remain_attributed_to_map_and_unknown_roots_refused(self):
        value = self.kings_db()
        value.kings_row_runtime = value.runtime.with_name(value.runtime.name + '-kings-row')
        value.atlas_map_runtime = value.runtime.with_name(value.runtime.name + '-atlas-park')
        expected = []
        for runtime, label in ((value.runtime, ''), (value.kings_row_runtime, 'map-5/'),
                               (value.atlas_map_runtime, 'map-1/')):
            logs = runtime / 'logs'; logs.mkdir(parents=True, exist_ok=True)
            (logs / 'owned.log').write_text(label + 'only\n')
            expected.append((label + 'logs/owned.log', label + 'only\n'))
        self.assertEqual(sorted(value.current_logs()), sorted(expected))
        value.kings_row_runtime = self.fixture.root / 'unowned' / 'nested'
        with self.assertRaisesRegex(server.base.DiagnosticError, 'escaped'):
            value.server_log_paths()


class SavedMapOverlapTests(unittest.TestCase):
    selected_map = 5
    def instance(self):
        fixture = startup_fixture.SavedMapStartupTests()
        self.addCleanup(fixture.doCleanups)
        value = fixture.instance(self.selected_map, None)
        fixture.baseline(value)
        value.startup_preparation_map_id = self.selected_map
        child, kings = fixture.fake_launch(value)
        child.started = 100
        value.kings_row_runtime = kings
        value.creation_report['kings_row_beacon_graph'] = {'verified': True, 'map_id': 5}
        if self.selected_map == 1:
            value.atlas_map_runtime = value.runtime.with_name('atlas-map-runtime')
            value.atlas_map_runtime.mkdir()
            value.atlas_preparation_deferred = True
            value.atlas_runtime_prepared = True
            value.prepare_atlas_runtime = Mock(return_value=value.atlas_map_runtime)
            value.creation_report['atlas_beacon_graph'] = {'status': 'reused_verified_graph',
                'map': 'maps/city_zones/city_01_01/city_01_01.txt'}
        value.overlap_client_initialization = True
        value.ctx.report['stages'] = [{'stage': 'local_atlas_startup', 'started_utc': 'fixture'}]
        value.query = Mock(side_effect=[startup_fixture.status(self.selected_map, False), startup_fixture.status(self.selected_map)])
        with patch.object(zoning.time, 'monotonic', return_value=100), \
                patch.object(zoning.character.game, 'check_game_port'):
            value.start_map()
        return fixture, value, child

    def test_owned_map_and_client_preparation_overlap_before_readiness_but_do_not_admit_input(self):
        fixture, value, child = self.instance()
        self.assertEqual(len(value.maps), 1)
        value.ctx.start.assert_called_once()
        self.assertEqual(value.query.call_count, 1)
        self.assertFalse(value.creation_report['map_ready'])
        self.assertFalse(value.zoning_report['saved_startup']['native_ready_verified'])
        self.assertTrue(value.client_startup_assets_allowed())
        self.assertIs(value.map_process, child)
        self.assertFalse(value.creation_report['startup_overlap']['client_input_admitted'])
        diagnostic = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
        diagnostic.local_server, diagnostic.ctx = value, value.ctx
        self.assertTrue(diagnostic.client_preparation_server_ready())
        with patch.object(value, '_map_progress', return_value={'available': False}), \
                patch.object(zoning.time, 'monotonic', return_value=101):
            self.assertFalse(diagnostic.interaction_dependencies_ready())
        self.assertFalse(value.creation_report['startup_overlap']['client_input_admitted'])
        self.assertEqual(value.query.call_count, 1)

    def test_independent_world_proof_completes_original_stage_and_both_proofs_admit_input(self):
        fixture, value, child = self.instance()
        map_stage = value.ctx.report['stages'][0]
        client_stage = {'stage': 'actual_client_startup', 'started_utc': 'later'}
        value.ctx.report['stages'].append(client_stage)
        value.owner.client = Mock(started=110)
        diagnostic = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
        diagnostic.local_server, diagnostic.ctx = value, value.ctx
        with patch.object(zoning.time, 'monotonic', return_value=150):
            self.assertTrue(diagnostic.interaction_dependencies_ready())
        self.assertEqual(map_stage['status'], 'passed')
        self.assertNotIn('status', client_stage)
        value.ctx.passed.assert_not_called()
        self.assertEqual(value.query.call_count, 2)
        overlap = value.creation_report['startup_overlap']
        self.assertTrue(overlap['native_map_ready_verified'])
        self.assertFalse(overlap['client_input_admitted'])
        self.assertEqual(overlap['native_map_ready_seconds'], 50)
        self.assertEqual(overlap['observed_native_process_overlap_seconds'], 40)
        self.assertTrue(value.creation_report['map_startup_guard']['passed'])
        self.assertTrue(value.zoning_report['saved_startup']['native_ready_verified'])
        self.assertFalse(value.zoning_report['saved_startup']['character_world_entry_verified'])
        value.ctx.report.update(startup_observed=True, renderer_initialized=True, all_data_loaded=True)
        with patch.object(zoning.time, 'monotonic', return_value=155):
            self.assertTrue(diagnostic.interaction_dependencies_ready())
        self.assertTrue(overlap['client_input_admitted'])
        self.assertEqual(value.query.call_count, 2)
        value.ctx.start.assert_called_once()

    def test_original_native_deadline_is_not_reset_by_client_loading_or_retry(self):
        fixture, value, child = self.instance()
        deadline = value.initial_map_startup['deadline']
        with patch.object(zoning.time, 'monotonic', return_value=deadline):
            with self.assertRaisesRegex(server.base.DiagnosticError, 'startup timed out'):
                value.poll_initial_map_startup()
        self.assertEqual(value.initial_map_startup['deadline'], deadline)
        value.ctx.start.assert_called_once()
        self.assertFalse(value.creation_report['startup_overlap']['client_input_admitted'])

    def test_cancellation_or_native_exit_preserves_database_and_owned_failure_evidence(self):
        fixture, value, child = self.instance()
        before = copy.deepcopy(fixture.rows)
        value.ctx.check.side_effect = server.base.Cancelled('user stopped')
        with self.assertRaises(server.base.Cancelled):
            value.poll_initial_map_startup()
        value.ctx.check.side_effect = None
        child.process.poll.return_value = 1
        with patch.object(zoning.time, 'monotonic', return_value=101):
            with self.assertRaises(server.base.DiagnosticError):
                value.poll_initial_map_startup()
        self.assertEqual(fixture.rows, before)
        self.assertIs(value.maps[self.selected_map]['process'], child)
        self.assertFalse(value.creation_report['map_ready'])
        self.assertFalse(value.creation_report['startup_overlap']['client_input_admitted'])

    def test_overlap_requires_current_saved_map_process_runtime_and_verified_graph(self):
        for field in ('runtime', 'map', 'graph'):
            fixture, value, child = self.instance()
            if field == 'runtime': value.maps[self.selected_map]['runtime'] = value.runtime
            elif field == 'map': value.startup_preparation_map_id = 5 if self.selected_map == 1 else 1
            elif self.selected_map == 5: value.creation_report['kings_row_beacon_graph']['verified'] = False
            else: value.creation_report['atlas_beacon_graph']['status'] = 'incomplete'
            with self.subTest(field=field), self.assertRaises(server.base.DiagnosticError):
                value.client_startup_assets_allowed()

    def test_client_preparation_health_checks_original_deadline_without_starting_queries(self):
        fixture, value, child = self.instance()
        original_check_count = value.ctx.check.call_count
        zero = {'available': True, 'tick_completed': 0, 'stage': 'DEFINITIONS', 'unchanged_seconds': 0}
        with patch.object(server.LocalCharacterReopenServer, 'health'), \
                patch.object(value, '_map_progress', return_value=zero), \
                patch.object(zoning.time, 'monotonic', return_value=101):
            value.health()
        self.assertEqual(value.ctx.check.call_count, original_check_count)
        self.assertEqual(value.query.call_count, 1)
        overlap = value.creation_report['startup_overlap']
        self.assertEqual(overlap['last_initializing_progress_observed_monotonic'], 101)
        self.assertEqual(overlap['initializing_progress_observations'][0]['completed_ticks'], 0)
        self.assertFalse(overlap['native_map_ready_verified'])
        with patch.object(server.LocalCharacterReopenServer, 'health'), \
                patch.object(zoning.time, 'monotonic', return_value=value.initial_map_startup['deadline']):
            with self.assertRaisesRegex(server.base.DiagnosticError, 'native startup timed out'):
                value.health()
        value.ctx.start.assert_called_once()

    def test_texture_preparation_report_attributes_selected_world(self):
        fixture, value, child = self.instance()
        value.ctx.children = []
        diagnostic = creation.CharacterCreationDiagnostic.__new__(creation.CharacterCreationDiagnostic)
        diagnostic.local_server, diagnostic.ctx = value, value.ctx
        preparation = type('Preparation', (), {'finished': 105, 'started': 100, 'thread_started': True})()
        diagnostic.record_texture_schedule(preparation, 104, 'passed')
        result = value.ctx.report['client_texture_startup_schedule']
        self.assertEqual(result['preparation_phase'], 'during_owned_saved_map_native_startup')
        self.assertEqual(result['saved_map_id'], self.selected_map)
        self.assertFalse(result['physical_startup_savings_validated'])

    def test_first_native_tick_is_timing_evidence_and_never_world_or_input_acceptance(self):
        fixture, value, child = self.instance()
        value.observe_initial_map_progress({'available': True, 'tick_completed': 1, 'unchanged_seconds': 0}, 125)
        overlap = value.creation_report['startup_overlap']
        self.assertEqual(overlap['first_completed_tick_observed_seconds'], 25)
        self.assertFalse(overlap['first_tick_alone_grants_readiness'])
        self.assertFalse(overlap['native_map_ready_verified'])
        self.assertFalse(overlap['client_input_admitted'])
        self.assertFalse(value.creation_report['map_ready'])
        self.assertEqual(value.query.call_count, 1)


class SavedAtlasOverlapTests(SavedMapOverlapTests):
    selected_map = 1


class DeferredAtlasPreparationGuardTests(unittest.TestCase):
    def instance(self):
        fixture = budget_fixture.KingsPreparationBudgetTests()
        self.addCleanup(fixture.doCleanups)
        value = fixture.instance()
        value.active_map_id = 5
        value.maps = {5: {'ready': True}}
        value.atlas_preparation_deferred = True
        fixture.control.report['map_id'] = 1
        now_ms = round(fixture.clock.utc() * 1000)
        value._accept_prepare(dict(format=1, session_id=budget_fixture.SESSION, client_pid=44,
            character_id=1, epoch=1, action='prepare', from_map_id=5, to_map_id=1,
            requested_utc_ms=now_ms), now_ms)
        target = value.runtime.with_name('deferred-atlas'); target.mkdir()
        return fixture, value, target

    def test_deferred_atlas_loop_respects_existing_phase_deadline_before_native_launch(self):
        fixture, value, target = self.instance()
        original_check = value.ctx.check
        def prepare():
            fixture.clock.advance(601)
            value.ctx.check()
            return target
        value.prepare_atlas_runtime = Mock(side_effect=prepare)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'Atlas Park Python preparation timed out'):
            value._spawn_map(1)
        self.assertIs(value.ctx.check, original_check)
        value.ctx.start.assert_not_called()
        self.assertEqual(value.active_map_id, 5)
        self.assertNotIn(1, value.maps)
        self.assertFalse(value.pending['python_preparation_completed'])
        self.assertEqual(value.pending['runtime_preparation_elapsed_ms'], 601000)

    def test_logout_request_interrupts_deferred_atlas_and_preserves_kings(self):
        fixture, value, target = self.instance()
        original_check = value.ctx.check
        def prepare():
            (value.owner.args.state / 'character-logout.json').write_text('current user request')
            value.ctx.check()
            return target
        value.prepare_atlas_runtime = Mock(side_effect=prepare)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'requested ordinary save'):
            value._spawn_map(1)
        self.assertIs(value.ctx.check, original_check)
        value.ctx.start.assert_not_called()
        self.assertEqual(value.active_map_id, 5)
        self.assertNotIn(1, value.maps)
        self.assertFalse(value.pending['python_preparation_completed'])

    def test_native_atlas_keeps_original_shared_deadline_after_python_preparation(self):
        fixture, value, target = self.instance()
        deadline = value.pending['preparation_overall_deadline']
        def prepare():
            fixture.clock.advance(200)
            value.ctx.check()
            return target
        value.prepare_atlas_runtime = Mock(side_effect=prepare)
        value._spawn_map(1)
        self.assertEqual(value.pending['deadline'], deadline)
        self.assertEqual(value.pending['preparation_phase'], 'native_readiness')
        self.assertTrue(value.pending['python_preparation_completed'])
        self.assertEqual(value.pending['runtime_preparation_elapsed_ms'], 200000)
        value.ctx.start.assert_called_once()
        command = value.ctx.start.call_args.args[1]
        self.assertIn('--chdir=' + str(target), command)
        self.assertEqual(command[command.index('-udp') + 1], '7001')
        self.assertEqual(command[command.index('-map_id') + 1], '1')
        self.assertEqual(value.active_map_id, 5)
        self.assertEqual(value.maps[1]['runtime'], target)


class ServerInputProjectionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = mirror_fixture.CharacterMapDataTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.value = self.fixture.value
        self.value.map_package = {'source_commit': server.device.SOURCE_COMMIT,
            'files': {'MapServer.exe': {'sha256': server.SERVER_TEXTURE_EXCLUSION_MAP}}}

    def test_source_and_exact_native_consumer_bind_the_excluded_directory(self):
        path = ROOT / 'upstream/ouroboros/MapServer/src/svr/svr_init.c'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), server.SERVER_TEXTURE_EXCLUSION_SOURCE)
        self.assertIn('FolderCacheExclude(FOLDER_CACHE_EXCLUDE_FOLDER, "texture_library")', path.read_text())
        proof = server.server_input_projection(self.value.map_package)
        self.assertEqual(proof['excluded_top_level_directories'], ['texture_library'])
        for key, changed in (('source_commit', '0' * 40), ('files', {'MapServer.exe': {'sha256': '0' * 64}})):
            candidate = dict(self.value.map_package, **{key: changed})
            self.assertIsNone(server.server_input_projection(candidate))

    def test_native_excluded_texture_tree_is_never_enumerated_and_client_bytes_stay_unchanged(self):
        for name in ('texture_library/nested/visual.texture', 'textures/retained.txt',
                     'texts/English/texture_library/retained.texword', 'object_library/collision.geo'):
            self.fixture.immutable(name, name)
        excluded = self.fixture.source / 'texture_library'
        before = (excluded / 'nested/visual.texture').read_bytes()
        real_scandir = os.scandir
        def scan(path):
            self.assertNotEqual(Path(path), excluded)
            return real_scandir(path)
        with patch.object(server.os, 'scandir', side_effect=scan):
            report = self.value.stage_map_data(self.fixture.source, self.fixture.target)
        self.assertEqual(report['files'], 3)
        self.assertFalse((self.fixture.target / 'texture_library').exists())
        self.assertEqual((excluded / 'nested/visual.texture').read_bytes(), before)
        self.assertTrue((self.fixture.target / 'texts/English/texture_library/retained.texword').is_file())
        self.assertTrue((self.fixture.target / 'object_library/collision.geo').is_file())

    def test_other_native_consumers_keep_all_inputs(self):
        self.fixture.immutable('texture_library/a.texture')
        self.value.map_package['files']['MapServer.exe']['sha256'] = '0' * 64
        report = self.value.stage_map_data(self.fixture.source, self.fixture.target)
        self.assertEqual(report['files'], 1)
        self.assertTrue((self.fixture.target / 'texture_library/a.texture').is_file())

    def test_native_excluded_directory_cannot_be_a_link(self):
        (self.fixture.source / 'texture_library').symlink_to(self.fixture.imported, target_is_directory=True)
        with self.assertRaisesRegex(server.base.DiagnosticError, 'not a real directory'):
            self.value.stage_map_data(self.fixture.source, self.fixture.target)

    def test_closed_complete_generation_is_compatible_without_replacing_source_links(self):
        previous = {'format': 2, 'source': 'fully_verified', 'native_closure_sha256': 'x'}
        current = dict(previous, server_input_projection=server.server_input_projection(self.value.map_package))
        self.assertTrue(self.value.legacy_data_identity_matches(previous, current, {}))
        self.assertFalse(self.value.legacy_data_identity_matches(dict(previous, source='different'), current, {}))

    def test_projected_cache_reuses_after_exact_changed_parent_validation(self):
        fixture = reuse_fixture.ServerWorktreeReuseTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.source('texture_library/nested/a.texture')
        projection = server.server_input_projection(self.value.map_package)
        with patch.object(server, 'server_input_projection', return_value=projection):
            first = fixture.make(1); fixture.prepare(first); fixture.close(first)
            cached = first.data_cache.path / 'data'
            os.utime(cached, ns=(cached.stat().st_atime_ns, cached.stat().st_mtime_ns + 1000000))
            second = fixture.make(2)
            with patch.object(second, 'stage_map_data', side_effect=AssertionError('cold mirror repeated')):
                fixture.prepare(second)
        self.assertTrue(second.data_cache.summary['reused'])
        self.assertEqual(second.data_cache.summary['changed_parent_paths'], ['.'])
        self.assertFalse((second.runtime / 'data/texture_library').exists())

    def test_existing_closed_full_cache_is_migrated_without_cold_mirror_or_removing_textures(self):
        fixture = reuse_fixture.ServerWorktreeReuseTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.source('texture_library/nested/a.texture')
        first = fixture.make(1); fixture.prepare(first); fixture.close(first)
        projection = server.server_input_projection(self.value.map_package)
        second = fixture.make(2)
        with patch.object(server, 'server_input_projection', return_value=projection), \
                patch.object(second, 'stage_map_data', side_effect=AssertionError('qualified cache discarded')):
            fixture.prepare(second)
        self.assertTrue(second.data_cache.summary['reused'])
        self.assertTrue(second.data_cache.summary['legacy_generation_migrated'])
        self.assertTrue((second.runtime / 'data/texture_library/nested/a.texture').is_file())
        self.assertEqual(second.data_cache.identity['server_input_projection'], projection)


if __name__ == '__main__':
    unittest.main()
