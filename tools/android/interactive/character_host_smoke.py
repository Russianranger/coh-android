#!/usr/bin/env python3
"""Qualify graphical THORHERO creation and an ordinary, committed logout save."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.util
import io
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

spec = importlib.util.spec_from_file_location('character_login_host', Path(__file__).with_name('login_host_smoke.py'))
login = importlib.util.module_from_spec(spec)
spec.loader.exec_module(login)
host = login.host
require = host.require
INTERACTION_SECONDS = 1200
LOGIN_STAGE_SECONDS = 180
OVERALL_SECONDS = 5400
CLEANUP_GRACE_SECONDS = 180
CHARACTER_EVIDENCE_LIMIT = 256*1024*1024
CHARACTER = 'THORHERO'


class CharacterEvents:
    """Keep packet/SQL evidence separate from pixels and input delivery."""
    def __init__(self, path, session):
        self.path, self.session = path, session
        self.offset = 0
        self.pending = b''
        self.generation = self.login_generation = self.connected_generation = self.saved_generation = 0
        self.client_pid = self.character_id = None
        self.active = self.terminal = False

    def poll(self):
        with self.path.open('rb') as source:
            source.seek(self.offset)
            data = source.read(131072)
        self.offset += len(data)
        require(self.offset <= 2*1024*1024, 'Host guest-event stream exceeds bound')
        lines = (self.pending+data).split(b'\n')
        self.pending = lines.pop()
        require(len(self.pending) <= 65536, 'Host guest-event line exceeds bound')
        for line in lines:
            require(len(line) <= 65536, 'Host guest-event line exceeds bound')
            try: event = json.loads(line)
            except (ValueError, UnicodeDecodeError): continue
            if not isinstance(event, dict): continue
            kind = event.get('type')
            if kind == 'stage' and event.get('stage') == 'actual_client_interaction' and event.get('status') == 'passed':
                require(self.saved_generation == 1, 'Character completion preceded committed save')
                self.active = False
                self.terminal = True
                continue
            if event.get('session_id') != self.session: continue
            if kind == 'client_interaction_ready':
                pid = event.get('client_pid')
                require(type(pid) is int and pid > 0 and self.generation == 0 and not self.terminal,
                        'Invalid or repeated character client readiness')
                self.client_pid = pid
                self.generation = 1
                self.active = True
            elif kind in ('client_login_ready', 'character_connected', 'character_saved'):
                require(self.active and type(event.get('client_pid')) is int
                        and event['client_pid'] == self.client_pid,
                        'Character event client identity differs or followed completion')
                if kind == 'client_login_ready':
                    require(self.login_generation == 0 and event.get('character_list_sent') is True,
                            'Invalid or repeated local login event')
                    self.login_generation = 1
                elif kind == 'character_connected':
                    require(self.login_generation == 1 and self.connected_generation == 0
                            and event.get('name') == CHARACTER and event.get('account') == 'COHLOCAL'
                            and type(event.get('character_id')) is int and event['character_id'] > 0
                            and type(event.get('map_id')) is int and event['map_id'] == 1,
                            'Invalid or repeated connected character event')
                    self.character_id = event['character_id']
                    self.connected_generation = 1
                else:
                    require(self.connected_generation == 1 and self.saved_generation == 0
                            and event.get('name') == CHARACTER
                            and type(event.get('character_id')) is int and event['character_id'] == self.character_id
                            and event.get('committed_sql_verified') is True,
                            'Invalid or repeated committed character save event')
                    self.saved_generation = 1


def key(connection, code):
    connection.sendall(struct.pack('!BBHI', 4, 1, 0, code))
    time.sleep(.12)
    connection.sendall(struct.pack('!BBHI', 4, 0, 0, code))


def fixed_text(connection, value, replace=False):
    require(value in ('COHLOCAL', 'offline', CHARACTER, '/quittologin'), 'Unexpected graphical fixture text')
    if replace:
        connection.sendall(struct.pack('!BBHI', 4, 1, 0, 0xffe3))
        key(connection, ord('a'))
        connection.sendall(struct.pack('!BBHI', 4, 0, 0, 0xffe3))
        time.sleep(.12)
    for character in value:
        key(connection, ord(character))
        time.sleep(.03)


def write_logout_request(path, session, client_pid, character_id):
    """Publish only after the real command's final Return release was sent."""
    require(re.fullmatch(r'[0-9a-f]{32}', session) and type(client_pid) is int and client_pid > 0
            and type(character_id) is int and character_id > 0, 'Logout request identity differs')
    require(path.parent.is_dir() and not path.parent.is_symlink() and not path.exists() and not path.is_symlink(),
            'Logout request destination is not fresh and private')
    value = {'format': 1, 'session_id': session, 'client_pid': client_pid, 'character_id': character_id,
             'action': 'quittologin', 'sent_utc_ms': int(time.time()*1000)}
    payload = (json.dumps(value, sort_keys=True)+'\n').encode()
    temporary = path.with_name(path.name+'.tmp-'+secrets.token_hex(8))
    try:
        with temporary.open('xb') as output:
            os.chmod(temporary, 0o600)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return value


