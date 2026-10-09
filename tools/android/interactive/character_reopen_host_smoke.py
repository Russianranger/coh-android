#!/usr/bin/env python3
"""Create and save through the UI, fully restart, then reopen the same character."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import socket
import subprocess
import time

spec = importlib.util.spec_from_file_location('character_reopen_shared_host', Path(__file__).with_name('character_host_smoke.py'))
character = importlib.util.module_from_spec(spec)
spec.loader.exec_module(character)
host, require = character.host, character.require
INTERACTION_SECONDS = character.INTERACTION_SECONDS
OVERALL_SECONDS = character.OVERALL_SECONDS
# Pinned Hybrid UI's first selected name row at 800x600. The actual click still
# comes only from exact recognized THORHERO bounds, never from a fixed point.
CHARACTER_REGION = (100, 60, 330, 83)
ATLAS_HELP_REGION = (345, 270, 680, 490)
WORLD_CACHE_POLICY = 'once_per_world_manifest_private_atlas_geobin_and_supplemented_object_library_only'


def reopen_actions():
    actions = [('login', None, 'wait_existing_character_list'),
        ('move', (600, 100), 'clear_cursor_before_existing_character'),
        ('ocr_move', ('THORHERO', CHARACTER_REGION), 'preposition_existing_character'),
        ('ocr_click', None, 'select_existing_character')]
    actions += character.click_steps('play_existing_character', 757, 579)
    actions += [('connected', None, 'wait_reopened_atlas_connection'),
                ('move', (600, 100), 'clear_cursor_before_atlas_help')]
    for index in range(1, 4):
        actions += [('optional_ocr_move', None, 'check_atlas_help_'+str(index)),
                    ('optional_ocr_click', None, 'dismiss_atlas_help_'+str(index))]
    actions += [('modal_clear', None, 'verify_atlas_help_dismissed'),
        ('key', 0xff0d, 'open_stuck_chat'), ('command', '/stuck', 'type_ordinary_stuck'),
        ('key', 0xff0d, 'submit_ordinary_stuck'),
        ('relocated', None, 'wait_world_after_stuck'),
        ('key', 0xff0d, 'open_chat'), ('command', '/quittologin', 'type_ordinary_logout'),
        ('key', 0xff0d, 'submit_ordinary_logout'), ('saved', None, 'wait_committed_save')]
    return tuple(actions)


def write_stuck_request(path, session, client_pid, character_id):
    # Same atomic private delivery receipt contract as ordinary logout. This
    # proves input delivery only; authoritative position remains guest evidence.
    require(re.fullmatch(r'[0-9a-f]{32}', session) and type(client_pid) is int and client_pid > 0
            and type(character_id) is int and character_id > 0, 'Stuck request identity differs')
    require(path.parent.is_dir() and not path.parent.is_symlink() and not path.exists() and not path.is_symlink(),
            'Stuck request destination is not fresh and private')
    value = {'format': 1, 'session_id': session, 'client_pid': client_pid, 'character_id': character_id,
             'action': 'stuck', 'sent_utc_ms': int(time.time()*1000)}
    payload = (json.dumps(value, sort_keys=True)+'\n').encode()
    temporary = path.with_name(path.name+'.tmp-'+secrets.token_hex(8))
    try:
        with temporary.open('xb') as output:
            os.chmod(temporary, 0o600)
            output.write(payload); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return value


class ReopenInteraction(character.CharacterInteraction):
    ACTIONS = character.CharacterInteraction.LOGIN_ACTIONS + reopen_actions()

    def __init__(self, session, evidence, finish_path):
        super().__init__(session, evidence, finish_path)
        self.result.update(scope='host_graphical_existing_character_reopen_and_ordinary_logout',
            character_reopen_visual_validated=False, atlas_scene_visual_validated=False,
            collision_validated=False, world_after_stuck_captures=[], atlas_help_checks=[])
        self.stuck_delivered_at = None
        self.modal_position = None

    def fixture_text(self, connection, value):
        if value == '/stuck':
            for letter in value: character.key(connection, ord(letter))
        else:
            super().fixture_text(connection, value)

    def custom_action(self, kind, value, name, connection, frame, events, sequence, now):
        if kind in ('optional_ocr_move', 'modal_clear'):
            match, stem = character.read_button(frame, self.evidence, 'OK', name,
                len(self.result['atlas_help_checks'])+1, ATLAS_HELP_REGION)
            self.result['atlas_help_checks'].append({'action': name, 'found': match is not None,
                'label': 'OK', 'evidence': stem, 'frame_sequence': sequence,
                'frame_generation': frame.generation, 'session_id': self.session, 'client_pid': events.client_pid})
            if kind == 'modal_clear':
                require(match is None, 'Atlas help dialog remained after three bounded rendered-button dismissals')
            elif match is not None:
                self.modal_position = match[:2]
                host.pointer_move(connection, *self.modal_position)
            else:
                self.modal_position = None
            return True
        if kind == 'optional_ocr_click':
            if self.modal_position is not None:
                host.pointer_click(connection, *self.modal_position)
            self.modal_position = None
            return True
        return False

    def proof_frames(self, name, event_generation, request_generation, frame, events, sequence, now):
        if self.ACTIONS[self.action][2] == 'wait_world_after_stuck':
            name = 'world_after_stuck_captures'
        return super().proof_frames(name, event_generation, request_generation, frame, events, sequence, now)

    def on_frame(self, connection, frame, events, sequence, captures, now):
        if self.ACTIONS[min(self.action, len(self.ACTIONS)-1)][0] == 'relocated' and events.relocated_generation == 0:
            require(self.stuck_delivered_at is not None and now-self.stuck_delivered_at < 180,
                    'Ordinary stuck recovery lacked native stable-position proof within 180 seconds')
        before = self.action
        super().on_frame(connection, frame, events, sequence, captures, now)
        if self.action != before and self.ACTIONS[before][2] == 'submit_ordinary_stuck':
            self.result['stuck_request'] = write_stuck_request(self.finish_path.parent/'character-relocation.json',
                self.session, events.client_pid, events.character_id)
            self.stuck_delivered_at = time.monotonic()


class ReopenEvents(character.CharacterEvents):
    def __init__(self, path, session):
        super().__init__(path, session)
        self.relocated_generation = 0

    def consume(self, event):
        if event.get('session_id') == self.session:
            if event.get('type') == 'character_connected':
                require(event.get('character_id') == 1 and type(event.get('baseline_character_id')) is int
                        and event['baseline_character_id'] == 1
                        and event.get('reopen_verified') is True and event.get('existing_character_verified') is True,
                        'Connected character differs from the persistent THORHERO baseline')
            elif event.get('type') == 'character_relocated':
                require(self.active and self.connected_generation == 1 and self.saved_generation == 0
                        and self.relocated_generation == 0 and type(event.get('client_pid')) is int
                        and event['client_pid'] == self.client_pid and event.get('character_id') == self.character_id == 1
                        and event.get('name') == 'THORHERO' and event.get('account') == 'COHLOCAL'
                        and type(event.get('map_id')) is int and event['map_id'] == 1
                        and all(event.get(name) is True for name in ('ordinary_stuck_observed',
                            'on_atlas_safe_position', 'stable_ground_verified')),
                        'Relocation event lacks current owned native stable-position evidence')
                self.relocated_generation = 1
                return
            elif event.get('type') == 'character_saved':
                require(self.relocated_generation == 1, 'Reopened character save preceded stable native relocation')
        super().consume(event)


def validate_world_supplement(report, manifest):
    world = host.assets_tool.world_tools()
    contract = world.bundle_contract()
    require(all(manifest.get('files', {}).get(name) == pin for name, pin in
            ((world.ARCHIVE, contract['archive_pin']), (world.MANIFEST, contract['manifest_pin']))),
            'World inputs differ from the reviewed exact APK package')
    # extract_apk_assets already verifies the complete world archive extracted
    # from this exact APK. Runtime checkouts only retain its committed metadata;
    # do not require a second copy of the ignored 200 MB source archive.
    pinned = world.read_manifest(host.ROOT/'assets'/world.MANIFEST)
    receipt = report.get('atlas_world_supplement')
    expected = {'format': 1, 'scope': contract['scope'],
        'manifest_sha256': contract['manifest_pin']['sha256'], 'archive_sha256': contract['archive_pin']['sha256'],
        'file_count': contract['file_count'], 'payload_bytes': contract['payload_bytes'],
        'verified_file_count': contract['file_count'], 'files_sha256': contract['files_sha256'],
        'normalized_mtime_epoch': 1767225600, 'imported_files_modified': False,
        'worktree_identity_modified': False, 'accepted_cache_archive_modified': False, 'runtime_visual_validated': False,
        'visual_scope': pinned['visual_scope']}
    require(isinstance(receipt, dict) and set(receipt) == set(expected) | {'installed_files', 'reused_files', 'worktree', 'cache_refresh'}
            and all(type(receipt.get(name)) is type(value) and receipt[name] == value for name, value in expected.items()),
            'Missing world installation identity or preservation receipt')
    require(all(type(receipt[name]) is int and 0 <= receipt[name] <= contract['file_count']
                for name in ('installed_files', 'reused_files'))
            and receipt['installed_files']+receipt['reused_files'] == contract['file_count'],
            'World installation count differs')
    worktree = report.get('client_worktree', {})
    identities = [worktree.get('import', {}).get('receipt_sha256'), worktree.get('package_sha256'),
                  worktree.get('cache_archive_sha256'), worktree.get('prerequisites_archive_sha256')]
    require(all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) for value in identities)
            and worktree.get('normalized_mtime_epoch') == expected['normalized_mtime_epoch'],
            'World supplement lost the accepted worktree input identity')
    key = hashlib.sha256((''.join(identities)+str(expected['normalized_mtime_epoch'])).encode()).hexdigest()[:24]
    require(receipt['worktree'] == 'client-work-'+key, 'World supplement was installed into another private tree')
    proof = report.get('character_reopen', report.get('character_creation', {}))
    require(proof.get('private_map_data', {}).get('source_worktree') == receipt['worktree']
            and proof['private_map_data'].get('imported_inputs_readonly') is True,
            'Owned MapServer did not mirror the supplemented private client tree')
    refresh = receipt['cache_refresh']
    require(isinstance(refresh, dict) and set(refresh) == {'policy', 'performed', 'removed_files', 'removed_bytes',
                'removed_inventory_sha256', 'accepted_cache_archive_modified'}
            and refresh.get('policy') == WORLD_CACHE_POLICY and refresh.get('accepted_cache_archive_modified') is False
            and type(refresh.get('performed')) is bool
            and type(refresh.get('removed_files')) is int and 0 <= refresh['removed_files'] <= 20000
            and type(refresh.get('removed_bytes')) is int and 0 <= refresh['removed_bytes'] <= 512*1024**2
            and isinstance(refresh.get('removed_inventory_sha256'), str)
            and re.fullmatch('[0-9a-f]{64}', refresh['removed_inventory_sha256']),
            'World private-cache refresh receipt is incomplete or unbounded')


def validate_report(report, session, manifest):
    require(report.get('scope') == 'actual_character_reopen_guest'
            and report.get('diagnostic_mode') == 'actual_character_reopen', 'Wrong reopen report scope')
    # Retain every creation-mode startup, current-client, ordinary logout,
    # committed SQL, owned process and asset identity check before adding reuse.
    common = copy.deepcopy(report)
    common.update(scope='actual_character_creation_guest', diagnostic_mode='actual_character_creation',
                  character_creation=report.get('character_reopen'))
    character.validate_report(common, session, manifest)
    validate_world_supplement(report, manifest)
    local = report['local_login']
    proof = report['character_reopen']
    baseline = proof.get('baseline', {})
    require(local.get('profile_reused') is True and local.get('character_count') == 1,
            'Reopening did not reuse the saved one-character profile')
    require(proof.get('character_id') == 1
            and all(type(proof.get(name)) is int and proof[name] == 1
                    for name in ('before_character_id', 'baseline_character_id', 'baseline_character_count'))
            and type(baseline.get('character_id')) is int and baseline['character_id'] == 1
            and type(baseline.get('auth_id')) is int and baseline['auth_id'] == proof.get('auth_id')
            and all(proof.get(name) is True for name in ('reopen_verified', 'existing_character_verified',
                'preserved_existing_identity', 'native_client_ready_observed', 'powers_preserved', 'costume_preserved',
                'selected_rows_preserved', 'ordinary_stuck_observed', 'on_atlas_safe_position',
                'stable_ground_verified', 'committed_safe_position_verified')),
            'Reopening lost the original character identity, powers, costume or native CLIENT_READY')
    require(type(baseline.get('login_count')) is int and baseline['login_count'] >= 1
            and type(proof.get('before_login_count')) is int and proof['before_login_count'] == baseline['login_count']
            and type(proof.get('login_count')) is int and proof['login_count'] == baseline['login_count']+1,
            'Character reopening did not increment the existing ordinary login count exactly once')
    for name in ('snapshot_sha256', 'identity_sha256'):
        require(isinstance(baseline.get(name), str) and re.fullmatch('[0-9a-f]{64}', baseline[name]),
                'Missing saved baseline identity: '+name)
    for table in ('powers', 'costumeparts'):
        require(proof.get('table_sha256', {}).get(table) == baseline.get('table_sha256', {}).get(table)
                and proof.get('row_counts', {}).get(table) == baseline.get('row_counts', {}).get(table),
                'Saved '+table+' differ from the pre-reopen baseline')


def validate_observer(observer, report):
    require(observer.get('failure') is None and observer.get('terminal_event_observed') is True
            and observer.get('client_pid') == report['client_launch']['pid'], 'Reopen observer did not complete')
    script = observer['interaction_script']
    checks = script.get('account_entry_checks', [])
    require(1 <= len(checks) <= character.ACCOUNT_ENTRY_ATTEMPTS
            and all(check.get('accepted') is False for check in checks[:-1])
            and checks[-1].get('accepted') is True
            and all(check.get('attempt') == index+1 and check.get('expected_account') == 'COHLOCAL'
                    and check.get('session_id') == report['session_id']
                    and check.get('client_pid') == observer['client_pid'] for index, check in enumerate(checks)),
            'Reopen login lacks exact rendered COHLOCAL evidence')
    names = [action[2] for action in ReopenInteraction.ACTIONS]
    retry_start, account_check = names.index('preposition_account'), names.index('verify_rendered_account')
    expected = names[:retry_start]+names[retry_start:account_check]*len(checks)+names[account_check:]
    require(script.get('script_completed') is True and [step['action'] for step in script['steps']] == expected
            and script.get('finish_request', {}).get('client_pid') == observer['client_pid']
            and len(script.get('ocr_buttons', [])) == 1 and script['ocr_buttons'][0].get('label') == 'THORHERO',
            'Existing-character UI script did not finish')
    modal = script.get('atlas_help_checks', [])
    require(len(modal) == 4 and modal[-1].get('found') is False
            and [check.get('action') for check in modal] == ['check_atlas_help_1', 'check_atlas_help_2',
                'check_atlas_help_3', 'verify_atlas_help_dismissed']
            and all(type(check.get('found')) is bool and check.get('session_id') == report['session_id']
                    and check.get('client_pid') == observer['client_pid'] and check.get('label') == 'OK' for check in modal),
            'Atlas help popup dismissal lacks bounded fresh rendered-button evidence')
    for field, action in (('stuck_request', 'stuck'), ('logout_request', 'quittologin')):
        receipt = script.get(field, {})
        require(set(receipt) == {'format', 'session_id', 'client_pid', 'character_id', 'action', 'sent_utc_ms'}
                and receipt['format'] == 1 and receipt['session_id'] == report['session_id']
                and receipt['client_pid'] == observer['client_pid'] and receipt['character_id'] == 1
                and receipt['action'] == action and type(receipt['sent_utc_ms']) is int and receipt['sent_utc_ms'] > 0,
                'Missing exact ordinary '+action+' delivery receipt')
    require(script['logout_request']['sent_utc_ms'] > script['stuck_request']['sent_utc_ms'],
            'Logout preceded ordinary stuck recovery delivery')
    for name in ('post_login_captures', 'connected_captures', 'world_after_stuck_captures', 'post_save_captures'):
        captures = script.get(name, [])
        require(len(captures) == 3 and len({item['frame_sequence'] for item in captures}) == 3
                and all(item['session_id'] == report['session_id'] and item['client_pid'] == observer['client_pid']
                        and item['proof_event_generation'] == 1 and item['width'] == 800 and item['height'] == 600
                        and item['frame_generation'] == captures[0]['frame_generation'] for item in captures)
                and captures[-1]['elapsed_since_ready']-captures[0]['elapsed_since_ready'] >= 2,
                'Missing fresh current-client reopen proof images: '+name)
    stuck = next(step['after_frame_sequence'] for step in script['steps'] if step['action'] == 'submit_ordinary_stuck')
    require(min(item['frame_sequence'] for item in script['world_after_stuck_captures']) > stuck,
            'World images preceded ordinary stuck command delivery')


def persistent_profile_identity(work):
    root = work/'state/diagnostic'
    directories = ('android-local-login', 'android-local-login/pgdata', 'wine')
    files = ('android-local-login/profile.json', 'android-local-login/pgdata/PG_VERSION', 'wine/.coh-wine-ready.json')
    result = {'directories': {}, 'files': {}}
    for name in directories:
        path = root/name
        require(path.is_dir() and not path.is_symlink(), 'Persistent restart directory is absent or linked')
        info = path.stat()
        result['directories'][name] = {'device': info.st_dev, 'inode': info.st_ino}
    for name in files:
        path = root/name
        require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 4096,
                'Persistent restart identity file is absent, linked or oversized')
        result['files'][name] = {'bytes': path.stat().st_size, 'sha256': host.digest(path)}
    require(json.loads((root/'android-local-login/profile.json').read_text()).get('initialized') is True,
            'Persistent restart profile was not initialized')
    require(not (root/'android-local-login/pgdata/postmaster.pid').exists(), 'PostgreSQL survived first-session cleanup')
    require(not (work/'socket/view.sock').exists(), 'First-session graphical display survived cleanup')
    return result


def reopen_command(command, previous_session, session):
    result = list(command)
    require(result.count('/opt/coh/character_creation_diagnostic.py') == 1
            and result.count(previous_session) == 1 and previous_session != session,
            'Reopen command does not describe exactly the prior guest session')
    result[result.index('/opt/coh/character_creation_diagnostic.py')] = '/opt/coh/character_reopen_diagnostic.py'
    result[result.index(previous_session)] = session
    return result


def reset_session_requests(state):
    # Remove only the successfully completed session's small delivery receipts.
    # Persistent profiles, game worktrees, SQL, reports and caches remain intact.
    removed = []
    for name in ('interaction-finish.json', 'character-logout.json', 'character-relocation.json', 'stop-request'):
        path = state/name
        require(not path.is_symlink(), 'Linked prior-session request refused')
        if path.exists():
            require(path.is_file() and path.stat().st_size <= 4096, 'Oversized prior-session request refused')
            path.unlink(); removed.append(name)
    return removed


def archive_completed_reports(state, session):
    destination = state/'completed-session-reports'/session
    require(not destination.exists() and not destination.is_symlink(), 'Completed-session archive is not fresh')
    destination.mkdir(mode=0o700, parents=True)
    for name, limit in (('latest-report.json', 2*1024*1024), ('report.zip', character.CHARACTER_EVIDENCE_LIMIT+4*1024*1024)):
        source = state/name
        require(source.is_file() and not source.is_symlink() and source.stat().st_size <= limit,
                'Completed creation report is absent, linked or oversized')
        if name == 'latest-report.json':
            require(json.loads(source.read_text()).get('session_id') == session,
                    'Completed creation report belongs to another session')
        source.rename(destination/name)
    return destination.relative_to(state).as_posix()


def validate_continuity(created, reopened, before, after):
    require(created['session_id'] != reopened['session_id'], 'Reopening reused the creation session identity')
    require(before == after, 'Persistent PostgreSQL or Wine profile was replaced between real sessions')
    saved = created['character_creation']
    proof = reopened['character_reopen']
    baseline = proof['baseline']
    require(saved['character_id'] == baseline['character_id'] == proof['character_id'] == 1
            and saved['auth_id'] == baseline['auth_id'] == proof['auth_id'],
            'Reopening did not select the character saved by the first graphical session')
    require(baseline['snapshot_sha256'] == saved['snapshot_sha256']
            and baseline['table_sha256'] == saved['table_sha256'] and baseline['row_counts'] == saved['row_counts'],
            'Pre-reopen SQL baseline differs from the real first-session committed save')
    require(created['cleanup_complete'] is True and all(created['cleanup'].values())
            and reopened['local_login']['profile_reused'] is True,
            'Reopening preceded owned first-session cleanup or replaced its profile')


def run_session(command, environment, work, evidence, session, manifest, deadline, reopening=False):
    evidence.mkdir(parents=True)
    process = observer = failure = report = None
    started = time.monotonic()
    with (evidence/'host-client.log').open('w') as log:
        try:
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            socket_path = work/'socket/view.sock'
            while not socket_path.exists():
                require(process.poll() is None and time.monotonic() < deadline, 'Guest exited before restart display socket')
                time.sleep(.1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(90); connection.connect(str(socket_path))
                observer = character.observe_rfb(connection, session, process, deadline, evidence,
                    evidence/'host-client.log', work/'state/interaction-finish.json',
                    ReopenInteraction if reopening else None, ReopenEvents if reopening else None)
            if reopening:
                observer['scope'] = 'host_external_unix_rfb_graphical_character_reopen'
            require(observer.get('failure') is None, observer.get('failure') or 'Graphical restart observer failed')
            require(process.wait(timeout=max(1, deadline-time.monotonic())) == 0, 'Restart guest exited unsuccessfully')
            report = json.loads((work/'state/latest-report.json').read_text())
            (validate_report if reopening else character.validate_report)(report, session, manifest)
            if not reopening:
                validate_world_supplement(report, manifest)
            (validate_observer if reopening else character.validate_observer)(observer, report)
            require(not socket_path.exists(), 'Private restart display socket survived cleanup')
        except Exception as error:
            failure = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            cleanup = character.stop_guest(process, work/'state')
            export = character.export_guest_evidence(work/'state', evidence, session)
            result = {'format': 1, 'status': 'failed' if failure else 'passed', 'session_id': session,
                'scope': 'host_existing_character_reopen' if reopening else 'host_graphical_character_creation_seed',
                'external_observer': observer, 'failure': failure, 'host_cleanup': cleanup,
                'guest_evidence_export': export, 'elapsed_seconds': round(time.monotonic()-started, 3)}
            (evidence/'host-session-report.json').write_text(json.dumps(result, indent=2)+'\n')
    return report, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('apk', 'build-report', 'proot', 'work', 'evidence', 'archive'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--startup-timeout-seconds', type=int, default=900, choices=range(120, 901))
    parser.add_argument('--interaction-seconds', type=int, default=INTERACTION_SECONDS, choices=(INTERACTION_SECONDS,))
    parser.add_argument('--timeout-seconds', type=int, default=OVERALL_SECONDS, choices=(OVERALL_SECONDS,))
    args = parser.parse_args()
    require(platform.machine().lower() in ('aarch64', 'arm64'), 'Native ARM64 Linux required')
    require(shutil.which('tesseract') is not None, 'Hosted graphical driver requires tesseract-ocr')
    require(not args.work.exists() and not args.work.is_symlink(), 'Fresh private restart work required')
    args.work = args.work.resolve(); args.proot = args.proot.resolve(); args.evidence = args.evidence.resolve()
    args.work.mkdir(parents=True); args.evidence.mkdir(parents=True, exist_ok=True)
    start = time.monotonic(); deadline = start+OVERALL_SECONDS
    sessions = []; failure = continuity = manifest = assets = None
    first_session, next_session = secrets.token_hex(16), secrets.token_hex(16)
    require(first_session != next_session, 'Fresh distinct restart sessions required')
    try:
        manifest, assets, imports = host.extract_apk_assets(args.apk, args.work/'apk-assets', args.build_report, args.repository_commit)
        data = host.import_game_data(imports, args.archive.resolve(), args.work, args.evidence)
        command, environment = character.make_command(args.work, assets, args.proot, first_session, data, args.startup_timeout_seconds)
        created, seed_result = run_session(command, environment, args.work, args.evidence/'creation', first_session, manifest, deadline)
        sessions.append(seed_result)
        before = persistent_profile_identity(args.work)
        prior_report_archive = archive_completed_reports(args.work/'state', first_session)
        removed = reset_session_requests(args.work/'state')
        require(time.monotonic() < deadline, 'Hosted qualification budget expired before reopening')
        restarted = reopen_command(command, first_session, next_session)
        reopened, reopen_result = run_session(restarted, environment, args.work, args.evidence/'reopen', next_session,
                                             manifest, deadline, reopening=True)
        sessions.append(reopen_result)
        after = persistent_profile_identity(args.work)
        validate_continuity(created, reopened, before, after)
        continuity = {'same_persistent_profile': True, 'fully_stopped_between_sessions': True,
            'same_character_id': 1, 'same_auth_id': created['character_creation']['auth_id'],
            'created_snapshot_sha256': created['character_creation']['snapshot_sha256'],
            'reopen_baseline_snapshot_sha256': reopened['character_reopen']['baseline']['snapshot_sha256'],
            'existing_powers_and_costume_preserved': True, 'prior_requests_removed': removed,
            'prior_report_archive': prior_report_archive,
            'profile_identity_before': before, 'profile_identity_after': after,
            'synthetic_character_rows': False, 'new_creation_requested_during_reopen': False}
    except Exception as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
        raise
    finally:
        result = {'format': 1, 'status': 'failed' if failure else 'passed',
            'scope': 'exact_apk_graphical_character_reopen_native_arm64', 'repository_commit': args.repository_commit,
            'apk_sha256': host.digest(args.apk),
            'runtime_manifest_sha256': host.digest(assets/'runtime-manifest.json') if assets else None,
            'creation_session_id': first_session, 'session_id': next_session, 'sessions': sessions,
            'persistent_reopen_continuity': continuity, 'failure': failure,
            'elapsed_seconds': round(time.monotonic()-start, 3), 'overall_timeout_seconds': OVERALL_SECONDS,
            'android_execution_validated': False, 'android_surface_validated': False,
            'character_reopen_visual_validated': False, 'atlas_scene_visual_validated': False,
            'collision_validated': False, 'gameplay_validated': False}
        (args.evidence/'host-client-report.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
