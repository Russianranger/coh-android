"""New trusted EDITMSG oracle; execute unchanged original sender, not a server.

Only fixed fixture-owned format/data enter the bounded estr/packet adapters.
The source console printf is counted instead of printing fixture message text.
No original dispatcher, network, UI, account or world service executes.
"""
from pathlib import Path
import ctypes as C
import hashlib,importlib.util,json,re,subprocess
HERE=Path(__file__).resolve().parent
FUNCTIONS={
 'libs/UtilitiesLib/src/components/BitStream.c': ['initBitStream','bsWriteBits','bsWriteBitsPack','bsWriteString','bsGetCursorBitPosition'],
 'libs/UtilitiesLib/src/network/net_packet.c': ['pktSendBits','pktSendBitsPack','pktSendString'],
 'MapServer/src/group/groupnetdb.c': ['sendEditMessage'],
}
AUDIT={
 'Game/src/clientcomm/clientcomm.c':['commHandleMessage'],
 'Game/src/edit/edit_net.c':['editNetUpdate'],
 'Game/src/edit/edit_select.c':['editWaitingForServer'],
 'MapServer/src/svr/svr_tick.c':['svrTickSendQueuedErrors','svrTickDoNetSend'],
 'Common/comm_game.h':[],
}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def extract(source,name):
 match=re.search(r'^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',source,re.M)
 if not match:raise ValueError('missing original function '+name)
 at=source.index('{',match.start())+1;depth=1
 while depth:depth+=(source[at]=='{')-(source[at]=='}');at+=1
 return source[match.start():at]+'\n'
def produce_fixtures(root,work):
 root=Path(root).resolve();work=Path(work);sources={p:(root/'upstream/ouroboros'/p).read_bytes().replace(b'\r\n',b'\n')for p in {*FUNCTIONS,*AUDIT}}
 pins=json.loads((HERE/'editmsg-source-pins.json').read_bytes())
 if {p:digest(raw)for p,raw in sources.items()}!=pins['sha256_lf']:raise ValueError('EDITMSG original source pin mismatch')
 spans={name:extract(sources[p].decode(),name)for p,names in {**FUNCTIONS,**AUDIT}.items()for name in names}
 if {name:digest(text.encode())for name,text in spans.items()}!=pins['functions_sha256_lf']:raise ValueError('EDITMSG original function pin mismatch')
 spec=importlib.util.spec_from_file_location('editmsg_original_bits',root/'native-android/tools/protocol_fixture/prepare.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 text=sources['Common/comm_game.h'].decode();start=text.index('typedef enum EditorMessageType');end=text.index('}EditorMessageType;',start)+len('}EditorMessageType;');enum=text[start:end]
 start=text.index('typedef enum ServerCommCmd');end=text.index('} ServerCommCmd;',start)+len('} ServerCommCmd;');enum='enum {COMM_MAX_CMD=2};\n'+text[start:end]+'\n'+enum
 code=helper.PREAMBLE+'\n#include <stdarg.h>\n'+enum+'\nstatic void bsTypedWriteString(BitStream*b,const char*s){(void)b;(void)s;assert(0);}\n'
 code+='\n'.join(spans[n]for names in list(FUNCTIONS.values())[:2]for n in names)
 code+=r'''
static U32 storage[8192];static Packet packet;static unsigned aligned,sends,console_calls;
static char text_buffer[20000];
static char *estrTemp(void){text_buffer[0]=0;return text_buffer;}
static void estrConcatfv(char **out,const char *fmt,va_list args){assert(*out==text_buffer);int n=vsnprintf(text_buffer,sizeof(text_buffer),fmt,args);assert(n>=0&&(size_t)n<sizeof(text_buffer));}
static void estrDestroy(char **out){assert(*out==text_buffer);*out=NULL;}
static Packet *pktCreate(void){memset(storage,0,sizeof(storage));memset(&packet,0,sizeof(packet));initBitStream(&packet.stream,(U8*)storage,sizeof(storage)-8,Write,aligned,0);return &packet;}
static void pktSend(Packet **p,NetLink *link){assert(*p==&packet&&link);assert(!packet.stream.errorFlags);sends++;*p=NULL;}
static int fixture_printf(const char *fmt,...){assert(!strcmp(fmt,"%s\n"));console_calls++;return 0;}
#define printf fixture_printf
'''+spans['sendEditMessage']+r'''
#undef printf
void original_editmsg(unsigned mode,unsigned type,unsigned count,U8 *out,U32 *bits){
 assert(mode<=1&&type<=3&&count<=16384);char text[16385];for(unsigned i=0;i<count;i++)text[i]=(char)(1+i%255);text[count]=0;
 NetLink link={0};aligned=mode;sends=console_calls=0;sendEditMessage(&link,(EditorMessageType)type,"%s",text);
 assert(sends==1&&console_calls==(type==3));*bits=packet.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
'''
 source=work/'editmsg-original.c';exe=work/'editmsg-original.so';source.write_text(code)
 result=subprocess.run(['cc','-std=c11','-O0','-fPIC','-shared','-w','-I'+str(root/'native-android/include'),str(source),'-o',str(exe)],capture_output=True,text=True,timeout=120)
 if result.returncode:raise ValueError('EDITMSG original compile failed: '+result.stderr)
 lib=C.CDLL(str(exe));lib.original_editmsg.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.POINTER(C.c_uint32)]
 rows=[];header='/* Trusted output of unchanged original sendEditMessage and bit writers. */\n'
 for aligned in (0,1):
  for typ in range(4):
   for count in (0,1,257,16383,16384):
    data=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_editmsg(aligned,typ,count,data,C.byref(bits));raw=bytes(data[:(bits.value+7)//8]);name='editmsg_'+str(len(rows))
    header+='static const unsigned char '+name+'[]={'+','.join(map(str,raw))+'};\n';rows.append((name,bits.value,aligned,typ,count));
 header+='static const struct {const unsigned char*data;size_t bits;unsigned aligned,type,bytes;} editmsg_fixtures[]={\n'+''.join('{'+name+','+','.join(map(str,(bits,aligned,typ,count)))+'},\n'for name,bits,aligned,typ,count in rows)+'};\n'
 (work/'editmsg-fixtures.h').write_text(header)
 return {'schema':'coh-original-editmsg-fixtures-v1','whole_source_sha256_lf':pins['sha256_lf'],'whole_function_sha256_lf':pins['functions_sha256_lf'],'whole_sendEditMessage_executed':True,'profiles':2,'types':4,'fixtures':len(rows),'generated_source_sha256':digest(code.encode()),'generated_header_sha256':digest(header.encode()),'oracle_binary_sha256':digest(exe.read_bytes()),'trusted_bounded_estr_and_packet_adapters':True,'console_printf_counted_not_printed':True,'original_network_ui_dispatcher_executed':False,'real_server':False}
