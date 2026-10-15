#!/usr/bin/env python3
"""Acquire explicitly selected original release entries with strict bounded ranges."""
from pathlib import Path
import argparse,importlib.util,json,hashlib,zipfile,zlib
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--selection',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
spec=importlib.util.spec_from_file_location('accepted_ranges',a.source_root/'native-android/tools/animation_fixture/acquire.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
index=json.loads(a.index.read_text());pins=index['pins'];wanted=json.loads(a.selection.read_text());records={x['name']:x for x in index['records']}
r=m.HTTPRange(pins['outer_asset_url'],pins['outer_expected_bytes'],32<<20)
with zipfile.ZipFile(r) as outer:sub=m.subzip(r,outer.getinfo(pins['inner_member']))
result=[]
with zipfile.ZipFile(sub) as inner:
 for name in wanted:
  entry=records[name];info=inner.getinfo(name)
  assert info.file_size==entry['size'] and info.compress_size==entry['compressed'] and info.header_offset==entry['offset'] and f'{info.CRC:08x}'==entry['crc32'] and info.file_size<=8<<20
  rel=Path(name);assert not rel.is_absolute() and '..' not in rel.parts
  with inner.open(info) as f:raw=f.read(info.file_size+1)
  assert len(raw)==info.file_size and f'{zlib.crc32(raw):08x}'==entry['crc32']
  target=a.output/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
  result.append(dict(entry,sha256=hashlib.sha256(raw).hexdigest()));print(name,len(raw),flush=True)
a.output.mkdir(parents=True,exist_ok=True)
(a.output/'acquisition.json').write_text(json.dumps({'schema':'coh-native-support-corpus-v1','source_release':pins['release_tag'],'outer_asset_url':pins['outer_asset_url'],'outer_published_sha256':pins['outer_published_sha256'],'full_outer_hash_locally_verified':False,'etag_stable':True,'etag':r.etag,'range_bytes':r.total,'ranges':r.requests,'records':result,'qualification':'CRC and new SHA identities; decoded/source parity is separate'},indent=2)+'\n')
