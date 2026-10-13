#!/usr/bin/env python3
"""Qualify real encoded animation and Surface lifecycle on the hosted emulator."""
import hashlib
import json
import math
import pathlib
import subprocess
import time
import zipfile

PACKAGE = 'org.coh.animationprobe'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = pathlib.Path('native-android/results/animation-probe')
REPORT = OUTPUT / 'emulator-animation-report.json'
REQUIRED_ASSETS = {'mesh.bin', 'texture0.rgba', 'texture1.rgba', 'rig.bin',
                   'rig-reference.bin', 'material-reference.bin'}


def adb(*args, check=True):
    return subprocess.run(['adb', *args], check=check, capture_output=True, timeout=30)


def read_report():
    result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/animation-probe-report.json', check=False)
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


def validate_assets(report, apk):
    """Compare hashes reported by Java with the actual installed APK inputs."""
    verified = report['fixture']['verified_assets']
    assert set(verified) == REQUIRED_ASSETS
    with zipfile.ZipFile(apk) as bundle:
        metadata = json.loads(bundle.read('assets/animation-fixture.json'))
        assert set(metadata['assets']) == REQUIRED_ASSETS
        for name in sorted(REQUIRED_ASSETS):
            payload = bundle.read('assets/' + name)
            identity = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
            assert verified[name] == identity, name
            assert metadata['assets'][name]['bytes'] == identity['bytes'], name
            assert metadata['assets'][name]['sha256'] == identity['sha256'], name
        assert report['fixture']['verified_total_bytes'] == sum(item['bytes'] for item in verified.values())


def validate_fixture(fixture):
    assert fixture['container'] == 'COHRIG01'
    assert fixture['base']['name'].casefold() == 'huge/skel_ready'
    assert fixture['motion']['name'].casefold() == 'huge/run'
    assert fixture['base']['bone_count'] == 60 and fixture['motion']['bone_count'] == 44
    assert fixture['palette_global_ids'] == [9, 5, 7] and fixture['socket_global_id'] == 72
    assert fixture['required_global_ids'] == [0, 1, 2, 5, 7, 9, 72]
    assert fixture['first_frame'] == 1 and fixture['last_frame'] == 25
    assert fixture['diagnostic_ticks_per_second'] == 30
    assert fixture['encoded_source_keys_preserved'] is fixture['runtime_sampler_required'] is True
    assert fixture['full_sequencer_speed_model_applied'] is False
    assert fixture['geom_scale_applied'] is fixture['bone_morphing_applied'] is False
    reference = fixture['reference']
    assert reference['format'] == 'COHAGL01' and reference['sample_count'] == 6
    assert reference['bone_count'] == 60 and reference['palette_count'] == 3
    assert reference['vertex_count'] == 116
    assert reference['checkpoint_frames'] == [1.0, 1.5, 5.25, 12.5, 24.5, 25.0]
    assert reference['portable_sampler_executed_by_generator'] is False
    assert reference['original_runtime_capture'] is False
    mesh = fixture['model']
    vertex_count = mesh['vertex_count']
    pose_count = reference['sample_count']
    material_case_count = fixture['material']['case_count']
    assert vertex_count > 0 and mesh['index_count'] > 0 and mesh['bone_count'] >= 2
    assert mesh['genuinely_blended_vertices'] > 0
    assert vertex_count == 116 and mesh['index_count'] == 594 and mesh['bone_count'] == 3
    assert pose_count == 6 and material_case_count == 18
    return vertex_count, pose_count, material_case_count


