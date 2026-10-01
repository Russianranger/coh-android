"""Two real sessions, unchanged saved rows, ordinary recovery and frame gates."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

spec = importlib.util.spec_from_file_location('character_reopen_host_test', Path(__file__).with_name('character_reopen_host_smoke.py'))
reopen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reopen)
character, host = reopen.character, reopen.host
SESSION, PREVIOUS, PID = '0123456789abcdef0123456789abcdef', 'f'*32, 460


class Connection:
    def __init__(self): self.sent = []
    def sendall(self, data): self.sent.append(data)


def save(path, pixels, *geometry): path.write_bytes(b'bounded-image-fixture')


def events():
    return [
        {'type': 'client_interaction_ready', 'session_id': SESSION, 'client_pid': PID},
        {'type': 'client_login_ready', 'session_id': SESSION, 'client_pid': PID, 'character_list_sent': True},
        {'type': 'character_connected', 'session_id': SESSION, 'client_pid': PID,
         'character_id': 1, 'baseline_character_id': 1, 'name': 'THORHERO', 'account': 'COHLOCAL', 'map_id': 1,
         'reopen_verified': True, 'existing_character_verified': True},
        {'type': 'character_relocated', 'session_id': SESSION, 'client_pid': PID, 'character_id': 1,
         'name': 'THORHERO', 'account': 'COHLOCAL', 'map_id': 1, 'ordinary_stuck_observed': True,
         'on_atlas_safe_position': True, 'stable_ground_verified': True},
        {'type': 'character_saved', 'session_id': SESSION, 'client_pid': PID,
         'character_id': 1, 'name': 'THORHERO', 'committed_sql_verified': True}]


class CharacterReopenHostTests(unittest.TestCase):
    def test_world_receipt_works_without_ignored_zip_and_binds_apk_and_private_map_tree(self):
        contract = {'scope':'atlas_world_geometry_texture_supplement', 'archive_pin':{'bytes':20,'sha256':'a'*64},
            'manifest_pin':{'bytes':30,'sha256':'b'*64}, 'file_count':2,'payload_bytes':40,'files_sha256':'c'*64}
        worktree = {'import':{'receipt_sha256':'d'*64}, 'package_sha256':'e'*64,
            'cache_archive_sha256':'f'*64, 'prerequisites_archive_sha256':'1'*64,'normalized_mtime_epoch':1767225600}
        key = hashlib.sha256(('d'*64+'e'*64+'f'*64+'1'*64+'1767225600').encode()).hexdigest()[:24]
        receipt = {'format':1,'scope':contract['scope'],'manifest_sha256':'b'*64,'archive_sha256':'a'*64,
            'file_count':2,'payload_bytes':40,'verified_file_count':2,'files_sha256':'c'*64,
            'normalized_mtime_epoch':1767225600,'imported_files_modified':False,'worktree_identity_modified':False,
            'accepted_cache_archive_modified':False,'runtime_visual_validated':False,
            'visual_scope':{'includes':['selected_atlas_world_assets']},
            'installed_files':2,'reused_files':0,'worktree':'client-work-'+key,
            'cache_refresh':{'policy':reopen.WORLD_CACHE_POLICY,'performed':True,
                'removed_files':1,'removed_bytes':50,'removed_inventory_sha256':'2'*64,'accepted_cache_archive_modified':False}}
        report = {'atlas_world_supplement':receipt,'client_worktree':worktree,
            'character_reopen':{'private_map_data':{'source_worktree':receipt['worktree'],'imported_inputs_readonly':True}}}
        manifest = {'files':{'world.zip':contract['archive_pin'],'world.json':contract['manifest_pin']}}
        world = SimpleNamespace(ARCHIVE='world.zip', MANIFEST='world.json',
            bundle_contract=lambda:contract, read_manifest=mock.Mock(return_value={'visual_scope':receipt['visual_scope']}),
            verify=mock.Mock(side_effect=AssertionError('The ignored world ZIP is absent in a fresh runtime checkout')))
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(host, 'ROOT', Path(temporary)), \
                mock.patch.object(host.assets_tool,'world_tools',return_value=world):
            metadata = Path(temporary)/'assets/world.json'
            metadata.parent.mkdir(); metadata.write_text('{"pinned_metadata":true}')
            self.assertFalse((metadata.parent/'world.zip').exists())
            reopen.validate_world_supplement(report,manifest)
            world.read_manifest.assert_called_once_with(metadata)
            world.verify.assert_not_called()
            for changes in ({'imported_files_modified':True},{'archive_sha256':'3'*64},
                    {'worktree':'client-work-another'},{'verified_file_count':1}):
                invalid = copy.deepcopy(report); invalid['atlas_world_supplement'].update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    reopen.validate_world_supplement(invalid,manifest)
            invalid = copy.deepcopy(report); invalid['character_reopen']['private_map_data']['source_worktree'] = 'other'
            with self.assertRaisesRegex(ValueError,'MapServer did not mirror'):
                reopen.validate_world_supplement(invalid,manifest)

    def test_report_independently_rejects_missing_ground_and_preserved_row_proofs(self):
        flags = ('reopen_verified','existing_character_verified','preserved_existing_identity','native_client_ready_observed',
            'powers_preserved','costume_preserved','selected_rows_preserved','ordinary_stuck_observed',
            'on_atlas_safe_position','stable_ground_verified','committed_safe_position_verified')
        baseline = {'character_id':1,'auth_id':7,'snapshot_sha256':'a'*64,'identity_sha256':'b'*64,
            'login_count':1,'table_sha256':{'powers':'c'*64,'costumeparts':'d'*64},'row_counts':{'powers':7,'costumeparts':14}}
        proof = dict.fromkeys(flags,True)
        proof.update(character_id=1,before_character_id=1,baseline_character_id=1,baseline_character_count=1,
            auth_id=7,baseline=baseline,before_login_count=1,login_count=2,
            table_sha256=baseline['table_sha256'],row_counts=baseline['row_counts'])
        report = {'scope':'actual_character_reopen_guest','diagnostic_mode':'actual_character_reopen',
            'local_login':{'profile_reused':True,'character_count':1},'character_reopen':proof}
        with mock.patch.object(character,'validate_report'), mock.patch.object(reopen,'validate_world_supplement'):
            reopen.validate_report(report,SESSION,{})
            for flag in flags:
                invalid = copy.deepcopy(report); invalid['character_reopen'].pop(flag)
                with self.subTest(flag=flag), self.assertRaises(ValueError): reopen.validate_report(invalid,SESSION,{})
            invalid = copy.deepcopy(report); invalid['character_reopen']['login_count'] = 1
            with self.assertRaisesRegex(ValueError,'increment'): reopen.validate_report(invalid,SESSION,{})

    def test_reopen_event_requires_same_existing_character_and_native_recovery_before_save(self):
        initial = events()
        invalid = [([], initial[3]), (initial[:2], initial[3]), (initial[:3], initial[4]),
            (initial[:2], dict(initial[2], character_id=2)),
            (initial[:2], dict(initial[2], reopen_verified=False)),
            (initial[:3], dict(initial[3], client_pid=PID+1)),
            (initial[:3], dict(initial[3], character_id=2)),
            (initial[:3], dict(initial[3], stable_ground_verified=False)),
            (initial[:4], initial[3])]
        for prefix, change in invalid:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary)/'events'
                path.write_text(''.join(json.dumps(item)+'\n' for item in prefix+[change]))
                with self.assertRaises(ValueError): reopen.ReopenEvents(path, SESSION).poll()
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'events'
            terminal = {'type': 'stage', 'stage': 'actual_client_interaction', 'status': 'passed'}
            path.write_text(''.join(json.dumps(item)+'\n' for item in initial+[terminal]))
            proof = reopen.ReopenEvents(path, SESSION); proof.poll()
            self.assertTrue(proof.terminal)
            self.assertEqual(proof.relocated_generation, 1)
            self.assertEqual(proof.saved_generation, 1)

    def test_second_command_reuses_exact_mounts_profile_and_arguments_with_new_session(self):
        command = ['proot', '-b', '/owned/state:/state', '/usr/bin/python3',
            '/opt/coh/character_creation_diagnostic.py', '--session-id', PREVIOUS,
            '--profile', 'android-local-login', '--interaction-seconds', '1200']
        result = reopen.reopen_command(command, PREVIOUS, SESSION)
        self.assertEqual(result, command[:4]+['/opt/coh/character_reopen_diagnostic.py',
            '--session-id', SESSION]+command[7:])
        self.assertEqual(command[4], '/opt/coh/character_creation_diagnostic.py')
        with self.assertRaises(ValueError): reopen.reopen_command(command, PREVIOUS, PREVIOUS)
        with self.assertRaises(ValueError): reopen.reopen_command(command+['--other', PREVIOUS], PREVIOUS, SESSION)

    def test_restart_preserves_database_and_prefix_but_clears_only_completed_requests(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary); state = work/'state'; state.mkdir()
            (work/'socket').mkdir()
            root = state/'diagnostic'; root.mkdir()
            profile = root/'android-local-login'; profile.mkdir()
            cluster = profile/'pgdata'; cluster.mkdir()
            prefix = root/'wine'; prefix.mkdir()
            (profile/'profile.json').write_text('{"initialized":true}')
            (cluster/'PG_VERSION').write_text('17\n')
            (prefix/'.coh-wine-ready.json').write_text('{"format":1}')
            (cluster/'preserved-database-page').write_bytes(b'actual-saved-page')
            for name in ('character-logout.json', 'interaction-finish.json'): (state/name).write_text('{}')
            before = reopen.persistent_profile_identity(work)
            self.assertEqual(reopen.reset_session_requests(state), ['interaction-finish.json', 'character-logout.json'])
            self.assertEqual(reopen.persistent_profile_identity(work), before)
            self.assertEqual((cluster/'preserved-database-page').read_bytes(), b'actual-saved-page')
            (cluster/'postmaster.pid').write_text('123')
            with self.assertRaisesRegex(ValueError, 'PostgreSQL survived'): reopen.persistent_profile_identity(work)

    def test_prior_reports_are_archived_so_second_failure_cannot_export_stale_creation_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            (state/'latest-report.json').write_text(json.dumps({'session_id': PREVIOUS, 'passed': True}))
            (state/'report.zip').write_bytes(b'atomic-first-session-report')
            directory = reopen.archive_completed_reports(state, PREVIOUS)
            self.assertFalse((state/'latest-report.json').exists())
            self.assertFalse((state/'report.zip').exists())
            self.assertEqual((state/directory/'report.zip').read_bytes(), b'atomic-first-session-report')
            with self.assertRaises(ValueError): reopen.archive_completed_reports(state, PREVIOUS)

    def test_full_reopen_script_never_creates_character_and_waits_for_three_native_proof_frames(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); finish = root/'finish.json'
            script = reopen.ReopenInteraction(SESSION, root, finish)
            frame = host.ClientFramebuffer(); frame.pixels[:] = bytes((32,64,96,0))*(800*600)
            frame.request_login_generation = 1
            frame.request_connected_generation = frame.request_relocated_generation = frame.request_saved_generation = 0
            proof = SimpleNamespace(client_pid=PID, character_id=1, login_generation=1,
                connected_generation=0, relocated_generation=0, saved_generation=0)
            connection = Connection(); clock = [0.0]; sequence = [0]
            def tick():
                sequence[0] += 1; clock[0] += 2
                script.on_frame(connection, frame, proof, sequence[0], [{},{},{}], clock[0])
            with mock.patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]), \
                    mock.patch.object(host.time, 'time', side_effect=lambda: 1000000+clock[0]), \
                    mock.patch.object(host.time, 'sleep', side_effect=lambda seconds: clock.__setitem__(0, clock[0]+seconds)), \
                    mock.patch.object(host, 'save_png', side_effect=save), \
                    mock.patch.object(character, 'read_rendered_account', return_value=(True, 'whole-account-ocr')), \
                    mock.patch.object(character, 'read_button', side_effect=lambda _f,_e,label,*_args:
                        (((200,72,95), 'actual-thorhero-ocr') if label == 'THORHERO' else (None, 'no-help-dialog'))):
                connected = next(i for i,a in enumerate(script.ACTIONS) if a[0] == 'connected')
                for _ in range(100):
                    tick()
                    if script.action == connected: break
                self.assertEqual(script.action, connected)
                proof.connected_generation = 1
                tick(); self.assertEqual(script.result['connected_captures'], [])
                frame.request_connected_generation = 1
                for _ in range(60):
                    tick()
                    if script.ACTIONS[script.action][0] == 'relocated': break
                self.assertTrue((root/'character-relocation.json').is_file())
                self.assertFalse((root/'character-logout.json').exists())
                for _ in range(3): tick()
                self.assertEqual(script.result['world_after_stuck_captures'], [])
                proof.relocated_generation = 1
                tick(); self.assertEqual(script.result['world_after_stuck_captures'], [])
                frame.request_relocated_generation = 1
                for _ in range(20):
                    tick()
                    if script.ACTIONS[script.action][0] == 'saved': break
                self.assertEqual(len(script.result['world_after_stuck_captures']), 3)
                self.assertTrue((root/'character-logout.json').is_file())
                self.assertFalse(finish.exists())
                proof.saved_generation = 1
                tick(); self.assertEqual(script.result['post_save_captures'], [])
                frame.request_saved_generation = 1
                for _ in range(4): tick()
            self.assertTrue(finish.is_file())
            observer = {'failure': None, 'terminal_event_observed': True, 'client_pid': PID, 'interaction_script': script.result}
            report = {'session_id': SESSION, 'client_launch': {'pid': PID}}
            reopen.validate_observer(observer, report)
            names = [step['action'] for step in script.result['steps']]
            self.assertNotIn('open_character_creator', names)
            self.assertNotIn('register_play', names)
            self.assertEqual([button['label'] for button in script.result['ocr_buttons']], ['THORHERO'])
            invalid = copy.deepcopy(observer)
            invalid['interaction_script']['world_after_stuck_captures'][0]['frame_sequence'] = 1
            with self.assertRaisesRegex(ValueError, 'preceded ordinary stuck'): reopen.validate_observer(invalid, report)

    def test_recovery_wait_is_bounded_and_delivered_receipt_follows_final_return_release(self):
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); receipt = root/'character-relocation.json'
                script = reopen.ReopenInteraction(SESSION, root, root/'finish.json')
                script.ready_at = 0
                script.action = next(i for i,a in enumerate(script.ACTIONS) if a[2] == 'submit_ordinary_stuck')
                frame = host.ClientFramebuffer(); script.frame_generation = frame.generation
                proof = SimpleNamespace(client_pid=PID, character_id=1, relocated_generation=0)
                class CheckConnection(Connection):
                    def sendall(self, data):
                        self.assert_receipt = receipt.exists()
                        if fail and data == struct.pack('!BBHI',4,0,0,0xff0d): raise BrokenPipeError('lost release')
                        super().sendall(data)
                connection = CheckConnection()
                with mock.patch.object(host.time, 'sleep'), mock.patch.object(host.time, 'monotonic', return_value=5), \
                        mock.patch.object(host, 'save_png', side_effect=save):
                    if fail:
                        with self.assertRaises(BrokenPipeError): script.on_frame(connection, frame, proof, 1, [{},{},{}], 5)
                    else:
                        script.on_frame(connection, frame, proof, 1, [{},{},{}], 5)
                        self.assertFalse(connection.assert_receipt)
                        with self.assertRaisesRegex(ValueError, 'within 180 seconds'):
                            script.on_frame(connection, frame, proof, 2, [{},{},{}], 185)
                self.assertEqual(receipt.exists(), not fail)

    def test_optional_help_dismissal_requires_rendered_button_and_absent_final_popup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = reopen.ReopenInteraction(SESSION, root, root/'finish.json')
            frame = host.ClientFramebuffer(); proof = SimpleNamespace(client_pid=PID)
            connection = Connection()
            with mock.patch.object(character, 'read_button', side_effect=[((512,474,95),'actual-ok'),
                        (None,'dialog-absent'), ((512,474,95),'still-open')]):
                self.assertTrue(script.custom_action('optional_ocr_move',None,'check_atlas_help_1',
                    connection,frame,proof,5,10))
                self.assertEqual(connection.sent, [struct.pack('!BBHH',5,0,512,474)])
                with mock.patch.object(host.time, 'sleep'):
                    script.custom_action('optional_ocr_click',None,'dismiss_atlas_help_1',connection,frame,proof,7,14)
                self.assertIn(struct.pack('!BBHH',5,1,512,474), connection.sent)
                connection.sent.clear()
                script.custom_action('optional_ocr_move',None,'check_atlas_help_2',connection,frame,proof,9,18)
                script.custom_action('optional_ocr_click',None,'dismiss_atlas_help_2',connection,frame,proof,11,22)
                self.assertEqual(connection.sent, [])
                with self.assertRaisesRegex(ValueError, 'three bounded'):
                    script.custom_action('modal_clear',None,'verify_atlas_help_dismissed',connection,frame,proof,13,26)
            self.assertFalse((root/'character-relocation.json').exists())

    def test_continuity_rejects_changed_full_snapshot_profiles_and_character_identity(self):
        saved = {'character_id':1, 'auth_id':7, 'snapshot_sha256':'a'*64,
            'table_sha256': {'ents':'b'*64,'ents2':'c'*64,'powers':'d'*64,'costumeparts':'e'*64},
            'row_counts': {'ents':1,'ents2':1,'powers':7,'costumeparts':14}}
        created = {'session_id':PREVIOUS, 'character_creation':saved, 'cleanup_complete':True,
                   'cleanup':{'postgres_graceful':True,'wine_prefix_stopped':True,'owned_processes_reaped':True}}
        reopened = {'session_id':SESSION, 'character_reopen':dict(saved, baseline=copy.deepcopy(saved)),
                    'local_login':{'profile_reused':True}}
        reopen.validate_continuity(created, reopened, {'profile_inode':1}, {'profile_inode':1})
        for field, value in [('snapshot_sha256','f'*64),('character_id',2),('auth_id',8)]:
            invalid = copy.deepcopy(reopened); invalid['character_reopen']['baseline'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                reopen.validate_continuity(created, invalid, {}, {})
        with self.assertRaisesRegex(ValueError, 'profile was replaced'):
            reopen.validate_continuity(created, reopened, {'profile_inode':1}, {'profile_inode':2})
        invalid = copy.deepcopy(reopened); invalid['session_id'] = PREVIOUS
        with self.assertRaisesRegex(ValueError, 'session identity'): reopen.validate_continuity(created, invalid, {}, {})


if __name__ == '__main__': unittest.main()