def ocr_button(tsv, label, region, scale=3, offset=(0, 0)):
    """Find a literal rendered button label; never infer progress from color."""
    left, top, right, bottom = region
    matches = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
        try:
            text = row['text'].strip().strip('.,:;!?[](){}<>|').casefold()
            x = offset[0] + (int(row['left'])+int(row['width'])/2)/scale
            y = offset[1] + (int(row['top'])+int(row['height'])/2)/scale
            confidence = float(row['conf'])
        except (KeyError, TypeError, ValueError): continue
        if text == label.casefold() and confidence >= 20 and left <= x <= right and top <= y <= bottom:
            matches.append((round(x), round(y), confidence))
    # Dialog prose can contain the same word. Buttons occupy the lowest row.
    return max(matches, key=lambda item: item[1]) if matches else None


def read_button(frame, evidence, label, step, attempt, region):
    require(shutil.which('tesseract') is not None, 'Hosted graphical driver requires tesseract-ocr')
    from PIL import Image
    # Enlarge and threshold the rendered light text for small outlined game
    # fonts. Retain the original color PNG for actual visual inspection.
    scale = 3
    pixels = frame.pixels
    left, top, right, bottom = region
    require(all(type(value) is int for value in region) and 0 <= left < right <= frame.width
            and 0 <= top < bottom <= frame.height, 'OCR region is outside the actual framebuffer')
    stem = '%s-ocr-%02d' % (step, attempt)
    host.save_png(evidence/(stem+'.png'), pixels)
    rendered = Image.frombytes('RGB', (frame.width, frame.height), bytes(pixels), 'raw', 'BGRX')
    rendered = rendered.crop(region)
    text = rendered.point(lambda value: 255 if value > 100 else 0).convert('L').point(lambda value: 0 if value > 225 else 255)
    text = text.resize(((right-left)*scale, (bottom-top)*scale), Image.Resampling.BICUBIC)
    ppm = io.BytesIO()
    text.save(ppm, format='PPM')
    # Bound OCR CPU use and image size while the client and MapServer share the
    # runner; a full upscaled frame previously exceeded the OCR deadline.
    environment = dict(os.environ, OMP_THREAD_LIMIT='1', OMP_NUM_THREADS='1')
    (evidence/(stem+'.json')).write_text(json.dumps({'region': list(region), 'scale': scale,
        'ocr_width': text.width, 'ocr_height': text.height, 'omp_threads': 1, 'timeout_seconds': 30})+'\n')
    result = subprocess.run(['tesseract', 'stdin', 'stdout', '--psm', '11', 'tsv'], input=ppm.getvalue(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True, env=environment)
    require(len(result.stdout) <= 1024*1024, 'OCR text exceeds bounded frame evidence')
    tsv = result.stdout.decode('utf-8')
    (evidence/(stem+'.tsv')).write_text(tsv)
    match = ocr_button(tsv, label, region, scale=scale, offset=(left, top))
    return match, stem


def click_steps(name, x, y):
    return [('move', (x, y), 'preposition_'+name), ('click', (x, y), name)]


def creation_actions():
    # Coordinates are 800x600 projections of the pinned Hybrid UI's 1024x768
    # layout. Confirm the retained images during hosted qualification.
    actions = [('login', None, 'wait_character_list')]
    actions += click_steps('open_character_creator', 200, 72)
    actions += click_steps('select_primal_earth', 190, 137)
    actions += click_steps('select_science_origin', 170, 328)
    actions += click_steps('focus_character_name', 390, 561)
    actions += [('text', CHARACTER, 'enter_character_name')]
    actions += click_steps('origin_next', 757, 579)
    actions += click_steps('select_ranged_playstyle', 170, 191)
    actions += click_steps('playstyle_next', 757, 579)
    # classes.def starts with Blaster; ranged filtering retains source order.
    actions += click_steps('select_blaster', 180, 102)
    actions += click_steps('archetype_next', 757, 579)
    actions += click_steps('select_primary_set', 200, 148)
    actions += click_steps('select_primary_power', 620, 148)
    actions += click_steps('choose_secondary', 757, 579)
    actions += click_steps('select_secondary_set', 200, 148)
    actions += click_steps('powers_next', 757, 579)
    actions += click_steps('select_male_body', 82, 195)
    actions += click_steps('body_next', 757, 579)
    # Costume entry chooses a random preset. The ordinary Clear button calls
    # resetCostume(0), restoring the pinned basic pieces without another dialog.
    actions += click_steps('clear_random_costume', 211, 555)
    actions += click_steps('accept_default_costume', 757, 579)
    actions += click_steps('accept_default_power_colors', 757, 579)
    actions += click_steps('register_play', 757, 579)
    for label, name in (('No', 'skip_tutorial'), ('Hero', 'choose_hero'), ('Yes', 'confirm_creation')):
        # Hero's old button position overlaps the following Yes label. Park
        # outside the dialog and obtain a fresh settled frame before reading it.
        actions += [('move', (600, 100), 'clear_cursor_before_'+name),
                    ('ocr_move', (label, (220, 230, 580, 465)), 'preposition_'+name),
                    ('ocr_click', None, name)]
    actions += [('connected', None, 'wait_atlas_connection'),
                ('key', 0xff0d, 'open_chat'), ('command', '/quittologin', 'type_ordinary_logout'),
                ('key', 0xff0d, 'submit_ordinary_logout'), ('saved', None, 'wait_committed_save')]
    return tuple(actions)


class CharacterInteraction(host.MenuInteraction):
    # The separate login qualification covers Settings recovery. Enter the
    # character milestone through ordinary login without opening that optional
    # window (uiLogin.c only opens it in the Settings button handler).
    LOGIN_ACTIONS = tuple(action for action in login.LoginInteraction.ACTIONS if action[2] not in {
        'preposition_settings', 'open_settings', 'preposition_settings_close', 'close_settings_x',
        'press_b_escape', 'observe_login_after_settings'})
    ACTIONS = LOGIN_ACTIONS + creation_actions()

    def __init__(self, session, evidence, finish_path):
        super().__init__(session, evidence, finish_path)
        self.result.pop('test_marker')
        self.result.update(scope='host_graphical_character_creation_and_ordinary_logout', account='COHLOCAL',
            character_name=CHARACTER, character_creation_visual_validated=False,
            post_login_captures=[], connected_captures=[], post_save_captures=[], ocr_buttons=[])
        self.ocr_position = None
        self.ocr_attempts = 0
        self.last_ocr_at = 0
        self.last_proof_capture = {}

    def proof_frames(self, name, event_generation, request_generation, frame, events, sequence, now):
        if event_generation != 1 or request_generation != 1: return False
        captures = self.result[name]
        if len(captures) == 3: return True
        if name in self.last_proof_capture and now-self.last_proof_capture[name] < 1: return False
        self.capture(name+'-%03d' % len(captures), frame, events, sequence, now)
        captures.append(dict(self.result['screenshots'][-1], proof_event_generation=event_generation))
        self.last_proof_capture[name] = now
        return len(captures) == 3

    def on_frame(self, connection, frame, events, sequence, captures, now):
        if self.ready_at is None: self.ready_at = now
        require(now-self.ready_at < INTERACTION_SECONDS, 'Host character creation exceeded twenty-minute interaction bound')
        if self.action <= len(self.LOGIN_ACTIONS):
            require(now-self.ready_at < LOGIN_STAGE_SECONDS,
                    'Host character login exceeded 180-second stage bound before fresh character-list proof')
        if len(captures) < 3 or (frame.width, frame.height) != (800, 600): return
        if self.action:
            require(frame.generation == self.frame_generation, 'Client resized during graphical character creation')
            if sequence <= self.watermark: return
            self.watermark = sequence
            self.fresh_frames += 1
            required = 2 if self.action < len(self.ACTIONS) and self.ACTIONS[self.action][0] in ('click', 'ocr_click') else 1
            if self.fresh_frames < required or now-self.last_action_at < 2: return
        if self.action == len(self.ACTIONS):
            if 'finish_request' not in self.result:
                self.result['script_completed'] = True
                self.result['finish_request'] = host.write_finish_request(self.finish_path, self.session, events.client_pid)
            return
        kind, value, name = self.ACTIONS[self.action]
        if kind in ('login', 'connected', 'saved'):
            proof, generation, requested = {
                'login': ('post_login_captures', events.login_generation, frame.request_login_generation),
                'connected': ('connected_captures', events.connected_generation, frame.request_connected_generation),
                'saved': ('post_save_captures', events.saved_generation, frame.request_saved_generation)}[kind]
            if not self.proof_frames(proof, generation, requested, frame, events, sequence, now): return
        elif kind == 'ocr_move':
            if now-self.last_ocr_at < 2: return
            self.last_ocr_at = now
            self.ocr_attempts += 1
            match, stem = read_button(frame, self.evidence, value[0], name, self.ocr_attempts, value[1])
            require(self.ocr_attempts <= 20, 'Rendered '+value[0]+' button not found; inspect retained creator frames')
            if match is None: return
            self.ocr_position = match[:2]
            self.result['ocr_buttons'].append({'label': value[0], 'x': match[0], 'y': match[1],
                'confidence': match[2], 'evidence': stem, 'frame_sequence': sequence})
            host.pointer_move(connection, *self.ocr_position)
        elif kind == 'ocr_click':
            require(self.ocr_position is not None, 'Missing rendered button location')
            host.pointer_click(connection, *self.ocr_position)
            self.ocr_position = None
            self.ocr_attempts = 0
        elif kind == 'move': host.pointer_move(connection, *value)
        elif kind == 'click': host.pointer_click(connection, *value)
        elif kind == 'text': fixed_text(connection, value, replace=True)
        elif kind == 'command': fixed_text(connection, value)
        elif kind in ('key', 'escape'): key(connection, 0xff1b if kind == 'escape' else value)
        else: require(False, 'Unknown graphical action')
        if name == 'submit_ordinary_logout':
            self.result['logout_request'] = write_logout_request(self.finish_path.parent/'character-logout.json',
                self.session, events.client_pid, events.character_id)
        self.capture('character-%02d-before-%s' % (self.action, name), frame, events, sequence, now)
        self.result['steps'].append({'action': name, 'session_id': self.session, 'client_pid': events.client_pid,
            'after_frame_sequence': sequence, 'fresh_frames_since_previous_action': self.fresh_frames,
            'elapsed_since_ready': round(now-self.ready_at, 3)})
        self.action += 1
        self.last_action_at = time.monotonic()
        self.fresh_frames = 0
        self.watermark = sequence
        self.frame_generation = frame.generation


def observe_rfb(connection,session,process,deadline,evidence,event_path,finish_path,interaction_factory=None):
    desktop=host.client_rfb_handshake(connection);frame=host.ClientFramebuffer()
    updates=0;fingerprints=[];snapshots=[];last_capture=0;terminal=None;started=time.monotonic()
    resizes=[];events=CharacterEvents(event_path,session);captures=[];event_generation=0
    pending_request=False;request_generation=0;failure=None
    interaction=(interaction_factory or CharacterInteraction)(session,evidence,finish_path)
    request_login_generation=request_connected_generation=request_saved_generation=0
    while process.poll() is None and time.monotonic()<deadline:
        try:
            events.poll()
            if events.generation!=event_generation:
                captures=[];event_generation=events.generation
                require(event_generation==1,'Unexpected repeated interaction readiness')
            if not pending_request:
                connection.sendall(struct.pack('!BBHHHH',3,0,0,0,frame.width,frame.height))
                request_generation=events.generation if events.active else 0
                request_login_generation=events.login_generation if events.active else 0
                request_connected_generation=events.connected_generation if events.active else 0
                request_saved_generation=events.saved_generation if events.active else 0
                pending_request=True
            kind=host.transport.recv_exact(connection,1)[0]
            if kind==2:continue
            if kind==3:
                header=host.transport.recv_exact(connection,7);size=struct.unpack_from('!I',header,3)[0]
                require(size<=4096,'Oversized cut text');host.transport.recv_exact(connection,size);continue
            require(kind==0,'Unexpected RFB message')
            changed,resized=frame.read_update(connection)
            pending_request=False
            events.poll()
            if events.generation!=event_generation:
                captures=[];event_generation=events.generation
                require(event_generation==1,'Unexpected repeated interaction readiness')
            if resized:
                require(len(resizes)<64,'RFB desktop-size event count exceeds bound')
                resizes.append({'width':frame.width,'height':frame.height,'generation':frame.generation,
                                'elapsed_seconds':round(time.monotonic()-started,3)})
                if not events.terminal:captures=[]
            if not changed:continue
            updates+=1;sha=hashlib.sha256(frame.pixels).hexdigest()
            if sha not in fingerprints and len(fingerprints)<2000:fingerprints.append(sha)
            now=time.monotonic()
            if (events.active and request_generation==events.generation and request_generation>0
                    and (frame.width,frame.height)==(host.WIDTH,host.HEIGHT) and len(captures)<3
                    and (not captures or now-started-captures[-1]['elapsed_seconds']>=1)):
                colors=set()
                for offset in range(0,len(frame.pixels),4):
                    colors.add(bytes(frame.pixels[offset:offset+3]))
                    if len(colors)>=8:break
                if len(colors)>=8:
                    name=f'client-startup-external-{len(captures):03d}.png'
                    host.save_png(evidence/name,frame.pixels)
                    captures.append({'file':name,'elapsed_seconds':now-started,'frame_sha256':sha,
                        'png_sha256':host.digest(evidence/name),'session_id':session,'client_pid':events.client_pid,
                        'width':host.WIDTH,'height':host.HEIGHT,'distinct_colors_capped':len(colors),
                        'frame_sequence':updates,'frame_generation':frame.generation,
                        'event_generation':events.generation})
            if events.active and request_generation==events.generation and request_generation>0:
                frame.request_login_generation=request_login_generation
                frame.request_connected_generation=request_connected_generation
                frame.request_saved_generation=request_saved_generation
                interaction.on_frame(connection,frame,events,updates,captures,now)
            if now-last_capture>=20 and len(snapshots)<280:
                name=f'client-frame-{len(snapshots):03d}.png';host.save_png(evidence/name,frame.pixels,frame.width,frame.height)
                snapshots.append({'file':name,'elapsed_seconds':round(now-started,3),'frame_sha256':sha,
                                  'width':frame.width,'height':frame.height,'generation':frame.generation});last_capture=now
            time.sleep(0.5)
        except (ValueError, subprocess.SubprocessError) as error:
            # Keep the current session's screenshots and input steps even when
            # a bounded observation/identity check fails. The caller still
            # rejects the result and stops the owned guest immediately.
            failure=str(error)
            break
        except (EOFError,BrokenPipeError,ConnectionResetError) as error:
            terminal=type(error).__name__
            # X closes during ordinary guest cleanup; event output may arrive
            # just after the socket EOF. Match the Android two-second allowance.
            terminal_deadline=min(deadline,time.monotonic()+2)
            while not events.terminal and time.monotonic()<terminal_deadline:
                try:events.poll()
                except ValueError as invalid:
                    failure=str(invalid)
                    break
                if not events.terminal:time.sleep(.05)
            if not events.terminal and failure is None:failure='Private RFB transport ended before client startup observation completed'
            break
    try:events.poll()
    except ValueError as invalid:
        if failure is None:failure=str(invalid)
    if frame.fresh:host.save_png(evidence/'client-frame-final.png',frame.pixels,frame.width,frame.height)
    return {'scope':'host_external_unix_rfb_graphical_character_creation','desktop':desktop,'session_id':session,'updates':updates,
            'distinct_frame_sha256':fingerprints,'snapshots':snapshots,'terminal_transport':terminal,
            'desktop_size_events':resizes,'final_frame':{'width':frame.width,'height':frame.height,
                'generation':frame.generation,'fresh_after_resize':frame.fresh,'updates_after_resize':frame.updates},
            'post_startup_captures':captures,'client_pid':events.client_pid,'terminal_event_observed':events.terminal,
            'failure':failure,
            'interaction_script':interaction.result,
            'connected_outside_proot':True,'android_surface_validated':False,'gameplay_validated':False}


def make_command(work, assets, proot, session, data, startup_timeout_seconds=900):
    command, environment = login.make_command(work, assets, proot, session, data, startup_timeout_seconds)
    command[command.index('/opt/coh/client_login_diagnostic.py')] = '/opt/coh/character_creation_diagnostic.py'
    command[command.index('--interaction-seconds')+1] = str(INTERACTION_SECONDS)
    command[command.index('--timeout-seconds')+1] = str(OVERALL_SECONDS)
    return command, environment


def validate_avatar_supplement(report, manifest):
    avatar = host.assets_tool.avatar_tools()
    contract = avatar.bundle_contract()
    require(all(manifest.get('files', {}).get(name) == pin for name, pin in
                ((avatar.ARCHIVE, contract['archive_pin']), (avatar.MANIFEST, contract['manifest_pin']))),
            'Character avatar inputs differ from the reviewed package')
    pinned = avatar.verify(host.ROOT/'assets'/avatar.ARCHIVE, host.ROOT/'assets'/avatar.MANIFEST)
    receipt = report.get('character_avatar_supplement')
    require(isinstance(receipt, dict), 'Missing character avatar supplement receipt')
    expected = {'format': 1, 'scope': contract['scope'],
        'manifest_sha256': contract['manifest_pin']['sha256'], 'archive_sha256': contract['archive_pin']['sha256'],
        'file_count': contract['file_count'], 'payload_bytes': contract['payload_bytes'], 'files': pinned['files'],
        'normalized_mtime_epoch': 1767225600, 'imported_files_modified': False,
        'worktree_identity_modified': False, 'cache_files_modified': False,
        'runtime_visual_validated': False, 'visual_scope': pinned['visual_scope']}
    require(set(receipt) == set(expected) | {'installed_files', 'reused_files', 'worktree'}
            and all(type(receipt.get(name)) is type(value) and receipt[name] == value for name, value in expected.items()),
            'Character avatar supplement identity or preservation proof differs')
    require(all(type(receipt[name]) is int and 0 <= receipt[name] <= contract['file_count']
                for name in ('installed_files', 'reused_files'))
            and receipt['installed_files']+receipt['reused_files'] == contract['file_count'],
            'Character avatar supplement installation count differs')
    worktree = report.get('client_worktree', {})
    identities = [worktree.get('import', {}).get('receipt_sha256'), worktree.get('package_sha256'),
                  worktree.get('cache_archive_sha256'), worktree.get('prerequisites_archive_sha256')]
    require(all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) for value in identities)
            and worktree.get('normalized_mtime_epoch') == expected['normalized_mtime_epoch'],
            'Missing original client worktree identity for avatar supplement')
    key = hashlib.sha256((''.join(identities)+str(expected['normalized_mtime_epoch'])).encode()).hexdigest()[:24]
    require(receipt['worktree'] == 'client-work-'+key, 'Character avatar supplement was installed into another worktree')


