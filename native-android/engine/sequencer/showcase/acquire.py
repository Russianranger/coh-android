#!/usr/bin/env python3
"""Recover the existing three-body family corpus with exact bounded ZIP reads.

The published outer hash is provenance, not a full archive verification claim.
All pre-existing motion/male/Huge-base SHA pins are independently checked.
The Female base pin was established by original central/local ZIP name, size,
CRC and stable release ETag, then recorded before pose qualification. Source
pose and original-loader checks remain separate from archive identity.
"""
import argparse,hashlib,importlib.util,json,zipfile,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[2]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 pins=json.loads((NATIVE/'tools/animation_fixture/pins.json').read_text())
 motion=json.loads((HERE.parent/'continuation/extra-asset-pins.json').read_text())
 known={x['name']:{'bytes':x['size'],'sha256':x['sha256']} for x in pins['records']}
 known.update({x['name']:{'bytes':x['size'],'sha256':x['sha256']} for x in json.loads((NATIVE/'tools/directional_fixture/pins.json').read_text())['records']})
 known.update(json.loads((HERE/'base-pins.json').read_text()))
 selected={f'assets/player_library/animations/{k}.anim':v for k,v in motion.items()}
 for body,name in [('male','skel_ready2'),('fem','skel_ready2'),('huge','skel_ready')]:
  path=f'assets/player_library/animations/{body}/{name}.anim';selected[path]=known.get(path)
 ranges=module('showcase_ranges',NATIVE/'tools/animation_fixture/acquire.py')
 reader=ranges.HTTPRange(pins['outer_asset_url'],pins['outer_expected_bytes'],16<<20)
 with zipfile.ZipFile(reader) as outer:
  inner=ranges.subzip(reader,outer.getinfo(pins['inner_member']))
 if inner.size!=pins['inner_expected_bytes']:raise ValueError('inner archive size differs')
 records=[]
 with zipfile.ZipFile(inner) as archive:
  for name,pin in selected.items():
   info=archive.getinfo(name)
   if info.flag_bits&1 or info.compress_type not in (0,8) or not 0<info.file_size<=2<<20:raise ValueError('unsupported source member')
   path=a.output/name;raw=path.read_bytes() if path.is_file() else None
   def valid(data):
    return data is not None and len(data)==info.file_size and zlib.crc32(data)==info.CRC and (not pin or (len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256']))
   reused=valid(raw)
   if not reused:
    with archive.open(info) as source:raw=source.read(info.file_size+1)
    if not valid(raw):raise ValueError('source SHA/size/CRC differs '+name)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
   records.append({'name':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'crc32':f'{info.CRC:08x}','existing_sha_pin':bool(pin),'reused':reused})
   print(name,len(raw),flush=True)
 receipt={'schema':'coh-three-body-showcase-acquisition-v1','outer_asset_url':pins['outer_asset_url'],'outer_published_sha256':pins['outer_published_sha256'],'full_outer_hash_verified':False,'full_inner_hash_verified':False,'strict_http206':True,'stable_etag':reader.etag,'network_bytes':reader.total,'ranges':reader.requests,'records':records}
 (a.output/'acquisition.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
