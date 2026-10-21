#!/usr/bin/env python3
"""Recover only requested authentic costume bodies for a bounded host proof.

Android resolves the same paths from its existing accepted imported ZIP FDs.
The optional host transport ZIP is generated metadata around original bodies,
not a replacement import receipt or a complete archive hash qualification.
"""
from pathlib import Path, PurePosixPath
import argparse
import codecs
import hashlib
import importlib.util
import json
import os
import shutil
import struct
import subprocess
import tempfile
import urllib.request
import zipfile
import zlib
from acquire_received_sources import NoRedirect, file_hash, fetch
from imported_archive import BODY_LIMIT, CHUNK, safe_path
from source_manifest_records import selected_records
from zone_source_index import zone_records, selected_provenance, PROVENANCE_PIN
from costume_texture_inventory import texture_inventory, SOURCES
from pigg_source_index import PiggSourceIndex

PROVENANCE_URL = 'https://github.com/Russianranger/coh-android/releases/download/coh-assets-v1.0.0/zones-world-supplement-provenance.json'
COMPOSITE_SOURCES = {
    'x_enforcer_glove_01_mask': 'shader_villain_enforcer.txt',
    'x_fullhelm_robot_01': 'shader_villain_male_robot.txt',
    'x_gear_pads': 'shader_villain_gear_pads.txt',
}


def repository_bytes(root, name, limit):
    source = root / name
    if source.is_symlink():
        raise ValueError('Original source file is a symlink')
    raw = source.read_bytes() if source.is_file() else subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=root)
    if not 0 < len(raw) <= limit:
        raise ValueError('Original selected source file exceeds its bound')
    return raw


def selected_composites(root, cache, names):
    """Use the existing native-generation-aware TexOpt parser, not a new shader.

    Original source text and surviving edges are delivered for the renderer to
    interpret. Having the leaves does not establish complete material drawing.
    """
    parser_path = 'tools/android/interactive/client_visual_tricks.py'
    raw = repository_bytes(root, parser_path, 65536)
    target = cache / 'client_visual_tricks.py'
    target.write_bytes(raw)
    spec = importlib.util.spec_from_file_location('coh_original_trick_discovery', target)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    definitions, sources, leaves = {}, {}, set()
    for key in sorted(set(name.casefold() for name in names) & set(COMPOSITE_SOURCES)):
        path = 'upstream/i24/data/tricks/v_shaders/villains/male/' + COMPOSITE_SOURCES[key]
        body = repository_bytes(root, path, 65536)
        matches = [row for row in parser.parse_texture_tricks_text(body.decode('utf-8'), path)
                   if parser.trick_name(row['name']).casefold() == key]
        if len(matches) != 1 or not matches[0]['composite_generation']['composite_alias_can_be_created']:
            raise ValueError('Original selected composite definition differs')
        definitions[key] = matches[0]
        sources[path] = body
        leaves.update(parser.texture_stem(edge['alias']) for edge in matches[0]['edges'])
    if len(leaves) > 64:
        raise ValueError('Original composite dependencies exceed bounded requests')
    return definitions, sources, leaves


def selected_texture_headers(bodies, files):
    """Preserve the original Basic key, independently of filename discovery.

    texFillInBind reads the cached name; texLoadHeader rejects a filename/key
    mismatch. These are cached-header observations, not effective TexOpt flags.
    """
    result = {}
    for name in files:
        if not name.endswith('.texture'):
            continue
        with (bodies / name).open('rb') as source:
            raw = source.read(1056)
        if len(raw) < 32:
            raise ValueError('Selected original texture header is truncated')
        header, payload, width, height = struct.unpack_from('<IIII', raw)
        if not 32 < header <= min(1056, len(raw)) or payload > files[name]['bytes'] - header or not 0 < width <= 16384 or not 0 < height <= 16384:
            raise ValueError('Selected original texture header bounds differ')
        original, separator, _ = raw[32:header].partition(b'\0')
        if not separator:
            raise ValueError('Selected original cached texture name is unterminated')
        original = original.decode('ascii')
        if (not original.casefold().startswith('texture_library/')
                or PurePosixPath(original).stem.casefold() != PurePosixPath(name).stem.casefold()):
            raise ValueError('Selected original cached texture key differs from its filename')
        result[name] = {'original_name': original, 'basic_key': PurePosixPath(original).stem.casefold(),
                        'header_bytes': header, 'width': width, 'height': height,
                        'effective_sampler_or_material_validated': False}
    return result