def validate_report(report, session, manifest):
    require(report.get('scope') == 'actual_character_creation_guest'
            and report.get('diagnostic_mode') == 'actual_character_creation'
            and report.get('session_id') == session, 'Wrong character session report')
    require(report.get('passed') is True and report.get('status') == 'passed' and report.get('failures') == [],
            'Graphical character creation did not pass')
    validate_avatar_supplement(report, manifest)
    require(report.get('interaction_session_completed') is True and report.get('input_effect_verified') is False
            and report.get('interaction_completion_reason') == 'finish_requested'
            and 30 <= report.get('observation_seconds', 0) <= INTERACTION_SECONDS+10
            and report.get('interaction_timeout_seconds') == INTERACTION_SECONDS
            and 0 <= report.get('startup_elapsed_seconds', -1) <= 900,
            'Character session bounds or finish evidence differ')
    launch = report.get('client_launch', {})
    require(launch.get('session_id') == session and type(launch.get('pid')) is int and launch['pid'] > 0,
            'Actual graphical client session identity differs')
    for name in ('postgres_started', 'server_started', 'mapserver_started', 'client_process_started',
                 'startup_observed', 'renderer_initialized', 'all_data_loaded', 'client_main_loop_reached',
                 'client_window_observed'):
        require(report.get(name) is True, 'Missing actual character evidence: '+name)
    require(report.get('gameplay_validated') is False, 'Unexpected gameplay validation claim')
    expected_stages = ['client_inputs', 'client_private_data', 'persistent_server_profile', 'postgres_local_login',
        'presentation_display', 'wine_initialization', 'local_login_odbc', 'local_dbserver_startup',
        'local_atlas_startup', 'win32_runtime_dll', 'actual_client_startup', 'actual_client_interaction']
    stages = report.get('stages', [])
    require([item.get('stage') for item in stages] == expected_stages
            and all(item.get('status') == 'passed' for item in stages), 'Character stages incomplete')
    local = report.get('local_login', {})
    require(local.get('session_id') == session and local.get('client_pid') == launch['pid']
            and local.get('profile') == 'android-local-login' and local.get('account') == 'COHLOCAL'
            and local.get('server_ready') is True and local.get('local_account_verified') is True
            and local.get('local_login_verified') is True and local.get('character_list_sent') is True
            and local.get('character_list_response_sent') is True and local.get('database_preserved') is True,
            'Missing current local login and persistent profile proof')
    saved = report.get('character_creation', {})
    require(saved.get('session_id') == session and saved.get('client_pid') == launch['pid']
            and saved.get('name') == CHARACTER and saved.get('account') == 'COHLOCAL'
            and type(saved.get('character_id')) is int and saved['character_id'] > 0
            and type(saved.get('auth_id')) is int and saved['auth_id'] > 0
            and saved['auth_id'] == local.get('auth_id')
            and type(saved.get('map_id')) is int and saved['map_id'] == 1
            and all(saved.get(name) is True for name in ('verified', 'connected_on_atlas',
                'committed_sql_verified', 'requested_logout_observed', 'logout_timer_observed', 'disconnected_before_sql'))
            and saved.get('forced_stop_before_save') is False,
            'Missing ordinary logout and committed graphical character save proof')
    children = report.get('processes', [])
    require(len(children) >= 7 and all(type(child.get('exit_code')) is int
            and child.get('input_closed') is True and child.get('output_capture_closed') is True for child in children),
            'Owned character children did not close')
    for label in ('actual-coh-client', 'runtime-probe', 'private-presentation-x', 'local-dbserver', 'local-character-atlas'):
        matching = [child for child in children if child.get('label') == label]
        require(len(matching) == 1, 'Missing or duplicate owned child: '+label)
        if label == 'runtime-probe': require(matching[0]['exit_code'] == 0, 'Runtime prerequisite failed')
    execution = report.get('cleanup_execution', {})
    require(execution == {'diagnostic_initialized': True, 'wine_started': True, 'owned_child_count': len(children)},
            'Cleanup ownership record differs')
    require(report.get('cleanup_complete') is True and report.get('presentation_socket_removed') is True
            and all(report.get('cleanup', {}).get(key) is True for key in
                    ('postgres_graceful', 'wine_prefix_stopped', 'owned_processes_reaped'))
            and report.get('wine_process_cleanup', {}).get('complete') is True
            and report.get('wine_process_cleanup', {}).get('remaining') == 0
            and report.get('wine_process_cleanup', {}).get('inspection_failures') == 0,
            'Character process/display/database cleanup incomplete')
    require(report.get('asset_sha256') == {name: manifest['files'][name]['sha256'] for name in host.assets_tool.PROBE_FILES},
            'Character guest input hashes differ')


