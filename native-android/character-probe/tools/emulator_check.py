#!/usr/bin/env python3
"""Qualify real encoded animation and Surface lifecycle on the hosted emulator."""
import hashlib
import json
import math
import pathlib
import subprocess
import time
import zipfile

PACKAGE = 'org.coh.characterprobe'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = pathlib.Path('native-android/results/character-probe')
REPORT = OUTPUT / 'emulator-character-report.json'
REQUIRED_ASSETS = {'character.bin', 'rig.bin', 'morph.bin', 'character-reference.bin', 'material-reference.bin'}


def adb(*args, check=True):
    return subprocess.run(['adb', *args], check=check, capture_output=True, timeout=30)


def read_report():
    result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/character-probe-report.json', check=False)
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
        metadata = json.loads(bundle.read('assets/character-fixture.json'))
        assert set(metadata['assets']) == REQUIRED_ASSETS
        for name in sorted(REQUIRED_ASSETS):
            payload = bundle.read('assets/' + name)
            identity = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
            assert verified[name] == identity, name
            assert metadata['assets'][name]['bytes'] == identity['bytes'], name
            assert metadata['assets'][name]['sha256'] == identity['sha256'], name
        assert report['fixture']['verified_total_bytes'] == sum(item['bytes'] for item in verified.values())


def validate_fixture(fixture):
    scene = fixture['scene']
    assert scene['container'] == 'COHCHAR8'
    assert scene['part_count'] == 11 and scene['texture_count'] == 17
    assert scene['vertex_count'] == 2626 and scene['index_count'] == 8958
    assert scene['triangle_count'] == 2986 and scene['genuinely_blended_vertices'] == 620
    assert scene['contains_baked_poses'] is False and scene['native_runtime_skinning_required'] is True
    assert len(fixture['parts']) == len(fixture['meshes']) == 11
    assert sum(part['vertex_count'] for part in fixture['parts']) == 2626
    assert sum(part['triangle_count'] for part in fixture['parts']) == 2986
    assert sum(len(part['palette_global_ids']) for part in fixture['parts']) == 45
    assert all(part['mirror'] is False for part in fixture['parts'])
    assert fixture['animation']['base']['bone_count'] == 60
    assert fixture['animation']['motion']['bone_count'] == 44
    ref = fixture['reference']
    assert ref['format'] == 'COHCHR01' and ref['bytes'] == 438216
    assert ref['sample_count'] == 6 and ref['bone_count'] == 60
    assert ref['draw_count'] == 11 and ref['palette_matrix_count'] == 45
    assert ref['vertex_count'] == 2626
    assert ref['frame_samples'] == [1, 1.5, 5.25, 12.5, 24.5, 25]
    assert ref['portable_native_sampler_called_by_generator'] is False
    assert ref['node_bone_scale_propagates_to_children'] is False
    assert set(fixture['assets']) == REQUIRED_ASSETS
    return 2626, 6, 66


