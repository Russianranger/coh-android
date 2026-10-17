"""Exact original outer-character helper and options oracles; no actor admission."""
from pathlib import Path
import independent
import argparse, ctypes as C, hashlib, importlib.util, json, re, subprocess, tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PIN='767d55e48fa35261f1428bd542aa6cd3b2b9fa32'
PATHS=['MapServer/src/entity/entserver.c','Game/src/entity/entrecv.c','Common/gameComm/wdwbase.c','Common/gameComm/wdwbase.h','Game/src/UI/uiOptions_Type.c','Game/src/UI/uiOptions_Type.h','Game/src/UI/uiNet.c','libs/UtilitiesLib/src/components/BitStream.c','Common/entity/entStrings.c','MapServer/src/entity/keybinds.c','Common/player/badges.h','Common/entity/attrib_description.c','Common/entity/attrib_description.h','Game/src/UI/uiKeybind.h','Common/entity/chatSettings.h','Common/gameComm/trayCommon.c','Common/gameComm/trayCommon.h','Common/entity/character_base.h','Game/src/UI/uiReticle.h','Common/entity/entity.h']
def sha(b): return hashlib.sha256(b).hexdigest()
def source(p): return subprocess.check_output(['git','-C',str(ROOT),'show',PIN+':upstream/ouroboros/'+p]).decode().replace('\r\n','\n')
def extract(text,name):
 m=re.search(r'^[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m:raise ValueError('missing '+name)
 at=text.index('{',m.start())+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def run(cmd):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,timeout=180)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout

