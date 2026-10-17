"""Whole original supergroup producer and independent bounded wire projection."""
import ctypes as C,json,re,tempfile
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
EXTRA=['MapServer/src/entity/SgrpServer.c','Common/entity/Supergroup.h','libs/UtilitiesLib/src/network/net_packetutil.c','Common/entity/entVarUpdate.h']
def texts():return {p:q.source(p) for p in q.PATHS+EXTRA}
def generate(src):
 code,functions,_=q.generate(src);code=re.sub(r'\bEntity\b','OuterEntity',code);code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',code)
 header=src[EXTRA[1]]
 for n in ['SG_NAME_LEN','SG_TITLE_LEN','SG_MESSAGE_LEN','SG_MOTTO_LEN','SG_DESCRIPTION_LEN','MAX_SUPER_GROUP_MEMBERS','MAX_SUPERGROUP_ALLIES','NUM_SG_RANKS']:code+=re.search(r'^#define\s+'+n+r'[^\n]+',header,re.M).group(0)+'\n'
 code+=re.search(r'typedef enum sgroupPermissionEnum\s*\{.*?\}\s*sgroupPermissionEnum;',header,re.S).group(0)+'\n'
 for n in ['SupergroupRank','SupergroupAlly','SupergroupStats']:code+=re.search(r'typedef struct '+n+r'\s*\{.*?\}\s*'+n+r';',header,re.S).group(0)+'\n'
 # Stats contains non-wire map metadata; original type is merely forward-declared.
 code=code.replace('typedef struct SupergroupRank','typedef struct StaticMapInfo StaticMapInfo;\ntypedef struct SupergroupRank',1)
 code+=re.search(r'^#define\s+PKT_BITS_TO_REP_DB_ID[^\n]+',src[EXTRA[3]],re.M).group(0)+'\n'
 code+='''
#define AINRANGE(i,a) ((i)>=0&&(i)<(int)ARRAY_SIZE(a))
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
static int eaSize(void*p){void**a=*(void***)p;return a?(int)(intptr_t)a[-1]:0;}
typedef struct{int dbid,rank;} SupergroupMemberInfo;
typedef struct{int influence,prestige,prestigeBase,prestigeAddedUpkeep;struct{int prtgRentDue,secsRentDueDate;}upkeep;int playerType;char name[SG_NAME_LEN],motto[SG_MOTTO_LEN],msg[SG_MESSAGE_LEN],emblem[64],description[SG_DESCRIPTION_LEN];U32 colors[2];int tithe,spacesForItemsOfPower;U32 demoteTimeout;SupergroupRank rankList[NUM_SG_RANKS];U32 entryPermission;SupergroupMemberInfo**memberranks;SupergroupAlly allies[MAX_SUPERGROUP_ALLIES];U32 alliance_minTalkRank;} Supergroup;
typedef struct{Supergroup*supergroup;SupergroupStats**sgStats;int supergroup_update;} Entity;
'''
 for path,names in [(q.PATHS[7],['bsWriteBitsArray']),(EXTRA[2],['pktSendBitsAuto','pktGetBitsAuto'])]:
  for n in names:
   body=q.extract(src[path],n);code+=body;functions[n]={'source':path,'sha256_lf':q.sha(body.encode())}
 code+='static void pktSendBitsArray(Packet*p,int n,void*v){bsWriteBitsArray(&p->stream,n,v);}\n'
 body=q.extract(src[EXTRA[0]],'sgroup_sendList');code+=body;functions['sgroup_sendList']={'source':EXTRA[0],'sha256_lf':q.sha(body.encode())}
 code+='''
void superstats_constants(U32*out){out[0]=NUM_SG_RANKS;out[1]=sizeof(((SupergroupRank*)0)->permissionInt);out[2]=MAX_SUPERGROUP_ALLIES;out[3]=SG_PERM_COUNT;}
void superstats_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits){
 U32 memory[32768]={0};Packet p={0};Supergroup sg={0};Entity e={&sg,NULL,scenario%2};SupergroupStats stats[MAX_SUPER_GROUP_MEMBERS]={0};SupergroupStats*rows[MAX_SUPER_GROUP_MEMBERS+1];SupergroupMemberInfo ranks[8];SupergroupMemberInfo*rankrows[9];int count=scenario%6==5?MAX_SUPER_GROUP_MEMBERS:scenario%6;
 rows[0]=(SupergroupStats*)(intptr_t)count;e.sgStats=rows+1;for(int i=0;i<count;i++){rows[i+1]=&stats[i];SupergroupStats*s=&stats[i];snprintf(s->name,32,"FixtureSG%d",i);s->db_id=1000+i;s->rank=i%NUM_SG_RANKS;s->level=i%51;s->last_online=0x12345678u+i;s->online=i%2;strcpy(s->arch,"Class_Fixture");strcpy(s->origin,"Origin_Fixture");s->member_since=0x87654321u+i;s->prestige=i*300;s->playerType=i%3;strcpy(s->zone,"FixtureAtlas");}
 sg.influence=scenario*65537;sg.prestige=scenario*12345;sg.prestigeBase=scenario*15;sg.prestigeAddedUpkeep=scenario+5;sg.upkeep.prtgRentDue=scenario*7;sg.upkeep.secsRentDueDate=scenario*300;sg.playerType=scenario%3;
 strcpy(sg.name,"FixtureSGName");strcpy(sg.motto,"FixtureMotto");strcpy(sg.msg,"FixtureMessage");strcpy(sg.emblem,"FixtureEmblem");strcpy(sg.description,"FixtureDescription");sg.colors[0]=0xffabcdef;sg.colors[1]=0x80000001;sg.tithe=scenario;sg.spacesForItemsOfPower=scenario*2;sg.demoteTimeout=0xdeadbeef;
 for(int i=0;i<NUM_SG_RANKS;i++){snprintf(sg.rankList[i].name,SG_TITLE_LEN,"FixtureRank%d",i);for(unsigned j=0;j<ARRAY_SIZE(sg.rankList[i].permissionInt);j++)sg.rankList[i].permissionInt[j]=0xfedcba98u+i+j;}
 sg.entryPermission=scenario*31;int n=scenario%9;rankrows[0]=(SupergroupMemberInfo*)(intptr_t)n;sg.memberranks=rankrows+1;for(int i=0;i<n;i++){rankrows[i+1]=&ranks[i];ranks[i].dbid=65537+i;ranks[i].rank=i%NUM_SG_RANKS;}
 for(int i=0;i<MAX_SUPERGROUP_ALLIES;i++)if((scenario+i)%2){sg.allies[i].db_id=2000+i;sg.allies[i].dontTalkTo=i%2;sg.allies[i].minDisplayRank=i%NUM_SG_RANKS;snprintf(sg.allies[i].name,SG_NAME_LEN,"FixtureAlly%d",i);}sg.alliance_minTalkRank=scenario%NUM_SG_RANKS;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);sgroup_sendList(&p,&e,(scenario>>1)&1);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
}
'''
 return code,functions