def validate_observer(observer, report):
    require(observer.get('failure') is None and observer.get('terminal_event_observed') is True,
            observer.get('failure') or 'Missing character observer completion')
    require(observer.get('client_pid') == report['client_launch']['pid'], 'Observed graphical client identity differs')
    script = observer['interaction_script']
    require(script.get('script_completed') is True and len(script['steps']) == len(CharacterInteraction.ACTIONS)
            and script.get('finish_request', {}).get('client_pid') == observer['client_pid']
            and len(script.get('ocr_buttons', [])) == 3, 'Graphical creator script did not finish')
    logout = script.get('logout_request', {})
    require(set(logout) == {'format', 'session_id', 'client_pid', 'character_id', 'action', 'sent_utc_ms'}
            and logout['format'] == 1 and logout['session_id'] == report['session_id']
            and logout['client_pid'] == observer['client_pid']
            and logout['character_id'] == report['character_creation']['character_id']
            and logout['action'] == 'quittologin' and type(logout['sent_utc_ms']) is int and logout['sent_utc_ms'] > 0,
            'Missing exact successfully sent ordinary logout receipt')
    for name in ('post_login_captures', 'connected_captures', 'post_save_captures'):
        captures = script.get(name, [])
        require(len(captures) == 3 and len({item['frame_sequence'] for item in captures}) == 3
                and all(item['session_id'] == report['session_id'] and item['client_pid'] == observer['client_pid']
                        and item['proof_event_generation'] == 1 and item['width'] == 800 and item['height'] == 600
                        and item['frame_generation'] == captures[0]['frame_generation'] for item in captures)
                and captures[-1]['elapsed_since_ready']-captures[0]['elapsed_since_ready'] >= 2,
                'Missing fresh current-client proof images: '+name)


