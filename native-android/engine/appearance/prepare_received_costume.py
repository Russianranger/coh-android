#!/usr/bin/env python3
"""Prepare selected original-receiver meshes from an available CLIENT archive.

This host tool keeps the live box fallback untouched. It resolves the original
appearance through actual archive texture-existence probes, verifies available
GEO bodies against retained source hashes, and uses the existing native GEO
converter and Huge hierarchy/palette sampler. Neutral skinning is explicitly an
inspection of selected meshes; packet-authored morphology is retained, not
silently replaced by NPC morphology. No archive download or live actor publish.
"""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import sys

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]
SCENE_LIMIT = 96 << 20
SOURCE_LIMIT = 4 << 20

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result

a = module('received_appearance_abi', HERE / 'tests/bindings.py')
api = module('received_asset_abi', HERE / 'check_render.py')
bridge = module('received_render_abi', HERE / 'tests/render_gpu.py')
source = module('received_source_fields', HERE / 'tests/source_data.py')
U, Z = C.c_uint32, C.c_size_t

class SnapshotPart(C.Structure):
    _fields_ = [('mask', U), ('colors', U * 4), ('strings', (C.c_char * 260) * 6)]
class Snapshot(C.Structure):
    _fields_ = [('body', U), ('count', U), ('header', U), ('skin', U),
                ('converted', C.c_int32), ('super_color', C.c_int32),
                ('scales', C.c_float * 30), ('super_colors', (U * 2) * 36),
                ('ent_type', C.c_char * 260), ('prefix', C.c_char * 260),
                ('parts', SnapshotPart * 30)]
class Inputs(C.Structure):
    _fields_ = [('definitions', C.POINTER(a.Def)), ('count', U), ('generation', U),
                ('links', C.POINTER(C.c_char_p)), ('link_count', U),
                ('probe', a.Probe), ('context', C.c_void_p), ('cancel', a.Cancel)]
class Workspace(C.Structure):
    _fields_ = [('assembly', a.Workspace), ('request', a.Request), ('parts', a.Part * 30)]
class Diagnostics(C.Structure):
    _fields_ = [('body', a.Body), ('assembly', a.Diagnostics), ('workspace', Z)]

def sha(raw): return hashlib.sha256(raw).hexdigest()
def text(value): return bytes(value).split(b'\0')[0].decode('ascii')
def checked_snapshot(raw):
    if len(raw) != C.sizeof(Snapshot): raise ValueError('Snapshot byte size differs')
    snapshot = Snapshot.from_buffer_copy(raw)
    if snapshot.body != 4: raise ValueError('This inspection requires the received Huge body')
    return snapshot

def git_bytes(root, name):
    path = root / name
    return path.read_bytes() if path.is_file() else subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=root)

def definitions(root):
    pins = json.loads((HERE / 'source-pins.json').read_text())['source_files']
    names = ['upstream/i24/data/defs/ui/bodyparts.bp', 'upstream/ouroboros/Common/seq/bones.h']
    raw = [git_bytes(root, name).replace(b'\r\n', b'\n') for name in names]
    for name, body in zip(names, raw):
        if sha(body) != pins[name]: raise ValueError('Source BodyPart/bone definition changed: ' + name)
    bones = raw[1].decode().split('typedef enum BoneId', 1)[1]
    ids = re.findall(r'\bBONEID_([A-Z0-9_]+)\s*,', bones)
    ids = ids[:ids.index('COUNT')]
    bp = raw[0].decode(); rows = []
    for match in re.finditer(r'(?m)^BodyPart\s*$', bp):
        fields = source.fields(bp[match.end():bp.index('\nEnd', match.end())])
        count = int(fields['bonecount'][0]); geo = fields['geoname'][0]
        sockets = [ids.index((geo + suffix).upper()) if (geo + suffix).upper() in ids else 0xffffffff for suffix in (['R', 'L'] if count == 2 else [''])]
        strings = [fields[key][0].encode() for key in ('name', 'geoname', 'texname', 'basename')]
        rows.append(a.Def(*strings, (U * 2)(*(sockets + [0])[:2]), len(sockets), int(fields.get('dontclear', ['0'])[0])))
    if len(rows) != 28: raise ValueError('Verified original BodyPart order/count differs')
    return (a.Def * len(rows))(*rows)

def configure(lib):
    api.configure(lib); bridge.animation.configure(lib)
    lib.coh_appearance_costume_assemble.argtypes = [C.POINTER(Snapshot), C.POINTER(Inputs), C.POINTER(Workspace), C.POINTER(a.Draw), Z, C.POINTER(Z), C.POINTER(Diagnostics)]
    lib.coh_appearance_geo_model.argtypes = [C.POINTER(api.asset.Geo), C.POINTER(a.Draw), U, C.POINTER(U), C.POINTER(api.asset.Model)]
    lib.coh_renderer_default_material.argtypes = [C.c_int]
    lib.coh_renderer_default_material.restype = bridge.renderer.Material
    lib.coh_appearance_render_part.argtypes = [C.POINTER(a.Draw), C.POINTER(bridge.Resource), C.POINTER(bridge.Actor), C.POINTER(bridge.Material), U, C.POINTER(C.c_float), C.POINTER(C.c_float), C.POINTER(bridge.renderer.Vertex), Z, C.POINTER(U), Z, C.POINTER(bridge.renderer.Draw), C.c_void_p]

