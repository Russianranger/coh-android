"""Whole original team/league wire senders and consumers with explicit UI shells."""
import ctypes as C,json,re,tempfile
from pathlib import Path
import member_oracle as member
q=member.q;HERE=Path(__file__).resolve().parent
EXTRA=['MapServer/src/container/league.c','libs/UtilitiesLib/src/network/net_packetutil.c','Common/entity/entVarUpdate.h']
def texts():return {**member.texts(),**{p:q.source(p) for p in EXTRA}}
def generate(src):
 code,functions=member.generate(src)
 code=code.replace('typedef struct{int ids[1],onMapserver[1];MemberName names[1];int mapIds[1],oldmapIds[1];} TeamMembers;','typedef struct{int*ids,*onMapserver;MemberName*names;int mapIds[48],oldmapIds[48];int leader,count;} TeamMembers;')
 # Remove standalone member harness, which assumes embedded member arrays.
 code=code[:code.index('void member_fixture(')]
 code=code.replace('typedef struct{char name[64];} Entity;', '''
typedef struct{TeamMembers members;int team_level,team_mentor,activePlayerDbid;} Teamup;
typedef struct{TeamMembers members;int teamLeaderIDs[48],lockStatus[48];} League;
typedef struct{int taskforce_mode,lfg;} PlayerState;
typedef struct{char name[64];int db_id,teamup_id,league_id;PlayerState*pl;Teamup*teamup,*teamup_activePlayer;League*league;} Entity;
''')
 code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',code)
 code+=re.search(r'^#define\s+PKT_BITS_TO_REP_DB_ID[^\n]+',src[EXTRA[2]],re.M).group(0)+'\n'
 for name in ['MAX_TEAM_MEMBERS','MAX_LEAGUE_TEAMS','MAX_LEAGUE_MEMBERS']:code+=re.search(r'^#define\s+'+name+r'[^\n]+',src[member.EXTRA[2]],re.M).group(0)+'\n'
 code+='''
#define INFO_SVR_COM 0
#define devassert(x) assert(x)
#define AINRANGE(i,a) ((i)>=0&&(i)<(int)ARRAY_SIZE(a))
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
static void pktSendIfSetBitsPack(Packet*p,int n,U32 v){pktSendBits(p,1,v!=0);if(v)pktSendBitsPack(p,n,v);}
static U32 pktGetIfSetBitsPack(Packet*p,int n){return pktGetBits(p,1)?pktGetBitsPack(p,n):0;}
static Teamup*createTeamup(void){return calloc(1,sizeof(Teamup));}
static void destroyTeamup(Teamup*t){free(t->members.ids);free(t->members.onMapserver);free(t->members.names);free(t);}
static League*createLeague(void){return calloc(1,sizeof(League));}
static void destroyLeague(League*l){free(l->members.ids);free(l->members.onMapserver);free(l->members.names);free(l);}
static void leagueClearFocusGroup(Entity*e){(void)e;}
static void leagueCheckFocusGroup(Entity*e){(void)e;}
static void leagueOrganizeTeamList(League*l){(void)l;}
static void league_updateTabCount(void){}
static const char*textStd(const char*t,...){return t;}
static void addSystemChatMsg(const char*t,int a,int b){(void)t;(void)a;(void)b;}
static MapName teamMapNames[48],leagueMapNames[48];
'''
 for path,names in [(EXTRA[1],['pktSendBitsAuto','pktGetBitsAuto']),(member.EXTRA[0],['sendTeammate','team_sendList']),(EXTRA[0],['sendLeagueMate','league_sendList']),(member.EXTRA[1],['receiveTeamList','receiveLeagueList'])]:
  for n in names:
   body=q.extract(src[path],n);code+=body;functions[n]={'source':path,'sha256_lf':q.sha(body.encode())}
 code+='''
void team_fixture(U32 scenario,U32 kind,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[16384]={0};Packet p={0};Entity source={0},dest={0};PlayerState sp={0},dp={0};Teamup team={0};League league={0};int ids[48],onmap[48];MemberName names[48];TeamMembers*m=kind?&league.members:&team.members;
 source.pl=&sp;dest.pl=&dp;source.teamup=&team;source.league=&league;source.teamup_activePlayer=&team;sp.taskforce_mode=scenario%4;sp.lfg=scenario*17%1024;team.team_level=scenario*3;team.team_mentor=100;team.activePlayerDbid=102;
 m->ids=ids;m->onMapserver=onmap;m->names=names;m->count=scenario%(kind?49:9);m->leader=100+m->count/3;team.team_mentor=100+m->count/2;m->mapIds[0]=1;
 if(!m->count){source.teamup_id=source.league_id=0;source.league=NULL;}else{source.teamup_id=source.league_id=65537;}
 for(int i=0;i<m->count;i++){ids[i]=100+i;snprintf(names[i],64,"FixtureMate%d",i);m->mapIds[i]=i+1;m->oldmapIds[i]=scenario%2?i+1:0;league.teamLeaderIDs[i]=100+(i/8)*8;league.lockStatus[i]=i%2;}
 server_onmap=(scenario>>1)&1;client_present=1;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);if(kind)league_sendList(&p,&source,(scenario>>2)&1);else team_sendList(&p,&source,(scenario>>2)&1);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 memset(teamMapNames,0,sizeof(teamMapNames));memset(leagueMapNames,0,sizeof(leagueMapNames));p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;if(kind)receiveLeagueList(&p,&dest);else receiveTeamList(&p,&dest);*end=bsGetCursorBitPosition(&p.stream);
 observed[0]=kind?dest.league_id:dest.teamup_id;observed[1]=dp.taskforce_mode;observed[2]=dp.lfg;
 TeamMembers*d=kind?(dest.league?&dest.league->members:NULL):(dest.teamup?&dest.teamup->members:NULL);observed[3]=d?d->leader:0;observed[4]=d?d->count:0;observed[5]=kind?0:dest.teamup?dest.teamup->team_level:0;observed[6]=kind?0:dest.teamup?dest.teamup->team_mentor:0;observed[7]=kind?0:dest.teamup?dest.teamup->activePlayerDbid:0;
 for(int i=0;d&&i<d->count;i++){observed[8+i*4]=d->ids[i];observed[9+i*4]=d->onMapserver[i];observed[10+i*4]=kind?dest.league->teamLeaderIDs[i]:0;observed[11+i*4]=kind?dest.league->lockStatus[i]:0;}
 if(dest.teamup)destroyTeamup(dest.teamup);if(dest.league)destroyLeague(dest.league);
}
'''
 return code,functions

