"""Exact group4 original inline body + full tray iterator/reader functions.
Synthetic dictionary/UI/storage shells are deliberately not gameplay authority.
"""
import ctypes as C, hashlib, json, re, tempfile
from pathlib import Path
import qualify_outer as q
import independent
HERE=q.HERE

def generate(texts):
 if {p:q.sha(texts[p].encode()) for p in q.PATHS}!=json.loads((HERE/'source-pins.json').read_text()):raise ValueError('group4 original source pin changed')
 allcode,_,_=q.generate(texts)
 code=allcode[:allcode.index('typedef enum Show')]
 code=code.replace('compress,ordered,ordered_id;','compress,ordered,ordered_id,reliable;')
 functions={}
 def get(path,n):
  body=q.extract(texts[path],n);functions[n]={'source':path,'sha256_lf':q.sha(body.encode())};return body
 tray=texts[q.PATHS[16]];impl=texts[q.PATHS[15]]
 for name in ['CurTrayType','TrayItemType','TrayCategory']:
  code+=re.search(r'typedef enum(?: '+name+r')?\s*\{[^{}]*\}\s*'+name+r';',tray,re.S).group(0)+'\n'
 for name in ['TRAY_WD','TRAY_HT','TRAY_SLOTS','NUM_CURTRAYTYPE_BITS','IS_TRAY_MACRO']:
  code+=re.search(r'^#define\s+'+name+r'(?:\([^\n]*|\s+[^\n]*)',tray,re.M).group(0)+'\n'
 code+=re.search(r'^#define\s+MAX_BUILD_NUM\s+[^\n]+',texts[q.PATHS[17]],re.M).group(0)+'\n'
 for name in ['TOTAL_PLAYER_TRAYS','TOTAL_SERVER_TRAYS','TRAY_SLOTS_PER_BUILD','MAX_SLOT_COUNT','MAX_SERVER_SLOT_COUNT']:
  code+=re.search(r'^#define\s+'+name+r'\s+[^\n]+',impl,re.M).group(0)+'\n'
 for name in ['WindowName','WindowDisplayMode','WindowStartState']:
  code+=re.search(r'typedef enum '+name+r'\s*\{.*?\}\s*'+name+r';',texts[q.PATHS[3]],re.S).group(0)+'\n'
 code+=re.search(r'typedef struct WdwBase\s*\{.*?\}\s*WdwBase;',texts[q.PATHS[3]],re.S).group(0)+'\n'
 code+=re.search(r'typedef struct EntStrings\s*\{.*?\}\s*EntStrings;',texts[q.PATHS[19]],re.S).group(0)+'\n'
 for name in ['MAX_POP_HELP','BITS_PER_POP_HELP','POP_HELP_STATUS_SIZE','POP_HELP_LATEST_SIZE']:
  code+=re.search(r'^#define\s+'+name+r'\s+[^\n]+',texts[q.PATHS[10]],re.M).group(0)+'\n'
 code+='''
typedef int bool;typedef float F32;
typedef struct TrayObj {TrayItemType type;TrayCategory icat;int itray,islot,iset,ipow;char command[256],shortName[32],iconName[256];}TrayObj;
typedef struct {TrayObj**slot,**serverSlot;}TrayInternals;
typedef struct Tray{int current_trays[kCurTrayType_Count];int trayIndexes,mode,mode_alt2;TrayInternals*internals;}Tray;
typedef struct Power Power;typedef struct PowerSet{int idx;Power**ppPowers;}PowerSet;
struct Power{int idx;PowerSet*psetParent;};
typedef struct {Power*ppowDefault;PowerSet**ppPowerSets;int iNumInspirationCols,iNumInspirationRows;void*aInspirations[2][2];}Character;
typedef struct EntPlayer {Tray*tray;U32 popHelpStatus[POP_HELP_STATUS_SIZE],popHelpLatest[POP_HELP_LATEST_SIZE];WdwBase*winLocs;}EntPlayer;
typedef struct Entity{EntPlayer*pl;Character*pchar;char name[64];EntStrings*strings;}Entity;
static int fixture_easize(void*p){(void)p;return MAX_SLOT_COUNT;}
#define eaSize(p) fixture_easize((void*)(p))
#define eaSetSize(p,n) assert((n)<=MAX_SLOT_COUNT)
static TrayObj fixture_created[MAX_SLOT_COUNT];
static TrayObj*createTrayObj(TrayObj***array,int i){assert(i>=0&&i<MAX_SLOT_COUNT);memset(&fixture_created[i],0,sizeof(TrayObj));(*array)[i]=&fixture_created[i];return (*array)[i];}
static void destroyTrayObj(TrayObj**array,int i){assert(i>=0&&i<MAX_SLOT_COUNT);array[i]=NULL;}
static int character_GetActiveBuild(Entity*e){(void)e;return 0;}
static void character_SelectBuildLightweight(Entity*e,int b){(void)e;(void)b;}
static void buildPowerTrayObj(TrayObj*o,int s,int p,int a){(void)a;o->type=kTrayItemType_Power;o->iset=s;o->ipow=p;}
static void tray_getPowerStrings(Entity*e,TrayObj*o,int s,int p){(void)e;(void)o;(void)s;(void)p;}
static void buildInspirationTrayObj(TrayObj*o,int c,int r){o->type=kTrayItemType_Inspiration;o->iset=c;o->ipow=r;}
'''
 globals=impl[impl.index('static Tray *s_currentIteratedTray'):impl.index('void resetTrayIterator')]
 code+=globals
 # Full unchanged original iterator control flow; only earray/storage adapters are synthetic.
 order=['resetTrayIterator','isTrayIteratorValid','incrementTrayIterator','getCurrentTrayObjFromIterator','getNextTrayObjFromIterator','getCurrentTrayIteratorIndices','createCurrentTrayObjViaIterator','destroyCurrentTrayObjViaIterator','sendTrayObj','sendTray','receiveTrayObj','receiveTrayObjs','receiveTray']
 code+=''.join(get(q.PATHS[15],n) for n in order)
 code+=''.join(get(q.PATHS[2],n) for n in ['sendWindow','receiveWindowIdx','receiveWindow'])
 code+=''.join(get(q.PATHS[8],n) for n in ['breakHTMLtags','sendEntStrings','receiveEntStrings'])
 code+=get(q.PATHS[1],'receiveFullPopHelp')
 code+='''
#define TEST_CLIENT 1
#define START_BIT_COUNT(p,n)
#define STOP_BIT_COUNT(p)
static unsigned mode_received;
static void tray_setMode(int n){mode_received=n;}
static void tray_init(void){}
static EntStrings*createEntStrings(void){assert(0);return NULL;}
static void initEntStrings(EntStrings*s){memset(s,0,sizeof(*s));}
static void windows_initDefaults(int n){(void)n;}
static void windowClientSizeThisFrame(int*w,int*h){*w=1920;*h=1080;}
'''+get(q.PATHS[6],'receiveTrayMode')
 sender=q.extract(texts[q.PATHS[0]],'sendCharacterToClient');sender=sender[sender.index('    sendTray( pak, e );'):sender.index('    pktSendBitsAuto( pak, eaSize(&e->pl->rewardTokens) );')]
 receiver=q.extract(texts[q.PATHS[1]],'receiveCharacterFromServer');receiver=receiver[receiver.index('    START_BIT_COUNT(pak, "receiveTray")'):receiver.index('    count = pktGetBitsAuto( pak );')]
 code+='static void original_group4_send(Packet*pak,Entity*e){int i,k;\n'+sender+'}\n'
 code+='static void original_group4_receive(Packet*pak,Entity*e){int i;\n'+receiver+'}\n'
 code+='''
static U32 fnv_bytes(U32 h,const void*p,size_t n){const U8*b=p;for(size_t i=0;i<n;i++){h^=b[i];h*=16777619u;}return h;}
void group4_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 static U32 memory[262144];static TrayObj source_objs[MAX_SLOT_COUNT];static TrayObj*source_slots[MAX_SLOT_COUNT],*read_slots[MAX_SLOT_COUNT];
 static WdwBase windows[MAX_WINDOW_COUNT],read_windows[MAX_WINDOW_COUNT];
 static EntPlayer pl,dl;static Tray source_tray,read_tray;static Character ch,dc;static Entity e,d;static EntStrings strings,decoded_strings;
 memset(memory,0,sizeof(memory));memset(source_objs,0,sizeof(source_objs));memset(source_slots,0,sizeof(source_slots));memset(read_slots,0,sizeof(read_slots));memset(&pl,0,sizeof(pl));memset(&dl,0,sizeof(dl));memset(&strings,0,sizeof(strings));memset(&decoded_strings,0,sizeof(decoded_strings));memset(&ch,0,sizeof(ch));memset(&dc,0,sizeof(dc));
 TrayInternals si={source_slots,NULL},di={read_slots,NULL};source_tray=(Tray){0};read_tray=(Tray){0};source_tray.internals=&si;read_tray.internals=&di;pl.tray=&source_tray;dl.tray=&read_tray;pl.winLocs=windows;dl.winLocs=read_windows;
 e=(Entity){&pl,&ch,"Oracle character",&strings};d=(Entity){&dl,&dc,"",&decoded_strings};
 static Power power;static PowerSet set;static Power*powers[MAX_SLOT_COUNT];static PowerSet*sets[MAX_SLOT_COUNT];for(int i=0;i<MAX_SLOT_COUNT;i++){powers[i]=&power;sets[i]=&set;}set.idx=0;set.ppPowers=powers;power.idx=0;power.psetParent=&set;ch.ppPowerSets=dc.ppPowerSets=sets;ch.iNumInspirationCols=dc.iNumInspirationCols=2;ch.iNumInspirationRows=dc.iNumInspirationRows=2;ch.aInspirations[0][0]=dc.aInspirations[0][0]=&power;
 if(scenario%2)ch.ppowDefault=&power;
 for(int i=0;i<kCurTrayType_Count;i++)source_tray.current_trays[i]=(scenario+i)%TOTAL_PLAYER_TRAYS;
 source_tray.trayIndexes=(int)(0x12345678u+scenario);source_tray.mode=scenario&1;source_tray.mode_alt2=(scenario>>1)&1;
 for(int i=0;i<MAX_SLOT_COUNT;i++){TrayObj*o=&source_objs[i];unsigned kind=(scenario+i)%6;if(!kind)continue;source_slots[i]=o;o->type=kind==1?kTrayItemType_Power:kind==2?kTrayItemType_Inspiration:kind==3?kTrayItemType_Macro:kind==4?kTrayItemType_MacroHideName:kTrayItemType_BodyItem;o->iset=o->ipow=0;if(IS_TRAY_MACRO(o->type)){strcpy(o->command,"say <hello> -- oracle");strcpy(o->shortName,"macro");strcpy(o->iconName,"icon_oracle");}}
 strcpy(strings.motto,"<motto>");strcpy(strings.playerDescription,"A <description>");
 for(int i=0;i<POP_HELP_STATUS_SIZE;i++)pl.popHelpStatus[i]=0xa5a5a5a5u^(scenario+i);
 for(int i=0;i<POP_HELP_LATEST_SIZE;i++)pl.popHelpLatest[i]=scenario*1024+i;
 for(int i=0;i<MAX_WINDOW_COUNT;i++){windows[i]=(WdwBase){0};windows[i].xp=i*100;windows[i].yp=i*50;windows[i].mode=i%5;windows[i].start_shrunk=i%3;windows[i].draggable_frame=i%2;windows[i].wd=200+i;windows[i].ht=300+i;windows[i].sc=i%3?1.5f:0;windows[i].color=(int)(0xff000000u+i);}
 Packet p={0};initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);original_group4_send(&p,&e);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;original_group4_receive(&p,&d);*end=bsGetCursorBitPosition(&p.stream);
 observed[0]=mode_received;observed[1]=read_tray.trayIndexes;observed[2]=dc.ppowDefault!=NULL;
 U32 h=2166136261u;for(int i=0;i<MAX_SLOT_COUNT;i++){TrayObj*o=read_slots[i];U32 type=o?o->type:0;h=fnv_bytes(h,&type,4);if(o&&(type==kTrayItemType_Power||type==kTrayItemType_Inspiration)){h=fnv_bytes(h,&o->iset,4);h=fnv_bytes(h,&o->ipow,4);}if(o&&IS_TRAY_MACRO(type)){h=fnv_bytes(h,o->command,strlen(o->command));h=fnv_bytes(h,o->shortName,strlen(o->shortName));h=fnv_bytes(h,o->iconName,strlen(o->iconName));}}observed[3]=h;
 observed[4]=fnv_bytes(2166136261u,d.name,strlen(d.name));observed[5]=fnv_bytes(2166136261u,d.strings->motto,strlen(d.strings->motto));observed[6]=fnv_bytes(2166136261u,d.strings->playerDescription,strlen(d.strings->playerDescription));observed[7]=fnv_bytes(2166136261u,dl.popHelpStatus,sizeof(dl.popHelpStatus));observed[8]=fnv_bytes(2166136261u,dl.popHelpLatest,sizeof(dl.popHelpLatest));
}
void group4_counts(U32*out){out[0]=MAX_BUILD_NUM;out[1]=TOTAL_PLAYER_TRAYS;out[2]=TRAY_SLOTS;out[3]=kCurTrayType_Count;out[4]=MAX_SLOT_COUNT;out[5]=POP_HELP_STATUS_SIZE;out[6]=POP_HELP_LATEST_SIZE;out[7]=MAX_WINDOW_COUNT;out[8]=kTrayItemType_Macro;out[9]=kTrayItemType_MacroHideName;}
'''
 return code,functions,{'sender_group4_sha256_lf':q.sha(sender.encode()),'receiver_group4_sha256_lf':q.sha(receiver.encode())}

