#!/usr/bin/env python3
"""Framework qualification on a disposable Android 13 x86_64 emulator.

This exercises actual Activities, SAF cancellation and native preview rendering.
The optional UDP executable uses scripted source-layout peers and never claims a
real database/account/map session. ARM64 guest servers require device acceptance.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import re
import selectors
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
import zipfile

PACKAGE = 'org.coh.nativecombined'
MAIN = PACKAGE + '/.MainActivity'
NATIVE = PACKAGE + '/.NativeClientActivity'
# AOSP DumpCommand reports these exact failures before writing a hierarchy.
CAPTURE_TRANSIENTS = frozenset(('ERROR: could not get idle state.',
    'ERROR: null root node returned by UiTestAutomationBridge.'))


def installed_apk_contract(value, expected_sha, expected_bytes, require_ready=True):
    status, identity = value.get('installed_apk_status'), value.get('installed_apk')
    assert status in ('pending', 'ready', 'unavailable'), 'Installed APK identity status is invalid'
    if status != 'ready':
        assert identity is None
        assert not require_ready, 'Installed APK identity is not ready'
        return {'installed_apk_status': status}
    assert isinstance(identity, dict) and set(identity) == {'bytes', 'sha256'}
    assert type(identity['bytes']) is int and 0 < identity['bytes'] <= 25 << 20
    assert isinstance(identity['sha256'], str) and re.fullmatch('[0-9a-f]{64}', identity['sha256'])
    assert identity == {'bytes': expected_bytes, 'sha256': expected_sha}, 'App report identifies a different installed APK'
    return {'installed_apk_status': status, 'installed_apk_bytes': identity['bytes'],
            'installed_apk_sha256': identity['sha256']}


def guest_resources_contract(value):
    rows = value.get('guest_resources')
    assert isinstance(rows, list) and len(rows) <= 32, 'Guest resource diagnostics exceed their public bound'
    metrics = ('rss_kib', 'peak_rss_kib', 'children_peak_rss_kib', 'cgroup_current_bytes',
               'cgroup_max_bytes', 'cgroup_oom_kill_count')
    for row in rows:
        assert isinstance(row, dict) and set(row) == set(metrics) | {'stage', 'boundary', 'elapsed_ms'}
        assert isinstance(row['stage'], str) and re.fullmatch(r'[A-Za-z0-9_ .:-]{1,120}', row['stage'])
        assert row['boundary'] in ('entered', 'leaving')
        assert type(row['elapsed_ms']) is int and row['elapsed_ms'] >= 0
        assert all(row[k] is None or (type(row[k]) is int and 0 <= row[k] <= 1 << 50) for k in metrics)
    return {'retained_guest_resource_samples': len(rows),
            'guest_resource_scope': 'Bounded numeric report schema; empty x86 samples do not qualify ARM64 guest RSS or an Android kill cause.'}


def viewport_contract(value):
    """Match the actual EGL viewport to its bounded Android SurfaceView."""
    policy = value.get('viewport_policy', {})
    assert policy.get('schema') == 'coh-native-viewport-v1'
    assert (policy.get('maximum_controls_percent'), policy.get('minimum_aspect'),
            policy.get('maximum_aspect'), policy.get('maximum_dimension')) == (60, .25, 8, 16384)
    area, native = value.get('input_area', {}), value.get('native', {})
    w, h = area.get('width'), area.get('height')
    assert type(w) is int and type(h) is int and 0 < w <= 16384 and 0 < h <= 16384
    assert 4*w >= h and w <= 8*h, 'Actual Surface exceeds unchanged native camera aspect bounds'
    assert area.get('shown') is True and area.get('surface_ready') is True
    assert all(type(area.get(k)) is int and area[k] >= 0 for k in ('left', 'top'))
    assert all(type(policy.get(k)) is int and policy[k] > 0 for k in ('host_width', 'host_height'))
    assert w <= policy['host_width'] and h <= policy['host_height']
    assert (native.get('width'), native.get('height')) == (w, h), 'Renderer retained a stale EGL viewport'
    assert value.get('preview_is_server_world') is False
    return {'surface_width': w, 'surface_height': h, 'host_width': policy['host_width'],
            'host_height': policy['host_height'], 'native_camera_aspect_valid': True}


def map_report_contract(value):
    """Exact numeric-only diagnostics: no packet payloads or session secrets."""
    assert value.get('schema') == 'coh-native-local-numeric-v1'
    assert isinstance(value.get('phase'), str) and re.fullmatch('[A-Z_]{1,40}', value['phase'])
    assert value.get('authserver_authenticated') is False and value.get('live_world_rendered') is False
    numbers = ('local_development_auth server_identity_bound generation selection_generation '
        'db_phase map_phase last_status attempts character_lists character_choices map_handoffs '
        'policy_rejections failures suspends cancellations opened_sockets closed_sockets '
        'terminal_failure terminal_db_phase terminal_map_phase').split()
    fields = ('phase stage last_status last_command_valid last_command last_payload_bits last_byte_aligned '
        'accepted_messages rejected_messages malformed unsupported scene_prefixes entity_prefixes disconnects suspends timeouts').split()
    udp_fields = ('state link_state sockets_opened sockets_closed datagrams_sent datagrams_received peer_rejects '
        'truncated empty malformed unsupported send_would_block interrupted io_errors receive_budget_exhausted '
        'suspends resumes cancellations timeouts last_system_error').split()
    link_fields = ('sent received retransmits acknowledged duplicates malformed queue_limits fragment_expirations '
        'timeouts unsupported tx_pending rx_pending fragment_groups storage_bytes codec_bytes high_water_retained_bytes').split()
    def exact(data, numeric, extras=(), signed=()):
        assert isinstance(data, dict) and set(data) == set(numeric) | set(extras), 'Unexpected public protocol fields'
        assert all(type(data[k]) is int and (k in signed or data[k] >= 0) for k in numeric)
    exact(value, numbers, ('schema', 'phase', 'map_protocol', 'authserver_authenticated', 'live_world_rendered'))
    mapping = value['map_protocol']; exact(mapping, fields, ('udp',))
    udp = mapping['udp']; exact(udp, udp_fields, ('link',), ('last_system_error',))
    exact(udp['link'], link_fields)
    assert all(value[k] in (0, 1) for k in ('local_development_auth', 'server_identity_bound', 'terminal_failure'))
    assert all(mapping[k] in (0, 1) for k in ('last_command_valid', 'last_byte_aligned'))
    return {'phase': value['phase'], 'map_stage': mapping['stage'], 'last_status': mapping['last_status'],
            'accepted_messages': mapping['accepted_messages'], 'scene_prefixes': mapping['scene_prefixes'],
            'numeric_privacy_bounds_verified': True}


def memory_report_contract(value):
    """Validate public report bounds without claiming ARM64 memory admission ran."""
    memory = value.get('server_memory')
    assert isinstance(memory, dict), 'Combined memory diagnostics are absent'
    nonnegative = ('samples', 'invalid_samples', 'sample_interval_ms', 'required_pressure_samples',
                   'required_pressure_span_ms', 'retained_sample_limit', 'pressure_samples')
    nullable = ('admission_reserve_bytes', 'running_reserve_bytes', 'java_heap_reserve_bytes',
                'minimum_java_heap_headroom_bytes', 'pressure_started_elapsed_ms', 'last_elapsed_ms')
    allowed = set(nonnegative + nullable + ('format', 'status', 'reason', 'scope',
                  'sample_unavailable_policy', 'admitted', 'stop_requested',
                  'minimum_system_headroom_bytes', 'recent_samples'))
    assert set(memory) == allowed, 'Unexpected memory diagnostic fields'
    assert type(memory['format']) is int and memory['format'] == 1
    assert isinstance(memory['status'], str) and re.fullmatch(r'[a-z_]{1,64}', memory['status'])
    assert isinstance(memory['reason'], str) and re.fullmatch(r'[A-Z0-9_]{0,80}', memory['reason'])
    assert isinstance(memory['scope'], str) and 0 < len(memory['scope']) <= 256
    assert memory['sample_unavailable_policy'] == 'block_start_or_request_owned_cleanup'
    assert all(type(memory[k]) is bool for k in ('admitted', 'stop_requested'))
    assert all(type(memory[k]) is int and memory[k] >= 0 for k in nonnegative)
    assert all(memory[k] is None or (type(memory[k]) is int and memory[k] >= 0) for k in nullable)
    assert memory['minimum_system_headroom_bytes'] is None or type(memory['minimum_system_headroom_bytes']) is int
    assert memory['invalid_samples'] <= memory['samples']
    assert (memory['sample_interval_ms'], memory['required_pressure_samples'],
            memory['required_pressure_span_ms'], memory['retained_sample_limit']) == (1000, 3, 3000, 64)
    rows = memory['recent_samples']
    assert isinstance(rows, list) and len(rows) <= min(64, memory['samples'])
    fields = ('available_bytes', 'total_bytes', 'threshold_bytes', 'java_heap_used_bytes',
              'java_heap_limit_bytes', 'java_heap_headroom_bytes')
    row_keys = set(fields + ('elapsed_ms', 'valid', 'system_headroom_bytes', 'low_memory'))
    for row in rows:
        assert isinstance(row, dict) and set(row) == row_keys
        assert type(row['valid']) is bool
        assert row['elapsed_ms'] is None or (type(row['elapsed_ms']) is int and row['elapsed_ms'] >= 0)
        assert all(row[k] is None or (type(row[k]) is int and row[k] >= 0) for k in fields)
        assert row['system_headroom_bytes'] is None or type(row['system_headroom_bytes']) is int
        assert row['low_memory'] is None or type(row['low_memory']) is bool
        if row['valid']:
            assert all(type(row[k]) is int for k in fields) and type(row['low_memory']) is bool
        else:
            assert all(row[k] is None for k in (*fields, 'system_headroom_bytes', 'low_memory'))
    exits = value.get('android_process_exits')
    assert isinstance(exits, list) and len(exits) <= 8, 'Android exit history exceeds its public bound'
    exit_numbers = ('reason', 'status', 'timestamp_utc_ms', 'importance', 'pss_kib', 'rss_kib')
    for item in exits:
        assert isinstance(item, dict) and set(item) == set(exit_numbers + ('low_memory',)), 'Unexpected Android exit metadata; descriptions and traces must stay private'
        assert all(type(item[k]) is int for k in exit_numbers)
        assert all(item[k] >= 0 for k in ('timestamp_utc_ms', 'pss_kib', 'rss_kib'))
        assert type(item['low_memory']) is bool
    assert isinstance(value.get('android_exit_history_status'), str)
    return {**guest_resources_contract(value), 'memory_samples': memory['samples'], 'memory_status': memory['status'],
            'retained_memory_samples': len(rows), 'android_exit_records': len(exits),
            'scope': 'Actual combined-report schema and numeric privacy bounds; zero samples do not qualify ARM64 server memory admission or guest execution.'}


def settled_preview(value, minimum_frames):
    native = value.get('native', {})
    static = native.get('static_renderer', {})
    return (value.get('assets_verified') is True and value.get('resumed') is True
            and value.get('failure') is None and value.get('report_write_failed') is False
            and native.get('valid') is True and native.get('failed') is False
            and native.get('running') is True and native.get('foreground') is True
            and native.get('objects_released') is False and native.get('frames', 0) > minimum_frames
            and native.get('contexts_started', 0) == native.get('contexts_completed', 0) + 1
            and native.get('gl_errors') == 0 and native.get('tf_mismatches') == 0
            and static.get('gpu_bytes', 0) > 0 and static.get('tf_mismatches') == 0
            and static.get('visible_pixels', 0) > 0
            and all(native.get(k, 0) > 0 for k in ('world_visible_pixels', 'actor_visible_pixels',
                'world_occludes_actor_pixels', 'actor_occludes_world_pixels', 'actor_changed_pixels')))


def scene_pixels(raw, area):
    from io import BytesIO
    from PIL import Image
    with Image.open(BytesIO(raw)) as image:
        if image.format != 'PNG':
            raise ValueError('Device screenshot is not PNG')
        image = image.convert('RGB')
        values = [area.get(k) for k in ('left','top','width','height')]
        if any(type(v) is not int for v in values):
            raise ValueError('Actual Surface bounds are absent')
        left, top, width, height = values
        if (left < 0 or top < 0 or width < 64 or height < 64
                or left+width > image.width or top+height > image.height
                or area.get('shown') is not True or area.get('surface_ready') is not True):
            raise ValueError('Actual foreground Surface bounds are invalid')
        crop = image.crop((left, top, left+width, top+height))
        count = width*height
        bright = sum(max(rgb) >= 40 for rgb in crop.getdata())
        black = sum(max(rgb) <= 4 for rgb in crop.getdata())
        colors = crop.getcolors(maxcolors=65536)
        distinct = len(colors) if colors is not None else 65537
        proof = {'surface_position_size':values,'surface_bounds_ltrb':[left,top,left+width,top+height],'screenshot_size':[image.width,image.height],
                 'surface_pixels':count,'bright_pixels':bright,'black_pixels':black,
                 'distinct_colors_at_least':distinct,'minimum_bright_pixels':max(256,count//100),
                 'minimum_distinct_colors':64,
                 'scope':'Actual device screenshot crop at Android framework-reported SurfaceView screen bounds; excludes app header, buttons and navigation bar.'}
        proof['passed'] = bright >= proof['minimum_bright_pixels'] and distinct >= proof['minimum_distinct_colors']
        return proof, crop


class Check:
    def __init__(self, args):
        self.args = args
        self.proofs = []
        self.launcher_anrs = 0
        self.capture_id = 0
        args.output.mkdir(parents=True, exist_ok=True)

    def adb(self, *args, check=True, timeout=45):
        r = subprocess.run([self.args.adb, '-s', self.args.serial, *map(str, args)], capture_output=True, timeout=timeout)
        if check and r.returncode:
            raise RuntimeError('ADB command failed: ' + repr(args) + '\nreturncode=' + str(r.returncode)
                + '\nstdout:\n' + r.stdout.decode(errors='replace') + '\nstderr:\n' + r.stderr.decode(errors='replace'))
        return r

    def text(self, *args, check=True):
        return self.adb(*args, check=check).stdout.decode(errors='replace')

    def record(self, name, **details):
        item = {'check': name, 'passed': True, **details}
        self.proofs.append(item)
        (self.args.output / 'progress.json').write_text(json.dumps(self.proofs, indent=2) + '\n')
        print(json.dumps(item), flush=True)

    def native_fault_evidence(self, prefix):
        last = self.text('shell', 'dumpsys', 'activity', 'lastanr')
        events = self.text('logcat', '-d', '-b', 'events', '-s', 'am_anr', 'am_crash')
        crashes = self.text('logcat', '-d', '-b', 'crash')
        (self.args.output / (prefix + '-lastanr.txt')).write_text(last)
        (self.args.output / (prefix + '-events.txt')).write_text(events)
        (self.args.output / (prefix + '-crashes.txt')).write_text(crashes)
        # A CoH app ANR anywhere in this fresh disposable session invalidates the
        # run even if an external system process also displayed a dialog.
        native_anr = re.search(r'ANR in ' + re.escape(PACKAGE) + r'(?:[\s(/]|$)', last)
        native_event = re.search(r'am_(?:anr|crash)[^\n]*[,\[]' + re.escape(PACKAGE) + r'[,\]]', events)
        if native_anr or native_event or PACKAGE in crashes:
            raise RuntimeError('Native app ANR or crash found in framework diagnostics; no retry or dismissal')
        return last, events

    def system_anr_evidence(self, label):
        last, events = self.native_fault_evidence('external-anr-' + str(self.launcher_anrs))
        if label == "Files isn't responding":
            packages = ('com.google.android.documentsui', 'com.android.documentsui')
            identified = next((p for p in packages if re.search(r'ANR in ' + re.escape(p) + r'(?:[\s(/]|$)', last)), None)
            if identified is None:
                identified = next((p for p in packages if re.search(r'am_anr[^\n]*[,\[]' + re.escape(p) + r'[,\]]', events)), None)
            if identified is None:
                raise RuntimeError('Files ANR process was not positively identified; traces preserved without dismissal')
            return identified
        return 'com.google.android.apps.nexuslauncher'

    def capture_command(self, prefix, phase, *command):
        result = self.adb(*command, check=False)
        (self.args.output / (prefix + '-' + phase + '.stdout')).write_bytes(result.stdout)
        (self.args.output / (prefix + '-' + phase + '.stderr')).write_bytes(result.stderr)
        (self.args.output / (prefix + '-' + phase + '.json')).write_text(json.dumps(
            {'command':command, 'returncode':result.returncode}, indent=2) + '\n')
        return result

    def capture_ui(self):
        self.capture_id += 1
        remote = '/data/local/tmp/combined-ui.xml'
        for attempt in range(1, 4):
            prefix = 'ui-capture-' + str(self.capture_id) + '-attempt-' + str(attempt)
            cleared = self.capture_command(prefix, 'clear', 'shell', 'rm', '-f', remote)
            if cleared.returncode:
                self.native_fault_evidence(prefix)
                raise RuntimeError('Cannot remove previous UI capture; refusing stale XML: ' + prefix)
            result = self.capture_command(prefix, 'dump', 'shell', 'uiautomator', 'dump', remote)
            diagnostic = (result.stdout + b'\n' + result.stderr).decode(errors='replace').strip()
            transient = diagnostic in CAPTURE_TRANSIENTS
            if result.returncode or transient:
                self.native_fault_evidence(prefix)
                if transient and attempt < 3:
                    time.sleep(.5)
                    continue
                raise RuntimeError('UI capture failed; raw stdout/stderr preserved: ' + prefix
                    + '; returncode=' + str(result.returncode) + '; diagnostic=' + diagnostic)
            read = self.capture_command(prefix, 'read', 'exec-out', 'cat', remote)
            if read.returncode:
                self.native_fault_evidence(prefix)
                raise RuntimeError('Fresh UI capture file unavailable: ' + prefix)
            raw = read.stdout
            assert 0 < len(raw) < 8 << 20, 'Fresh UI capture is empty or unbounded'
            root = ET.fromstring(raw)
            if attempt > 1:
                self.native_fault_evidence(prefix)
                self.record('fresh UI capture after bounded framework idle retry', attempts=attempt,
                            maximum_attempts=3, raw_command_results_preserved=True, stale_xml_used=False)
            (self.args.output / 'last-ui.xml').write_bytes(raw)
            return raw, root
        raise RuntimeError('UI capture retry bound exhausted')

    def dump(self):
        for unused in range(4):
            # Keep driver snapshots outside shared storage so DocumentsUI does
            # not index its own rapidly-changing diagnostic XML as user files.
            raw, root = self.capture_ui()
            alerts = [n for n in root.iter('node') if n.attrib.get('resource-id') == 'android:id/alertTitle']
            external = next((n for n in alerts if n.attrib.get('text') in ("Pixel Launcher isn't responding", "Files isn't responding")), None)
            if external is None:
                if any("isn't responding" in n.attrib.get('text', '') for n in alerts):
                    raise RuntimeError('App or nonallowlisted component ANR; qualification failed without dismissal')
                return root
            self.launcher_anrs += 1
            (self.args.output / ('external-launcher-anr-' + str(self.launcher_anrs) + '.xml')).write_bytes(raw)
            component = self.system_anr_evidence(external.attrib['text'])
            if self.launcher_anrs > 3:
                raise RuntimeError('External Android UI components repeatedly failed to respond')
            wait = next((n for n in root.iter('node') if n.attrib.get('resource-id') == 'android:id/aerr_wait' and n.attrib.get('text') == 'Wait'), None)
            if wait is None:
                raise RuntimeError('Observed external UI ANR has no framework Wait action')
            xy = [int(v) for v in re.findall(r'\d+', wait.attrib['bounds'])]
            self.adb('shell', 'input', 'tap', (xy[0]+xy[2])//2, (xy[1]+xy[3])//2)
            self.record('external Android UI ANR observed and framework Wait selected', external_component=component, occurrence=self.launcher_anrs, native_app_anr_dismissed=False, framework_process_traces_preserved=True)
            time.sleep(.5)
        raise RuntimeError('External Android UI dialog did not clear')

    @staticmethod
    def bounds(node):
        values = [int(v) for v in re.findall(r'-?\d+', node.attrib.get('bounds', ''))]
        return values if len(values) == 4 and values[2] > values[0] and values[3] > values[1] else None

    def controls_bounds(self, root):
        nodes = list(root.iter('node'))
        control = next((n for n in nodes if n.attrib.get('content-desc') == 'Native client controls'), None)
        if control is None:
            control = next((n for n in nodes if n.attrib.get('package') == PACKAGE
                            and n.attrib.get('class') == 'android.widget.ScrollView'), None)
        candidates = [self.bounds(n) for n in nodes if n.attrib.get('package') == PACKAGE]
        candidates = [v for v in candidates if v]
        return self.bounds(control) if control is not None else (max(candidates, key=lambda v:(v[2]-v[0])*(v[3]-v[1])) if candidates else None)

    def tap(self, label, prefix=False, activate=True):
        deadline = time.monotonic() + 30
        swipes = 0
        while time.monotonic() < deadline:
            root = self.dump()
            clip = self.controls_bounds(root)
            disabled = False
            for node in root.iter('node'):
                text = node.attrib.get('text', '').lower()
                if not (text.startswith(label.lower()) if prefix else text == label.lower()):
                    continue
                if node.attrib.get('enabled') != 'true':
                    disabled = True
                    break
                coordinates = self.bounds(node)
                if coordinates is None:
                    continue
                x, y = (coordinates[0]+coordinates[2])//2, (coordinates[1]+coordinates[3])//2
                if clip and not (clip[0] <= x < clip[2] and clip[1] <= y < clip[3]):
                    continue
                if activate:
                    self.adb('shell', 'input', 'tap', x, y)
                return node
            if disabled:
                time.sleep(.2)
                continue
            if clip is None or swipes >= 10:
                break
            x = (clip[0]+clip[2])//2
            low, high = clip[1]+(clip[3]-clip[1])//5, clip[3]-(clip[3]-clip[1])//5
            start, end = (high, low) if swipes % 6 < 3 else (low, high)
            self.adb('shell', 'input', 'swipe', x, start, x, end, '250')
            swipes += 1
            time.sleep(.3)
        raise RuntimeError('UI control not found: ' + label)

    def viewport(self, label, minimum_frames=0):
        def ready(value):
            if not settled_preview(value, minimum_frames):
                return False
            try:
                viewport_contract(value)
                return True
            except AssertionError:
                return False
        value = self.wait_report('native-client-report.json', ready, label + ' settled bounded EGL viewport', seconds=60)
        proof = viewport_contract(value)
        root = self.dump()
        clip = self.controls_bounds(root)
        assert clip, 'Actual controls accessibility viewport is absent'
        controls_height = clip[3]-clip[1]
        assert controls_height*100 <= (controls_height+proof['host_height'])*60+100, 'Controls displaced the reserved scene'
        (self.args.output / (label+'-native-report.json')).write_text(json.dumps(value, indent=2)+'\n')
        self.record('bounded native viewport: '+label, **proof, controls_height=controls_height)
        return value

    def scripted_character_picker(self):
        """Drive the real app against explicit source-layout UDP fixtures only."""
        data = self.args.ui_peer_binary.read_bytes()
        assert self.args.protocol_receipt, 'Scripted UI peer requires its exact Android build receipt'
        receipt = json.loads(self.args.protocol_receipt.read_text())
        peers = [v for v in receipt.get('scripted_ui_peer_artifacts', [])
                 if v.get('abi') == 'x86_64' and v.get('file') == self.args.ui_peer_binary.name]
        assert len(peers) == 1 and peers[0].get('role') == 'scripted-ui-peer'
        assert peers[0]['sha256'] == hashlib.sha256(data).hexdigest()
        remote, report_path = '/data/local/tmp/coh-combined-ui-peer', '/data/local/tmp/coh-combined-ui-peer-report.json'
        staging = '/data/local/tmp/coh-combined-ui-policy.json'
        self.adb('push', self.args.ui_peer_binary, remote)
        self.adb('shell', 'chmod', '700', remote)
        self.adb('shell', 'rm', '-f', report_path)
        process = None
        ready = None
        stop = threading.Event()
        errors = []
        thread = None
        completed = False
        final = None
        log = (self.args.output/'scripted-ui-peer.stderr').open('wb')
        try:
            process = subprocess.Popen([self.args.adb, '-s', self.args.serial, 'shell', remote,
                '--serve', '--report', report_path], stdout=subprocess.PIPE, stderr=log)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                raw, deadline = b'', time.monotonic()+30
                while b'\n' not in raw and time.monotonic() < deadline:
                    if selector.select(.5):
                        chunk = process.stdout.read1(4096)
                        if not chunk: break
                        raw += chunk
                        assert len(raw) <= 4096, 'Scripted peer readiness exceeds its bound'
            (self.args.output/'scripted-ui-peer-ready.stdout').write_bytes(raw)
            assert b'\n' in raw, 'Scripted peer did not publish bounded readiness'
            ready = json.loads(raw.splitlines()[0])
            assert ready.get('scripted_source_layout') is True and ready.get('real_server_interoperability') is False
            assert all(type(ready.get(k)) is int and 0 < ready[k] <= 65535 for k in ('db_port', 'map_port'))
            assert type(ready.get('pid')) is int and ready['pid'] > 0
            policy_file = self.args.output/'scripted-ui-policy.json'
            def refresh():
                elapsed = int(float(self.adb('shell','cat','/proc/uptime',timeout=5).stdout.split()[0])*1000)
                policy = {'schema':'coh-native-local-policy-v1', 'state':'ready', 'db_address':'127.0.0.1',
                    'db_port':ready['db_port'], 'net_version':5, 'account':'Fixture',
                    'server_session_id':'f'*32, 'import_generation':'e'*32,
                    'ready_elapsed_ms':elapsed, 'encryption_required':False, 'outbound_compressed':False}
                policy_file.write_text(json.dumps(policy)+'\n')
                self.adb('push', policy_file, staging,timeout=5)
                self.adb('shell','run-as',PACKAGE,'cp',staging,'files/native-session-policy.json.tmp',timeout=5)
                self.adb('shell','run-as',PACKAGE,'mv','files/native-session-policy.json.tmp','files/native-session-policy.json',timeout=5)
            refresh()
            def maintain():
                while not stop.wait(2):
                    try: refresh()
                    except Exception as failure:
                        errors.append(str(failure));return
            thread = threading.Thread(target=maintain, daemon=True);thread.start()
            self.tap('Connect local server')
            characters = self.wait_report('native-client-report.json', lambda x:x.get('server_protocol',{}).get('phase') == 'CHARACTERS_READY', 'actual native app DB list from explicit scripted UDP peer')
            map_report_contract(characters['server_protocol'])
            self.tap('Native Fixture', prefix=True, activate=False)
            before = self.viewport('character-picker-visible', characters['native']['frames']+30)
            assert before['server_protocol']['phase'] == 'CHARACTERS_READY'
            (self.args.output/'character-picker-visible.png').write_bytes(self.adb('exec-out','screencap','-p').stdout)
            self.tap('Native Fixture', prefix=True)
            selected = self.wait_report('native-client-report.json', lambda x:x.get('server_protocol',{}).get('phase') == 'SCENE_INCOMPLETE', 'actual character selection and bounded Map scene prefix', seconds=60)
            protocol = selected['server_protocol']; proof = map_report_contract(protocol)
            assert protocol['character_lists'] == 1 and protocol['character_choices'] == 1 and protocol['map_handoffs'] == 1
            assert protocol['terminal_failure'] == 0 and protocol['map_protocol']['scene_prefixes'] >= 1
            mapping = protocol['map_protocol']
            assert (mapping['accepted_messages'],mapping['phase'],mapping['stage'],mapping['last_status'],
                    mapping['last_command_valid'],mapping['last_command']) == (2,5,6,2,1,6)
            assert mapping['udp']['link']['queue_limits'] == 0
            self.viewport('after-character-selection', before['native']['frames']+5)
            peer_raw = self.adb('exec-out','cat',report_path).stdout
            assert 0 < len(peer_raw) <= 16384
            peer = json.loads(peer_raw)
            assert peer.get('scripted_source_layout') is True and peer.get('real_server_interoperability') is False
            assert peer.get('authserver_authenticated') is False and peer.get('live_world') is False and peer.get('failed') is False
            assert all(peer.get(k) == 1 for k in ('character_lists','character_choices','map_handoffs','map_connects','source_command_catalogs','scene_prefixes'))
            assert peer.get('source_command_count') == 915 and peer.get('selected_wire_slot') == 0
            (self.args.output/'scripted-ui-peer-report.json').write_bytes(peer_raw)
            assert not errors, 'Scripted policy refresh failed: '+repr(errors)
            self.record('actual app character picker and native DB-to-Map scene boundary', **proof,
                peer_binary_sha256=hashlib.sha256(data).hexdigest(), scripted_source_layout=True,
                real_server_interoperability=False, real_authenticated_session=False, preview_is_server_world=False)
            self.tap('Disconnect client')
            completed = True
        finally:
            stop.set()
            if thread:
                thread.join(timeout=25)
                if thread.is_alive(): errors.append('Scripted policy refresher exceeded bounded ADB shutdown')
            try:
                if ready:
                    cmdline = self.adb('exec-out','cat','/proc/'+str(ready['pid'])+'/cmdline',check=False).stdout
                    if cmdline.split(b'\0')[0] == remote.encode():
                        self.adb('shell','kill','-TERM',ready['pid'],check=False)
                if process:
                    try:
                        remaining, unused = process.communicate(timeout=10)
                        (self.args.output/'scripted-ui-peer-final.stdout').write_bytes(remaining)
                    except subprocess.TimeoutExpired:
                        process.terminate();process.communicate(timeout=5)
                if ready:
                    final = self.adb('exec-out','cat',report_path,check=False)
                    (self.args.output/'scripted-ui-peer-final-report.json').write_bytes(final.stdout)
            except Exception as failure:
                errors.append('Peer cleanup: '+str(failure))
            finally:
                log.close()
                for command in (
                    ('shell','run-as',PACKAGE,'rm','-f','files/native-session-policy.json','files/native-session-policy.json.tmp'),
                    ('shell','rm','-f',remote,report_path,staging),
                ):
                    try:
                        result = self.adb(*command,check=False)
                        if result.returncode: errors.append('Fixture cleanup returned '+str(result.returncode))
                    except Exception as failure:
                        errors.append('Fixture cleanup: '+str(failure))
        assert not errors, 'Scripted fixture lifecycle failure: '+repr(errors)
        assert completed and process.returncode == 0 and final is not None and final.returncode == 0, 'Scripted peer did not exit cleanly'
        final_peer = json.loads(final.stdout)
        assert final_peer['closed_sockets'] == final_peer['opened_sockets'] == 2
        assert final_peer['failed'] is False
        self.record('scripted UI peer lifecycle cleanup', opened_sockets=2, closed_sockets=2,
                    fixture_policy_removed=True, real_server_interoperability=False)

    def report(self, filename):
        r = self.adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/' + filename, check=False)
        if r.returncode:
            return None
        assert len(r.stdout) < 8 << 20
        try:
            value = json.loads(r.stdout)
        except (ValueError, UnicodeDecodeError):
            return None
        (self.args.output / filename).write_bytes(r.stdout)
        return value

    def wait_report(self, filename, predicate, label, seconds=45):
        deadline = time.monotonic() + seconds
        value = None
        while time.monotonic() < deadline:
            value = self.report(filename)
            if value is not None and predicate(value):
                return value
            time.sleep(.2)
        raise RuntimeError(label + ' failed: ' + json.dumps(value)[:3000])

    def launch(self, activity):
        result = self.text('shell', 'am', 'start', '-W', '-n', activity)
        assert re.search(r'^Status:\s*ok\s*$', result, re.M), result
        assert not re.search(r'^(Error|Exception|Failure)', result, re.M), result

    def picker_cancel(self, label):
        self.tap(label)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            root = self.dump()
            if any('documentsui' in n.attrib.get('package', '') for n in root.iter('node')):
                break
            time.sleep(.2)
        else:
            raise RuntimeError('Actual SAF provider UI did not open: ' + label)
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            root = self.dump()
            if any(n.attrib.get('package') == PACKAGE for n in root.iter('node')):
                self.record('framework SAF cancellation and app return', control=label)
                return
            time.sleep(.2)
        raise RuntimeError('SAF cancellation did not return to the app: ' + label)

    def select_document(self, control, filename):
        self.tap(control)
        deadline = time.monotonic() + 25
        selected = False
        trace = []
        while time.monotonic() < deadline:
            nodes = list(self.dump().iter('node'))
            picker = any('documentsui' in n.attrib.get('package', '') for n in nodes)
            if selected and not picker and any(n.attrib.get('package') == PACKAGE for n in nodes):
                (self.args.output / 'picker-selection-history.json').write_text(json.dumps(trace, indent=2) + '\n')
                return
            if not picker:
                time.sleep(.2)
                continue
            # Android includes the obscured file list in its accessibility tree
            # while the navigation drawer is open. Select its foreground root
            # before considering any file row behind that drawer.
            drawer = any(n.attrib.get('text', '').lower() == 'open from' for n in nodes)
            target = None
            if drawer:
                target = next((n for n in nodes if n.attrib.get('text', '').lower() == 'downloads' and n.attrib.get('resource-id') == 'android:id/title'), None)
            else:
                target = next((n for n in nodes if n.attrib.get('text') == filename), None)
                if target is None:
                    target = next((n for n in nodes if n.attrib.get('content-desc', '').lower() in ('show roots', 'open navigation drawer')), None)
            if target is not None:
                xy = [int(v) for v in re.findall(r'\d+', target.attrib['bounds'])]
                selected = not drawer and target.attrib.get('text') == filename
                trace.append({'drawer_open': drawer, 'target_text': target.attrib.get('text'), 'target_description': target.attrib.get('content-desc'), 'selected_file': selected, 'bounds': xy})
                self.adb('shell', 'input', 'tap', (xy[0]+xy[2])//2, (xy[1]+xy[3])//2)
            time.sleep(.3)
        (self.args.output / 'picker-selection-history.json').write_text(json.dumps(trace, indent=2) + '\n')
        raise RuntimeError('SAF document selection never returned to the app: ' + filename)

    def import_donor(self):
        from prepare import DONOR_SHA, DONOR_BYTES, verify
        verify(self.args.donor_apk, DONOR_SHA, DONOR_BYTES)
        donor_name = 'native-test-donor.apk'
        invalid = self.args.output / 'native-invalid.apk'
        invalid.write_bytes(b'Untrusted donor APK must be rejected before publication.\n')
        for path, name in ((self.args.donor_apk, donor_name), (invalid, invalid.name)):
            self.adb('push', path, '/sdcard/Download/' + name)
            self.adb('shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', 'file:///sdcard/Download/' + name)
        before_fds = self.app_fd_count()
        self.select_document('Import launcher APK', donor_name)
        value = self.wait_report('combined-report.json', lambda x: x.get('busy') is False and 'Server payload: verified' in x.get('imports', ''), 'real pinned donor APK SAF import', seconds=90)
        assert value['runtime_ready'] is False and value['server']['ready'] is False
        accepted = 'files/combined-import/donor-' + DONOR_SHA + '/accepted.sha256'
        assert self.text('exec-out', 'run-as', PACKAGE, 'cat', accepted) == DONOR_SHA + '\n'
        self.record('actual pinned donor APK imported through SAF', bytes=DONOR_BYTES, sha256=DONOR_SHA)
        first_fds = self.app_fd_count()
        import zipfile
        with zipfile.ZipFile(self.args.apk) as apk:
            contract = json.loads(apk.read('assets/combined/import-contract.json'))
        members = contract['donor_files']
        assert 0 < len(members) <= 128
        directory = 'files/combined-import/donor-' + DONOR_SHA + '/'
        paths = [directory + name.removeprefix('assets/runtime/') for name in sorted(members)]
        modes = self.text('exec-out', 'run-as', PACKAGE, 'stat', '-c', '%a', *paths).split()
        assert len(modes) == len(paths) and all(re.fullmatch(r'[0-7]{3,4}', value) for value in modes)
        assert all(int(value, 8) & 0o222 == 0 for value in modes), 'Imported pinned donor payload remains writable'
        fx = self.adb('exec-out', 'run-as', PACKAGE, 'cat', directory + 'server-fx-catalog.bin').stdout
        assert len(fx) == 3380680 and hashlib.sha256(fx).hexdigest() == 'ab97aa3d9ec2a8edf1ea77d3c807e630e21c3d78555b3650bf80c1025bce8890'
        self.record('actual imported donor payload sealed with original FX bytes', payload_files=len(paths),
                    write_permission_bits=0, fx_bytes=len(fx), fx_sha256=hashlib.sha256(fx).hexdigest())
        prior_events = len(value.get('events', []))
        self.select_document('Import launcher APK', donor_name)
        value = self.wait_report('combined-report.json', lambda x: x.get('busy') is False
            and len(x.get('events', [])) > prior_events and 'Server payload: verified' in x.get('imports', ''),
            'repeated complete pinned donor SAF import', seconds=90)
        repeated_fds = self.app_fd_count()
        fd_proof = {'before': before_fds, 'after_first': first_fds, 'after_repeat': repeated_fds,
                    'complete_imports': 2, 'first_import_growth_limit': 32, 'repeat_growth_limit': 8,
                    'scope': 'Actual app descriptor counts across two complete SAF donor imports, allowing bounded framework/provider cache growth; no guest server execution.'}
        if all(item['available'] for item in (before_fds, first_fds, repeated_fds)):
            assert before_fds['pid'] == first_fds['pid'] == repeated_fds['pid'], 'App process changed during imports'
            assert first_fds['count'] <= before_fds['count'] + 32, 'First donor import retained excessive descriptors'
            assert repeated_fds['count'] <= first_fds['count'] + 8, 'Repeated donor import retained descriptors'
            fd_proof['bounded_growth_verified'] = True
        else:
            fd_proof['bounded_growth_verified'] = False
        (self.args.output / 'donor-import-fd-proof.json').write_text(json.dumps(fd_proof, indent=2) + '\n')
        self.record('repeated donor import descriptor observation', **fd_proof)
        old_events = len(value.get('events', []))
        self.select_document('Import launcher APK', invalid.name)
        after = self.wait_report('combined-report.json', lambda x: x.get('busy') is False and len(x.get('events', [])) > old_events and str(x.get('server', {}).get('phase', '')).lower() == 'failed', 'untrusted donor APK admission refusal')
        assert 'Server payload: verified' in after['imports']
        assert self.text('exec-out', 'run-as', PACKAGE, 'cat', accepted) == DONOR_SHA + '\n'
        self.record('untrusted donor refused and previous accepted payload preserved')

    def app_fd_count(self):
        pid = self.text('shell', 'pidof', '-s', PACKAGE).strip()
        assert re.fullmatch(r'[1-9][0-9]*', pid), 'Expected app process is absent'
        result = self.adb('exec-out', 'run-as', PACKAGE, 'ls', '/proc/' + pid + '/fd', check=False)
        if result.returncode:
            return {'available': False, 'reason': 'run_as_proc_access_unavailable'}
        values = result.stdout.decode().split()
        assert 0 < len(values) < 4096 and all(v.isdigit() for v in values), 'Unexpected app descriptor inventory'
        return {'available': True, 'pid': int(pid), 'count': len(values)}

    def retain_failed_attempt(self, failed):
        session = failed.get('server', {}).get('session_id', '')
        assert re.fullmatch(r'[0-9a-f]{32}', session), 'Failed admission did not record its attempt identity'
        # run() has already proved this is a fresh disposable emulator. Preserve
        # its data while exercising Android's actual force-stop/relaunch path.
        self.adb('shell', 'am', 'force-stop', PACKAGE)
        self.launch(MAIN)
        current = self.wait_report('combined-report.json', lambda x: x.get('server', {}).get('session_id') != session
            and x.get('server', {}).get('owned_process_alive') is False, 'fresh report after force-stop and relaunch')
        memory_report_contract(current)
        (self.args.output / 'combined-server').mkdir(exist_ok=True)
        history = self.wait_report('combined-server/previous-attempts.json', lambda x: any(
            item.get('session_id') == session for item in x.get('attempts', [])), 'prior attempt retained after framework relaunch')
        assert history.get('format') == 1 and history.get('maximum_attempts') == 4
        assert isinstance(history.get('attempts'), list) and 0 < len(history['attempts']) <= 4
        saved = next(item for item in history['attempts'] if item.get('session_id') == session)
        assert saved['app']['package'] == PACKAGE and saved['app']['server']['session_id'] == session
        assert 'guest' not in saved, 'Missing-import admission unexpectedly generated a guest report'
        memory_report_contract(saved['app'])
        self.record('failed attempt survives actual force-stop and relaunch', retained_attempts=len(history['attempts']),
                    android_exit_records=len(current['android_process_exits']),
                    scope='Framework force-stop retention with data preserved; this does not simulate or qualify Android low-memory killing or guest startup.')

    def save_document(self):
        deadline = time.monotonic() + 25
        saved = False
        while time.monotonic() < deadline and not saved:
            nodes = list(self.dump().iter('node'))
            candidates = [n for n in nodes if n.attrib.get('text', '').lower() == 'save' and n.attrib.get('enabled') == 'true']
            is_save = bool(candidates)
            if not candidates:
                candidates = [n for n in nodes if n.attrib.get('text', '').lower() == 'downloads' and n.attrib.get('enabled') == 'true']
            if not candidates:
                candidates = [n for n in nodes if n.attrib.get('content-desc', '').lower() in ('show roots', 'open navigation drawer')]
            if candidates:
                xy = [int(v) for v in re.findall(r'\d+', candidates[0].attrib['bounds'])]
                self.adb('shell', 'input', 'tap', (xy[0]+xy[2])//2, (xy[1]+xy[3])//2)
                saved = is_save
            time.sleep(.3)
        assert saved, 'Real CREATE_DOCUMENT Save unavailable'

    def export_native(self):
        before = self.report('native-client-report.json')
        self.tap('Export report')
        self.save_document()
        self.wait_report('native-client-report.json', lambda x: x.get('session_id') == before['session_id'] and any(e.get('type') == 'export_complete' for e in x.get('events', [])), 'actual native JSON export callback')
        files = self.text('shell', 'find', '/sdcard/Download', '-maxdepth', '1', '-name', 'COH-NativeCombined-*.json').splitlines()
        assert len(files) == 1
        raw = self.adb('exec-out', 'cat', files[0]).stdout
        assert 0 < len(raw) < 8 << 20
        exported = json.loads(raw)
        assert exported['session_id'] == before['session_id'] and exported['assets_verified'] is True
        assert exported['preview_is_server_world'] is False
        assert exported['native']['frames'] >= before['native']['frames']
        (self.args.output / 'exported-native-report.json').write_bytes(raw)
        self.record('actual framework JSON document export', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def export_retained_native_fixture(self):
        """Exercise actual SAF ZIP provenance labeling with an explicit fixture."""
        self.wait_report('native-client-report.json', lambda x:x.get('resumed') is False,
                         'native Activity stops before retained-report export fixture')
        original = self.adb('exec-out','run-as',PACKAGE,'cat','files/native-client-report.json').stdout
        fixture = copy.deepcopy(json.loads(original))
        assert fixture.get('device',{}).get('emulator_detected') is True
        fixture['app'].update(version_code=3, version_name='0.1.2-local-server-native',
            installed_apk={'bytes':11519003,'sha256':'1913613656032400ee7ba70a46d56242567d23040b896032ad8a9bc90e9ae449'})
        fixture['qualification_fixture'] = {'type':'retained_native_version_label',
            'scripted':True, 'physical_device_evidence':False}
        path = self.args.output/'scripted-retained-native-report.json'
        path.write_text(json.dumps(fixture)+'\n')
        backup = self.args.output/'native-report-before-scripted-export.json';backup.write_bytes(original)
        remote = '/data/local/tmp/coh-retained-native-export.json'
        def publish(source):
            self.adb('push',source,remote)
            self.adb('shell','run-as',PACKAGE,'cp',remote,'files/native-client-report.json.tmp')
            self.adb('shell','run-as',PACKAGE,'mv','files/native-client-report.json.tmp','files/native-client-report.json')
        try:
            publish(path)
            before = set(self.text('shell','find','/sdcard/Download','-maxdepth','1','-name','COH-NativeCombined-*.zip').splitlines())
            self.tap('Export report');self.save_document()
            deadline = time.monotonic()+30
            exported = None
            while time.monotonic() < deadline:
                files = set(self.text('shell','find','/sdcard/Download','-maxdepth','1','-name','COH-NativeCombined-*.zip').splitlines())-before
                if len(files) == 1:
                    raw = self.adb('exec-out','cat',next(iter(files))).stdout
                    assert len(raw) <= 8 << 20
                    try:
                        from io import BytesIO
                        with zipfile.ZipFile(BytesIO(raw)) as archive:
                            assert archive.testzip() is None
                            candidate = json.loads(archive.read('combined-report.json'))
                            assert 'native-client-report.json' not in archive.namelist(), 'Historical native report was mislabeled current'
                            retained = json.loads(archive.read('previous-app-native-client-report.json'))
                            assert retained == fixture, 'Historical native report was modified or discarded'
                            exported = candidate
                            break
                    except (zipfile.BadZipFile, KeyError):
                        pass  # CREATE_DOCUMENT may expose its file before ZipOutputStream closes.
                time.sleep(.2)
            assert exported is not None, 'Actual launcher ZIP export never completed'
            installed_apk_contract(exported,hashlib.sha256(self.args.apk.read_bytes()).hexdigest(),self.args.apk.stat().st_size)
            memory_report_contract(exported)
            (self.args.output/'exported-launcher-report.zip').write_bytes(raw)
            self.record('actual SAF ZIP separates scripted retained native report from current APK',
                historical_entry='previous-app-native-client-report.json', scripted_fixture=True,
                historical_version_code=3, current_version_code=exported['version_code'],
                bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), physical_device_evidence=False)
        finally:
            try:
                publish(backup)
                restored = self.adb('exec-out','run-as',PACKAGE,'cat','files/native-client-report.json').stdout
                assert restored == original, 'Original native report was not restored after fixture qualification'
            finally:
                self.adb('shell','rm','-f',remote,check=False)

    def capture_visible_scene(self, minimum_frames):
        before = self.wait_report('native-client-report.json', lambda x: settled_preview(x, minimum_frames), 'foreground preview finishes new-context GPU reconstruction and advancing presentation', seconds=60)
        root = self.dump()
        before = self.wait_report('native-client-report.json', lambda x: settled_preview(x, minimum_frames), 'foreground preview stays settled after UI-bound observation', seconds=30)
        area = before['input_area']
        ui_surface = [n.attrib.get('bounds') for n in root.iter('node') if n.attrib.get('class') == 'android.view.SurfaceView']
        raw = self.adb('exec-out', 'screencap', '-p').stdout
        (self.args.output / 'native-preview.png').write_bytes(raw)
        proof, crop = scene_pixels(raw, area)
        crop.save(self.args.output / 'native-preview-surface.png')
        after = self.report('native-client-report.json')
        proof.update(uiautomator_surface_bounds=ui_surface, bounds_source='SurfaceView.getLocationOnScreen/getWidth/getHeight in input_area; crop uses left,top,left+width,top+height', screenshot_sha256=hashlib.sha256(raw).hexdigest(),
                     before_frames=before['native']['frames'],
                     before_context=before['native']['contexts_started'],
                     before_gpu_bytes=before['native']['static_renderer']['gpu_bytes'])
        (self.args.output / 'foreground-scene-report.json').write_text(json.dumps(before,indent=2)+'\n')
        (self.args.output / 'scene-pixel-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        assert proof['passed'], 'Actual Surface screenshot contains no sufficiently nonuniform visible scene'
        assert after is not None and settled_preview(after, minimum_frames)
        assert after['native']['contexts_started'] == before['native']['contexts_started']
        assert after['input_area'] == area
        self.record('current foreground GPU resources and actual on-screen scene pixels', frames=before['native']['frames'],
                    context=before['native']['contexts_started'], gpu_bytes=proof['before_gpu_bytes'],
                    bright_pixels=proof['bright_pixels'], distinct_colors_at_least=proof['distinct_colors_at_least'],
                    screenshot_sha256=proof['screenshot_sha256'])

    def run(self):
        assert self.text('shell', 'getprop', 'ro.boot.qemu').strip() == '1', 'Qualification is limited to its disposable CI emulator'
        assert self.text('shell', 'getprop', 'ro.product.cpu.abi').strip() == 'x86_64'
        assert not self.text('shell', 'pm', 'list', 'packages', '--user', '0', PACKAGE).strip(), 'Require fresh disposable emulator; never clear user data'
        print(json.dumps({'stage':'cold_boot_settle','seconds':30,'scope':'Allow first-boot Android system providers to settle before installing the app'}), flush=True)
        time.sleep(30)
        installed = self.text('install', '-g', self.args.apk)
        assert re.search(r'^Success\s*$', installed, re.M)
        self.launch(MAIN)
        time.sleep(.5)
        self.record('fresh install and exact main Activity', apk_sha256=hashlib.sha256(self.args.apk.read_bytes()).hexdigest())
        initial = self.wait_report('combined-report.json', lambda x: 'Server payload:' in x.get('imports', '') or any(e.get('name') == 'operation_failed' for e in x.get('events', [])), 'fresh app import initialization')
        (self.args.output / 'initial-combined-report.json').write_text(json.dumps(initial, indent=2) + '\n')
        assert not any(e.get('name') == 'operation_failed' for e in initial.get('events', [])), 'Fresh app import initialization failed: ' + initial.get('message', '')
        identity = self.wait_report('combined-report.json', lambda x:x.get('installed_apk_status') == 'ready',
                                    'cached current APK identity becomes ready')
        self.record('current launcher APK identity matches exact installed package', **installed_apk_contract(identity,
                    hashlib.sha256(self.args.apk.read_bytes()).hexdigest(),self.args.apk.stat().st_size))
        assert 'Server payload: import ' in initial['imports'] and 'Game files: import all four asset parts' in initial['imports']
        assert initial['runtime_ready'] is False and initial['server']['ready'] is False
        self.record('fresh app initialized for external imports without failures')
        self.record('bounded public memory and Android exit diagnostics', **memory_report_contract(initial))
        for label in ('Import launcher APK', 'Import game asset part'):
            self.picker_cancel(label)
        # These controls must fail closed without imported runtime/assets. Inspect
        # the actual app diagnostic state, not merely an on-screen status label.
        self.tap('Set up runtime')
        time.sleep(.5)
        self.tap('Start server')
        time.sleep(.5)
        state = self.wait_report('combined-report.json', lambda x: x.get('busy') is False
            and re.fullmatch(r'[0-9a-f]{32}', x.get('server', {}).get('session_id', ''))
            and x.get('server', {}).get('ready') is False
            and str(x.get('server', {}).get('phase', '')).upper() not in ('READY', 'STARTING', 'RUNNING'), 'missing-import admission remains closed')
        assert state.get('runtime_ready') is False
        assert str(state.get('server', {}).get('phase', '')).upper() not in ('READY', 'STARTING', 'RUNNING')
        self.record('missing imports refuse setup and server start', runtime_ready=False, server_ready=False)
        self.retain_failed_attempt(state)
        if self.args.donor_apk:
            self.import_donor()
        self.tap('Launch native client')
        current = self.wait_report('native-client-report.json', lambda x: x.get('assets_verified') is True and x.get('native', {}).get('frames', 0) >= 30, 'actual native scene preview frames')
        native = current['native']
        assert current.get('failure') is None and current.get('report_write_failed') is False
        assert native.get('gl_errors') == 0 and native.get('static_renderer', {}).get('tf_mismatches') == 0
        assert current.get('preview_is_server_world') is False
        self.viewport('initial-preview', native['frames'])
        self.tap('Connect local server')
        self.wait_report('native-client-report.json', lambda x: x.get('server_protocol', {}).get('phase') == 'POLICY_UNAVAILABLE', 'native connect refuses missing owned server lease')
        self.record('native connection refuses absent server lease', actual_server_interoperability_verified=False)
        self.record('native preview actual GLES frames', frames=native['frames'], gl_errors=native['gl_errors'])
        self.adb('shell','settings','put','system','accelerometer_rotation','0')
        self.adb('shell','settings','put','system','user_rotation','1')
        landscape = self.wait_report('native-client-report.json', lambda x:
            settled_preview(x, native['frames']+10) and x.get('viewport_policy',{}).get('host_width',0)
            > x.get('viewport_policy',{}).get('host_height',16384), 'actual landscape native preview after framework rotation', seconds=60)
        assert self.dump().attrib.get('rotation') == '1', 'Framework did not rotate into landscape'
        self.viewport('landscape-preview', landscape['native']['frames'])
        if self.args.ui_peer_binary:
            self.scripted_character_picker()
        current = self.report('native-client-report.json')
        native = current['native']
        first = native.get('contexts_started', 1)
        first_count = native['stream']['selected_instances']
        assert first_count in (6, 11)
        self.tap('View distance')
        changed = self.wait_report('native-client-report.json', lambda x: x.get('native', {}).get('frames', 0) > native['frames'] + 10 and x.get('native', {}).get('stream', {}).get('selected_instances') == (11 if first_count == 6 else 6), 'preview actual Near/Far instance selection')
        self.tap('Recreate')
        self.wait_report('native-client-report.json', lambda x: x.get('native', {}).get('contexts_started', 0) > first, 'actual preview Surface recreation')
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        self.wait_report('native-client-report.json', lambda x: x.get('resumed') is False, 'framework Home pauses native preview')
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_APP_SWITCH')
        time.sleep(.5)
        recent = self.dump()
        card = next((n for n in recent.iter('node') if n.attrib.get('resource-id', '').endswith('/snapshot')), None)
        if card is None:
            self.adb('shell', 'input', 'keyevent', 'KEYCODE_APP_SWITCH')
        else:
            xy = [int(v) for v in re.findall(r'\d+', card.attrib['bounds'])]
            self.adb('shell', 'input', 'tap', (xy[0]+xy[2])//2, (xy[1]+xy[3])//2)
        self.wait_report('native-client-report.json', lambda x: x.get('resumed') is True and x.get('native', {}).get('frames', 0) > changed['native']['frames'], 'native preview Home recovery')
        self.record('framework view distance, Surface recreation and Home recovery')
        before_export = self.report('native-client-report.json')
        self.export_native()
        self.capture_visible_scene(before_export['native']['frames'] + 10)
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
        self.export_retained_native_fixture()
        if self.args.protocol_binary:
            data = self.args.protocol_binary.read_bytes()
            if self.args.protocol_receipt:
                receipt = json.loads(self.args.protocol_receipt.read_text())
                candidates = [v for v in receipt.get('artifacts', []) if v.get('abi') == 'x86_64' and v.get('file') == self.args.protocol_binary.name]
                assert len(candidates) == 1 and candidates[0]['sha256'] == hashlib.sha256(data).hexdigest()
            remote = '/data/local/tmp/coh-combined-local-contract'
            try:
                self.adb('push', self.args.protocol_binary, remote)
                self.adb('shell', 'chmod', '700', remote)
                result = self.text('shell', remote)
                value = json.loads(result)
                assert value['passed'] is True and value['checks'] >= 400 and value['socket_scenarios'] >= 6
                assert value['actual_os_udp'] is True and value['full_scripted_db_map_chain'] is True
                assert value['real_server_interoperability'] is False and value['real_authenticated_session'] is False
                (self.args.output / 'local-protocol-android.json').write_text(json.dumps(value, indent=2) + '\n')
                self.record('Android native UDP DB-to-Map controller', checks=value['checks'], socket_scenarios=value['socket_scenarios'], real_server_interoperability=False)
            finally:
                self.adb('shell', 'rm', '-f', remote, check=False)
        self.native_fault_evidence('final-app-fault-audit')
        self.record('no app crash or ANR recorded')
        value = {'format': 1, 'status': 'passed', 'checks': self.proofs, 'device': {'api': self.text('shell', 'getprop', 'ro.build.version.sdk').strip(), 'abi': 'x86_64', 'emulator': True}, 'physical_thor_accepted': False, 'actual_server_interoperability_verified': False, 'real_authenticated_session': False, 'scope': 'Consolidated app Android framework imports, native preview GLES, landscape viewport and lifecycle; optional source-layout UDP peer drives the actual app character picker to its bounded Map scene prefix. This does not qualify ARM64 guest execution, a real authenticated session or live-world rendering.'}
        (self.args.output / 'receipt.json').write_text(json.dumps(value, indent=2) + '\n')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb', default='adb')
    p.add_argument('--serial', required=True)
    p.add_argument('--apk', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--protocol-binary', type=Path)
    p.add_argument('--donor-apk', type=Path)
    p.add_argument('--protocol-receipt', type=Path)
    p.add_argument('--ui-peer-binary', type=Path, help='Exact receipt-pinned source-layout UDP peer; does not qualify a real server session')
    args = p.parse_args()
    driver = Check(args)
    try:
        driver.run()
    except Exception as failure:
        (args.output / 'failure.json').write_text(json.dumps({'type':type(failure).__name__,'message':str(failure),'actual_server_interoperability_verified':False},indent=2)+'\n')
        for name, command in (
            ('failure-lastanr.txt', ('shell','dumpsys','activity','lastanr')),
            ('failure-events.txt', ('logcat','-d','-b','events','-s','am_anr','am_crash')),
            ('failure-crashes.txt', ('logcat','-d','-b','crash')),
            ('failure-window.txt', ('shell','dumpsys','window','windows')),
        ):
            try:
                (args.output / name).write_bytes(driver.adb(*command,check=False).stdout)
            except Exception:
                pass
        try:
            (args.output / 'failure.png').write_bytes(driver.adb('exec-out','screencap','-p',check=False).stdout)
        except Exception:
            pass
        raise


if __name__ == '__main__':
    main()
