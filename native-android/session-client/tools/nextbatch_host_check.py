#!/usr/bin/env python3
"""Validate fresh real-callback predicates on independent observed-style fixtures.

This qualifies host evidence admission logic only. No fixture in this script is
an Android execution or a physical-device acceptance claim.
"""
import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    path = Path(__file__).with_name('nextbatch_emulator_check.py')
    spec = importlib.util.spec_from_file_location('nextbatch_predicates', path)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    driver.configure()
    labels = []

    def passed(label):
        labels.append(label)

    def rejects(function, label):
        try:
            function()
        except AssertionError:
            passed(label)
        else:
            raise AssertionError('Incorrectly accepted: ' + label)

    native = {'valid': True, 'running': True, 'foreground': True,
              'frames': 120, 'movement_ticks': 50,
              'held_dirs': 0, 'input_pending_edges': 0, 'source_state_bits': 0,
              'motion_local': [0, 0, 0], 'motion_world': [0, 0, 0], 'animation_state': 0,
              'actor_position': [582.5, 74, -1380],
              'walk': {'bounded_scene': True, 'grounded': True, 'ground_y': 74,
                       'triangles': 276, 'blocked_ticks': 0, 'sliding_ticks': 0,
                       'ground_hits': 40, 'collision_queries': 90, 'bounded_ticks': 0}}
    synthetic = {key: 0 for key in ('key_down', 'key_up', 'key_repeat', 'motion',
                                    'touch_begin', 'touch_move', 'touch_end')}
    before = {'session_id': 'independent-fixture-session', 'assets_verified': True, 'resumed': True,
              'native': native, 'events': [{'sequence': 20, 'type': 'resume'}],
              'input_adapter': {'external_android': {'key_down': 5, 'key_up': 5},
                                'in_app_synthetic': deepcopy(synthetic)}}
    after = deepcopy(before)
    after['input_adapter']['external_android'].update(key_down=6, key_up=6)
    down = deepcopy(native)
    down.update(held_dirs=1, input_pending_edges=1)
    up = deepcopy(native)
    up.update(source_state_bits=1, movement_ticks=58, frames=136,
              actor_position=[582.5, 74, -1380.75])
    up['walk'].update(ground_hits=48, collision_queries=114)
    after['events'] += [{'sequence': 21, 'type': 'key_down', 'time_ms': 1000, 'native': down},
                        {'sequence': 22, 'type': 'key_up', 'time_ms': 1250, 'native': up}]
    assert driver.bounded_key_witness(before, after, 1) == after['events'][-1]
    passed('Fresh genuine down/up callback with achieved source motion qualifies')
    for field, value, label in [
        ('held_dirs', 1, 'Still-held final callback'),
        ('source_state_bits', 0, 'Held request without achieved source direction'),
        ('source_state_bits', 2, 'Achieved wrong source direction'),
        ('movement_ticks', 52, 'Fewer than three source ticks'),
        ('movement_ticks', 81, 'Source physics outlived the bounded hold'),
        ('frames', 120, 'Stopped rendered frames'),
        ('actor_position', native['actor_position'], 'No actual source displacement'),
        ('actor_position', [float('nan'), 74, -1381], 'Non-finite actor position'),
        ('foreground', False, 'Background movement receipt'),
        ('running', False, 'Stopped native rendering'),
    ]:
        bad = deepcopy(after)
        bad['events'][-1]['native'][field] = value
        rejects(lambda: driver.bounded_key_witness(before, bad, 1), label)
    for stamp in (1000, 2001, 999):
        bad = deepcopy(after)
        bad['events'][-1]['time_ms'] = stamp
        rejects(lambda: driver.bounded_key_witness(before, bad, 1), 'Unbounded or reversed Android callback time: ' + str(stamp))
    for field, value, label in [
        ('grounded', False, 'Airborne source callback'),
        ('ground_y', 73, 'Ground height mismatch'),
        ('bounded_ticks', 1, 'Safety clamp cannot qualify movement'),
        ('collision_queries', 90, 'No new original collision query'),
        ('ground_hits', 0, 'Missing original ground witness'),
    ]:
        bad = deepcopy(after)
        bad['events'][-1]['native']['walk'][field] = value
        rejects(lambda: driver.bounded_key_witness(before, bad, 1), label)
    for field, value, label in [
        ('key_down', 5, 'No fresh framework down'),
        ('key_up', 5, 'No fresh framework release'),
        ('key_down', 7, 'Unrelated extra framework press'),
        ('key_up', 7, 'Unrelated extra framework release'),
    ]:
        bad = deepcopy(after)
        bad['input_adapter']['external_android'][field] = value
        rejects(lambda: driver.bounded_key_witness(before, bad, 1), label)
    bad = deepcopy(after)
    bad['session_id'] = 'other-session'
    rejects(lambda: driver.bounded_key_witness(before, bad, 1), 'Stale other-session receipt')
    bad = deepcopy(after)
    bad['events'][-2]['sequence'] = 18
    bad['events'][-1]['sequence'] = 19
    rejects(lambda: driver.bounded_key_witness(before, bad, 1), 'Historical prior-command callback')
    bad = deepcopy(after)
    bad['events'][-1]['sequence'] = 21
    rejects(lambda: driver.bounded_key_witness(before, bad, 1), 'Duplicate callback sequence')
    bad = deepcopy(after)
    bad['events'].insert(-1, {'sequence': 22, 'type': 'key_down', 'native': down})
    bad['events'][-1]['sequence'] = 23
    rejects(lambda: driver.bounded_key_witness(before, bad, 1), 'Extra actual keyboard callback')
    bad = deepcopy(after)
    bad['events'][-2]['native']['held_dirs'] = 0
    rejects(lambda: driver.bounded_key_witness(before, bad, 1), 'Press never reached native requested controls')
    for field in synthetic:
        bad = deepcopy(after)
        bad['input_adapter']['in_app_synthetic'][field] = 1
        rejects(lambda: driver.bounded_key_witness(before, bad, 1), 'Synthetic input rejected: ' + field)
    for field, value in [('held_dirs', 1), ('input_pending_edges', 1), ('source_state_bits', 1),
                         ('motion_local', [0, 0, 1]), ('motion_world', [0, 0, 1]), ('animation_state', 2)]:
        bad = deepcopy(before)
        bad['native'][field] = value
        rejects(lambda: driver.bounded_key_witness(bad, after, 1), 'Previous source command not settled: ' + field)
    for direction in (2, 4, 8):
        directional = deepcopy(after)
        directional['events'][-2]['native']['held_dirs'] = direction
        directional['events'][-1]['native']['source_state_bits'] = direction
        assert driver.bounded_key_witness(before, directional, direction)
        passed('Real achieved directional callback admits source bit ' + str(direction))
    for original in ('null', '500'):
        assert driver.framework_timeout_receipt(original, original)['restored'] is True
        passed('Original emulator framework setting restored: ' + original)
        rejects(lambda: driver.framework_timeout_receipt(original, '250'),
                'Changed framework setting cannot be marked restored: ' + original)
    rejects(lambda: driver.framework_timeout_receipt('unexpected output', 'unexpected output'),
            'Malformed framework setting observation')
    # This command grammar has one finite wait and release on normal completion
    # and signal/ordinary-error paths; there is no host report-dependent hold.
    script = driver.bounded_home_script(250)
    assert script.count('sleep ') == 2 and 'sleep 0.250' in script and 'sleep 0.100' in script
    assert 'for coh_home_probe in 1 2 3 4 5 6; do' in script
    assert script.index('test "$coh_home_ready" = 1') < script.rindex('input joystick motionevent MOVE 0 0')
    assert 'trap ' in script and 'EXIT HUP INT TERM' in script
    assert script.index('input keyevent KEYCODE_HOME') < script.index('am start -W -a android.intent.action.MAIN -c android.intent.category.HOME') < script.rindex('input joystick motionevent MOVE 0 0')
    passed('Bounded device-side Home path neutralizes before host polling')
    home_stdout = ('COH_HOME_COMPONENT=com.google.android.apps.nexuslauncher/.NexusLauncherActivity\n'
                   'Starting: Intent { act=android.intent.action.MAIN cat=[android.intent.category.HOME] }\n'
                   'Status: ok\nLaunchState: HOT\nActivity: com.google.android.apps.nexuslauncher/.NexusLauncherActivity\n'
                   'TotalTime: 122\nWaitTime: 123\nComplete\n'
                   'COH_HOME_RESUMED=com.google.android.apps.nexuslauncher/.NexusLauncherActivity\n')
    assert driver.framework_home_completion(home_stdout)['completed'] is True
    passed('Actual synchronous Android HOME completion admits release after launch')
    for bad, label in [
        (home_stdout.replace('Status: ok\n', ''), 'Missing Android HOME completion status'),
        (home_stdout.replace('COH_HOME_RESUMED=com.google.android.apps.nexuslauncher/.NexusLauncherActivity\n', ''), 'am -W alone without actual HOME resumed observation'),
        (home_stdout.replace('COH_HOME_RESUMED=com.google.android.apps.nexuslauncher/.NexusLauncherActivity', 'COH_HOME_RESUMED=org.coh.sessionclient.walk/.MainActivity'), 'Wrong Activity resumed before neutral'),
        (home_stdout.replace('Status: ok', 'Status: timeout'), 'Android HOME launch timed out'),
        (home_stdout.replace('Complete\n', ''), 'HOME launch wait still incomplete'),
        (home_stdout.replace('android.intent.category.HOME', 'android.intent.category.LAUNCHER'), 'Unrelated Activity launch'),
        (home_stdout.replace('Activity: com.google.android.apps.nexuslauncher/.NexusLauncherActivity\n', ''), 'Missing actual HOME Activity identity'),
        (home_stdout + 'Error: Activity class does not exist\n', 'Framework launch error despite success-looking status'),
    ]:
        rejects(lambda: driver.framework_home_completion(bad), label)
    # Match the observed first 0.3 CI race: real forward motion and blocking
    # occurred, but an early neutral arrived before asynchronous Home pause.
    # Historical displacement and aggregate axis coverage cannot substitute for
    # an actually held source direction in the pre-clear lifecycle callback.
    home_before = deepcopy(before)
    home_before['input_adapter']['external_android'].update(motion=0, left_axis_directions=0)
    held = deepcopy(native)
    held.update(held_dirs=1, source_state_bits=1, movement_ticks=98, frames=147,
                actor_position=[582.460449, 74, -1384.01367])
    held['walk'].update(blocked_ticks=10, bounded_ticks=0, collision_queries=281)
    background = deepcopy(held)
    background.update(held_dirs=0, source_state_bits=0, foreground=False, running=False,
                      motion_local=[0,0,0], motion_world=[0,0,0])
    home_paused = {'resumed':False, 'native':background,
                   'input_adapter':{'external_android':{'key_down':5,'key_up':5,'motion':2,'left_axis_directions':4},
                                    'in_app_synthetic':deepcopy(synthetic)},
                   'events':[{'sequence':21,'type':'pause_requested','native':held},
                             {'sequence':22,'type':'pause','native':background}]}
    assert driver.session.home_interrupt_witness(home_before, home_paused, source='joystick')
    passed('Genuine held source movement remains mandatory at the Home pre-clear callback')
    premature = deepcopy(home_paused)
    premature['events'][0]['native'].update(held_dirs=0, source_state_bits=0,
                                           motion_local=[0,0,0], motion_world=[0,0,0])
    rejects(lambda: driver.session.home_interrupt_witness(home_before, premature, source='joystick'),
            'Observed 0.3 early-neutral race cannot qualify historical source movement as held Home interruption')
    for value in (-1, 0, 99, 501, 5000, True, 250.5):
        rejects(lambda: driver.bounded_home_script(value), 'Invalid or excessive device-side hold: ' + repr(value))
    integration = deepcopy(native)
    integration.update(camera_yaw=0, camera_pitch=.16)
    integration['stream'] = {'catalog_instances': 100, 'selected_instances': 12,
                             'resident_bytes': 1024, 'budget_bytes': 4096,
                             'peak_resident_bytes': 2048, 'selection_updates': 5,
                             'cache_hits': 9, 'cache_misses': 2, 'evictions': 0,
                             'generation': 1, 'draws': 120, 'view_radius': 24}
    integration['source_assets'] = {'geo_loads': 2, 'texture_loads': 6, 'errors': 0}
    integration['static_renderer'] = {'draw_packets': 3, 'tf_components': 100,
                                      'tf_mismatches': 0, 'visible_pixels': 200,
                                      'material_mode_mask': 3}
    assert driver.integration_witness(integration)
    passed('Finite source asset residency with actual static draw witnesses qualifies')
    for section, field, value, label in [
        ('stream', 'catalog_instances', 0, 'Empty authentic source catalog'),
        ('stream', 'selected_instances', 0, 'Empty source selection'),
        ('stream', 'selected_instances', 101, 'Selection exceeds authentic catalog'),
        ('stream', 'resident_bytes', 4097, 'Resident cache exceeds budget'),
        ('stream', 'peak_resident_bytes', 4097, 'Peak cache exceeds budget'),
        ('stream', 'resident_bytes', 0, 'Live scene has no actual cache residency'),
        ('stream', 'cache_misses', 0, 'No actual asset admission'),
        ('stream', 'selection_updates', 0, 'No actual source selection update'),
        ('stream', 'generation', 0, 'No actual GPU generation'),
        ('stream', 'draws', 0, 'No actual generic renderer draws'),
        ('stream', 'view_radius', 100000, 'Unbounded or unsupported source query'),
        ('source_assets', 'geo_loads', 0, 'No actual source GEO decode'),
        ('source_assets', 'texture_loads', 0, 'No actual source texture decode'),
        ('source_assets', 'errors', 1, 'Sticky source asset failure'),
        ('static_renderer', 'draw_packets', 0, 'No admitted generic draw packets'),
        ('static_renderer', 'tf_components', 0, 'No actual generic GPU transform comparison'),
        ('static_renderer', 'tf_mismatches', 1, 'Generic GPU transform mismatch'),
        ('static_renderer', 'visible_pixels', 0, 'Generic source geometry has no visible witness'),
        ('static_renderer', 'material_mode_mask', 1, 'Dual source material was not drawn'),
        ('static_renderer', 'material_mode_mask', 2, 'Multiply source material was not drawn'),
    ]:
        bad = deepcopy(integration)
        bad[section][field] = value
        rejects(lambda: driver.integration_witness(bad), label)
    selection_before = deepcopy(before)
    selection_before['native'] = deepcopy(integration)
    selection_after = deepcopy(selection_before)
    selection_after['events'].append({'sequence': 21, 'type': 'view_distance_requested'})
    selection_after['native']['stream'].update(view_radius=96, selected_instances=24,
                                                selection_updates=6, cache_hits=12, draws=160)
    selection_after['native']['frames'] = 160
    assert driver.view_distance_witness(selection_before, selection_after)
    passed('Fresh genuine View distance callback changes bounded source-instance selection')
    for field, value, label in [
        ('view_radius', 24, 'Unchanged source query radius'),
        ('selected_instances', 12, 'Label change without actual instance selection'),
        ('catalog_instances', 101, 'Source catalog changed during distance query'),
        ('budget_bytes', 8192, 'Cache budget changed during distance query'),
        ('selection_updates', 5, 'Historical selection cannot qualify new query'),
        ('cache_hits', 9, 'No fresh cache observation for new query'),
        ('generation', 0, 'No actual source-world GPU generation'),
        ('draws', 120, 'No live rendering after actual query'),
    ]:
        bad = deepcopy(selection_after)
        bad['native']['stream'][field] = value
        rejects(lambda: driver.view_distance_witness(selection_before, bad), label)
    for field, value, label in [
        ('frames', 120, 'Non-advancing render after distance change'),
        ('actor_position', [583.5, 74, -1380], 'Distance button secretly moved actor'),
        ('camera_yaw', 1, 'Distance button secretly changed camera yaw'),
        ('camera_pitch', 1, 'Distance button secretly changed camera pitch'),
    ]:
        bad = deepcopy(selection_after)
        bad['native'][field] = value
        rejects(lambda: driver.view_distance_witness(selection_before, bad), label)
    bad = deepcopy(selection_after)
    bad['events'][-1]['sequence'] = 19
    rejects(lambda: driver.view_distance_witness(selection_before, bad), 'Stale historical View distance listener')
    bad = deepcopy(selection_after)
    bad['events'][-1]['type'] = 'reset_requested'
    rejects(lambda: driver.view_distance_witness(selection_before, bad), 'Wrong actual button listener')
    bad = deepcopy(selection_after)
    bad['events'].append({'sequence': 22, 'type': 'recreate_requested'})
    rejects(lambda: driver.view_distance_witness(selection_before, bad), 'Multiple actual action callbacks')
    receipt = {'schema': 1, 'passed': True, 'checks': len(labels), 'predicates': labels,
               'scope': 'Independent host fixtures for fresh actual framework callback admission, unchanged grounded source predicates, exact release ordering, restored disposable timing and finite Home input grammar; no Android or physical execution',
               'driver_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'shared_driver_sha256': hashlib.sha256(driver._BASE_PATH.read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
