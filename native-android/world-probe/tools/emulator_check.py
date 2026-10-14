#!/usr/bin/env python3
"""Qualify source-authored world geometry, camera and Surface lifecycle.

Counts come from the exact installed APK binary inputs; report assertions do not
borrow actor counts, relax byte/float tolerances, or accept export-picker events.
"""
import hashlib
import json
import math
import pathlib
import struct
import subprocess
import time
import zipfile

PACKAGE = 'org.coh.worldprobe'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = pathlib.Path('native-android/results/world-probe')
REPORT = OUTPUT / 'emulator-world-report.json'
REQUIRED_ASSETS = {'world.bin', 'world-reference.bin', 'material-reference.bin'}
FBO_SIZE = 512
POSES = 6
NODES = 6


def adb(*args, check=True):
    return subprocess.run(['adb', *args], check=check, capture_output=True, timeout=30)


def read_report():
    result = adb('exec-out', 'run-as', PACKAGE, 'cat', 'files/world-probe-report.json', check=False)
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


def wait_report(predicate, label, seconds=180):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        last = read_report()
        if last is not None and predicate(last):
            return last
        time.sleep(2)
    raise RuntimeError(label + ' did not pass; latest app evidence retained at ' + str(REPORT))


def successful_runs(report):
    return [run for run in report.get('native_runs', [])
            if run.get('passed') is True and run.get('obsolete') is False]


