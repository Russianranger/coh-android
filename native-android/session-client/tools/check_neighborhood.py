#!/usr/bin/env python3
"""Exercise the real near-pose source subset, ownership and GLES drawing path."""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, math, os, struct, subprocess, sys, tempfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]
sys.path.insert(0, str(HERE))
import stream_gpu_check as gpu
F, U, Z, Q, V3, M4, Draw = gpu.F, gpu.U, gpu.Z, gpu.Q, gpu.V3, gpu.M4, gpu.Draw

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result

def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=180, **kwargs)
    if result.returncode:
        raise RuntimeError(' '.join(map(str, command)) + '\n' + result.stdout + result.stderr)
    return result.stdout

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def original_packet(raw, source_root, work):
    legacy = module('neighborhood_legacy', NATIVE / 'tools/walkable_fixture/prepare.py')
    original = module('neighborhood_original', NATIVE / 'tools/material_fixture/original_delta_check.py')
    code = original.original_c(source_root / 'upstream/ouroboros/Common/seq/anim.c')
    (work / 'original.c').write_bytes(code)
    run(['cc', '-std=c99', '-O0', '-fno-strict-aliasing', '-shared', '-fPIC', work / 'original.c', '-o', work / 'original.so'])
    lib = C.CDLL(str(work / 'original.so'))
    lib.uncompressDeltas.argtypes = [C.c_void_p, C.c_void_p, C.c_int, C.c_int, C.c_int]
    data, models = legacy.legacy_records(raw)
    model = next(m for m in models if m['name'] == '_4_strt_hi__roadhi')
    decoded = []
    for stream, count, stride, integer in [(0, model['triangle_count'], 3, True), (1, model['vertex_count'], 3, False), (2, model['vertex_count'], 3, False), (3, model['vertex_count'], 2, False)]:
        payload = legacy.stream(data, model, stream)
        source, out = C.create_string_buffer(payload + bytes(16)), C.create_string_buffer(count * stride * 4)
        assert lib.uncompressDeltas(out, source, stride, count, int(integer)) == len(payload)
        decoded.append(struct.unpack('<' + ('I' if integer else 'f') * (count * stride), out.raw))
    packet = bytearray()
    for i in range(model['vertex_count']):
        u, v = decoded[3][i * 2:i * 2 + 2]; v = gpu.f32(1 - v)
        packet += struct.pack('<14f', *decoded[1][i * 3:i * 3 + 3], *decoded[2][i * 3:i * 3 + 3], gpu.f32(u * 5), gpu.f32(v * 5), u, v, 1, 1, 1, 1)
    first = model['materials'][0]
    assert first['name'] == 'street_sidewalk1.tga' and first['triangle_count'] == 12
    packet += struct.pack('<36I', *decoded[0][:36])
    return bytes(packet)

