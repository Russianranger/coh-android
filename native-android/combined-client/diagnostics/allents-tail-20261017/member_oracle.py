"""Exact team/league shared member producer/consumer and retained-state cases."""
import ctypes as C,json,re,tempfile
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
EXTRA=['MapServer/src/container/team.c','Game/src/UI/uiNet.c','Common/entity/teamCommon.h']
def texts():return {p:q.source(p) for p in q.PATHS+EXTRA}
def generate(src):
 code,functions,_=q.generate(src);code=re.sub(r'\bEntity\b','OuterEntity',code)
 membername=re.search(r'typedef char MemberName\[[^\]]+\];',src[EXTRA[2]]).group(0)
 code+=membername+'''
typedef char MapName[256];
typedef struct{int ids[1],onMapserver[1];MemberName names[1];int mapIds[1],oldmapIds[1];} TeamMembers;
typedef struct{char name[64];} Entity;
static Entity mate={"FixtureLocalMate"};static unsigned server_onmap,client_present;
static Entity*entFromDbId(int id){(void)id;return server_onmap&&client_present?&mate:NULL;}
static char*getTranslatedMapName(int id){(void)id;return "FixtureLocalizedAtlas";}
'''
 for path,name in [(EXTRA[0],'sendMemberCommon'),(EXTRA[1],'recieveMemberCommon')]:
  body=q.extract(src[path],name);code+=body;functions[name]={'source':path,'sha256_lf':q.sha(body.encode())}
 code+='''
void member_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed,char*name,char*map){
 U32 memory[4096]={0};Packet p={0};TeamMembers s={0},d={0};MapName maps[1]={"PreviousMap"};s.ids[0]=123456+scenario;s.mapIds[0]=7;s.oldmapIds[0]=scenario%2?7:6;strcpy(s.names[0],"FixtureRemoteMate");strcpy(d.names[0],"PreviousName");
 server_onmap=(scenario>>1)&1;client_present=1;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);sendMemberCommon(&p,&s,0,(scenario>>2)&1);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 client_present=!((scenario>>3)&1);p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;recieveMemberCommon(&p,&d,0,maps);*end=bsGetCursorBitPosition(&p.stream);observed[0]=d.ids[0];observed[1]=d.onMapserver[0];observed[2]=s.oldmapIds[0];strcpy(name,d.names[0]);strcpy(map,maps[0]);
}
'''
 return code,functions
def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'member-source-pins.json').read_text())!=pins:raise ValueError('source pin mismatch')
 code,functions=generate(src);cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-team-member-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(16):
     raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();obs=(C.c_uint32*3)();name=C.create_string_buffer(64);mapname=C.create_string_buffer(256);lib.member_fixture(scenario,aligned,prefix,raw,C.byref(bits),C.byref(end),obs,name,mapname)
     data=bytes(raw[:(bits.value+7)//8]);r=inv.independent.Reader(data,bits.value,aligned,prefix);dbid=r.scalar(32);onmap=r.scalar(1);changed=None;wire_name=wire_map=None
     if not onmap:
      changed=r.scalar(1)
      if changed:wire_name=r.string(64).decode();wire_map=r.string(256).decode()
     expected_name='FixtureLocalMate' if onmap and not scenario&8 else wire_name if changed else 'PreviousName';expected_map=wire_map if changed else 'PreviousMap'
     assert r.cursor==bits.value==end.value and obs[0]==dbid==123456+scenario and obs[1]==(onmap and not scenario&8) and name.value.decode()==expected_name and mapname.value.decode()==expected_map
     assert obs[2]==(7 if changed or scenario%2 else 6)
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=end.value,wire_hex=data.hex(),expected={'dbid':dbid,'onmap_wire':onmap,'changed':changed,'wire_name':wire_name,'wire_map':wire_map,'applied_name':expected_name,'applied_map':expected_map,'applied_onmap':obs[1]}))
 return dict(schema='coh-team-league-member-source-oracle-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),scope='whole shared member sender/consumer with explicit map localization/entity DBID fixtures and previous-state names; no whole team/league transaction',dictionary_authority=False,original_oracle_sanitized=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'member-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
