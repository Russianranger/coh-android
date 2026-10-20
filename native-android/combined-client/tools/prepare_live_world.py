#!/usr/bin/env python3
"""Write every authentic admitted Atlas road placement, without a build-time pose.

The native reader streams this compact index and keeps only the nearby window.
Original GEO/textures are loaded from the existing imported archives at runtime.
Other source models/materials remain outside this deliberately bounded subset.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json, math, struct

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result

def prepare(root, assets, cache):
    native = root / 'native-android'
    source = module('live_neighborhood_sources', native / 'combined-client/tools/prepare_neighborhood.py')
    builder = module('live_original_groups', native / 'tools/map_fixture/prepare.py')
    reference = module('live_original_matrices', native / 'tools/world_fixture/world_reference.py')
    legacy = module('live_original_geo', native / 'tools/walkable_fixture/prepare.py')
    require = source.require
    for path, size, digest in source.SOURCE:
        raw = (root / path).read_bytes()
        require(len(raw) == size and source.sha(raw) == digest, 'Original placement source differs: ' + path)
    bodies = source.payloads(root, cache)
    data, models = legacy.legacy_records(bodies[0]['raw'])
    model = next(row for row in models if row['name'] == '_4_strt_hi__roadhi')
    require(model['materials'][0] == {'name': 'street_sidewalk1.tga', 'triangle_count': 12, 'first_triangle': 0}, 'Original source partition differs')
    positions = legacy.geo.accepted.decode_delta(legacy.stream(data, model, 1), model['vertex_count'], 3, True)
    indices = legacy.geo.accepted.decode_delta(legacy.stream(data, model, 0), model['triangle_count'], 3, False)
    used = set(indices[:36]); lo = [min(positions[i * 3 + j] for i in used) for j in range(3)]; hi = [max(positions[i * 3 + j] for i in used) for j in range(3)]
    center = [reference.f32((a + b) * .5) for a, b in zip(lo, hi)]
    radius = reference.f32(math.sqrt(sum(max(abs(a - c), abs(b - c)) ** 2 for a, b, c in zip(lo, hi, center))))
    definitions, refs, _ = builder.parse_groups((root / source.SOURCE[0][0]).read_text())
    road, _, _ = builder.parse_groups((root / source.SOURCE[1][0]).read_text())
    wrapper = road['4_strt']; high = next(row for row in wrapper['groups'] if row['name'] == '_4_strt_hi')
    require(high['pos'] == [0., -.000366, 0.] and high['pyr'] == [0., 0., 0.], 'Original high-child transform differs')
    rows = []; visits = 0
    def walk(edge, parent, inherited, chain, properties):
        nonlocal visits
        visits += 1; key = edge['name'].casefold()
        require(visits <= 1000000 and len(chain) < 512 and key not in chain, 'Original hierarchy size/cycle bound')
        target = definitions.get(key); local = reference.local(edge['pos'], edge['pyr'])
        world = reference.multiply(parent, local) if parent else local
        tint = target['tint'] if target and target['tint'] is not None else inherited
        props = properties + (target['properties'] if target else [])
        if key == 'streets/road_4lane/4_strt':
            for tokens in props + wrapper['properties'] + road['_4_strt_hi']['properties']:
                if tokens[0].casefold() in ('texswap', 'replacetex'):
                    require(len(tokens) > 1 and tokens[1].casefold() not in ('street_sidewalk1', 'street_sidewalk1.tga'), 'Unsupported original sidewalk override')
            final = reference.multiply(world, reference.local(high['pos'], high['pyr']))
            effective = road['_4_strt_hi']['tint'] or wrapper['tint'] or tint
            effective = [reference.f32(v * reference.f32(1. / 255.)) for v in effective] if effective else [1., 1., 1., 0., 0., 0.]
            bounds = reference.transform(final, center)
            require(len(rows) < 65536 and all(math.isfinite(v) and abs(v) <= 1e7 for v in reference.source_columns(final) + bounds), 'Placement bound')
            rows.append({'node': len(rows), 'endpoint': 3, 'world': reference.source_columns(final), 'tint': effective, 'world_center': bounds, 'radius': radius})
            return
        if target:
            for child in target['groups']: walk(child, world, tint, [*chain, key], props)
    for ref in refs: walk(ref, None, None, [], [])
    require(rows, 'No original admitted road occurrences')
    total = 64 + 96 * len(rows)
    raw = struct.pack('<8s6I32s', b'COHLIVE1', 1, 64, total, len(rows), 96, 0, bytes.fromhex(source.SOURCE[0][2]))
    raw += b''.join(struct.pack('<2I22f', row['node'], row['endpoint'], *row['world'], *row['tint'], *row['world_center'], row['radius']) for row in rows)
    require(len(raw) == total and total <= 64 + 96 * 65536, 'Live source index bound')
    assets.mkdir(parents=True, exist_ok=True); target = assets / 'live-world.bin'; temporary = target.with_suffix('.bin.tmp')
    with temporary.open('xb') as stream: stream.write(raw)
    temporary.replace(target)
    return {'assets': {'live-world.bin': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}, 'source_files': [{'path': p, 'bytes': n, 'sha256': h} for p, n, h in source.SOURCE], 'source_visits': visits, 'instances': rows, 'source_part_mask': 1, 'model': model['name'], 'inputs': [{k: v for k, v in row.items() if k != 'raw'} for row in bodies], 'scope': 'All source occurrences of admitted high-road sidewalk partition; no pose pruning, full-world/model admission or server generation claim'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True); parser.add_argument('--assets', type=Path, required=True); parser.add_argument('--cache', type=Path, required=True); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); result = prepare(args.source_root.resolve(), args.assets, args.cache)
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'instances'}))
if __name__ == '__main__': main()
