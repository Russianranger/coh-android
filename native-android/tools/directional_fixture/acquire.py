#!/usr/bin/env python3
"""Acquire eight hash-pinned authored clips through accepted bounded ZIP ranges."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,struct,zipfile,zlib
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('accepted_character_ranges',HERE.parent/'animation_fixture/acquire.py')
ranges=importlib.util.module_from_spec(spec);spec.loader.exec_module(ranges)
def require(v,s):
    if not v:raise ValueError(s)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--use-verified-local',action='store_true');a=p.parse_args()
    pins=json.loads((HERE/'pins.json').read_text());a.output.mkdir(parents=True,exist_ok=True);reader=None;sub=None;reused=[]
    for item in pins['records']:
        f=a.output/item['file_name']
        def verified(raw):return len(raw)==item['size'] and f'{zlib.crc32(raw):08x}'==item['crc32'] and hashlib.sha256(raw).hexdigest()==item['sha256']
        if a.use_verified_local and f.exists() and verified(f.read_bytes()):reused.append(item['id']);continue
        if reader is None:
            reader=ranges.HTTPRange(pins['outer_asset_url'],pins['outer_expected_bytes'],2<<20)
            with zipfile.ZipFile(reader) as outer:sub=ranges.subzip(reader,outer.getinfo(pins['inner_member']))
            require(sub.size==pins['inner_expected_bytes'],'inner ZIP size differs')
        sub.seek(item['offset']);header=sub.read(30);require(header[:4]==b'PK\x03\x04','ZIP local header differs')
        flags,method=struct.unpack_from('<HH',header,6);require(not(flags&1) and method==item['method']==8,'ZIP encryption/method differs')
        nl,el=struct.unpack_from('<HH',header,26);name=sub.read(nl).decode('utf8');require(name==item['name'],'ZIP source member differs')
        sub.seek(item['offset']+30+nl+el);compressed=sub.read(item['compressed']);require(len(compressed)==item['compressed'],'ZIP member truncated')
        decoder=zlib.decompressobj(-15);raw=decoder.decompress(compressed,item['size']+1)
        require(decoder.eof and not decoder.unconsumed_tail and not decoder.unused_data,'deflate bounds differ');require(verified(raw),'source size/CRC/SHA differs')
        f.write_bytes(raw);print(item['id']+': source SHA256 verified',flush=True)
    receipt={'schema':'coh-native-directional-acquisition-v2','status':'passed','source_release':pins['release_tag'],
             'all_fixture_sha256_verified':True,'all_fixture_size_crc_verified':True,'full_outer_hash_locally_verified':False,
             'bounded_http_ranges':True,'range_bytes_downloaded':reader.total if reader else 0,
             'range_count':len(reader.requests) if reader else 0,'locally_reused_after_verification':reused,'records':pins['records']}
    (a.output/'corpus.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