def validate(report, minimum_generations=2):
    assert report['schema'] == 'coh-native-character-probe-v1'
    assert report['qualification_passed'] is True
    assert report['passed'] is report['overall_passed'] is True
    assert report['session_failures'] == 0
    assert report['device']['sdk'] == 33 and report['device']['emulator_detected'] is True
    q = report['qualification']
    assert q['failed_runs'] == 0 and q['current_surface_passed'] is True and q['pending_requirements'] == []
    assert q['successful_surface_generations'] >= minimum_generations
    assert q['successful_actual_dimensions'] >= 2 and q['successful_widths'] >= 2 and q['successful_heights'] >= 2
    runs = successful_runs(report)
    assert len(runs) >= 3 and len({run['generation'] for run in runs}) >= minimum_generations
    assert len({run['callback_width'] for run in runs}) >= 2 and len({run['callback_height'] for run in runs}) >= 2
    vertices, poses, materials = validate_fixture(report['fixture'])
    flags = ['passed', 'mesh_valid', 'rig_valid', 'morph_valid', 'character_valid', 'actor_sample_match',
             'hierarchy_match', 'morph_scale_match', 'socket_palette_match', 'character_assembly_match',
             'animation_clock_match', 'animated_preview_passed', 'skin_transform_match', 'skin_render_match',
             'material_pixel_match', 'alpha_fog_passed', 'offscreen_passed', 'context_recreation_passed', 'window_pixel_match']
    counts = {'local_components': 2520, 'world_components': 4320, 'scaled_world_components': 4320,
              'btt_components': 180, 'morph_scale_components': 192, 'palette_components': 3240}
    for run in runs:
        assert run['session_id'] == report['session_id']
        assert run['java_validation']['required_native_checks'] is True
        assert run['java_validation']['native_context_cycles_match'] is True
        native = run['native']
        assert all(native.get(key) is True for key in flags)
        assert native['surface_width'] == run['callback_width'] > 0 and native['surface_height'] == run['callback_height'] > 0
        assert native['pointer_bytes'] == native['long_bytes'] == 8
        assert native['required_cycles'] == native['attempted_cycles'] == len(native['cycles']) == 2
        assert native['character_part_count'] == 11 and native['costume_category_count'] == 10
        assert native['mesh_vertices'] == vertices and native['mesh_indices'] == 8958 and native['blended_vertices'] == 620
        assert native['unique_textures'] == 17 and native['palette_matrix_count'] == 45
        assert native['pose_count'] == poses and native['material_case_count'] == materials
        assert native['skin_fbo_width'] == native['skin_fbo_height'] == 512
        assert native['transform_absolute_tolerance'] == 0.0001 and native['rgba_byte_tolerance'] == 2
        assert native['triangle_edge_exclusion_pixels'] == 2
        assert native['standalone_projection_scope'] == 'per-part-six-checkpoint-union'
        assert native['standalone_minimum_interior_pixels_per_part_pose'] == 64
        assert native['assembled_projection_independent_of_standalone'] is True
        assert native['original_cg_execution'] is False and native['reference_palettes_drive_rendering'] is False
        assert native['high_quality_materials_qualified'] is False
        assert native['front_face'] == 'CW' and native['depth_write'] is True
        assert native['first_frame'] == 1 and native['last_frame'] == 25 and native['ticks_per_second'] == 30
        for c in native['cycles']:
            assert c['passed'] and c['completed'] and c['context_created'] and c['objects_released'] and c['swap_passed']
            assert c['gl_errors'] == c['egl_error'] == 0
            assert c['surface_width'] == run['callback_width'] and c['surface_height'] == run['callback_height']
            assert c['transform_vertices'] == vertices * poses and c['transform_components'] == vertices * poses * 6
            assert c['transform_mismatches'] == c['position_mismatches'] == c['normal_mismatches'] == 0
            assert 0 <= c['max_transform_error'] <= 0.0001 and math.isfinite(c['max_transform_error'])
            assert c['stock_normal_components'] == vertices * poses * 3
            assert math.isfinite(c['stock_normal_max_error'])
            assert c['animation_samples'] == poses and c['hierarchy_nodes_verified'] == c['hierarchy_parent_comparisons'] == 60
            assert c['part_palettes_sampled'] == 66 and c['base_fallback_samples'] == 96
            for key, expected in counts.items():
                assert c[key] == expected, key
            for key in ['local', 'world', 'scaled_world', 'btt', 'morph_scale', 'palette']:
                assert c[key+'_mismatches'] == 0 and 0 <= c[key+'_max_error'] <= 0.0001, key
            assert c['animation_clock_cases'] == 8 and c['animation_clock_mismatches'] == 0
            assert c['skin_poses'] == poses and c['skin_mismatches'] == 0 and c['skin_max_byte_error'] <= 2
            assert c['skin_interior_pixels'] >= 64 * poses
            assert c['skin_compared_pixels'] + c['skin_edge_excluded_pixels'] == 512 * 512 * poses
            assert len(c['skin_pose_interior_pixels']) == poses and all(n >= 64 for n in c['skin_pose_interior_pixels'])
            assert sum(c['skin_pose_compared_pixels']) == c['skin_compared_pixels']
            assert sum(c['skin_pose_edge_excluded_pixels']) == c['skin_edge_excluded_pixels']
            assert sum(c['skin_pose_interior_pixels']) == c['skin_interior_pixels']
            assert len(c['part_interior_pixels']) == 11 and all(n >= 64 * poses for n in c['part_interior_pixels'])
            assert c['part_transform_vertices'] == [part['vertex_count'] * poses for part in report['fixture']['parts']]
            assert c['part_palette_components'] == [len(part['palette_global_ids']) * 12 * poses for part in report['fixture']['parts']]
            assert len(c['part_image_compared_pixels']) == len(c['part_image_mismatches']) == 11
            assert all(n > 0 for n in c['part_image_compared_pixels']) and not any(c['part_image_mismatches'])
            assert c['standalone_compared_pixels'] == sum(c['part_image_compared_pixels'])
            assert c['standalone_mismatches'] == 0 and c['standalone_max_byte_error'] <= 2
            assert c['material_cases'] == materials and c['material_pixels'] == materials * 64 * 64
            assert c['real_material_cases'] == 44 and c['synthetic_semantic_cases'] == 22
            assert c['material_mismatches'] == 0 and c['material_max_byte_error'] <= 2
            assert c['material_blended_cases'] > 0 and c['material_discard_clear_pixels'] > 0
            assert c['window_samples'] == 49 and c['window_mismatches'] == 0
            assert c['preview_frames'] == c['preview_clock_steps'] == 45 and c['preview_clock_wraps'] == 1
            assert c['distinct_animated_poses'] >= 2 and c['preview_first_frame'] == 1
            assert c['preview_last_frame'] == 21 and c['preview_next_frame'] == 22
            assert c['preview_image_samples'] == 3 and 1 <= c['preview_changed_image_samples'] <= 2
            assert c['preview_pixels_changed_from_first'] >= 64
    names = [event['event'] for event in report['events']]
    assert all(name in names for name in ['resize_requested', 'surface_changed', 'surface_recreation_requested',
                                        'surface_destroyed', 'surface_created', 'auto_smoke_completed'])


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    apk = OUTPUT / 'CoH-Native-Character-Probe-0.1.0-emulator-x86_64.apk'
    adb('install', '-r', str(apk))
    adb('shell', 'am', 'force-stop', PACKAGE)
    # A new CI session cannot inherit successful runs from an earlier attempt.
    adb('shell', 'pm', 'clear', PACKAGE)
    adb('logcat', '-c')
    try:
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--ez', 'autoSmoke', 'true')
        first = wait_report(lambda report: report.get('qualification_passed') is True
                            and report.get('auto_smoke_stage') == 3,
                            'Complete character, material, resize, and Surface recreation')
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
                   'scaled_world_components_compared': sum(cycle['scaled_world_components'] for cycle in cycles),
                   'morph_scale_components_compared': sum(cycle['morph_scale_components'] for cycle in cycles),
                   'standalone_image_pixels_compared': sum(cycle['standalone_compared_pixels'] for cycle in cycles),
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
