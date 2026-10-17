"""Whole original group5/6 inline wire bodies and helper functions with explicit UI/storage shells."""
import argparse,ctypes as C,json,re,tempfile
from pathlib import Path
import qualify_outer as q
import group56_independent as independent
EXTRA=['Common/entity/entVarUpdate.h','Common/entity/chatSettings.c','MapServer/src/entity/friends.c','Game/src/UI/uiChat.c','Common/chatdefs.h','MapServer/src/entity/keybinds.h','Common/entity/RewardToken.h','Common/entity/gametypes.h','Common/entity/entPlayer.h','libs/UtilitiesLib/src/network/net_packetutil.c']
HERE=q.HERE

def generate(texts):
 pins={p:q.sha(t.encode()) for p,t in texts.items()}
 pinfile=HERE/'group56-source-pins.json'
 if json.loads(pinfile.read_text())!=pins:raise ValueError('group56 original source pins changed')
 code,functions,schema=q.generate(texts);code=code.replace('compress,ordered,ordered_id;','compress,ordered,ordered_id,id;')
 def get(path,n):
  body=q.extract(texts[path],n);functions[n]={'source':path,'sha256_lf':q.sha(body.encode())};return body
 def enum(path,name):return re.search(r'typedef enum(?: '+name+r')?\s*\{[^{}]*\}\s*'+name+r';',texts[path],re.S).group(0)+'\n'
 def struct(path,name):return re.search(r'typedef struct '+name+r'\s*\{.*?\}\s*'+name+r';',texts[path],re.S).group(0)+'\n'
 def define(path,name):return re.search(r'^#define\s+'+name+r'\s+[^\n]+',texts[path],re.M).group(0)+'\n'
 definitions='\n#define SERVER 1\n'+enum('Common/entity/entVarUpdate.h','INFO_BOX_MSGS')+define('Common/entity/entVarUpdate.h','SYSTEM_CHANNEL_BITFIELD_SIZE')
 for name in ['MAX_CHAT_WINDOWS','MAX_CHAT_CHANNELS','MAX_CHAT_TABS','MAX_TAB_NAME_LEN']:definitions+=define('Common/entity/chatSettings.h',name)
 definitions+=define('Common/chatdefs.h','MAX_CHANNELNAME')
 for name in ['ChatWindowSettings','ChatTabSettings','ChatChannelSettings','ChatSettings']:definitions+=struct('Common/entity/chatSettings.h',name)
 definitions+=enum('Common/entity/chatSettings.h','CSFlags_Type')
 definitions+=define('MapServer/src/entity/keybinds.h','BIND_MAX')+struct('MapServer/src/entity/keybinds.h','ServerKeyBind')
 definitions+=enum('Game/src/UI/uiKeybind.h','ModTypes')+struct('Game/src/UI/uiKeybind.h','KeyBind')
 definitions+=struct('Common/entity/RewardToken.h','RewardToken')+define('Common/entity/attrib_description.h','MAX_COMBAT_STATS')
 definitions+='''
typedef struct {int iKey,iOrder;} CombatMonitorStat;
typedef struct {size_t count;RewardToken*slots[16];RewardToken storage[16];char names[16][256];}TokenList;
static int eaSize(void*p){RewardToken**a=*(RewardToken***)p;return a?(int)((TokenList*)((char*)a - offsetof(TokenList,slots)))->count:0;}
#define AINRANGE(i,a) ((i)>=0&&(unsigned)(i)<sizeof(a)/sizeof((a)[0]))
#define EAINRANGE(i,a) ((i)>=0&&(i)<eaSize(&(a)))
static int rewardtoken_IdxFromName(RewardToken***a,const char*n){for(int i=0;i<eaSize(a);i++)if(!strcmp((*a)[i]->reward,n))return i;return -1;}
static int rewardtoken_Award(RewardToken***a,const char*n,int v){TokenList*l=(TokenList*)((char*)*a - offsetof(TokenList,slots));unsigned i=l->count++;assert(i<16);strncpyt(l->names[i],n,256);l->storage[i]=(RewardToken){l->names[i],v,0};l->slots[i]=&l->storage[i];return i;}
typedef struct EntStrings EntStrings;
typedef struct {U32 send,dbid,online,map_id;char*name,*arch,*origin,*mapname;}Friend;
typedef struct {const char*pchName;}CharacterClass,CharacterOrigin;
static CharacterClass fixture_class={"Class0"};static CharacterOrigin fixture_origin={"Origin0"};
static const CharacterClass*fixture_classes[]={&fixture_class};static const CharacterOrigin*fixture_origins[]={&fixture_origin};
static struct{const CharacterClass**ppClasses;}g_CharacterClasses={fixture_classes};
static struct{const CharacterOrigin**ppOrigins;}g_CharacterOrigins={fixture_origins};
static int classes_GetIndexFromName(void*c,const char*n){(void)c;assert(!strcmp(n,"Class0"));return 0;}
static int origins_GetIndexFromName(void*c,const char*n){(void)c;assert(!strcmp(n,"Origin0"));return 0;}
static char*allocAddString(const char*s){return (char*)s;}
static char fixture_strings[256][512];static unsigned fixture_string_count;
static void strncpyta(char**d,const char*s,size_t cap){assert(fixture_string_count<256&&cap<=512);*d=fixture_strings[fixture_string_count++];strncpyt(*d,s,cap);}
'''
 # q's original fixture only needed option scalars. Extend explicit entity shells.
 pattern=r'typedef struct \{([^{}]*)\} Player;typedef struct\{Player\*pl;\} Entity;'
 match=re.search(pattern,code);assert match
 fields=match.group(1)
 extra_scalars=['lfg','hidden','supergroup_mode','hide_supergroup_emblem','skillsUnlocked','teambuff_display','dock_mode','inspiration_mode','newFeaturesVersion','titleThe','titleBadge','helpChatAdded','chatSendChannel','topChatChannels','botChatChannels','divSuperName','divSuperMap','divSuperTitle','divEmailFrom','divEmailSubject','divFriendName','divLfgName','divLfgMap','first']
 for f in extra_scalars:
  if not re.search(r'\b'+f+r'\s*;',fields):fields+='U32 '+f+';'
 for f in ['titleTheText','titleCommon','titleOrigin','titleSpecial','comment','keyProfile']:
  fields+=re.search(r'char\s+'+f+r'\s*\[[^]]+\]\s*;',texts['Common/entity/entPlayer.h']).group(0)
 fields+='U32 titleColors[2];RewardToken**rewardTokens,**activePlayerRewardTokens;void*superCostume,*keybinds;ChatSettings chat_settings;CombatMonitorStat combatMonitorStats[MAX_COMBAT_STATS];'
 entity='typedef struct Player{'+fields+'}Player;typedef struct Entity{Player*pl;EntStrings*strings;void*costume;struct{struct{U32 nocoll;}controls;}*client;U32 db_flags,friendCount;Friend friends[16];}Entity;'
 code=code[:match.start()]+definitions+entity+code[match.end():]
 # Packet-array helpers execute whole original alignment code.
 code+=''.join(get(q.PATHS[7],n) for n in ['bsWriteBitsArray','bsReadBitsArray'])
 code+='''
#include <stddef.h>
#define SIZEOF2(T,f) sizeof(((T*)0)->f)
#define SAFESTR(x) (x),sizeof(x)
#define TRUE 1
#define FALSE 0
#define TEST_CLIENT 1
#define START_BIT_COUNT(p,n)
#define STOP_BIT_COUNT(p)
static void pktSendBitsArray(Packet*p,int n,const void*v){bsWriteBitsArray(&p->stream,n,v);}
static void pktGetBitsArray(Packet*p,int n,void*v){bsReadBitsArray(&p->stream,n,v);}
static void pktSendIfSetBits(Packet*p,int n,U32 v){pktSendBits(p,1,v!=0);if(v)pktSendBits(p,n,v);}
static void pktSendIfSetBitsPack(Packet*p,int n,U32 v){pktSendBits(p,1,v!=0);if(v)pktSendBitsPack(p,n,v);}
static U32 pktGetIfSetBits(Packet*p,int n){return pktGetBits(p,1)?pktGetBits(p,n):0;}
static U32 pktGetIfSetBitsPack(Packet*p,int n){return pktGetBits(p,1)?pktGetBitsPack(p,n):0;}
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
'''
 code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',code)
 for n in ['pktSendBitsAuto','pktGetBitsAuto']:code+=get('libs/UtilitiesLib/src/network/net_packetutil.c',n)
 code+='''
static unsigned fixture_development,fixture_rename,fixture_team_mode,fixture_inspiration;
static Entity*fixture_player;
static Entity*playerPtr(void){return fixture_player;}
static int isDevelopmentMode(void){return fixture_development;}
static void createDefaultChatSettings(Entity*e,int top,int bot){(void)top;(void)bot;e->pl->chat_settings.options=CSFlags_DoNotLocalize|CSFlags_AddedCombat|CSFlags_AddedArchitect|CSFlags_AddedLeague|CSFlags_AddedLookingForGroup|CSFlags_AddedLegacyUINote|CSFlags_MovedVisitedMaps|CSFlags_ClearMARTYHistory;}
static void addCombatChannels(Entity*e){e->pl->chat_settings.options|=CSFlags_AddedCombat;}
static int BitFieldGet(const U32*a,int words,int id){assert(id>=0&&id<words*32);return (a[id/32]>>(id%32))&1;}
static void BitFieldSet(U32*a,int words,int id,int v){assert(id>=0&&id<words*32);if(v)a[id/32]|=1u<<(id%32);else a[id/32]&=~(1u<<(id%32));}
static void automapserver_sendAllStaticMaps(Entity*e){(void)e;}
static void clearMARTYHistory(Entity*e){(void)e;}
static void addHelpChatTab(Entity*e){(void)e;}
'''
 code+=get('Common/entity/chatSettings.c','sendChatSettings')
 code+='\n#undef SERVER\n#define CLIENT 1\n'+get('Common/entity/chatSettings.c','receiveChatSettings')
 # Execute full client wrapper; translation/UI callbacks are non-wire shells.
 code+='''
#define DIALOG_TWO_RESPONSE 0
static void*menuMessages,*playerSeenLegacyUINoteKeep,*playerSeenLegacyUINoteLegacy;
static void msPrintf(void*m,char*d,size_t n,const char*s){(void)m;strncpyt(d,s,n);}
static void dialogStd(int a,const char*b,const char*c,const char*d,void*e,void*f,int g){(void)a;(void)b;(void)c;(void)d;(void)e;(void)f;(void)g;}
static int stricmp(const char*a,const char*b){return strcmp(a,b);}
static void loadEntityChatSettings(Entity*e,int n){(void)e;(void)n;}
static void sendChatSettingsToServer(void){}
static void setTeamBuffMode(U32 n){fixture_team_mode=n;}
static void inspiration_setMode(U32 n){fixture_inspiration=n;}
static void*costume_as_const(void*p){return p;}
static void costume_Apply(Entity*e){(void)e;}
static int game_binds_profile;
static void keybinds_init(const char*p,void*g,void*b){(void)p;(void)g;(void)b;}
static void optionSet(int id,U32 n,int save){(void)save;userOptionGet(id)->iVal=(int)n;}
static void optionSetf(int id,float n,int save){(void)save;userOptionGet(id)->fVal=n;}
static int gDivSuperName,gDivSuperMap,gDivSuperTitle,gDivEmailFrom,gDivEmailSubject,gDivFriendName,gDivLfgName,gDivLfgMap;
static void setSavedDividerSettings(void){}
static struct{U32 first,nocoll;}control_state;
static void friendListPrepareUpdate(void){}
static void dialogChooseNameImmediate(int n){fixture_rename=n;}
#define DBFLAG_RENAMEABLE (1u<<12)
'''
 code+=get('Game/src/UI/uiChat.c','receiveChatSettingsFromServer')
 code+=get('MapServer/src/entity/keybinds.c','keybinds_send')
 for n in ['keybinds_recieve','receiveTeamBuffMode','receiveDockMode','receiveInspirationMode','receiveTitles','receiveDescription','receiveDividers','receiveFriendsList']:code+=get('Game/src/UI/uiNet.c',n)
 code+=get('MapServer/src/entity/friends.c','sendFriendsList')
 for n in ['sendCombatMonitorStats','receiveCombatMonitorStats']:code+=get('Common/entity/attrib_description.c',n)
 sender=q.extract(texts['MapServer/src/entity/entserver.c'],'sendCharacterToClient');sender=sender[sender.index('    pktSendBitsAuto( pak, eaSize(&e->pl->rewardTokens) );'):sender.index('    // these all send their own packets')]
 receiver=q.extract(texts['Game/src/entity/entrecv.c'],'receiveCharacterFromServer');receiver=receiver[receiver.index('    count = pktGetBitsAuto( pak );'):receiver.index('    pets_Clear();')]
 code+='static void original_group56_send(Packet*pak,Entity*e){int i;\n'+sender+'}\n'
 code+='static void original_group56_receive(Packet*pak,Entity*e){int i,count;\n'+receiver+'}\n'
 code+='''
static U32 fixture_words[8192],fixture_words_used,fixture_text_used;static U8 fixture_text[131072];
static void word(U32 n){assert(fixture_words_used<8192);fixture_words[fixture_words_used++]=n;}
static void text(const char*s){size_t n=strlen(s);assert(n+1<=sizeof(fixture_text)-fixture_text_used);word(fixture_text_used);word(n);memcpy(fixture_text+fixture_text_used,s,n+1);fixture_text_used+=(U32)n+1;}
static void floatword(float f){U32 w;memcpy(&w,&f,4);word(w);}
void group56_observe(U32*w,U8*t,U32*wn,U32*tn){*wn=fixture_words_used;*tn=fixture_text_used;memcpy(w,fixture_words,4*fixture_words_used);memcpy(t,fixture_text,fixture_text_used);}
static U32 hash_bytes(U32 h,const void*p,size_t n){const U8*b=p;for(size_t i=0;i<n;i++){h^=b[i];h*=16777619u;}return h;}
static U32 hash_text(const char*s){return hash_bytes(2166136261u,s,strlen(s));}
static U32 hash_tokens(RewardToken**p){U32 h=2166136261u;for(int i=0;i<eaSize(&p);i++){h=hash_bytes(h,p[i]->reward,strlen(p[i]->reward));h=hash_bytes(h,&p[i]->val,4);h=hash_bytes(h,&p[i]->timer,4);}return h;}
void group56_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 static U32 memory[262144];static Player pl,dl;static Entity e,d;static EntStrings strings,decoded;static TokenList reward,active,read_reward,read_active;static ServerKeyBind server_keys[BIND_MAX];static KeyBind read_keys[BIND_MAX];static char key_commands[BIND_MAX][BIND_MAX];
 memset(memory,0,sizeof(memory));memset(&pl,0,sizeof(pl));memset(&dl,0,sizeof(dl));memset(&e,0,sizeof(e));memset(&d,0,sizeof(d));memset(&strings,0,sizeof(strings));memset(&decoded,0,sizeof(decoded));memset(&reward,0,sizeof(reward));memset(&active,0,sizeof(active));memset(&read_reward,0,sizeof(read_reward));memset(&read_active,0,sizeof(read_active));memset(server_keys,0,sizeof(server_keys));memset(read_keys,0,sizeof(read_keys));memset(key_commands,0,sizeof(key_commands));fixture_string_count=fixture_rename=fixture_team_mode=fixture_inspiration=0;fixture_development=scenario%3==0;fixture_player=&d;
 e.pl=&pl;e.strings=&strings;d.pl=&dl;d.strings=&decoded;pl.rewardTokens=reward.slots;pl.activePlayerRewardTokens=active.slots;dl.rewardTokens=read_reward.slots;dl.activePlayerRewardTokens=read_active.slots;pl.keybinds=server_keys;dl.keybinds=read_keys;
 for(int i=0;i<BIND_MAX;i++){read_keys[i].command[0]=key_commands[i];sprintf(server_keys[i].command,"cmd_%u_%d",scenario,i);server_keys[i].key=(int)(0x100u*(i%16)+(i%256));server_keys[i].modifier=i%4;}
 for(int i=0;i<3;i++){char name[32];sprintf(name,"Reward_%d",i);rewardtoken_Award(&pl.rewardTokens,name,100+i);reward.slots[i]->timer=0x80000000u+i;sprintf(name,"Active_%d",i);rewardtoken_Award(&pl.activePlayerRewardTokens,name,200+i);active.slots[i]->timer=0xffffffffu-i;}
 if(scenario==0)reward.count=active.count=0;
'''
 for index,f in enumerate(schema['option_fields']):
  value='(float)((scenario+'+str(index)+')%17)/4.f' if f in schema['float_fields'] else '((scenario*37u+'+str(index)+'u)^0xa5a5a5a5u)'
  code+='pl.'+f+'='+value+';\n'
 code+='''
 pl.options_saved=scenario%2;pl.contactSortByName=scenario%5==0;pl.contactSortByZone=scenario%5==1;pl.contactSortByRelationship=scenario%5==2;pl.contactSortByActive=scenario%5==3;
 pl.lfg=0x155;pl.hidden=0x2aa;pl.supergroup_mode=scenario%2;pl.hide_supergroup_emblem=(scenario>>1)%2;pl.skillsUnlocked=1;pl.teambuff_display=(scenario>>2)%2;pl.dock_mode=0xdeadbeef;pl.inspiration_mode=0x12345678;pl.newFeaturesVersion=scenario;
 pl.titleThe=scenario*9;strcpy(pl.titleTheText,"The");strcpy(pl.titleCommon,"Unchanged");strcpy(pl.titleOrigin,"Synthetic");strcpy(pl.titleSpecial,"Oracle");pl.titleColors[0]=0x12345678;pl.titleColors[1]=0x87654321;pl.titleBadge=0xffffffff;
 strcpy(strings.playerDescription,"<raw description>");strcpy(strings.motto,"<raw motto>");strcpy(pl.comment,"<comment>");if(scenario%3)strcpy(pl.keyProfile,"default");
 pl.divSuperName=scenario?101:0;pl.divSuperMap=102;pl.divSuperTitle=103;pl.divEmailFrom=104;pl.divEmailSubject=105;pl.divFriendName=106;pl.divLfgName=107;pl.divLfgMap=108;pl.first=scenario%2;
 pl.chat_settings.options=CSFlags_DoNotLocalize|CSFlags_AddedCombat|CSFlags_AddedArchitect|CSFlags_AddedLeague|CSFlags_AddedLookingForGroup|CSFlags_AddedLegacyUINote|CSFlags_MovedVisitedMaps|CSFlags_ClearMARTYHistory;
 pl.helpChatAdded=scenario%2;pl.chatSendChannel=7;pl.chat_settings.userSendChannel=3;pl.chat_settings.primaryChatMinimized=1;
 for(int i=0;i<MAX_CHAT_WINDOWS;i++){pl.chat_settings.windows[i]=(ChatWindowSettings){1<<i,i,i+1,(float)i/4.f};}
 for(int i=0;i<MAX_CHAT_TABS;i++){sprintf(pl.chat_settings.tabs[i].name,"Tab_%d",i);pl.chat_settings.tabs[i].systemChannels[0]=0xa5a5a5a5u^i;pl.chat_settings.tabs[i].systemChannels[1]=0x5a5a5a5au^i;pl.chat_settings.tabs[i].userBF=1<<i;pl.chat_settings.tabs[i].optionsBF=i;pl.chat_settings.tabs[i].defaultChannel=i+1;pl.chat_settings.tabs[i].defaultType=i%3;}
 for(int i=0;i<MAX_CHAT_CHANNELS;i++){sprintf(pl.chat_settings.channels[i].name,"Channel_%d",i);pl.chat_settings.channels[i].optionsBF=i;pl.chat_settings.channels[i].color1=0xff000000|i;pl.chat_settings.channels[i].color2=0x80000000|i;}
 static struct{struct{U32 nocoll;}controls;}client;client.controls.nocoll=scenario%4;e.client=(void*)&client;
 e.friendCount=scenario%4;for(U32 i=0;i<e.friendCount;i++){e.friends[i]=(Friend){1,1000+i,i%2,5+i,"Friend",i%2?"Class0":NULL,i%2?"Origin0":NULL,"maps/Oracle"};}
 for(int i=0;i<MAX_COMBAT_STATS;i++){pl.combatMonitorStats[i].iKey=i%2?1000+i:0;pl.combatMonitorStats[i].iOrder=i;}
 if(scenario%2)e.db_flags|=DBFLAG_RENAMEABLE;
 Packet p={0};p.id=1+scenario;initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);original_group56_send(&p,&e);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;original_group56_receive(&p,&d);*end=bsGetCursorBitPosition(&p.stream);
 observed[0]=eaSize(&dl.rewardTokens);observed[1]=hash_tokens(dl.rewardTokens);observed[2]=eaSize(&dl.activePlayerRewardTokens);observed[3]=hash_tokens(dl.activePlayerRewardTokens);observed[4]=dl.lfg;observed[5]=dl.hidden;observed[6]=dl.supergroup_mode;observed[7]=dl.hide_supergroup_emblem;observed[8]=dl.skillsUnlocked;observed[9]=fixture_team_mode;observed[10]=fixture_inspiration;observed[11]=dl.newFeaturesVersion;
 observed[12]=dl.titleThe;observed[13]=hash_text(dl.titleTheText);observed[14]=hash_text(dl.titleCommon);observed[15]=hash_text(dl.titleOrigin);observed[16]=dl.titleColors[0];observed[17]=dl.titleColors[1];observed[18]=dl.titleBadge;observed[19]=hash_text(dl.titleSpecial);observed[20]=hash_text(decoded.playerDescription);observed[21]=hash_text(decoded.motto);observed[22]=hash_text(dl.comment);observed[23]=hash_text(dl.keyProfile);
 U32 h=2166136261u;for(int i=0;i<BIND_MAX;i++){h=hash_bytes(h,read_keys[i].command[0],strlen(read_keys[i].command[0]));h=hash_bytes(h,&read_keys[i].key,4);h=hash_bytes(h,&read_keys[i].modifier,4);h=hash_bytes(h,&read_keys[i].secondary,4);}observed[24]=h;
 observed[25]=d.friendCount;h=2166136261u;for(U32 i=0;i<d.friendCount;i++){Friend*f=&d.friends[i];h=hash_bytes(h,&f->dbid,4);h=hash_bytes(h,&f->online,4);h=hash_bytes(h,f->name,strlen(f->name));if(f->online){h=hash_bytes(h,&f->map_id,4);h=hash_bytes(h,f->mapname,strlen(f->mapname));}}observed[26]=h;
 observed[27]=hash_bytes(2166136261u,dl.combatMonitorStats,sizeof(dl.combatMonitorStats));observed[28]=fixture_rename;observed[29]=control_state.first;observed[30]=control_state.nocoll;
 fixture_words_used=fixture_text_used=0;
 RewardToken**lists[]={dl.rewardTokens,dl.activePlayerRewardTokens};for(int k=0;k<2;k++){word(eaSize(&lists[k]));for(int i=0;i<eaSize(&lists[k]);i++){text(lists[k][i]->reward);word(lists[k][i]->val);word(lists[k][i]->timer);}}
 U32 g5[]={dl.lfg,dl.hidden,dl.supergroup_mode,dl.hide_supergroup_emblem,dl.skillsUnlocked,fixture_team_mode,pl.dock_mode,fixture_inspiration,dl.newFeaturesVersion};for(unsigned i=0;i<ARRAY_SIZE(g5);i++)word(g5[i]);
 ChatSettings*c=&dl.chat_settings;word(dl.helpChatAdded);word(dl.chatSendChannel);word(c->userSendChannel);word(c->options);word(c->primaryChatMinimized);
 for(int i=0;i<MAX_CHAT_WINDOWS;i++){word(c->windows[i].selectedtop);word(c->windows[i].selectedbot);word(c->windows[i].tabListBF);floatword(c->windows[i].divider);}
 for(int i=0;i<MAX_CHAT_TABS;i++){ChatTabSettings*t=&c->tabs[i];text(t->name);for(int j=0;j<SYSTEM_CHANNEL_BITFIELD_SIZE;j++)word(t->systemChannels[j]);word(t->userBF);word(t->optionsBF);word(t->defaultChannel);word(t->defaultType);}
 for(int i=0;i<MAX_CHAT_CHANNELS;i++){ChatChannelSettings*t=&c->channels[i];text(t->name);word(t->optionsBF);word(t->color1);word(t->color2);}
 word(dl.titleThe);text(dl.titleTheText);text(dl.titleCommon);text(dl.titleOrigin);word(dl.titleColors[0]);word(dl.titleColors[1]);word(dl.titleBadge);text(dl.titleSpecial);text(decoded.playerDescription);text(decoded.motto);text(dl.comment);
 text(pl.keyProfile);text(dl.keyProfile);for(int i=0;i<BIND_MAX;i++){text(read_keys[i].command[0]);word(server_keys[i].key);word(read_keys[i].modifier);word(read_keys[i].key);word(read_keys[i].secondary);}
 word(pl.options_saved);if(pl.options_saved){for(int i=1;i<kUO_OptionTotal;i++){UserOption*o=userOptionGet(i);if(o->bitSize<0)floatword(o->fVal);else word(o->iVal);}}else{word(userOptionGet(kUO_MouseInvert)->iVal);floatword(userOptionGet(kUO_MouseSpeed)->fVal);floatword(userOptionGet(kUO_SpeedTurn)->fVal);}
 U32 dividers[]={pl.divSuperName,pl.divSuperMap,pl.divSuperTitle,pl.divEmailFrom,pl.divEmailSubject,pl.divFriendName,pl.divLfgName,pl.divLfgMap};for(int i=0;i<8;i++)word(dividers[i]);word(control_state.first);word(control_state.nocoll);
 word(d.friendCount);for(U32 i=0;i<d.friendCount;i++){Friend*f=&d.friends[i];word(f->dbid);word(f->online);text(f->name);word(e.friends[i].arch?0:UINT32_MAX);word(e.friends[i].origin?0:UINT32_MAX);if(f->online){word(f->map_id);text(f->mapname);}}
 for(int i=0;i<MAX_COMBAT_STATS;i++){word(dl.combatMonitorStats[i].iKey);word(dl.combatMonitorStats[i].iOrder);}word(fixture_rename);

}
'''
 return code,functions,{'sender_group56_sha256_lf':q.sha(sender.encode()),'receiver_group56_sha256_lf':q.sha(receiver.encode())}


