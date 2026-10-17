"""Bounded read-only Health/topology observations from exact existing capture.
No dynamic status/world admission. Names/Health presence are projected from the
saved original sendDef bodies, with sidecar roots/future ownership retained.
"""
import json,struct,hashlib
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
CAT_SHA='61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'
SNAP_SHA='c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02'
def matrix(r):
 if not r.scalar(1):
  for _ in range(12):r.scalar(32)
 else:
  pos,angles,scale=[r.scalar(1) for _ in range(3)]
  for _ in range(3*(pos+angles)):
   if r.scalar(1):r.scalar(1);r.packed(5)
   else:r.scalar(32)
  if scale:
   for _ in range(3):r.scalar(32)
def optional(r):
 if r.scalar(1):r.scalar(32)
def definition(data,bits,aligned):
 r=inv.independent.Reader(data,bits,aligned,0);identity=r.packed(1)-1;active=r.scalar(1);name=None;children=[];properties=[]
 if active:
  name=r.string(256).decode('ascii');r.scalar(32);count=r.packed(1)
  if count>262144:raise ValueError('child count cap')
  for _ in range(count):children.append(r.string(256).decode('ascii'));matrix(r)
  if r.scalar(1):
   for _ in range(5):optional(r)
   r.scalar(2)
   for _ in range(4):r.scalar(1)
  if r.scalar(1):
   for _ in range(6):r.scalar(1)
  optional(r);optional(r)
  if r.scalar(1):
   r.string(256);r.scalar(1);light=r.scalar(1);ambient=r.scalar(1)
   if light or ambient:
    if light:optional(r)
    for _ in range(8):r.scalar(8)
   if r.scalar(1):
    r.scalar(16);r.scalar(16);r.scalar(32);r.scalar(32)
   if r.scalar(1):r.string(256);r.string(256);r.scalar(8);r.scalar(32);r.scalar(1)
   if r.scalar(1):
    for _ in range(4):r.scalar(32)
    for _ in range(8):r.scalar(8)
   if r.scalar(1):
    for _ in range(3):r.scalar(32)
   if r.scalar(1):r.string(256);r.scalar(32)
   if r.scalar(1):
    for _ in range(6):r.scalar(8)
   texture=r.packed(1)
   if texture&~3:raise ValueError('texture flags')
   if texture&1:r.string(256)
   if texture&2:r.string(256)
   optional(r);props=r.packed(1)
   if props not in (0,1):raise ValueError('property flag')
   if props:
    count=r.scalar(32)
    if count>4096:raise ValueError('property count cap')
    for _ in range(count):
     key=r.string(64).decode('ascii');value=r.string(4096);typ=r.scalar(1);properties.append((key,value.decode('ascii'),typ))
  swaps=r.packed(1)
  if swaps>4096:raise ValueError('swap cap')
  for _ in range(swaps):r.string(256);r.string(256);r.scalar(1)
  if r.scalar(1):r.string(256)
  r.scalar(1)
 if r.cursor!=bits:raise ValueError('definition end')
 return {'id':identity,'active':active,'name':name,'children':children,'health_properties':[p for p in properties if p[0].lower()=='health']}
class Frame:
 def __init__(self,b,at=0):self.b=b;self.at=at
 def take(self,n):
  if n<0 or n>len(self.b)-self.at:raise ValueError('framing')
  v=self.b[self.at:self.at+n];self.at+=n;return v
 def words(self,n):return struct.unpack('<'+'I'*n,self.take(n*4))
 def string(self,n):
  b=self.take(n)
  if not 2<=n<=256 or b[-1]!=0:raise ValueError('framing name')
  return b[:-1].decode('ascii')
