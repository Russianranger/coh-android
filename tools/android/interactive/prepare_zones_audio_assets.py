#!/usr/bin/env python3
"""Complete original audio from the 15 standalone sound archives.

The preceding frozen Zones volume already owns 4,042 stage-archive sounds.
This append preserves those exact resources and fills the 2,177 remaining
original names. Original Ogg and DEFLATE bytes are never recompressed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path, PurePosixPath

import prepare_zones_world_assets as zones

ROOT = zones.ROOT
ARCHIVE = 'zones-audio-supplement.zip'
MANIFEST = 'zones-audio-supplement-manifest.json'
PROVENANCE = 'zones-audio-supplement-provenance.json'
METADATA = 'zones-audio-metadata.json'
VERSION = '1.0.0'
SCOPE = 'coh_all_zones_original_audio_supplement_v1'
ARCHIVE_PIN = {'bytes': 847802311, 'sha256': '3bbc5773f50593e5b2e667c7e01e7f971c3a6a65137f149e0823423798d7b2a7'}
MANIFEST_PIN = {'bytes': 316144, 'sha256': 'c819e1af90c1f29a64eac57a20b0bdfb61a50bd9791206ab1ce18c05d210ec6f'}
PROVENANCE_PIN = {'bytes': 2388947, 'sha256': 'b55c46cbe09d8044c955ec3a2e5bcfeaa5aea36e37ca088363a308c5763aad95'}
METADATA_PIN = {'bytes': 4972, 'sha256': '729035bea0e65fc9585c084efbb67dea0ffc2546f630dc01c28811173e95c78b'}
require, canonical, pin = zones.require, zones.canonical, zones.pin


def plan(root, cache):
    metadata_path = Path(root) / 'assets' / METADATA
    require(pin(metadata_path) == METADATA_PIN, 'Frozen audio metadata identity differs')
    identities = json.loads(metadata_path.read_bytes())
    require(len(identities) == 15 and identities == sorted(identities, key=lambda row: row['archive'].casefold())
            and all(row['archive'].startswith('sound') for row in identities), 'Standalone audio catalog differs')
    original = {}
    for identity in identities:
        original.update(zones.all_metadata(identity, cache)[0])
    baseline = zones.frozen_manifest(root)
    selected = {name: row for name, row in original.items() if name not in baseline['files']}
    require(len(selected) == 2177 and all(name.startswith('data/sound/ogg/') and name.endswith('.ogg')
            for name in selected), 'Frozen standalone original audio inventory differs')
    sounds = defaultdict(list)
    for name in set(baseline['files']) | set(selected):
        if name.endswith('.ogg'):
            require(len(name.removeprefix('data/')) + 1 < 80, 'Original sound exceeds native path buffer')
            sounds[PurePosixPath(name).stem].append(name)
    require(len(sounds) == 6219 and all(len(rows) == 1 for rows in sounds.values()),
            'Combined original sound basenames conflict')
    return selected, {'format': 1, 'scope': SCOPE, 'version': VERSION,
        'source_commit': zones.kings.SOURCE, 'data_commit': zones.kings.DATA,
        'missing_only': True, 'retained_resources_preserved': True,
        'donor_generated_caches_installed': False,
        'base_zones_archive_pin': zones.ARCHIVE_PIN, 'base_zones_manifest_pin': zones.MANIFEST_PIN,
        'frozen_metadata_archives': identities,
        'combined_native_sound_inventory': {'unique_names': len(sounds), 'duplicate_basename_count': 0,
            'native_80_byte_path_bound_verified': True, 'prior_zone_sounds_preserved': 4042,
            'additional_original_sounds': len(selected),
            'rule_source': 'upstream/ouroboros/Game/src/sound/sound.c:soundLoadCallback'},
        'original_payloads_verified': True, 'physical_playback_verified': False,
        'full_dynamic_source_dependency_closure': False}


def prepare(root, metadata_cache, payload_cache, output, workers=8):
    require(not output.exists() and not output.is_symlink(), 'Preserve existing audio output')
    output.mkdir(parents=True); payload_cache.mkdir(parents=True, exist_ok=True)
    selected, document = plan(root, metadata_cache)
    groups, gap_bytes = zones.sweep.payload_groups(selected)
    print(json.dumps({'original_audio_files': len(selected), 'groups': len(groups), 'gap_bytes': gap_bytes}), flush=True)
    records = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(zones.materialize, group, payload_cache) for group in groups]
        for index, future in enumerate(as_completed(futures), 1):
            records.update(future.result())
            if index % 10 == 0 or index == len(groups):
                print(json.dumps({'groups_completed': index, 'groups_total': len(groups),
                                  'audio_files_verified': len(records)}), flush=True)
    require(set(records) == set(selected), 'Original standalone audio materialization incomplete')
    def members():
        for name, row in sorted(records.items()):
            stored = (payload_cache / hashlib.sha256(name.encode()).hexdigest()).read_bytes()
            yield name, *zones.donor.decode_entry(stored, row)
    zones.donor.write_zip_members(output / ARCHIVE, members())
    files = {name: {key: row[key] for key in ('bytes', 'sha256')} for name, row in sorted(records.items())}
    provenance = {'format': 1, 'scope': SCOPE, 'version': VERSION, 'entries': dict(sorted(records.items()))}
    (output / PROVENANCE).write_bytes(canonical(provenance) + b'\n')
    document.update({'archive': {'filename': ARCHIVE, **pin(output / ARCHIVE)}, 'files': files,
        'file_count': len(files), 'payload_bytes': sum(row['bytes'] for row in files.values()),
        'files_sha256': hashlib.sha256(canonical(files)).hexdigest(),
        'provenance': {'filename': PROVENANCE, **pin(output / PROVENANCE)}})
    verification = zones.verify_archive(output / ARCHIVE, document)
    (output / MANIFEST).write_bytes(canonical(document) + b'\n')
    require(pin(output / ARCHIVE) == ARCHIVE_PIN and pin(output / MANIFEST) == MANIFEST_PIN
            and pin(output / PROVENANCE) == PROVENANCE_PIN, 'Rebuilt Audio1.0.0 identities differ')
    print(json.dumps({'archive': document['archive'], 'verification': verification}), flush=True)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--metadata-cache', type=Path, required=True)
    parser.add_argument('--payload-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=8)
    args = parser.parse_args()
    require(1 <= args.workers <= 12, 'Audio worker bound differs')
    prepare(args.root, args.metadata_cache, args.payload_cache, args.output, args.workers)


if __name__ == '__main__':
    main()