def select(lib, snapshot, defs, archive):
    errors = []
    def probe(context, kind, key):
        try:
            # No chest-link overrides are supplied: only source texture probes
            # can occur. Geometry is resolved later by the original GEO model API.
            if kind != 2: raise ValueError('Unexpected source geometry existence probe')
            return bool(archive.lookup(texture_names=[key.decode('ascii')]))
        except Exception as error:
            errors.append(error); return 0
    callback = a.Probe(probe)
    inputs = Inputs(defs, len(defs), 1, None, 0, callback, None, a.Cancel())
    work, draws, count, diag = Workspace(), (a.Draw * 120)(), Z(), Diagnostics()
    status = lib.coh_appearance_costume_assemble(C.byref(snapshot), C.byref(inputs), C.byref(work), draws, len(draws), C.byref(count), C.byref(diag))
    if errors: raise errors[0]
    if status: raise ValueError('Original appearance selection status ' + str(status))
    return draws, count.value, diag

def source_pins(extra=None):
    pins = {row['name'].casefold(): {'bytes': row['size'], 'sha256': row['sha256']} for row in json.loads((HERE / 'corpus-pins.json').read_text())['records']}
    if extra:
        for name, pin in json.loads(extra.read_text()).items():
            if name.casefold() in pins and pins[name.casefold()] != pin: raise ValueError('Source pin overrides an existing identity')
            pins[name.casefold()] = pin
    return pins

