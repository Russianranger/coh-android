"""A graphical save requires this session's account, connection and logout proof."""
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import character_creation_diagnostic as guest

SESSION = '0123456789abcdef0123456789abcdef'
PID = 44


def identity(**changes):
    value = dict(session_id=SESSION, name='THORHERO', account='COHLOCAL',
                 character_id=17, auth_id=900260380, map_id=1, connected_on_atlas=True)
    value.update(changes)
    return value


def saved(**changes):
    value = dict(identity(), verified=True, committed_sql_verified=True,
                 requested_logout_observed=True, logout_timer_observed=True, disconnected_before_sql=True,
                 forced_stop_before_save=False)
    value.update(changes)
    return value


class CharacterProofTests(unittest.TestCase):
    def test_save_requires_every_explicit_protocol_and_commit_fact(self):
        self.assertTrue(guest.save_verified(saved(), SESSION))
        for field in ('verified', 'committed_sql_verified', 'requested_logout_observed', 'logout_timer_observed',
                      'disconnected_before_sql', 'connected_on_atlas'):
            for value in (False, None, 1, 'true'):
                with self.subTest(field=field, value=value):
                    self.assertFalse(guest.save_verified(saved(**{field: value}), SESSION))
            incomplete = saved(); del incomplete[field]
            self.assertFalse(guest.save_verified(incomplete, SESSION))
        for value in (True, None, 0, 'false'):
            self.assertFalse(guest.save_verified(saved(forced_stop_before_save=value), SESSION))
        incomplete = saved(); del incomplete['forced_stop_before_save']
        self.assertFalse(guest.save_verified(incomplete, SESSION))

    def test_stale_session_account_name_map_and_noninteger_ids_are_rejected(self):
        for field, values in {
            'session_id': ['f' * 32, None], 'account': ['OTHER', None],
            'name': ['OTHERHERO', None], 'map_id': [True, '1', 2, None],
            'character_id': [True, 0, -1, 2**32, '17', 17.0, None],
            'auth_id': [True, 0, -1, 2**32, '900260380', None],
        }.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.assertFalse(guest.save_verified(saved(**{field: value}), SESSION))
        for value in (None, [], 'saved', 1):
            self.assertFalse(guest.save_verified(value, SESSION))
        self.assertTrue(guest.character_identity(identity(character_id=2**32-1), SESSION))


class CharacterObservationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.launch = {'session_id': SESSION, 'pid': PID}
        self.observation = ('Renderer initialization complete\nLoaded all data!\n', self.launch,
                            dict(self.launch, attached=True))
        d = guest.CharacterCreationDiagnostic.__new__(guest.CharacterCreationDiagnostic)
        d.args = SimpleNamespace(session_id=SESSION)
        d.ctx = SimpleNamespace(report={'startup_observed': True, 'mapserver_started': True,
                                        'character_creation': identity(connected_on_atlas=False)}, event=Mock())
        d.local_server = SimpleNamespace(report={'auth_id': 900260380}, character_evidence=Mock(return_value=None))
        d.login_announced = True; d.connected_announced = False; d.saved_announced = False
        d.connected_identity = None; d.capture_dir = self.root
        d.observer = Mock()
        d.observer.windows.return_value = [{'title': 'City of Heroes : PID: 44', 'mapped': True,
                                            'width': 800, 'height': 600}]
        self.colors = 16
        def capture(path):
            path.write_bytes(b'capture')
            return {'path': path.name, 'distinct_colors_capped': self.colors}
        d.observer.capture.side_effect = capture
        self.d = d
        parent = patch.object(guest.login.ClientLoginDiagnostic, 'observe_console', return_value=self.observation)
        self.parent_observe = parent.start(); self.addCleanup(parent.stop)

    def connect(self):
        self.d.ctx.report['character_creation'] = identity()
        self.d.observe_console()

    def test_connection_then_commit_emit_once_and_keep_same_identity(self):
        self.connect()
        self.assertTrue(self.d.connected_announced)
        self.assertFalse(self.d.saved_announced)
        self.assertEqual(self.d.connected_identity, (17, 900260380))
        self.assertEqual([call.args[0] for call in self.d.ctx.event.call_args_list], ['character_connected'])
        self.d.local_server.character_evidence.return_value = saved()
        self.d.observe_console()
        self.assertTrue(self.d.saved_announced)
        receipt = self.d.ctx.report['character_creation']
        self.assertEqual(receipt['client_pid'], PID)
        self.assertEqual(receipt['client_capture']['session_id'], SESSION)
        self.assertIn('verified_utc', receipt)
        calls = self.d.ctx.event.call_args_list
        self.assertEqual([call.args[0] for call in calls], ['character_connected', 'character_saved'])
        self.assertEqual(calls[-1].kwargs['character_id'], 17)
        self.assertTrue(calls[-1].kwargs['committed_sql_verified'])
        self.d.observe_console()
        self.assertEqual(self.d.ctx.event.call_count, 2)
        self.assertEqual(self.d.local_server.character_evidence.call_count, 2)
        self.d.observer.capture.assert_called_once()

    def test_connection_and_commit_in_one_poll_emit_in_order(self):
        self.d.ctx.report['character_creation'] = identity()
        self.d.local_server.character_evidence.return_value = saved()
        self.d.observe_console()
        self.assertEqual([call.args[0] for call in self.d.ctx.event.call_args_list],
                         ['character_connected', 'character_saved'])

    def test_no_character_poll_before_login_startup_and_actual_client(self):
        cases = [('login', False), ('startup', False), ('launch', None), ('console', None), ('observer', None)]
        for condition, value in cases:
            with self.subTest(condition=condition):
                self.d.login_announced = condition != 'login'
                self.d.ctx.report['startup_observed'] = condition != 'startup'
                observation = list(self.observation)
                if condition == 'launch': observation[1] = value
                if condition == 'console': observation[2] = value
                self.parent_observe.return_value = tuple(observation)
                observer = self.d.observer
                if condition == 'observer': self.d.observer = None
                self.d.observe_console()
                self.d.observer = observer
        self.d.local_server.character_evidence.assert_not_called()
        self.d.ctx.event.assert_not_called()

    def test_connected_character_must_match_session_and_logged_in_account(self):
        for changes in ({'session_id': 'f' * 32}, {'auth_id': 12}, {'character_id': True}, {'map_id': 2}):
            with self.subTest(changes=changes):
                self.d.ctx.report['character_creation'] = identity(**changes)
                with self.assertRaises(guest.base.DiagnosticError): self.d.observe_console()
        self.assertFalse(self.d.connected_announced)
        self.d.ctx.event.assert_not_called()

    def test_save_without_observed_connection_is_rejected(self):
        self.d.local_server.character_evidence.return_value = saved()
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'protocol save is incomplete'):
            self.d.observe_console()
        self.d.observer.capture.assert_not_called()

    def test_save_cannot_switch_character_auth_or_session(self):
        self.connect()
        for changes in ({'character_id': 18}, {'auth_id': 12}, {'session_id': 'f' * 32},
                        {'requested_logout_observed': False}, {'logout_timer_observed': False},
                        {'forced_stop_before_save': True}):
            with self.subTest(changes=changes):
                self.d.local_server.character_evidence.return_value = saved(**changes)
                with self.assertRaises(guest.base.DiagnosticError): self.d.observe_console()
        self.assertFalse(self.d.saved_announced)
        self.d.observer.capture.assert_not_called()

    def test_owned_mapserver_and_original_visible_client_are_required(self):
        self.connect(); self.d.local_server.character_evidence.return_value = saved()
        self.d.ctx.report['mapserver_started'] = False
        with self.assertRaisesRegex(guest.base.DiagnosticError, 'owned MapServer'): self.d.observe_console()
        self.d.ctx.report['mapserver_started'] = True
        for changes in ({'title': 'City of Heroes : PID: 45'}, {'mapped': False}, {'width': 1}):
            with self.subTest(changes=changes):
                self.d.observer.windows.return_value = [dict(title='City of Heroes : PID: 44',
                                                              mapped=True, width=800, height=600) | changes]
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'client identity disappeared'):
                    self.d.observe_console()
        self.d.observer.capture.assert_not_called()

    def test_blank_save_frame_waits_for_fresh_nonblank_capture_without_success_event(self):
        self.connect(); self.d.local_server.character_evidence.return_value = saved()
        self.colors = 1; self.d.observe_console()
        self.assertFalse(self.d.saved_announced)
        self.assertFalse((self.root / 'client-character-saved.ppm').exists())
        self.assertEqual(self.d.ctx.event.call_count, 1)
        self.colors = 16; self.d.observe_console()
        self.assertTrue(self.d.saved_announced)
        self.assertTrue((self.root / 'client-character-saved.ppm').is_file())

    def test_finish_requires_proved_save_and_same_client_before_parent_validation(self):
        with patch.object(guest.login.ClientLoginDiagnostic, 'finish_observation', return_value='finished') as parent:
            for announced, proof in [(False, saved(client_pid=PID)), (True, saved(client_pid=45)),
                                      (True, saved(client_pid=PID, disconnected_before_sql=False))]:
                self.d.saved_announced = announced; self.d.ctx.report['character_creation'] = proof
                with self.assertRaisesRegex(guest.base.DiagnosticError, 'save was not verified'):
                    self.d.finish_observation(self.launch, 'registry', 100)
            parent.assert_not_called()
            self.d.saved_announced = True; self.d.ctx.report['character_creation'] = saved(client_pid=PID)
            self.assertEqual(self.d.finish_observation(self.launch, 'registry', 100), 'finished')
            parent.assert_called_once_with(self.launch, 'registry', 100)


