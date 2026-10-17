#!/usr/bin/env python3
"""Every full attribute field and modifier compared to original consumer views."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,struct,tempfile,types,sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();sha=lambda b:hashlib.sha256(b).hexdigest()
pins=json.loads((HERE/'source-pins.json').read_bytes());extra=[HERE/'check.py',HERE/'source-pins.json'];start={**pins,**{str(x.relative_to(ROOT)):sha(x.read_bytes())for x in extra}}
assert all(sha((ROOT/k).read_bytes())==v for k,v in start.items())
m=types.ModuleType('full_attrib_admitted');m.__file__=str(HERE/'oracle.py');exec(compile((HERE/'oracle.py').read_bytes(),m.__file__,'exec'),m.__dict__)
rows=json.loads((HERE/'ordered-rows.json').read_bytes())['ordered_sender_rows'];assert len({x['lookup_key']for x in rows})==69
word=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
def namehash(s):
 h=0
 for x in s.encode():h=(h*33+x)&0xffffffff
 return h
cases=[];checks=0
with tempfile.TemporaryDirectory(prefix='coh-full-attribute-')as d:
 lib,original=m.build(ROOT,Path(d));Reader=sys.modules['independent'].Reader
 for aligned in [0,1]:
  for prefix in ([0]if aligned else range(8)):
   for scenario in range(16):
    out=C.create_string_buffer(32768);bits=C.c_uint();end=C.c_uint();fields=(C.c_uint*210)();mods=(C.c_uint*257)();lib.attribute_full(scenario,aligned,prefix,out,C.byref(bits),C.byref(end),fields,mods);wire=out.raw[:(bits.value+7)//8];r=Reader(wire,bits.value,aligned,prefix)
    target=scenario%3!=0;assert [r.scalar(1),r.scalar(1),r.scalar(1)]==[scenario%2,1,int(target)];checks+=3
    if target:assert r.scalar(32)==888;checks+=1
    assert list(fields[:3])==[scenario%2,0,888 if target else 0];checks+=3;expectedrows=[]
    for i,row in enumerate(rows):
     key=row['lookup_key'];v=word((key-scenario)/16);buff=(key+scenario)&3
     assert [r.scalar(32),r.scalar(2)]==[v,buff]and list(fields[3+i*3:6+i*3])==[key,v,buff];checks+=5;expectedrows.append({'lookup_key':key,'value_word':v,'buff':buff})
    want=[];count=0 if scenario==15 else scenario%9
    for i in range(count):
     if scenario%5==1 and i==1 or scenario%5==2 and i==2 or scenario%5==3 and i==3:continue
     key=rows[i]['lookup_key'];power=[0,3,1023,0xf1234567][i%4];srctype=[0,1,2,3,3][i%5];name=['','','source player','source critter','source NPC display'][i%5];svrid=[0,0,45,46,47][i%5]
     assert r.scalar(1)==1 and r.packed(10)==key;bin=r.scalar(2);assert r.scalar([2,10,24,32][bin])==power;assert r.scalar(2)==srctype;checks+=4
     if srctype in [2,3]:assert r.string(256)==name.encode() and r.packed(20)==svrid;checks+=2
     chance=word((i+1)/8);mag=word(-(i+1)*2.5);assert [r.scalar(32),r.scalar(32)]==[chance,mag];checks+=2
     j=len(want);observed=list(mods[1+j*8:1+j*8+7]);assert observed==[power,srctype,svrid,chance,mag,namehash(name),key],(scenario,i,observed,[power,srctype,svrid,chance,mag,namehash(name),key]);checks+=7
     want.append(dict(hash=key,power=power,source_type=srctype,name=name,server_id=svrid,chance_word=chance,magnitude_word=mag))
    assert r.scalar(1)==0 and r.cursor==bits.value==end.value and mods[0]==len(want);checks+=4
    cases.append(dict(scenario=scenario,aligned=aligned,begin=prefix,end=end.value,wire_hex=wire.hex(),new_target=scenario%2,target_owner=888 if target else None,rows=expectedrows,modifiers=want))
assert all(sha((ROOT/k).read_bytes())==v for k,v in start.items())
a.output.write_text(json.dumps({'passed':True,'checks':checks,'cases':cases,'source_sha256':start,'original':original,'scope':'whole original four full attribute functions plus basepower/Auto under explicit gameplay value,modhash,target,powerlookup,UI,earray and allocator observers; exact69row schema candidate','original_gameplay_value_or_dictionary_or_stash_executed':False,'original_attribute_postprocessor_executed':False,'original_consumer_contribution_merge_executed':False,'source_fixture_consumer_allocations_zeroed_and_freed':True,'original_code_sanitized':False,'real_server_client_world_actor_ack':False},indent=2)+'\n');print(json.dumps({'cases':len(cases),'checks':checks}))
