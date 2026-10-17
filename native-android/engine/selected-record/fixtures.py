"""Source child fixtures and explicit raw bit concatenation (not whole outer).
The independent outer source-control oracle is a separate qualification input.
"""
import ctypes as C,hashlib,importlib.util,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Bits:
 def __init__(self,aligned):self.aligned=aligned;self.data=[]
 def scalar(self,width,v):
  width=(width+7)//8*8 if self.aligned else width;self.data.extend((v>>i)&1 for i in range(width))
 def pack(self,width,v):
  if self.aligned:self.scalar(32,v);return
  while width<32 and v>=(1<<width)-1:self.scalar(width,(1<<width)-1);v-=(1<<width)-1;width=min(32,width*2)
  self.scalar(width,v)
 def auto(self,v):
  widths=(2,10,24,32);i=next(i for i,n in enumerate(widths)if v<1<<n);self.scalar(2,i);self.scalar(widths[i],v)
 def append(self,raw,bits,begin=0):self.data.extend((raw[i//8]>>(i%8))&1 for i in range(begin,bits))
 def bytes(self):
  out=bytearray((len(self.data)+7)//8)
  for i,v in enumerate(self.data):out[i//8]|=v<<(i%8)
  return bytes(out)
def build(work):
 base=load('selected_base_entities',HERE/'../entities/check.py');b=work/'base';b.mkdir();lib,pins,names,title,rare=base.oracle(ROOT,b);code=(b/'source-oracle.c').read_text()+(HERE/'oracle_front.h').read_text();(work/'front.c').write_text(code);subprocess.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),'-I'+str(HERE/'../entities'),work/'front.c','-lm','-o',work/'front.so'],check=True);front=C.CDLL(str(work/'front.so'));front.selected_record_front.argtypes=[C.c_uint]*6+[C.c_void_p,C.c_void_p,C.c_void_p]
 # Retained complete costume/power/taskforce provider; its66 small source
 # fixtures execute without replaying old native/emulator/game suites.
 costume=load('selected_costume_provider',HERE/'../entities/costume_oracle.py');helper=load('selected_bits_helper',ROOT/'native-android/tools/protocol_fixture/prepare.py');cw=work/'costume';cw.mkdir();costume_proof=costume.generate(ROOT,cw,helper,base.run);costume_lib=C.CDLL(str(cw/'costume-oracle.so'))
 for name in('original_envelope','original_power_custom','original_taskforce'):setattr(lib,name,getattr(costume_lib,name));getattr(lib,name).argtypes=[C.c_int,C.c_int,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
 # Source complete child body oracles build only; no broad old suite replay.
 buff=load('selected_buff_provider',HERE/'../entities/check_teammate_buffs.py');bw=work/'buff';bw.mkdir();blib,bproof=buff.oracle(bw)
 tail=load('selected_tail_provider',HERE/'../entities/check_very_rare_tail.py');tw=work/'tail';tw.mkdir();tlib,tproof=tail.oracle(tw)
 return front,lib,blib,tlib,{'base_original_source_sha256_lf':pins,'base_extracted_functions':names,'base_titles':title,'base_rare':rare,'costume':costume_proof,'buffs':bproof,'tail':tproof,'front_c_sha256':hashlib.sha256(code.encode()).hexdigest(),'scope':'Component original producer fixtures + explicit synthetic flags/concatenation. No complete original sendEntity, live dictionary/identity, or actor.'}
def simple_record(front,aligned,prefix):
 raw=(C.c_ubyte*262144)();bits=C.c_uint();begin=C.c_uint();front.selected_record_front(0,0,0,0,aligned,prefix,raw,C.byref(bits),C.byref(begin));out=Bits(aligned);out.append(raw,bits.value);out.scalar(1,0) # ragdoll absent
 out.auto(1);out.auto(0);out.auto(0);out.scalar(1,0) # final teammate absent
 return out.bytes(),len(out.data),begin.value
def full_record(front,base,buff,tail,aligned,prefix,scenario):
 # Actual child producers execute; scalar outer fields/concatenation are explicit
 # synthetic composition until separately compared with original outer blocks.
 raw=(C.c_ubyte*262144)();bits=C.c_uint();begin=C.c_uint();front.selected_record_front(1,1,1,1,aligned,prefix,raw,C.byref(bits),C.byref(begin));out=Bits(aligned);out.append(raw,bits.value)
 boundaries={'front_end':len(out.data)};children=[]
 def child(name,fn,args,has_begin=False,expected_size=2*1024*1024):
  wire=(C.c_ubyte*1048576)();length=C.c_uint();start=C.c_uint();expected=(C.c_ubyte*expected_size)();size=C.c_uint()
  if has_begin:fn(*args,wire,C.byref(length),C.byref(start),expected)
  else:fn(*args,wire,C.byref(length),expected,C.byref(size))
  at=len(out.data);out.append(wire,length.value,start.value if has_begin else 0);children.append({'name':name,'begin_bit':at,'end_bit':len(out.data),'source_bits':length.value,'sha256':hashlib.sha256(bytes(wire[:(length.value+7)//8])).hexdigest()})
 child('costume',base.original_envelope,([0,1,7,8][scenario%4],aligned));out.scalar(1,1);out.scalar(8,20);boundaries['costume_end']=len(out.data)
 child('power',base.original_power_custom,([0,2,4,6][scenario%4],aligned));boundaries['power_end']=len(out.data)
 # Complete actual inline title producer, without result projection parameter.
 wire=(C.c_ubyte*32768)();length=C.c_uint();start=C.c_uint();base.original_titles(1,aligned,0,wire,C.byref(length),C.byref(start));at=len(out.data);out.append(wire,length.value,start.value);children.append({'name':'titles','begin_bit':at,'end_bit':len(out.data),'source_bits':length.value,'sha256':hashlib.sha256(bytes(wire[:(length.value+7)//8])).hexdigest()});boundaries['titles_end']=len(out.data)
 out.scalar(1,1);out.scalar(5,2)
 for i in range(6):out.scalar(10,128+i)
 boundaries['ragdoll_end']=len(out.data)
 # Source basic statistics full producer plus source target/inventory producers.
 out.scalar(1,1);out.scalar(1,1);wire=(C.c_ubyte*32768)();length=C.c_uint();stats=(C.c_float*5)();base.original_stats(0,aligned,wire,C.byref(length),stats);out.append(wire,length.value)
 out.auto(3);out.auto(7);out.auto(1);out.auto(8)
 base.original_target(scenario%3,aligned,wire,C.byref(length));out.append(wire,length.value)
 # Complete status grammar through original scalar widths, explicit synthetic
 # descriptions; no whole source status producer is claimed here.
 out.scalar(1,1);out.scalar(10,0x305);out.auto(3);out.auto(7);out.auto(2)
 for text in(b'Held\0',b'SyntheticStatus\0'):
  for value in text:out.scalar(8,value)
 base.original_inventory(1,aligned,wire,C.byref(length));out.append(wire,length.value);boundaries['common_end']=len(out.data)
 child('taskforce',base.original_taskforce,([3,4,6,7][scenario%4],aligned));boundaries['taskforce_end']=len(out.data)
 child('rare',base.original_rare,([0,1,2,7][scenario%4],aligned,0),True,base.original_rare_size());boundaries['rare_end']=len(out.data)
 wire=(C.c_ubyte*262144)();length=C.c_uint();start=C.c_uint();normal=(C.c_ubyte*tail.tail_observation_size())();stale=(C.c_ubyte*tail.tail_observation_size())();tail.tail_original([0,1,8,20][scenario%4],aligned,0,wire,C.byref(length),C.byref(start),normal,stale);at=len(out.data);out.append(wire,length.value,start.value);children.append({'name':'tail','begin_bit':at,'end_bit':len(out.data),'source_bits':length.value,'sha256':hashlib.sha256(bytes(wire[:(length.value+7)//8])).hexdigest()});boundaries['tail_end']=len(out.data)
 wire=(C.c_ubyte*1048576)();length=C.c_uint();start=C.c_uint();normal=(C.c_uint*32768)();stale=(C.c_uint*32768)();nc=C.c_uint();sc=C.c_uint();buff.buffs_original([1,5,6,14][scenario%4],aligned,0,wire,C.byref(length),C.byref(start),normal,C.byref(nc),stale,C.byref(sc));at=len(out.data);out.append(wire,length.value,start.value);children.append({'name':'buff','begin_bit':at,'end_bit':len(out.data),'source_bits':length.value,'sha256':hashlib.sha256(bytes(wire[:(length.value+7)//8])).hexdigest()});boundaries['buff_end']=len(out.data)
 return out.bytes(),len(out.data),begin.value,{'boundaries':boundaries,'children':children,'synthetic_outer_and_status_fields':True,'whole_original_outer_executed':False}