def auto(r):return r.scalar([2,10,24,32][r.scalar(2)])
def decode(data,bits,aligned,prefix,constants):
 r=inv.independent.Reader(data,bits,aligned,prefix);count=r.packed(1);result={'count':count}
 if count:
  result['financial']=[r.packed(1) for _ in range(7)];update=r.scalar(1);result['update']=update
  if update:
   members=[]
   for i in range(count):
    m={'name':r.string(32).decode(),'dbid':r.packed(1),'rank':r.packed(1),'level':r.packed(1),'last_online':r.scalar(32),'online':r.scalar(1),'arch':r.string(32).decode(),'origin':r.string(32).decode(),'member_since':r.scalar(32),'prestige':r.scalar(32),'player_type':r.packed(1)}
    if m['online']:m['zone']=r.string(256).decode()
    members.append(m)
   result['members']=members;result['strings']=[r.string(n).decode() for n in [64,256,256,64,512]];result['colors_tithe_spaces']=[r.packed(1) for _ in range(4)];result['demote_timeout']=r.scalar(32);ranks=[]
   for _ in range(constants[0]):
    name=r.string(64).decode()
    # Original bsWriteBitsArray always rounds cursor to byte boundary.
    r.cursor=(r.cursor+7)//8*8
    if r.cursor>r.bits:raise inv.independent.Refused('array alignment')
    permissions=[r.scalar(8) for _ in range(constants[1])];ranks.append({'name':name,'permission_bytes':permissions})
   result['ranks']=ranks;result['entry_permission']=auto(r);result['memberranks']=[[r.packed(22),r.packed(1)] for _ in range(r.packed(1))];allies=[]
   for _ in range(constants[2]):
    ally={'dbid':r.scalar(32)}
    if ally['dbid']:ally.update(dont_talk=r.scalar(1),min_display_rank=auto(r),name=r.string(64).decode())
    allies.append(ally)
   result['allies']=allies;result['alliance_min_talk_rank']=auto(r)
 if r.cursor!=bits:raise ValueError('source producer cursor mismatch')
 return result