def inspect(catalog,snapshot,oracle_state=None):
 cat=catalog.read_bytes();snap=snapshot.read_bytes()
 if hashlib.sha256(cat).hexdigest()!=CAT_SHA or hashlib.sha256(snap).hexdigest()!=SNAP_SHA:raise ValueError('authentic pins')
 f=Frame(cat);assert f.take(8)==b'COHCAT01';h=f.words(10);assert h[:5]==(1,48,len(cat),20261016,508);defs={};names={}
 for file in range(h[4]):
  idx,crc,slots,allocated,length=f.words(5);assert idx==file and allocated<=slots<=65536;path=f.string(length)
  for _ in range(allocated):
   slot,bits,size,aligned=f.words(4);assert slot<slots and bits==size*8 and aligned==1
   d=definition(f.take(size),bits,aligned);assert d['id']==slot;d.update(file=file,slot=slot,path=path);defs[(file,slot)]=d
   if d['active']:
    if d['name'] in names:raise ValueError('duplicate canonical name')
    names[d['name']]=d
 assert f.at==len(cat)
 f=Frame(snap);assert f.take(8)==b'COHRTS01';h=f.words(18);assert h[:5]==(1,80,len(snap),20261016,len(cat));roots=[]
 for ordinal in range(h[9]):
  slot,present,kind,file,definition_id,n,bits,size=f.words(8);assert slot==ordinal
  if present:
   name=f.string(n);f.take(48);f.take(size);assert kind==1 and defs[(file,definition_id)]['name']==name;roots.append((slot,name))
 externals=[]
 for ordinal in range(h[11]):
  i,originalid,owner,model,n,bits,size,found,pathbytes=f.words(9);assert i==ordinal;live=f.take(60);scratch=f.take(60);name=f.string(n);path=f.take(pathbytes);d=definition(f.take(size),bits,1);assert d['name']==name and d['id']==originalid;flags=struct.unpack_from('<I',live,56)[0];d.update(external=True,flags=flags,file=0xffffffff,slot=ordinal);assert name not in names;names[name]=d;externals.append(d)
 assert f.at==len(snap)
 for d in names.values():
  for child in d['children']:
   if child not in names:raise ValueError('unresolved child '+child)
 # Independent full-root graph reachability witness, preserving root/entry order.
 witnesses={};work=0
 for root,name in roots:
  stack=[(name,[],[])]
  while stack:
   name,path,edges=stack.pop();work+=1
   if work>4_000_000 or len(path)>128:raise ValueError('work/depth')
   if name in path:raise ValueError('cycle')
   if name in witnesses:continue
   witnesses[name]={'root_slot':root,'names':path+[name],'child_ordinals':edges}
   for i in reversed(range(len(names[name]['children']))):stack.append((names[name]['children'][i],path+[name],edges+[i]))
 # Source groupSetVisBounds propagation is definition-based; traversal emits
 # TRACKER occurrences and must not deduplicate the graph's shared definitions.
 memo={}
 def flags(name,visiting=()):
  if name in memo:return memo[name]
  if name in visiting or len(visiting)>128:raise ValueError('flag cycle/depth')
  d=names[name]
  if d.get('external'):result=(bool(d['flags']&1),bool(d['flags']&2))
  else:result=(bool(d['health_properties']),any(any(flags(n,visiting+(name,))) for n in d['children']))
  memo[name]=result;return result
 occurrences=[];walk_work=0
 for root,name in roots:
  stack=[(name,[],[])]
  while stack:
   name,path,edges=stack.pop();walk_work+=1
   if walk_work>4_000_000 or len(path)>128:raise ValueError('occurrence work/depth')
   d=names[name];own,child=flags(name)
   if d.get('external') and (own or child):raise ValueError('future preload may mutate source graph')
   if own:occurrences.append({'world_id':len(occurrences)+1,'root_slot':root,'names':path+[name],'child_ordinals':edges,'file':d['file'],'slot':d['slot']})
   if child:
    for i in reversed(range(len(d['children']))):stack.append((d['children'][i],path+[name],edges+[i]))
 if oracle_state is not None:
  oracle_state.update(names=names,roots=roots,flags={n:flags(n) for n in witnesses})
 return {'schema':'coh-dynamic-breakable-capture-observation-v1','passed':True,'catalog_sha256':CAT_SHA,'snapshot_sha256':SNAP_SHA,'saved_definitions':len(defs),'active_names':len(names),'health_definition_count':sum(bool(d['health_properties']) for d in defs.values()),'health_definitions':[{'name':d['name'],'file':d['file'],'slot':d['slot'],'properties':d['health_properties'],'root_reachable':d['name'] in witnesses} for d in defs.values() if d['health_properties']],'external':[{'name':d['name'],'flags':d['flags'],'breakable':bool(d['flags']&1),'child_breakable':bool(d['flags']&2),'root_reachable':d['name'] in witnesses,'witness':witnesses.get(d['name'])} for d in externals],'derived_breakable_occurrence_count':len(occurrences),'occurrences':occurrences,'walk_work':walk_work,'scope':'read-only independent raw property/topology projection using already captured source pins; original tracker occurrence oracle still required before admission','dynamic_status_admitted':False,'world_authority':False,'actor_publication':False}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--catalog',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=inspect(a.catalog,a.snapshot);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['saved_definitions','health_definition_count','derived_breakable_occurrence_count','external']}))
