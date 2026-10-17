#!/usr/bin/env python3
"""Recover one reviewed exact authentic texture fixture by bounded public ZIP ranges.

Stores raw game data only at an explicitly external scratch destination. Full
outer/inner archive hashes are not verified; the selected payload SHA+CRC are.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    output=a.output.resolve()
    if output.exists() or output==ROOT or output.is_relative_to(ROOT):p.error('New external output directory required')
    pins=json.loads((HERE/'sampler-authentic-pins.json').read_text());release=pins['release']
    helper=ROOT/'native-android/tools/material_fixture/acquire.py'
    spec=importlib.util.spec_from_file_location('qualified_fixture_ranges',helper);ranges=importlib.util.module_from_spec(spec);spec.loader.exec_module(ranges)
    reader=ranges.HTTPRange(release['outer_asset_url'],release['outer_expected_bytes'],8<<20)
    with zipfile.ZipFile(reader) as outer:
        stream=ranges.subzip(reader,outer.getinfo(release['inner_member']))
    if stream.size!=release['inner_expected_bytes']:raise ValueError('Inner ZIP exact size differs')
    with zipfile.ZipFile(stream) as inner:
        info=inner.getinfo(pins['virtual'])
        if (info.flag_bits&1 or info.file_size!=pins['payload']['bytes'] or
                info.compress_type!=pins['zip_method'] or info.compress_size!=pins['zip_compressed_bytes'] or
                info.header_offset!=pins['zip_header_offset'] or f'{info.CRC:08x}'!=pins['zip_crc32']):
            raise ValueError('Selected ZIP member envelope differs')
        raw=inner.read(info)
    if len(raw)!=pins['payload']['bytes'] or hashlib.sha256(raw).hexdigest()!=pins['payload']['sha256']:raise ValueError('Authentic texture payload differs')
    output.mkdir(parents=True)
    (output/'box-1.texture').write_bytes(raw)
    receipt=dict(pins,payload_sha_verified=True,zip_crc_verified=True,outer_full_sha_verified=False,
                 inner_full_sha_verified=False,ranges=reader.requests,range_bytes=reader.total,
                 etag=reader.etag,original_pigg_reacquired=False,world_authority=False)
    (output/'acquisition.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':True,'payload_sha256':pins['payload']['sha256'],'bytes':len(raw),'world_authority':False}))
if __name__=='__main__':main()