def render(library, bundle, world_bin, work):
    e = gpu.EGL(); g = e.g; lib = C.CDLL(str(library)); world = C.c_void_p()
    stats = gpu.WorldStats(); error = C.create_string_buffer(1024); data = C.create_string_buffer(bundle)
    for name, result, args in [('glGenRenderbuffers', None, [C.c_int, C.POINTER(U)]), ('glDeleteRenderbuffers', None, [C.c_int, C.POINTER(U)]), ('glBindRenderbuffer', None, [U, U]), ('glRenderbufferStorage', None, [U, U, C.c_int, C.c_int]), ('glFramebufferRenderbuffer', None, [U, U, U, U])]:
        e.gf(name, result, args)
    lib.coh_session_world_create.argtypes = [C.c_void_p, Z, C.POINTER(C.c_void_p), C.c_void_p, Z]
    lib.coh_session_world_destroy.argtypes = [C.POINTER(C.c_void_p)]
    lib.coh_session_world_owned_bytes.argtypes = [C.c_void_p, C.POINTER(Q), C.POINTER(Q)]
    for name in ('coh_session_world_surface', 'coh_session_world_draw_observed'):
        getattr(lib, name).argtypes = [C.c_void_p, C.POINTER(F), C.POINTER(F), C.POINTER(F), F, C.POINTER(gpu.WorldStats), C.c_void_p, Z]
    lib.coh_session_world_observed_entity.argtypes = [C.c_void_p, C.POINTER(F), C.POINTER(F), U, C.POINTER(F), C.POINTER(gpu.WorldStats), C.c_void_p, Z]
    lib.coh_session_world_surface_lost.argtypes = [C.c_void_p, C.c_int, C.POINTER(gpu.WorldStats)]
    lib.coh_world_parse_inputs.argtypes = [C.c_void_p, Z, C.POINTER(gpu.CameraInputs)]
    lib.coh_world_camera.argtypes = [C.POINTER(gpu.CameraInputs), U, F, C.POINTER(F), C.POINTER(F)]
    lib.coh_stream_test_bridge_stats.argtypes = [C.c_void_p]; lib.coh_stream_test_bridge_stats.restype = gpu.BridgeStats
    lib.coh_stream_test_asset_stats.argtypes = [C.c_void_p]; lib.coh_stream_test_asset_stats.restype = gpu.AssetStats
    source = world_bin.read_bytes(); offset = struct.unpack_from('<I', source, 48)[0]
    inputs = gpu.CameraInputs(); raw_inputs = C.create_string_buffer(source[offset:offset + 520])
    assert lib.coh_world_parse_inputs(raw_inputs, 520, C.byref(inputs)) == 0
    pose = V3(131.453125, .25, -114.953125); view = (F * 12)(); projection = M4()
    camera = inputs.cameras[0]; pitch = gpu.f32(.16); distance = 22.
    camera.position = V3(pose[0], gpu.f32(pose[1] + 3.8 + distance * math.sin(pitch)), gpu.f32(pose[2] + distance * math.cos(pitch)))
    camera.pyr_degrees = V3(gpu.f32(pitch * 180 / math.pi), 0, 0)
    assert lib.coh_world_camera(C.byref(inputs), 0, 1, view, projection) == 0
    frame = []
    def target():
        texture = e.texture(256, 256); fbo, depth = U(), U()
        g.glGenFramebuffers(1, C.byref(fbo)); g.glBindFramebuffer(0x8d40, fbo)
        g.glFramebufferTexture2D(0x8d40, 0x8ce0, 0xde1, texture, 0)
        g.glGenRenderbuffers(1, C.byref(depth)); g.glBindRenderbuffer(0x8d41, depth)
        g.glRenderbufferStorage(0x8d41, 0x81a6, 256, 256); g.glFramebufferRenderbuffer(0x8d40, 0x8d00, 0x8d41, depth)
        assert g.glCheckFramebufferStatus(0x8d40) == 0x8cd5
        frame[:] = [texture, fbo, depth]
    def invoke(name):
        assert getattr(lib, name)(world, view, projection, pose, 24, C.byref(stats), error, len(error)), error.value.decode()
        assert stats.selected_instances > 0 and stats.tf_mismatches == stats.errors == 0
        assert stats.resident_bytes <= stats.budget_bytes == 512 * 1024
    def read():
        pixels = (C.c_ubyte * (256 * 256 * 4))(); g.glReadPixels(0, 0, 256, 256, 0x1908, 0x1401, pixels)
        assert g.glGetError() == 0
        return bytes(pixels)
    try:
        target(); assert lib.coh_session_world_create(data, len(bundle), C.byref(world), error, len(error)), error.value.decode()
        invoke('coh_session_world_surface')
        g.glBindFramebuffer(0x8d40, frame[1]); g.glViewport(0, 0, 256, 256)
        g.glClearColor(17 / 255, 19 / 255, 23 / 255, 1); g.glClear(0x4000 | 0x100)
        invoke('coh_session_world_draw_observed'); floor = read()
        visible = sum(any(abs(floor[i + j] - c) > 3 for j, c in enumerate((17, 19, 23))) for i in range(0, len(floor), 4))
        assert visible > 64, visible
        assert lib.coh_session_world_observed_entity(world, view, projection, 125, pose, C.byref(stats), error, len(error)), error.value.decode()
        combined = read(); changed = sum(floor[i:i + 4] != combined[i:i + 4] for i in range(0, len(floor), 4)); assert changed > 4, changed
        from PIL import Image
        Image.frombytes('RGBA', (256, 256), combined).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(work / 'world-and-box.png')
        cpu, gpu_bytes = Q(), Q()
        assert not lib.coh_session_world_owned_bytes(None, C.byref(cpu), C.byref(gpu_bytes))
        assert not lib.coh_session_world_owned_bytes(world, C.byref(cpu), C.byref(cpu))
        assert lib.coh_session_world_owned_bytes(world, C.byref(cpu), C.byref(gpu_bytes))
        assert cpu.value > stats.owned_cpu_bytes and gpu_bytes.value == stats.gpu_bytes + 1310720
        concrete = {'owned_cpu_bytes': cpu.value, 'owned_gpu_payload_bytes': gpu_bytes.value, 'borrowed_bundle_bytes_counted_by_parent': len(bundle)}
        baseline = gpu.values(lib.coh_stream_test_bridge_stats(world))
        for _ in range(32): invoke('coh_session_world_draw_observed')
        after = gpu.values(lib.coh_stream_test_bridge_stats(world)); assert after == baseline
        lib.coh_session_world_surface_lost(world, 0, C.byref(stats))
        assert lib.coh_session_world_owned_bytes(world, C.byref(cpu), C.byref(gpu_bytes)) and gpu_bytes.value == 0
        assert cpu.value < concrete['owned_cpu_bytes']
        e.recreate_context(); target(); invoke('coh_session_world_surface')
        recreated = gpu.values(lib.coh_stream_test_bridge_stats(world)); assert recreated['allocated_bytes'] == baseline['allocated_bytes'] and recreated['mesh_loads'] == baseline['mesh_loads']
        return {'passed': True, 'scope': 'actual Mesa host GLES, not Thor', 'identity': e.identity, 'selected_instances': stats.selected_instances, 'world_draw_packets': stats.draw_packets, 'visible_world_pixels': visible, 'box_changed_pixels': changed, 'gl_errors': 0, 'context_recreate': True, 'unchanged_cpu_owner_over_32_draws': True, 'asset_owner': gpu.values(lib.coh_stream_test_asset_stats(world)), 'bridge_owner': recreated, 'gpu_buffer_bytes': stats.gpu_bytes, 'concrete_owner': concrete, 'image': str(work / 'world-and-box.png')}
    finally:
        if world:
            lib.coh_session_world_surface_lost(world, 1, C.byref(stats)); lib.coh_session_world_destroy(C.byref(world)); assert not world.value
        if frame:
            g.glDeleteFramebuffers(1, C.byref(frame[1])); g.glDeleteTextures(1, C.byref(frame[0])); g.glDeleteRenderbuffers(1, C.byref(frame[2]))
        e.close()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assets', type=Path, required=True); p.add_argument('--metadata', type=Path, required=True)
    p.add_argument('--world-bin', type=Path, required=True); p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--gles-headers', type=Path, required=True); p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args(); a.work.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(a.metadata.read_text()); bundle_path = a.assets / 'neighborhood-map.bin'; bundle = bundle_path.read_bytes()
    assert len(bundle) == metadata['assets']['neighborhood-map.bin']['bytes'] and sha(bundle_path) == metadata['assets']['neighborhood-map.bin']['sha256']
    rows, strings = struct.unpack_from('<I', bundle, 32)[0], struct.unpack_from('<I', bundle, 36)[0]
    road = None
    for i in range(struct.unpack_from('<I', bundle, 28)[0]):
        name, _, offset, size, _, _ = struct.unpack_from('<6I', bundle, rows + i * 24)
        path = bundle[strings + name:bundle.index(0, strings + name)].decode()
        if path.endswith('/road_4lane.geo'): road = bundle[offset:offset + size]
    assert road is not None
    expected = original_packet(road, a.source_root, a.work)
    core = [NATIVE / n for n in ['engine/world/coh_world_live.c', 'engine/assets/coh_asset_zip.c', 'engine/world/coh_world_stream.c', 'engine/bridge/coh_asset_render.c', 'engine/assets/coh_asset_loader.c', 'engine/assets/coh_asset_geo.c', 'engine/renderer/coh_renderer.c', 'src/coh_assets.c', 'src/coh_dds.c']]
    flags = ['-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-ffp-contract=off', '-I', NATIVE / 'include']
    modes = {}
    for mode, extra in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address', '-no-pie']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        binary, packet = a.work / mode, a.work / (mode + '.packet')
        run(['cc', *flags, *extra, NATIVE / 'engine/world/test_neighborhood.c', *core, '-lz', '-lm', '-o', binary])
        modes[mode] = json.loads(run([binary, bundle_path, packet], env={**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1'}))
        assert packet.read_bytes() == expected, mode + ' differs from unchanged original delta consumer'
    includes = a.work / 'include'; includes.mkdir(exist_ok=True)
    for sub in ('GLES3', 'KHR'):
        link = includes / sub
        if not link.exists(): link.symlink_to((a.gles_headers / sub).resolve(), target_is_directory=True)
    camera = a.work / 'camera.o'; run(['cc', '-std=c11', '-O2', '-fPIC', '-ffp-contract=off', '-I', NATIVE / 'include', '-c', NATIVE / 'world/coh_world.c', '-o', camera])
    library = a.work / 'stream.so'
    source = [NATIVE / n for n in ['session-client/tools/stream_gpu_fixture.c', 'session-client/app/src/main/cpp/session_stream_qualify.c', 'engine/renderer/coh_debug_entity.c', 'engine/renderer/coh_renderer_gles.c']]
    run(['cc', *flags, '-O2', '-fPIC', '-shared', '-I', includes, '-I', NATIVE / 'engine/assets', '-I', NATIVE / 'engine/world', '-I', NATIVE / 'engine/bridge', '-I', NATIVE / 'engine/renderer', *source, *core, camera, '-l:libGL.so.1', '-lz', '-lm', '-o', library])
    result = {'passed': True, 'modes': modes, 'original_source_packet_sha256': hashlib.sha256(expected).hexdigest(), 'gpu': render(library, bundle, a.world_bin, a.work), 'source_sha256': {str(x.relative_to(NATIVE)): sha(x) for x in [*core, *source, Path(__file__), NATIVE / 'engine/world/test_neighborhood.c', NATIVE / 'session-client/app/src/main/cpp/session_stream_world.c']}}
    a.output.parent.mkdir(parents=True, exist_ok=True); a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'source_sha256'}, indent=2))

if __name__ == '__main__': main()