def query_plan(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1 << 20:
        raise ValueError('Functional resource plan exceeds its bounded input')
    plan = json.loads(path.read_bytes())
    if (set(plan) != {'schema', 'bodytype', 'texture_prefix', 'parts', 'morph_paths'}
            or plan.get('schema') != 'coh-huge-source-query-v1' or plan.get('bodytype') != 4
            or plan.get('texture_prefix') != 'SH' or not 0 < len(plan['parts']) <= 60):
        raise ValueError('Functional Huge resource plan differs')
    geometry, names = set(plan['morph_paths']), set()
    for part in plan['parts']:
        if set(part) != {'path', 'model', 'textures', 'texture_explicit'}:
            raise ValueError('Resource plan contains fields outside source queries')
        geometry.add(part['path'])
        if len(part['textures']) != 2 or len(part['texture_explicit']) != 2:
            raise ValueError('Original part texture shape differs')
        for name, explicit in zip(part['textures'], part['texture_explicit']):
            if not name or '/' in name or '\\' in name or len(name) > 255:
                raise ValueError('Original texture basename differs')
            names.add(name)
            if not explicit:
                names.add('SH_' + name)
    if len(geometry) + len(names) > 64 or any(not safe_path(name) or not name.endswith('.geo') for name in geometry):
        raise ValueError('Functional selected source request exceeds 64 rows')
    return plan, geometry, names


def source_indexes(root, cache):
    directory = cache / 'source-indexes'
    directory.mkdir(parents=True, exist_ok=True)
    for name, *_ in SOURCES + [('client-appearance-manifest.json',)]:
        source, target = root / 'assets' / name, directory / name
        if source.is_file():
            if not target.exists():
                shutil.copyfile(source, target)
        elif not target.exists():
            # Sparse host checkouts may omit the existing pinned source blobs.
            # This is a local Git object read, never an asset network download.
            with target.open('xb') as output:
                subprocess.run(['git', 'show', 'HEAD:assets/' + name], cwd=root, stdout=output, check=True)
    return directory


def provenance_chunks():
    request = urllib.request.Request(PROVENANCE_URL, headers={'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.status != 200 or response.headers.get('Content-Length') not in (None, str(PROVENANCE_PIN['bytes'])) or response.headers.get('Content-Encoding', 'identity') != 'identity':
            raise ValueError('Pinned JSON source metadata envelope differs; body not read')
        digest, total = hashlib.sha256(), 0
        utf8 = codecs.getincrementaldecoder('utf-8')('strict')
        while True:
            raw = response.read(min(CHUNK, PROVENANCE_PIN['bytes'] - total + 1))
            if not raw:
                break
            total += len(raw)
            if total > PROVENANCE_PIN['bytes']:
                raise ValueError('Pinned JSON metadata overrun')
            digest.update(raw)
            yield utf8.decode(raw)
        end = utf8.decode(b'', final=True)
        if end:
            yield end
        if total != PROVENANCE_PIN['bytes'] or digest.hexdigest() != PROVENANCE_PIN['sha256']:
            raise ValueError('Pinned JSON source metadata SHA differs')


def metadata_range(identity, start, stored, decoded, sha256, path, *, compressed=False, stored_sha256=None, md5=None, cached_header=None, opener=None):
    """One exact original span, with independently pinned decoded identity.

    A compressed hash absent from the original metadata is reported as observed;
    it is never promoted to a previously authenticated compressed-byte pin.
    """
    if not 0 < stored <= BODY_LIMIT or not 0 < decoded <= BODY_LIMIT or start < 0 or stored > identity['source_archive_bytes'] - start:
        raise ValueError('Original selected range exceeds existing body/metadata cap')
    path = Path(path)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.stat().st_size != decoded or file_hash(path) != sha256:
            raise ValueError('Existing original body differs')
        return {'bytes': decoded, 'sha256': sha256, 'compressed_read': 0, 'reused': True}
    request = urllib.request.Request('https://dists.thunderspy.org/piggs/' + identity['archive'], headers={
        'Range': f'bytes={start}-{start + stored - 1}', 'If-Range': identity['source_etag'],
        'Accept-Encoding': 'identity', 'User-Agent': 'CoH-selected-source/1'})
    stage = None
    try:
        with (opener or urllib.request.build_opener(NoRedirect()).open)(request, timeout=30) as response:
            if (response.status != 206 or response.headers.get('Content-Range') != f"bytes {start}-{start + stored - 1}/{identity['source_archive_bytes']}"
                    or response.headers.get('ETag') != identity['source_etag']
                    or response.headers.get('Content-Length') != str(stored)
                    or response.headers.get('Content-Encoding', 'identity') != 'identity'):
                raise ValueError('Pinned original range headers differ; body not read')
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.part', dir=path.parent)
            stage = Path(temporary)
            encoded_hash, decoded_hash, decoded_md5 = hashlib.sha256(), hashlib.sha256(), hashlib.md5()
            decoder = zlib.decompressobj() if compressed else None
            received, written = 0, 0
            with os.fdopen(fd, 'wb') as output:
                def emit(raw):
                    nonlocal written
                    if len(raw) > decoded - written:
                        raise ValueError('Original decoded body overrun')
                    output.write(raw)
                    decoded_hash.update(raw)
                    decoded_md5.update(raw)
                    written += len(raw)

                while received < stored:
                    wanted = min(CHUNK, stored - received)
                    raw = response.read(wanted)
                    if not raw or len(raw) > wanted:
                        raise ValueError('Original compressed body truncated/overrun')
                    received += len(raw)
                    encoded_hash.update(raw)
                    if decoder is None:
                        emit(raw)
                    else:
                        while raw:
                            before = len(raw)
                            body = decoder.decompress(raw, CHUNK)
                            emit(body)
                            raw = decoder.unconsumed_tail
                            if decoder.eof:
                                if decoder.unused_data or raw or received != stored:
                                    raise ValueError('Original deflate stream has trailing bytes')
                                break
                            if not body and len(raw) == before:
                                raise ValueError('Original deflate stream stalled')
                if response.read(1):
                    raise ValueError('Original HTTP range overrun')
                if decoder is not None:
                    while not decoder.eof:
                        raw = decoder.decompress(b'', CHUNK)
                        if not raw and not decoder.eof:
                            raise ValueError('Original deflate stream ended early')
                        emit(raw)
            if (written != decoded or decoded_hash.hexdigest() != sha256
                    or stored_sha256 is not None and encoded_hash.hexdigest() != stored_sha256
                    or md5 is not None and decoded_md5.hexdigest() != md5):
                raise ValueError('Independent original body identity differs')
            if cached_header is not None:
                with stage.open('rb') as source:
                    digest, left = hashlib.sha256(), cached_header['bytes']
                    while left:
                        raw = source.read(min(CHUNK, left))
                        if not raw:
                            raise ValueError('Original cached header truncated')
                        digest.update(raw)
                        left -= len(raw)
                if digest.hexdigest() != cached_header['sha256']:
                    raise ValueError('Original cached header differs')
            os.rename(stage, path)
            stage = None
            return {'bytes': written, 'sha256': decoded_hash.hexdigest(), 'compressed_read': received,
                    'compressed_sha256': encoded_hash.hexdigest(), 'compressed_sha256_independently_pinned': stored_sha256 is not None}
    finally:
        if stage is not None:
            stage.unlink(missing_ok=True)


def recover(root, plan_path, cache, output):
    plan, geometry, names = query_plan(plan_path)
    if output.exists() or output.is_symlink():
        raise ValueError('Choose a new functional source output directory')
    cache.mkdir(parents=True, exist_ok=True)
    indexes = source_indexes(root, cache)
    composites, trick_sources, leaves = selected_composites(root, cache, names)
    inventory = texture_inventory(indexes, sorted(names | leaves))
    required = {name.casefold(): None for name in geometry}
    for part in plan['parts']:
        for name, explicit in zip(part['textures'], part['texture_explicit']):
            key = name.casefold()
            if not explicit and inventory['lookup']['sh_' + key]['present']:
                key = 'sh_' + key
            if key == 'none':
                continue
            if key in composites:
                # Composite aliases are not Basic texture file basenames.
                continue
            choices = inventory['lookup'][key]['paths']
            if len(choices) != 1:
                raise ValueError('Original texture basename absent/ambiguous: ' + key)
            required[choices[0]] = inventory['files'][choices[0]]['pin']
    for key in leaves:
        choices = inventory['lookup'][key]['paths']
        if len(choices) != 1:
            raise ValueError('Original composite Basic dependency absent/ambiguous: ' + key)
        required[choices[0]] = inventory['files'][choices[0]]['pin']
    if len(required) > 64:
        raise ValueError('Selected source owner exceeds 64 body records')
    zones = zone_records(indexes / 'zones-world-supplement-manifest.json', paths=list(required))['files']
    base = {name: row for name, row in inventory['files'].items() if name in required and row['original_input'] is not None}
    ancestor_names = sorted(set(required) - set(zones) - set(base))
    records = selected_records(indexes / 'client-appearance-manifest.json', ancestor_names) if ancestor_names else {}
    if zones:
        records.update(selected_provenance(provenance_chunks(), list(zones)))
    for name, record in records.items():
        expected = zones.get(name) or required.get(name)
        if expected is not None and (record['bytes'] != expected['bytes'] or record['sha256'] != expected['sha256']):
            raise ValueError('Selected source provenance conflicts with its accepted file pin')
    derived = {}
    donor_names = sorted({row['original_input']['donor'] for row in base.values()})
    identities = zone_records(indexes / 'zones-world-supplement-manifest.json', metadata_archives=donor_names)['metadata_archives'] if donor_names else {}
    for donor, identity in identities.items():
        metadata = cache / 'metadata' / donor
        metadata_range(identity, 0, identity['source_metadata_bytes'], identity['source_metadata_bytes'], identity['source_metadata_sha256'], metadata,
                       stored_sha256=identity['source_metadata_sha256'])
        fd = os.open(metadata, os.O_RDONLY | os.O_CLOEXEC)
        try:
            with PiggSourceIndex(fd, identity) as source:
                desired = {name: row['pin'] for name, row in base.items() if row['original_input']['donor'] == donor}
                found = source.rows(desired)
                if set(found) != set(desired):
                    raise ValueError('Original baseline texture missing from its pinned donor metadata')
                derived.update(found)
        finally:
            os.close(fd)
    if set(records) | set(derived) != set(required) or sum(row['stored_bytes'] for row in [*records.values(), *derived.values()]) > BODY_LIMIT:
        raise ValueError('Selected original body set or compressed aggregate differs')
    bodies = cache / 'bodies'
    fetch(records, bodies, progress=lambda row: print(json.dumps(row), flush=True))
    for name, row in derived.items():
        identity = identities[row['source_archive']]
        result = metadata_range(identity, row['offset'], row['stored_bytes'], row['bytes'], row['sha256'], bodies / name,
                    compressed=row['compressed'], md5=row['md5_table'],
                    cached_header={'bytes': row['cached_header_bytes'], 'sha256': row['cached_header_sha256']})
        print(json.dumps({'path': name, **result}), flush=True)
    files = {name: {'bytes': row['bytes'], 'sha256': row['sha256']} for name, row in {**records, **derived}.items()}
    headers = selected_texture_headers(bodies, files)
    index = {'files': files, 'texture_namespace': inventory['lookup'], 'texture_probe_complete': True,
             'texture_headers': headers,
             'texture_inventory_scope': inventory['scope'], 'source_indexes': inventory['source_indexes'],
             'scope': 'Generated host transport of original verified selected bodies, not original ZIP or Thor execution proof',
             'bodytype': plan['bodytype'], 'resource_plan': plan,
             'composites': composites,
             'original_trick_sources': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                                        for name, raw in trick_sources.items()},
             'material_runtime_rendering_validated': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='coh-selected-sources-', dir=output.parent) as temporary:
        stage = Path(temporary)
        with zipfile.ZipFile(stage / 'source-format.zip', 'x', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            for name in sorted(files):
                archive.write(bodies / name, name)
        (stage / 'source-index.json').write_text(json.dumps(index, indent=2) + '\n')
        for name, raw in trick_sources.items():
            destination = stage / 'original-tricks' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        os.rename(stage, output)
    return {'files': len(files), 'decoded_source_bytes': sum(pin['bytes'] for pin in files.values()), 'output': str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--resource-plan', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(recover(args.source_root, args.resource_plan, args.cache, args.output)))


if __name__ == '__main__':
    main()
