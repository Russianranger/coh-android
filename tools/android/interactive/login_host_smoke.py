#!/usr/bin/env python3
"""Qualify the exact local-login APK on native ARM64 with a private server."""
from __future__ import annotations
import argparse
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
    args = parser.parse_args()
    require(platform.machine().lower() in ('aarch64', 'arm64'), 'Native ARM64 Linux required')
    require(not args.work.exists(), 'Fresh private smoke work required')
    args.work = args.work.resolve(); args.proot = args.proot.resolve(); args.evidence = args.evidence.resolve()
    args.work.mkdir(parents=True); args.evidence.mkdir(parents=True, exist_ok=True)
    manifest, assets, imports = host.extract_apk_assets(args.apk, args.work/'apk-assets', args.build_report, args.repository_commit)
    data = host.import_game_data(imports, args.archive.resolve(), args.work, args.evidence)
    session = secrets.token_hex(16)
    command, environment = make_command(args.work, assets, args.proot, session, data, args.startup_timeout_seconds)
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
                'elapsed_seconds':round(time.monotonic()-start, 3), 'android_execution_validated':False,
                'android_surface_validated':False, 'character_selection_visual_validated':False, 'gameplay_validated':False}
            (args.evidence/'host-client-report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
