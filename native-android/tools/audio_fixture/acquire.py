#!/usr/bin/env python3
"""Acquire one genuine client Ogg with exact bounded release ZIP ranges."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
import zipfile,zlib
HERE=Path(__file__).resolve().parent
def require(value,message):
    if not value: raise ValueError(message)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--use-verified-local',action='store_true');a=p.parse_args()
    pins=json.loads((HERE/'pins.json').read_text());pin=pins['record'];a.output.mkdir(parents=True,exist_ok=True)
    target=a.output/pin['file_name']
    if a.use_verified_local and target.is_file():
        raw=target.read_bytes()
        require(len(raw)==pin['size'] and hashlib.sha256(raw).hexdigest()==pin['sha256'] and f'{zlib.crc32(raw):08x}'==pin['crc32'],'Local source Ogg differs')
        old=json.loads((a.output/'corpus.json').read_text());require(old.get('acquisition_passed') is True,'Local acquisition receipt missing')
        print(json.dumps({'source_sha256':pin['sha256'],'reused':True}));return
    spec=importlib.util.spec_from_file_location('reviewed_material_ranges',HERE.parent/'material_fixture/acquire.py')
    ranges=importlib.util.module_from_spec(spec);spec.loader.exec_module(ranges)
    reader=ranges.HTTPRange(pins['outer_asset_url'],pins['outer_expected_bytes'],2<<20)
    with zipfile.ZipFile(reader) as outer:
        info=outer.getinfo(pins['inner_member']);require(info.compress_type==zipfile.ZIP_STORED and not info.flag_bits&1,'Stored inner ZIP required')
        innerfile=ranges.subzip(reader,info);require(innerfile.size==pins['inner_expected_bytes'],'Inner ZIP size differs')
        with zipfile.ZipFile(innerfile) as inner:
            info=inner.getinfo(pin['name'])
            require((info.file_size,info.compress_size,info.header_offset,info.compress_type,f'{info.CRC:08x}')==(pin['size'],pin['compressed'],pin['offset'],pin['method'],pin['crc32']),'Selected Ogg ZIP metadata differs')
            require(not info.flag_bits&1 and info.file_size<1<<20,'Selected Ogg bounds differ')
            raw=inner.read(info)
        manifest=outer.read(pins['manifest_member'])
        require(len(manifest)==pins['manifest_bytes'] and hashlib.sha256(manifest).hexdigest()==pins['manifest_sha256'],'Release source manifest differs')
        declared=json.loads(manifest)['files'][pin['name']]
        require(declared=={'bytes':pin['size'],'sha256':pin['sha256']},'Selected original payload manifest pin differs')
    require(len(raw)==pin['size'] and hashlib.sha256(raw).hexdigest()==pin['sha256'] and f'{zlib.crc32(raw):08x}'==pin['crc32'],'Source Ogg CRC/SHA differs')
    target.write_bytes(raw)
    receipt={'schema':'coh-native-audio-acquisition-v1','acquisition_passed':True,'source':pin,
             'manifest_sha256':pins['manifest_sha256'],'source_manifest_verified':True,
             'range_bytes_downloaded':reader.total,'range_count':len(reader.requests),'ranges':reader.requests,
             'exact_http_range_enforced':True,'stable_etag':True,'crc32_verified':True,'sha256_verified':True,
             'outer_archive_fully_hashed_locally':False,'inner_archive_fully_hashed_locally':False,
             'outer_release_sha256':pins['outer_release_sha256'],'inner_release_sha256':pins['inner_release_sha256']}
    (a.output/'corpus.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':True,'source_sha256':pin['sha256'],'range_bytes':reader.total}))
if __name__=='__main__':main()
