#!/usr/bin/env python3
"""Read retained capture only; enumerate available wire inputs and absent raw bounds.
No server execution, native seed import or live-generation admission occurs.
"""
from pathlib import Path
import argparse,hashlib,json,struct
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def u32(b,o):
 if o<0 or o+4>len(b):raise ValueError('truncated u32')
 return struct.unpack_from('<I',b,o)[0]
def text(raw):
 if not raw or raw[-1] or b'\0' in raw[:-1] or any(x<32 or x>126 for x in raw[:-1]):raise ValueError('noncanonical name')
 return raw[:-1].decode('ascii')
def inspect(directory,binding_sha):
 names=['resource-binding.json','catalog.cohcat','runtime.cohrts','resources.cohres','source-identity.json','run-identity.json']
 limits=[16384,32<<20,16<<20,64<<20,2<<20,1<<20]
 for n,limit in zip(names,limits):
  if (directory/n).stat().st_size>limit:raise ValueError('artifact exceeds source audit bound')
 pins={n:{'bytes':(directory/n).stat().st_size,'sha256':sha(directory/n)} for n in names}
 if pins[names[0]]['sha256']!=binding_sha:raise ValueError('untrusted binding bytes')
 binding=json.loads((directory/names[0]).read_text());source=json.loads((directory/names[4]).read_text());run=json.loads((directory/names[5]).read_text())
 for key,name in [('catalog',names[1]),('snapshot',names[2]),('resources',names[3])]:
  if binding[key]!=pins[name]:raise ValueError('artifact association differs')
 for key,name in [('source_identity',names[4]),('run_identity',names[5])]:
  if binding[key]['file']!=name or binding[key]['sha256']!=pins[name]['sha256']:raise ValueError('identity association differs')
 if binding['source_snapshot_only'] is not True or binding['live_groups_transaction'] is not False or binding['assets_admitted'] is not False:raise ValueError('capture scope differs')
 if source['retained_catalog_sha256']!=pins[names[1]]['sha256'] or run['source_identity_sha256']!=pins[names[4]]['sha256'] or source['exporter_source_revision']!=run['orchestration_source_revision']:raise ValueError('source/run association differs')
 supplier=ROOT/'native-android/engine/scenecatalog-server/source_resources.inc'
 if sha(supplier)!=source['resource_producer_sha256']:raise ValueError('resource schema supplier differs')
 cat=(directory/names[1]).read_bytes();snap=(directory/names[2]).read_bytes()
 if cat[:8]!=b'COHCAT01' or snap[:8]!=b'COHRTS01' or u32(cat,16)!=len(cat) or u32(snap,24)!=len(cat) or u32(cat,20)!=binding['asset_generation'] or u32(snap,20)!=binding['asset_generation'] or u32(cat,32)!=u32(snap,56) or u32(cat,36)!=u32(snap,60):raise ValueError('capture headers differ')
 if u32(cat,24)>4096 or u32(cat,28)>65536:raise ValueError('catalog admission bounds')
 at=48;files=[];active=removed=allocated=public=holes=total_slots=0
 for f in range(u32(cat,24)):
  idx,crc,slots,records,n=struct.unpack_from('<5I',cat,at);at+=20
  if idx!=f or n>256 or n>len(cat)-at or records>slots or slots>65536:raise ValueError('file shape')
  total_slots+=slots
  if total_slots>65536:raise ValueError('aggregate slots limit')
  filename=text(cat[at:at+n]);at+=n;public_slots=[];last=-1
  for _ in range(records):
   slot,bits,size,aligned=struct.unpack_from('<4I',cat,at);at+=16
   if slot<=last or slot>=slots or aligned!=1 or bits!=size*8 or size<5 or size>len(cat)-at:raise ValueError('wire shape')
   last=slot;raw=cat[at:at+size];at+=size
   if u32(raw,0)!=slot+1 or raw[4]>1:raise ValueError('wire identity')
   allocated+=1
   if raw[4]:
    active+=1;end=raw.find(b'\0',5)
    if end<6 or end-5>=256:raise ValueError('active name')
    name=text(raw[5:end+1])
    if filename.lower().startswith('object_library') and not name.lower().startswith('grp') and not name.endswith('&'):public_slots.append(slot);public+=1
   else:removed+=1
  holes+=slots-records
  files.append({'file':f,'name':filename,'observed_bounds_checksum':crc,'allocated':records,'slots':slots,'public_slots_requiring_exact_raw_bounds':public_slots,'file0_original_writer_skips':f==0})
 if at!=len(cat) or allocated!=u32(cat,28):raise ValueError('catalog closure')
 if pins!={n:{'bytes':(directory/n).stat().st_size,'sha256':sha(directory/n)} for n in names}:raise ValueError('capture changed while inspecting')
 source_pins={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),HERE/'coh_catalog_seed.c',HERE/'coh_catalog_seed.h',ROOT/'upstream/ouroboros/Common/group/group.c',ROOT/'upstream/ouroboros/Common/group/groupfilelib.c',ROOT/'upstream/ouroboros/Game/src/group/groupnetrecv.c',supplier]}
 return {'schema':'coh-catalog-seed-input-audit-v1','passed':True,'capture_pins':pins,'source_sha256':source_pins,'files':files,'summary':{'files':len(files),'allocated_protocol_records':allocated,'active_records':active,'tombstones':removed,'holes':holes,'ordinary_public_raw_bounds_missing':public,'minimum_missing_raw_bounds_bytes':public*60,'runtime_root_slots':u32(snap,44),'runtime_external_future_records':u32(snap,52)},'scope':'prefix/identity availability audit of previously qualified detached source artifacts; not a complete parser or actual seed transaction','all_catalog_wire_records_retained':True,'ordinary_raw_groupbounds_present':False,'bounds_cache_checksums_recomputed':False,'native_seed_transaction_executed':False,'client_derived_state_complete':False,'source_generation_admitted':False,'world_authority':False}
def main():
 p=argparse.ArgumentParser();p.add_argument('--capture-dir',type=Path,required=True);p.add_argument('--binding-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=inspect(a.capture_dir,a.binding_sha256);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['summary']))
if __name__=='__main__':main()
