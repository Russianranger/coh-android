"""Unchanged original sky-fade sender/consumer with finite fixture values."""
import ctypes as C,json,re,struct,tempfile
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
EXTRA=['MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c']
def texts():return {p:q.source(p) for p in q.PATHS+EXTRA}
def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'sky-source-pins.json').read_text())!=pins:raise ValueError('source pins changed')
 code,functions,_=q.generate(src);code+='''
#define bool int
static struct{U32 skyFadeInteresting;F32 skyFadeWeight;U32 skyFade1,skyFade2;}server_state;
static U32 projected[3];
static void sunSetSkyFadeClient(int a,int b,F32 weight){projected[0]=a;projected[1]=b;memcpy(projected+2,&weight,4);}
static int demoIsRecording(void){return 0;}
static void demoRecordSkyFile(int a,int b,F32 c){(void)a;(void)b;(void)c;assert(0);}
'''
 for path,n in [(EXTRA[0],'sendSkyFade'),(EXTRA[1],'receiveSkyFade')]:
  body=q.extract(src[path],n);code+=body;functions[n]={'source':path,'sha256_lf':q.sha(body.encode())}
 code+='''
void sky_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[4096]={0};Packet p={0};server_state.skyFadeInteresting=scenario%2;server_state.skyFadeWeight=(float)((int)scenario-8)/4.f;server_state.skyFade1=scenario*300;server_state.skyFade2=scenario*65537;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);sendSkyFade(&p);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;receiveSkyFade(&p);*end=bsGetCursorBitPosition(&p.stream);memcpy(observed,projected,sizeof(projected));
}
'''
 cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-sky-oracle-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(20):
     raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();obs=(C.c_uint32*3)();lib.sky_fixture(scenario,aligned,prefix,raw,C.byref(bits),C.byref(end),obs);data=bytes(raw[:(bits.value+7)//8]);r=inv.independent.Reader(data,bits.value,aligned,prefix);present=r.scalar(1)
     values=[0,1,0]
     if present:weight=r.scalar(32);values=[r.packed(2),r.packed(2),weight]
     expected=[scenario*300,scenario*65537,struct.unpack('<I',struct.pack('<f',(scenario-8)/4))[0]] if scenario%2 else [0,1,0]
     assert r.cursor==bits.value==end.value and list(obs)==values==expected
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=end.value,wire_hex=data.hex(),expected={'interesting':present,'sky1':values[0],'sky2':values[1],'weight_word':values[2]}))
 return dict(schema='coh-sky-source-oracle-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),scope='whole original sky sender/consumer with callback projection only; actual sky-file dictionary/resource application not executed',original_oracle_sanitized=False,dictionary_authority=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'sky-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
