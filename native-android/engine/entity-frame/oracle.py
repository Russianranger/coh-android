"""Reused unchanged source component producers; synthetic framing joins only."""
import ctypes as C,hashlib,importlib.util,json,struct,sys
from pathlib import Path
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def sha(data):return hashlib.sha256(data).hexdigest()
def build(root,work):
 entities=root/'native-android/engine/entities';control=root/'native-android/engine/entity-control'
 entity=module('frame_entity_source',entities/'check.py');ctl=module('frame_control_source',control/'check.py')
 ew=work/'entities';cw=work/'control';ew.mkdir();cw.mkdir();elib,pins,functions,titles,rare=entity.oracle(root,ew);clib,control_proof=ctl.oracle(root,cw)
 ecode=(ew/'source-oracle.c').read_text();listbody=entity.extract(ecode,'original_list');newlist=listbody.replace('original_list(int scenario,int aligned,','frame_original_list(int scenario,int aligned,int prefix,').replace(' initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);',' initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);if(prefix)bsWriteBits(&p.stream,prefix,0);')
 deletebody=entity.extract(ecode,'original_deletes');newdelete=deletebody.replace('original_deletes(int aligned,','frame_original_deletes(int aligned,int prefix,').replace(' initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);',' initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);if(prefix)bsWriteBits(&p.stream,prefix,0);')
 (ew/'frame.c').write_text(ecode+newlist+newdelete);entity.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(entities),ew/'frame.c','-lm','-o',ew/'frame.so']);elib=C.CDLL(str(ew/'frame.so'));elib.original_fields.argtypes=[C.c_void_p,C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
 elib.frame_original_list.argtypes=[C.c_int,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)];elib.frame_original_deletes.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
 ccode=(cw/'original.c').read_text();cb=ctl.extract(ccode,'original_send');newcontrol=cb.replace('original_send(','frame_control_send(').replace('svrPlayerSendControlState(&p,&e,&link,scenario==4);','svrPlayerSendControlState(&p,&e,&link,1);')
 (cw/'frame.c').write_text(ccode+newcontrol);ctl.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),'-I'+str(control),cw/'frame.c','-lm','-o',cw/'frame.so']);clib=C.CDLL(str(cw/'frame.so'));clib.frame_control_send.argtypes=[C.c_int,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)];clib.original_receive.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_int,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.POINTER(C.c_uint32)]
 def fields(mode,prefix,legacy,variant):
  widths=[prefix,-1,-1,1,-1,32,-1,-1,-1,32,32,32,-1,32,32,1];values=[0,8 if legacy else 3,77,0 if variant==6 else 1,11,struct.unpack('<I',struct.pack('<f',-3.5))[0],12,0xffffffff,13,*[struct.unpack('<I',struct.pack('<f',n))[0] for n in (1.,2.,3.)],0,0xfedcba98,0x87654321,0 if variant==5 else 1]
  if variant==5:widths.extend([1,1,2,2]);values.extend([1,1,2,1])
  if variant==7:values[4]=99
  data=(C.c_uint8*32768)();bits=C.c_uint32();elib.original_fields((C.c_int*len(widths))(*widths),(C.c_uint32*len(values))(*values),len(widths),mode,data,C.byref(bits));return bytes(data[:(bits.value+7)//8]),prefix,bits.value
 def part(function,args):
  data=(C.c_uint8*32768)();bits=C.c_uint32();function(*args,data,C.byref(bits));return bytes(data[:(bits.value+7)//8]),args[-1],bits.value
 lines=[];rows=[];cases=[];roundtrips=0
 for mode in (0,1):
  for prefix in ((0,3,7) if not mode else (0,8)):
   for legacy in (0,1):
    for variant in range(8):
     for control_choice in ([1,2,4,7,8] if variant==0 else [[1,2,4,7,8][variant%5]]):
      bits=[0]*prefix
      def append(part):
       data,begin,end=part;bits.extend((data[i//8]>>(i%8))&1 for i in range(begin,end))
      append(fields(mode,prefix,legacy,variant));header=len(bits);scenario={0:3,1:0,2:1,3:2,4:4,5:3,6:3,7:3}[variant];append(part(elib.frame_original_list,(scenario,mode,len(bits)%8)));list_end=len(bits)
      cs=control_choice;control_part=part(clib.frame_control_send,(cs,mode,len(bits)%8));append(control_part);control_end=len(bits)
      data,start,end=control_part;raw=(C.c_uint8*len(data)).from_buffer_copy(data);state=(C.c_uint8*clib.original_state_size())();events=(C.c_uint8*clib.original_update_size())();cursor=C.c_uint32();clib.original_receive(raw,end,mode,start,10,0,state,events,C.byref(cursor));assert cursor.value==end;roundtrips+=1
      append(part(elib.frame_original_deletes,(mode,len(bits)%8)));end=len(bits)
      # Deliberate unread future-body marker; no whole suffix or packet-end claim.
      for i in range(32):bits.append((0x13579bdf>>i)&1)
      raw=bytearray((len(bits)+7)//8)
      for i,b in enumerate(bits):raw[i//8]|=b<<(i%8)
      name='wire_'+str(len(rows));lines.append('static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};');rows.append('{'+name+',sizeof('+name+'),'+','.join(map(str,[prefix,len(bits),header,list_end,control_end,end,mode,legacy,variant,scenario,cs]))+'}');cases.append({'mode':mode,'prefix':prefix,'legacy':legacy,'variant':variant,'list_scenario':scenario,'control_scenario':cs,'header_end':header,'list_end':list_end,'control_end':control_end,'end':end})
 return '\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+',\n'.join(rows)+'};\n',{'scope':'Original entity component producers and original complete control producer/TEST_CLIENT consumer; synthetic list/body/header concatenation, not whole original sendEntity/entSendUpdate/entReceiveUpdate or live capture. Header fields use original bit writers and pinned replication shortcut types.','entity_source_sha256_lf':pins,'entity_original_functions':functions,'control':control_proof,'fixture_list_before_sha256':sha(listbody.encode()),'fixture_list_prefix_adapter_sha256':sha(newlist.encode()),'fixture_deletes_before_sha256':sha(deletebody.encode()),'fixture_deletes_prefix_adapter_sha256':sha(newdelete.encode()),'fixture_control_full_state_adapter_sha256':sha(newcontrol.encode()),'control_original_consumer_roundtrips':roundtrips,'cases':cases,'original_oracle_sanitized':False,'selected_dbid_fixture_only':4242,'whole_original_enclosing_producer_consumer_executed':False}