def _u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def inspect_apk_inputs(apk):
    """Independently derive report cardinalities from immutable input envelopes."""
    with zipfile.ZipFile(apk) as bundle:
        expected = REQUIRED_ASSETS | {'world-fixture.json'}
        packaged = {name.removeprefix('assets/') for name in bundle.namelist()
                    if name.startswith('assets/') and not name.endswith('/')}
        assert packaged == expected, packaged
        metadata_bytes = bundle.read('assets/world-fixture.json')
        assert 0 < len(metadata_bytes) <= 512 * 1024
        metadata = json.loads(metadata_bytes)
        assert set(metadata['assets']) == REQUIRED_ASSETS
        payloads = {name: bundle.read('assets/' + name) for name in REQUIRED_ASSETS}
    for name, payload in payloads.items():
        identity = metadata['assets'][name]
        assert identity['bytes'] == len(payload)
        assert identity['sha256'] == hashlib.sha256(payload).hexdigest()
    data = payloads['world.bin']
    assert 128 <= len(data) <= 16 << 20
    assert data[:8] == b'COHWOR09' and _u32(data, 8) == 1 and _u32(data, 12) == 128
    parts, textures, vertices, indices = struct.unpack_from('<4I', data, 16)
    assert 0 < parts <= 16 and 0 < textures <= 32
    assert _u32(data, 32) == 128 and _u32(data, 36) == 96
    texture_offset, texture_stride, input_offset, input_size, cursor, total = struct.unpack_from('<6I', data, 40)
    assert texture_offset == 128 + parts * 96 and texture_stride == 32
    assert input_offset == texture_offset + textures * 32 and input_size == 520
    assert cursor == input_offset + input_size and total == len(data)
    assert data[64:128] == bytes(64)
    assert data[input_offset:input_offset + 8] == b'COHWRI09'
    part_vertices, part_indices, flags, modes = [], [], [], []
    for index in range(parts):
        r = 128 + index * 96
        mesh_offset, mesh_bytes, node, base, dual, flag = struct.unpack_from('<6I', data, r)
        assert mesh_offset == cursor and mesh_bytes > 0 and cursor + mesh_bytes <= len(data)
        assert node < NODES and base < textures and dual < textures and flag & ~3 == 0
        mode = _u32(data, r + 68)
        assert mode in (0, 1) and data[r + 72:r + 96] == bytes(24)
        mesh = data[cursor:cursor + mesh_bytes]
        assert mesh[:8] == b'COHMESH1' and _u32(mesh, 8) == 1 and _u32(mesh, 12) == 64
        nv, ni, bones, stride, vo, io, bo, length = struct.unpack_from('<8I', mesh, 16)
        assert 0 < nv <= 65536 and 0 < ni <= 196608 and ni % 3 == 0
        assert bones == 1 and stride == 48 and vo == 64
        assert io == vo + nv * stride and bo == io + ni * 4 and bo + 4 == length == mesh_bytes
        assert mesh[48:64] == bytes(16)
        assert all(value < nv for value in struct.unpack_from('<' + 'I' * ni, mesh, io))
        for v in range(nv):
            p = vo + v * stride
            values = struct.unpack_from('<10f2I', mesh, p)
            assert all(math.isfinite(x) for x in values[:10])
            assert values[8:10] == (1.0, 0.0) and values[10:] == (0, 0)
            assert sum(x * x for x in values[3:6]) > 0
        part_vertices.append(nv)
        part_indices.append(ni)
        flags.append(flag)
        modes.append(mode)
        cursor += mesh_bytes
    assert sum(part_vertices) == vertices and sum(part_indices) == indices
    for index in range(textures):
        r = texture_offset + index * texture_stride
        offset, size, width, height = struct.unpack_from('<4I', data, r)
        assert offset == cursor and 0 < width <= 4096 and 0 < height <= 4096
        assert size == width * height * 4 and cursor + size <= len(data)
        assert data[r + 16:r + 32] == bytes(16)
        cursor += size
    assert cursor == len(data)
    material = payloads['material-reference.bin']
    assert material[:8] == b'COHWMAT9'
    assert struct.unpack_from('<12I', material, 8) == (1, 64, 64, 64, parts * 6, 128, parts, 16384, 16512, 64, len(material), 0)
    assert material[52:64] == bytes(12) and len(material) == 64 + parts * 6 * 16512
    expected_flags = [0, 1, 0, 1, 2, 3]
    expected_refs = [0.0, 0.0, 0.0, 1.0, 0.0, struct.unpack('<f', struct.pack('<f', .6))[0]]
    expected_clear_pixels = 0
    for index in range(parts * 6):
        r = 64 + index * 16512
        assert struct.unpack_from('<3I', material, r + 104) == (expected_flags[index % 6], index // 6, index % 6)
        assert struct.unpack_from('<f', material, r + 100)[0] == expected_refs[index % 6]
        assert _u32(material, r + 116) == modes[index // 6]
        assert material[r + 120:r + 128] == bytes(8)
        clear = struct.unpack_from('<4f', material, r + 80)
        clear_rgba = bytes(math.floor(min(1, max(0, x)) * 255 + .5) for x in clear)
        expected_pixels = material[r + 128:r + 16512]
        expected_clear_pixels += sum(expected_pixels[p:p + 4] == clear_rgba for p in range(0, 16384, 4))
    reference = payloads['world-reference.bin']
    assert reference[:8] == b'COHWRF09'
    case_stride = 160 + vertices * 52
    assert len(reference) == 640 + POSES * case_stride
    assert struct.unpack_from('<12I', reference, 8) == (1, 64, NODES, POSES, vertices, parts, 64, 352, 640, case_stride, len(reference), 160)
    assert reference[56:64] == bytes(8)
    assert all(math.isfinite(x) for x in struct.unpack_from('<' + 'f' * ((len(reference) - 64) // 4), reference, 64))
    contract = {'world_parts': parts, 'textures': textures, 'vertices': vertices, 'indices': indices,
                'part_vertices': part_vertices, 'part_indices': part_indices, 'part_flags': flags, 'part_material_modes': modes,
                'group_nodes': NODES, 'camera_poses': POSES, 'material_cases': parts * 6,
                'real_material_cases': parts * 4, 'synthetic_material_cases': parts * 2,
                'gpu_components_per_vertex': 13, 'material_clear_pixels': expected_clear_pixels}
    scene = metadata['scene']
    assert scene['container'] == 'COHWOR09' and scene['part_count'] == parts and scene['texture_count'] == textures
    assert scene['canonical_vertices'] == vertices and scene['indices'] == indices
    assert scene['source_vertices'] == 256 and scene['source_root_instances'] == 1
    assert scene['source_group_nodes'] == NODES and scene['source_group_node_per_part'] == 5
    assert scene['static_identity_adapter'] is True and scene['world_coordinates_preserved'] is True
    assert scene['reference_matrices_drive_rendering'] is False
    assert len(metadata['parts']) == parts
    assert [part['mode'] for part in metadata['parts']] == modes == [0, 1]
    assert [part['vertex_count'] for part in metadata['parts']] == part_vertices
    assert [part['triangle_count'] * 3 for part in metadata['parts']] == part_indices
    assert len(metadata['textures']) == textures == 4
    assert vertices == 512 and indices == 564 and parts == 2
    ref = metadata['reference']
    assert ref['container'] == 'COHWRF09' and ref['bytes'] == len(reference)
    assert ref['sha256'] == hashlib.sha256(reference).hexdigest()
    assert ref['reference_cameras'] == POSES and ref['reference_nodes'] == NODES
    assert ref['reference_vertices'] == vertices and ref['reference_parts'] == parts
    assert ref['vertex_output_floats'] == 13 and ref['reference_data_drive_rendering'] is False
    assert ref['source_map_group_locals'] is True and ref['source_ancestor_chain_retained'] is True
    assert ref['gameplay_fov_adjustment_selected'] is False
    mat = metadata['material']
    assert mat['container'] == 'COHWMAT9' and mat['case_count'] == len(mat['cases']) == parts * 6
    assert mat['width'] == mat['height'] == 64 and mat['cases_per_part'] == 6
    assert mat['original_cg_execution'] is False and mat['original_gpu_driver_texture_capture'] is False
    for index, case in enumerate(mat['cases']):
        r = 64 + index * 16512
        assert case['part_index'] == index // 6 and case['case_index'] == index % 6
        assert case['material_mode'] == modes[index // 6] and case['flags'] == expected_flags[index % 6]
        assert case['expected_rgba_sha256'] == hashlib.sha256(material[r + 128:r + 16512]).hexdigest()
        floats = [value for name in ('const0', 'const1', 'vertex_color', 'fog_params', 'fog_color', 'clear') for value in case[name]]
        floats += [case['fog_coord'], case['alpha_ref']]
        assert list(struct.unpack_from('<26f', material, r)) == floats
    return contract, metadata


def validate_source_trick_audit(metadata):
    """Require complete immutable source declaration resolution before execution."""
    assert metadata['source_trick_resolution_qualified'] is True
    audit = metadata['source_trick_resolution_audit']
    assert audit['passed'] is True and audit['kind'] == 'complete immutable original trick declaration audit'
    pins = json.loads((pathlib.Path(__file__).resolve().parents[1] / 'contract/source-material-pins.json').read_text())
    assert audit['git_tree_sha'] == pins['tricks_tree']['git_tree_sha']
    assert audit['source_files_verified'] == pins['tricks_tree']['file_count']
    expected = [{key: identity[key] for key in ('path', 'bytes', 'sha256')}
                for identity in pins['source_files']]
    assert audit['primary_source_files_verified'] == expected
    lookups = audit['direct_and_directory_lookup']
    assert [item['alias'] for item in lookups] == ['Signmetal', 'grey', 'white']
    assert lookups[0]['source_matches'] == lookups[2]['source_matches'] == []
    grey_source = next(pin for pin in pins['source_files'] if pin['path'] == 'upstream/i24/data/tricks/btest.txt')
    assert lookups[1]['source_matches'] == [{
        'lookup_name': 'grey', 'source_path': grey_source['path'], 'source_sha256': grey_source['sha256'],
        'tokens': ['flags truecolor'], 'resolved_texopt_flags': 2,
        'selected_role': 'secondary BasicTexture in Signmetal generic layer',
        'changes_composite_shader_family': False, 'clamp_s': False, 'clamp_t': False,
        'mirror_s': False, 'mirror_t': False, 'point_sample': False, 'no_mip': False,
        'qualified_mip': 0, 'qualified_rgba': [128, 128, 128, 255]}]
    assert lookups[0]['default_generic'] == 'grey'
    assert audit['modern_bench_tokens'] == ['surface metal', 'blend white.tga', 'blendtype colorblenddual']
    assert audit['mbench_tokens'] == ['lodfar 250', 'lodfarfade 75']
    assert audit['full_original_texopt_parser_executed'] is False
    assert audit['original_atlas_lighting_executed'] is False


def validate_assets(report, apk, metadata=None):
    """Compare Java-observed hashes and all metadata with installed APK bytes."""
    verified = report['fixture']['verified_assets']
    assert set(verified) == REQUIRED_ASSETS
    with zipfile.ZipFile(apk) as bundle:
        if metadata is None:
            metadata = json.loads(bundle.read('assets/world-fixture.json'))
        for name in sorted(REQUIRED_ASSETS):
            payload = bundle.read('assets/' + name)
            identity = {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
            assert verified[name] == identity, name
            assert metadata['assets'][name]['bytes'] == identity['bytes'], name
            assert metadata['assets'][name]['sha256'] == identity['sha256'], name
    assert report['fixture']['verified_total_bytes'] == sum(item['bytes'] for item in verified.values())
    validate_source_trick_audit(metadata)
    for key, value in metadata.items():
        assert report['fixture'][key] == value, key


def finite_error(value, tolerance):
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    assert math.isfinite(value) and 0 <= value <= tolerance, value


def background_callbacks_complete(report):
    events = report.get('events', [])
    pauses = [i for i, event in enumerate(events) if event['event'] == 'activity_paused']
    if not pauses:
        return False
    pause = pauses[-1]
    tail = [event['event'] for event in events[pause + 1:]]
    return 'activity_stopped' in tail and 'surface_destroyed' in tail and 'activity_resumed' not in tail


def validate_background_receipt(report):
    q = report['qualification']
    assert report['background_return_passed'] is q['background_return_passed'] is True
    receipt = q['background_return']
    assert receipt['passed'] is True and receipt['session_id'] == report['session_id']
    events = report['events']
    by_serial = {event['serial']: event for event in events}
    expected_names = {'pause': 'activity_paused', 'stop': 'activity_stopped',
                      'surface_destroyed': 'surface_destroyed', 'resume': 'activity_resumed',
                      'surface_created': 'surface_created', 'probe_completed': 'probe_completed'}
    for key, name in expected_names.items():
        observed = receipt[key]
        assert observed['event'] == name and by_serial[observed['serial']] == observed
    pause, stop, destroy, resume, create, complete = (receipt[name] for name in expected_names)
    assert pause['serial'] < min(stop['serial'], destroy['serial'])
    assert max(stop['serial'], destroy['serial']) < resume['serial'] < create['serial'] < complete['serial']
    assert receipt['paused_generation'] == pause['generation'] < receipt['returned_generation']
    assert receipt['returned_generation'] == create['generation'] == complete['generation']
    assert complete['details']['passed'] is True and complete['details']['obsolete'] is False
    matching = [run for run in successful_runs(report) if run['request'] == receipt['request']]
    assert len(matching) == 1
    run = matching[0]
    assert run['generation'] == receipt['returned_generation']
    assert run['callback_width'] == receipt['width'] and run['callback_height'] == receipt['height']
    assert complete['details']['request'] == run['request']
    assert all(events[i]['elapsed_ms'] <= events[i + 1]['elapsed_ms'] for i in range(len(events) - 1))
    assert all(events[i]['serial'] < events[i + 1]['serial'] for i in range(len(events) - 1))


def validate(report, contract, minimum_generations=2, full_qualification=True):
    assert report['schema'] == 'coh-native-world-probe-v1'
    assert report['pre_background_checks_passed'] is True
    assert report['qualification_passed'] is report['passed'] is report['overall_passed'] is full_qualification
    assert report['session_failures'] == 0
    assert report['device']['sdk'] == 33 and report['device']['emulator_detected'] is True
    q = report['qualification']
    assert q['passed'] is full_qualification
    assert q['pre_background_checks_passed'] is True
    assert q['failed_runs'] == 0 and q['current_surface_passed'] is True
    if full_qualification:
        assert q['pending_requirements'] == []
        validate_background_receipt(report)
    else:
        assert q['background_return_passed'] is False and len(q['pending_requirements']) == 1
    assert q['successful_surface_generations'] >= minimum_generations
    assert q['successful_actual_dimensions'] >= 2 and q['successful_widths'] >= 2 and q['successful_heights'] >= 2
    runs = successful_runs(report)
    assert len(runs) >= 3 and len({run['generation'] for run in runs}) >= minimum_generations
    assert len({run['callback_width'] for run in runs}) >= 2 and len({run['callback_height'] for run in runs}) >= 2
    assert q['successful_runs'] == len(runs)
    assert q['successful_surface_generations'] == len({run['generation'] for run in runs})
    assert q['successful_actual_dimensions'] == len({(run['callback_width'], run['callback_height']) for run in runs})
    assert q['successful_widths'] == len({run['callback_width'] for run in runs})
    assert q['successful_heights'] == len({run['callback_height'] for run in runs})
    flags = ['passed', 'mesh_valid', 'world_valid', 'group_transform_match', 'camera_match',
             'world_transform_match', 'world_render_match', 'scene_assembly_match', 'camera_preview_passed',
             'material_pixel_match', 'alpha_fog_passed', 'offscreen_passed', 'context_recreation_passed', 'window_pixel_match', 'controlled_depth_cull_clip_passed']
    vertices, parts, materials = contract['vertices'], contract['world_parts'], contract['material_cases']
    counts = {'group_local_components': NODES * 12, 'group_world_components': NODES * 12,
              'camera_view_components': POSES * 12, 'projection_components': POSES * 16, 'modelview_components': POSES * 12}
    for run in runs:
        assert run['session_id'] == report['session_id']
        assert run['java_validation']['required_native_checks'] is True
        assert run['java_validation']['native_context_cycles_match'] is True
        native = run['native']
        assert all(native.get(key) is True for key in flags)
        assert native['surface_width'] == run['callback_width'] > 0 and native['surface_height'] == run['callback_height'] > 0
        assert native['pointer_bytes'] == native['long_bytes'] == 8
        assert native['required_cycles'] == native['attempted_cycles'] == len(native['cycles']) == 2
        assert native['source_mesh_vertices'] == 256
        assert native['world_part_count'] == parts and native['mesh_vertices'] == vertices
        assert native['mesh_indices'] == contract['indices'] and native['unique_textures'] == contract['textures']
        assert native['group_node_count'] == NODES and native['camera_count'] == POSES
        assert native['material_case_count'] == materials
        assert native['world_fbo_width'] == native['world_fbo_height'] == FBO_SIZE
        assert native['transform_absolute_tolerance'] == .0001 and native['rgba_byte_tolerance'] == 2
        assert native['triangle_edge_exclusion_pixels'] == 2
        assert native['world_texture_filter'] == 'GL_LINEAR' and native['material_probe_texture_filter'] == 'GL_NEAREST'
        assert native['mip_policy'] == 'base level only; original mip chain unqualified'
        assert native['reference_matrices_drive_rendering'] is False and native['reference_geometry_drive_rendering'] is False
        assert native['original_cg_execution'] is False and native['window_alpha_compared'] is False
        assert native['front_face'] == 'CW' and native['cull_face'] == 'BACK except source DoubleSided' and native['depth_write'] is True
        assert native['high_quality_materials_qualified'] is False
        assert native['draw_order'] == 'source original material partition order'
        assert native['material_profile'] == 'actual Signmetal MULTIPLY with grey and modern_bench COLORBLEND_DUAL with white'
        assert native['window_image_filter'] == 'GL_NEAREST'
        for c in native['cycles']:
            assert c['passed'] is True and c['completed'] is True and c['context_created'] is True
            assert c['objects_released'] is True and c['swap_passed'] is True
            assert c['gl_errors'] == c['egl_error'] == 0
            assert c['surface_width'] == run['callback_width'] and c['surface_height'] == run['callback_height']
            assert c['transform_vertices'] == vertices * POSES and c['transform_components'] == vertices * POSES * 13
            assert c['transform_mismatches'] == c['world_position_mismatches'] == c['eye_position_mismatches'] == c['normal_mismatches'] == c['clip_mismatches'] == 0
            finite_error(c['max_transform_error'], .0001)
            for key, expected in counts.items():
                assert c[key] == expected, key
            for key in ['group_local', 'group_world', 'camera_view', 'projection', 'modelview']:
                assert c[key + '_mismatches'] == 0
                finite_error(c[key + '_max_error'], .0001)
            assert c['world_poses'] == POSES and c['world_mismatches'] == 0
            finite_error(c['world_max_byte_error'], 2)
            assert c['world_interior_pixels'] >= 64 * POSES
            assert c['world_compared_pixels'] + c['world_edge_excluded_pixels'] == FBO_SIZE * FBO_SIZE * POSES
            assert len(c['world_pose_interior_pixels']) == POSES and all(n >= 64 for n in c['world_pose_interior_pixels'])
            for prefix in ['compared', 'edge_excluded', 'interior']:
                assert len(c['world_pose_' + prefix + '_pixels']) == POSES
                assert sum(c['world_pose_' + prefix + '_pixels']) == c['world_' + prefix + '_pixels']
            assert all(c['world_pose_compared_pixels'][i] + c['world_pose_edge_excluded_pixels'][i] == FBO_SIZE * FBO_SIZE for i in range(POSES))
            assert c['part_transform_vertices'] == [n * POSES for n in contract['part_vertices']]
            assert len(c['part_interior_pixels']) == parts and all(n >= 64 for n in c['part_interior_pixels'])
            assert len(c['part_image_compared_pixels']) == len(c['part_image_mismatches']) == parts
            assert all(n > 0 for n in c['part_image_compared_pixels']) and not any(c['part_image_mismatches'])
            assert c['material_cases'] == materials and c['material_pixels'] == materials * 64 * 64
            assert c['real_material_cases'] == contract['real_material_cases']
            assert c['synthetic_semantic_cases'] == contract['synthetic_material_cases']
            assert c['material_mismatches'] == 0
            finite_error(c['material_max_byte_error'], 2)
            assert c['material_blended_cases'] == parts * 3
            assert c['material_discard_clear_pixels'] == contract['material_clear_pixels'] > 0
            assert c['diagnostic_cases'] == 5 and c['diagnostic_pixels'] == 125 and c['diagnostic_mismatches'] == 0
            assert c['window_samples'] == 49 and c['window_mismatches'] == 0
            assert c['preview_frames'] == 45 and c['distinct_camera_views'] >= 2
            assert c['preview_image_samples'] == 3 and 1 <= c['preview_changed_image_samples'] <= 2
            assert c['preview_pixels_changed_from_first'] >= 64
    names = [event['event'] for event in report['events']]
    assert all(name in names for name in ['resize_requested', 'surface_changed', 'surface_recreation_requested',
                                        'surface_destroyed', 'surface_created', 'auto_smoke_completed'])
def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    apk = OUTPUT / 'CoH-Native-World-Probe-0.1.0-emulator-x86_64.apk'
    contract, metadata = inspect_apk_inputs(apk)
    validate_source_trick_audit(metadata)
    adb('install', '-r', str(apk))
    adb('shell', 'am', 'force-stop', PACKAGE)
    # A new CI session cannot inherit successful runs from an earlier attempt.
    adb('shell', 'pm', 'clear', PACKAGE)
    adb('logcat', '-c')
    try:
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--ez', 'autoSmoke', 'true')
        first = wait_report(lambda report: report.get('pre_background_checks_passed') is True
                            and report.get('auto_smoke_stage') == 3,
                            'Source world, camera, material, resize, and Surface recreation')
        validate(first, contract, full_qualification=False)
        validate_assets(first, apk, metadata)
        (OUTPUT / 'emulator-initial-report.json').write_text(json.dumps(first, indent=2)+'\n')
        session = first['session_id']
        before = max(run['request'] for run in successful_runs(first))
        before_generation = max(run['generation'] for run in successful_runs(first))
        adb('shell', 'input', 'keyevent', 'KEYCODE_HOME')
        paused = wait_report(lambda report: report.get('session_id') == session
                             and report.get('qualification_passed') is False
                             and background_callbacks_complete(report),
                             'Background lifecycle callbacks', seconds=30)
        (OUTPUT / 'emulator-background-report.json').write_text(json.dumps(paused, indent=2)+'\n')
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'run')
        foreground = wait_report(lambda report: report.get('qualification_passed') is True
                                 and report.get('session_id') == session
                                 and any(run['request'] > before and run['generation'] > before_generation
                                         for run in successful_runs(report)),
                                 'Native world/camera rendering on a new Surface after foreground return')
        validate(foreground, contract, minimum_generations=3)
        (OUTPUT / 'emulator-foreground-report.json').write_text(json.dumps(foreground, indent=2)+'\n')
        before = max(run['request'] for run in successful_runs(foreground))
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'resize')
        resized = wait_report(lambda report: report.get('qualification_passed') is True
                              and report.get('session_id') == session
                              and any(run['request'] > before for run in successful_runs(report)),
                              'Second actual Surface resize')
        validate(resized, contract, minimum_generations=3)
        before_generation = max(run['generation'] for run in successful_runs(resized))
        adb('shell', 'am', 'start', '-W', '-n', ACTIVITY, '--es', 'probe_action', 'recreate')
        final = wait_report(lambda report: report.get('qualification_passed') is True
                            and report.get('session_id') == session
                            and any(run['generation'] > before_generation for run in successful_runs(report)),
                            'Second explicit Surface recreation')
        validate(final, contract, minimum_generations=4)
        validate_assets(final, apk, metadata)
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
        summary = {'schema': 1, 'passed': True,
                   'scope': 'Android 13 x86_64 hosted emulator with SwiftShader; not AYN Thor',
                   'verified_fixture_assets': final['fixture']['verified_assets'],
                   'independently_parsed_inputs': contract,
                   'successful_runs': len(successful_runs(final)),
                   'successful_surface_generations': final['qualification']['successful_surface_generations'],
                   'successful_actual_dimensions': final['qualification']['successful_actual_dimensions'],
                   'successful_actual_widths': final['qualification']['successful_widths'],
                   'successful_actual_heights': final['qualification']['successful_heights'],
                   'completed_context_cycles': len(cycles),
                   'gpu_geometry_components_compared': sum(cycle['transform_components'] for cycle in cycles),
                   'world_image_pixels_compared': sum(cycle['world_compared_pixels'] for cycle in cycles),
                   'material_pixels_compared': sum(cycle['material_pixels'] for cycle in cycles),
                   'window_samples_compared': sum(cycle['window_samples'] for cycle in cycles),
                   'presented_camera_frames': sum(cycle['preview_frames'] for cycle in cycles),
                   'original_group_local_components_compared': sum(cycle['group_local_components'] for cycle in cycles),
                   'original_group_world_components_compared': sum(cycle['group_world_components'] for cycle in cycles),
                   'original_camera_view_components_compared': sum(cycle['camera_view_components'] for cycle in cycles),
                   'original_projection_components_compared': sum(cycle['projection_components'] for cycle in cycles),
                   'original_draw_modelview_components_compared': sum(cycle['modelview_components'] for cycle in cycles),
                   'controlled_depth_cull_clip_cases': sum(cycle['diagnostic_cases'] for cycle in cycles),
                   'controlled_depth_cull_clip_pixels': sum(cycle['diagnostic_pixels'] for cycle in cycles),
                   'camera_image_temporal_samples': sum(cycle['preview_image_samples'] for cycle in cycles),
                   'camera_images_changed_from_first': sum(cycle['preview_changed_image_samples'] for cycle in cycles),
                   'camera_pixels_changed_from_first': sum(cycle['preview_pixels_changed_from_first'] for cycle in cycles),
                   'original_cg_execution': False, 'original_game_execution': False,
                   'full_atlas_loaded': False, 'original_lighting_qualified': False,
                   'original_scene_sorter_qualified': False,
                   'actual_resize_verified': True, 'surface_recreation_verified': True,
                   'foreground_return_verified': True,
                   'background_return_receipt': final['qualification']['background_return'],
                   'thor_device_execution_verified': False}
        (OUTPUT / 'emulator-smoke-summary.json').write_text(json.dumps(summary, indent=2)+'\n')
        print(json.dumps(summary))
    finally:
        (OUTPUT / 'emulator-logcat.txt').write_bytes(adb('logcat', '-d', check=False).stdout)
        screenshot = adb('exec-out', 'screencap', '-p', check=False)
        if screenshot.returncode == 0 and screenshot.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
            (OUTPUT / 'emulator-screenshot.png').write_bytes(screenshot.stdout)


if __name__ == '__main__':
    main()
