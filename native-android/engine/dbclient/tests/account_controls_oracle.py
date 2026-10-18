"""Trusted original account-control sender/relay/client fixtures, no service."""
from pathlib import Path
import ctypes as C, hashlib, importlib.util, json, re, subprocess
HERE=Path(__file__).resolve().parent
FUNCTIONS={
'libs/UtilitiesLib/src/components/BitStream.c':['initBitStream','bsWriteBits','bsReadBits','bsWriteBitsPack','bsReadBitsPack','bsWriteString','bsReadStringAndLength','bsGetCursorBitPosition'],
'libs/UtilitiesLib/src/network/net_packet.c':['pktSendBits','pktGetBits','pktSendBitsPack','pktGetBitsPack','pktSendString','pktGetStringAndLength'],
'libs/UtilitiesLib/src/network/net_packetutil.c':['pktSendBitsAuto','pktGetBitsAuto'],
'DBServer/src/accountservercomm.c':['account_clientCountFailure','account_clientAccountServerUnavailable'],
'QueueServer/src/QueueServer_Passthrough.c':['passSendCharacterCounts','passAccountServerUnavailable'],
'Game/src/clientcomm/dbclient.c':['handleSendCharacterCounts','receiveAccountServerUnavailable'],
}
AUDIT=['Common/comm_backend.h','AccountServer/src/AccountServer.cpp','Game/src/UI/uiServerTransfer.c','DBServer/src/clientcomm.c']
def digest(b):return hashlib.sha256(b).hexdigest()
def extract(source,name):
 m=re.search(r'^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',source,re.M)
 if not m:raise ValueError('missing source function '+name)
 at=source.index('{',m.start());depth=0;mode='code'
 while at<len(source):
  c=source[at];n=source[at:at+2]
  if mode=='code':
   if n=='//':mode='line';at+=2;continue
   if n=='/*':mode='comment';at+=2;continue
   if c in ('"',"'"):mode=c
   elif c=='{':depth+=1
   elif c=='}':
    depth-=1
    if not depth:return source[m.start():at+1]+'\n'
  elif mode=='line':
   if c=='\n':mode='code'
  elif mode=='comment':
   if n=='*/':mode='code';at+=2;continue
  elif c=='\\':at+=2;continue
  elif c==mode:mode='code'
  at+=1
 raise ValueError('unclosed source function')
def source_pins(root):
 sources={p:(root/'upstream/ouroboros'/p).read_bytes().replace(b'\r\n',b'\n')for p in [*FUNCTIONS,*AUDIT]}
 spans={n:extract(sources[p].decode(),n)for p,names in FUNCTIONS.items()for n in names}
 return sources,spans,{'sha256_lf':{p:digest(b)for p,b in sources.items()},'functions_sha256_lf':{n:digest(s.encode())for n,s in spans.items()}}