def projection(words,text):
 at=0
 def w():
  nonlocal at
  value=words[at];at+=1;return value
 def t():
  offset,n=w(),w();assert offset+n<len(text) and text[offset+n]==0;return text[offset:offset+n].decode()
 def rows(n,fields):return [{name:(t() if kind=='text' else w()) for name,kind in fields} for _ in range(n)]
 out={}
 for key in ['reward_tokens','active_tokens']:out[key]=rows(w(),[('name','text'),('value','word'),('timer','word')])
 for key in ['lfg','hidden','supergroup_mode','hide_supergroup_emblem','skills_unlocked','team_buff','dock_mode','inspiration_mode','new_features']:out[key]=w()
 chat={};out['chat']=chat
 for key in ['help_added','send_channel','user_send_channel','options','primary_minimized']:chat[key]=w()
 chat['windows']=rows(5,[(x,'word') for x in ['selected_top','selected_bottom','tabs','divider_word']])
 chat['tabs']=rows(20,[('name','text')]+[(x,'word') for x in ['system0','system1','users','options','default_channel','default_type']])
 chat['channels']=rows(15,[('name','text'),('options','word'),('color1','word'),('color2','word')])
 out['title_the']=w()
 for key in ['title_the_text','title_common','title_origin']:out[key]=t()
 for key in ['title_color0','title_color1','title_badge']:out[key]=w()
 for key in ['title_special','description','motto','comment','wire_key_profile','applied_key_profile']:out[key]=t()
 out['keybinds']=rows(256,[('command','text')]+[(x,'word') for x in ['wire_key','modifier','applied_key','applied_secondary']])
 out['options_saved']=w();out['option_words']=[w() for _ in range(114 if out['options_saved'] else 3)]
 out['dividers']=[w() for _ in range(8)];out['first']=w();out['nocoll']=w()
 out['friends']=[]
 for _ in range(w()):
  f={'dbid':w(),'online':w(),'name':t(),'class':w(),'origin':w()}
  if f['online']:f.update(map_id=w(),map_name=t())
  out['friends'].append(f)
 out['combat_monitors']=rows(10,[('key','word'),('order','word')]);out['rename']=w();assert at==len(words)
 return out

