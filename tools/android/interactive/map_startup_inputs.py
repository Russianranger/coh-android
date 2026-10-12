#!/usr/bin/env python3
"""Stage exact published .31/native animation inputs without rebuilding donors."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'android/guest'))
import server_fx_catalog as fx

RELEASE = 'https://github.com/Russianranger/coh-android/releases/download/'
DONOR = {'bytes': 41203812, 'sha256': 'e56df1bcf2210aff131ba80189b1b2dee760f27066e3ee26e09c5fea1654ad80'}
BASE = {'bytes': 1630092780, 'sha256': '6d6e3304e48b89f8fdb218754a57380b3108140ef31bddb30f699ebcf28c2e3d'}
INPUTS = {
    'server-animations.pigg': {'bytes': 97084456, 'sha256': '465d69a266f2b07afd800b8a7bd3f5e63fa16a24955391f826264d7f8d3a968b'},
    'server-animation-manifest.json': {'bytes': 1005794, 'sha256': '8f752dceeffa632287602176f26722c3129fcdc9941709793d8b26d22151859f'},
    'client-caches.zip': {'bytes': 27071659, 'sha256': '5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'},
}


def pin(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError('Regular native input required: ' + path.name)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def checked(path, expected):
    if pin(path) != expected:
        raise ValueError('Exact native input differs: ' + Path(path).name)


def download(url, target, expected):
    target = Path(target)
    if target.exists():
        checked(target, expected)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_suffix(target.suffix + '.partial')
    try:
        with urllib.request.urlopen(url, timeout=120) as source, pending.open('xb') as output:
            while block := source.read(1024 * 1024):
                output.write(block)
                if output.tell() > expected['bytes']:
                    raise ValueError('Published native input exceeds exact size')
        checked(pending, expected)
        pending.replace(target)
    finally:
        pending.unlink(missing_ok=True)


def stage(output, cache):
    output, cache = Path(output), Path(cache)
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    donor = cache / 'COH-Atlas-Gameplay-0.13.31.apk'
    download(RELEASE + 'coh-atlas-gameplay-v0.13.31/' + donor.name, donor, DONOR)
    target = output / donor.name
    if target.exists():
        checked(target, DONOR)
    else:
        shutil.copyfile(donor, target)
    existing = cache / 'payloads'
    missing = []
    for name, expected in INPUTS.items():
        target = output / name
        if target.exists():
            checked(target, expected)
        elif (existing / name).exists():
            checked(existing / name, expected)
            shutil.copyfile(existing / name, target)
        else:
            missing.append(name)
    if missing:
        volume = cache / 'COH-Assets-1.0.0-Base.zip'
        download(RELEASE + 'coh-assets-v1.0.0/' + volume.name, volume, BASE)
        with zipfile.ZipFile(volume) as archive:
            for name in missing:
                member = archive.getinfo('payloads/runtime/' + name)
                if member.is_dir() or member.flag_bits & 1 or member.file_size != INPUTS[name]['bytes']:
                    raise ValueError('Native asset volume member differs')
                with archive.open(member) as source, (output / name).open('xb') as destination:
                    shutil.copyfileobj(source, destination, 1024 * 1024)
                checked(output / name, INPUTS[name])
    with zipfile.ZipFile(output / 'client-caches.zip') as archive:
        raw = archive.read('data/bin/fxinfo.bin')
    if fx.pin_bytes(raw) != fx.BASE:
        raise ValueError('Original full client FX differs')
    full = output / 'fxinfo-full.bin'
    if full.exists():
        checked(full, fx.BASE)
    else:
        full.write_bytes(raw)
    receipt = {'format': 1, 'status': 'exact_published_inputs_staged',
        'donor_commit': '74fe247be85173e618f1af2c8af71b1316de4cd8',
        'donor_apk': DONOR, 'asset_release': 'coh-assets-v1.0.0',
        'base_volume': BASE, 'files': {**INPUTS, 'fxinfo-full.bin': fx.BASE},
        'donor_rebuilt': False, 'assets_republished': False,
        'native_runtime_execution_validated': False, 'physical_execution_validated': False}
    (output / 'map-startup-inputs.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cache', required=True, type=Path)
    args = parser.parse_args()
    result = stage(args.output, args.cache)
    print(json.dumps({'status': result['status'], 'donor_rebuilt': False, 'asset_release': result['asset_release']}))
