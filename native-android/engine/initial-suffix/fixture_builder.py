"""Exact bit concatenation of independently original-source-produced bodies."""
import ctypes as C,importlib.util,json,sys
from pathlib import Path
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class Bits:
 def __init__(self,mode,prefix):self.mode=mode;self.bits=[0]*prefix
 def scalar(self,v,n):self.bits.extend((v>>i)&1 for i in range((n+7)//8*8 if self.mode else n))
 def append(self,c):
  raw=bytes.fromhex(c['wire_hex']);self.bits.extend((raw[i//8]>>(i%8))&1 for i in range(c['begin_bit'],c['end_bit']))
 def raw(self):
  result=bytearray((len(self.bits)+7)//8)
  for i,b in enumerate(self.bits):result[i//8]|=b<<(i%8)
  return bytes(result)
def case(data,bits,prefix):return dict(wire_hex=bytes(data[:(bits+7)//8]).hex(),begin_bit=prefix,end_bit=bits)
def choose(proof,mode,prefix,scenario=None,predicate=None,kind=None):
 return next(c for c in proof['cases'] if c['aligned']==mode and c['begin_bit']==prefix and (scenario is None or c['scenario']==scenario) and (predicate is None or predicate(c)) and (kind is None or c['kind']==kind))
def build(root,oracle_root,work):
 entities=root/'native-android/engine/entities';globals=root/'native-android/engine/entity-globals';sys.path.insert(0,str(entities));import check_character_initial as initial
 provider=oracle_root/'native-android/combined-client/diagnostics';sys.path.insert(0,str(provider/'character-outer-20261017'));sys.path.insert(0,str(provider/'allents-tail-20261017'))
 import group4_oracle as g4,group56_oracle as g56,qualify_outer as q
 import update_oracle as inv,active_invention_oracle as invention,team_oracle as team,superstats_oracle as sg,attribute_monitor_oracle as attrib,dynamic_wire_oracle as dyn,sky_oracle as sky
 power=module('suffix_power',globals/'check_power_info.py');modes=module('suffix_modes',globals/'check.py');badges=module('suffix_badges',globals/'check_badges.py');workshop=module('suffix_workshop',root/'native-android/engine/entity-inventory/check.py');slave=module('suffix_slave',root/'native-android/engine/entity-view/slave_oracle.py')
 spaces={n:work/n for n in ['initial','power','modes','badges']}
 for p in spaces.values():p.mkdir()
 ilib,iproof=initial.oracle(spaces['initial']);plib,pproof=power.oracle(root,spaces['power']);mlib,mproof=modes.oracle(root,spaces['modes']);blib,bproof=badges.oracle(spaces['badges'])
 texts={p:q.source(p) for p in q.PATHS};proofs={'initial':iproof,'power_info':pproof,'power_modes':mproof,'badges':bproof,'ui':g4.qualify(texts),'tail':g56.qualify({p:q.source(p) for p in q.PATHS+g56.EXTRA}),'inventory':inv.qualify(),'invention':invention.qualify(),'team':team.qualify(),'superstats':sg.qualify(),'attributes':attrib.qualify(),'dynamic':dyn.qualify(),'sky':sky.qualify(),'slave':slave.qualify(sky,work)}
 # Exact original workshop source statement oracle; generate fresh byte fixtures
 # from its already-qualified original library rather than re-encoding strings.
 workshop_proof=workshop.workshop(q,work);wlib=C.CDLL(str(work/'workshop.so'));proofs['workshop']=workshop_proof
 def initial_case(mode,prefix):
  data=(C.c_uint8*262144)();offsets=(C.c_uint32*5)();words=(C.c_uint32*15)();auth=(C.c_uint8*128)();stats=(C.c_float*16)();integers=(C.c_int32*6)();ilib.initial_fixture(1,mode,prefix,data,offsets,words,auth,stats,integers);return case(data,offsets[0],prefix)
 def power_case(mode,prefix,scenario):
  data=(C.c_uint8*65536)();bits=C.c_uint32();plib.original_power_info(scenario,mode,prefix,data,C.byref(bits));return case(data,bits.value,prefix)
 def modes_case(mode,prefix,scenario):
  data=(C.c_uint8*32768)();bits=C.c_uint32();flag=C.c_uint32();mlib.original_send(scenario%2,scenario%8,mode,prefix,data,C.byref(bits),C.byref(flag));assert flag.value==0;return case(data,bits.value,prefix)
 def badge_case(mode,prefix,scenario):
  data=(C.c_uint8*262144)();bits=C.c_uint32();badge_bits=C.c_uint32();observed=(C.c_uint8*41612)();blib.badge_original(scenario,mode,prefix,data,C.byref(bits),C.byref(badge_bits),observed);return case(data,bits.value,prefix),badge_bits.value
 def workshop_case(mode,prefix):
  data=(C.c_uint8*4096)();bits=C.c_uint32();end=C.c_uint32();wlib.workshop_fixture(mode,prefix,data,C.byref(bits),C.byref(end));assert bits.value==end.value;return case(data,bits.value,prefix)
 lines=[];rows=[];cases=[]
 for mode in (0,1):
  for prefix in ((0,3,7) if not mode else (0,8)):
   for scenario in range(8):
    for control in ((0,1,2,3) if scenario==0 else (0,)):
     b=Bits(mode,prefix);spans=[]
     def finish(begin):spans.append((begin,len(b.bits)))
     begin=len(b.bits);b.append(initial_case(mode,len(b.bits)%8));b.append(choose(proofs['ui'],mode,len(b.bits)%8,scenario%6));b.append(choose(proofs['tail'],mode,len(b.bits)%8,scenario%10));finish(begin)
     begin=len(b.bits);b.append(power_case(mode,len(b.bits)%8,scenario%7));finish(begin)
     begin=len(b.bits);b.append(modes_case(mode,len(b.bits)%8,scenario));finish(begin)
     begin=len(b.bits);badge,badge_end=badge_case(mode,len(b.bits)%8,scenario%12);data=bytes.fromhex(badge['wire_hex']);b.append(dict(wire_hex=data.hex(),begin_bit=badge['begin_bit'],end_bit=badge_end));finish(begin)
     begin=len(b.bits);b.append(dict(wire_hex=data.hex(),begin_bit=badge_end,end_bit=badge['end_bit']));finish(begin)
     begin=len(b.bits);b.append(choose(proofs['inventory'],mode,len(b.bits)%8,scenario));b.append(choose(proofs['invention'],mode,len(b.bits)%8,predicate=lambda c:c['expected']['status_change']==int(control==1)));b.append(workshop_case(mode,len(b.bits)%8));finish(begin)
     begin=len(b.bits);b.scalar(int(control==3),1)
     if control!=3:b.append(choose(proofs['team'],mode,len(b.bits)%8,scenario,kind='team'))
     b.append(choose(proofs['superstats'],mode,len(b.bits)%8,scenario));b.scalar(0,1);b.append(choose(proofs['team'],mode,len(b.bits)%8,scenario,kind='league'));finish(begin)
     begin=len(b.bits);present=1 if control==2 else scenario%2;b.scalar(present,1)
     if present:
      if control==2:b.scalar(0,1);b.scalar(1,1)
      else:b.append(choose(proofs['attributes'],mode,len(b.bits)%8,scenario%12))
     finish(begin)
     begin=len(b.bits);dynamic=choose(proofs['dynamic'],mode,len(b.bits)%8,scenario%16);b.append(dynamic);finish(begin)
     begin=len(b.bits);b.append(choose(proofs['sky'],mode,len(b.bits)%8,scenario%20));b.append(choose(proofs['slave'],mode,len(b.bits)%8,scenario%10));finish(begin)
     raw=b.raw();name='wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[prefix,len(b.bits),mode,scenario,control,dynamic['expected_world_count']]))+',{'+','.join('{'+str(a)+','+str(z)+'}' for a,z in spans)+'}}');cases.append(dict(mode=mode,prefix=prefix,scenario=scenario,control=control,bits=len(b.bits),spans=spans))
 for p in proofs.values():p.pop('cases',None)
 return '\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n',{'original':proofs,'cases':cases,'scope':'Synthetic bit concatenation of separately original-produced components at matching absolute bit offsets; not whole original entSendUpdate/entReceiveUpdate execution. Controls1active invention,2fullattribute header,3impossible fullupdate team skip are refusal cases.'}
def bytes_c(data):return '{'+','.join(map(str,data))+'}'