def stop_guest(process, state):
    """Allow bounded evidence collection and report persistence after cancellation."""
    result = {'stop_requested': False, 'grace_seconds': CLEANUP_GRACE_SECONDS,
              'forced_quit': False, 'forced_kill': False, 'errors': []}
    if process is not None and process.poll() is None:
        try:
            (state/'stop-request').write_text('stop\n')
            result['stop_requested'] = True
        except OSError as error:
            result['errors'].append('Cannot request guest stop: '+str(error))
        try:
            try: process.wait(timeout=CLEANUP_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                result['forced_quit'] = True
                process.send_signal(signal.SIGQUIT)
                try: process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    result['forced_kill'] = True
                    process.kill()
                    process.wait(timeout=5)
        except (OSError, subprocess.SubprocessError) as error:
            # Cleanup errors must not prevent retention of the original
            # observer failure and support evidence already written by guest.
            result['errors'].append('Guest stop failed: '+str(error))
    result['process_reaped'] = process is None or process.poll() is not None
    return result


def export_guest_evidence(state, evidence, session):
    """Retain atomic reports, or the current session's collected support files."""
    result = {'files': [], 'fallback_used': False, 'errors': []}
    for name, limit in (('latest-report.json', 2*1024*1024), ('report.zip', CHARACTER_EVIDENCE_LIMIT+4*1024*1024)):
        source = state/name
        try:
            require(not source.is_symlink(), 'Linked guest report refused')
            if not source.is_file(): continue
            require(source.stat().st_size <= limit, 'Guest report exceeded export bound')
            shutil.copyfile(source, evidence/name)
            result['files'].append(name)
        except (OSError, ValueError) as error:
            result['errors'].append(name+': '+str(error))
    if 'report.zip' in result['files']:
        return result
    # Guest-produced evidence is bounded and server logs have already passed its
    # credential redaction. Never traverse the live runtime, database, or config.
    captures = state/('client-evidence-'+session)
    try:
        require(not captures.is_symlink(), 'Linked guest evidence directory refused')
        if not captures.is_dir(): return result
        paths = sorted(captures.rglob('*'))
        require(len(paths) <= 140, 'Guest evidence entry count exceeded bound')
        files, total = [], 0
        for path in paths:
            require(not path.is_symlink(), 'Linked guest evidence refused')
            if not path.is_file(): continue
            files.append(path)
            total += path.stat().st_size
            require(len(files) <= 70 and total <= CHARACTER_EVIDENCE_LIMIT, 'Guest evidence exceeded export bound')
        result['fallback_used'] = True
        for source in files:
            relative = Path('guest-evidence')/source.relative_to(captures)
            target = evidence/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            result['files'].append(relative.as_posix())
    except (OSError, ValueError) as error:
        result['errors'].append('Guest evidence fallback: '+str(error))
    return result


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
    require(not args.work.exists(), 'Fresh private character smoke work required')
    args.work = args.work.resolve(); args.proot = args.proot.resolve(); args.evidence = args.evidence.resolve()
    args.work.mkdir(parents=True); args.evidence.mkdir(parents=True, exist_ok=True)
    manifest, assets, imports = host.extract_apk_assets(args.apk, args.work/'apk-assets', args.build_report, args.repository_commit)
    data = host.import_game_data(imports, args.archive.resolve(), args.work, args.evidence)
    session = secrets.token_hex(16)
    command, environment = make_command(args.work, assets, args.proot, session, data, args.startup_timeout_seconds)
    start = time.monotonic(); deadline = start+OVERALL_SECONDS+60
    observer = failure = process = None
    with (args.evidence/'host-client.log').open('w') as log:
        try:
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            socket_path = args.work/'socket/view.sock'
            while not socket_path.exists():
                require(process.poll() is None and time.monotonic() < deadline, 'Guest exited before character display socket')
                time.sleep(.1)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(90); connection.connect(str(socket_path))
                observer = observe_rfb(connection, session, process, deadline, args.evidence,
                    args.evidence/'host-client.log', args.work/'state/interaction-finish.json')
            require(observer.get('failure') is None, observer.get('failure') or 'Character observer failed')
            require(process.wait(timeout=max(1, deadline-time.monotonic())) == 0, 'Character guest exited unsuccessfully')
            report = json.loads((args.work/'state/latest-report.json').read_text())
            validate_report(report, session, manifest)
            validate_observer(observer, report)
            require(not socket_path.exists(), 'Private character display socket survived cleanup')
        except Exception as error:
            failure = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            cleanup = stop_guest(process, args.work/'state')
            export = export_guest_evidence(args.work/'state', args.evidence, session)
            result = {'format': 1, 'status': 'failed' if failure else 'passed',
                'scope': 'exact_apk_graphical_character_creation_native_arm64', 'repository_commit': args.repository_commit,
                'apk_sha256': host.digest(args.apk), 'runtime_manifest_sha256': host.digest(assets/'runtime-manifest.json'),
                'session_id': session, 'external_observer': observer, 'failure': failure,
                'host_cleanup': cleanup, 'guest_evidence_export': export,
                'elapsed_seconds': round(time.monotonic()-start, 3), 'android_execution_validated': False,
                'android_surface_validated': False, 'character_creation_visual_validated': False,
                'gameplay_validated': False}
            (args.evidence/'host-client-report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
