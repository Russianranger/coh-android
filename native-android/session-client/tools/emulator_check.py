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
import struct
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
    assert native['depth_sampler_controls_passed'] is True
    raw = native['raw_changed_pixels']
    ties = native['qualified_equal_depth_ties']
    non_ties = native['non_tie_mismatches']
    assert raw == ties + non_ties and non_ties == 0
    diagnostics = native['depth_tie_diagnostics']
    assert len(diagnostics) == raw <= 16
    assert len({(w['x'],w['y']) for w in diagnostics}) == len(diagnostics)
    for witness in diagnostics:
        assert 0 <= witness['x'] < 512 and 0 <= witness['y'] < 512
        assert 0 <= witness['world_depth'] < 0xffffff
        assert witness['world_depth'] == witness['actor_depth'] == witness['combined_depth']
        assert max(abs(a-b) for a,b in zip(witness['forward_rgba'][:3], witness['reverse_rgba'][:3])) > 2
    controls = native['depth_sampler_controls']
    assert set(controls) == {'clear', 'world_front', 'actor_front'}
    clear, world_front, actor_front = (controls[name] for name in ('clear', 'world_front', 'actor_front'))
    assert len({(w['x'],w['y']) for w in controls.values()}) == 3
    assert all(0 <= w['x'] < 512 and 0 <= w['y'] < 512 for w in controls.values())
    assert clear['world_depth'] == clear['actor_depth'] == clear['combined_depth'] == 0xffffff
    assert 0 <= world_front['world_depth'] < world_front['actor_depth'] < 0xffffff
    assert world_front['combined_depth'] == world_front['world_depth']
    assert 0 <= actor_front['actor_depth'] < actor_front['world_depth'] < 0xffffff
    assert actor_front['combined_depth'] == actor_front['actor_depth']
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


def button_nodes(nodes,label):
    # Android's Material button transformation exposes all-caps accessibility
    # text even when the app calls setText with sentence case.
    return [node for node in nodes if node.get('text','').casefold()==label.casefold()
            and node.get('enabled')=='true' and node.get('clickable')=='true'
            and node.get('package')==PACKAGE]


def button_listener(value,sequence,event_type):
    matched=[e for e in value['events'] if e['sequence']>sequence and e['type'] in
             {'reset_requested','recreate_requested','export_requested'}]
    if not matched:
        return None
    assert len(matched)==1 and matched[0]['type']==event_type, 'Measured tap reached wrong/multiple action listeners'
    return matched[0]


