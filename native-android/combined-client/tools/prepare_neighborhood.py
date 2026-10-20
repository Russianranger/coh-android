#!/usr/bin/env python3
"""Add an authentic bounded Atlas sidewalk neighborhood to the accepted map bundle.

Only original source instances and material partition zero of the high road
model are retained. The original map.bin and offline preview stay byte exact.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import struct
import zipfile

POSE = [131.453125, 0.25, -114.953125]
RADIUS = 96.0
NO = 0xffffffff
PART_MASK = 1
SOURCE = [
    ('upstream/i24/data/maps/city_zones/city_01_01/city_01_01_layer_geometry.txt', 2617295, 'e2fcea989f1030e6e4fc57d94d2130302a8271eaabcbd8b9a6488040d94e9e28'),
    ('upstream/i24/data/object_library/Streets/road_4lane/road_4lane.txt', 45452, '48d194222613282a3418295f78dca79ccac4a4af3c7a1c4abb7a95283192a402'),
    ('upstream/i24/data/tricks/streets/streets.txt', 3419, '21b8e0fbca77e50cddc259781286c9443d48e84e43bea1c27e75dcc06dee8662'),
]
INPUTS = [
    ('data/object_library/streets/road_4lane/road_4lane.geo', 'road_4lane.geo', 109481, '43bd2f6f192bdfc88f44328657f5c16b042d0dea9bb34b1e5e1704befeb8bcd2', 'atlas'),
    ('data/texture_library/world/streets/streets/street_sidewalk1.texture', 'street_sidewalk1.texture', 175067, 'a2bd476cc82ff8175d5c23f98f1c4ea709c70cf0ba6fe3bd2f699b168ee00dab', 'atlas'),
    ('data/texture_library/world/det_texture/dcoarse_sidewalk.texture', 'dcoarse_sidewalk.texture', 43991, '312ed00587c8663376ac38260b721df6ac7ead3e39f528f23f8b8777d7180b4e', 'client'),
]


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def payloads(root, cache):
    cache.mkdir(parents=True, exist_ok=True)
    missing = []
    for path, alias, size, digest, origin in INPUTS:
        file = cache / alias
        if file.exists():
            require(file.is_file() and not file.is_symlink() and file.stat().st_size == size and sha(file.read_bytes()) == digest,
                    'Neighborhood cached source payload differs: ' + alias)
        else:
            missing.append((path, alias, size, digest, origin))
    if missing:
        ranges = module('neighborhood_original_zip_ranges', root / 'native-android/tools/material_fixture/acquire.py')
        reader = ranges.HTTPRange('https://github.com/Russianranger/coh-android/releases/download/coh-assets-v1.0.0/COH-Assets-1.0.0-Base.zip', 1630092780, 16 << 20)
        archives = {}
        try:
            with zipfile.ZipFile(reader) as outer:
                for origin, name, size in [('atlas', 'atlas-world-supplement.zip', 207803201), ('client', 'client-visual-assets.zip', 859075775)]:
                    if any(row[4] == origin for row in missing):
                        info = outer.getinfo('payloads/runtime/' + name)
                        require(info.file_size == size and not info.flag_bits & 1, 'Neighborhood source archive envelope differs')
                        archives[origin] = zipfile.ZipFile(ranges.subzip(reader, info))
            for path, alias, size, digest, origin in missing:
                info = archives[origin].getinfo(path)
                require(info.file_size == size and not info.flag_bits & 1 and info.compress_type in (0, 8), 'Neighborhood source member envelope differs')
                raw = archives[origin].read(info)
                require(len(raw) == size and sha(raw) == digest, 'Neighborhood source payload hash differs: ' + alias)
                temporary = cache / (alias + '.tmp')
                with temporary.open('xb') as stream:
                    stream.write(raw)
                temporary.replace(cache / alias)
        finally:
            for archive in archives.values():
                archive.close()
    return [{'path': path, 'generation': 1, 'source_file': alias, 'raw': (cache / alias).read_bytes(), 'bytes': size, 'sha256': digest}
            for path, alias, size, digest, origin in INPUTS]


def original_assets(raw, fixture):
    require(raw[:8] == b'COHWB001' and len(raw) == fixture['bundle']['bytes'] and sha(raw) == fixture['bundle']['sha256'], 'Accepted original map bundle differs')
    version, header, total, ix, ix_size, count, rows, strings, string_size, payload, materials, material_offset, material_size, reserved = struct.unpack_from('<14I', raw, 8)
    require(version == 1 and header == 64 and total == len(raw) and count == len(fixture['assets']), 'Accepted bundle header differs')
    result = []
    for i, item in enumerate(fixture['assets']):
        name, generation, offset, size, a, b = struct.unpack_from('<6I', raw, rows + 24 * i)
        require(offset <= len(raw) and size <= len(raw) - offset and name < string_size, 'Accepted asset span differs')
        end = raw.find(b'\0', strings + name, strings + string_size)
        require(end >= 0 and raw[strings + name:end].decode() == item['path'] and generation == item['generation'], 'Accepted asset identity differs')
        body = raw[offset:offset + size]
        require(size == item['bytes'] and sha(body) == item['sha256'], 'Accepted asset body differs')
        result.append(dict(item, raw=body))
    return result


def ground_hits(vertices, indices, part, world, reference):
    relative = [POSE[i] - world[i][3] for i in range(3)]
    point = [sum(world[i][j] * relative[i] for i in range(3)) for j in range(3)]
    hits = []
    for triangle in range(part['first_triangle'], part['first_triangle'] + part['triangle_count']):
        a, b, c = [[vertices[3 * index + j] for j in range(3)] for index in indices[triangle * 3:triangle * 3 + 3]]
        den = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
        if abs(den) < 1e-9:
            continue
        u = ((b[2] - c[2]) * (point[0] - c[0]) + (c[0] - b[0]) * (point[2] - c[2])) / den
        v = ((c[2] - a[2]) * (point[0] - c[0]) + (a[0] - c[0]) * (point[2] - c[2])) / den
        w = 1 - u - v
        if min(u, v, w) >= -1e-6:
            y = u * a[1] + v * b[1] + w * c[1]
            ground = reference.transform(world, [point[0], y, point[2]])
            if 0 <= POSE[1] - ground[1] <= 0.5:
                hits.append({'triangle': triangle, 'barycentric': [u, v, w], 'ground': ground, 'pose_height': POSE[1] - ground[1]})
    return hits


def prepare(source_root: Path, assets: Path, cache: Path) -> dict:
    source_root, assets, cache = source_root.resolve(), assets.resolve(), cache.resolve()
    require(assets.is_dir(), 'Accepted scene assets directory required')
    source_files = []
    for path, size, digest in SOURCE:
        raw = (source_root / path).read_bytes()
        require(len(raw) == size and sha(raw) == digest, 'Neighborhood original source changed: ' + path)
        source_files.append({'path': path, 'bytes': size, 'sha256': digest})
    native = source_root / 'native-android'
    builder = module('neighborhood_map_builder', native / 'tools/map_fixture/prepare.py')
    reference = module('neighborhood_source_matrices', native / 'tools/world_fixture/world_reference.py')
    legacy = module('neighborhood_legacy_geo', native / 'tools/walkable_fixture/prepare.py')
    old_raw = (assets / 'map.bin').read_bytes()
    fixture = json.loads((assets / 'map-fixture.json').read_text())
    require(fixture.get('passed') and len(fixture['nodes']) == 25 and len(fixture['endpoints']) == 3 and len(fixture['assets']) == 8, 'Accepted map fixture shape differs')
    prior_assets = original_assets(old_raw, fixture)
    extra = payloads(source_root, cache)
    data, models = legacy.legacy_records(extra[0]['raw'])
    model = next(row for row in models if row['name'] == '_4_strt_hi__roadhi')
    require(model['scale'] == [1.0, 1.0, 1.0] and model['vertex_count'] == 120 and model['triangle_count'] == 62, 'Original high road model differs')
    part = model['materials'][0]
    require(part == {'name': 'street_sidewalk1.tga', 'triangle_count': 12, 'first_triangle': 0}, 'Original sidewalk partition differs')
    positions = legacy.geo.accepted.decode_delta(legacy.stream(data, model, 1), model['vertex_count'], 3, True)
    indices = legacy.geo.accepted.decode_delta(legacy.stream(data, model, 0), model['triangle_count'], 3, False)
    used = set(indices[:part['triangle_count'] * 3])
    lo = [min(positions[3 * i + j] for i in used) for j in range(3)]
    hi = [max(positions[3 * i + j] for i in used) for j in range(3)]
    center = [legacy.f32((a + b) * 0.5) for a, b in zip(lo, hi)]
    radius = legacy.f32(math.sqrt(sum(max(abs(a - c), abs(b - c)) ** 2 for a, b, c in zip(lo, hi, center))))
    definitions, refs, _ = builder.parse_groups((source_root / SOURCE[0][0]).read_text())
    road_defs, _, _ = builder.parse_groups((source_root / SOURCE[1][0]).read_text())
    wrapper = road_defs['4_strt']
    high = next(row for row in wrapper['groups'] if row['name'] == '_4_strt_hi')
    require(high['pos'] == [0.0, -0.000366, 0.0] and high['pyr'] == [0.0, 0.0, 0.0], 'Original high-road child transform differs')
    nodes, endpoints = copy.deepcopy(fixture['nodes']), copy.deepcopy(fixture['endpoints'])
    endpoint = len(endpoints)
    endpoints.append({'group': 'Streets/road_4lane/_4_strt_hi', 'geometry': len(prior_assets), 'model': model['name'], 'dependencies': list(range(len(prior_assets), len(prior_assets) + 3)), 'center': center, 'radius': radius, 'source_part_mask': PART_MASK, 'source_model_materials': [part], 'source_rootmod': SOURCE[1][0], 'source_scale': model['scale']})
    instances, proof = [], []
    visits = 0

    def walk(edge, parent_world, chain, keys):
        nonlocal visits
        visits += 1
        require(visits <= 1000000 and len(chain) < 512, 'Bounded original hierarchy exceeded')
        key = edge['name'].casefold()
        require(key not in keys, 'Original hierarchy cycle')
        target = definitions.get(key)
        local = reference.local(edge['pos'], edge['pyr'])
        world = reference.multiply(parent_world, local) if parent_world else local
        record = {'name': edge['name'], 'pos': edge['pos'], 'pyr': edge['pyr'], 'tint': target['tint'] if target else None, 'line': edge['line'], 'properties': target['properties'] if target else []}
        path = [*chain, record]
        if key == 'streets/road_4lane/4_strt':
            final = reference.multiply(world, reference.local(high['pos'], high['pyr']))
            world_center = reference.transform(final, center)
            if sum((a - b) ** 2 for a, b in zip(world_center, POSE)) > (RADIUS + radius) ** 2:
                return
            require(len(instances) < 64, 'Neighborhood instance capacity exceeded')
            parent = NO
            for source in [*path, {'name': high['name'], 'pos': high['pos'], 'pyr': high['pyr'], 'tint': road_defs['_4_strt_hi']['tint'], 'line': high['line'], 'properties': wrapper['properties']}]:
                for tokens in source['properties']:
                    if tokens[0].casefold() in ('texswap', 'replacetex'):
                        require(len(tokens) > 1 and tokens[1].casefold() not in ('street_sidewalk1', 'street_sidewalk1.tga'), 'Selected sidewalk texture override is unsupported')
                require(len(nodes) < 512, 'Neighborhood node capacity exceeded')
                nodes.append(dict(source, parent=parent, endpoint=NO))
                parent = len(nodes) - 1
            nodes[parent]['endpoint'] = endpoint
            instances.append({'node': parent, 'endpoint': endpoint, 'name': high['name'], 'world': reference.source_columns(final), 'world_center': world_center, 'radius': radius})
            for hit in ground_hits(positions, indices, part, final, reference):
                proof.append(dict(hit, node=parent, source_material_part=0, model=model['name']))
            return
        if target:
            for child in target['groups']:
                walk(child, world, path, [*keys, key])

    for ref in refs:
        walk(ref, None, [], [])
    require(instances and proof, 'Original sidewalk does not cover observed pose')
    materials = copy.deepcopy(fixture['materials'])
    materials.append({'name': part['name'], 'textures': [extra[1]['path'], extra[2]['path']], 'family': 0, 'uv_scale': [[5, 5], [1, 1]], 'const0': [1, 1, 1, 1], 'const1': [0, 0, 0, 1], 'wrap': [0, 0], 'cull_back': 1, 'alpha_ref': 20.0 / 255.0, 'diffuse': [0, 0, 0, 1], 'ambient': [0.125, 0.125, 0.125, 1]})
    all_assets = prior_assets + extra
    index = bytearray(builder.index_bytes(nodes, endpoints, all_assets))
    struct.pack_into('<I', index, 8, 2)
    endpoint_offset = struct.unpack_from('<I', index, 44)[0]
    struct.pack_into('<I', index, endpoint_offset + endpoint * 40 + 32, PART_MASK)
    bundle = builder.bundle_bytes(bytes(index), all_assets, materials)
    require(len(bundle) < 8 << 20 and sum(row['bytes'] for row in extra) == 328539, 'Neighborhood payload budget exceeded')
    destination = assets / 'neighborhood-map.bin'
    temporary = destination.with_suffix('.bin.tmp')
    with temporary.open('xb') as stream:
        stream.write(bundle)
    temporary.replace(destination)
    require((assets / 'map.bin').read_bytes() == old_raw, 'Original offline map changed')
    fixture.update({'nodes': nodes, 'endpoints': endpoints, 'assets': [{k: v for k, v in row.items() if k != 'raw'} for row in all_assets], 'materials': materials, 'instances': fixture['instances'] + instances, 'bundle': {'bytes': len(bundle), 'sha256': sha(bundle)}, 'index': {'bytes': len(index), 'sha256': sha(index)}, 'catalog': {'nodes': len(nodes), 'endpoints': len(endpoints), 'assets': len(all_assets), 'instances': len(fixture['instances']) + len(instances)}})
    fixture['offline_spawn'] = fixture['spawn']
    fixture['spawn'] = list(POSE)
    fixture['radius_queries'] = {str(int(r)): [row['node'] for row in fixture['instances'] if sum((a - b) ** 2 for a, b in zip(row['world_center'], POSE)) <= (r + row['radius']) ** 2] for r in (24.0, RADIUS)}
    return {'assets': {'neighborhood-map.bin': {'bytes': len(bundle), 'sha256': sha(bundle)}}, 'source_files': source_files, 'inputs': [{k: v for k, v in row.items() if k != 'raw'} for row in extra], 'instances': instances, 'observed_pose': POSE, 'selection_radius': RADIUS, 'raw_dependency_bytes': 328539, 'ground_proof': proof, 'source_part_mask': PART_MASK, 'fixture': fixture}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--corpus', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    for path, alias, size, digest, origin in INPUTS:
        for directory in args.corpus:
            candidate = next((p for p in (directory / alias, directory / path) if p.is_file()), None)
            if candidate:
                raw = candidate.read_bytes()
                require(len(raw) == size and sha(raw) == digest, 'Supplied neighborhood corpus differs')
                target = args.cache / alias
                if target.exists():
                    require(target.read_bytes() == raw, 'Existing neighborhood cache differs')
                else:
                    target.write_bytes(raw)
                break
    result = prepare(args.source_root, args.assets, args.cache)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('fixture', 'instances', 'ground_proof')}))


if __name__ == '__main__':
    main()
