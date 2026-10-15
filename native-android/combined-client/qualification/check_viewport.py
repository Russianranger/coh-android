#!/usr/bin/env python3
"""Exercise the production Java layout policy against the unchanged C camera.

The reported Thor failure is replayed with its actual camera pose. This is host
qualification of layout and camera contracts, not Android framework evidence.
"""
from pathlib import Path
import ctypes as C
import hashlib
import json
import math
import random
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'combined-client/app/src/main/java/org/coh/nativecombined/ViewportPolicy.java'
WORLD = ROOT / 'world/coh_world.c'

HARNESS = r'''
package org.coh.nativecombined;
import java.io.BufferedReader;
import java.io.InputStreamReader;
public final class ViewportTest {
 public static void main(String[] args) throws Exception {
  BufferedReader input = new BufferedReader(new InputStreamReader(System.in));
  for(String line; (line=input.readLine()) != null;) {
   String[] p=line.split(" ");
   int w=Integer.parseInt(p[1]), h=Integer.parseInt(p[2]);
   if(p[0].equals("fit")) {
    int[] fitted=ViewportPolicy.fit(w,h);
    System.out.println(fitted[0]+" "+fitted[1]);
   } else if(p[0].equals("controls")) {
    System.out.println(ViewportPolicy.controlsHeight(w,h));
   } else throw new AssertionError("Unknown test operation");
  }
 }
}
'''


class Node(C.Structure):
    _fields_ = [('parent', C.c_uint32), ('position', C.c_float * 3), ('pyr', C.c_float * 3)]


class Camera(C.Structure):
    _fields_ = [('position', C.c_float * 3), ('pyr', C.c_float * 3),
                ('fovy', C.c_float), ('aspect', C.c_float),
                ('znear', C.c_float), ('zfar', C.c_float),
                ('flip_x', C.c_uint32), ('flip_y', C.c_uint32)]


class Inputs(C.Structure):
    _fields_ = [('nodes', Node * 6), ('cameras', Camera * 6)]


def need(value, message):
    if not value:
        raise AssertionError(message)


