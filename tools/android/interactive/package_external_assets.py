#!/usr/bin/env python3
"""Build independently versioned, bounded asset volumes from authenticated inputs.

Every volume carries the same manifest; each member is streamed and checked.
The manifest is also embedded in the small APK, so an imported ZIP cannot choose
its own trusted hashes. Future APKs can retain this manifest unchanged.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import zipfile

FORMAT = 1
PACK_ID, VERSION = 'coh-assets', '1.0.0'
MANIFEST = 'asset-pack-manifest.json'
MAX_VOLUME_BYTES = 2 * 1024**3 - 1
MAX_MEMBERS = 257
BASE_FILES = frozenset({'atlas/atlas-text.zip', 'atlas/atlas-assets-index.tsv', 'atlas/atlas-text-index.tsv',
    *('runtime/'+name for name in ('client-visual-assets.zip','client-visual-manifest.json',
        'atlas-world-supplement.zip','atlas-world-supplement-manifest.json',
        'server-animations.pigg','server-animation-manifest.json','server-caches.zip','server-cache-manifest.json',
        'client-caches.zip','atlas-beacons.zip','atlas-beacon-manifest.json',
        'character-avatar-defaults.zip','character-avatar-defaults-manifest.json'))})
REFERENCE_FILE = 'atlas/atlas-assets.zip'
ZONE_FILES = frozenset('runtime/'+name for name in ('zones-world-supplement.zip','zones-world-supplement-manifest.json',
    'kings-row-beacons.zip','kings-row-beacon-manifest.json'))
AUDIO_FILES = frozenset('runtime/'+name for name in ('zones-audio-supplement.zip','zones-audio-supplement-manifest.json'))


def require(condition, message):
    if not condition: raise ValueError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode('ascii')


def file_pin(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Regular asset input required: '+path.name)
    with path.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'bytes':path.stat().st_size, 'sha256':digest}


def safe_name(name):
    require(type(name) is str and re.fullmatch(r'(?:runtime|atlas)/[A-Za-z0-9_.\-/]+',name)
        and all(part not in ('','.', '..') for part in name.split('/')) and len(name) < 240,
        'Unsafe asset path')
    return name


def validate_manifest(manifest):
    require(type(manifest) is dict and manifest.get('format') == FORMAT and type(manifest.get('format')) is int
        and manifest.get('id') == PACK_ID and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',str(manifest.get('version',''))),
        'Unsupported asset manifest')
    files, volumes = manifest.get('files'), manifest.get('volumes')
    require(type(files) is dict and 0 < len(files) < MAX_MEMBERS and type(volumes) is dict and 0 < len(volumes) <= 8,
        'Bounded files and volume inventory required')
    for name, expected in files.items():
        safe_name(name)
        require(type(expected) is dict and set(expected) == {'bytes','sha256'}
            and type(expected['bytes']) is int and 0 < expected['bytes'] < MAX_VOLUME_BYTES
            and type(expected['sha256']) is str and re.fullmatch('[0-9a-f]{64}',expected['sha256']), 'Invalid asset pin')
    require(len({name.casefold() for name in files}) == len(files), 'Case-colliding asset identity')
    membership = []
    for volume, names in volumes.items():
        require(re.fullmatch('[a-z][a-z0-9-]{0,31}',volume) and type(names) is list and names == sorted(set(names))
            and names and set(names) <= set(files), 'Invalid volume inventory')
        require(sum(files[name]['bytes'] for name in names)+65536 < MAX_VOLUME_BYTES, 'Volume exceeds transport size bound')
        membership += names
    require(len(membership) == len(set(membership)) and set(membership) == set(files), 'Volumes must partition every asset exactly once')
    require(len(encoded(manifest)) <= 262144, 'Asset manifest exceeds Android bound')
    return manifest


def make_manifest(inputs, volumes, *, version=VERSION):
    return validate_manifest({'format':FORMAT, 'id':PACK_ID, 'version':version,
        'files':{safe_name(name):file_pin(path) for name,path in sorted(inputs.items())},
        'volumes':{name:sorted(members) for name,members in sorted(volumes.items())}})


def zip_info(name, size):
    item = zipfile.ZipInfo(name, (1980,1,1,0,0,0)); item.create_system = 3
    item.external_attr = (stat.S_IFREG|0o644) << 16
    item.compress_type = zipfile.ZIP_STORED; item.file_size = size
    return item


def volume_filename(version, volume):
    return 'COH-Assets-'+version+'-'+volume.title()+'.zip'


def write_volume(path, manifest, volume, inputs):
    validate_manifest(manifest); path = Path(path)
    require(not path.exists() and not path.is_symlink(), 'Fresh asset output required')
    names = manifest['volumes'][volume]; raw = encoded(manifest)
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with zipfile.ZipFile(path,'x',allowZip64=False) as archive:
            archive.writestr(zip_info(MANIFEST,len(raw)),raw)
            for name in names:
                expected = manifest['files'][name]
                require(file_pin(inputs[name]) == expected, 'Asset changed after manifest: '+name)
                with Path(inputs[name]).open('rb') as source, archive.open(zip_info('payloads/'+name,expected['bytes']),'w') as target:
                    shutil.copyfileobj(source,target,1024*1024)
        require(path.stat().st_size < MAX_VOLUME_BYTES,'Asset volume exceeded GitHub transport bound')
        verify_volume(path,manifest,volume)
    except Exception:
        path.unlink(missing_ok=True); raise
    return file_pin(path)


def verify_volume(path, manifest, volume=None):
    validate_manifest(manifest); require(Path(path).stat().st_size < MAX_VOLUME_BYTES,'Oversized asset archive')
    raw = encoded(manifest)
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist(); names = [entry.filename for entry in infos]
        require(0 < len(infos) <= MAX_MEMBERS and len(names) == len(set(names)) and names[0] == MANIFEST,
            'Duplicate or unbounded asset inventory')
        require(archive.read(MANIFEST) == raw, 'Imported manifest differs from APK trust root')
        matching = [name for name,members in manifest['volumes'].items()
            if names == [MANIFEST]+['payloads/'+member for member in members]]
        require(len(matching) == 1 and (volume is None or matching == [volume]), 'Archive must contain one complete exact volume')
        for entry in infos:
            require(entry.create_system == 3 and stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFREG
                and not entry.is_dir() and not entry.flag_bits & 1 and entry.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED),
                'Only regular unencrypted asset members allowed')
            expected = {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} if entry.filename == MANIFEST else manifest['files'][entry.filename[9:]]
            require(entry.file_size == expected['bytes'], 'Asset size differs')
            digest = hashlib.sha256(); received = 0
            with archive.open(entry) as stream:
                while block := stream.read(1024*1024):
                    received += len(block); require(received <= expected['bytes'], 'Asset exceeded bound'); digest.update(block)
            require(received == expected['bytes'] and digest.hexdigest() == expected['sha256'],'Asset digest differs')
    return matching[0]


def stage_donor_assets(apk, donor_payloads, output):
    """Extract only independently authenticated payloads; never materialize a ZIP in heap."""
    output = Path(output); output.mkdir(parents=True,exist_ok=False); result = {}
    with zipfile.ZipFile(apk) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate donor member')
        for name in sorted(BASE_FILES):
            expected = donor_payloads['assets/'+name]; destination = output/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            with archive.open('assets/'+name) as source,destination.open('xb') as target: shutil.copyfileobj(source,target,1024*1024)
            require(file_pin(destination) == expected, 'Donor asset differs: '+name)
            result[name] = destination
    return result


def build(inputs, output, *, zones, audio, version=VERSION):
    require(set(zones) == ZONE_FILES and set(audio) == AUDIO_FILES, 'Complete frozen Zones and Audio groups required')
    volumes = {'base':sorted(BASE_FILES), 'reference':[REFERENCE_FILE], 'zones':sorted(zones), 'audio':sorted(audio)}
    manifest = make_manifest(inputs,volumes,version=version); output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    (output/MANIFEST).write_bytes(encoded(manifest)); receipts = {}
    for volume in sorted(volumes):
        path = output/volume_filename(version,volume)
        receipts[path.name] = write_volume(path,manifest,volume,inputs)
        path.with_suffix('.zip.sha256').write_text(receipts[path.name]['sha256']+'  '+path.name+'\n')
    report = {'format':1,'asset_pack_version':version,'asset_manifest':file_pin(output/MANIFEST),'volumes':receipts,
        'all_payloads_streamed_and_verified':True,'all_volumes_required_for_fresh_install':True,
        'existing_pack_reusable_by_future_apk_if_manifest_unchanged':True}
    (output/'asset-pack-build-report.json').write_bytes(encoded(report))
    return manifest,report


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True)
    args = parser.parse_args(); print(verify_volume(args.archive,json.loads(args.manifest.read_bytes())))


if __name__ == '__main__': main()
