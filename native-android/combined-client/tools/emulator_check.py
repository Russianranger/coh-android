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

    def dump(self):
        for unused in range(4):
            self.adb('shell', 'uiautomator', 'dump', '/sdcard/combined-ui.xml')
            raw = self.adb('exec-out', 'cat', '/sdcard/combined-ui.xml').stdout
            (self.args.output / 'last-ui.xml').write_bytes(raw)
            root = ET.fromstring(raw)
            alerts = [n for n in root.iter('node') if n.attrib.get('resource-id') == 'android:id/alertTitle']
            launcher = next((n for n in alerts if n.attrib.get('text') == "Pixel Launcher isn't responding"), None)
            if launcher is None:
                if any("isn't responding" in n.attrib.get('text', '') for n in alerts):
                    raise RuntimeError('App or nonallowlisted component ANR; qualification failed without dismissal')
                return root
            # This is an observed headless-emulator launcher failure, before any
            # native preview starts. Recover only that exact external component;
            # an app ANR remains a qualification failure and is never dismissed.
            self.launcher_anrs += 1
            (self.args.output / ('external-launcher-anr-' + str(self.launcher_anrs) + '.xml')).write_bytes(raw)
            if self.launcher_anrs > 3:
                raise RuntimeError('External Pixel Launcher repeatedly failed to respond')
            wait = next((n for n in root.iter('node') if n.attrib.get('resource-id') == 'android:id/aerr_wait' and n.attrib.get('text') == 'Wait'), None)
            if wait is None:
                raise RuntimeError('Observed external launcher ANR has no framework Wait action')
            xy = [int(v) for v in re.findall(r'\d+', wait.attrib['bounds'])]
            self.adb('shell', 'input', 'tap', (xy[0]+xy[2])//2, (xy[1]+xy[3])//2)
            self.record('external Pixel Launcher ANR observed and framework Wait selected', external_component='com.google.android.apps.nexuslauncher', occurrence=self.launcher_anrs, native_app_anr_dismissed=False)
            time.sleep(.5)
        raise RuntimeError('External launcher dialog did not clear')

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
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            focus = self.text('shell', 'dumpsys', 'window', 'windows')
            if 'com.google.android.documentsui' in focus or 'com.android.documentsui' in focus:
                break
            time.sleep(.15)
        else:
            raise RuntimeError('SAF picker did not open: ' + label)
        self.adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
        time.sleep(.3)
        self.record('framework SAF cancellation', control=label)

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

    def run(self):
        assert self.text('shell', 'getprop', 'ro.boot.qemu').strip() == '1', 'Qualification is limited to its disposable CI emulator'
        assert self.text('shell', 'getprop', 'ro.product.cpu.abi').strip() == 'x86_64'
        assert not self.text('shell', 'pm', 'list', 'packages', '--user', '0', PACKAGE).strip(), 'Require fresh disposable emulator; never clear user data'
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
        self.export_native()
        (self.args.output / 'native-preview.png').write_bytes(self.adb('exec-out', 'screencap', '-p').stdout)
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
    Check(p.parse_args()).run()


if __name__ == '__main__':
    main()