def produce(root,work):
 root=Path(root);work=Path(work);sources,spans,pins=source_pins(root)
 if json.loads((HERE/'account-controls-source-pins.json').read_bytes())!=pins:raise ValueError('original account-control source mismatch')
 spec=importlib.util.spec_from_file_location('account_control_bits',root/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 pre=helper.PREAMBLE
 pre=pre.replace('static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}','')
 code=pre+r'''
#define THREADSAFE_STATIC static
#define THREADSAFE_STATIC_MARK(x)
#define AINRANGE(v,a) ((unsigned)(v)<sizeof(a)/sizeof(*(a)))
static int g_bAssertOnBitStreamError;
static U32 bsTypedReadBits(BitStream*b,int n){(void)b;(void)n;assert(0);return 0;}
static void bsTypedWriteString(BitStream*b,const char*s){(void)b;(void)s;assert(0);}
static char *bsTypedReadStringAndLength(BitStream*b,int*n){(void)b;(void)n;assert(0);return NULL;}
int auto_bins[]={2,10,24,32};
'''
 for p in list(FUNCTIONS)[:3]:code+='\n'.join(spans[n]for n in FUNCTIONS[p])
 backend=sources['Common/comm_backend.h'].decode();start=backend.index('enum\n{\n    DBGAMESERVER_SEND_PLAYERS');end=backend.index('\n};',start)+3
 code+='\nenum {COMM_MAX_CMD=2};\n'+backend[start:end]+r'''
#define pktGetString(p) pktGetStringAndLength((p),&(int){0})
static U32 storage[32770];static Packet packet;static NetLink link;
typedef struct {int unused;} GameClientLink;static GameClientLink client;
static unsigned aligned,legacy,sends,done,errors,rows;static struct {int vip;} db_info;
static NetLink *linkFromAuthId(U32 id,GameClientLink **out){assert(id==42);*out=&client;return &link;}
static Packet *dbClient_createPacket(U32 command,GameClientLink*c){assert(c==&client);memset(storage,0,sizeof(storage));memset(&packet,0,sizeof(packet));initBitStream(&packet.stream,(U8*)storage,sizeof(storage)-16,Write,aligned,0);pktSendBitsPack(&packet,1,command+(legacy?5:0));return &packet;}
static void pktSend(Packet **p,NetLink*l){assert(*p==&packet&&l==&link);sends++;*p=NULL;}
static U32 pktSendGetBitsAuto(Packet*out,Packet*in){U32 v=pktGetBitsAuto(in);pktSendBitsAuto(out,v);return v;}
static void pktSendGetStringNLength(Packet*out,Packet*in){pktSendString(out,pktGetString(in));}
static void characterTransferAddCharacterCount(const char*s,int a,int b,int c,int d){assert(s);(void)a;(void)b;(void)c;(void)d;rows++;}
static void characterTransferReceiveCharacterCountsDone(void){done++;}
static void characterTransferReceiveError(const char*s){assert(s);errors++;}
static void accountCatalogDone(void){done++;}
'''
 for p in list(FUNCTIONS)[3:]:code+='\n'.join(spans[n]for n in FUNCTIONS[p])
 code+=r'''
void original_control(unsigned profile,unsigned old,unsigned kind,unsigned count,unsigned length,U8*out,U32*bits){
 assert(profile<=1&&old<=1&&count<=257&&length<=16384);aligned=profile;legacy=old;sends=0;
 if(kind==0)account_clientAccountServerUnavailable(42);
 else if(kind==1)account_clientCountFailure(42);
 else {dbClient_createPacket(DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT,&client);pktSendBitsAuto(&packet,count);char text[16385];for(unsigned i=0;i<length;i++)text[i]='x';text[length]=0;
  if(!count)pktSendString(&packet,text);
  else for(unsigned i=0;i<count;i++){pktSendString(&packet,text);U32 values[]={0,3,1023,16777215,0xffffffff};for(unsigned j=0;j<5;j++)pktSendBitsAuto(&packet,values[(i+j)%5]);}
 }
 assert(!packet.stream.errorFlags);*bits=packet.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
 /* Execute exact client consumer on trusted complete source output. The five
  * row values deliberately include all Auto bins and truthy non-Bool VIP. */
 Packet input=packet;input.stream.mode=Read;input.stream.cursor.byte=input.stream.cursor.bit=0;
 U32 cmd=pktGetBitsPack(&input,1)-(old?5:0);done=errors=rows=0;db_info.vip=1;
 if(cmd==DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT)handleSendCharacterCounts(&input);else receiveAccountServerUnavailable(&input);
 assert(!input.stream.errorFlags&&bsGetCursorBitPosition(&input.stream)==*bits);
 assert(cmd==DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT?(count&&kind!=1?done==1&&rows==count&&!errors:errors==1&&!done&&!rows):done==1&&!errors&&!rows);
 /* Execute whole Queue passthrough too and require exact packet equality. */
 input=packet;input.stream.mode=Read;input.stream.cursor.byte=input.stream.cursor.bit=0;pktGetBitsPack(&input,1);
 U32 relay_storage[32770]={0};Packet relay={0};initBitStream(&relay.stream,(U8*)relay_storage,sizeof(relay_storage)-16,Write,profile,0);pktSendBitsPack(&relay,1,cmd+(old?5:0));
 if(cmd==DBGAMESERVER_ACCOUNTSERVER_CHARCOUNT)passSendCharacterCounts(&input,&relay);else passAccountServerUnavailable(&input,&relay);
 assert(relay.stream.bitLength==*bits&&!memcmp(out,relay_storage,(*bits+7)/8));
}
'''
 source=work/'account-original.c';libpath=work/'account-original.so';source.write_text(code)
 p=subprocess.run(['cc','-std=c11','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),str(source),'-o',str(libpath)],capture_output=True,text=True,timeout=120)
 if p.returncode:raise ValueError(p.stderr)
 lib=C.CDLL(str(libpath));lib.original_control.argtypes=[C.c_uint]*5+[C.c_void_p,C.POINTER(C.c_uint32)]
 configs=[(0,0,0),(1,0,0),(2,0,0),(2,0,16383),(2,0,16384),(2,1,0),(2,3,7),(2,256,0),(2,257,0),(2,1,16383),(2,1,16384)]
 header='/* Exact original account failure senders and original scalar/string writers. */\n';cases=[]
 for aligned in (0,1):
  for legacy in (0,1):
   for kind,count,length in configs:
    data=(C.c_uint8*131072)();bits=C.c_uint32();lib.original_control(aligned,legacy,kind,count,length,data,C.byref(bits));raw=bytes(data[:(bits.value+7)//8]);name='account_'+str(len(cases));header+='static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};\n';cases.append((name,bits.value,aligned,legacy,kind,count,length))
 header+='static const struct {const uint8_t*data;size_t bits;unsigned aligned,legacy,kind,shards,length;} account_fixtures[]={\n'+''.join('{'+n+','+','.join(map(str,v))+'},\n'for n,*v in cases)+'};\n';(work/'account-fixtures.h').write_text(header)
 return {'whole_source_sha256_lf':pins['sha256_lf'],'whole_function_sha256_lf':pins['functions_sha256_lf'],'original_failure_senders_executed':2,'original_complete_client_and_queue_consumers_executed':True,'positive_rows_fixture_written_with_original_bit_writers':True,'positive_account_server_full_dispatcher_executed':False,'fixtures':len(cases),'generated_source_sha256':digest(code.encode()),'generated_header_sha256':digest(header.encode()),'oracle_elf_sha256':digest(libpath.read_bytes()),'original_unsafe_code_trusted_fixture_only':True,'real_network_ui_account_service':False}
