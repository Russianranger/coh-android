"""Original initial-create outer controls with real, separately bound children."""
import ctypes as C,hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];SELECTED=HERE/'../selected-record';ORDER=ROOT/'native-android/combined-client/diagnostics/selected-record-order-20261017'
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def digest(b):return hashlib.sha256(b).hexdigest()
def build(work):
 f=load('initial_child_baseline',SELECTED/'fixtures.py');observe=load('initial_child_observe',SELECTED/'outer_components.py');front,base_unused,buff,tail_unused,proof=f.build(work)
 front.selected_record_leaf.argtypes=[C.c_uint]*3+[C.c_void_p]*3
 create_code=(work/'base/source-oracle.c').read_text()+(HERE/'fixture_create.h').read_text();(work/'create.c').write_text(create_code);subprocess.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE/'../entities'),work/'create.c','-lm','-Wl,-z,defs','-o',work/'create.so'],check=True);create=C.CDLL(str(work/'create.so'));create.initial_create_fixture.argtypes=[C.c_uint]*7+[C.c_void_p]*3
 libs={};observers={}
 for kind,path in [('base',work/'base/source-oracle.c'),('costume',work/'costume/costume-oracle.c'),('tail',work/'tail/tail-original.c')]:libs[kind],observers[kind]=observe.build(ROOT,work,kind,path)
 cost=libs['costume'];leafmod=load('initial_exact_leaves',ORDER/'leaf_oracle.py');lw=work/'leaf';lw.mkdir();leaf,leafproof=leafmod.build(ROOT,lw)
 # A fixture-only different viewed entity selects the genuine original
 # entSendCharacterStats nonself branch; original serializer bodies unchanged.
 leaf_code=(lw/'leaf-source.c').read_text();body=observe.extract(leaf_code,'original_record_leaf');other=body.replace('void original_record_leaf(','void initial_other_record_leaf(',1).replace('entSendCharacterStats(&p,&e,&e,scenario!=1);','LeafStatsEntity viewed={0};entSendCharacterStats(&p,&e,&viewed,scenario!=1);');leaf_code+='\n'+other;(work/'other-leaves.c').write_text(leaf_code);subprocess.run(['cc','-std=gnu99','-O0','-fwrapv','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE/'../entities'),work/'other-leaves.c','-lz','-lm','-o',work/'other-leaves.so'],check=True);other_leaf=C.CDLL(str(work/'other-leaves.so'));other_leaf.initial_other_record_leaf.argtypes=leaf.original_record_leaf.argtypes
 generic=load('initial_generic_outer',ORDER/'generic_order.py');gw=work/'generic';gw.mkdir();outer,outerproof=generic.build(ROOT,gw)
 proof={'original_components':proof,'observed_original_children':observers,'exact_leaf_source':leafproof,'whole_original_outer':outerproof,'create_generated_sha256':digest(create_code.encode()),'nonself_stats_generated_sha256':digest(leaf_code.encode()),'scope':'Whole original INITIAL sendEntity control and separately qualified actual original child writers. Fixture objects/identity/dictionaries are synthetic and independent across child adapters, not a whole engine or runtime object graph.'}
 return Generator(f,observe,front,create,libs,buff,leaf,other_leaf,outer,proof)
class Generator:
 def __init__(self,f,observe,front,create,libs,buff,leaf,other_leaf,outer,proof):
  self.f=f;self.observe=observe;self.front=front;self.create=create;self.libs=libs;self.buff=buff;self.leaf=leaf;self.other_leaf=other_leaf;self.outer=outer;self.proof=proof;self.cache={};self.relocations=0
 def cut(self,raw,begin,end):
  b=self.f.Bits(False);b.append(raw,end,begin);return b.bytes(),end-begin
 def children(self,profile,variant,aligned):
  key=profile,variant,aligned
  if key in self.cache:return self.cache[key]
  raw=(C.c_ubyte*262144)();bits=C.c_uint();begin=C.c_uint();expected=(C.c_ubyte*(2*1024*1024))();other=(C.c_ubyte*(2*1024*1024))();size=C.c_uint();base,cost,tail=self.libs['base'],self.libs['costume'],self.libs['tail'];canonical={}
  for offset in(range(8)if not aligned else(0,)):
   leaves={}
   for ident in(2,3,4,6,7,8):self.front.selected_record_leaf(ident,aligned,offset,raw,C.byref(bits),C.byref(begin));leaves[ident]=self.cut(raw,begin.value,bits.value)
   cost.selected_set_fixture_prefix(offset)
   envelope=([0,1,7,8][variant]if not profile else 2 if profile==1 else 3 if profile==2 else 4 if profile==3 else 5)
   power=([0,2,4,6][variant]if not profile else 1 if profile==1 else 3 if profile==2 else 5)
   for ident,name,scenario in((9,'original_envelope',envelope),(10,'original_power_custom',power)):
    getattr(cost,name)(scenario,aligned,raw,C.byref(bits),expected,C.byref(size));leaves[ident]=self.cut(raw,offset,bits.value)
   if not profile:
    cost.original_taskforce([1,4,6,7][variant],aligned,raw,C.byref(bits),expected,C.byref(size))
    for ident in(16,17):data,n,_=self.observe.span(cost,ident,bytes(raw));leaves[ident]=(data,n)
   base.selected_set_fixture_prefix(offset);base.original_target(variant%3,aligned,raw,C.byref(bits));leaves[13]=self.cut(raw,offset,bits.value)
   if not profile:base.original_inventory(1,aligned,raw,C.byref(bits));leaves[15]=self.cut(raw,offset,bits.value)
   base.original_rare([0,1,2,7][variant],aligned,offset,raw,C.byref(bits),C.byref(begin),expected)
   for ident in(18,19):data,n,_=self.observe.span(base,ident,bytes(raw));leaves[ident]=(data,n)
   tail.tail_original([1,3,4,17][variant]if not profile else 8,aligned,offset,raw,C.byref(bits),C.byref(begin),expected,other)
   for ident in(20,21,22):data,n,_=self.observe.span(tail,ident,bytes(raw));leaves[ident]=(data,n)
   normal=(C.c_uint*32768)();stale=(C.c_uint*32768)();nc=C.c_uint();sc=C.c_uint();self.buff.buffs_original([1,5,6,7][variant]if not profile else 0,aligned,offset,raw,C.byref(bits),C.byref(begin),normal,C.byref(nc),stale,C.byref(sc));leaves[23]=self.cut(raw,begin.value,bits.value)
   for ident,kind,scenario in((5,3,[0,0,2,3][variant]),(11,2,variant),(12,1,2 if profile==4 else 0),(14,4,variant)):
    end=C.c_uint();fn=self.other_leaf.initial_other_record_leaf if profile and ident==12 else self.leaf.original_record_leaf;fn(kind,scenario,aligned,offset,raw,C.byref(bits),C.byref(begin),C.byref(end));leaves[ident]=self.cut(raw,begin.value,end.value)
   if not offset:canonical=leaves
   else:
    for ident,value in leaves.items():
     if value!=canonical[ident]:raise ValueError('child relocation mismatch '+str((profile,variant,ident,offset)))
     self.relocations+=1
  self.cache[key]=canonical;return canonical
 def record(self,profile,variant,aligned,prefix=0,index=17,previous=16,entity_id=91,dbid=None,pet=False,scenario=None):
  leaves=dict(self.children(profile,variant,aligned));raw=(C.c_ubyte*262144)();bits=C.c_uint();begin=C.c_uint();dbid=(4242 if not profile else 5000+entity_id)if dbid is None else dbid;type_=2 if profile<2 else 4 if profile==2 else 1 if profile==3 else 3
  # Establish create payload relocation directly with its actual original
  # producer at all offsets before giving the adapter a relocation permit.
  first=None
  for offset in(range(8)if not aligned else(0,)):
   self.create.initial_create_fixture(type_,not profile,pet,entity_id,dbid,aligned,offset,raw,C.byref(bits),C.byref(begin));value=self.cut(raw,begin.value,bits.value)
   if first is None:first=value
   elif first!=value:raise ValueError('create relocation changed')
   else:self.relocations+=1
  leaves[1]=first;backing=[];self.outer.record_clear_children()
  for ident,(data,n)in leaves.items():
   if n>65536:raise ValueError('child exceeds preserved original outer fixture cap')
   a=(C.c_ubyte*len(data)).from_buffer_copy(data);backing.append(a);self.outer.record_set_child(ident,a,n,255)
  self.outer.record_generic_indices(index,previous);events=(C.c_uint*72)();count=C.c_uint();self.outer.record_generic_outer(profile,variant if scenario is None else scenario,aligned,prefix,raw,C.byref(bits),C.byref(begin),events,C.byref(count));wire=bytes(raw[:(bits.value+7)//8]);event_rows=[list(events[i*3:i*3+3])for i in range(count.value)]
  return wire,bits.value,begin.value,{'profile':profile,'variant':variant,'scenario':variant if scenario is None else scenario,'index':index,'previous':previous,'entity_id':entity_id,'dbid':dbid if type_==2 else 0,'type':type_,'begin_bit':begin.value,'end_bit':bits.value,'events':event_rows,'sha256':digest(wire)}
def generate(work):
 import struct
 g=build(work);record_rows=[];record_proof=[]
 for aligned in(0,1):
  for profile in range(5):
   for scenario in range(16):
    for prefix in(range(8)if not aligned else(0,)):
     wire,bits,begin,p=g.record(profile,scenario%4,aligned,prefix,entity_id=91+profile,scenario=scenario);record_rows.append((wire,bits,begin,aligned,p));record_proof.append(p)
 # Original bit writers emit the exact signed-delta field and canonical
 # sentinel field sequence. This is explicit list composition, not execution
 # of the large entSendUpdate object/visibility/command producer.
 base=g.libs['base'];base.original_fields.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p]
 def fields(aligned,widths,values):
  raw=(C.c_ubyte*4096)();n=C.c_uint();w=(C.c_int*len(widths))(*widths);v=(C.c_uint*len(values))(*(x&0xffffffff for x in values));base.original_fields(w,v,len(widths),aligned,raw,C.byref(n));return bytes(raw[:(n.value+7)//8]),n.value
 list_rows=[];list_proof=[]
 def make_list(label,specs,aligned,prefix=0,capacity=256,status=0,trailer=True,mutation=None,end_delta=0):
  out=g.f.Bits(aligned)
  if prefix:out.scalar(prefix,0)
  begin=len(out.data);previous=-1;rows=[];proof=[]
  for spec in specs:
   profile,index,entity,dbid=spec[:4];variant=spec[4]if len(spec)>4 else 0;scenario=spec[5]if len(spec)>5 else variant
   start=len(out.data);delta,n=fields(aligned,[-1],[index-previous-1]);out.append(delta,n);body_start=len(out.data)
   source_previous=previous if previous>=0 else 0;source_delta,source_delta_bits=fields(aligned,[-1],[index-source_previous-1]);source_prefix=0 if aligned else(body_start-source_delta_bits)%8
   wire,bits,body,p=g.record(profile,variant,aligned,source_prefix,index,source_previous,entity,dbid,scenario=scenario);out.append(wire,bits,body)
   row=[index,entity,dbid if p['type']==2 else 0,p['type'],int(profile==0),start,len(out.data)];rows.append(row);proof.append({'original_record':p,'list_begin_bit':start,'list_body_bit':body_start,'list_end_bit':len(out.data),'signed_delta':index-previous-1})
   if mutation and len(rows)==mutation[0]:
    if mutation[1]=='noncreate':out.data[body_start]=0
    elif mutation[1]=='veryrare':
     source_create_end=next(e[2]for e in p['events']if e[0]==1);at=body_start+source_create_end-body+2*(8 if aligned else 1);out.data[at]=0
    elif mutation[1]=='partialpose':
     source_pos_start=next(e[1]for e in p['events']if e[0]==3);at=body_start+source_pos_start-body;out.data[at:at+(8 if aligned else 3)]=[1]+[0]*((8 if aligned else 3)-1)
    else:raise ValueError('unknown malformed control')
   previous=index
  endwire,endbits=fields(aligned,[-1,1,1],[end_delta,1,1]);out.append(endwire,endbits);end=len(out.data)
  if trailer:out.scalar(32,0xaabbccdd)
  wire=out.bytes();list_rows.append((wire,len(out.data),begin,aligned,rows,capacity,status,end));list_proof.append({'label':label,'aligned':aligned,'prefix':prefix,'capacity':capacity,'expected_status':status,'count':len(rows),'begin_bit':begin,'end_bit':end,'transport_bits':len(out.data),'trailer_present':trailer,'mutation':mutation,'records':proof,'sha256':digest(wire)})
 for aligned in(0,1):
  prefixes=range(8)if not aligned else(0,8)
  for prefix in prefixes:
   make_list('single-selected-at-max',[(0,10239,91,4242)],aligned,prefix)
   make_list('negative-and-forward-indices',[(0,17,91,4242),(1,7,92,5000,1),(4,3,93,0,2),(2,10239,94,0,3)],aligned,prefix)
   make_list('npc-before-selected',[(3,3,100,0),(2,5,101,0,1),(1,7,102,5001,2),(0,17,103,4242,3)],aligned,prefix)
  cases=[('missing-selected',[(1,7,91,5000)],7,None,0,256),('duplicate-self',[(0,17,91,4242),(0,7,92,4242)],7,None,0,256),('selected-dbid-other-player',[(0,17,91,4242),(1,7,92,4242)],7,None,0,256),('duplicate-server-generation',[(0,17,91,4242),(3,7,91,0)],7,None,0,256),('duplicate-other-player-dbid',[(0,17,91,4242),(1,7,92,5000),(1,3,93,5000)],7,None,0,256),('duplicate-slot',[(0,17,91,4242),(3,17,92,0)],1,None,0,256),('later-noncreate',[(0,17,91,4242),(3,7,92,0)],2,(2,'noncreate'),0,256),('later-not-full-rare',[(0,17,91,4242),(3,7,92,0)],2,(2,'veryrare'),0,256),('later-partial-position',[(0,17,91,4242),(3,7,92,0)],7,(2,'partialpose'),0,256),('noncanonical-end-delta',[(0,17,91,4242)],1,None,1,256),('capacity-refusal',[(0,17,91,4242),(3,7,92,0)],4,None,0,1),('empty-initial',[],7,None,0,256)]
  for label,specs,status,mutation,enddelta,capacity in cases:make_list(label,specs,aligned,status=status,mutation=mutation,end_delta=enddelta,capacity=capacity)
  maximum=[(3,j+1,1000+j,0)for j in range(255)]+[(0,10239,2000,4242)]
  make_list('existing-256-record-bound',maximum,aligned,trailer=True)
  make_list('257-record-refusal',[(3,j+1,1000+j,0)for j in range(256)]+[(0,10239,2000,4242)],aligned,status=4)
 file=work/'initial-fixtures.bin'
 with file.open('wb')as f:
  f.write(struct.pack('<I',len(record_rows)))
  for wire,bits,begin,aligned,p in record_rows:
   f.write(struct.pack('<12I',len(wire),bits,begin,aligned,p['profile'],p['variant'],p['scenario'],p['index'],p['entity_id'],p['dbid'],p['type'],len(p['events'])))
   for event in p['events']:f.write(struct.pack('<3I',*event))
   f.write(wire)
  f.write(struct.pack('<I',len(list_rows)))
  for wire,bits,begin,aligned,rows,capacity,status,end in list_rows:
   f.write(struct.pack('<8I',len(wire),bits,begin,aligned,len(rows),capacity,status,end))
   for row in rows:f.write(struct.pack('<7I',*row))
   f.write(wire)
 send=(ROOT/'upstream/ouroboros/MapServer/src/entity/entsend.c').read_text();a=send.index('    // send end of ent list message');b=send.index('\n\n',a);endblock=send[a:b]
 return file,{'source_providers':g.proof,'record_cases':len(record_rows),'list_cases':len(list_rows),'child_relocation_equalities':g.relocations,'fixture_sha256':digest(file.read_bytes()),'record_projections':record_proof,'list_projections':list_proof,'original_list_end_block_sha256_lf':digest(endblock.encode()),'original_list_end_block':endblock,'scope':'Original full-create outer functions and separately source-qualified component writer bytes. List delta/sentinel fields use original bit writers in explicit fixture composition; whole entSendUpdate/visibility/objectgraph/runtime semantics not executed. No authentic dictionary/actor/ACK authority.'}