def tap_button(label, event_type):
    before = report()
    sequence = max(e['sequence'] for e in before['events'])
    measurements = []
    for _ in range(3):
        matches=button_nodes(ui_nodes(),label)
        assert len(matches) == 1, 'Actual Android button missing: ' + label
        measurements.append(bounds(matches[0]))
        time.sleep(.15)
    assert measurements.count(measurements[0]) == len(measurements), 'Button moved during coordinate measurement'
    x0, y0, x1, y1 = measurements[0]
    adb('shell', 'input', 'touchscreen', 'tap', str((x0+x1)//2), str((y0+y1)//2))
    result = wait(lambda r:button_listener(r,sequence,event_type) is not None,
                  'Actual button listener ' + label)
    matched=button_listener(result,sequence,event_type)
    BUTTON_PROOFS.append({'label': label, 'bounds': measurements, 'event': matched})
    save('emulator-button-tap-proof.json', {'schema': 1, 'passed': True, 'taps': BUTTON_PROOFS})
    return result


def scene_input_bounds():
    """Ground coordinates in the actual accessible view or fresh Android layout."""
    screen=adb('exec-out','screencap','-p').stdout
    assert screen[:8] == b'\x89PNG\r\n\x1a\n' and screen[12:16] == b'IHDR'
    screen_width,screen_height=struct.unpack_from('>II',screen,16)
    (OUTPUT/'emulator-input-area-screen.png').write_bytes(screen)
    nodes=[n for n in ui_nodes() if n.get('package')==PACKAGE]
    labelled=[n for n in nodes if n.get('content-desc','').casefold()=='native atlas scene']
    assert len(labelled)<=1, 'Duplicate accessible native scene labels'
    surface_nodes=[n for n in nodes if n.get('class')=='android.view.SurfaceView']
    if labelled:
        selected=labelled[0]; source='actual Android accessibility node, Native Atlas scene'
    elif len(surface_nodes)==1:
        selected=surface_nodes[0]; source='actual Android accessibility SurfaceView node'
    else:
        selected=None; source='actual SurfaceView getLocationOnScreen/getWidth/getHeight report'
    observed=bounds(selected) if selected is not None else None
    deadline=time.monotonic()+10; samples=[]; last_stamp=None; geometry=None
    while time.monotonic()<deadline:
        current=report()
        if current is None or not native_ready(current):
            time.sleep(.1);continue
        if current['updated_at']==last_stamp:
            time.sleep(.1);continue
        last_stamp=current['updated_at']; area=current['input_area']
        assert area['shown'] is True and area['surface_ready'] is True
        left,top,width,height=(int(area[k]) for k in ('left','top','width','height'))
        assert width>=160 and height>=160
        assert current['native']['width']==width and current['native']['height']==height
        rect=[left,top,left+width,top+height]
        assert 0<=left<rect[2]<=screen_width and 0<=top<rect[3]<=screen_height
        if observed is not None:
            assert observed==rect, 'Accessibility bounds differ from the current native SurfaceView layout'
        if rect!=geometry:
            geometry=rect;samples=[]
        samples.append({'updated_at':current['updated_at'],'native_frames':current['native']['frames'],
                        'input_area':dict(area),'bounds':rect})
        if len(samples)>=3 and samples[-1]['native_frames']>samples[0]['native_frames']:
            proof={'scope':source,'screen_width':screen_width,'screen_height':screen_height,
                   'accessibility_bounds':observed,'fresh_layout_samples':samples,'selected_bounds':rect}
            save('emulator-input-area-proof.json',proof)
            return current,rect,proof
        time.sleep(.1)
    raise AssertionError('Native SurfaceView input geometry did not settle across fresh rendering reports')


def touch_look():
    current,rect,selection=scene_input_bounds()
    x0,y0,x1,y1=rect; xc,yc=(x0+x1)//2,(y0+y1)//2
    previous=current['input_adapter']['external_android']
    before = current['native']['camera_yaw']
    adb('shell', 'input', 'touchscreen', 'swipe', str(xc-40), str(yc), str(xc+40), str(yc), '450')
    result = wait(lambda r:abs(r['native']['camera_yaw']-before) > .01
                  and r['input_adapter']['external_android']['touch_end']>previous['touch_end']
                  and r['input_adapter']['touch_active'] is False,'Real touch moves shared camera and releases')
    assert result['native']['held_dirs'] == 0
    external=result['input_adapter']['external_android']
    assert external['touch_begin']==previous['touch_begin']+1 and external['touch_move']>previous['touch_move']
    assert external['touch_end']==previous['touch_end']+1
    save('emulator-camera-proof.json', {'passed': True, 'bounds': [x0,y0,x1,y1],
                                       'selection':selection,'external_android_before':previous,'external_android_after':external,
                                       'camera_yaw_before': before, 'camera_yaw_after': result['native']['camera_yaw'],
                                       'scope': 'Actual Android touchscreen; same camera used by authored world and actor'})
    return result


def home_interrupt_witness(before,paused,source='keyboard'):
    """Require an unreleased source key at Home interruption and exact order."""
    old=before['input_adapter']['external_android']
    sequence=max(e['sequence'] for e in before['events'])
    final=paused['input_adapter']['external_android']
    if source=='keyboard':
        assert final['key_down']==old['key_down']+1
        assert final['key_up']==old['key_up'], 'Release arrived before Home focus interruption'
        down_events=[e for e in paused['events'] if e['sequence']>sequence and e['type']=='key_down'
                     and e.get('native',{}).get('held_dirs')==1]
        assert len(down_events)==1, 'Exactly one actual forwarded movement key down must be retained'
        down_sequence=down_events[0]['sequence']
    else:
        assert source=='joystick'
        assert final['key_down']==old['key_down'] and final['key_up']==old['key_up']
        assert final['motion']>old['motion'] and final['controller_events']>old['controller_events']
        down_sequence=sequence
    interruption=[e for e in paused['events'] if e['sequence']>down_sequence
                  and e['type'] in ('input_clear_requested','pause_requested')
                  and e.get('native',{}).get('held_dirs')==1
                  and e.get('native',{}).get('source_state_bits',0)&1
                  and e.get('native',{}).get('movement_ticks',0)>before['native']['movement_ticks']
                  and distance(e['native']['actor_position'],before['native']['actor_position'])>.01
                  and e.get('native',{}).get('running') is True
                  and e.get('native',{}).get('frames',0)>before['native']['frames']
                  and e.get('native',{}).get('foreground') is True]
    assert interruption, 'Home event trace lacks actual held and moving source input immediately before clear'
    clear_sequence=interruption[0]['sequence']
    assert not any(e['type']=='key_up' and down_sequence<e['sequence']<clear_sequence for e in paused['events']), 'Framework key release preceded focus interruption'
    assert any(e['type']=='pause' and e['sequence']>clear_sequence for e in paused['events'])
    assert paused['resumed'] is False and paused['native']['running'] is False and paused['native']['held_dirs']==0
    assert paused['native']['foreground'] is False and paused['native']['source_state_bits']==0
    assert paused['native']['motion_local']==paused['native']['motion_world']==[0,0,0]
    return interruption


def home_with_held_input(before):
    usage=[]
    for arg in ('--help','help'):
        output=adb('shell','input',arg,check=False)
        text=(output.stdout+output.stderr).decode(errors='replace')
        usage.append({'argv':[ADB,'shell','input',arg],'returncode':output.returncode,'output':text})
        if re.search(r'^\s+joystick\s*$',text,re.M) and 'motionevent <DOWN|UP|MOVE|CANCEL> <x> <y>' in text:
            break
    save('emulator-android-input-help.json',{'commands':usage})
    assert any(re.search(r'^\s+joystick\s*$',item['output'],re.M)
               and 'motionevent <DOWN|UP|MOVE|CANCEL> <x> <y>' in item['output'] for item in usage), 'Framework joystick MOVE capability not advertised'
    old=before['input_adapter']['external_android']
    command=[ADB,'shell','input','joystick','motionevent','MOVE','0','-1']
    adb(*command[1:])
    held=wait(lambda r:native_ready(r) and r['native']['held_dirs']==1
              and r['native']['source_state_bits']&1
              and r['native']['movement_ticks']>before['native']['movement_ticks']
              and distance(r['native']['actor_position'],before['native']['actor_position'])>.01
              and r['native']['frames']>before['native']['frames']
              and r['native']['run_samples']>before['native']['run_samples']
              and r['input_adapter']['external_android']['motion']>old['motion']
              and r['input_adapter']['external_android']['controller_events']>old['controller_events'],
              'Actual framework joystick forward axis reaches moving native source state')
    assert held['input_adapter']['external_android']['key_down']==old['key_down']
    assert held['input_adapter']['external_android']['key_up']==old['key_up']
    adb('shell','input','keyevent','KEYCODE_HOME')
    paused=wait(lambda r:r['resumed'] is False and r['native']['running'] is False
                and r['native']['held_dirs']==0,'Actual Home clears held framework joystick axis',seconds=30)
    interruption=home_interrupt_witness(before,paused,source='joystick')
    assert paused['native']['objects_released'] is True
    assert paused['native']['contexts_completed']==paused['native']['contexts_started']
    assert paused['native']['cleanup_gl_errors']==paused['native']['cleanup_egl_errors']==0
    save('emulator-home-held-input-proof.json',{'schema':1,'passed':True,
         'scope':'Actual Android framework joystick MOVE creates held source movement; actual system Home preserves a pre-clear held/moving native witness and clears input in background; no physical controller claim',
         'framework_input_argv':command,'advertised_framework_source':'joystick',
         'rendered_source_movement_observed_before_home':True,
         'held_snapshot':held,'interruption_events':interruption,
         'background_native':paused['native'],'background_input_adapter':paused['input_adapter']})
    return paused


def renewed_joystick_input(before):
    old=before['input_adapter']['external_android']
    adb('shell','input','joystick','motionevent','MOVE','0','0')
    neutral=wait(lambda r:r['native']['held_dirs']==0
                 and r['input_adapter']['external_android']['motion']>old['motion'], 'Real neutral joystick event after foreground return')
    old=neutral['input_adapter']['external_android']
    adb('shell','input','joystick','motionevent','MOVE','0','1')
    moved=wait(lambda r:r['native']['held_dirs']==2 and r['native']['source_state_bits']&2
               and r['native']['frames']>neutral['native']['frames']
               and distance(r['native']['actor_position'],neutral['native']['actor_position'])>.01
               and r['input_adapter']['external_android']['motion']>old['motion'], 'Renewed framework joystick backward input moves source actor')
    old=moved['input_adapter']['external_android']
    adb('shell','input','joystick','motionevent','MOVE','0','0')
    released=wait(lambda r:r['native']['held_dirs']==0 and r['native']['animation_state']==0
                  and r['input_adapter']['external_android']['motion']>old['motion'], 'Real neutral joystick release settles authored actor')
    position=released['native']['actor_position'][:];frames=released['native']['frames']
    settled=wait(lambda r:r['native']['frames']>=frames+30, 'Continuous rendering after fresh joystick release')
    assert distance(position,settled['native']['actor_position'])<=.001
    save('emulator-renewed-joystick-proof.json',{'passed':True,'scope':'Actual framework joystick neutral/backward/neutral after Home; no physical controller claim',
         'neutral':neutral,'moving':moved,'released':released,'settled':settled})
    return settled


def export_document():
    before = report(); session = before['session_id']
    tapped = tap_button('Export report', 'export_requested')
    deadline = time.monotonic()+25
    saved = False
    while time.monotonic() < deadline and not saved:
        nodes = ui_nodes()
        save_nodes = [n for n in nodes if n.get('text', '').casefold() == 'save' and n.get('enabled') == 'true']
        candidates = save_nodes or [n for n in nodes if n.get('text','').casefold() == 'downloads' and n.get('enabled') == 'true']
        if not candidates:
            candidates = [n for n in nodes if n.get('content-desc','').casefold() in ('show roots', 'open navigation drawer')]
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
        contexts=recreated['native']['contexts_started']; frames=recreated['native']['frames']
        paused = home_with_held_input(recreated)
        position=paused['native']['actor_position'][:]
        save('emulator-background-report.json', paused)
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY)
        returned = wait(lambda r:native_ready(r) and r['native']['contexts_started'] > contexts
                        and r['native']['frames'] > frames+30 and r['native']['animation_state']==0,
                        'Actual Home return starts fresh context and authored post-run settles without resetting actor')
        assert returned['session_id'] == first['session_id']
        assert distance(position, returned['native']['actor_position']) <= .001
        assert abs(camera[0]-returned['native']['camera_yaw']) <= .0001 and abs(camera[1]-returned['native']['camera_pitch']) <= .0001
        validate(returned, moved=True); save('emulator-foreground-report.json', returned)
        renewed=renewed_joystick_input(returned);validate(renewed,moved=True)
        screenshot('emulator-foreground-scene.png')
        exported = export_document()
        wait(native_ready, 'Scene returns after document picker')
        tap_button('Reset actor', 'reset_requested')
        reset = wait(lambda r:native_ready(r) and distance(initial_position,r['native']['actor_position'])<=.001,
                     'Actual Reset button returns authored actor placement')
        validate(reset); save('emulator-final-report.json', reset)
        summary={'schema':1,'gates':[16,17,18],'passed':True,'installed_apk':apk_identity,
                 'native_session_execution_verified':True,
                 'scope':'Installed Android 13 x86_64; persistent authored Atlas benchmark and Wretch, source no-collision actor movement, authored idle/run/post tracks under actual Android keyboard/touch input',
                 'frames':reset['native']['frames'],'contexts_started':reset['native']['contexts_started'],
                 'actual_keyboard_motion':True,'actual_touch_camera':True,'actual_surface_recreation':True,
                 'actual_home_preserves_actor_and_camera':True,'actual_document_export':True,'actual_reset_button':True,
                 'actual_home_clears_held_framework_input':True,
                 'actual_home_input_source':'Android framework joystick; not a physical controller',
                 'renewed_framework_joystick_input_after_home':True,
                 'source_tf_components':reset['native']['tf_components'],'source_tf_mismatches':reset['native']['tf_mismatches'],
                 'raw_depth_order_color_differences':reset['native']['raw_changed_pixels'],
                 'exact_equal_depth_ties':reset['native']['qualified_equal_depth_ties'],
                 'non_tie_depth_order_mismatches':reset['native']['non_tie_mismatches'],
                 'actual_depth_sampler_controls_verified':True,
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