def prepare(library, archive, snapshot_raw, rig_raw, root, output, pins):
    lib = C.CDLL(str(library)); configure(lib)
    snapshot = checked_snapshot(snapshot_raw); defs = definitions(root)
    recovered = module('received_huge_identity', HERE / 'recover_huge_rig.py').recover(rig_raw)
    del recovered
    draws, count, diagnostics = select(lib, snapshot, defs, archive)
    rig_buffer = (C.c_uint8 * len(rig_raw)).from_buffer_copy(rig_raw)
    rig, pose = bridge.animation.Rig(), bridge.animation.Pose()
    if lib.coh_animation_parse(rig_buffer, len(rig_raw), C.byref(rig)): raise ValueError('Original Huge rig cannot parse')
    if lib.coh_animation_sample(C.byref(rig), rig.first_frame, C.byref(pose)): raise ValueError('Original Huge pose cannot sample')
    fixed = len(snapshot_raw) + C.sizeof(snapshot) + C.sizeof(defs) + C.sizeof(Workspace) + C.sizeof(draws) + C.sizeof(rig) + C.sizeof(pose) + len(rig_raw) * 2 + (32 << 10) + (192 << 10)
    peak = fixed; retained = 0; packets = []; parts = []; missing = []
    visible = [draw for draw in draws[:count] if not draw.flags & 1]
    for index, draw in enumerate(visible):
        path = text(draw.geometry_path); matches = archive.lookup(paths=[path])
        row = {'definition': draw.definition, 'socket': draw.socket, 'path': path, 'model': text(draw.model_name), 'textures': [text(value) for value in draw.texture], 'colors': [list(value) for value in draw.color]}
        parts.append(row)
        if not matches:
            missing.append({'kind': 'geometry', 'path': path, 'model': row['model']}); continue
        if len(matches) != 1: raise ValueError('Selected source geometry is ambiguous: ' + path)
        pin = pins.get(path.casefold())
        if pin is None:
            missing.append({'kind': 'geometry_hash', 'path': path}); continue
        raw = archive.read_body(matches[0], pin)
        if len(raw) > SOURCE_LIMIT: raise ValueError('Source body exceeds existing 4 MiB bound')
        body = (C.c_uint8 * len(raw)).from_buffer(raw); needed = Z()
        if lib.coh_asset_geo_workspace(api.asset.Bytes(C.addressof(body), len(raw)), C.byref(needed)): raise ValueError('Invalid selected original GEO')
        if fixed + retained + len(raw) + needed.value + (128 << 10) > SCENE_LIMIT: raise ValueError('GEO preflight exceeds existing scene cap')
        header = C.create_string_buffer(needed.value); geo = api.asset.Geo()
        if lib.coh_asset_geo_open(api.asset.Bytes(C.addressof(body), len(raw)), header, len(header), 4096, C.byref(geo)): raise ValueError('Original GEO cannot open')
        model_index, model = U(), api.asset.Model()
        status = lib.coh_appearance_geo_model(C.byref(geo), C.byref(draw), 4096, C.byref(model_index), C.byref(model))
        if status == 3:
            missing.append({'kind': 'model', 'path': path, 'model': row['model']})
            del model_index, model, body, raw, header, geo
            continue
        if status: raise ValueError('Original model lookup failed: ' + str(status))
        requirement = api.Requirements()
        if lib.coh_appearance_mesh_requirements(C.byref(geo), model_index, draw.socket, C.byref(requirement)): raise ValueError('Selected mesh requirements failed')
        vertex_bytes, index_bytes = requirement.vertices * C.sizeof(bridge.renderer.Vertex), requirement.indices * 4
        total = fixed + retained + len(raw) + needed.value + requirement.workspace_bytes + requirement.canonical_bytes + vertex_bytes + index_bytes + (128 << 10)
        if total > SCENE_LIMIT: raise ValueError('Mesh preflight exceeds existing scene cap')
        peak = max(peak, total)
        scratch, canonical = C.create_string_buffer(requirement.workspace_bytes), C.create_string_buffer(requirement.canonical_bytes)
        mesh = api.Mesh()
        if lib.coh_appearance_mesh_build(C.byref(geo), model_index, draw.socket, scratch, len(scratch), canonical, len(canonical), C.byref(mesh), None): raise ValueError('Original source mesh conversion failed')
        vertices, indices = (bridge.renderer.Vertex * mesh.vertices)(), (U * mesh.indices)()
        actor = bridge.Actor(1, 1, 4, 1, 1, 1, C.addressof(rig), None, C.addressof(pose))
        resource = bridge.Resource(1, 1, index + 1, 1, 1, 4, 0, mesh.indices, draw.geometry_path, draw.model_name, C.addressof(mesh))
        binding = bridge.Material(lib.coh_renderer_default_material(1), 1, (C.c_char_p * 2)(*[name.encode() for name in row['textures']]))
        packet = bridge.renderer.Draw(); identity = bridge.renderer.identity()
        if lib.coh_appearance_render_part(C.byref(draw), C.byref(resource), C.byref(actor), C.byref(binding), 1, identity, identity, vertices, len(vertices), indices, len(indices), C.byref(packet), None): raise ValueError('Selected Huge palette/skin failed')
        filename = 'part-' + str(index) + '.mesh'
        (output / filename).write_bytes(memoryview(canonical))
        (output / ('part-' + str(index) + '.vertices')).write_bytes(memoryview(vertices))
        row.update(canonical=filename, canonical_sha256=sha(memoryview(canonical)), source_sha256=sha(raw), vertices=mesh.vertices, indices=mesh.indices, materials=requirement.materials)
        packets.append((packet, vertices, indices)); retained += vertex_bytes + index_bytes + C.sizeof(packet)
        del resource, binding, actor, model, model_index, body, raw, header, geo, scratch, canonical, mesh
        for name in row['textures']:
            if name.casefold() != 'none' and not archive.lookup(texture_names=[name + '.tga']): missing.append({'kind': 'texture', 'name': name})
    result = {'snapshot_sha256': sha(snapshot_raw), 'bodytype': snapshot.body, 'records': count, 'visible_parts': len(visible), 'converted_parts': len(packets), 'parts': parts, 'missing': missing, 'rig_sha256': sha(rig_raw), 'scales': list(snapshot.scales), 'authored_scales_applied': False, 'skinning_scope': 'authentic Huge hierarchy; neutral inspection only; no Wretch morphology', 'source_payload_peak_bytes': peak, 'source_payload_limit_bytes': SCENE_LIMIT, 'measurement_scope': 'explicit source/native buffers and stack reserve; Python allocator/RSS not measured', 'live_actor_published': False}
    return result, packets

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('library', 'archive', 'snapshot', 'rig', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=HERE.parents[2])
    parser.add_argument('--source-pins', type=Path)
    args = parser.parse_args()
    provider = module('received_imported_archive', HERE / 'imported_archive.py')
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('Output already exists')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.archive, os.O_RDONLY | os.O_CLOEXEC)
    try:
        with tempfile.TemporaryDirectory(prefix='coh-received-source-', dir=args.output.parent) as temporary:
            stage = Path(temporary)
            with provider.ImportedArchive(descriptor) as archive:
                result, _ = prepare(args.library, archive, args.snapshot.read_bytes(), args.rig.read_bytes(), args.source_root, stage, source_pins(args.source_pins))
            (stage / 'costume.json').write_text(json.dumps(result, indent=2) + '\n')
            os.rename(stage, args.output)
        print(json.dumps({key: result[key] for key in ('visible_parts', 'converted_parts', 'missing', 'source_payload_peak_bytes')}))
    finally:
        os.close(descriptor)

if __name__ == '__main__': main()
