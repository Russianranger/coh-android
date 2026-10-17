"""Original dynamic-group producer with bounded diagnostic zlib decode."""
import ctypes as C,json,re,tempfile,zlib
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
EXTRA=['MapServer/src/group/groupdynsend.c','Common/group/groupdyn.h','libs/UtilitiesLib/src/network/netcomp.c']
def texts():return {p:q.source(p) for p in q.PATHS+EXTRA}
def decode(data,bits,aligned,prefix,expected_count,raw_limit=65536,zip_limit=1024*1024):
 if not 0<=expected_count<=raw_limit:raise ValueError('unbound world count')
 r=inv.independent.Reader(data,bits,aligned,prefix);count=r.packed(1);result={'modified_count':count}
 if count==0xffffffff:
  compressed=r.packed(1);raw=r.packed(1)
  if compressed>zip_limit or raw>raw_limit or raw!=expected_count:raise ValueError('compressed/world count bound')
  r.cursor=(r.cursor+7)//8*8
  if r.cursor>bits or compressed*8>bits-r.cursor:raise ValueError('compressed payload truncated')
  payload=data[r.cursor//8:r.cursor//8+compressed];r.cursor+=compressed*8
  stream=zlib.decompressobj();out=stream.decompress(payload,raw+1)
  if len(out)!=raw or not stream.eof or stream.unused_data or stream.unconsumed_tail:raise ValueError('zlib exact envelope')
  result.update(raw_bytes=raw,status=[[b&127,b>>7] for b in out])
 else:
  if count>65536:raise ValueError('delta count cap')
  rows=[]
  for _ in range(count):
   idx=r.packed(16)
   if idx>=expected_count:raise ValueError('delta world ownership index')
   rows.append([idx,r.scalar(7),r.scalar(1)])
  result['delta']=rows
 if r.cursor!=bits:raise ValueError('dynamic exact end')
 return result

def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'dynamic-wire-source-pins.json').read_text())!=pins:raise ValueError('source pins changed')
 code,functions,_=q.generate(src);header=src[EXTRA[1]];code+='\n#include <zlib.h>\n'
 for n in ['GRPDYN_HP_BITS','GRPDYN_REPAIR_BITS','GROUP_DYN_FULL_UPDATE']:code+=re.search(r'^#define '+n+r'[^\n]+',header,re.M).group(0)+'\n'
 code+=re.search(r'typedef struct\s*\{\s*U8\s+hp\s*:.*?\}\s*DynGroupStatus;',header,re.S).group(0)+'\n'
 for path,ns in [(q.PATHS[7],['bsWriteBitsArray'])]:
  for n in ns:
   body=q.extract(src[path],n);code+=body;functions[n]={'path':path,'sha256_lf':q.sha(body.encode())}
 code+='static void pktSendBitsArray(Packet*p,int n,void*v){bsWriteBitsArray(&p->stream,n,v);}\n'
 for n in ['pktSendZippedAlready','pktSendZipped']:
  body=q.extract(src[EXTRA[2]],n);code+=body;functions[n]={'path':EXTRA[2],'sha256_lf':q.sha(body.encode())}
 code+='static int net_modified_groups[256],net_modified_count,dyn_rescan_breakable,dyn_group_count;static DynGroupStatus*dyn_group_status;\n'
 body=q.extract(src[EXTRA[0]],'groupDynSend');code+=body;functions['groupDynSend']={'path':EXTRA[0],'sha256_lf':q.sha(body.encode())}
 code+='''
void dynamic_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*result,U32*world_count){
 U32 memory[32768]={0};Packet p={0};DynGroupStatus status[256];dyn_group_status=status;dyn_group_count=scenario%4==0?0:scenario%4==1?1:scenario%4==2?9:256;*world_count=dyn_group_count;
 for(int i=0;i<dyn_group_count;i++){status[i].hp=(scenario+i)%128;status[i].repair=(scenario+i)%2;net_modified_groups[i]=dyn_group_count-1-i;}
 net_modified_count=scenario%3?dyn_group_count:0;dyn_rescan_breakable=(scenario>>2)&1;initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);*result=groupDynSend(&p,(scenario>>3)&1);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
}
'''
 cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-dynamic-wire-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-lz','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(16):
     raw=(C.c_uint8*131072)();bits=C.c_uint32();result=C.c_uint32();world=C.c_uint32();lib.dynamic_fixture(scenario,aligned,prefix,raw,C.byref(bits),C.byref(result),C.byref(world));data=bytes(raw[:(bits.value+7)//8]);expected=decode(data,bits.value,aligned,prefix,world.value)
     if scenario&12:
      assert result.value==1 and expected['status']==[[(scenario+i)%128,(scenario+i)%2] for i in range(world.value)]
     else:
      assert expected['delta']==([[i,(scenario+i)%128,(scenario+i)%2] for i in reversed(range(world.value))] if scenario%3 else []) and result.value==bool(expected['delta'])
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=bits.value,wire_hex=data.hex(),expected_world_count=world.value,expected=expected))
 return dict(schema='coh-dynamic-wire-source-producer-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),scope='whole original groupDynSend and pktSendZipped, synthetic source status arrays; bounded independent diagnostic zlib decoder; no original gameplay consumer execution',world_count_authentication=False,original_oracle_sanitized=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'dynamic-wire-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
