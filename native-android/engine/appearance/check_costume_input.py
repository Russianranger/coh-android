#!/usr/bin/env python3
"""Original costume_send -> retained receive -> original appearance selection.

Source NPC selectors are test inputs, never substitutes for a live character.
Existence inventories deliberately exercise the established source branches;
this test does not claim those assets were loaded or rendered on a device.
"""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE / 'tests'))
import bindings as a
import original_oracle
import source_data


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def quoted(value):
    return 'NULL' if value is None else json.dumps(value)


def fixtures(source_root, work):
    entities = HERE / '../entities'
    legacy = module('costume_input_sender', entities / 'check_original_costume_receive.py')
    generator = module('costume_input_source', entities / 'prepare_original_costume_receive.py')
    _, sender_provenance = legacy.fixtures(source_root, work, generator.extract)
    corpus = source_data.load(source_root)
    pins = json.loads((HERE / 'source-pins.json').read_text())
    assert corpus['source_pins'] == pins['source_files']
    definition_text = ',\n'.join('{' + ','.join([quoted(d['name']), quoted(d['geometry_name']), quoted(d['texture_name']), quoted(d['base_name']), '{' + ','.join(map(str, (d['sockets'] + [0])[:2])) + '}', str(len(d['sockets'])), '0']) + '}' for d in corpus['definitions'])
    (work / 'costume-definitions.h').write_text('static const CohAppearancePartDef definitions[28]={\n' + definition_text + '\n};\n')
    declarations = []
    for index, costume in enumerate(corpus['costumes']):
        declarations.append(('if' if index == 0 else 'else if') + '(choice==' + str(index) + '){')
        declarations.append('c.appearance.bodytype=' + str(costume['body']) + ';c.appearance.entTypeFile=' + quoted(costume['ent_type']) + ';c.appearance.costumeFilePrefix=' + quoted(costume['prefix']) + ';')
        declarations.append('c.appearance.colorSkin.integer=' + str(int.from_bytes(bytes(costume['skin']), 'little')) + 'u;')
        for part in costume['parts']:
            prefix = 'parts[' + str(part['definition']) + ']'
            declarations.append(prefix + '.pchGeom=' + quoted(part['geometry']) + ';' + prefix + '.pchTex1=' + quoted(part['textures'][0]) + ';' + prefix + '.pchTex2=' + quoted(part['textures'][1]) + ';')
            for color in range(2):
                declarations.append(prefix + '.color[' + str(color) + '].integer=' + str(int.from_bytes(bytes(part['colors'][color]), 'little')) + 'u;')
        declarations.append('}')
    code = (work / 'original-sender.c').read_text() + '''
void appearance_fixture(unsigned choice,unsigned mode,unsigned start,U8*out,U32*length){
 U32 memory[32768]={0};Packet p={0};Costume c={0};CostumePart parts[30]={{0}};fixture_default=28;
 for(unsigned i=0;i<30;i++){c.parts[i]=&parts[i];parts[i].pchGeom="None";parts[i].pchTex1="None";parts[i].pchTex2="None";}
 c.appearance.iNumParts=28;
''' + '\n'.join(declarations) + '''
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned i=0;i<start;i++)bsWriteBits(&p.stream,1,i&1);p.stream.byteAlignedMode=mode;costume_send(&p,&c,0);assert(!p.stream.errorFlags);*length=p.stream.bitLength;memcpy(out,memory,(*length+7)/8);
}
'''
    sender = work / 'appearance-original-sender.c'
    sender.write_text(code)
    library = work / 'appearance-original-sender.so'
    legacy.run(['cc', '-std=c99', '-O0', '-shared', '-fPIC', '-w', '-I' + str(ROOT / 'native-android/include'), '-I' + str(entities), sender, '-lm', '-o', library], work, 'appearance-sender-compile')
    dll = C.CDLL(str(library))
    dll.appearance_fixture.argtypes = [C.c_uint] * 3 + [C.c_void_p, C.c_void_p]
    ref, functions = original_oracle.build(source_root, work, HERE)
    assert functions == pins['executed_functions']
    ref.ref_ent.argtypes = [C.c_int]
    ref.ref_ent.restype = C.c_char_p
    ref.ref_tex.argtypes = [C.c_int]
    ref.ref_tex.restype = C.c_char_p
    with (work / 'costume-definitions.h').open('a') as header:
        header.write('static const char *const source_ent[9]={' + ','.join(quoted(ref.ref_ent(i).decode()) for i in range(9)) + '};\n')
        header.write('static const char *const source_texture_prefix[9]={' + ','.join(quoted(ref.ref_tex(i).decode()) for i in range(9)) + '};\n')
    ref.ref_geometry.argtypes = [C.POINTER(a.Body), C.POINTER(a.Def), C.c_char_p, C.POINTER(C.c_char_p), C.c_int, a.Probe, C.c_void_p, C.c_void_p, C.c_void_p]
    ref.ref_textures.argtypes = [C.POINTER(a.Body), C.POINTER(a.Def), C.c_char_p, C.c_char_p, a.Probe, C.c_void_p, C.c_void_p]
    ref.ref_colors.argtypes = [C.c_void_p, C.c_void_p, C.c_char_p, C.c_void_p]
    defs = [a.Def(a.b(d['name']), a.b(d['geometry_name']), a.b(d['texture_name']), a.b(d['base_name']), (a.u32 * 2)(*(d['sockets'] + [0])[:2]), len(d['sockets']), 0) for d in corpus['definitions']]
    inventories = [set(), {'SF_FACE_none.tga', 'SH_HIPS_none.tga', 'SM_CHEST_skin_01a.tga'}, {'huge_BACK.GEO_BACK_Armored_Tight', 'V_Wretch_FACE_skin_01a.tga'}]
    links = (C.c_char_p * 2)(b'Armored', b'Jacket')
    rows = []
    for choice, costume in enumerate(corpus['costumes']):
        # Original sendCachedIndexedString compares case-insensitively and
        # reuses the first spelling. The authored HUGE/huge header exercises
        # that observable source behavior before any part strings are sent.
        cache = {}
        def canonical(value):
            value = value if value is not None else 'None'
            return cache.setdefault(value.lower(), value)
        ent = canonical(costume['ent_type']) if costume['ent_type'] is not None else None
        prefix = canonical(costume['prefix']) if costume['prefix'] is not None else None
        body = a.Body(costume['body'], a.b(ent) or ref.ref_ent(costume['body']), a.b(prefix) or ref.ref_ent(costume['body']), ref.ref_tex(costume['body']))
        authored = {p['definition']: p for p in costume['parts']}
        parts = {}
        for definition in range(28):
            part = dict(authored.get(definition, {'geometry': 'None', 'textures': ['None', 'None'], 'colors': [[0] * 4] * 4}))
            part['geometry'] = canonical(part['geometry'])
            part['textures'] = [canonical(value) for value in part['textures']]
            canonical(None)  # Source sender encodes the absent FX as None.
            parts[definition] = part
        for inventory, names in enumerate(inventories):
            callback = a.Probe(lambda ctx, kind, key: int(key.decode() in names))
            expected = []
            for definition, d in enumerate(defs):
                part = parts[definition]
                keys = C.create_string_buffer(512)
                sockets = (C.c_int * 2)()
                count = ref.ref_geometry(C.byref(body), C.byref(d), a.b(part['geometry']), links, 2, callback, None, keys, sockets)
                if not count:
                    continue
                textures = C.create_string_buffer(512)
                ref.ref_textures(C.byref(body), C.byref(d), *map(a.b, part['textures']), callback, None, textures)
                skin = C.create_string_buffer(bytes(costume['skin']))
                colors = C.create_string_buffer(bytes(part['colors'][0] + part['colors'][1]))
                selected_colors = C.create_string_buffer(8)
                ref.ref_colors(skin, colors, a.b(part['textures'][0]), selected_colors)
                for socket in range(count):
                    draw = a.Draw()
                    draw.definition, draw.socket, draw.generation = definition, sockets[socket], 19
                    key = keys.raw[socket * 256:(socket + 1) * 256].split(b'\0')[0]
                    draw.geometry_key = key
                    if key == b'NONE':
                        draw.flags |= 1
                    else:
                        file, model = key.split(b'.', 1)
                        draw.geometry_path, draw.model_name = b'data/player_library/' + file + b'.geo', model
                    if 'skin' in part['textures'][0].lower():
                        draw.flags |= 2
                    for texture in range(2):
                        draw.texture[texture].value = textures.raw[texture * 256:(texture + 1) * 256].split(b'\0')[0]
                        draw.color[texture][:] = selected_colors.raw[texture * 4:(texture + 1) * 4]
                    expected.append(bytes(draw))
            for mode, start in [(0, 0), (0, 3), (0, 7), (1, 0)]:
                message = (C.c_uint8 * 16384)()
                bits = C.c_uint32()
                dll.appearance_fixture(choice, mode, start, message, C.byref(bits))
                rows.append(struct.pack('<5I', mode, start, bits.value, inventory, len(expected)) + bytes(message[:(bits.value + 7) // 8]) + bytes(body) + b''.join(expected))
    path = work / 'costume-input-fixtures.bin'
    path.write_bytes(struct.pack('<I', len(rows)) + b''.join(rows))
    return path, {'source_pins': corpus['source_pins'], 'original_client_functions': functions, 'original_sender': sender_provenance, 'costumes': [c['name'] for c in corpus['costumes']], 'complete_fixture_empty_parts': 'Absent NPC parts explicitly sent as None; no live substitution.', 'generated_sender_sha256': hashlib.sha256(code.encode()).hexdigest(), 'fixtures_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'existence_inventories_mocked': True}, legacy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    fixture, source, legacy = fixtures(args.source_root, work)
    sources = [HERE / n for n in ['coh_appearance.c', 'coh_appearance_costume.c', 'test_costume_input.c']] + [HERE / '../entities/coh_original_costume_receive.c', HERE / '../replication/coh_replication.c']
    flags = ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-fno-pie', '-no-pie', '-fstack-usage', '-I' + str(work)]
    dependencies = subprocess.run([*flags, '-M', *map(str, sources)], capture_output=True, text=True, check=True)
    inputs = {Path(__file__).resolve(), HERE / 'source-pins.json', HERE / 'tests/original_oracle.py', HERE / 'tests/source_data.py', HERE / 'tests/bindings.py'}
    for line in dependencies.stdout.replace('\\\n', ' ').splitlines():
        for token in shlex.split(line.split(':', 1)[1]):
            path = Path(token).resolve()
            if path.is_relative_to(ROOT):
                inputs.add(path)
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)}
    result = {'passed': True, 'source': source, 'input_sha256': hashes, 'modes': {}, 'scope': 'Decoded costume asset selection only; no invented rig, model, texture, morph, actor publication or physical packet replay.'}
    env = {**os.environ, 'ASAN_OPTIONS': 'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
    for mode, options in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fsanitize=address']), ('ubsan', ['-O1', '-g', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
        binary = work / mode
        legacy.run([*flags, *options, *sources, '-lm', '-o', binary], work, mode + '-compile')
        result['modes'][mode] = json.loads(legacy.run([binary, fixture], work, mode + '-run', env))
    assert len({json.dumps(row, sort_keys=True) for row in result['modes'].values()}) == 1
    frames = []
    for path in work.glob('release-*.su'):
        for line in path.read_text().splitlines():
            name, size, kind = line.split('\t')
            if 'test_costume_input.c:' not in name and ('coh_appearance' in name or 'coh_original_costume_receive.c:' in name or 'original_costume_receive.inc:' in name or name.rsplit(':', 1)[-1] in ('valid', 'coh_rep_read', 'coh_rep_pack')):
                frames.append({'function': name.rsplit(':', 1)[-1], 'bytes': int(size), 'kind': kind})
    assert sum(row['bytes'] for row in frames) < 8192
    result['memory'] = {'workspace_bytes': result['modes']['release']['workspace_bytes'], 'snapshot_bytes': 48352, 'heap_allocations': 0, 'conservative_combined_frame_sum': sum(row['bytes'] for row in frames), 'native_frames': frames, 'scene_limit': 100663296, 'initial_limit': 8388608, 'RSS_PSS_observed': None}
    assert hashes == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(inputs)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'modes': result['modes'], 'memory': {k: v for k, v in result['memory'].items() if k != 'native_frames'}}))


if __name__ == '__main__':
    main()