def main():
    rng = random.Random(0x434F4856)
    # Exact failure geometry, normal orientations, zero-size lifecycle states,
    # camera boundaries, EGL limits and signed-int overflow-adjacent values.
    edges = [-2147483648, -1, 0, 1, 2, 3, 4, 7, 8, 9, 136, 137,
             239, 240, 469, 1080, 1920, 16383, 16384, 16385, 2147483647]
    sizes = [(1920, 469), (1920, 137), (137, 1920), (1080, 1920)]
    sizes += [(w, h) for w in edges for h in edges]
    small = [(w, h) for w in range(1, 25) for h in range(1, 25)]
    sizes += small
    sizes += [(rng.randint(1, 2147483647), rng.randint(1, 2147483647)) for _ in range(4000)]
    controls = [(h, p) for h in edges for p in edges]
    controls += [(rng.randint(1, 2147483647), rng.randint(0, 2147483647)) for _ in range(1000)]

    with tempfile.TemporaryDirectory(prefix='coh-viewport-') as directory:
        tmp = Path(directory)
        harness = tmp / 'ViewportTest.java'
        harness.write_text(HARNESS)
        subprocess.run(['java', 'com.sun.tools.javac.Main', '-d', str(tmp), str(JAVA), str(harness)],
                       check=True, capture_output=True, text=True)
        requests = [f'fit {w} {h}' for w, h in sizes] + [f'controls {h} {p}' for h, p in controls]
        completed = subprocess.run(['java', '-cp', str(tmp), 'org.coh.nativecombined.ViewportTest'],
                                   input='\n'.join(requests) + '\n',
                                   check=True, capture_output=True, text=True)
        lines = completed.stdout.splitlines()
        need(len(lines) == len(requests), 'Production Java policy omitted results')
        fitted = [tuple(map(int, line.split())) for line in lines[:len(sizes)]]

        library = tmp / 'world.so'
        subprocess.run(['cc', '-std=c11', '-O2', '-shared', '-fPIC', '-ffp-contract=off',
                        str(WORLD), '-lm', '-o', str(library)], check=True, capture_output=True, text=True)
        source = C.CDLL(str(library))
        source.coh_world_camera.argtypes = [C.POINTER(Inputs), C.c_uint32, C.c_float,
                                           C.POINTER(C.c_float), C.POINTER(C.c_float)]
        source.coh_world_group_eye_matrices.argtypes = [C.POINTER(Inputs), C.POINTER(C.c_float),
                                                        C.POINTER(C.c_float)]
        scene = Inputs()
        for i, node in enumerate(scene.nodes):
            node.parent = i - 1 if i else 0xffffffff
        camera = scene.cameras[0]
        # Actual pose from the failing 0.1.2 report, after controller movement.
        camera.position[:] = [575.005554, 90.3099747, -1352.3988]
        camera.pyr[:] = [0.604845524 * 180 / math.pi, -0.827515125 * 180 / math.pi, 0]
        camera.fovy = 60
        camera.aspect = 16 / 9
        camera.znear = .1
        camera.zfar = 500
        view, projection, eye = (C.c_float * 12)(), (C.c_float * 16)(), (C.c_float * 72)()

        def admit(w, h):
            return source.coh_world_camera(C.byref(scene), 0, w / h, view, projection)

        need(admit(1920, 469) == 0, 'Recorded initial camera pose must pass')
        need(admit(1920, 137) == -2, 'Recorded collapsed viewport must reproduce bounds rejection')
        boundary = [(1, 4, 0), (8, 1, 0), (1, 5, -2), (9, 1, -2)]
        for w, h, expected in boundary:
            need(admit(w, h) == expected, 'Unchanged source camera boundary differs')

        camera_comparisons = 0
        maximum_area_checks = 0
        for (available_w, available_h), (w, h) in zip(sizes, fitted):
            if available_w <= 0 or available_h <= 0:
                need((w, h) == (0, 0), 'Unmeasured Surface must remain unavailable')
                continue
            need(0 < w <= min(available_w, 16384) and 0 < h <= min(available_h, 16384),
                 'Fitted Surface exceeds measured or EGL bounds')
            need(w <= 8 * h and h <= 4 * w, 'Fitted Surface exceeds source camera bounds')
            need(admit(w, h) == 0, 'Production Java fit rejected by unchanged source camera')
            need(source.coh_world_group_eye_matrices(C.byref(scene), view, eye) == 0,
                 'Valid source view rejected by hierarchy evaluation')
            need(all(math.isfinite(v) for v in (*view, *projection, *eye)), 'Nonfinite source matrices')
            camera_comparisons += 1
            if available_w <= 24 and available_h <= 24:
                # Independent exhaustive oracle: no supported integer rectangle
                # inside these available bounds may have a larger area.
                best = max(x * y for x in range(1, available_w + 1)
                           for y in range(1, available_h + 1) if x <= 8 * y and y <= 4 * x)
                need(w * h == best, 'Production fit wastes available supported area')
                maximum_area_checks += 1

        control_results = list(map(int, lines[len(sizes):]))
        for (height, preferred), result in zip(controls, control_results):
            if height <= 0 or preferred <= 0:
                need(result == 0, 'Unavailable controls must not reserve height')
                continue
            need(0 <= result <= preferred and result <= height, 'Controls exceed available bounds')
            need(5 * (height - result) >= 2 * height, 'Controls leave less than 40% for the scene')
            need(result == preferred or 5 * (result + 1) > 3 * height,
                 'Controls unnecessarily lose a usable pixel')

    print(json.dumps({'status': 'passed', 'production_java_fit_cases': len(sizes),
                      'production_java_controls_cases': len(controls),
                      'unchanged_source_camera_comparisons': camera_comparisons,
                      'exhaustive_maximum_area_cases': maximum_area_checks,
                      'reported_failure_reproduced': {'size': [1920, 137], 'source_result': -2},
                      'reported_size_fitted': list(fitted[1]),
                      'production_policy_sha256': hashlib.sha256(JAVA.read_bytes()).hexdigest(),
                      'source_camera_sha256': hashlib.sha256(WORLD.read_bytes()).hexdigest(),
                      'scope': 'Host layout policy and unchanged source camera only; Android framework qualification is separate',
                      'actual_server_interoperability_verified': False}))


if __name__ == '__main__':
    main()
