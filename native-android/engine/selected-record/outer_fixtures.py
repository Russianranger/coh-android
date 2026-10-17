"""Original outer source control with separately qualified real child spans.

Whole sendEntity executes with immutable span adapters, not the original child
object graph. Selected record index17 and prior sent-index16 are fixture-only.
Every injected leaf now comes from its separately qualified original producer.
"""
import ctypes as C,hashlib,json,struct
from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def generate(work):
 f=load('outer_record_fixture_components',HERE/'fixtures.py');observer=load('outer_record_child_observer',HERE/'outer_components.py');front,unused,buff,unused_tail,childproof=f.build(work)
 front.selected_record_leaf.argtypes=[C.c_uint]*3+[C.c_void_p]*3
 libs={};observed={}
 for kind,path in [('base',work/'base/source-oracle.c'),('costume',work/'costume/costume-oracle.c'),('tail',work/'tail/tail-original.c')]:libs[kind],observed[kind]=observer.build(ROOT,work,kind,path)
 base,cost,tail=libs['base'],libs['costume'],libs['tail'];order=load('selected_outer_order',ROOT/'native-android/combined-client/diagnostics/selected-record-order-20261017/order_oracle.py');ow=work/'outer';ow.mkdir();outer,outerproof=order.build(ROOT,ow);leaf_provider=load('selected_record_exact_leaves',ROOT/'native-android/combined-client/diagnostics/selected-record-order-20261017/leaf_oracle.py');lw=work/'leaves';lw.mkdir();leaf,leafproof=leaf_provider.build(ROOT,lw)
 raw=(C.c_ubyte*262144)();bits=C.c_uint();begin=C.c_uint();expected=(C.c_ubyte*(2*1024*1024))();other=(C.c_ubyte*(2*1024*1024))();size=C.c_uint();relocations=0;profiles={};rows=[];packetproof=[]
 def cut(data,start,end):
  b=f.Bits(False);b.append(data,end,start);return b.bytes(),end-start
 for aligned in(0,1):
  for variant in range(4):
   canonical={}
   for offset in(range(8)if not aligned else(0,)):
    leaves={}
    for ident in(1,2,3,4,6,7,8):front.selected_record_leaf(ident,aligned,offset,raw,C.byref(bits),C.byref(begin));leaves[ident]=cut(raw,begin.value,bits.value)
    cost.selected_set_fixture_prefix(offset)
    for ident,name,scenario in[(9,'original_envelope',[0,1,7,8][variant]),(10,'original_power_custom',[0,2,4,6][variant])]:getattr(cost,name)(scenario,aligned,raw,C.byref(bits),expected,C.byref(size));leaves[ident]=cut(raw,offset,bits.value)
    cost.original_taskforce([1,4,6,7][variant],aligned,raw,C.byref(bits),expected,C.byref(size))
    for ident in(16,17):data,n,mod=observer.span(cost,ident,bytes(raw));leaves[ident]=(data,n)
    base.selected_set_fixture_prefix(offset);values=(C.c_float*5)();base.original_stats(0,aligned,raw,C.byref(bits),values);b=f.Bits(aligned);b.scalar(1,1);b.scalar(1,1);b.append(raw,bits.value,offset);leaves[12]=(b.bytes(),len(b.data))
    base.original_target(variant%3,aligned,raw,C.byref(bits));leaves[13]=cut(raw,offset,bits.value)
    base.original_inventory(1,aligned,raw,C.byref(bits));leaves[15]=cut(raw,offset,bits.value)
    base.original_rare([0,1,2,7][variant],aligned,offset,raw,C.byref(bits),C.byref(begin),expected)
    for ident in(18,19):data,n,mod=observer.span(base,ident,bytes(raw));leaves[ident]=(data,n)
    tail.tail_original([1,3,4,17][variant],aligned,offset,raw,C.byref(bits),C.byref(begin),expected,other)
    for ident in(20,21,22):data,n,mod=observer.span(tail,ident,bytes(raw));leaves[ident]=(data,n)
    normal=(C.c_uint*32768)();stale=(C.c_uint*32768)();nc=C.c_uint();sc=C.c_uint();buff.buffs_original([1,5,6,7][variant],aligned,offset,raw,C.byref(bits),C.byref(begin),normal,C.byref(nc),stale,C.byref(sc));leaves[23]=cut(raw,begin.value,bits.value)
    for ident,kind,scenario in((5,3,[0,0,2,3][variant]),(11,2,variant),(12,1,0),(14,4,variant)):
     end=C.c_uint();leaf.original_record_leaf(kind,scenario,aligned,offset,raw,C.byref(bits),C.byref(begin),C.byref(end))
     if end.value!=bits.value:raise ValueError('leaf cursor mismatch')
     leaves[ident]=cut(raw,begin.value,end.value)
    if not offset:canonical=leaves
    else:
     for ident,value in leaves.items():
      if value!=canonical[ident]:raise ValueError('original child is not bit-relocatable '+str((ident,variant,offset)))
      relocations+=1
   profiles[aligned,variant]=canonical
  for scenario in range(16):
   leaves=profiles[aligned,scenario%4];backing=[];outer.record_clear_children()
   for ident,(data,n)in leaves.items():
    if n>65536:raise ValueError('original outer adapter per-child cap '+str((ident,aligned,scenario,n)))
    a=(C.c_ubyte*len(data)).from_buffer_copy(data);backing.append(a);outer.record_set_child(ident,a,n,255)
   for prefix in(range(8)if not aligned else(0,)):
    bounds=(C.c_uint*28)();events=(C.c_uint*72)();count=C.c_uint();outer.record_outer(scenario,aligned,prefix,raw,C.byref(bits),C.byref(begin),bounds,events,C.byref(count));data=bytes(raw[:(bits.value+7)//8]);rows.append((data,bits.value,begin.value,aligned,scenario,list(bounds[:26])));packetproof.append({'scenario':scenario,'aligned':aligned,'prefix':prefix,'begin_bit':begin.value,'end_bit':bits.value,'packet_sha256':hashlib.sha256(data).hexdigest(),'boundaries':list(bounds),'child_events':[list(events[i*3:i*3+3])for i in range(count.value)]})
 wire=work/'outer-fixtures.bin'
 with wire.open('wb')as out:
  out.write(struct.pack('<I',len(rows)))
  for data,bits,begin,aligned,scenario,bounds in rows:out.write(struct.pack('<31I',len(data),bits,begin,aligned,scenario,*bounds));out.write(data)
 return wire,{'whole_original_outer':outerproof,'original_component_providers':childproof,'observed_child_producers':observed,'all_bit_offsets_child_payload_equality_checks':relocations,'count':len(rows),'sha256':hashlib.sha256(wire.read_bytes()).hexdigest(),'packets':packetproof,'explicit_scalar_fixture_children':[],'exact_additional_original_leaves':leafproof,'selected_self_stats_profile':'Whole original entSendCharacterStats with self/full_update1; whole ParserSendEmptyDiff force-all-fields with the actual basic schema.','original_child_object_graph_bound_to_outer_objects':False,'scope':'Whole original outer source control + real separately qualified original child payloads. Original children are injected borrowed spans, not called with the original outer objects. Synthetic dictionary/selected identity only. No whole-engine, live entity, actor or ACK claim.'}
