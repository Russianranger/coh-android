#!/usr/bin/env python3
"""Recover the exact historical cache retained in Git, with bounded inflation and exact hashes."""
import argparse,hashlib,json,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
COMPRESSED_SHA='3e00fe9f1fcc98eb3ae91208ff7b3153569c747878f33a93001acdf253d1fbdb';RAW_SHA='cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1'
def unpack(body):
 if type(body) is not bytes or len(body)!=603236 or hashlib.sha256(body).hexdigest()!=COMPRESSED_SHA:raise ValueError('exact compressed cache required')
 d=zlib.decompressobj(31);raw=d.decompress(body,13537053)
 if len(raw)!=13537052 or not d.eof or d.unused_data or d.unconsumed_tail or hashlib.sha256(raw).hexdigest()!=RAW_SHA:raise ValueError('exact bounded original cache required')
 return raw
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve()
 if out.exists() or out==ROOT or ROOT in out.parents:raise ValueError('fresh external output required')
 body=(HERE/'qualification/client-texopt-cache-20261017/tricks.bin.gz').read_bytes();raw=unpack(body);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw);print(json.dumps({'passed':True,'raw_bytes':len(raw),'raw_sha256':RAW_SHA,'material_authority':False,'world_authority':False}))