def generate(texts):
 spec=importlib.util.spec_from_file_location('bits',ROOT/'native-android/tools/protocol_fixture/prepare.py');bits=importlib.util.module_from_spec(spec);spec.loader.exec_module(bits)
 code=bits.PREAMBLE;functions={}
 def get(path,n):
  body=extract(texts[path],n);functions[n]={'source':path,'sha256_lf':sha(body.encode())};return body
 code+='\n#define THREADSAFE_STATIC static\n#define THREADSAFE_STATIC_MARK(x)\n'
 code+=''.join(get(PATHS[7],n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString','bsReadStringAndLength','bsWriteF32','bsReadF32'])
 code+='''
#define TRUE 1
#define FALSE 0
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
static void strncpyt(char*d,const char*s,size_t n){assert(n);strncpy(d,s,n-1);d[n-1]=0;}
static void pktSendBits(Packet*p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet*p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet*p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet*p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendF32(Packet*p,float f){bsWriteF32(&p->stream,f);}
static float pktGetF32(Packet*p){return bsReadF32(&p->stream);}
static void pktSendString(Packet*p,const char*s){bsWriteString(&p->stream,s?s:"");}
static char*pktGetString(Packet*p){int n;return bsReadStringAndLength(&p->stream,&n);}
static void pktSendIfSetF32(Packet*p,float f){pktSendBits(p,1,f!=0);if(f!=0)pktSendF32(p,f);}
static float pktGetIfSetF32(Packet*p){return pktGetBits(p,1)?pktGetF32(p):0;}
'''
 # Copy exact original enum/struct/table; stash is explicitly fixture storage.
 header=texts[PATHS[5]]
 code+=re.search(r'typedef enum Show\s*\{.*?\}\s*Show;',texts[PATHS[18]],re.S).group(0)+'\n'
 code+=re.search(r'typedef enum EUserOptions\s*\{.*?\}EUserOptions;',header,re.S).group(0)
 code+='\ntypedef float F32;\n'+re.search(r'typedef struct UserOption\s*\{.*?\}UserOption;',header,re.S).group(0)
 table=texts[PATHS[4]];code+=table[table.index('UserOption game_options[]'):table.index('static StashTable')]
 code+='''
typedef void** StashTable;static void*fixture_stash[256];
static StashTable stashTableCreateInt(int n){(void)n;memset(fixture_stash,0,sizeof(fixture_stash));return fixture_stash;}
static void stashIntAddPointer(StashTable s,int id,void*v,int overwrite){(void)overwrite;assert(id>=0&&id<256&&!s[id]);s[id]=v;}
static void stashIntFindPointer(StashTable s,int id,void**v){assert(id>=0&&id<256);*v=s[id];}
static StashTable st_GameOptions;
'''+get(PATHS[4],'initGameOptionStash')+get(PATHS[4],'userOptionGet')+get(PATHS[6],'receiveOptions')
 whole_send=get(PATHS[0],'sendCharacterToClient')
 start=whole_send.index('    if( e->pl->options_saved )');end=whole_send.index('    pktSendBitsPack( pak, 9, e->pl->divSuperName')
 options=whole_send[start:end]
 fields=sorted(set(re.findall(r'e->pl->(\w+)',options)));floats=set(re.findall(r'pktSendF32\(\s*pak,\s*e->pl->(\w+)\s*\)',options))
 code+='typedef struct {'+''.join(('float ' if f in floats else 'U32 ')+f+';' for f in fields)+'} Player;typedef struct{Player*pl;} Entity;\n'
 code+='static void original_send_options(Packet*pak,Entity*e){\n'+options+'}\n'
 code+='void options_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){\n U32 memory[4096]={0};Packet p={0};Player player={0};Entity entity={&player};\n'
 for index,f in enumerate(fields):
  value='(float)((scenario+'+str(index)+')%17)/4.0f' if f in floats else '((scenario*37u+'+str(index)+'u)^0xa5a5a5a5u)'
  code+='player.'+f+'='+value+';\n'
 code+='''
 player.options_saved=scenario%2;
 player.contactSortByName=scenario%5==0;player.contactSortByZone=scenario%5==1;
 player.contactSortByRelationship=scenario%5==2;player.contactSortByActive=scenario%5==3;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;
 if(prefix)bsWriteBits(&p.stream,prefix,0);original_send_options(&p,&entity);
 *bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
 observed[0]=pktGetBits(&p,1);
 if(observed[0]){receiveOptions(&p);for(int i=1;i<kUO_OptionTotal;i++){UserOption*o=userOptionGet(i);if(o->bitSize<0)memcpy(&observed[i],&o->fVal,4);else observed[i]=(U32)o->iVal;}}
 else{observed[1]=pktGetBits(&p,1);float f=pktGetF32(&p);memcpy(&observed[2],&f,4);f=pktGetF32(&p);memcpy(&observed[3],&f,4);}
 *end=bsGetCursorBitPosition(&p.stream);
}
'''
 # WdwBase has no external wire dependencies. Exact original enums/structure.
 header=texts[PATHS[3]]
 for name in ['WindowName','WindowDisplayMode','WindowStartState']:
  code+=re.search(r'typedef enum '+name+r'\s*\{.*?\}\s*'+name+r';',header,re.S).group(0)+'\n'
 code+=re.search(r'typedef struct WdwBase\s*\{.*?\}\s*WdwBase;',header,re.S).group(0)+'\n'
 code+=''.join(get(PATHS[2],n) for n in ['sendWindow','receiveWindowIdx','receiveWindow'])
 code+='''
void window_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[4096]={0};Packet p={0};WdwBase w={0},d={0};int idx=(int)(scenario%MAX_WINDOW_COUNT),decoded;
 w.xp=(int)(scenario*65537u);w.yp=-(int)(scenario*257u);w.mode=scenario%5;w.locked=scenario%2;
 w.start_shrunk=scenario%3;w.color=(int)(0xff000000u|scenario);w.back_color=(int)(0x80000000u|scenario);
 w.maximized=(scenario>>1)%2;w.draggable_frame=(scenario>>2)%2;w.wd=100+scenario;w.ht=500+scenario;
 w.sc=scenario%3?(float)(scenario%11)/4.f:0;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;
 if(prefix)bsWriteBits(&p.stream,prefix,0);sendWindow(&p,&w,idx);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
 receiveWindowIdx(&p,&decoded);receiveWindow(&p,&d);*end=bsGetCursorBitPosition(&p.stream);
 U32 values[]={decoded,d.xp,d.yp,d.mode,d.locked,d.color,d.back_color,d.maximized,d.draggable_frame,d.wd,d.ht,0};memcpy(&values[11],&d.sc,4);memcpy(observed,values,sizeof(values));
}
'''
 # Constant query avoids silently copying old numeric maxima.
 code+='void constants(U32*out){out[0]=kUO_OptionTotal;out[1]=MAX_WINDOW_COUNT;out[2]=WDW_CHAT_BOX;out[3]=ALWAYS_CLOSED;out[4]=WINDOW_DOCKED;for(int i=1;i<kUO_OptionTotal;i++)out[4+i]=(U32)userOptionGet(i)->bitSize;}\n'
 code+=re.search(r'typedef struct EntStrings\s*\{.*?\}\s*EntStrings;',texts[PATHS[19]],re.S).group(0)+'\n'
 code+=''.join(get(PATHS[8],n) for n in ['breakHTMLtags','sendEntStrings','receiveEntStrings'])
 code+='''
void strings_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed){
 U32 memory[4096]={0};Packet p={0};EntStrings s={0},d={0};
 for(unsigned i=0;i<(scenario%2?127:0);i++)s.motto[i]='A'+i%26;
 for(unsigned i=0;i<(scenario%3?1023:0);i++)s.playerDescription[i]=i%11==0?'<':i%11==1?'>':'a'+i%26;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;
 if(prefix)bsWriteBits(&p.stream,prefix,0);sendEntStrings(&p,&s);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;receiveEntStrings(&p,&d);*end=bsGetCursorBitPosition(&p.stream);
 U32 h=2166136261u;for(unsigned i=0;i<strlen(d.motto);i++){h^=(U8)d.motto[i];h*=16777619u;}observed[0]=h;h=2166136261u;for(unsigned i=0;i<strlen(d.playerDescription);i++){h^=(U8)d.playerDescription[i];h*=16777619u;}observed[1]=h;observed[2]=strlen(d.motto);observed[3]=strlen(d.playerDescription);
}
'''
 return code,functions,{'options_statement_sha256_lf':sha(options.encode()),'option_fields':fields,'float_fields':sorted(floats)}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--fixtures-output',type=Path);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 texts={n:source(n) for n in PATHS};pins={n:sha(s.encode()) for n,s in texts.items()};pinfile=HERE/'source-pins.json'
 if a.initialize_pins:pinfile.write_text(json.dumps(pins,indent=2)+'\n')
 elif json.loads(pinfile.read_text())!=pins:raise ValueError('source pin changed')
 code,functions,schema=generate(texts)
 with tempfile.TemporaryDirectory(prefix='coh-outer-character-') as tmp:
  work=Path(tmp);(work/'original.c').write_text(code);run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(ROOT/'native-android/include'),work/'original.c','-o',work/'original.so'])
  lib=C.CDLL(str(work/'original.so'));values=(C.c_uint32*256)();lib.constants(values)
  result={'schema':'coh-character-outer-oracles-v1','passed':True,'source_pin':PIN,'original_source_sha256_lf':pins,'original_functions':functions,'original_generated_source_sha256':sha(code.encode()),'source_schema':schema,'constants':{'options_total_including_zero':values[0],'windows':values[1],'chat_window_index':values[2],'always_closed':values[3],'window_docked':values[4],'option_widths_in_enum_order':[C.c_int32(values[4+i]).value for i in range(1,values[0])]},'cases':[]}
  for kind,scenarios in [('options',20),('window',130),('strings',6)]:
   fn=getattr(lib,kind+'_fixture');fn.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p]
   for aligned in (0,1):
    for prefix in (range(8) if not aligned else (0,8)):
     for scenario in range(scenarios):
      raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();observed=(C.c_uint32*256)();fn(scenario,aligned,prefix,raw,C.byref(bits),C.byref(end),observed)
      if bits.value!=end.value:raise ValueError(f'original cursor mismatch {kind}/{scenario}/{aligned}/{prefix}: {bits.value}!={end.value}')
      count=(values[0] if scenario%2 else 4) if kind=='options' else (12 if kind=='window' else 4)
      result['cases'].append({'kind':kind,'scenario':scenario,'aligned':aligned,'begin_bit':prefix,'end_bit':bits.value,'wire_hex':bytes(raw[:(bits.value+7)//8]).hex(),'observed':list(observed[:count])})
  result['independent_model']=independent.qualify(result['cases'],result['constants'])
  result.update(cases_count=len(result['cases']),original_oracle_sanitized=False,full_outer_groups_4_to_6_complete=False,whole_character_complete=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False,physical_thor_accepted=False)
  if texts!={n:source(n) for n in PATHS}:raise ValueError('source mutated')
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
  if a.fixtures_output:a.fixtures_output.write_text(code)
  print(json.dumps({'passed':True,'cases':len(result['cases']),'constants':result['constants']}))
if __name__=='__main__':main()
