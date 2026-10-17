#!/usr/bin/env python3
"""Acquire one exact retained Atlas cached-header test input using bounded ZIP ranges."""
import argparse,hashlib,importlib.util,json,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists() or out==ROOT or out.is_relative_to(ROOT):raise ValueError('Fresh external output directory required')
 pins=json.loads((HERE/'tex-inputs-authentic-pins.json').read_text());raw=a.manifest.read_bytes()
 if len(raw)>8*1024**2 or hashlib.sha256(raw).hexdigest()!=pins['manifest_sha256']:raise ValueError('Exact complete retained manifest required')
 manifest=json.loads(raw);item=pins['bar'];name=item['asset_path']
 if manifest['files'][name]!={'bytes':item['bytes'],'sha256':item['sha256']} or manifest['provenance']['entries'][name]!=item['source']:raise ValueError('Manifest selected payload/provenance differs')
 helper=ROOT/'native-android/tools/material_fixture/acquire.py';helper_sha=sha(helper);spec=importlib.util.spec_from_file_location('qualified_cached_header_ranges',helper);ranges=importlib.util.module_from_spec(spec);spec.loader.exec_module(ranges)
 release=pins['release'];reader=ranges.HTTPRange(release['url'],release['outer_bytes'],8*1024**2);out.mkdir(parents=True);receipt={'passed':False,'manifest_sha256':pins['manifest_sha256'],'helper_sha256':helper_sha,'script_sha256':sha(Path(__file__)),'outer_full_sha_verified':False,'inner_full_sha_verified':False,'source_generation_established':False,'asset_generation_permit':False,'material_authority':False,'world_authority':False}
 try:
  with zipfile.ZipFile(reader) as outer:stream=ranges.subzip(reader,outer.getinfo(release['inner_member']))
  if stream.size!=release['inner_bytes']:raise ValueError('Inner archive identity size differs')
  with zipfile.ZipFile(stream) as inner:
   info=inner.getinfo(name)
   if info.file_size!=item['bytes'] or info.flag_bits&1 or info.compress_type not in(0,8):raise ValueError('Selected ZIP envelope differs')
   body=inner.read(info)
  if len(body)!=item['bytes'] or hashlib.sha256(body).hexdigest()!=item['sha256']:raise ValueError('Selected body identity differs')
  if sha(helper)!=helper_sha or a.manifest.read_bytes()!=raw:raise ValueError('Admitted inputs changed')
  (out/'bar_vert_sign.texture').write_bytes(body);receipt.update(passed=True,selected_payload_sha256=item['sha256'],selected_payload_bytes=len(body),zip_crc_verified=True,zip_crc32=f'{info.CRC:08x}',zip_header_offset=info.header_offset,zip_method=info.compress_type,zip_compressed_bytes=info.compress_size)
 finally:
  receipt.update(range_bytes=reader.total,ranges=reader.requests,etag=reader.etag);(out/'acquisition.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'passed':True,'payload_bytes':len(body),'range_bytes':reader.total,'asset_generation_permit':False}))
if __name__=='__main__':main()
