#!/usr/bin/env python3
"""Exercise one installed session through genuine Android framework input.

The host driver never calls JNI input or supplies an automatic motion script.
This qualifies an offline source-derived scene session, not a full game client,
physical controller, AYN Thor GPU, server protocol, walking collision or login.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile

PACKAGE = 'org.coh.sessionclient'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = None
ADB = 'adb'
INPUT_PROOFS = []
BUTTON_PROOFS = []


def adb(*arguments, check=True):
    return subprocess.run([ADB, *arguments], check=check, capture_output=True, timeout=30)


def save(name, value):
    (OUTPUT / name).write_text(json.dumps(value, indent=2) + '\n')


def report():
    result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/session-report.json', check=False)
    if result.returncode:
        return None
    assert len(result.stdout) <= 4 << 20, 'Session evidence exceeds bound'
    try:
        value = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    (OUTPUT / 'emulator-session-report.json').write_bytes(result.stdout)
    if value.get('failure') or value.get('report_write_failed') or value.get('native', {}).get('failed'):
        raise RuntimeError('Sticky app/native failure: ' + json.dumps(value.get('native', {}))[:8192])
    return value


def wait(predicate, label, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        current = report()
        if current is not None and predicate(current):
            return current
        time.sleep(.15)
    raise RuntimeError(label + ' failed; latest installed session report retained')


def native_ready(value):
    native = value.get('native', {})
    return (value.get('assets_verified') is True and value.get('resumed') is True
            and native.get('valid') is True and native.get('running') is True
            and native.get('frames', 0) >= 30)


def validate(value, moved=False):
    assert value['schema'] == 'coh-native-session-v1' and value['phases'] == [16, 17, 18]
    assert value['app']['package'] == PACKAGE and value['app']['version_name'] == '0.1.0-gates16-18'
    assert value['app']['version_code'] == 1
    assert value['device']['sdk'] == 33 and value['device']['emulator_detected'] is True
    assert value['assets_verified'] is True and value['failure'] is None and value['report_write_failed'] is False
    native = value['native']
    assert native['valid'] is True and native['failed'] is False
    assert native['source_controlled'] is True and native['pointer_bytes'] == 8
    assert native['collision'] is native['live_server'] is native['full_atlas'] is False
    assert native['frames'] >= 30 and native['contexts_started'] > 0
    assert native['world_draws'] >= 2 and native['actor_draws'] >= 11
    assert native['tf_components'] > 0 and native['tf_mismatches'] == 0
    assert math.isfinite(native['tf_max_error']) and 0 <= native['tf_max_error'] <= .0001
    assert native['depth_order_mismatches'] == native['gl_errors'] == native['egl_error'] == 0
    assert native['world_visible_pixels'] > 0 and native['actor_visible_pixels'] > 0
    assert native['world_occludes_actor_pixels'] > 0 and native['actor_occludes_world_pixels'] > 0
    assert native['actor_changed_pixels'] > 0 and native['skin_samples'] > 0
    assert all(math.isfinite(v) for v in native['actor_position'] + native['camera_position'])
    assert native['held_dirs'] == 0
    synthetic = value['input_adapter']['in_app_synthetic']
    assert all(synthetic[key] == 0 for key in ('key_down', 'key_up', 'key_repeat', 'motion',
                                               'touch_begin', 'touch_move', 'touch_end'))
    if moved:
        assert native['direction_mask'] == 15 and native['movement_ticks'] > 0
        assert native['animation_transitions'] >= 2
        assert native['run_samples'] > 0 and native['idle_samples'] > 0
        assert native['animation_state'] == 0  # Authored Ready move.


def screenshot(name):
    result = adb('exec-out', 'screencap', '-p')
    assert result.stdout.startswith(b'\x89PNG\r\n\x1a\n')
    (OUTPUT / name).write_bytes(result.stdout)


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def input_key(key, rounds=1):
    before = report()
    old = before['input_adapter']['external_android']
    for _ in range(rounds):
        adb('shell', 'input', 'keyboard', 'keyevent', '--longpress', key)
    after = wait(lambda r:r['native']['movement_ticks'] > before['native']['movement_ticks']
                 and r['native']['held_dirs'] == 0
                 and r['input_adapter']['external_android']['key_up'] >= old['key_up'] + rounds,
                 'Real Android keyboard movement and release ' + key)
    newer = after['input_adapter']['external_android']
    assert newer['key_down'] >= old['key_down'] + rounds
    assert newer['key_down'] == newer['key_up'], 'Keyboard release must reach native input'
    assert distance(before['native']['actor_position'], after['native']['actor_position']) > .01
    INPUT_PROOFS.append({'source': 'Android input keyboard keyevent --longpress', 'key': key, 'rounds': rounds,
                         'position_before': before['native']['actor_position'],
                         'position_after': after['native']['actor_position'],
                         'movement_ticks_before': before['native']['movement_ticks'],
                         'movement_ticks_after': after['native']['movement_ticks'],
                         'adapter_before': old, 'adapter_after': newer,
                         'animation_transitions': after['native']['animation_transitions'],
                         'run_samples': after['native']['run_samples']})
    save('emulator-input-motion-proof.json', {'schema': 1, 'passed': True, 'inputs': INPUT_PROOFS,
                                            'physical_controller_verified': False})
    return after


def ui_nodes():
    adb('shell', 'uiautomator', 'dump', '/sdcard/session-ui.xml', check=False)
    raw = adb('exec-out', 'cat', '/sdcard/session-ui.xml', check=False).stdout
    (OUTPUT / 'emulator-ui.xml').write_bytes(raw)
    try:
        return list(ET.fromstring(raw).iter('node'))
    except ET.ParseError:
        return []


def bounds(node):
    values = [int(n) for n in re.findall(r'\d+', node.get('bounds', ''))]
    assert len(values) == 4 and values[2] > values[0] and values[3] > values[1]
    return values


def tap_button(label, event_type):
    before = report()
    sequence = max(e['sequence'] for e in before['events'])
    measurements = []
    for _ in range(3):
        matches = [node for node in ui_nodes() if node.get('text') == label and node.get('enabled') == 'true'
                   and node.get('clickable') == 'true' and node.get('package') == PACKAGE]
        assert len(matches) == 1, 'Actual Android button missing: ' + label
        measurements.append(bounds(matches[0]))
        time.sleep(.15)
    assert measurements.count(measurements[0]) == len(measurements), 'Button moved during coordinate measurement'
    x0, y0, x1, y1 = measurements[0]
    adb('shell', 'input', 'touchscreen', 'tap', str((x0+x1)//2), str((y0+y1)//2))
    result = wait(lambda r:any(e['type'] == event_type and e['sequence'] > sequence for e in r['events']),
                  'Actual button listener ' + label)
    matched = [e for e in result['events'] if e['sequence'] > sequence and e['type'] in
               {'reset_requested', 'recreate_requested', 'export_requested'}]
    assert len(matched) == 1 and matched[0]['type'] == event_type, 'Measured tap reached wrong/multiple action listeners'
    BUTTON_PROOFS.append({'label': label, 'bounds': measurements, 'event': matched[0]})
    save('emulator-button-tap-proof.json', {'schema': 1, 'passed': True, 'taps': BUTTON_PROOFS})
    return result


def touch_look():
    current = report()
    nodes = [n for n in ui_nodes() if n.get('class') == 'android.view.SurfaceView' and n.get('package') == PACKAGE]
    assert len(nodes) == 1
    x0, y0, x1, y1 = bounds(nodes[0]); xc, yc = (x0+x1)//2, (y0+y1)//2
    before = current['native']['camera_yaw']
    adb('shell', 'input', 'touchscreen', 'swipe', str(xc-40), str(yc), str(xc+40), str(yc), '450')
    result = wait(lambda r:abs(r['native']['camera_yaw']-before) > .01, 'Real touch moves shared camera')
    assert result['native']['held_dirs'] == 0
    save('emulator-camera-proof.json', {'passed': True, 'bounds': [x0,y0,x1,y1],
                                       'camera_yaw_before': before, 'camera_yaw_after': result['native']['camera_yaw'],
                                       'scope': 'Actual Android touchscreen; same camera used by authored world and actor'})
    return result


def export_document():
    before = report(); session = before['session_id']
    tapped = tap_button('Export report', 'export_requested')
    deadline = time.monotonic()+25
    saved = False
    while time.monotonic() < deadline and not saved:
        nodes = ui_nodes()
        save_nodes = [n for n in nodes if n.get('text', '').upper() == 'SAVE' and n.get('enabled') == 'true']
        candidates = save_nodes or [n for n in nodes if n.get('text') == 'Downloads' and n.get('enabled') == 'true']
        if not candidates:
            candidates = [n for n in nodes if n.get('content-desc') in ('Show roots', 'Open navigation drawer')]
        if candidates:
            x0,y0,x1,y1 = bounds(candidates[0])
            adb('shell', 'input', 'touchscreen', 'tap', str((x0+x1)//2), str((y0+y1)//2))
            saved = bool(save_nodes)
        time.sleep(.3)
    assert saved, 'Document picker Save never became available'
    result = wait(lambda r:r['session_id'] == session and r.get('resumed') is True
                  and any(e['type'] == 'export_complete' for e in r['events']), 'Actual document export callback')
    paths = adb('shell', 'find', '/sdcard/Download', '-maxdepth', '1', '-name', 'COH-NativeSession-*.json', check=False).stdout.decode().splitlines()
    assert paths, 'Exported session JSON missing from Downloads'
    raw = adb('exec-out', 'cat', paths[-1]).stdout
    assert 0 < len(raw) <= 4 << 20
    frozen = json.loads(raw)
    assert frozen['session_id'] == session
    validate(frozen, moved=True)
    assert frozen['native']['movement_ticks'] >= before['native']['movement_ticks']
    assert any(e['type'] == 'export_requested' for e in frozen['events'])
    assert not any(e['type'] == 'export_complete' and e['sequence'] > tapped['events'][-1]['sequence'] for e in frozen['events'])
    (OUTPUT / 'emulator-exported-report.json').write_bytes(raw)
    save('emulator-export-proof.json', {'passed': True, 'path': paths[-1], 'bytes': len(raw),
                                      'sha256': hashlib.sha256(raw).hexdigest(),
                                      'scope': 'Actual CREATE_DOCUMENT Save; frozen native session evidence before picker pause'})
    return result


def main():
    global OUTPUT, ADB
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--adb', default='adb')
    args = parser.parse_args(); OUTPUT=args.output; ADB=args.adb; OUTPUT.mkdir(parents=True, exist_ok=True)
    apk_identity = {'bytes': args.apk.stat().st_size, 'sha256': hashlib.sha256(args.apk.read_bytes()).hexdigest()}
    with zipfile.ZipFile(args.apk) as apk:
        assert apk.testzip() is None
        pins = json.loads(apk.read('assets/asset-manifest.json'))
        for name, pin in pins['assets'].items():
            raw = apk.read('assets/'+name)
            assert {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == pin
    adb('install', '-r', str(args.apk)); adb('shell', 'am', 'force-stop', PACKAGE)
    adb('shell', 'pm', 'clear', PACKAGE); adb('logcat', '-c')
    try:
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY)
        first = wait(native_ready, 'Continuous authored shared scene startup', seconds=90)
        validate(first)
        assert first['app']['installed_apk'] == apk_identity
        assert first['asset_manifest'] == pins
        save('emulator-initial-report.json', first); screenshot('emulator-initial-scene.png')
        initial_position = first['native']['actor_position'][:]
        input_key('KEYCODE_W', rounds=3)
        screenshot('emulator-moved-scene.png')
        for key in ('KEYCODE_A', 'KEYCODE_S', 'KEYCODE_D'):
            input_key(key)
        # Leave the actor away from reset to make preservation meaningful.
        input_key('KEYCODE_W', rounds=2)
        moved = wait(lambda r:native_ready(r) and r['native']['held_dirs'] == 0
                     and r['native']['animation_state'] == 0, 'Idle after released authored run', seconds=30)
        validate(moved, moved=True)
        assert distance(initial_position, moved['native']['actor_position']) > .1
        settled_position = moved['native']['actor_position'][:]
        settled_frames = moved['native']['frames']
        moved = wait(lambda r:r['native']['frames'] >= settled_frames+30, 'Continued idle rendering after release')
        assert distance(settled_position,moved['native']['actor_position']) <= .001, 'Released actor continues drifting'
        moved = touch_look(); save('emulator-moved-report.json', moved)
        state = moved['native']; contexts=state['contexts_started']; position=state['actor_position'][:]
        camera=(state['camera_yaw'],state['camera_pitch']); frames=state['frames']
        tap_button('Recreate', 'recreate_requested')
        recreated = wait(lambda r:native_ready(r) and r['native']['contexts_started'] > contexts
                         and r['native']['frames'] > frames + 30, 'Actual recreated Surface resumes persistent scene')
        assert recreated['session_id'] == first['session_id']
        assert distance(position, recreated['native']['actor_position']) <= .001, 'Surface recreation reset actor'
        assert abs(camera[0]-recreated['native']['camera_yaw']) <= .0001 and abs(camera[1]-recreated['native']['camera_pitch']) <= .0001
        validate(recreated, moved=True); save('emulator-recreated-report.json', recreated)
        prior_sequence=max(e['sequence'] for e in recreated['events'])
        contexts=recreated['native']['contexts_started']; frames=recreated['native']['frames']
        adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        paused = wait(lambda r:r['resumed'] is False and r['native']['running'] is False
                      and r['native']['held_dirs'] == 0 and any(e['type']=='pause' and e['sequence']>prior_sequence for e in r['events']),
                      'Actual Android Home stops worker and clears native input', seconds=30)
        assert paused['native']['objects_released'] is True
        assert paused['native']['contexts_completed'] == paused['native']['contexts_started']
        save('emulator-background-report.json', paused)
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY)
        returned = wait(lambda r:native_ready(r) and r['native']['contexts_started'] > contexts
                        and r['native']['frames'] > frames+30, 'Actual Home return starts fresh context without resetting actor')
        assert returned['session_id'] == first['session_id']
        assert distance(position, returned['native']['actor_position']) <= .001
        assert abs(camera[0]-returned['native']['camera_yaw']) <= .0001 and abs(camera[1]-returned['native']['camera_pitch']) <= .0001
        validate(returned, moved=True); save('emulator-foreground-report.json', returned)
        screenshot('emulator-foreground-scene.png')
        exported = export_document()
        wait(native_ready, 'Scene returns after document picker')
        tap_button('Reset actor', 'reset_requested')
        reset = wait(lambda r:native_ready(r) and distance(initial_position,r['native']['actor_position'])<=.001,
                     'Actual Reset button returns authored actor placement')
        validate(reset); save('emulator-final-report.json', reset)
        summary={'schema':1,'gates':[16,17,18],'passed':True,'installed_apk':apk_identity,
                 'scope':'Installed Android 13 x86_64; persistent authored Atlas benchmark and Wretch, source no-collision actor movement, authored idle/run/post tracks under actual Android keyboard/touch input',
                 'frames':reset['native']['frames'],'contexts_started':reset['native']['contexts_started'],
                 'actual_keyboard_motion':True,'actual_touch_camera':True,'actual_surface_recreation':True,
                 'actual_home_preserves_actor_and_camera':True,'actual_document_export':True,'actual_reset_button':True,
                 'source_tf_components':reset['native']['tf_components'],'source_tf_mismatches':reset['native']['tf_mismatches'],
                 'physical_controller_verified':False,'thor_device_execution_verified':False,
                 'original_game_execution':False,'full_atlas_loaded':False,'server_interoperability_verified':False,
                 'walking_collision_qualified':False,'full_sequencer_execution':False}
        save('emulator-smoke-summary.json',summary); print(json.dumps(summary))
    finally:
        (OUTPUT/'emulator-logcat.txt').write_bytes(adb('logcat','-d',check=False).stdout)
        result=adb('exec-out','screencap','-p',check=False)
        if result.returncode==0 and result.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            (OUTPUT/'emulator-screenshot.png').write_bytes(result.stdout)


if __name__ == '__main__':
    main()
