#!/usr/bin/env python3
"""Framework qualification on a disposable Android 13 x86_64 emulator.

This exercises actual Activities, SAF cancellation and native preview rendering.
The optional UDP executable uses scripted source-layout peers and never claims a
real database/account/map session. ARM64 guest servers require device acceptance.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET

PACKAGE = 'org.coh.nativecombined'
MAIN = PACKAGE + '/.MainActivity'
NATIVE = PACKAGE + '/.NativeClientActivity'


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
        args.output.mkdir(parents=True, exist_ok=True)

    def adb(self, *args, check=True):
        r = subprocess.run([self.args.adb, '-s', self.args.serial, *map(str, args)], capture_output=True, timeout=45)
        if check and r.returncode:
            raise RuntimeError('ADB command failed: ' + repr(args) + '\n' + r.stderr.decode(errors='replace'))
        return r

    def text(self, *args, check=True):
        return self.adb(*args, check=check).stdout.decode(errors='replace')

    def record(self, name, **details):
        item = {'check': name, 'passed': True, **details}
        self.proofs.append(item)
        (self.args.output / 'progress.json').write_text(json.dumps(self.proofs, indent=2) + '\n')
        print(json.dumps(item), flush=True)

    def system_anr_evidence(self, label):
        last = self.text('shell', 'dumpsys', 'activity', 'lastanr', check=False)
        events = self.text('logcat', '-d', '-b', 'events', '-s', 'am_anr', 'am_crash', check=False)
        prefix = 'external-anr-' + str(self.launcher_anrs)
        (self.args.output / (prefix + '-lastanr.txt')).write_text(last)
        (self.args.output / (prefix + '-events.txt')).write_text(events)
        # A CoH app ANR anywhere in this fresh disposable session invalidates the
        # run even if an external system process also displayed a dialog.
        native_anr = re.search(r'ANR in ' + re.escape(PACKAGE) + r'(?:[\s(/]|$)', last)
        native_event = re.search(r'am_(?:anr|crash)[^\n]*[,\[]' + re.escape(PACKAGE) + r'[,\]]', events)
        if native_anr or native_event:
            raise RuntimeError('Native app ANR found in framework diagnostics; no dismissal')
        if label == "Files isn't responding":
            packages = ('com.google.android.documentsui', 'com.android.documentsui')
            identified = next((p for p in packages if re.search(r'ANR in ' + re.escape(p) + r'(?:[\s(/]|$)', last)), None)
            if identified is None:
                identified = next((p for p in packages if re.search(r'am_anr[^\n]*[,\[]' + re.escape(p) + r'[,\]]', events)), None)
            if identified is None:
                raise RuntimeError('Files ANR process was not positively identified; traces preserved without dismissal')
            return identified
        return 'com.google.android.apps.nexuslauncher'

    def dump(self):
        for unused in range(4):
            # Keep driver snapshots outside shared storage so DocumentsUI does
            # not index its own rapidly-changing diagnostic XML as user files.
            self.adb('shell', 'uiautomator', 'dump', '/data/local/tmp/combined-ui.xml')
            raw = self.adb('exec-out', 'cat', '/data/local/tmp/combined-ui.xml').stdout
            (self.args.output / 'last-ui.xml').write_bytes(raw)
            root = ET.fromstring(raw)
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

    def tap(self, label):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            root = self.dump()
            disabled = False
            for node in root.iter('node'):
                if node.attrib.get('text', '').lower() != label.lower():
                    continue
                if node.attrib.get('enabled') != 'true':
                    disabled = True
                    break
                coordinates = [int(v) for v in re.findall(r'\d+', node.attrib['bounds'])]
                self.adb('shell', 'input', 'tap', (coordinates[0]+coordinates[2])//2, (coordinates[1]+coordinates[3])//2)
                return
            if disabled:
                time.sleep(.2)
                continue
            self.adb('shell', 'input', 'swipe', '500', '1400', '500', '600', '250')
            time.sleep(.3)
        raise RuntimeError('UI control not found: ' + label)

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
        before = self.report('combined-report.json')
        self.select_document('Import launcher APK', donor_name)
        value = self.wait_report('combined-report.json', lambda x: x.get('busy') is False and 'Server payload: verified' in x.get('imports', ''), 'real pinned donor APK SAF import', seconds=90)
        assert value['runtime_ready'] is False and value['server']['ready'] is False
        accepted = 'files/combined-import/donor-' + DONOR_SHA + '/accepted.sha256'
        assert self.text('exec-out', 'run-as', PACKAGE, 'cat', accepted) == DONOR_SHA + '\n'
        self.record('actual pinned donor APK imported through SAF', bytes=DONOR_BYTES, sha256=DONOR_SHA)
        old_events = len(value.get('events', []))
        self.select_document('Import launcher APK', invalid.name)
        after = self.wait_report('combined-report.json', lambda x: x.get('busy') is False and len(x.get('events', [])) > old_events and str(x.get('server', {}).get('phase', '')).lower() == 'failed', 'untrusted donor APK admission refusal')
        assert 'Server payload: verified' in after['imports']
        assert self.text('exec-out', 'run-as', PACKAGE, 'cat', accepted) == DONOR_SHA + '\n'
        self.record('untrusted donor refused and previous accepted payload preserved')

    def export_native(self):
        before = self.report('native-client-report.json')
        self.tap('Export report')
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
        assert 'Server payload: import ' in initial['imports'] and 'Game files: import all four asset parts' in initial['imports']
        assert initial['runtime_ready'] is False and initial['server']['ready'] is False
        self.record('fresh app initialized for external imports without failures')
        for label in ('Import launcher APK', 'Import game asset part'):
            self.picker_cancel(label)
        # These controls must fail closed without imported runtime/assets. Inspect
        # the actual app diagnostic state, not merely an on-screen status label.
        self.tap('Set up runtime')
        time.sleep(.5)
        self.tap('Start server')
        time.sleep(.5)
        state = self.wait_report('combined-report.json', lambda x: x.get('server', {}).get('ready') is False and str(x.get('server', {}).get('phase', '')).upper() not in ('READY', 'STARTING', 'RUNNING'), 'missing-import admission remains closed')
        assert state.get('runtime_ready') is False
        assert str(state.get('server', {}).get('phase', '')).upper() not in ('READY', 'STARTING', 'RUNNING')
        self.record('missing imports refuse setup and server start', runtime_ready=False, server_ready=False)
        if self.args.donor_apk:
            self.import_donor()
        self.tap('Launch native client')
        current = self.wait_report('native-client-report.json', lambda x: x.get('assets_verified') is True and x.get('native', {}).get('frames', 0) >= 30, 'actual native scene preview frames')
        native = current['native']
        assert current.get('failure') is None and current.get('report_write_failed') is False
        assert native.get('gl_errors') == 0 and native.get('static_renderer', {}).get('tf_mismatches') == 0
        assert current.get('preview_is_server_world') is False
        self.tap('Connect local server')
        self.wait_report('native-client-report.json', lambda x: x.get('server_protocol', {}).get('phase') == 'POLICY_UNAVAILABLE', 'native connect refuses missing owned server lease')
        self.record('native connection refuses absent server lease', actual_server_interoperability_verified=False)
        self.record('native preview actual GLES frames', frames=native['frames'], gl_errors=native['gl_errors'])
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
        if self.args.protocol_binary:
            data = self.args.protocol_binary.read_bytes()
            if self.args.protocol_receipt:
                receipt = json.loads(self.args.protocol_receipt.read_text())
                candidates = [v for v in receipt.get('artifacts', []) if v.get('abi') == 'x86_64']
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
        crashes = self.text('logcat', '-d', '-b', 'crash')
        assert PACKAGE not in crashes, 'App crash recorded'
        self.record('no app crash recorded')
        value = {'format': 1, 'status': 'passed', 'checks': self.proofs, 'device': {'api': self.text('shell', 'getprop', 'ro.build.version.sdk').strip(), 'abi': 'x86_64', 'emulator': True}, 'physical_thor_accepted': False, 'actual_server_interoperability_verified': False, 'real_authenticated_session': False, 'scope': 'Consolidated app Android framework import cancellation/admission, native preview GLES and lifecycle; optional source-layout scripted native UDP controller. ARM64 guest server startup and real local account handoff require device qualification.'}
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
    args = p.parse_args()
    driver = Check(args)
    try:
        driver.run()
    except Exception as failure:
        (args.output / 'failure.json').write_text(json.dumps({'type':type(failure).__name__,'message':str(failure),'actual_server_interoperability_verified':False},indent=2)+'\n')
        for name, command in (
            ('failure-lastanr.txt', ('shell','dumpsys','activity','lastanr')),
            ('failure-events.txt', ('logcat','-d','-b','events','-s','am_anr','am_crash')),
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
