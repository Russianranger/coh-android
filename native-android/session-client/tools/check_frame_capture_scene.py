#!/usr/bin/env python3
"""Capture source neighborhood and observed-pose box on Mesa, never Thor/Android.

Run after check_neighborhood.py. Reuses its just-built production stream DSO,
then executes the shipped capture owner/readback/publication and Java ZIP writer.
The Android Session render loop, actual EGL window swap and live packet receipt
are separate coverage; this test uses the retained real-pose regression sample.
Serialize externally with flock /tmp/coh-next-build.lock.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, json, math, struct, subprocess, sys, zipfile
HERE = Path(__file__).resolve().parent
CPP = HERE.parent / 'app/src/main/cpp'
NATIVE = HERE.parents[1]
sys.path.insert(0, str(HERE))
import stream_gpu_check as gpu
F, U, Q, Z, V3, M4 = gpu.F, gpu.U, gpu.Q, gpu.Z, gpu.V3, gpu.M4


def run(command):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stdout[-2000:] + result.stderr[-4000:])
    return result.stdout


def pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class Info(C.Structure):
    _fields_ = [(n, U) for n in ('viewport_width', 'viewport_height', 'entity_index')] + [
        (n, Q) for n in ('frame', 'epoch', 'pose_generation', 'pose_lock_frame',
                        'world_packets', 'entity_draws', 'base_charge')] + [('pose', V3)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('stream-library', 'assets', 'world-bin', 'gles-headers', 'work', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--fullscreen',action='store_true')
    a = p.parse_args(); a.work.mkdir(parents=True, exist_ok=False)
    bundle = (a.assets / 'neighborhood-map.bin').read_bytes()
    assert pin(bundle) == {'bytes': 491565, 'sha256': 'fcd3a97f8a84165316c6784016d1ab38402602fdfadeca1ed31fb3329426a1a7'}
    vw,vh,cw,ch=(1280,720,640,360)if a.fullscreen else(256,256,108,108)
    library = a.work / 'capture.so'
    # Host libc remains authoritative; do not import Bionic standard headers.
    includes = a.work / 'include'; includes.mkdir()
    for sub in ('GLES3', 'KHR'):
        (includes / sub).symlink_to((a.gles_headers / sub).resolve(), target_is_directory=True)
    sources = [CPP / 'session_frame_capture.c', CPP / 'session_frame_capture.h',
               CPP / 'session_frame_capture_gl.c', CPP / 'session_frame_capture_gl.h',
               CPP / 'session_renderer.c']
    pins = {str(x): pin(x.read_bytes()) for x in sources}
    run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O2',
         '-shared', '-fPIC', *(['-DCOH_FULLSCREEN_DIAGNOSTIC=1']if a.fullscreen else []),'-I', includes, sources[0], sources[2],
         '-l:libGL.so.1', '-lm', '-o', library])
    cap, lib = C.CDLL(str(library)), C.CDLL(str(a.stream_library))
    cap.coh_frame_capture_create.argtypes = [Q]; cap.coh_frame_capture_create.restype = C.c_void_p
    cap.coh_frame_capture_begin.argtypes = [C.c_void_p, C.POINTER(Info), C.POINTER(C.c_void_p), C.POINTER(U), C.POINTER(U)]
    cap.coh_frame_capture_readback.argtypes = [U, U, U, U, C.c_void_p]
    cap.coh_frame_capture_publish.argtypes = [C.c_void_p, C.c_int]
    cap.coh_frame_capture_data.argtypes = [C.c_void_p, C.POINTER(Z), Q]; cap.coh_frame_capture_data.restype = C.c_void_p
    cap.coh_frame_capture_reserve_bytes.restype=U
    cap.coh_frame_capture_destroy.argtypes = [C.POINTER(C.c_void_p)]
    lib.coh_session_world_create.argtypes = [C.c_void_p, Z, C.POINTER(C.c_void_p), C.c_void_p, Z]
    lib.coh_session_world_destroy.argtypes = [C.POINTER(C.c_void_p)]
    for name in ('coh_session_world_surface', 'coh_session_world_draw_observed'):
        getattr(lib, name).argtypes = [C.c_void_p, C.POINTER(F), C.POINTER(F), C.POINTER(F), F, C.POINTER(gpu.WorldStats), C.c_void_p, Z]
    lib.coh_session_world_observed_entity.argtypes = [C.c_void_p, C.POINTER(F), C.POINTER(F), U, C.POINTER(F), C.POINTER(gpu.WorldStats), C.c_void_p, Z]
    lib.coh_session_world_surface_lost.argtypes = [C.c_void_p, C.c_int, C.POINTER(gpu.WorldStats)]
    lib.coh_session_world_owned_bytes.argtypes = [C.c_void_p, C.POINTER(Q), C.POINTER(Q)]
    lib.coh_world_parse_inputs.argtypes = [C.c_void_p, Z, C.POINTER(gpu.CameraInputs)]
    lib.coh_world_camera.argtypes = [C.POINTER(gpu.CameraInputs), U, F, C.POINTER(F), C.POINTER(F)]
    e = gpu.EGL(); g = e.g
    # Select a real depth24 pbuffer. All rendering still uses the default FBO,
    # matching the gameSurface target read by the shipped capture helper.
    config, count = C.c_void_p(), C.c_int()
    attrs = (C.c_int * 17)(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8,
                           0x3022, 8, 0x3021, 8, 0x3025, 24, 0x3038, 0, 0)
    assert e.e.eglChooseConfig(e.display, attrs, C.byref(config), 1, C.byref(count)) and count.value
    e.config = config; e.recreate_context()
    e.ef('eglCreatePbufferSurface', C.c_void_p, [C.c_void_p, C.c_void_p, C.POINTER(C.c_int)])
    e.ef('eglDestroySurface', U, [C.c_void_p, C.c_void_p])
    e.ef('eglSwapBuffers', U, [C.c_void_p, C.c_void_p])
    surface = e.e.eglCreatePbufferSurface(e.display, config, (C.c_int * 5)(0x3057, vw, 0x3056, vh, 0x3038)); assert surface
    assert e.e.eglMakeCurrent(e.display, surface, surface, e.context)
    world, owner = C.c_void_p(), C.c_void_p()
    stats, error, data = gpu.WorldStats(), C.create_string_buffer(1024), C.create_string_buffer(bundle)
    source = a.world_bin.read_bytes(); off = struct.unpack_from('<I', source, 48)[0]
    camera_inputs, raw_inputs = gpu.CameraInputs(), C.create_string_buffer(source[off:off + 520])
    assert lib.coh_world_parse_inputs(raw_inputs, 520, C.byref(camera_inputs)) == 0
    pose = V3(131.453125, .25, -114.953125); view, projection = (F * 12)(), M4()
    camera = camera_inputs.cameras[0]; pitch, distance = gpu.f32(.16), 22.
    camera.position = V3(pose[0], gpu.f32(pose[1] + 3.8 + distance * math.sin(pitch)), gpu.f32(pose[2] + distance * math.cos(pitch)))
    camera.pyr_degrees = V3(gpu.f32(pitch * 180 / math.pi), 0, 0)
    assert lib.coh_world_camera(C.byref(camera_inputs), 0, vw/vh, view, projection) == 0
    try:
        assert lib.coh_session_world_create(data, len(bundle), C.byref(world), error, len(error)), error.value.decode()
        assert lib.coh_session_world_surface(world, view, projection, pose, 24, C.byref(stats), error, len(error)), error.value.decode()
        packets = 0
        for frame in range(1, 13):
            g.glBindFramebuffer(0x8d40, 0); g.glViewport(0, 0, vw, vh)
            g.glClearColor(17/255, 19/255, 23/255, 1); g.glClear(0x4000 | 0x100)
            before = stats.draw_packets
            assert lib.coh_session_world_draw_observed(world, view, projection, pose, 24, C.byref(stats), error, len(error)), error.value.decode()
            packets = stats.draw_packets - before; assert packets > 0
            if frame == 12:
                floor_pixels = (C.c_ubyte * (cw * ch * 4))()
                assert cap.coh_frame_capture_readback(vw, vh, cw, ch, floor_pixels)
            assert lib.coh_session_world_observed_entity(world, view, projection, 125, pose, C.byref(stats), error, len(error)), error.value.decode()
            if frame < 12:
                assert e.e.eglSwapBuffers(e.display, surface)
        cpu, gpu_bytes = Q(), Q()
        assert lib.coh_session_world_owned_bytes(world, C.byref(cpu), C.byref(gpu_bytes))
        base = cpu.value + gpu_bytes.value + len(bundle)
        owner = C.c_void_p(cap.coh_frame_capture_create(base)); assert owner
        info = Info(vw, vh, 125, 12, 1, 1, 0, packets, 1, base, pose)
        pixels, width, height = C.c_void_p(), U(), U()
        assert cap.coh_frame_capture_begin(owner, C.byref(info), C.byref(pixels), C.byref(width), C.byref(height))
        assert (width.value, height.value) == (cw, ch)
        assert cap.coh_frame_capture_readback(vw, vh, width, height, pixels)
        assert e.e.eglSwapBuffers(e.display, surface)
        cap.coh_frame_capture_publish(owner, 1)
        size = Z(); raw_ptr = cap.coh_frame_capture_data(owner, C.byref(size), 0); assert raw_ptr
        raw = C.string_at(raw_ptr, size.value); assert len(raw) == 128+cw*ch*4
        assert not cap.coh_frame_capture_data(owner, C.byref(size), 12)
        rgba = raw[128:]
        visible = sum(any(abs(rgba[i+j]-c)>3 for j,c in enumerate((17,19,23))) for i in range(0,len(rgba),4))
        box_pixels = sum(rgba[i:i+4] != bytes(floor_pixels[i:i+4]) for i in range(0,len(rgba),4))
        assert visible > 64 and box_pixels > 4 and g.glGetError() == 0
        (a.work/'scene-capture.rgba').write_bytes(raw)
        from PIL import Image
        Image.frombytes('RGBA', (cw,ch), rgba).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(a.work/'captured-world-and-box.png')
    finally:
        cap.coh_frame_capture_destroy(C.byref(owner)); assert not owner.value
        if world:
            lib.coh_session_world_surface_lost(world, 1, C.byref(stats)); lib.coh_session_world_destroy(C.byref(world)); assert not world.value
        assert e.e.eglMakeCurrent(e.display, None, None, e.context)
        assert e.e.eglDestroySurface(e.display, surface); e.close()
    java = a.work/'ExportSceneCapture.java'
    java.write_text('''import java.io.*;import java.nio.file.*;import org.coh.nativecombined.SceneFrameCapture;
public class ExportSceneCapture{public static void main(String[]args)throws Exception{
File d=new File(args[0]);byte[]b=Files.readAllBytes(new File(d,"scene-capture.rgba").toPath());
String m=SceneFrameCapture.save(d,b,17,"cafe01");Files.write(new File(d,"scene-capture.json").toPath(),m.getBytes("UTF-8"));
try(OutputStream o=new FileOutputStream(new File(d,"scene-capture.zip"))){if(!SceneFrameCapture.writeZip(d,o))throw new AssertionError();}}}''')
    if a.fullscreen:
        java.write_text(java.read_text().replace('SceneFrameCapture.save(', 'SceneFrameCapture.saveLarge(').replace('SceneFrameCapture.writeZip(', 'SceneFrameCapture.writeZipLarge(').replace('d,b,17,','d,b,18,'))
    store = NATIVE/'combined-client/app/src/main/java/org/coh/nativecombined/SceneFrameCapture.java'
    run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-d',a.work,store,store.with_name('SceneCapturePng.java'),java])
    run(['java','-Xmx64m','-cp',a.work,'ExportSceneCapture',a.work])
    with zipfile.ZipFile(a.work/'scene-capture.zip') as archive:
        assert archive.read('scene-capture.rgba') == raw
        metadata = json.loads(archive.read('scene-capture.json'))
        assert metadata['sha256'] == pin(raw)['sha256'] and metadata['size_bytes'] == len(raw)
        assert metadata['frame'] == 12 and metadata['pose_generation'] == 1
        assert metadata['pose'] == list(pose) and metadata['whole_game_surface'] is True
    assert pins == {str(x):pin(x.read_bytes()) for x in sources}
    result = {'passed':True,'scope':'actual source neighborhood+box Mesa pbuffer through shipped capture owner/readback/publish and Java ZIP; Android window loop/JNI/live server not executed',
              'physical_Thor':False,'source_pose_regression_sample':list(pose),'viewport':[vw,vh],'dimensions':[cw,ch],
              'frame':12,'capture':pin(raw),'zip':pin((a.work/'scene-capture.zip').read_bytes()),'visible_pixels':visible,'box_changed_pixels':box_pixels,'bundle':pin(bundle),'world_bin':pin(source),
              'named_test_scene_cpu_bytes':cpu.value,'named_test_scene_gpu_bytes':gpu_bytes.value,'borrowed_bundle_bytes':len(bundle),
              'capture_reserve_bytes':cap.coh_frame_capture_reserve_bytes(),'process_or_driver_memory_measured':False,'gl_errors':0,'source_pins':pins,
              'stream_library':pin(a.stream_library.read_bytes()),'image':str(a.work/'captured-world-and-box.png')}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_pins'}))


if __name__ == '__main__': main()