class CharacterBoundsTests(unittest.TestCase):
    def args(self, **changes):
        result = dict(session_id=SESSION, startup_timeout_seconds=900, observation_seconds=30,
                      interaction_seconds=1200, timeout_seconds=5400, profile=guest.login.server.PROFILE,
                      state=Path('/private/state'), assets=Path('/private/assets'),
                      socket_dir=Path('/private/socket'), game_data=Path('/private/data'))
        result.update(changes)
        return SimpleNamespace(**result)

    def test_native_character_mode_and_report_match_without_changing_local_login(self):
        d = guest.CharacterCreationDiagnostic.__new__(guest.CharacterCreationDiagnostic)
        d.args = SimpleNamespace(wine=Path('/wine'), assets=Path('/assets'), session_id=SESSION)
        d.work = Path('/work')
        default = guest.interactive.ClientInteractiveDiagnostic.launcher_command(d)
        self.assertEqual(d.launcher_command(), default + ['--character-creation'])
        self.assertEqual(guest.login.ClientLoginDiagnostic.launcher_command(d), default + ['--local-login'])
        policy = {'native_launcher_mode': '--local-login', 'protocol_version_check_retained': True}
        def parent_init(owner, args, context):
            owner.local_server = SimpleNamespace(report={'version_policy': policy})
        with patch.object(guest.login.ClientLoginDiagnostic, '__init__', parent_init), \
                patch.object(guest.character, 'LocalCharacterServer', return_value=SimpleNamespace(report={})):
            initialized = guest.CharacterCreationDiagnostic(None, None)
        self.assertEqual(initialized.local_server.report['version_policy'],
                         dict(policy, native_launcher_mode='--character-creation'))
        self.assertEqual(policy['native_launcher_mode'], '--local-login')

    def test_fixed_creator_budget_does_not_allow_short_unbounded_or_boolean_values(self):
        guest.validate_args(self.args()); guest.validate_args(self.args(startup_timeout_seconds=60))
        invalid = {'session_id': ['', 'g'*32, 'a'*31, 'A'*32, None],
                   'startup_timeout_seconds': [59, 901, True, '900'],
                   'observation_seconds': [0, 29, 31, True],
                   'interaction_seconds': [180, 1199, 1201, True],
                   'timeout_seconds': [1800, 5399, 5401, True], 'profile': ['other', None]}
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(guest.base.DiagnosticError): guest.validate_args(self.args(**{field: value}))

    def test_private_paths_reject_relative_parent_traversal_root_and_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            link = Path(temporary) / 'linked'; link.symlink_to(Path(temporary) / 'missing')
            for field in ('state', 'assets', 'socket_dir', 'game_data'):
                for value in (Path('relative'), Path('/private/../other'), Path('/'), link):
                    with self.subTest(field=field, value=value):
                        with self.assertRaises(guest.base.DiagnosticError): guest.validate_args(self.args(**{field: value}))

    def test_initialize_rejects_stale_logout_receipt_and_links_before_starting_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = root / 'character-logout.json'
            target = root / 'target.json'; target.write_text('{}')
            diagnostic = guest.CharacterCreationDiagnostic.__new__(guest.CharacterCreationDiagnostic)
            diagnostic.args = self.args(state=root)
            diagnostic.work = root / 'work'
            diagnostic.ctx = SimpleNamespace(report={'asset_sha256': dict.fromkeys(guest.REQUIRED, 'pinned')})
            with patch.object(guest.login.ClientLoginDiagnostic, 'initialize') as parent, \
                    patch.object(guest.avatar, 'install', return_value={}) as supplement, \
                    patch.dict(sys.modules, atlas_world_assets=SimpleNamespace(install=Mock(return_value={}))) as modules:
                for kind in ('file', 'existing_link', 'dangling_link'):
                    with self.subTest(kind=kind):
                        if kind == 'file': request.write_text('{}')
                        else: request.symlink_to(target if kind == 'existing_link' else root / 'missing')
                        with self.assertRaisesRegex(guest.base.DiagnosticError, 'Stale character logout'):
                            diagnostic.initialize()
                        parent.assert_not_called()
                        supplement.assert_not_called()
                        request.unlink()
                diagnostic.initialize()
                parent.assert_called_once_with()
                supplement.assert_called_once_with(diagnostic.work, diagnostic.args.assets, diagnostic.ctx)
                modules['atlas_world_assets'].install.assert_called_once_with(
                    diagnostic.work, diagnostic.args.assets, diagnostic.ctx)

    def test_process_budget_caps_observation_and_retains_ownership_and_checks(self):
        context = guest.CharacterContext.__new__(guest.CharacterContext)
        context.children = []; context.check = Mock()
        with patch.object(guest.base, 'OwnedProcess', return_value=Mock()) as create:
            child = context.start('query', ['query'], env={'PRIVATE': '1'}, input_text='read only')
            self.assertIs(context.children[0], child)
            context.check.assert_called_once()
            create.assert_called_once_with('query', ['query'], {'PRIVATE': '1'}, 'read only')
            context.children = [child] * guest.MAX_CHILDREN
            with self.assertRaisesRegex(guest.base.DiagnosticError, 'process count exceeded'):
                context.start('overflow', ['query'])
            self.assertEqual(create.call_count, 1)


if __name__ == '__main__': unittest.main()
