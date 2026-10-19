#!/usr/bin/env python3
"""Reuse one pinned historical capture/cache and acquire only the CityHall GEO."""
import argparse, gzip, hashlib, json, stat, subprocess, zipfile
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = a.source_root.resolve()
out = a.output.resolve()
if out == root or out.is_relative_to(root) or out.exists():
    p.error('New external output directory required')
out.mkdir(parents=True)
archive = root / 'native-android/combined-client/evidence/20261017/emergency-recovery/resource-capture-38994607354/evidence.zip'
assert archive.stat().st_size == 2945220
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '572d5cde08f698173cce4c9a0860902a2da91841b22dbdd124501e1e601e192d'
members = ['capture/' + n for n in ('catalog.cohcat', 'runtime.cohrts', 'resources.cohres', 'source-identity.json', 'run-identity.json', 'resource-binding.json', 'capture-receipt.json')] + ['control-fixture.json']
with zipfile.ZipFile(archive) as z:
    infos = z.infolist()
    assert len(infos) <= 128 and len({i.filename for i in infos}) == len(infos)
    assert sum(i.file_size for i in infos) <= 64 * 1024**2 and z.testzip() is None
    for name in members:
        info = z.getinfo(name)
        assert not info.flag_bits & 1 and stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(info))
cache = root / 'native-android/engine/world-render-adapter/qualification/client-texopt-cache-20261017/tricks.bin.gz'
with gzip.open(cache, 'rb') as stream:
    raw = stream.read(13537053)
assert len(raw) == 13537052 and hashlib.sha256(raw).hexdigest() == 'cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1'
(out / 'tricks.bin').write_bytes(raw)
scene = root / 'native-android/engine/scenecatalog'
subprocess.run(['python3', str(scene / 'acquire_resource_candidates.py'), '--source-root', str(root), '--candidates', str(scene / 'evidence/actual-resource-manifest-candidates-38994607354-verified.json'), '--candidates-sha256', 'a52d6470847fc01a677cfa2822c0cf5eae23eecefcb52edb7e2789ecd5c637a6', '--source-geo', 'object_library/city_zones/Atlas_Park_makeover/ap_cityhall_makeover_01.geo', '--output', str(out / 'bodies')], check=True, timeout=240)
body = out / 'bodies/data/object_library/city_zones/atlas_park_makeover/ap_cityhall_makeover_01.geo'
assert body.stat().st_size == 1104239 and hashlib.sha256(body.read_bytes()).hexdigest() == '80e8e7530ab9d42ad98a6ddd065a0e40ba1cc1a999558241c3aebc17eb89db9a'
receipt = {'passed': True, 'capture_artifact_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'body_sha256': hashlib.sha256(body.read_bytes()).hexdigest(), 'body_bytes': body.stat().st_size, 'body_acquisition': json.loads((out / 'bodies/acquisition.json').read_text()), 'current_live_generation_admitted': False, 'world_authority': False}
(out / 'preparation.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'passed': True, 'body_bytes': body.stat().st_size, 'current_live_generation_admitted': False}))
