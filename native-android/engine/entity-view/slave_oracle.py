"""Exact slave send/receive blocks; outer ownership/control-client conditions not executed."""
import ctypes as C,json,struct,tempfile
from pathlib import Path
def block(text,start):
 begin=text.index(start);brace=text.index('{',begin);depth=1;end=brace+1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[begin:end]+'\n'
def qualify(sky,work):
 q=sky.q;src=sky.texts();pins={n:q.sha(src[n].encode()) for n in sky.EXTRA}
 if pins!=json.loads((Path(__file__).parent/'slave-source-pins.json').read_text()):raise ValueError('slave source pins changed')
 send=block(src[sky.EXTRA[0]],'if(controlClient){');send+='else{\n'+next(s for s in src[sky.EXTRA[0]][src[sky.EXTRA[0]].index('if(controlClient){'):].splitlines() if 'pktSendBits(pak, 1, 0);' in s)+'\n}\n'
 receive=block(src[sky.EXTRA[1]][src[sky.EXTRA[1]].index('// Receive the QROT for a slave.'):],'if(pktGetBits(pak, 1))')
 code,_,_=q.generate(src);code+='''
typedef struct{struct{struct{F32 cur[3];}pyr;}controls;}SlaveControl;
static struct{struct{F32 cur[3];}pyr;}control_state;
static void slave_send(Packet*pak,SlaveControl*controlClient){
'''+send+'}\nstatic void slave_receive(Packet*pak){\n'+receive+'''}
void slave_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[4096]={0};Packet p={0};SlaveControl client={{{{(float)((int)scenario-5)/3.f,(float)scenario*2.f,-(float)scenario/7.f}}}};memset(&control_state,0,sizeof(control_state));initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);slave_send(&p,scenario%2?&client:NULL);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;slave_receive(&p);*end=bsGetCursorBitPosition(&p.stream);memcpy(observed,control_state.pyr.cur,12);
}
'''
 (work/'slave.c').write_text(code);q.run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),work/'slave.c','-o',work/'slave.so']);lib=C.CDLL(str(work/'slave.so'));cases=[]
 for mode in (0,1):
  for prefix in (range(8) if not mode else (0,8)):
   for scenario in range(10):
    data=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();observed=(C.c_uint32*3)();lib.slave_fixture(scenario,mode,prefix,data,C.byref(bits),C.byref(end),observed);raw=bytes(data[:(bits.value+7)//8]);r=sky.inv.independent.Reader(raw,bits.value,mode,prefix);present=r.scalar(1);words=[r.scalar(32) for _ in range(3)] if present else [0]*3;assert r.cursor==bits.value==end.value and list(observed)==words
    if present:
     # Each explicit float fixture is rounded in original C; exact emitted words
     # independently decoded above and compared to unchanged receiver storage.
     assert words[1]==struct.unpack('<I',struct.pack('<f',scenario*2.))[0]
    cases.append(dict(scenario=scenario,aligned=mode,begin_bit=prefix,end_bit=end.value,wire_hex=raw.hex(),expected={'present':present,'words':words}))
 return {'scope':'exact original slave conditional send/receive blocks and original bitstream functions; outer control-client selection/ownership not executed','source_sha256_lf':pins,'send_block_sha256':q.sha(send.encode()),'receive_block_sha256':q.sha(receive.encode()),'generated_source_sha256':q.sha(code.encode()),'cases':cases,'cases_count':len(cases),'original_oracle_sanitized':False,'camera_or_character_authority':False}
