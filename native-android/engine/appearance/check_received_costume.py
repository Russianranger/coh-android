#!/usr/bin/env python3
"""Focused native-backed checks of received-Huge source preparation.

No raw packet or generated corpus is committed. Optional local source bodies
exercise the same original model conversion and neutral skinning path.
"""
import argparse
import ctypes as C
import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]
spec = importlib.util.spec_from_file_location('received_costume_prepare', HERE / 'prepare_received_costume.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

class Inventory:
    def __init__(self, names=()): self.names = set(names)
    def lookup(self, paths=(), texture_names=()):
        return [name for name in texture_names if name.casefold() in self.names]

def checks(library, args=None):
    lib = C.CDLL(str(library)); p.configure(lib)
    lib.received_abi.argtypes = [C.c_uint]; lib.received_abi.restype = C.c_size_t
    assert [lib.received_abi(i) for i in range(4)] == [C.sizeof(p.Snapshot), C.sizeof(p.Workspace), C.sizeof(p.a.Draw), C.sizeof(p.Diagnostics)]
    defs = p.definitions(HERE.parents[2]); assert len(defs) == 28
    snapshot = p.Snapshot(); snapshot.body = 4; snapshot.count = 28
    for part in snapshot.parts:
        part.mask = 7
        for i in range(3): part.strings[i].value = b'None'
    snapshot.parts[0].strings[0].value = b'Tight'
    snapshot.parts[0].strings[1].value = b'Pants'
    draws, count, diag = p.select(lib, snapshot, defs, Inventory())
    visible = [d for d in draws[:count] if not d.flags & 1]
    assert len(visible) == 1 and visible[0].geometry_path.lower() == b'data/player_library/huge_pants.geo'
    assert p.text(visible[0].texture[0]) == 'HIPS_Pants' and diag.body.body_type == 4
    assert p.text(diag.body.texture_prefix) == 'SH'
    draws, count, _ = p.select(lib, snapshot, defs, Inventory({'sh_hips_pants.tga'}))
    visible = [d for d in draws[:count] if not d.flags & 1]
    assert p.text(visible[0].texture[0]) == 'SH_HIPS_Pants'
    work, output, written, diagnostics = p.Workspace(), (p.a.Draw * 120)(), C.c_size_t(73), p.Diagnostics()
    C.memset(C.addressof(output), 0xa5, C.sizeof(output)); C.memset(C.addressof(diagnostics), 0xa5, C.sizeof(diagnostics))
    expected_output, expected_diagnostics = bytes(output), bytes(diagnostics)
    inputs = p.Inputs(defs, len(defs), 1, None, 0, p.a.Probe(), None, p.a.Cancel())
    status = lib.coh_appearance_costume_assemble(C.cast(C.byref(work), C.POINTER(p.Snapshot)), C.byref(inputs), C.byref(work), output, len(output), C.byref(written), C.byref(diagnostics))
    assert status == 1 and written.value == 73 and bytes(output) == expected_output and bytes(diagnostics) == expected_diagnostics
    status = lib.coh_appearance_costume_assemble(C.byref(snapshot), C.byref(inputs), C.byref(work), output, C.c_size_t(-1), C.byref(written), C.byref(diagnostics))
    assert status == 4 and written.value == 73 and bytes(output) == expected_output and bytes(diagnostics) == expected_diagnostics
    old = bytes(snapshot)
    for raw in (old[:-1], old + b'\0'):
        try: p.checked_snapshot(raw)
        except ValueError: pass
        else: raise AssertionError('Snapshot size admitted')
    snapshot.body = 0
    try: p.checked_snapshot(bytes(snapshot))
    except ValueError: pass
    else: raise AssertionError('Male substitute admitted')
    snapshot.body = 4; snapshot.count = 31
    try: p.select(lib, snapshot, defs, Inventory())
    except ValueError: pass
    else: raise AssertionError('Excess source parts admitted')
    snapshot.count = 28; snapshot.parts[0].mask = 0
    snapshot.parts[0].strings[0].value = b'nonempty-absent-string'
    try: p.select(lib, snapshot, defs, Inventory())
    except ValueError: pass
    else: raise AssertionError('Absent/nonempty string admitted')
    assert p.source_pins()['data/player_library/huge_pants.geo']['bytes'] > 0
    actual = None
    if args and args.archive:
        provider = p.module('received_check_archive', HERE / 'imported_archive.py')
        descriptor = os.open(args.archive, os.O_RDONLY | os.O_CLOEXEC)
        try:
            with tempfile.TemporaryDirectory(prefix='coh-received-actual-') as temporary:
                with provider.ImportedArchive(descriptor) as archive:
                    pins = p.source_pins(args.source_pins)
                    result, packets, layers = p.prepare(library, archive, args.snapshot.read_bytes(), args.rig.read_bytes(), HERE.parents[2], Path(temporary), pins)
                    texture_oracles = 0
                    from PIL import Image
                    for texture in result['available_texture_sources'].values():
                        if 'rgba_sha256' not in texture: continue
                        matches = archive.lookup(paths=[texture['path']]); assert len(matches) == 1
                        raw = archive.read_body(matches[0], pins[texture['path'].casefold()])
                        offset = 0 if raw[:4] == b'DDS ' else int.from_bytes(raw[:4], 'little')
                        expected = Image.open(io.BytesIO(raw[offset:])).convert('RGBA').tobytes()
                        assert hashlib.sha256(expected).hexdigest() == texture['rgba_sha256']
                        texture_oracles += 1
                assert result['bodytype'] == 4 and result['converted_parts'] == args.expect_parts
                assert result['source_payload_peak_bytes'] <= p.SCENE_LIMIT
                actual = {key: result[key] for key in ('snapshot_sha256', 'visible_parts', 'converted_parts', 'source_payload_peak_bytes')}
                actual['pillow_texture_oracles'] = texture_oracles
                actual['decoded_textures'] = len([value for value in result['available_texture_sources'].values() if 'rgba_sha256' in value])
                actual['vertices'] = sum(len(vertices) for _, vertices, _ in packets)
                actual['indices'] = sum(len(indices) for _, _, indices in packets)
                if args.capture:
                    capture = p.module('received_check_capture', HERE / 'capture_received_costume.py')
                    try:
                        capture.capture(packets, Path(temporary), p.SCENE_LIMIT, layers)
                    except ValueError: pass
                    else: raise AssertionError('Oversize old/candidate capture storage admitted')
                    assert not list(Path(temporary).glob('*.png'))
                    actual['capture_overflow_preflight'] = True
                    actual['capture'] = capture.capture(packets, Path(temporary), result['source_payload_peak_bytes'], layers)
        finally:
            os.close(descriptor)
    return {'actual': actual, 'abi': True, 'original_ordered_bodyparts': 28, 'actual_archive_probe_branch': True,
            'preserved_huge_source_selection': True, 'size_body_count_presence_negatives': 5,
            'source_geometry_substitutions': 0, 'alias_overflow_transaction_negatives': 2}

def build(output, mode):
    sources = [HERE / name for name in ('coh_appearance.c', 'coh_appearance_adapters.c', 'coh_appearance_mesh.c', 'coh_appearance_render.c', 'coh_appearance_costume.c')]
    sources += [NATIVE / name for name in ('character/coh_character.c', 'engine/assets/coh_asset_geo.c', 'engine/assets/coh_asset_loader.c', 'src/coh_assets.c', 'src/coh_dds.c', 'material-probe/app/src/main/cpp/coh_mesh.c', 'engine/renderer/coh_renderer.c')]
    helper = output / 'abi.c'
    helper.write_text('#include "coh_appearance_costume.h"\nsize_t received_abi(unsigned i){size_t a[]={sizeof(CohOriginalCostumeSnapshot),sizeof(CohAppearanceCostumeWorkspace),sizeof(CohAppearanceDraw),sizeof(CohAppearanceCostumeDiagnostics)};return i<4?a[i]:0;}\n')
    flags = ['-O2'] if mode == 'release' else ['-O1', '-g', '-fno-omit-frame-pointer', '-fsanitize=' + ('address' if mode == 'asan' else 'undefined')]
    library = output / ('received-' + mode + '.so')
    subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-ffp-contract=off', '-fno-fast-math', '-I' + str(NATIVE / 'include'), '-I' + str(HERE), *flags, '-shared', '-fPIC', *map(str, sources), str(helper), '-lz', '-lm', '-o', str(library)], check=True)
    return library

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['release', 'asan', 'ubsan', 'all'], default='release')
    parser.add_argument('--library', type=Path)
    for name in ('archive', 'snapshot', 'rig', 'source-pins'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--expect-parts', type=int, default=10)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    if any((args.archive, args.snapshot, args.rig)) and not all((args.archive, args.snapshot, args.rig)):
        parser.error('Optional actual source replay requires archive, snapshot and rig together')
    if args.library:
        print(json.dumps(checks(args.library, args))); return
    modes = ['release', 'asan', 'ubsan'] if args.mode == 'all' else [args.mode]
    results = {}
    with tempfile.TemporaryDirectory(prefix='coh-received-costume-') as temporary:
        for mode in modes:
            library = build(Path(temporary), mode); env = dict(os.environ)
            if mode == 'asan':
                env['LD_PRELOAD'] = subprocess.check_output(['cc', '-print-file-name=libasan.so'], text=True).strip()
                env['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
            if mode == 'ubsan': env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
            command = [sys.executable, str(Path(__file__).resolve()), '--library', str(library), '--expect-parts', str(args.expect_parts)]
            for name in ('archive', 'snapshot', 'rig', 'source_pins'):
                value = getattr(args, name)
                if value: command += ['--' + name.replace('_', '-'), str(value)]
            if args.capture and mode == 'release': command += ['--capture']
            results[mode] = json.loads(subprocess.check_output(command, env=env, text=True))
    print(json.dumps(results))

if __name__ == '__main__': main()
