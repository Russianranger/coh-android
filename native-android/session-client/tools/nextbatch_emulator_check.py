#!/usr/bin/env python3
"""Qualify integrated source loading, bounded Atlas residency and static drawing.

Only genuine Android framework input is sent. Every movement command supplies
its own release before host report polling begins. The accepted gates 19--21
qualification driver and all of its original receipts remain unchanged.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shlex
import subprocess
import time
import zipfile

_BASE_PATH = Path(__file__).with_name('emulator_check.py')
_SPEC = importlib.util.spec_from_file_location('accepted_session_helpers', _BASE_PATH)
session = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(session)

PACKAGE = 'org.coh.sessionclient.walk'
VERSION_NAME = '0.3.0-gates22-24'
VERSION_CODE = 3
GATES = [22, 23, 24]
INPUT_PROOFS = []


def configure(package=PACKAGE):
    session.PACKAGE = package
    session.ACTIVITY = package + '/org.coh.sessionclient.MainActivity'
    session.GATES = GATES
    # The shared CREATE_DOCUMENT helper validates its frozen exported receipt
    # against this batch's strict identity and new integration predicates.
    session.validate = validate


def positive_integer(value):
    return type(value) is int and value > 0


def finite_position(position):
    return (isinstance(position, list) and len(position) == 3
            and all(type(v) in (int, float) and math.isfinite(v) for v in position))


def event_sequence(value):
    assert value['events'], 'A genuine callback trace is required'
    sequences = [e['sequence'] for e in value['events']]
    assert all(type(n) is int for n in sequences)
    assert sequences == sorted(set(sequences)), 'Callback sequences must be unique and ordered'
    return sequences[-1]


def no_synthetic_input(value):
    synthetic = value['input_adapter']['in_app_synthetic']
    assert all(synthetic[key] == 0 for key in ('key_down', 'key_up', 'key_repeat', 'motion',
                                               'touch_begin', 'touch_move', 'touch_end'))


def bounded_key_witness(before, after, directions):
    """A fresh actual key-up retains the source state achieved before release.

    Counters and the final idle snapshot cannot stand in for current source
    physics. Key-up clears requested controls before the next physics step;
    its retained native snapshot still carries the achieved source direction.
    """
    assert directions in (1, 2, 4, 8)
    assert before['session_id'] == after['session_id']
    assert session.released_walk_controls(before)
    old = before['input_adapter']['external_android']
    current = after['input_adapter']['external_android']
    assert old['key_down'] == old['key_up']
    assert current['key_down'] == old['key_down'] + 1
    assert current['key_up'] == old['key_up'] + 1
    assert current['key_down'] == current['key_up']
    no_synthetic_input(before)
    no_synthetic_input(after)
    sequence = event_sequence(before)
    event_sequence(after)
    events = [e for e in after['events'] if e['sequence'] > sequence
              and e['type'] in ('key_down', 'key_up')]
    assert [e['type'] for e in events] == ['key_down', 'key_up']
    assert events[0]['native']['held_dirs'] == directions
    assert events[1]['native']['held_dirs'] == 0
    observed = events[1]['native']
    assert observed['foreground'] is True and observed['running'] is True
    assert observed['source_state_bits'] == directions
    assert type(events[0]['time_ms']) is int and type(events[1]['time_ms']) is int
    assert 0 < events[1]['time_ms'] - events[0]['time_ms'] <= 1000, 'Actual Android callbacks exceeded the bounded physical hold'
    pressed = events[0]['native']
    assert pressed['movement_ticks'] + 3 <= observed['movement_ticks'] <= pressed['movement_ticks'] + 30
    assert observed['frames'] > pressed['frames'] >= before['native']['frames']
    assert finite_position(observed['actor_position'])
    assert session.distance(observed['actor_position'], before['native']['actor_position']) > .01
    walk = session.grounded_walk(observed)
    assert walk['bounded_ticks'] == before['native']['walk']['bounded_ticks'], 'A safety clamp cannot qualify bounded source movement'
    assert walk['collision_queries'] > before['native']['walk']['collision_queries']
    return events[1]


def framework_timeout_receipt(original, observed):
    assert original == 'null' or original.isdecimal()
    assert observed == original, 'The disposable emulator framework setting was not restored'
    return {'original_long_press_timeout': original,
            'restored_long_press_timeout': observed, 'restored': True,
            'scope': 'Disposable CI emulator secure setting only; no user device configuration'}


@contextmanager
def framework_timeout(duration_ms):
    """Bound a single Android input process and restore its verified setting."""
    assert type(duration_ms) is int and 100 <= duration_ms <= 750
    qemu = session.adb('shell', 'getprop', 'ro.boot.qemu').stdout.decode().strip()
    assert qemu == '1', 'Framework timing controls are restricted to the disposable CI emulator'
    original = session.adb('shell', 'settings', 'get', 'secure', 'long_press_timeout').stdout.decode().strip()
    assert original == 'null' or original.isdecimal()
    receipt = {'duration_ms': duration_ms, 'passed': False,
               'scope': 'Android input keyboard --longpress supplies DOWN/repeat/UP inside one process, independently of host polling'}
    try:
        session.adb('shell', 'settings', 'put', 'secure', 'long_press_timeout', str(duration_ms))
        observed = session.adb('shell', 'settings', 'get', 'secure', 'long_press_timeout').stdout.decode().strip()
        assert observed == str(duration_ms)
        yield receipt
    finally:
        if original == 'null':
            session.adb('shell', 'settings', 'delete', 'secure', 'long_press_timeout')
        else:
            session.adb('shell', 'settings', 'put', 'secure', 'long_press_timeout', original)
        observed = session.adb('shell', 'settings', 'get', 'secure', 'long_press_timeout').stdout.decode().strip()
        receipt.update(framework_timeout_receipt(original, observed))
        session.save('emulator-bounded-framework-setting.json', receipt)


def bounded_key(key, directions, duration_ms=250):
    before = session.wait(session.released_walk_controls, 'Source input is fully released before bounded framework key')
    sequence = event_sequence(before)
    progress = {'key': key, 'directions': directions, 'duration_ms': duration_ms,
                'before': before, 'passed': False}
    INPUT_PROOFS.append(progress)
    session.save('emulator-bounded-input-proof.json', {'passed': False, 'commands': INPUT_PROOFS})
    with framework_timeout(duration_ms) as setting:
        command = [session.ADB, 'shell', 'input', 'keyboard', 'keyevent', '--longpress', key]
        started = time.monotonic()
        command_result = session.adb(*command[1:], check=False)
        elapsed = time.monotonic() - started
        progress.update(framework_input_argv=command, command_elapsed_seconds=elapsed,
                        command_returncode=command_result.returncode,
                        command_stdout=command_result.stdout.decode(errors='replace'),
                        command_stderr=command_result.stderr.decode(errors='replace'))
        assert command_result.returncode == 0, 'The bounded framework command did not complete'
        # Framework KEY_UP is emitted inside the command, before any host poll.
        # A command overrun fails rather than converting a long walk into proof.
        assert elapsed <= 8, 'Bounded framework input process overran its qualification deadline'
        after = session.wait(lambda r:any(e['sequence'] > sequence and e['type'] == 'key_up'
                                         for e in r['events']),
                             'Fresh actual bounded Android key-up callback is retained', seconds=20)
        witness = bounded_key_witness(before, after, directions)
        setting['passed'] = True
    settled = session.settle_released_walk(after, 'One bounded actual Android framework key', command)
    session.grounded_walk(settled['native'])
    assert settled['native']['walk']['bounded_ticks'] == before['native']['walk']['bounded_ticks']
    progress.update(after=after, key_up_native_witness=witness, settled=settled,
                    framework_setting=setting, passed=True)
    session.save('emulator-bounded-input-proof.json', {'passed': True, 'commands': INPUT_PROOFS,
                 'scope': 'Every genuine framework movement command completes its release before host polling; exact fresh key-up callback carries achieved source physics',
                 'physical_controller_verified': False})
    session.progress('bounded framework movement and authentic source release pass', settled,
                     key=key, framework_duration_ms=duration_ms,
                     callback_sequence=witness['sequence'])
    return settled


def bounded_home_script(duration_ms):
    """Finite device-side framework input and actual HOME-resumed barrier."""
    assert type(duration_ms) is int and 100 <= duration_ms <= 500
    return '\n'.join([
        'set -e',
        "trap 'input joystick motionevent MOVE 0 0' EXIT HUP INT TERM",
        'coh_home_component="$(cmd package resolve-activity --brief --user 0 -a android.intent.action.MAIN -c android.intent.category.HOME | tail -n 1)"',
        'case "$coh_home_component" in */*) ;; *) exit 71 ;; esac',
        'printf \'COH_HOME_COMPONENT=%s\\n\' "$coh_home_component"',
        'input joystick motionevent MOVE 0 -1',
        'sleep %.3f' % (duration_ms / 1000),
        'input keyevent KEYCODE_HOME',
        # Android 13 may return START_DELIVERED_TO_TOP from am -W before a
        # previously queued lifecycle transaction completes. Require the real
        # ActivityManager resumed-HOME state as well, within six device probes.
        # This finite device-side barrier never reads or drives the app report.
        'am start -W -a android.intent.action.MAIN -c android.intent.category.HOME -n "$coh_home_component"',
        'coh_home_ready=0',
        'for coh_home_probe in 1 2 3 4 5 6; do',
        '  if dumpsys activity activities | grep -E "mResumedActivity:|topResumedActivity=" | grep -F "$coh_home_component" >/dev/null; then',
        '    coh_home_ready=1; break',
        '  fi',
        '  sleep 0.100',
        'done',
        'test "$coh_home_ready" = 1',
        'printf \'COH_HOME_RESUMED=%s\\n\' "$coh_home_component"',
        'input joystick motionevent MOVE 0 0',
        'trap - EXIT HUP INT TERM',
    ])


def framework_home_completion(stdout):
    """An actual Android HOME launch must complete before neutral is sent."""
    assert 'android.intent.action.MAIN' in stdout and 'android.intent.category.HOME' in stdout
    statuses = session.re.findall(r'^Status:\s*(\S+)\s*$', stdout, session.re.M)
    assert statuses == ['ok'], 'The real HOME Activity launch was not completed successfully'
    activities = session.re.findall(r'^Activity:\s*(\S+)\s*$', stdout, session.re.M)
    assert len(activities) == 1 and '/' in activities[0]
    resolved = session.re.findall(r'^COH_HOME_COMPONENT=(\S+)\s*$', stdout, session.re.M)
    resumed = session.re.findall(r'^COH_HOME_RESUMED=(\S+)\s*$', stdout, session.re.M)
    assert resolved == resumed == activities, 'Actual ActivityManager resumed HOME state was not observed before neutral'
    assert session.re.search(r'^Complete\s*$', stdout, session.re.M), 'Android HOME wait did not complete'
    assert not session.re.search(r'^(?:Error|Exception|Failure)\b', stdout, session.re.M | session.re.I)
    return {'status': statuses[0], 'activity': activities[0], 'completed': True,
            'scope': 'Genuine HOME key plus Android MAIN/HOME request and finite ActivityManager resumed-HOME observation; neutral follows the actual system lifecycle barrier'}


def bounded_home(before, duration_ms=250):
    assert session.released_walk_controls(before)
    command = [session.ADB, 'shell', 'sh', '-c', shlex.quote(bounded_home_script(duration_ms))]
    started = time.monotonic()
    result = session.adb(*command[1:], check=False)
    elapsed = time.monotonic() - started
    proof = {'passed': False, 'framework_input_argv': command, 'before': before,
             'command_returncode': result.returncode, 'command_elapsed_seconds': elapsed,
             'command_stdout': result.stdout.decode(errors='replace'),
             'command_stderr': result.stderr.decode(errors='replace'),
             'scope': 'One device-side timed framework joystick/Home sequence requires actual ActivityManager resumed-HOME state before neutral; six finite system probes, release before host polling, and a shell trap neutralizes on ordinary command failure'}
    session.save('emulator-bounded-home-proof.json', proof)
    assert result.returncode == 0 and elapsed <= 10
    proof['android_home_completion'] = framework_home_completion(proof['command_stdout'])
    session.save('emulator-bounded-home-proof.json', proof)
    paused = session.wait(lambda r:r['resumed'] is False and r['native']['running'] is False
                          and r['native']['held_dirs'] == 0,
                          'Actual bounded Home clears source input and stops renderer', seconds=30)
    witnesses = session.home_interrupt_witness(before, paused, source='joystick')
    for event in witnesses:
        session.grounded_walk(event['native'])
        assert event['native']['walk']['bounded_ticks'] == before['native']['walk']['bounded_ticks']
    assert paused['native']['objects_released'] is True
    assert paused['native']['contexts_completed'] == paused['native']['contexts_started']
    assert paused['native']['cleanup_gl_errors'] == paused['native']['cleanup_egl_errors'] == 0
    proof.update(passed=True, background=paused, pre_clear_native_witnesses=witnesses)
    session.save('emulator-bounded-home-proof.json', proof)
    return paused


def rendering_witness(native):
    """Retain the existing independent real-GPU transform/depth predicates."""
    assert native['tf_components'] > 0 and native['tf_mismatches'] == 0
    assert math.isfinite(native['tf_max_error']) and 0 <= native['tf_max_error'] <= .0001
    assert native['walkable_tf_components'] > 0 and native['walkable_tf_mismatches'] == 0
    assert native['walkable_visible_pixels'] > 0
    assert native['depth_order_mismatches'] == native['gl_errors'] == native['egl_error'] == 0
    assert native['depth_sampler_controls_passed'] is True
    raw, ties, non_ties = (native[key] for key in ('raw_changed_pixels', 'qualified_equal_depth_ties', 'non_tie_mismatches'))
    assert raw == ties + non_ties and non_ties == 0
    diagnostics = native['depth_tie_diagnostics']
    assert len(diagnostics) == raw <= 16
    assert len({(w['x'], w['y']) for w in diagnostics}) == len(diagnostics)
    for witness in diagnostics:
        assert 0 <= witness['x'] < 512 and 0 <= witness['y'] < 512
        assert 0 <= witness['world_depth'] < 0xffffff
        assert witness['world_depth'] == witness['actor_depth'] == witness['combined_depth']
        assert max(abs(a-b) for a, b in zip(witness['forward_rgba'][:3], witness['reverse_rgba'][:3])) > 2
    controls = native['depth_sampler_controls']
    assert set(controls) == {'clear', 'world_front', 'actor_front'}
    clear, world_front, actor_front = (controls[name] for name in ('clear', 'world_front', 'actor_front'))
    assert len({(w['x'], w['y']) for w in controls.values()}) == 3
    assert all(0 <= w['x'] < 512 and 0 <= w['y'] < 512 for w in controls.values())
    assert clear['world_depth'] == clear['actor_depth'] == clear['combined_depth'] == 0xffffff
    assert 0 <= world_front['world_depth'] < world_front['actor_depth'] < 0xffffff
    assert world_front['combined_depth'] == world_front['world_depth']
    assert 0 <= actor_front['actor_depth'] < actor_front['world_depth'] < 0xffffff
    assert actor_front['combined_depth'] == actor_front['actor_depth']
    assert all(native[key] > 0 for key in ('world_visible_pixels', 'actor_visible_pixels',
                                         'world_occludes_actor_pixels', 'actor_occludes_world_pixels',
                                         'actor_changed_pixels', 'skin_samples'))
    return True


def validate(value, moved=False):
    assert value['schema'] == 'coh-native-session-v1' and value['phases'] == GATES
    assert value['app']['package'] == session.PACKAGE
    assert value['app']['version_name'] == VERSION_NAME and value['app']['version_code'] == VERSION_CODE
    assert value['device']['sdk'] == 33 and value['device']['emulator_detected'] is True
    assert value['assets_verified'] is True and value['failure'] is None and value['report_write_failed'] is False
    native = value['native']
    assert native['valid'] is True and native['failed'] is False
    assert native['source_controlled'] is True and native['pointer_bytes'] == 8
    assert native['collision'] is True and native['live_server'] is native['full_atlas'] is False
    assert native['frames'] >= 30 and native['contexts_started'] > 0
    assert session.released_walk_controls(value), 'Integrated snapshots must have drained source controls and authored Ready state'
    assert finite_position(native['actor_position']) and finite_position(native['camera_position'])
    session.grounded_walk(native)
    no_synthetic_input(value)
    rendering_witness(native)
    integration_witness(native)
    if moved:
        assert native['direction_mask'] == 15
        assert native['movement_ticks'] > 0 and native['animation_transitions'] > 0


def integration_witness(native, active=True):
    """Require actual integrated loader/cache/draw results under finite budgets."""
    stream = native['stream']
    assert positive_integer(stream['catalog_instances'])
    assert positive_integer(stream['selected_instances'])
    assert stream['selected_instances'] <= stream['catalog_instances']
    assert positive_integer(stream['budget_bytes'])
    assert type(stream['resident_bytes']) is int and 0 <= stream['resident_bytes'] <= stream['budget_bytes']
    assert type(stream['peak_resident_bytes']) is int
    assert stream['resident_bytes'] <= stream['peak_resident_bytes'] <= stream['budget_bytes']
    assert stream['view_radius'] in (24, 96)
    assert all(type(stream[key]) is int and stream[key] >= 0 for key in
               ('selection_updates', 'cache_hits', 'cache_misses', 'evictions', 'generation', 'draws'))
    assert stream['selection_updates'] > 0 and stream['cache_misses'] > 0
    assets = native['source_assets']
    assert positive_integer(assets['geo_loads']) and positive_integer(assets['texture_loads'])
    assert assets['errors'] == 0
    draw = native['static_renderer']
    assert positive_integer(draw['draw_packets']) and positive_integer(draw['tf_components'])
    assert draw['tf_mismatches'] == 0
    assert positive_integer(draw['visible_pixels'])
    assert draw['material_mode_mask'] == 3, 'Both admitted Multiply and Dual source materials must actually draw'
    if active:
        assert stream['resident_bytes'] > 0 and stream['generation'] > 0 and stream['draws'] > 0
    return True


def action_listener(value, sequence, event_type):
    actions = {'reset_requested', 'recreate_requested', 'export_requested', 'view_distance_requested'}
    matched = [e for e in value['events'] if e['sequence'] > sequence and e['type'] in actions]
    if not matched:
        return None
    assert len(matched) == 1 and matched[0]['type'] == event_type, 'Measured tap reached wrong or multiple action listeners'
    return matched[0]


def tap_view_distance():
    before = session.report()
    sequence = event_sequence(before)
    measurements = []
    for _ in range(3):
        matches = session.button_nodes(session.ui_nodes(), 'View distance')
        assert len(matches) == 1, 'Actual Android View distance button is missing or ambiguous'
        measurements.append(session.bounds(matches[0]))
        time.sleep(.15)
    assert measurements.count(measurements[0]) == len(measurements), 'View distance button moved during measurement'
    x0, y0, x1, y1 = measurements[0]
    session.adb('shell', 'input', 'touchscreen', 'tap', str((x0+x1)//2), str((y0+y1)//2))
    tapped = session.wait(lambda r:action_listener(r, sequence, 'view_distance_requested') is not None,
                          'Actual View distance listener callback')
    event = action_listener(tapped, sequence, 'view_distance_requested')
    proof = {'label': 'View distance', 'bounds': measurements, 'event': event}
    session.BUTTON_PROOFS.append(proof)
    session.save('emulator-button-tap-proof.json', {'schema': 1, 'passed': True, 'taps': session.BUTTON_PROOFS})
    return before, tapped, proof


def view_distance_witness(before, after):
    assert before['session_id'] == after['session_id']
    event_sequence(after)
    event = action_listener(after, event_sequence(before), 'view_distance_requested')
    assert event is not None
    assert session.released_walk_controls(before) and session.released_walk_controls(after)
    no_synthetic_input(before)
    no_synthetic_input(after)
    old, new = before['native']['stream'], after['native']['stream']
    integration_witness(after['native'])
    assert new['catalog_instances'] == old['catalog_instances']
    assert new['budget_bytes'] == old['budget_bytes']
    assert new['view_radius'] == (96 if old['view_radius'] == 24 else 24)
    assert new['selected_instances'] != old['selected_instances'], 'A radius label change cannot substitute for actual source-instance selection'
    assert new['selection_updates'] > old['selection_updates']
    assert new['cache_hits'] + new['cache_misses'] > old['cache_hits'] + old['cache_misses']
    assert new['generation'] >= old['generation'] and new['draws'] > old['draws']
    assert after['native']['frames'] > before['native']['frames']
    assert session.distance(before['native']['actor_position'], after['native']['actor_position']) <= .001
    assert abs(before['native']['camera_yaw'] - after['native']['camera_yaw']) <= .0001
    assert abs(before['native']['camera_pitch'] - after['native']['camera_pitch']) <= .0001
    return event


def change_view_distance():
    before, tapped, button = tap_view_distance()
    target = 96 if before['native']['stream']['view_radius'] == 24 else 24
    after = session.wait(lambda r:session.released_walk_controls(r)
                         and r['native']['stream']['view_radius'] == target
                         and r['native']['stream']['selected_instances'] != before['native']['stream']['selected_instances']
                         and r['native']['frames'] > before['native']['frames'],
                         'Changed radius selects and actually draws a different source-instance set', seconds=30)
    event = view_distance_witness(before, after)
    validate(after)
    proof = {'passed': True, 'before': before, 'tapped': tapped, 'after': after,
             'listener': event, 'button': button,
             'scope': 'Measured genuine Android View distance button changes a bounded query of authentic source instances; source selection count changes while actor and camera are preserved'}
    session.save('emulator-view-distance-%s-proof.json' % target, proof)
    session.progress('bounded source-instance view-distance query and live draws pass', after,
                     view_radius=target, selected_instances=after['native']['stream']['selected_instances'])
    return after


def context_rebuild_witness(before, after):
    assert before['session_id'] == after['session_id']
    validate(after)
    a, b = before['native'], after['native']
    assert b['contexts_started'] > a['contexts_started']
    assert b['frames'] > a['frames'] + 30
    assert session.distance(a['actor_position'], b['actor_position']) <= .001
    assert abs(a['camera_yaw'] - b['camera_yaw']) <= .0001
    assert abs(a['camera_pitch'] - b['camera_pitch']) <= .0001
    assert b['stream']['generation'] > a['stream']['generation']
    assert b['stream']['catalog_instances'] == a['stream']['catalog_instances']
    assert b['stream']['selected_instances'] == a['stream']['selected_instances']
    assert b['stream']['view_radius'] == a['stream']['view_radius']
    assert b['stream']['budget_bytes'] == a['stream']['budget_bytes']
    assert b['stream']['resident_bytes'] == a['stream']['resident_bytes']
    assert b['stream']['draws'] > a['stream']['draws']
    assert b['static_renderer']['tf_components'] > a['static_renderer']['tf_components'], 'A new GPU context must supply a new transform witness'
    assert b['static_renderer']['visible_pixels'] > a['static_renderer']['visible_pixels'], 'A historical readback cannot qualify the rebuilt GPU generation'
    assert b['source_assets']['geo_loads'] == a['source_assets']['geo_loads']
    assert b['source_assets']['texture_loads'] == a['source_assets']['texture_loads']
    assert b['source_assets']['errors'] == 0
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--adb', default='adb')
    args = parser.parse_args()
    session.OUTPUT, session.ADB = args.output, args.adb
    session.OUTPUT.mkdir(parents=True, exist_ok=True)
    configure()
    raw = args.apk.read_bytes()
    identity = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    with zipfile.ZipFile(args.apk) as apk:
        assert apk.testzip() is None
        manifest = json.loads(apk.read('assets/asset-manifest.json'))
        for name, pin in manifest['assets'].items():
            asset = apk.read('assets/' + name)
            assert {'bytes': len(asset), 'sha256': hashlib.sha256(asset).hexdigest()} == pin
    try:
        session.install_and_launch(args.apk)
        first = session.wait(session.native_ready, 'New integrated source loader, bounded Atlas query and renderer startup', seconds=90)
        validate(first)
        assert first['app']['installed_apk'] == identity and first['asset_manifest'] == manifest
        assert 'walkable.bin' in manifest['assets']
        session.save('emulator-initial-report.json', first)
        session.screenshot('emulator-initial-scene.png')
        session.progress('new integrated native source-world scene and GPU witnesses pass', first,
                         selected_instances=first['native']['stream']['selected_instances'])
        initial_position = first['native']['actor_position'][:]
        initial_radius = first['native']['stream']['view_radius']
        initial_selected = first['native']['stream']['selected_instances']
        changed = change_view_distance()
        restored = change_view_distance()
        assert restored['native']['stream']['view_radius'] == initial_radius
        assert restored['native']['stream']['selected_instances'] == initial_selected
        assert restored['native']['source_assets']['geo_loads'] == changed['native']['source_assets']['geo_loads']
        assert restored['native']['source_assets']['texture_loads'] == changed['native']['source_assets']['texture_loads']
        assert restored['native']['stream']['cache_hits'] > changed['native']['stream']['cache_hits']
        # Each case starts from the supported authored spawn. Its own finite
        # framework process releases input before any host-side report polling.
        for key, directions in [('KEYCODE_W', 1), ('KEYCODE_S', 2), ('KEYCODE_A', 4), ('KEYCODE_D', 8)]:
            session.reset_actor(initial_position)
            moved = bounded_key(key, directions)
            validate(moved)
        moved = session.touch_look()
        validate(moved, moved=True)
        assert session.distance(initial_position, moved['native']['actor_position']) > .01
        session.save('emulator-moved-report.json', moved)
        session.screenshot('emulator-moved-scene.png')
        tapped = session.tap_button('Recreate', 'recreate_requested')
        event = session.BUTTON_PROOFS[-1]['event']
        recreated = session.wait(lambda r:session.native_ready(r)
                                 and r['native']['contexts_started'] > event['native']['contexts_started']
                                 and r['native']['frames'] > event['native']['frames'] + 30,
                                 'Recreated live source-instance GPU resources resume', seconds=45)
        context_rebuild_witness(moved, recreated)
        session.save('emulator-recreated-report.json', recreated)
        # Recenter using the actual existing Reset button so the bounded Home
        # case starts behind the real bench instead of near a fixture edge.
        home_before = session.reset_actor(initial_position)
        paused = bounded_home(home_before)
        pre_clear = session.home_interrupt_witness(home_before, paused, source='joystick')[-1]['native']
        assert paused['native']['stream']['resident_bytes'] == pre_clear['stream']['resident_bytes']
        assert paused['native']['stream']['selected_instances'] == pre_clear['stream']['selected_instances']
        if 'gpu_bytes' in paused['native']['static_renderer']:
            assert paused['native']['static_renderer']['gpu_bytes'] == 0
        session.save('emulator-background-report.json', paused)
        returned_receipt = session.adb_receipt('shell', 'am', 'start', '-W', '-n', session.ACTIVITY)
        session.launch_success(returned_receipt)
        returned = session.wait(lambda r:session.native_ready(r)
                                and r['native']['contexts_started'] > paused['native']['contexts_started']
                                and r['native']['frames'] > paused['native']['frames'] + 30
                                and session.released_walk_controls(r),
                                'Actual Home return rebuilds GPU generation and preserves source actor', seconds=45)
        context_rebuild_witness(paused, returned)
        validate(returned, moved=True)
        session.save('emulator-foreground-report.json', returned)
        renewed = bounded_key('KEYCODE_S', 2)
        validate(renewed, moved=True)
        session.screenshot('emulator-foreground-scene.png')
        exported = session.export_document()
        session.wait(session.native_ready, 'Source-world scene returns after actual document picker')
        reset = session.reset_actor(initial_position)
        validate(reset)
        session.save('emulator-final-report.json', reset)
        summary = {'schema': 1, 'gates': GATES, 'passed': True, 'installed_apk': identity,
                   'scope': 'Fresh disposable Android 13 x86_64 install; actual source-loader/cache/static-render integration, bounded source-instance selection, real finite framework movement and camera, recreated/Home render generations, actual document export and Reset',
                   'frames': reset['native']['frames'], 'contexts_started': reset['native']['contexts_started'],
                   'source_assets': reset['native']['source_assets'], 'stream': reset['native']['stream'],
                   'static_renderer': reset['native']['static_renderer'],
                   'actual_framework_callback_source_motion_verified': True,
                   'all_movement_released_before_host_polling': True,
                   'actual_view_distance_selection_verified': True,
                   'actual_context_rebuild_and_source_cache_reuse_verified': True,
                   'actual_home_interrupt_and_renewed_input_verified': True,
                   'actual_document_export_verified': True, 'actual_reset_verified': True,
                   'full_atlas_loaded': False, 'physical_controller_verified': False,
                   'thor_device_execution_verified': False, 'server_interoperability_verified': False}
        session.save('emulator-nextbatch-summary.json', summary)
        print(json.dumps(summary), flush=True)
    finally:
        (session.OUTPUT / 'emulator-logcat.txt').write_bytes(session.adb('logcat', '-d', check=False).stdout)
        screen = session.adb('exec-out', 'screencap', '-p', check=False)
        if screen.returncode == 0 and screen.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            (session.OUTPUT / 'emulator-screenshot.png').write_bytes(screen.stdout)


if __name__ == '__main__':
    main()
