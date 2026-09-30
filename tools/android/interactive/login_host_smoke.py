#!/usr/bin/env python3
"""Qualify the exact local-login APK on native ARM64 with a private server."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import socket
import struct
import subprocess
import time

spec = importlib.util.spec_from_file_location('local_login_shared_host', Path(__file__).with_name('host_smoke.py'))
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)
require = host.require

# This small hosted driver uses only the APK's pinned guest modules and actual
# Wine/PE32 executables. It never manufactures a Wine readiness marker.
WARM_PREFIX_SEED = r'''
import json, os, platform, signal, sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, '/opt/coh')
import client_startup_diagnostic as startup
import presentation_diagnostic as presentation
base = startup.base
args = SimpleNamespace(state=Path('/state'), assets=Path('/opt/coh'),
    pg_bin=Path('/opt/coh/pgsql/bin'), wine=Path('/opt/wine/bin/wine'),
    wineserver=Path('/opt/wine/bin/wineserver'), xserver=Path('/usr/bin/Xtigervnc'),
    socket_dir=Path('/presentation-socket'), session_id=sys.argv[1])
os.umask(0o077)
context = base.Context(args.state, 690)
context.report.update(scope='host_real_wine_prefix_seed', session_id=args.session_id,
    postgres_started=False, server_started=False, client_process_started=False)
for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, lambda *_: setattr(context, 'cancel_requested', True))
diagnostic = None
try:
    base.require(platform.machine().lower() in ('aarch64', 'arm64') and os.geteuid() == 1000,
                 'Seed must execute in the accepted ARM64 guest identity')
    context.report['asset_sha256'] = startup.verify_assets(args.assets)
    base.arm64_elf(args.wine); base.arm64_elf(args.wineserver)
    base.require(not (args.state/'diagnostic/wine').exists(), 'Seed requires a genuinely fresh prefix')
    diagnostic = presentation.PresentationDiagnostic(args, context)
    diagnostic.start_wine()
    context.stage('win32_runtime_dll')
    result = context.run('runtime-probe', [args.wine, base.windows_path(args.assets/'runtime-probe.exe')],
                         timeout=60, env=diagnostic.wine_env)
    proof = base.validate_runtime_probe(result['output'])
    context.passed(**proof)
    diagnostic.mark_wine_ready()
    context.report.update(runtime_probe=proof, status='passed')
except Exception as error:
    context.report.update(status='failed', failures=[str(error)])
finally:
    if diagnostic is not None:
        try: context.report['failures'].extend(diagnostic.cleanup())
        except Exception as error: context.report['failures'].append('Seed cleanup failed: '+str(error))
    closed = all(c.process.poll() is not None and not c.reader.is_alive() and not c.writer.is_alive()
                 for c in context.children)
    context.report.update(cleanup_complete=closed,
        cleanup=diagnostic.cleanup_status if diagnostic else {},
        cleanup_execution={'diagnostic_initialized': diagnostic is not None,
            'wine_started': bool(diagnostic is not None and diagnostic.wine_started),
            'owned_child_count': len(context.children)})
    context.report['passed'] = (context.report['status'] == 'passed' and not context.report['failures']
        and diagnostic is not None and diagnostic.wine_initialization['state'] == 'ready'
        and closed and all(context.report['cleanup'].values()))
    base.private_write(args.state/'warm-prefix-seed.json', json.dumps(context.report, indent=2)+'\n')
sys.exit(0 if context.report['passed'] else 1)
'''


def verify_prefix_seed(report, session, manifest):
    require(report.get('scope') == 'host_real_wine_prefix_seed' and report.get('session_id') == session
        and report.get('status') == 'passed' and report.get('passed') is True and report.get('failures') == [],
        'Real Wine prefix seed did not complete')
    require(report.get('asset_sha256') == {name: manifest['files'][name]['sha256']
        for name in host.assets_tool.PROBE_FILES}, 'Seed APK input hashes differ')
    initialization = report.get('wine_initialization', {})
    require(initialization.get('state') == 'ready' and initialization.get('ready_prefix_reused') is False
        and tuple(initialization.get(k) for k in ('registration_processes', 'wow64_registration_processes',
            'registration_passes')) == (3, 1, 1), 'Seed did not perform real initial Wine registration')
    require(report.get('runtime_probe') == {'pointer_bits': 32, 'dll_export_verified': True,
        'odbc_manager_loaded': True}, 'Seed lacks actual PE32/DLL proof')
    children = report.get('processes', [])
    probes = [child for child in children if child.get('label') == 'runtime-probe']
    require(len(probes) == 1 and probes[0].get('exit_code') == 0
        and probes[0].get('output', '').splitlines().count('COH_RUNTIME_PROBE_V1 PASS bits=32 dll=verified') == 1,
        'Seed must retain successful real runtime-probe output')
    require(report.get('postgres_started') is False and report.get('server_started') is False
        and report.get('client_process_started') is False, 'Prefix seed exceeded its scope')
    require(report.get('cleanup_complete') is True and len(children) >= 5
        and all(type(child.get('exit_code')) is int and child.get('input_closed') is True
            and child.get('output_capture_closed') is True for child in children)
        and report.get('cleanup_execution') == {'diagnostic_initialized': True,
            'wine_started': True, 'owned_child_count': len(children)}
        and report.get('cleanup', {}).get('wine_prefix_stopped') is True
        and report.get('cleanup', {}).get('owned_processes_reaped') is True
        and report.get('wine_process_cleanup', {}).get('complete') is True
        and report.get('wine_process_cleanup', {}).get('remaining') == 0
        and report.get('wine_process_cleanup', {}).get('inspection_failures') == 0
        and report.get('presentation_socket_removed') is True,
        'Seed owned-process cleanup was not proved')


def stage_stale_prefix(work, manifest, report, session):
    """Change one timestamp only after a real, closed, current-APK seed passed."""
    verify_prefix_seed(report, session, manifest)
    prefix = work/'state/diagnostic/wine'
    marker = prefix/'.coh-wine-ready.json'
    timestamp = prefix/'.update-timestamp'
    wine_inf = work/'wine/share/wine/wine.inf'
    require(prefix.is_dir() and not prefix.is_symlink() and all(path.is_file() and not path.is_symlink()
        for path in (marker, timestamp, wine_inf)), 'Seed prefix identity files are missing or linked')
    identity = {'format': 1, 'purpose': 'coh-wine-initialization',
        'runtime_lock_sha256': manifest['files']['runtime-lock.json']['sha256']}
    require(marker.stat().st_size <= 4096 and json.loads(marker.read_text()) == identity,
        'Real seed did not publish the expected Wine readiness marker')
    require(timestamp.stat().st_size <= 128 and re.fullmatch(r'[0-9]+\n?', timestamp.read_text()),
        'Seed Wine timestamp is not decimal')
    current = int(wine_inf.stat().st_mtime)
    require(current > 1 and int(timestamp.read_text()) == current, 'Real seed timestamp differs from installed wine.inf')
    sentinel = prefix/'.coh-host-prefix-retained'
    require(not sentinel.exists() and not sentinel.is_symlink(), 'Host preservation sentinel already exists')
    sentinel.write_text(session+'\n'); sentinel.chmod(0o600)
    before = prefix.stat()
    timestamp.write_text(str(current-1)+'\n')
    return {'mode': 'real_prefix_then_stale_wine_inf_timestamp', 'session_id': session,
        'prefix_device': before.st_dev, 'prefix_inode': before.st_ino,
        'prefix_sentinel_sha256': host.digest(sentinel), 'ready_marker_sha256': host.digest(marker),
        'wine_inf_sha256': host.digest(wine_inf), 'wine_inf_mtime': current,
        'timestamp_before': current, 'timestamp_staged': current-1,
        'seed_driver_sha256': hashlib.sha256(WARM_PREFIX_SEED.encode()).hexdigest()}


def prepare_warm_prefix(command, environment, work, evidence, manifest, session):
    start = command.index('/usr/bin/python3')
    seed_command = command[:start]+['/usr/bin/python3', '-c', WARM_PREFIX_SEED, session]
    process = None
    try:
        with (evidence/'warm-prefix-seed.log').open('w') as log:
            process = subprocess.Popen(seed_command, env=environment, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
            code = process.wait(timeout=720)
        require(code == 0, 'Real Wine prefix preparation failed')
        report = host.assets_tool.read_json(work/'state/warm-prefix-seed.json')
        require(not (work/'socket/view.sock').exists(), 'Seed display socket survived cleanup')
        receipt = stage_stale_prefix(work, manifest, report, session)
        (evidence/'warm-prefix-refresh.json').write_text(json.dumps(receipt, indent=2)+'\n')
        return receipt
    finally:
        if process is not None and process.poll() is None:
            (work/'state/stop-request').write_text('stop\n')
            try: process.wait(timeout=35)
            except subprocess.TimeoutExpired:
                process.send_signal(signal.SIGQUIT)
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        source = work/'state/warm-prefix-seed.json'
        if source.is_file(): shutil.copyfile(source, evidence/source.name)


def verify_warm_refresh(work, receipt, report):
    initialization = report.get('wine_initialization', {})
    require(initialization.get('state') == 'ready' and initialization.get('prior_ready_prefix') is True
        and initialization.get('ready_prefix_reused') is False
        and initialization.get('refresh_reason') == 'wine_inf_timestamp_changed'
        and initialization.get('existing_prefix_preserved') is True
        and initialization.get('registration_timestamp_verified') is True
        and initialization.get('update_timestamp_content_before') == receipt['timestamp_staged']
        and initialization.get('update_timestamp_content_after') == receipt['wine_inf_mtime']
        and tuple(initialization.get(k) for k in ('registration_processes', 'wow64_registration_processes',
            'registration_passes')) == (3, 1, 1), 'Existing prefix did not execute the required real Wine refresh')
    prefix = work/'state/diagnostic/wine'
    require(prefix.is_dir() and not prefix.is_symlink() and all((prefix/name).is_file()
        and not (prefix/name).is_symlink() for name in ('.coh-host-prefix-retained', '.coh-wine-ready.json', '.update-timestamp')),
        'Existing prefix evidence became linked or missing')
    current = prefix.stat()
    require(current.st_dev == receipt['prefix_device'] and current.st_ino == receipt['prefix_inode']
        and host.digest(prefix/'.coh-host-prefix-retained') == receipt['prefix_sentinel_sha256']
        and host.digest(prefix/'.coh-wine-ready.json') == receipt['ready_marker_sha256']
        and int((prefix/'.update-timestamp').read_text()) == receipt['wine_inf_mtime'],
        'Existing Wine prefix was replaced or readiness was not restored')
    wine_inf = work/'wine/share/wine/wine.inf'
    require(int(wine_inf.stat().st_mtime) == receipt['wine_inf_mtime']
        and host.digest(wine_inf) == receipt['wine_inf_sha256'], 'Installed Wine initialization source changed')
    return dict(receipt, refresh_validated=True, prefix_retained=True, actual_registration_counts=[3, 1, 1])


def replace_field(connection, value):
    require(value in ('COHLOCAL', 'offline'), 'Unexpected local-login fixture')
    def key(code, down): connection.sendall(struct.pack('!BBHI', 4, down, 0, code))
    key(0xffe3, 1); key(ord('a'), 1); key(ord('a'), 0); key(0xffe3, 0)
    time.sleep(.12)
    for character in value:
        key(ord(character), 1); time.sleep(.03)
        key(ord(character), 0); time.sleep(.03)


class LoginInteraction(host.MenuInteraction):
    """Fixed local account; server proof and pixels remain separate evidence."""
    ACTIONS = (
        ('move', (400, 403), 'preposition_graphics_cancel'),
        ('click', (400, 403), 'cancel_graphics_prompt'),
        ('move', (635, 430), 'preposition_settings'),
        ('click', (635, 430), 'open_settings'),
        ('move', (433, 70), 'preposition_settings_close'),
        ('click', (433, 70), 'close_settings_x'),
        ('escape', None, 'press_b_escape'),
        ('restore', None, 'observe_login_after_settings'),
        ('move', (625, 240), 'preposition_account'),
        ('click', (625, 240), 'focus_account'),
        ('text', 'COHLOCAL', 'replace_account'),
        ('move', (625, 328), 'preposition_password'),
        ('click', (625, 328), 'focus_password'),
        ('text', 'offline', 'replace_dummy_password'),
        ('move', (704, 379), 'preposition_login'),
        ('click', (704, 379), 'submit_local_login'),
        ('move', (644, 219), 'preposition_local_server'),
        ('click', (644, 219), 'select_local_server'),
    )

    def __init__(self, session, evidence, finish_path):
        super().__init__(session, evidence, finish_path)
        self.result.update(scope='host_local_login_input_and_post_response_capture', account='COHLOCAL',
            character_selection_visual_validated=False, post_login_captures=[])
        self.result.pop('test_marker')
        self.last_login_capture = None
        self.login_reference = None
        self.restored_frames = 0

    @staticmethod
    def login_panel(pixels):
        # Settings covers the left side; sampling only the account fields on
        # the right would mistake an open Settings window for recovery.
        regions = ((15, 420, 90, 350), (590, 770, 190, 355))
        return bytes(channel for left, right, top, bottom in regions
                     for y in range(top, bottom, 8) for x in range(left, right, 8)
                     for channel in pixels[(y*800+x)*4:(y*800+x)*4+3])

    def on_frame(self, connection, frame, events, sequence, captures, now):
        if self.ready_at is None: self.ready_at = now
        require(now-self.ready_at < 180, 'Host local login exceeded the existing interaction bound')
        if len(captures) < 3 or (frame.width, frame.height) != (800, 600): return
        if self.action:
            require(frame.generation == self.frame_generation, 'Client resized during local login')
            if sequence <= self.watermark: return
            self.watermark = sequence
            self.fresh_frames += 1
            required_frames = 2 if self.action < len(self.ACTIONS) and self.ACTIONS[self.action][0] == 'click' else 1
            # The login screen switches to the one-row shard list locally.
            delay = 3 if self.action < len(self.ACTIONS) and self.ACTIONS[self.action][2] == 'preposition_local_server' else 1
            if self.fresh_frames < required_frames or now-self.last_action_at < delay: return
        if self.action < len(self.ACTIONS):
            kind, value, name = self.ACTIONS[self.action]
            if name == 'preposition_settings': self.login_reference = self.login_panel(frame.pixels)
            if kind == 'restore':
                panel = self.login_panel(frame.pixels)
                difference = sum(abs(a-b) for a,b in zip(panel, self.login_reference))/len(panel)
                self.restored_frames = self.restored_frames+1 if difference <= 8 else 0
                if self.restored_frames < 3: return
                self.result['settings_recovery'] = {'panel_mean_absolute_difference':difference,
                    'fresh_restored_frames':self.restored_frames, 'visual_review_pending':True}
            if name in ('preposition_graphics_cancel', 'preposition_settings', 'preposition_settings_close',
                        'observe_login_after_settings', 'preposition_password', 'preposition_login',
                        'preposition_local_server', 'select_local_server'):
                self.capture('login-before-'+name, frame, events, sequence, now)
            if kind == 'move': host.pointer_move(connection, *value)
            elif kind == 'click': host.pointer_click(connection, *value)
            elif kind == 'text': replace_field(connection, value)
            elif kind == 'escape':
                connection.sendall(struct.pack('!BBHI', 4, 1, 0, 0xff1b)); time.sleep(.12)
                connection.sendall(struct.pack('!BBHI', 4, 0, 0, 0xff1b))
            self.result['steps'].append({'action':name, 'session_id':self.session, 'client_pid':events.client_pid,
                'after_frame_sequence':sequence, 'fresh_frames_since_previous_action':self.fresh_frames,
                'elapsed_since_ready':round(now-self.ready_at, 3)})
            self.action += 1
            self.last_action_at = time.monotonic()
            self.fresh_frames = 0
            self.watermark = sequence
            self.frame_generation = frame.generation
            return
        # A frame already requested before the login event cannot qualify.
        if events.login_generation != 1 or frame.request_login_generation != 1: return
        if self.last_login_capture is not None and now-self.last_login_capture < 1: return
        colors = {bytes(frame.pixels[i:i+3]) for i in range(0, min(len(frame.pixels), 800*600*4), 4)}
        if len(colors) < 8: return
        post = self.result['post_login_captures']
        if len(post) < 3:
            self.capture('login-character-list-%03d' % len(post), frame, events, sequence, now)
            post.append(dict(self.result['screenshots'][-1], login_event_generation=events.login_generation,
                             distinct_colors_capped=min(len(colors), 8)))
            self.last_login_capture = now
        if len(post) == 3 and now-self.ready_at >= 30 and 'finish_request' not in self.result:
            self.result['script_completed'] = True
            self.result['finish_request'] = host.write_finish_request(self.finish_path, self.session, events.client_pid)


def make_command(work, assets, proot, session, data, startup_timeout_seconds=900):
    command, environment = host.make_command(work, assets, proot, session, data, startup_timeout_seconds)
    command[command.index('/opt/coh/client_interactive_diagnostic.py')] = '/opt/coh/client_login_diagnostic.py'
    hostname = socket.gethostname()
    require(len(hostname) <= 253 and all(re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
        for label in hostname.split('.')), 'Unsafe host hostname')
    hosts = work/'hosts'
    hosts.write_text('127.0.0.1 '+' '.join(dict.fromkeys(('localhost', hostname, hostname.split('.')[0])))+'\n')
    where = command.index('-w'); command[where:where] = ['-b', str(hosts)+':/etc/hosts']
    command += ['--profile', 'android-local-login']
    return command, environment


def validate_report(report, session, manifest):
    host.validate_report(report, session, manifest, local_login=True)
    login = report.get('local_login', {})
    require(login.get('session_id') == session and login.get('client_pid') == report['client_launch']['pid']
        and login.get('profile') == 'android-local-login' and login.get('account') == 'COHLOCAL'
        and login.get('character_count') == 0 and login.get('server_ready') is True
        and login.get('local_account_verified') is True and login.get('local_login_verified') is True
        and login.get('character_list_sent') is True and login.get('character_list_response_sent') is True
        and login.get('database_preserved') is True and login.get('character_selection_visual_validated') is False,
        'Missing current-session local login, empty character list, or persistent profile proof')
    require(report.get('mapserver_started') is False and login.get('mapserver_started') is False
        and report.get('cleanup', {}).get('postgres_graceful') is True, 'Server scope or PostgreSQL cleanup differs')
    children = report.get('processes', [])
    require(len([p for p in children if p.get('label') == 'local-dbserver']) == 1,
        'Missing unique owned local DbServer')


def validate_observer(observer, report):
    require(observer.get('failure') is None and observer.get('terminal_event_observed') is True,
            observer.get('failure') or 'Missing external observer completion')
    require(observer['client_pid'] == report['client_launch']['pid'], 'External observer client identity differs')
    captures = observer['post_startup_captures']
    require(len(captures) == 3 and captures[-1]['elapsed_seconds']-captures[0]['elapsed_seconds'] >= 2,
        'Missing three fresh startup frames')
    script = observer['interaction_script']; post = script.get('post_login_captures', [])
    require(script.get('script_completed') is True and len(script['steps']) == len(LoginInteraction.ACTIONS)
        and script.get('settings_recovery', {}).get('fresh_restored_frames', 0) >= 3
        and script.get('finish_request', {}).get('client_pid') == observer['client_pid']
        and report.get('interaction_completion_reason') == 'finish_requested', 'Local login script did not finish')
    require(len(post) == 3 and all(p['session_id'] == report['session_id']
        and p['client_pid'] == observer['client_pid'] and p['login_event_generation'] == 1
        and p['width'] == 800 and p['height'] == 600 and p['frame_generation'] == post[0]['frame_generation'] for p in post)
        and len({p['frame_sequence'] for p in post}) == 3
        and post[-1]['elapsed_since_ready']-post[0]['elapsed_since_ready'] >= 2,
        'Missing three fresh current-client post-response images')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('apk', 'build-report', 'proot', 'work', 'evidence', 'archive'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    parser.add_argument('--startup-timeout-seconds', type=int, default=900, choices=range(120, 901))
    parser.add_argument('--warm-prefix-refresh', action='store_true',
        help='Seed a real qualified Wine prefix, then exercise refresh from a stale wine.inf timestamp')
    args = parser.parse_args()
    require(platform.machine().lower() in ('aarch64', 'arm64'), 'Native ARM64 Linux required')
    require(not args.work.exists(), 'Fresh private smoke work required')
    args.work = args.work.resolve(); args.proot = args.proot.resolve(); args.evidence = args.evidence.resolve()
    args.work.mkdir(parents=True); args.evidence.mkdir(parents=True, exist_ok=True)
    manifest, assets, imports = host.extract_apk_assets(args.apk, args.work/'apk-assets', args.build_report, args.repository_commit)
    data = host.import_game_data(imports, args.archive.resolve(), args.work, args.evidence)
    session = secrets.token_hex(16)
    command, environment = make_command(args.work, assets, args.proot, session, data, args.startup_timeout_seconds)
    warm_prefix = prepare_warm_prefix(command, environment, args.work, args.evidence, manifest, session) \
        if args.warm_prefix_refresh else None
    start = time.monotonic(); deadline = start+1860; observer = failure = process = None
    with (args.evidence/'host-client.log').open('w') as log:
        try:
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            socket_path = args.work/'socket/view.sock'
            while not socket_path.exists():
                require(process.poll() is None and time.monotonic() < deadline, 'Guest exited before display socket')
                time.sleep(.1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(90); connection.connect(str(socket_path))
                observer = host.observe_rfb(connection, session, process, deadline, args.evidence,
                    args.evidence/'host-client.log', args.work/'state/interaction-finish.json', LoginInteraction)
            require(observer.get('failure') is None, observer.get('failure') or 'Local login observer failed')
            code = process.wait(timeout=max(1, deadline-time.monotonic()))
            require(code == 0, 'Local login guest exited unsuccessfully')
            report = json.loads((args.work/'state/latest-report.json').read_text())
            validate_report(report, session, manifest); validate_observer(observer, report)
            if warm_prefix is not None:
                warm_prefix = verify_warm_refresh(args.work, warm_prefix, report)
                (args.evidence/'warm-prefix-refresh.json').write_text(json.dumps(warm_prefix, indent=2)+'\n')
            require(not socket_path.exists(), 'Private display socket survived cleanup')
        except Exception as error:
            failure = {'type':type(error).__name__, 'message':str(error)}
            raise
        finally:
            if process is not None and process.poll() is None:
                (args.work/'state/stop-request').write_text('stop\n')
                try: process.wait(timeout=35)
                except subprocess.TimeoutExpired:
                    process.send_signal(signal.SIGQUIT)
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
            for name in ('latest-report.json', 'report.zip'):
                source = args.work/'state'/name
                if source.is_file(): shutil.copyfile(source, args.evidence/name)
            result = {'format':1, 'status':'failed' if failure else 'passed',
                'scope':'exact_apk_actual_client_local_login_native_arm64', 'repository_commit':args.repository_commit,
                'apk_sha256':host.digest(args.apk), 'runtime_manifest_sha256':host.digest(assets/'runtime-manifest.json'),
                'session_id':session, 'external_observer':observer, 'failure':failure,
                'warm_prefix_refresh':warm_prefix,
                'elapsed_seconds':round(time.monotonic()-start, 3), 'android_execution_validated':False,
                'android_surface_validated':False, 'character_selection_visual_validated':False, 'gameplay_validated':False}
            (args.evidence/'host-client-report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