def validate(report, minimum_generations=2):
    assert report['schema'] == 'coh-native-animation-probe-v1'
    assert report['qualification_passed'] is True
    assert report['passed'] is report['overall_passed'] is True
    assert report['session_failures'] == 0
    assert report['device']['sdk'] == 33
    assert report['device']['emulator_detected'] is True
    qualification = report['qualification']
    assert qualification['failed_runs'] == 0
    assert qualification['successful_surface_generations'] >= minimum_generations
    assert qualification['current_surface_passed'] is True
    assert qualification['pending_requirements'] == []
    assert qualification['successful_actual_dimensions'] >= 2
    assert qualification['successful_widths'] >= 2
    assert qualification['successful_heights'] >= 2
    runs = successful_runs(report)
    assert len(runs) >= 3
    assert len({(run['callback_width'], run['callback_height']) for run in runs}) >= 2
    assert len({run['generation'] for run in runs}) >= minimum_generations
    assert len({run['callback_width'] for run in runs}) >= 2
    assert len({run['callback_height'] for run in runs}) >= 2
    mesh = report['fixture']['model']
    vertex_count, pose_count, material_case_count = validate_fixture(report['fixture'])
    for run in runs:
        assert run['session_id'] == report['session_id']
        assert run['java_validation']['required_native_checks'] is True
        assert run['java_validation']['native_context_cycles_match'] is True
        native = run['native']
        assert all(native.get(key) is True for key in
                   ['passed', 'mesh_valid', 'skin_transform_match', 'skin_render_match',
                    'material_pixel_match', 'alpha_fog_passed', 'offscreen_passed',
                    'context_recreation_passed', 'window_pixel_match', 'rig_valid',
                    'animation_sample_match', 'hierarchy_match', 'socket_palette_match',
                    'animation_clock_match', 'animated_preview_passed'])
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
            assert all(cycle.get(key) is True for key in
                       ['skin_transform_match', 'skin_render_match', 'material_pixel_match',
                        'window_pixel_match', 'animation_sample_match', 'hierarchy_match',
                        'socket_palette_match', 'animation_clock_match', 'animated_preview_passed'])
            assert cycle['completed'] is True and cycle['objects_released'] is True
            assert cycle['swap_passed'] is True
            assert cycle['gl_errors'] == 0 and cycle['egl_error'] == 0
            assert cycle['surface_width'] == run['callback_width']
            assert cycle['surface_height'] == run['callback_height']
            assert cycle['transform_vertices'] == vertex_count * pose_count
            assert cycle['transform_components'] == vertex_count * pose_count * 6
            assert cycle['transform_mismatches'] == 0
            assert cycle['position_mismatches'] == cycle['normal_mismatches'] == 0
            assert cycle['stock_normal_components'] == vertex_count * pose_count * 3
            assert math.isfinite(cycle['stock_normal_max_error'])
            assert math.isfinite(cycle['max_transform_error'])
            assert 0 <= cycle['max_transform_error'] <= 0.0001
            assert cycle['skin_poses'] == pose_count
            assert cycle['skin_compared_pixels'] > 0
            assert cycle['skin_interior_pixels'] >= 64 * pose_count
            assert cycle['skin_compared_pixels'] + cycle['skin_edge_excluded_pixels'] == 384 * 384 * pose_count
            assert cycle['skin_mismatches'] == 0 and cycle['skin_max_byte_error'] <= 2
            interiors = cycle['skin_pose_interior_pixels']
            excluded = cycle['skin_pose_edge_excluded_pixels']
            compared = cycle['skin_pose_compared_pixels']
            assert len(interiors) == len(excluded) == len(compared) == pose_count
            assert all(interior >= 64 for interior in interiors)
            assert all(a + b == 384 * 384 for a, b in zip(compared, excluded))
            assert sum(interiors) == cycle['skin_interior_pixels']
            assert sum(excluded) == cycle['skin_edge_excluded_pixels']
            assert sum(compared) == cycle['skin_compared_pixels']
            assert cycle['material_cases'] == material_case_count
            assert cycle['real_material_cases'] == 14 and cycle['synthetic_semantic_cases'] == 4
            assert cycle['material_pixels'] == material_case_count * 64 * 64
            assert cycle['material_mismatches'] == 0 and cycle['material_max_byte_error'] <= 2
            assert cycle['material_blended_cases'] > 0
            assert cycle['material_discard_clear_pixels'] > 0
            assert cycle['window_samples'] == 49 and cycle['window_mismatches'] == 0
            assert cycle['animation_samples'] == pose_count
            assert cycle['hierarchy_nodes_verified'] == cycle['hierarchy_parent_comparisons'] == 60
            for name, components in [('local', 2520), ('world', 4320), ('btt', 180),
                                     ('bpt', 4320), ('palette', 216)]:
                assert cycle[name + '_components'] == components
                assert cycle[name + '_mismatches'] == 0
                error = cycle[name + '_max_error']
                assert math.isfinite(error) and 0 <= error <= 0.0001
            assert cycle['animation_clock_cases'] == 8
            assert cycle['animation_clock_mismatches'] == 0
            assert cycle['base_fallback_samples'] == 96
            assert cycle['preview_frames'] == cycle['preview_clock_steps'] == 45
            assert cycle['preview_clock_wraps'] >= 1
            assert cycle['preview_first_frame'] == 1
            assert cycle['preview_last_frame'] == 21 and cycle['preview_next_frame'] == 22
            assert cycle['distinct_animated_poses'] >= 2
            assert cycle['preview_image_samples'] == 3
            assert 1 <= cycle['preview_changed_image_samples'] <= 2
            assert cycle['preview_pixels_changed_from_first'] >= 64
    names = [event['event'] for event in report['events']]
    for name in ['resize_requested', 'surface_changed', 'surface_recreation_requested',
                 'surface_destroyed', 'surface_created', 'auto_smoke_completed']:
        assert name in names, name


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    apk = OUTPUT / 'CoH-Native-Animation-Probe-0.1.0-emulator-x86_64.apk'
    adb('install', '-r', str(apk))
    adb('shell', 'am', 'force-stop', PACKAGE)
    # A new CI session cannot inherit successful runs from an earlier attempt.
    adb('shell', 'pm', 'clear', PACKAGE)
    adb('logcat', '-c')
    try:
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--ez', 'autoSmoke', 'true')
        first = wait_report(lambda report: report.get('qualification_passed') is True
                            and report.get('auto_smoke_stage') == 3,
                            'Encoded animation, material, resize, and Surface recreation')
        validate(first)
        validate_assets(first, apk)
        (OUTPUT / 'emulator-initial-report.json').write_text(json.dumps(first, indent=2)+'\n')
        session = first['session_id']
        before = max(run['request'] for run in successful_runs(first))
        before_generation = max(run['generation'] for run in successful_runs(first))
        adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        paused = wait_report(lambda report: report.get('session_id') == session
                             and report.get('qualification_passed') is False
                             and all(any(event['event'] == name for event in report.get('events', []))
                                     for name in ('activity_paused', 'activity_stopped')),
                             'Background lifecycle callbacks', seconds=30)
        (OUTPUT / 'emulator-background-report.json').write_text(json.dumps(paused, indent=2)+'\n')
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'run')
        foreground = wait_report(lambda report: report.get('qualification_passed') is True
                                 and report.get('session_id') == session
                                 and any(run['request'] > before and run['generation'] > before_generation
                                         for run in successful_runs(report)),
                                 'Native animation on a new Surface after foreground return')
        validate(foreground, minimum_generations=3)
        (OUTPUT / 'emulator-foreground-report.json').write_text(json.dumps(foreground, indent=2)+'\n')
        before = max(run['request'] for run in successful_runs(foreground))
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'resize')
        resized = wait_report(lambda report: report.get('qualification_passed') is True
                              and report.get('session_id') == session
                              and any(run['request'] > before for run in successful_runs(report)),
                              'Second actual Surface resize')
        validate(resized, minimum_generations=3)
        before_generation = max(run['generation'] for run in successful_runs(resized))
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'recreate')
        final = wait_report(lambda report: report.get('qualification_passed') is True
                            and report.get('session_id') == session
                            and any(run['generation'] > before_generation for run in successful_runs(report)),
                            'Second explicit Surface recreation')
        validate(final, minimum_generations=4)
        validate_assets(final, apk)
        names = [event['event'] for event in final['events']]
        assert 'activity_paused' in names and names.count('activity_resumed') >= 2
        pause_index = names.index('activity_paused')
        resume_index = next(index for index, name in enumerate(names)
                            if index > pause_index and name == 'activity_resumed')
        assert 'activity_stopped' in names[pause_index+1:resume_index]
        assert 'surface_destroyed' in names[pause_index+1:resume_index]
        assert 'surface_created' in names[resume_index+1:]
        assert names.count('surface_created') >= 4
        assert names.count('surface_recreation_requested') >= 2
        assert names.count('resize_requested') >= 2
        cycles = [cycle for run in successful_runs(final) for cycle in run['native']['cycles']]
        summary = {'schema': 1, 'passed': True, 'scope': 'Android 13 x86_64 hosted emulator with SwiftShader; not AYN Thor',
                   'verified_fixture_assets': final['fixture']['verified_assets'],
                   'successful_runs': len(successful_runs(final)),
                   'successful_surface_generations': final['qualification']['successful_surface_generations'],
                   'successful_actual_dimensions': final['qualification']['successful_actual_dimensions'],
                   'successful_actual_widths': final['qualification']['successful_widths'],
                   'successful_actual_heights': final['qualification']['successful_heights'],
                   'completed_context_cycles': len(cycles),
                   'gpu_pose_components_compared': sum(cycle['transform_components'] for cycle in cycles),
                   'skinned_image_pixels_compared': sum(cycle['skin_compared_pixels'] for cycle in cycles),
                   'material_pixels_compared': sum(cycle['material_pixels'] for cycle in cycles),
                   'window_samples_compared': sum(cycle['window_samples'] for cycle in cycles),
                   'presented_animated_frames': sum(cycle['preview_frames'] for cycle in cycles),
                   'original_local_components_compared': sum(cycle['local_components'] for cycle in cycles),
                   'hierarchy_world_components_compared': sum(cycle['world_components'] for cycle in cycles),
                   'bind_translation_components_compared': sum(cycle['btt_components'] for cycle in cycles),
                   'inverse_bind_components_compared': sum(cycle['bpt_components'] for cycle in cycles),
                   'socket_palette_components_compared': sum(cycle['palette_components'] for cycle in cycles),
                   'original_clock_cases_compared': sum(cycle['animation_clock_cases'] for cycle in cycles),
                   'missing_motion_base_fallback_samples': sum(cycle['base_fallback_samples'] for cycle in cycles),
                   'stock_normal_components_compared_diagnostic_only': sum(cycle['stock_normal_components'] for cycle in cycles),
                   'stock_normal_mismatches_diagnostic_only': sum(cycle['stock_normal_mismatches'] for cycle in cycles),
                   'native_animation_clock_steps': sum(cycle['preview_clock_steps'] for cycle in cycles),
                   'native_animation_clock_wraps': sum(cycle['preview_clock_wraps'] for cycle in cycles),
                   'animated_image_temporal_samples': sum(cycle['preview_image_samples'] for cycle in cycles),
                   'animated_images_changed_from_first': sum(cycle['preview_changed_image_samples'] for cycle in cycles),
                   'animated_pixels_changed_from_first': sum(cycle['preview_pixels_changed_from_first'] for cycle in cycles),
                   'original_cg_execution': False,
                   'original_game_execution': False, 'full_sequencer_execution': False,
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
