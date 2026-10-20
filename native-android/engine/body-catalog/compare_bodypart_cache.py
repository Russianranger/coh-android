#!/usr/bin/env python3
"""Compare one real common server BodyParts.bin against its original .bp offline.

Reuses the existing Parse6 reader. No server, build, witness, lease or owner is
created. The caller supplies the actual imported-server file; a CLIENT donor is
identified as such in the report and is never relabeled server data.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex

HERE = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bodypart_text(raw):
    rows = []; active = None
    for number, line in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
        words = shlex.split(line.split('//', 1)[0])
        if not words:
            continue
        if words == ['BodyPart']:
            if active is not None: raise ValueError('Nested BodyPart at line ' + str(number))
            active = {}; rows.append(active)
        elif words == ['End']:
            if active is None: raise ValueError('Unmatched End at line ' + str(number))
            active = None
        else:
            if active is None: raise ValueError('Field outside BodyPart at line ' + str(number))
            key = words[0]
            if key not in ('Name', 'GeoName', 'TexName', 'BaseName', 'BoneCount', 'DontClear', 'InfluenceCost'):
                raise ValueError('Unrecognized original field ' + key)
            active[key] = words[1:]
    if active is not None: raise ValueError('Unclosed BodyPart')
    return rows


def cache_reader():
    spec = importlib.util.spec_from_file_location('existing_bodypart_cache_projection', HERE / 'check_body_part_loader.py')
    reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
    return reader


def read_cache(raw):
    return cache_reader().project(raw)


def dependency_timestamp_identity(raw):
    """Content comparison only: zero original Files1 timestamp words in a copy.

    Full cache framing is checked by the reused reader. No other header, path,
    schema, count, row, index or string byte is normalized; raw input is untouched.
    """
    reader = cache_reader(); reader.project(raw)
    stream = reader.Projection(raw)
    stream.take(8); stream.word(); stream.text(); stream.text()
    dependency_end = stream.end(); count = stream.word()
    normalized = bytearray(raw); timestamps = []
    for _ in range(count):
        name, _ = stream.text(); offset = stream.at; value = stream.word()
        timestamps.append({'path': name.decode('ascii'), 'offset': offset, 'bytes': 4, 'raw_timestamp': value})
        normalized[offset:offset + 4] = bytes(4)
    if stream.at != dependency_end: raise ValueError('Original Files1 extent differs')
    return {'raw_sha256': digest(raw), 'timestamp_zeroed_sha256': digest(normalized),
            'normalization': 'Zero only the original Files1 dependency timestamp words; preserve every other byte',
            'dependency_timestamps': timestamps}


def compare(cache_raw, text_raw, *, origin):
    cache = read_cache(cache_raw); text = bodypart_text(text_raw)
    expected_names = [row['Name'][0] for row in text]
    actual_names = [row['strings'][0].decode('ascii') for row in cache['rows']]
    differences = []
    if len(cache['rows']) != len(text): differences.append('count')
    for index, (binary, source) in enumerate(zip(cache['rows'], text)):
        for slot, key in ((0, 'Name'), (2, 'GeoName'), (3, 'TexName'), (4, 'BaseName')):
            actual = binary['strings'][slot].decode('ascii')
            expected = source.get(key, [''])[0]
            if actual != expected: differences.append(str(index) + ':' + key)
        # The original schema serializes BoneCount twice; both target the same
        # field. ParseBoneNames assigns index from the original ordered array.
        parts = int(source.get('BoneCount', ['0'])[0])
        if binary['words'][0] != parts or binary['words'][2] != parts:
            differences.append(str(index) + ':BoneCount')
        influence = int(source.get('InfluenceCost', ['0'])[0])
        if binary['words'][1] != influence: differences.append(str(index) + ':InfluenceCost')
        dont_clear = int(source['DontClear'][0]) if source.get('DontClear') else int('DontClear' in source)
        if binary['words'][3] & 255 != dont_clear: differences.append(str(index) + ':DontClear')
        if binary['words'][6] != index: differences.append(str(index) + ':original-index')
    result = {'schema': 'coh-bodypart-cache-text-offline-comparison-v1', 'origin': origin,
        'cache': {'bytes': len(cache_raw), 'sha256': digest(cache_raw)},
        'bodyparts_bp': {'bytes': len(text_raw), 'sha256': digest(text_raw)},
        'cache_count': len(cache['rows']), 'source_count': len(text),
        'ordered_names_match': actual_names == expected_names, 'all_source_fields_match': not differences,
        'differences': differences, 'ordered_names': actual_names,
        'cache_dependencies': [{'path': name.decode('ascii'), 'raw_time': stamp} for name, stamp in cache['deps']],
        'reader': {'path': 'native-android/engine/body-catalog/check_body_part_loader.py',
                   'sha256': digest((HERE / 'check_body_part_loader.py').read_bytes())},
        'dependency_timestamp_identity': dependency_timestamp_identity(cache_raw),
        'server_started': False, 'cache_generated': False}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-bin', type=Path, required=True)
    parser.add_argument('--bodyparts-bp', type=Path, required=True)
    parser.add_argument('--origin', default='actual-imported-server-common-cache')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = compare(args.server_bin.read_bytes(), args.bodyparts_bp.read_bytes(), origin=args.origin)
    rendered = json.dumps(result, indent=2) + '\n'
    if args.output: args.output.write_text(rendered)
    print(rendered, end='')


if __name__ == '__main__': main()
