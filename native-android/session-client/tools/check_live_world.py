#!/usr/bin/env python3
"""Focused archive-backed runtime placement, rollback, eviction and GLES checks.

Offline only: the input description distinguishes retained original ZIP ranges
from generated ZIP format fixtures carrying authentic bodies. Selected retained
bytes are verified before/after; a fixture is never original-archive proof.
Android uses the actual archives verified by its existing importer.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, struct, subprocess, sys
HERE = Path(__file__).resolve().parent; NATIVE = HERE.parents[1]
sys.path.insert(0, str(HERE))
import stream_gpu_check as gpu

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path); result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result
def sha(raw): return hashlib.sha256(raw).hexdigest()
def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=180, **kwargs)
    if result.returncode: raise RuntimeError(' '.join(map(str, command)) + '\n' + result.stdout + result.stderr)
    return result.stdout

def offline_archives(work):
    descriptor = work / 'original-archive-ranges.json'
    result = json.loads(descriptor.read_text())
    for item in result['archives']:
        path = work / item['file']; assert path.stat().st_size == item['bytes']
        with path.open('rb') as source:
            for block in item['ranges']:
                assert 0 <= block['offset'] <= item['bytes'] and 0 < block['bytes'] <= (1 << 20)
                assert block['bytes'] <= item['bytes'] - block['offset']
                source.seek(block['offset']); assert sha(source.read(block['bytes'])) == block['sha256']
    return result

def render_runtime(library, bundle, index, world_bin, live, archives, work):
    """Drive the production stream owner at two poses using the same disk index."""
    F, U, Q, Z, V3, M4 = gpu.F, gpu.U, gpu.Q, gpu.Z, gpu.V3, gpu.M4
    ReadAt = C.CFUNCTYPE(C.c_int, C.c_void_p, Q, C.c_void_p, Z)
    class AssetSource(C.Structure): _fields_ = [('read_at', ReadAt), ('context', C.c_void_p), ('size', Q), ('generation', U)]
    class Sources(C.Structure): _fields_ = [('placements', AssetSource), ('atlas_zip', AssetSource), ('client_zip', AssetSource), ('parent_retained_bytes', Q)]
    retained = []; reads = [0]
    def source(path):
        stream = path.open('rb')
        @ReadAt
        def read(context, offset, dst, count):
            try:
                stream.seek(offset); raw = stream.read(count)
                if len(raw) != count: return 1
                C.memmove(dst, raw, count); reads[0] += count; return 0
            except OSError: return 1
        retained.append((stream, read)); return AssetSource(read, None, path.stat().st_size, 1)
    sources = Sources(source(index), source(archives / 'atlas.sparse.zip'), source(archives / 'client.sparse.zip'), 64 << 20)
    e = gpu.EGL(); g = e.g; lib = C.CDLL(str(library)); world = C.c_void_p(); stats = gpu.WorldStats(); error = C.create_string_buffer(1024)
    lib.coh_session_world_create_archives.argtypes = [C.c_void_p, Z, C.POINTER(Sources), C.POINTER(C.c_void_p), C.c_void_p, Z]
    lib.coh_session_world_parent_bytes.argtypes = [C.c_void_p, Q, C.c_void_p, Z]
    lib.coh_session_world_owned_bytes.argtypes = [C.c_void_p, C.POINTER(Q), C.POINTER(Q)]
    lib.coh_session_world_destroy.argtypes = [C.POINTER(C.c_void_p)]
    lib.coh_session_world_surface_lost.argtypes = [C.c_void_p, C.c_int, C.POINTER(gpu.WorldStats)]
    for name in ('coh_session_world_surface', 'coh_session_world_draw_observed'):
        getattr(lib, name).argtypes = [C.c_void_p, C.POINTER(F), C.POINTER(F), C.POINTER(F), F, C.POINTER(gpu.WorldStats), C.c_void_p, Z]
    lib.coh_world_parse_inputs.argtypes = [C.c_void_p, Z, C.POINTER(gpu.CameraInputs)]
    lib.coh_world_camera.argtypes = [C.POINTER(gpu.CameraInputs), U, F, C.POINTER(F), C.POINTER(F)]
    lib.coh_stream_test_asset_stats.argtypes = [C.c_void_p]; lib.coh_stream_test_asset_stats.restype = gpu.AssetStats
    lib.coh_stream_test_bridge_stats.argtypes = [C.c_void_p]; lib.coh_stream_test_bridge_stats.restype = gpu.BridgeStats
    # Erase only the three embedded body copies in this scratch test descriptor.
    # Successful drawing must therefore read the original archive members.
    raw = bytearray(bundle.read_bytes()); entries = struct.unpack_from('<I', raw, 32)[0]
    for i in range(8, 11):
        offset, size = struct.unpack_from('<2I', raw, entries + i * 24 + 8); raw[offset:offset + size] = bytes(size)
    data = C.create_string_buffer(bytes(raw)); camera_data = world_bin.read_bytes(); offset = struct.unpack_from('<I', camera_data, 48)[0]
    inputs = gpu.CameraInputs(); raw_inputs = C.create_string_buffer(camera_data[offset:offset + 520])
    assert lib.coh_world_parse_inputs(raw_inputs, 520, C.byref(inputs)) == 0
    view = (F * 12)(); projection = M4(); camera = inputs.cameras[0]
    def aim(pose):
        import math
        pitch = gpu.f32(.16); camera.position = V3(pose[0], gpu.f32(pose[1] + 3.8 + 22 * math.sin(pitch)), gpu.f32(pose[2] + 22 * math.cos(pitch)))
        camera.pyr_degrees = V3(gpu.f32(pitch * 180 / math.pi), 0, 0)
        assert lib.coh_world_camera(C.byref(inputs), 0, 1, view, projection) == 0
    texture = e.texture(256, 256); fbo = U(); g.glGenFramebuffers(1, C.byref(fbo)); g.glBindFramebuffer(0x8d40, fbo); g.glFramebufferTexture2D(0x8d40, 0x8ce0, 0xde1, texture, 0)
    assert g.glCheckFramebufferStatus(0x8d40) == 0x8cd5
    expected_errors = [0]
    def invoke(name, pose):
        aim(pose)
        assert getattr(lib, name)(world, view, projection, V3(*pose), 24, C.byref(stats), error, len(error)), error.value.decode()
        assert stats.resident_bytes <= 512 << 10 and stats.errors == expected_errors[0] and stats.tf_mismatches == 0
    def pixels():
        rgba = (C.c_ubyte * (256 * 256 * 4))(); g.glReadPixels(0, 0, 256, 256, 0x1908, 0x1401, rgba); assert g.glGetError() == 0
        return bytes(rgba)
    def draw(pose):
        g.glBindFramebuffer(0x8d40, fbo); g.glViewport(0, 0, 256, 256); g.glClearColor(17 / 255, 19 / 255, 23 / 255, 1); g.glClear(0x4000)
        invoke('coh_session_world_draw_observed', pose); raw = pixels()
        visible = sum(any(abs(raw[i + j] - c) > 3 for j, c in enumerate((17, 19, 23))) for i in range(0, len(raw), 4))
        return visible, raw
    try:
        before = reads[0]; sources.parent_retained_bytes = 96 << 20
        assert not lib.coh_session_world_create_archives(data, len(raw), C.byref(sources), C.byref(world), error, len(error)) and not world.value and reads[0] == before
        sources.parent_retained_bytes = 64 << 20
        assert lib.coh_session_world_create_archives(data, len(raw), C.byref(sources), C.byref(world), error, len(error)), error.value.decode()
        invoke('coh_session_world_surface', [582.5, 74, -1380]); assert stats.selected_instances == 6
        first = [131.453125, .25, -114.953125]; visible_first, _ = draw(first); assert stats.selected_instances == 2 and visible_first > 64
        # Same original local sidewalk point, placed at another source occurrence.
        rows = live['instances']; original = rows[8]['world']; target = rows[0]['world']; relative = [first[i] - original[9 + i] for i in range(3)]
        local = [sum(original[j * 3 + i] * relative[i] for i in range(3)) for j in range(3)]
        second = [sum(target[j * 3 + i] * local[j] for j in range(3)) + target[9 + i] for i in range(3)]
        visible_second, image = draw(second); second_count = stats.selected_instances; assert second_count > 0 and visible_second > 64
        stationary_reads = reads[0]
        for _ in range(32): draw(second)
        assert reads[0] == stationary_reads, 'Stationary frames performed archive/index I/O'
        from PIL import Image
        Image.frombytes('RGBA', (256, 256), image).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(work / 'runtime-second-pose.png')
        cpu, gpu_bytes = Q(), Q(); assert lib.coh_session_world_owned_bytes(world, C.byref(cpu), C.byref(gpu_bytes)); owned = {'cpu': cpu.value, 'gpu_payload': gpu_bytes.value}
        limit = (96 << 20) - (15 << 20) - 65536
        assert lib.coh_session_world_parent_bytes(world, limit, error, len(error))
        assert not lib.coh_session_world_parent_bytes(world, limit + 1, error, len(error))
        expected_errors[0] += 1
        # A failed parent update preserves the previously valid parent charge.
        visible_second, _ = draw(second); assert visible_second > 64
        before = reads[0]; empty_pixels, _ = draw([5000, 0, 5000]); assert stats.selected_instances == 0 and stats.resident_bytes == 0 and empty_pixels == 0
        assert gpu.values(lib.coh_stream_test_bridge_stats(world))['meshes'] == 0
        assert lib.coh_session_world_owned_bytes(world, C.byref(cpu), C.byref(gpu_bytes)) and gpu_bytes.value == stats.gpu_bytes
        visible_revisit, _ = draw(second); assert visible_revisit > 64 and reads[0] > before and stats.selected_instances == second_count
        for _ in range(16): draw(first); draw(second)
        return {'passed': True, 'scope': 'Actual host Mesa GLES, not Thor; same index reused at changed pose', 'first_pose': first, 'first_pose_visible_pixels': visible_first, 'second_pose': second, 'second_pose_instances': second_count, 'second_pose_visible_pixels': visible_second, 'stationary_32_frames_no_io': True, 'empty_window_evicted_raw_meshes_textures': True, 'revisit_archive_reload': True, 'owned_scene': owned, 'peak_resident_bytes': stats.peak_resident_bytes, 'gl_errors': 0, 'source_reads_bytes': reads[0], 'identity': e.identity}
    finally:
        if world: lib.coh_session_world_surface_lost(world, 1, C.byref(stats)); lib.coh_session_world_destroy(C.byref(world)); assert not world.value
        g.glDeleteFramebuffers(1, C.byref(fbo)); g.glDeleteTextures(1, C.byref(texture)); e.close()
        for stream, callback in retained: stream.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True); parser.add_argument('--metadata', type=Path, required=True); parser.add_argument('--live-assets', type=Path, required=True); parser.add_argument('--live-metadata', type=Path, required=True)
    parser.add_argument('--archives', type=Path, required=True); parser.add_argument('--world-bin', type=Path, required=True); parser.add_argument('--source-root', type=Path, required=True); parser.add_argument('--gles-headers', type=Path, required=True); parser.add_argument('--work', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args(); a.work.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(a.metadata.read_text()); live = json.loads(a.live_metadata.read_text())
    assert live['source_files'] == metadata['source_files']
    for pin in live['source_files']:
        source = a.source_root / pin['path']; assert source.stat().st_size == pin['bytes'] and sha(source.read_bytes()) == pin['sha256']
    bundle = a.assets / 'neighborhood-map.bin'; index = a.live_assets / 'live-world.bin'
    for path, pin in [(bundle, metadata['assets']['neighborhood-map.bin']), (index, live['assets']['live-world.bin'])]: assert path.stat().st_size == pin['bytes'] and sha(path.read_bytes()) == pin['sha256']
    archive_dir = a.archives; transport = offline_archives(archive_dir)
    core = [NATIVE / path for path in ['engine/world/coh_world_stream.c', 'engine/world/coh_world_live.c', 'engine/assets/coh_asset_zip.c', 'engine/bridge/coh_asset_render.c', 'engine/assets/coh_asset_loader.c', 'engine/assets/coh_asset_geo.c', 'engine/renderer/coh_renderer.c', 'src/coh_assets.c', 'src/coh_dds.c']]
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-ffp-contract=off', '-I', NATIVE / 'include']
    modes = {}
    for mode, extra in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address', '-no-pie']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        output = a.work / mode; output.mkdir(exist_ok=True); executable = output / 'test'
        run(['cc', *flags, *extra, NATIVE / 'engine/world/test_live_world.c', *core, '-lz', '-lm', '-o', executable])
        run([executable, bundle, index, archive_dir / 'atlas.sparse.zip', archive_dir / 'client.sparse.zip', output, output / 'result.json', transport['archives'][0]['members'][live['inputs'][0]['path']]['data_offset']], env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1'})
        for i, item in enumerate(live['inputs']): assert sha((output / (str(i) + '.body')).read_bytes()) == item['sha256']
        modes[mode] = json.loads((output / 'result.json').read_text())
    includes = a.work / 'include'; includes.mkdir(exist_ok=True)
    for sub in ('GLES3', 'KHR'):
        link = includes / sub
        if not link.exists(): link.symlink_to((a.gles_headers / sub).resolve(), target_is_directory=True)
    camera = a.work / 'camera.o'; run(['cc', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-I', NATIVE / 'include', '-c', NATIVE / 'world/coh_world.c', '-o', camera])
    library = a.work / 'runtime-stream.so'
    source = [NATIVE / n for n in ['session-client/tools/stream_gpu_fixture.c', 'session-client/app/src/main/cpp/session_stream_qualify.c', 'engine/renderer/coh_debug_entity.c', 'engine/renderer/coh_renderer_gles.c']]
    run(['cc', *flags, '-O2', '-fPIC', '-shared', '-I', includes, '-I', NATIVE / 'engine/assets', '-I', NATIVE / 'engine/world', '-I', NATIVE / 'engine/bridge', '-I', NATIVE / 'engine/renderer', *source, *core, camera, '-l:libGL.so.1', '-lz', '-lm', '-o', library])
    result = {'passed': True, 'transport': transport, 'modes': modes, 'gpu': render_runtime(library, bundle, index, a.world_bin, live, archive_dir, a.work), 'live_index': live['assets'], 'scope': 'Native runtime source path; APK archive FD/import wiring follows separately'}
    assert offline_archives(archive_dir) == transport
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': modes, 'gpu': result['gpu'], 'transport_bytes': transport.get('network_range_bytes')}, indent=2))
if __name__ == '__main__': main()