def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'superstats-source-pins.json').read_text())!=pins:raise ValueError('source pin mismatch')
 code,functions=generate(src);cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-superstats-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'));const=(C.c_uint32*4)();lib.superstats_constants(const);constants=list(const);assert constants==[7,4,10,22],constants
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(18):
     raw=(C.c_uint8*131072)();bits=C.c_uint32();lib.superstats_fixture(scenario,aligned,prefix,raw,C.byref(bits));data=bytes(raw[:(bits.value+7)//8]);expected=decode(data,bits.value,aligned,prefix,constants)
     assert expected['count']==(150 if scenario%6==5 else scenario%6)
     if expected['count']:
      assert expected['financial']==[scenario*65537,scenario*12345,scenario*15,scenario+5,scenario*7,scenario*300,scenario%3]
      assert expected['update']==int(bool(scenario%2 or ((scenario>>1)&1)))
      if expected['update']:
       for i,m in enumerate(expected['members']):
        value={'name':f'FixtureSG{i}','dbid':1000+i,'rank':i%7,'level':i%51,'last_online':0x12345678+i,'online':i%2,'arch':'Class_Fixture','origin':'Origin_Fixture','member_since':0x87654321+i,'prestige':i*300,'player_type':i%3}
        if i%2:value['zone']='FixtureAtlas'
        assert m==value
       assert expected['strings']==['FixtureSGName','FixtureMotto','FixtureMessage','FixtureEmblem','FixtureDescription'] and expected['colors_tithe_spaces']==[0xffabcdef,0x80000001,scenario,scenario*2] and expected['demote_timeout']==0xdeadbeef
       assert expected['ranks']==[{'name':f'FixtureRank{i}','permission_bytes':list((0xfedcba98+i).to_bytes(4,'little'))} for i in range(7)]
       assert expected['entry_permission']==scenario*31 and expected['memberranks']==[[65537+i,i%7] for i in range(scenario%9)] and expected['alliance_min_talk_rank']==scenario%7
       for i,ally in enumerate(expected['allies']):assert ally==({'dbid':2000+i,'dont_talk':i%2,'min_display_rank':i%7,'name':f'FixtureAlly{i}'} if (scenario+i)%2 else {'dbid':0})
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=bits.value,wire_hex=data.hex(),expected=expected))
 return dict(schema='coh-superstats-source-producer-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),constants={'ranks':7,'permission_bytes':4,'allies':10,'permission_enum_count':22},cases=cases,cases_count=len(cases),scope='whole original sender and independent bounded raw model; original receiveSuperStats is source-ledger pinned but not executed here',original_consumer_executed=False,dictionary_authority=False,original_oracle_sanitized=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'superstats-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