def qualify(texts):
 code,functions,blocks=generate(texts)
 with tempfile.TemporaryDirectory(prefix='coh-character-group56-') as tmp:
  w=Path(tmp);(w/'source.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-Wl,-z,defs','-I'+str(q.ROOT/'native-android/include'),w/'source.c','-o',w/'original.so'])
  lib=C.CDLL(str(w/'original.so'));fn=lib.group56_fixture;fn.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p];cases=[]
  lib.group56_observe.argtypes=[C.c_void_p,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(10):
     data=(C.c_uint8*1048576)();bits=C.c_uint32();end=C.c_uint32();observed=(C.c_uint32*64)();fn(scenario,aligned,prefix,data,C.byref(bits),C.byref(end),observed)
     if bits.value!=end.value:raise ValueError(f'group56 cursor mismatch {scenario}/{aligned}/{prefix}: {bits.value}!={end.value}')
     words=(C.c_uint32*8192)();text=(C.c_uint8*131072)();wn=C.c_uint32();tn=C.c_uint32();lib.group56_observe(words,text,C.byref(wn),C.byref(tn));project=projection(list(words[:wn.value]),bytes(text[:tn.value]))
     cases.append({'expected':project,'kind':'group56','scenario':scenario,'aligned':aligned,'begin_bit':prefix,'end_bit':bits.value,'wire_hex':bytes(data[:(bits.value+7)//8]).hex(),'observed':list(observed[:31])})
  widths=json.loads((HERE/'host-proof.json').read_text())['constants']['option_widths_in_enum_order']
  model=independent.qualify(cases,widths)
  return {'independent_model':model,'original_functions':functions,'blocks':blocks,'original_generated_source_sha256':q.sha(code.encode()),'cases':cases,'producer_consumer_cases':len(cases),'whole_character_complete':False,'dictionary_ui_storage_shells':True,'original_oracle_sanitized':False,'chat_profile':'already migrated/localized; migration/default/UI callbacks are non-wire synthetic shells'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args();texts={p:q.source(p) for p in q.PATHS+EXTRA};pins={p:q.sha(t.encode()) for p,t in texts.items()}
 if a.initialize_pins:(HERE/'group56-source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
 result=qualify(texts);a.output.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['cases','original_functions']})