def qualify(texts):
 code,functions,blocks=generate(texts)
 with tempfile.TemporaryDirectory(prefix='coh-character-group4-') as tmp:
  w=Path(tmp);(w/'source.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),w/'source.c','-o',w/'original.so'])
  lib=C.CDLL(str(w/'original.so'));counts=(C.c_uint32*32)();lib.group4_counts(counts);fn=lib.group4_fixture;fn.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p];cases=[]
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(6):
     data=(C.c_uint8*1048576)();bits=C.c_uint32();end=C.c_uint32();observed=(C.c_uint32*16)();fn(scenario,aligned,prefix,data,C.byref(bits),C.byref(end),observed)
     if bits.value!=end.value:raise ValueError('group4 producer/consumer cursor mismatch')
     cases.append({'kind':'group4','scenario':scenario,'aligned':aligned,'begin_bit':prefix,'end_bit':bits.value,'wire_hex':bytes(data[:(bits.value+7)//8]).hex(),'observed':list(observed[:9])})
  model=independent.qualify(cases,{})
  return {'independent_model':model,'original_functions':functions,'blocks':blocks,'original_generated_source_sha256':q.sha(code.encode()),'counts':list(counts[:10]),'cases':cases,'producer_consumer_cases':len(cases),'whole_character_complete':False,'dictionary_shells':True,'original_oracle_sanitized':False,'ui_window_state_applied':False}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 texts={p:q.source(p) for p in q.PATHS};result=qualify(texts);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['cases','original_functions']})
