#!/usr/bin/env python3
"""Inspect/extract a commit-complete COHGTX01 source observation, never authority.

Hashing and extraction are streamed. Exact source/build/run provenance and actual
native-owned receive correlation are independently required; this parser never
converts a self-described file or CRC into a live-generation certificate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

MAXIMUM=160*1024**2
ORDER=(1,2,3,4,6,5,7,8,9)
NAMES={1:'owner.cohown',2:'catalog.cohcat',3:'runtime.cohrts',4:'resources.cohres',5:'eligibility.bin',6:'public-bounds.cohrbw',7:'packet-metadata.bin',8:'packet.bin'}
CAPS={1:192,2:32*1024**2,3:16*1024**2,4:64*1024**2,5:(2+4096+65536+65536)*64,6:32*1024**2,7:192,8:16*1024**2,9:128}
def require(value,code):
 if not value:raise ValueError('COH_GROUPS_CAPTURE_'+code)
def words(raw):return struct.unpack('<'+'I'*(len(raw)//4),raw)
def exact(stream,n):
 raw=stream.read(n);require(len(raw)==n,'TRUNCATED');return raw
def private_output(path,binary):
 return os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb' if binary else 'w')
def inspect(path,extract=None):
 path=Path(path);require(not path.is_symlink(),'SOURCE_SYMLINK')
 if extract is not None:
  extract=Path(os.path.abspath(extract));require(not any(p.is_symlink() for p in (extract,*extract.parents)),'OUTPUT_SYMLINK');extract.mkdir(mode=0o700)
 outputs={};created=[]
 try:
  digests={k:hashlib.sha256() for k in NAMES};sizes={k:0 for k in CAPS};chunks={k:0 for k in CAPS};prefixes={};digest=hashlib.sha256();at=64;sequence=0;order=-1
  with os.fdopen(os.open(path,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)),'rb') as source:
   before=os.fstat(source.fileno());require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 64<=before.st_size<=MAXIMUM,'SOURCE_FILE')
   header=exact(source,64);digest.update(header);h=words(header[8:])
   require(header[:8]==b'COHGTX01' and h[0:2]==(1,64) and h[2] and h[3] and not any(h[4:]),'HEADER');observation,thread=h[2:4]
   while at<before.st_size:
    raw=exact(source,16);digest.update(raw);kind,identity,n,ordinal=struct.unpack('<4I',raw)
    require(kind in CAPS and identity==observation and ordinal==sequence and n and n<=CAPS[kind]-sizes[kind] and n<=before.st_size-at-16,'CHUNK')
    index=ORDER.index(kind);require(index in (order,order+1),'ORDER');order=index
    require(kind not in (1,7,8,9) or not chunks[kind],'SINGLETON')
    sizes[kind]+=n;chunks[kind]+=1;sequence+=1;at+=16+n
    if kind==9:
     footer=exact(source,n);digest.update(footer);require(n==128 and at==before.st_size,'FOOTER_SIZE');f=words(footer[8:])
     require(footer[:8]==b'COHGEND1' and f[0:3]==(1,128,observation) and f[3]==before.st_size and f[4]==sequence and f[5]==thread,'FOOTER')
     require(f[6:14]==tuple(sizes[k] for k in range(1,9)) and f[14:22]==tuple(chunks[k] for k in range(1,9)) and not any(f[22:]),'FOOTER_COUNTS');continue
    if extract is not None and kind not in outputs:
     target=extract/NAMES[kind];outputs[kind]=private_output(target,True);created.append(target)
    remaining=n
    while remaining:
     body=exact(source,min(64*1024,remaining));digest.update(body);digests[kind].update(body)
     if kind not in prefixes:prefixes[kind]=body[:192]
     elif len(prefixes[kind])<192:prefixes[kind]=(prefixes[kind]+body)[:192]
     if kind in outputs:outputs[kind].write(body)
     remaining-=len(body)
   require(order==len(ORDER)-1 and all(chunks[k] for k in CAPS) and not source.read(1),'END')
   after=os.fstat(source.fileno());require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'SOURCE_CHANGED')
  meta=prefixes[7];require(len(meta)==192 and meta[:8]==b'COHGPAK1','PACKET_METADATA');m=words(meta[8:]);require(m[0:3]==(1,192,observation) and m[3] and m[4] in (0,1) and m[5] in (0,1) and m[37]==thread and not any(m[38:]),'PACKET_METADATA_FIELDS')
  require(sizes[8]==(m[3]+7)//8 and sizes[5]==m[6]*64 and sizes[2]==m[17] and sizes[3]==m[24] and sizes[4]==m[30] and sizes[6]==m[36] and m[31:33]==(0,0),'PACKET_METADATA_COUNTS')
  cat=prefixes[2];require(cat[:8]==b'COHCAT01' and len(cat)>=48,'CATALOG_HEADER');c=words(cat[8:48]);require(c[0:2]==(1,48) and c[2]==sizes[2] and c[3]==observation and c[4]==m[13] and c[5]==m[14] and c[6:8]==m[22:24] and c[8]==m[19] and c[9]==0,'CATALOG_COUNTS')
  runtime=prefixes[3];require(runtime[:8]==b'COHRTS01' and len(runtime)>=80,'RUNTIME_HEADER');t=words(runtime[8:80]);require(t[0:5]==(1,80,sizes[3],observation,sizes[2]) and t[5:9]==(m[13],m[15],m[14],m[16]) and t[9:14]==(m[18],m[19],m[20],m[22],m[23]) and not any(t[14:]),'RUNTIME_CATALOG')
  bounds=prefixes[6];require(bounds[:8]==b'COHRBW01' and len(bounds)>=96 and bounds[32:80]==cat[:48] and struct.unpack_from('<I',bounds,16)[0]==sizes[6],'BOUNDS_CATALOG')
  owner=prefixes[1];require(len(owner)==192 and owner[:8]==b'COHOWN01' and words(owner[8:16])==(1,192),'OWNER_HEADER');o=words(owner[8:]);require(o[2]>0 and o[3]>0 and o[4]>0,'OWNER_IDENTITY')
  result={'schema':'coh-source-groups-envelope-inspection-v1','passed':True,'envelope':{'bytes':before.st_size,'sha256':digest.hexdigest()},'observation_id':observation,'source_thread_id':thread,
          'files':{NAMES[k]:{'bytes':sizes[k],'chunks':chunks[k],'sha256':digests[k].hexdigest()} for k in NAMES},
          'packet':{'bits':m[3],'byte_aligned':m[4],'compress':m[5],'includes_original_command':True,'pre_pktSend_observation':True},
          'source_owner':{'selected_dbid':o[2],'entity_id':o[3],'server_index':o[4],'map_id':o[36],'static_map_id':o[37],'auth_id':o[45]},
          'source_catalog':{'files':m[13],'definitions':m[14],'slots':m[15],'children':m[16]},'source_snapshot':{'root_slots':m[18],'active_roots':m[19],'external_count':m[20],'external_children':m[21],'definitions_crc':m[22],'references_crc':m[23]},
          'source_provenance_verified':False,'source_run_identity_verified':False,'actual_native_receive_correlated':False,'cache_equivalence_verified':False,'source_generation_admitted':False,'world_authority':False}
  for output in outputs.values():output.flush();os.fsync(output.fileno());output.close()
  if extract is not None:
   target=extract/'inspection.json'
   with private_output(target,False) as output:created.append(target);json.dump(result,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
  return result
 except Exception as failure:
  cleanup_errors=[]
  for output in outputs.values():
   try:
    if not output.closed:output.close()
   except OSError as error:cleanup_errors.append(type(error).__name__)
  for target in reversed(created):
   try:target.unlink()
   except OSError as error:cleanup_errors.append(type(error).__name__)
  if extract is not None:
   try:extract.rmdir()
   except OSError as error:cleanup_errors.append(type(error).__name__)
  if cleanup_errors and hasattr(failure,'add_note'):failure.add_note('Extraction cleanup refusals: '+','.join(cleanup_errors))
  raise
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path);parser.add_argument('--extract',type=Path);args=parser.parse_args();print(json.dumps(inspect(args.capture,args.extract),indent=2))
if __name__=='__main__':main()
