#!/usr/bin/env python3
"""Run the installed probe's real Surface lifecycle on the hosted emulator."""
import json
import math
import pathlib
import subprocess
import time

PACKAGE = 'org.coh.materialprobe'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = pathlib.Path('native-android/results/material-probe')
REPORT = OUTPUT / 'emulator-material-report.json'


def adb(*args, check=True):
    return subprocess.run(['adb', *args], check=check, capture_output=True, timeout=30)


def read_report():
    result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/material-probe-report.json', check=False)
    if result.returncode != 0:
        return None
    if len(result.stdout) > 4 << 20:
        raise RuntimeError('Probe report exceeded 4 MiB evidence limit')
    try:
        report = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    REPORT.write_bytes(result.stdout)
    return report


def wait_report(predicate, label, seconds=120):
    deadline = time.monotonic() + seconds
    last = None
    while time.monotonic() < deadline:
        last = read_report()
        if last is not None and predicate(last):
            return last
        time.sleep(2)
    raise RuntimeError(label + ' did not pass; latest app evidence retained at ' + str(REPORT))


def successful_runs(report):
    return [run for run in report.get('native_runs', [])
            if run.get('passed') is True and run.get('obsolete') is False]


def validate(report):
    assert report['schema'] == 'coh-native-material-probe-v1'
    assert report['qualification_passed'] is True
    assert report['device']['sdk'] == 33
    assert report['device']['emulator_detected'] is True
    qualification = report['qualification']
    assert qualification['failed_runs'] == 0
    assert qualification['successful_surface_generations'] >= 2
    assert qualification['successful_actual_dimensions'] >= 2
    assert qualification['successful_widths'] >= 2
    assert qualification['successful_heights'] >= 2
    runs = successful_runs(report)
    assert len(runs) >= 3
    assert len({(run['callback_width'], run['callback_height']) for run in runs}) >= 2
    assert len({run['generation'] for run in runs}) >= 2
    assert len({run['callback_width'] for run in runs}) >= 2
    assert len({run['callback_height'] for run in runs}) >= 2
    mesh = report['fixture']['model']
    vertex_count = mesh['vertex_count']
    pose_count = len(report['fixture']['poses'])
    material_case_count = report['fixture']['material']['case_count']
    assert vertex_count > 0 and mesh['index_count'] > 0 and mesh['bone_count'] >= 2
    assert mesh['genuinely_blended_vertices'] > 0
    assert pose_count == 2 and material_case_count == 18
    for run in runs:
        native = run['native']
        assert all(native.get(key) is True for key in
                   ['passed', 'mesh_valid', 'skin_transform_match', 'skin_render_match',
                    'material_pixel_match', 'alpha_fog_passed', 'offscreen_passed',
                    'context_recreation_passed', 'window_pixel_match'])
        assert native['surface_width'] == run['callback_width'] > 0
        assert native['surface_height'] == run['callback_height'] > 0
        assert native['pointer_bytes'] == 8 and native['long_bytes'] == 8
        assert native['required_cycles'] == 2 and native['attempted_cycles'] == 2
        assert native['mesh_vertices'] == vertex_count
        assert native['mesh_indices'] == mesh['index_count']
        assert native['mesh_bones'] == mesh['bone_count']
        assert native['pose_count'] == pose_count
        assert native['material_case_count'] == material_case_count
        assert native['real_material_case_count'] == 14
        assert native['synthetic_semantic_case_count'] == 4
        assert native['controlled_dual_rgba'] == [51, 153, 230, 128]
        assert native['transform_absolute_tolerance'] == 0.0001
        assert native['rgba_byte_tolerance'] == 2
        assert native['skin_fbo_width'] == native['skin_fbo_height'] == 384
        assert native['original_cg_execution'] is False
        assert len(native['cycles']) == 2
        for cycle in native['cycles']:
            assert cycle['passed'] is True and cycle['context_created'] is True
            assert cycle['completed'] is True and cycle['objects_released'] is True
            assert cycle['swap_passed'] is True
            assert cycle['gl_errors'] == 0 and cycle['egl_error'] == 0
            assert cycle['surface_width'] == run['callback_width']
            assert cycle['surface_height'] == run['callback_height']
            assert cycle['transform_vertices'] == vertex_count * pose_count
            assert cycle['transform_components'] == vertex_count * pose_count * 6
            assert cycle['transform_mismatches'] == 0
            assert math.isfinite(cycle['max_transform_error'])
            assert 0 <= cycle['max_transform_error'] <= 0.0001
            assert cycle['skin_poses'] == pose_count
            assert cycle['skin_compared_pixels'] > 0
            assert cycle['skin_interior_pixels'] >= 64 * pose_count
            assert cycle['skin_compared_pixels'] + cycle['skin_edge_excluded_pixels'] == 384 * 384 * pose_count
            assert cycle['skin_mismatches'] == 0 and cycle['skin_max_byte_error'] <= 2
            assert cycle['material_cases'] == material_case_count
            assert cycle['real_material_cases'] == 14 and cycle['synthetic_semantic_cases'] == 4
            assert cycle['material_pixels'] == material_case_count * 64 * 64
            assert cycle['material_mismatches'] == 0 and cycle['material_max_byte_error'] <= 2
            assert cycle['material_blended_cases'] > 0
            assert cycle['material_discard_clear_pixels'] > 0
            assert cycle['window_samples'] == 49 and cycle['window_mismatches'] == 0
    names = [event['event'] for event in report['events']]
    for name in ['resize_requested', 'surface_changed', 'surface_recreation_requested',
                 'surface_destroyed', 'surface_created', 'auto_smoke_completed']:
        assert name in names, name


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    apk = OUTPUT / 'CoH-Native-Material-Probe-0.1.0-emulator-x86_64.apk'
    adb('install', '-r', str(apk))
    adb('logcat', '-c')
    try:
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--ez', 'autoSmoke', 'true')
        first = wait_report(lambda report: report.get('qualification_passed') is True
                            and report.get('auto_smoke_stage') == 3,
                            'Skinned material, resize, and Surface recreation')
        validate(first)
        before = len(successful_runs(first))
        adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        wait_report(lambda report: any(event['event'] == 'activity_paused'
                                      for event in report.get('events', [])),
                    'Background lifecycle callback', seconds=20)
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'run')
        final = wait_report(lambda report: report.get('qualification_passed') is True
                            and len(successful_runs(report)) > before,
                            'Render after returning to foreground')
        validate(final)
        names = [event['event'] for event in final['events']]
        assert 'activity_paused' in names and names.count('activity_resumed') >= 2
        cycles = [cycle for run in successful_runs(final) for cycle in run['native']['cycles']]
        summary = {'schema': 1, 'passed': True, 'scope': 'Android 13 x86_64 hosted emulator with SwiftShader; not AYN Thor',
                   'verified_fixture_assets': final['fixture']['verified_assets'],
                   'successful_runs': len(successful_runs(final)),
                   'completed_context_cycles': len(cycles),
                   'gpu_pose_components_compared': sum(cycle['transform_components'] for cycle in cycles),
                   'skinned_image_pixels_compared': sum(cycle['skin_compared_pixels'] for cycle in cycles),
                   'material_pixels_compared': sum(cycle['material_pixels'] for cycle in cycles),
                   'window_samples_compared': sum(cycle['window_samples'] for cycle in cycles),
                   'original_cg_execution': False,
                   'actual_resize_verified': True, 'surface_recreation_verified': True,
                   'foreground_return_verified': True, 'thor_device_execution_verified': False}
        (OUTPUT / 'emulator-smoke-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary))
    finally:
        (OUTPUT / 'emulator-logcat.txt').write_bytes(adb('logcat', '-d', check=False).stdout)
        screenshot = adb('exec-out', 'screencap', '-p', check=False)
        if screenshot.returncode == 0 and screenshot.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            (OUTPUT / 'emulator-screenshot.png').write_bytes(screenshot.stdout)


if __name__ == '__main__':
    main()