def auto(r):return r.scalar([2,10,24,32][r.scalar(2)])
def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'team-source-pins.json').read_text())!=pins:raise ValueError('source pin mismatch')
 code,functions=generate(src);cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-team-league-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for kind in (0,1):
   for aligned in (0,1):
    for prefix in (range(8) if not aligned else (0,8)):
     for scenario in range(50):
      raw=(C.c_uint8*65536)();bits=C.c_uint32();end=C.c_uint32();obs=(C.c_uint32*200)();lib.team_fixture(scenario,kind,aligned,prefix,raw,C.byref(bits),C.byref(end),obs)
      data=bytes(raw[:(bits.value+7)//8]);r=member.inv.independent.Reader(data,bits.value,aligned,prefix);identity=r.packed(22) if r.scalar(1) else 0;expected={'id':identity}
      if not kind:expected.update(taskforce=r.scalar(2),lfg=r.scalar(10))
      rows=[]
      if identity:
       expected['leader']=r.packed(32);count=r.packed(1)
       if not kind:expected.update(level=auto(r),mentor=auto(r),active=auto(r))
       for i in range(count):
        row={'dbid':r.scalar(32),'onmap':r.scalar(1)}
        if not row['onmap']:
         row['changed']=r.scalar(1)
         if row['changed']:row.update(name=r.string(64).decode(),map=r.string(256).decode())
        if kind:row.update(team_leader=r.scalar(32),locked=r.scalar(32))
        rows.append(row)
       assert obs[3]==expected['leader']==100+count//3 and obs[4]==count==scenario%(49 if kind else 9)
       first=count//3 if kind else count//2;order=[first]+[i for i in range(count) if i!=first]
       for i,row in enumerate(rows):
        assert obs[8+i*4]==row['dbid']==100+order[i] and obs[9+i*4]==row['onmap']
        if not row['onmap']:
         assert row['changed']==int(not scenario%2 or bool((scenario>>2)&1))
         if row['changed']:assert row['name']==f'FixtureMate{order[i]}' and row['map']=='FixtureLocalizedAtlas'
       if kind:
        for i,row in enumerate(rows):assert obs[10+i*4]==row['team_leader']==100+(order[i]//8)*8 and obs[11+i*4]==row['locked']==order[i]%2
       else:assert list(obs[5:8])==[expected['level'],expected['mentor'],expected['active']]==[scenario*3,100+count//2,102]
      if not kind:assert obs[1]==expected['taskforce']==scenario%4 and obs[2]==(0 if len(rows)>1 else expected['lfg'])
      assert r.cursor==bits.value==end.value and obs[0]==identity
      expected['members']=rows;cases.append(dict(kind='league' if kind else 'team',scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=end.value,wire_hex=data.hex(),expected=expected))
 return dict(schema='coh-team-league-source-oracle-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),scope='whole original team/league producers and consumers; explicit earray/storage/localization/entity/UI callback shells',dictionary_authority=False,original_oracle_sanitized=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'team-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
