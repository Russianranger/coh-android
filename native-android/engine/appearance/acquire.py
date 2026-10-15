#!/usr/bin/env python3
"""Bounded subset acquisition; never downloads entire Base archive.
Reuse the accepted strict HTTP206 reader. Each member requires pinned local-header
identity, deflate bounds, exact length, ZIP CRC and independent original SHA256.
Outer/inner whole archive hashes are published provenance, not subset verification.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,struct,zipfile,zlib
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('appearance_accepted_ranges',HERE.parents[1]/'tools/animation_fixture/acquire.py');ranges=importlib.util.module_from_spec(s);s.loader.exec_module(ranges)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);pins=json.loads((HERE/'corpus-pins.json').read_text());reader=None;stream=None;verified=[]
 for pin in pins['records']:
  if not re.fullmatch('[a-z0-9_]+[.]geo',pin['file_name']) or not 0<pin['size']<=2<<20:raise ValueError('unsafe output or oversized member')
  path=a.output/pin['file_name'];raw=path.read_bytes() if path.is_file() else None
  valid=lambda b:b is not None and len(b)==pin['size'] and f'{zlib.crc32(b):08x}'==pin['crc32'] and hashlib.sha256(b).hexdigest()==pin['sha256']
  reused=valid(raw)
  if not reused:
   if reader is None:
    reader=ranges.HTTPRange(pins['outer_asset_url'],pins['outer_expected_bytes'],16<<20)
    with zipfile.ZipFile(reader) as outer:stream=ranges.subzip(reader,outer.getinfo(pins['inner_member']))
    if stream.size!=pins['inner_expected_bytes']:raise ValueError('inner size differs')
   stream.seek(pin['offset']);h=stream.read(30)
   if h[:4]!=b'PK\x03\x04':raise ValueError('local header signature differs')
   flags,method=struct.unpack_from('<HH',h,6);nl,el=struct.unpack_from('<HH',h,26)
   if flags&1 or method!=pin['method'] or method not in (0,8):raise ValueError('unsupported method/encryption')
   if stream.read(nl).decode()!=pin['name']:raise ValueError('source member identity differs')
   stream.seek(pin['offset']+30+nl+el);stored=stream.read(pin['compressed'])
   if len(stored)!=pin['compressed']:raise ValueError('stored member truncated')
   if method==8:
    dec=zlib.decompressobj(-15);raw=dec.decompress(stored,pin['size']+1)
    if not dec.eof or dec.unused_data or dec.unconsumed_tail:raise ValueError('deflate bounds differ')
   else:raw=stored
   if not valid(raw):raise ValueError('member size/CRC/source SHA256 differs')
   path.write_bytes(raw)
  verified.append({'name':pin['name'],'file_name':pin['file_name'],'bytes':len(raw),'sha256':pin['sha256'],'reused_after_verification':reused})
 receipt={'format':'coh-appearance-corpus-v1','passed':True,'files':verified,'strict_http206_ranges':True,'network_bytes':reader.total if reader else 0,'network_etag':reader.etag if reader else None,'source_manifest_full_hash_previously_verified':pins['manifest_full_size_crc_sha256_verified_here'],'outer_full_hash_verified':False,'inner_full_hash_verified':False}
 (a.output/'corpus.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'files':len(verified),'network_bytes':receipt['network_bytes']}))
if __name__=='__main__':main()
