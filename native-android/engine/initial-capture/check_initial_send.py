#!/usr/bin/env python3
"""Original CLIENT_INPUT/READY producer goldens; no sockets, server or receipts.

Original x86 BitStream code runs at O0 on padded/aligned storage. Sanitizers
cover the portable serializers against those independent original outputs.
The caller owns build serialization; this script never acquires a flock.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent
EXTRA_PINS={
 'Game/src/clientcomm/authclient.c':'d1f5ff0dae7728af8537e727ff781c8930345d536634e3438e661ebb8c3f3015',
 'Game/src/clientcomm/clientcomm.h':'640af8fd68bc3c42390235e15adc13192129d3626199ec6b27bc1844d44fae54',
 'Game/src/gameComm/initClient.c':'2a6da67369d4f1506ebc112b7bfe3485c741920f8ec12f3229e4c10dbe608d38',
 'Game/src/UI/uiTarget.c':'cbfdd2d89cffd3a58f5d6803867c980efd20b58bae96d5b525d1b69e7b0c8866',
 'libs/UtilitiesLib/src/utils/cmdoldparse.c':'5e370b1d639d540992799aa1ba9519c34a314c5b16ca17c625eef8ba3ad71d10',
 'libs/UtilitiesLib/src/network/crypt.cpp':'cde2d5acd0bd23cf2b681d968f3b241ace148afc31f7a8af353920087e812b60'}
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,**kw):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
    if result.returncode:raise RuntimeError(str(args[:3])+' failed:\n'+result.stdout[-2000:]+result.stderr[-4000:])
    return result.stdout

def producer(root,work):
    spec=importlib.util.spec_from_file_location('accepted_original_bitstream',root/'native-android/tools/protocol_fixture/prepare.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    pins=dict(json.loads((root/'native-android/engine/mapclient/source-pins.json').read_text())['sha256_lf']);pins.update(EXTRA_PINS)
    texts={}
    for path,pin in pins.items():
        raw=subprocess.check_output(['git','-C',str(root),'show','HEAD:upstream/ouroboros/'+path]).replace(b'\r\n',b'\n')
        if sha(raw)!=pin:raise ValueError('original source pin: '+path)
        texts[path]=raw.decode()
    if not re.search(r'int\s+gSelectedDBID\s*=\s*0\s*;',texts['Game/src/UI/uiTarget.c']):raise ValueError('source initial selected-target DBID changed')
    client=texts['Game/src/clientcomm/clientcomm.c'];init=texts['Game/src/gameComm/initClient.c']
    auth=texts['Game/src/clientcomm/authclient.c'];header=texts['Game/src/clientcomm/clientcomm.h']
    # Exact source blocks; no independent reconstruction of their write order.
    ack_begin=client.index('            U32 ackFullUpdateID = pktGetBitsPack(pak, 1);')
    ack_end=client.index('            netSendIdle(link);',ack_begin)
    ack=client[ack_begin:ack_end]
    ready_begin=client.index('        pak = pktCreateEx(&comm_link,CLIENT_READY);')
    ready_end=client.index('        rdrNeedGammaReset();',ready_begin)
    ready=client[ready_begin:ready_end]
    controls=helper.extract(client,'commSendControlUpdate');first_end=controls.index('    pktSendBits(pak, 1, 1);')
    first_controls=controls[:first_end]+'    assert(!"non-first control update outside fixture");\n}\n'
    auth_begin=auth.index('    memset(&auth_info,0,sizeof(auth_info));',auth.index('int authLogin('))
    auth_end=auth.index('    if (!game_state.auth_address[0]',auth_begin)
    auth_block=auth[auth_begin:auth_end]
    comm_enum=re.search(r'typedef enum ClientCommCmd\s*\{.*?} ClientCommCmd;',texts['Common/comm_game.h'],re.S).group()
    inp_enum=re.search(r'enum\s*\{.*?\n};',texts['Common/entity/entVarUpdate.h'],re.S).group()
    macros=header[header.index('#define START_INPUT_PACKET'):header.index('#define RECV_HISTORY_SIZE')]
    pre=helper.PREAMBLE.replace('int compressionAllowed,orderedAllowed;','int compressionAllowed,orderedAllowed,controlCommandsSeparate,cookieSend,cookieEcho;U32 nextID,cookie_send,cookie_recv,last_cookie_recv;')
    pre=pre.replace('U32 checksum,truncatedID,','U32 reliable,checksum,truncatedID,')
    pre=pre.replace('static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}','')
    code=pre+r'''
#include <math.h>
typedef int S32;typedef float F32;typedef struct {int unused;} ControlStateChange;
typedef struct {int svr_idx;} Entity;
typedef struct {const char*name;int send;} Cmd;typedef void CmdContext;
typedef struct {U32 actualTime,mmTime;F32 timestep,timestep_noscale;uint64_t qpc,qpcFreq;} ControlLogEntry;
static struct {U32 new_last_send_ms;} csc_send;
static struct {U32 first_packet_sent,client_pos_id;struct{U32 last_send_ms;}time;struct{int cur;ControlLogEntry entries[1];}controlLog;struct{int lag,lag_vary,pl,oo_packets;}snc_client;} control_state;
static struct {int game_mode;}game_state;
static struct {struct{U32 cookie;}mapserver;}db_info;
static struct {char name[128];U32 passwordMD5[4];}auth_info;
static Cmd control_cmds[]={{0,0}};
static Entity*current_target;static int gSelectedDBID;
int glob_client_pos_id,glob_plrstate_valid;
static int waiting_for_full_update,enter_game_now,isInitialLogin,console_open;
static NetLink comm_link;
static Packet*client_input_pak,*captured;
static Packet packets[4];static U32 memories[4][256];static unsigned packet_count,aligned_profile,send_count,waiting_when_sent;
#define COMM_MAX_CMD 2
#define COMM_OLDMAX_CMD 7
#define COMM_CONTROLCOMMAND 0
#define SHOW_LOAD_SCREEN 0
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define START_BIT_COUNT(a,b) ((void)0)
#define STOP_BIT_COUNT(a) ((void)0)
#define devassert(x) assert(x)
#define Strncpyt(dst,src) do{strncpy(dst,src,sizeof(dst)-1);dst[sizeof(dst)-1]=0;}while(0)
static U32 timeGetTime(void){return 0x01020304u;}
static int timerAlloc(void){return 1;}static void timerStart(int x){(void)x;}
static F32 timerElapsed(int x){(void)x;return 1;}static F32 timerElapsedAndStart(int x){(void)x;return 1;}
static Entity*controlledPlayerPtr(void){return NULL;}
static void cmdParse(char*s){(void)s;assert(0);}
static void pktSendF32(Packet*p,F32 v){(void)p;(void)v;assert(0);}
static void sendBits64(Packet*p,uint64_t v){(void)p;(void)v;assert(0);}
static int cmdOldSendPacked(Packet*p,Cmd*c,Cmd*d,CmdContext*x){(void)p;(void)c;(void)d;(void)x;assert(0);return 0;}
static void cmdOldSetSends(Cmd*c,int v){assert(!c[0].name&&!v);}
static void lnkSimulateNetworkConditions(NetLink*l,int a,int b,int c,int d){(void)l;assert(!a&&!b&&!c&&!d);}
static int isConsoleOpen(void){return console_open;}
extern void cryptMD5Update(U8*,int);extern void cryptMD5Final(U32[4]);
static Packet*pktCreate(void){assert(packet_count<4);Packet*p=&packets[packet_count];memset(p,0,sizeof(*p));initBitStream(&p->stream,(U8*)memories[packet_count++],sizeof memories[0],Write,aligned_profile,0);return p;}
static void pktSend(Packet**p,NetLink*l){(void)l;captured=*p;*p=NULL;send_count++;waiting_when_sent=waiting_for_full_update;}
static void commNewInputPak(void){client_input_pak=pktCreate();}
void pktSendCmd(NetLink*,Packet*,int);
static Packet*pktCreateEx(NetLink*l,int cmd){Packet*p=pktCreate();pktSendCmd(l,p,cmd);return p;}
'''
    code+=comm_enum+'\n'+inp_enum+'\n'+macros+'\n'
    for name in ('initBitStream','bsWriteBits','bsReadBits','bsWriteBitsPack','bsReadBitsPack','bsWriteBitsArray','bsAlignByte','bsGetCursorBitPosition','bsGetBitLength'):
        body=helper.extract(texts['libs/UtilitiesLib/src/components/BitStream.c'],name);code+=body
    for name in ('pktSendBits','pktSendBitsPack','pktGetBitsPack','pktSendBitsArray'):
        code+=helper.extract(texts['libs/UtilitiesLib/src/network/net_packet.c'],name)
    code+='int auto_bins[]={2,10,24,32};\n'+helper.extract(texts['libs/UtilitiesLib/src/network/net_packetutil.c'],'pktSendBitsAuto')
    code+=helper.extract(texts['libs/UtilitiesLib/src/network/netio_send.c'],'pktSendCmd')
    code+=first_controls+helper.extract(texts['libs/UtilitiesLib/src/utils/cmdoldparse.c'],'cmdOldSend')
    code+=helper.extract(init,'setWaitingForFullUpdate')+helper.extract(init,'notifyReceivedCharacter')
    code+=helper.extract(client,'commSendInput')
    code+='\nstatic void source_auth(const char*name,const char*password){char passwordCopy[128];\n'+auth_block+'}\n'
    code+=r'''
static void reset(unsigned legacy,unsigned aligned){
 memset(packets,0,sizeof packets);memset(memories,0,sizeof memories);memset(&control_state,0,sizeof control_state);memset(&comm_link,0,sizeof comm_link);
 packet_count=send_count=0;captured=NULL;aligned_profile=aligned;comm_link.controlCommandsSeparate=!legacy;comm_link.nextID=0x11223344;
 current_target=NULL;gSelectedDBID=0;glob_client_pos_id=0;glob_plrstate_valid=1;waiting_for_full_update=enter_game_now=0;
}
void original_ack(unsigned legacy,unsigned aligned,U32 full_id,unsigned received,U8*out,U32*bits){
 reset(legacy,aligned);client_input_pak=pktCreate();U32 source_memory[64]={0};Packet incoming={0};
 initBitStream(&incoming.stream,(U8*)source_memory,sizeof source_memory,Write,aligned,0);pktSendBitsPack(&incoming,1,full_id);
 incoming.stream.mode=Read;incoming.stream.cursor.byte=incoming.stream.cursor.bit=0;Packet*pak=&incoming;
'''+ack+r'''
 waiting_for_full_update=received;notifyReceivedCharacter();assert(enter_game_now==(int)received);
 commSendInput();assert(send_count==1&&captured&&captured->reliable==1&&control_state.first_packet_sent==1);
 *bits=captured->stream.bitLength;memcpy(out,captured->stream.data,(*bits+7)/8);
}
void original_ready(unsigned legacy,unsigned aligned,U32 cookie,unsigned console,unsigned initial,const U8*md5,U8*out,U32*bits){
 reset(legacy,aligned);db_info.mapserver.cookie=cookie;console_open=console;isInitialLogin=initial;memcpy(auth_info.passwordMD5,md5,16);Packet*pak;
'''+ready+r'''
 assert(send_count==1&&captured&&captured->reliable==1&&!waiting_when_sent&&waiting_for_full_update);
 *bits=captured->stream.bitLength;memcpy(out,captured->stream.data,(*bits+7)/8);
}
void original_empty_password(U8*out){source_auth("LOCAL_SOURCE_FIXTURE","");memcpy(out,auth_info.passwordMD5,16);}
'''
    crypt=texts['libs/UtilitiesLib/src/network/crypt.cpp']
    cpp='''#include <stdint.h>\n#include <openssl/md5.h>\ntypedef unsigned char U8;typedef unsigned char byte;typedef uint32_t U32;
class MD5Adapter {MD5_CTX c;public:MD5Adapter(){MD5_Init(&c);}void Update(byte*p,int n){MD5_Update(&c,p,n);}void Final(byte*p){MD5_Final(p,&c);MD5_Init(&c);}};
static MD5Adapter object;static MD5Adapter*md5=&object;\nextern "C" {\n'''+helper.extract(crypt,'cryptMD5Update')+helper.extract(crypt,'cryptMD5Final')+'}\n'
    cfile=work/'source-producer.c';cppfile=work/'md5-adapter.cpp';cfile.write_text(code);cppfile.write_text(cpp)
    run(['cc','-std=c99','-O0','-fPIC','-w','-I'+str(root/'native-android/include'),'-c',cfile,'-o',work/'source.o'])
    run(['c++','-std=c++11','-O0','-fPIC','-Wno-deprecated-declarations','-c',cppfile,'-o',work/'md5.o'])
    run(['c++','-shared',work/'source.o',work/'md5.o','-lcrypto','-lm','-o',work/'source.so'])
    library=C.CDLL(str(work/'source.so'))
    library.original_ack.argtypes=[C.c_uint,C.c_uint,C.c_uint32,C.c_uint,C.c_void_p,C.POINTER(C.c_uint32)]
    library.original_ready.argtypes=[C.c_uint,C.c_uint,C.c_uint32,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.POINTER(C.c_uint32)]
    library.original_empty_password.argtypes=[C.c_void_p]
    proof={'source_sha256_lf':pins,'whole_commSendInput_sha256_lf':sha(helper.extract(client,'commSendInput').encode()),
           'whole_cmdOldSend_sha256_lf':sha(helper.extract(texts['libs/UtilitiesLib/src/utils/cmdoldparse.c'],'cmdOldSend').encode()),
           'first_control_branch_sha256_lf':sha(first_controls.encode()),'ALLENTS_ACK_statements_sha256_lf':sha(ack.encode()),
           'commReqScene_READY_statements_sha256_lf':sha(ready.encode()),'authLogin_MD5_statements_sha256_lf':sha(auth_block.encode()),
           'original_legacy_writer_sanitized':False,'MD5_engine':'OpenSSL adapter for original CryptoPP Update/Final calls; not a Win32 execution claim'}
    return library,proof

def fixtures(library,work):
    md5=(C.c_uint8*16)();library.original_empty_password(md5);digest=bytes(md5)
    if digest!=hashlib.md5(b'').digest():raise ValueError('original auth empty password digest differs')
    rows=['typedef struct {unsigned legacy,aligned,received,console,initial;uint32_t id,cookie,ack_bits,ready_bits;unsigned char ack[128],ready[128],md5[16];} SendGolden;','static const SendGolden source_sends[]={']
    ids=(0,1,2,3,7,31,255,65535,0x7fffffff,0x80000000,0xffffffff);count=0
    def array(data):return '{'+','.join(map(str,data))+'}'
    for legacy in (0,1):
        for aligned in (0,1):
            for ident in ids:
                for received in (0,1):
                    for console,initial in ((0,0),(1,0),(0,1),(1,1)):
                        a=(C.c_uint8*128)();b=(C.c_uint8*128)();ab=C.c_uint32();bb=C.c_uint32();cookie=0x1a2b3c4d
                        library.original_ack(legacy,aligned,ident,received,a,C.byref(ab))
                        library.original_ready(legacy,aligned,cookie,console,initial,md5,b,C.byref(bb))
                        rows.append('{'+','.join(str(x)+'u' for x in (legacy,aligned,received,console,initial,ident,cookie,ab.value,bb.value))+','+array(a[:(ab.value+7)//8])+','+array(b[:(bb.value+7)//8])+','+array(md5)+'},');count+=1
    rows+=['};'];(work/'initial-send-fixtures.h').write_text('\n'.join(rows)+'\n');return count,digest.hex()

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--candidate-root',type=Path);parser.add_argument('--sanitize',action='store_true');args=parser.parse_args()
    root=args.source_root.resolve();candidate=(args.candidate_root or root).resolve();native=candidate/'native-android'
    sourcepaths=[native/'engine/initial-capture/coh_initial_send.c',native/'engine/initial-capture/coh_initial_send.h',native/'engine/mapclient/coh_mapclient.c',native/'protocol/coh_protocol.c',HERE/'test_initial_send.c']
    frozen={p:p.read_bytes() for p in sourcepaths}
    def unchanged():
        if any(p.read_bytes()!=raw for p,raw in frozen.items()):raise ValueError('candidate changed during send qualification')
    with tempfile.TemporaryDirectory(prefix='coh-initial-send-') as t:
        work=Path(t);original,proof=producer(root,work);count,digest=fixtures(original,work);results={}
        modes=[('release',['-O2'])]
        if args.sanitize:modes += [('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        for name,flags in modes:
            unchanged();exe=work/name
            objects=[]
            for index,source in enumerate((sourcepaths[0],sourcepaths[2],sourcepaths[3],sourcepaths[4])):
                obj=work/(name+'-'+str(index)+'.o');objects.append(obj)
                # Match the existing mapclient checker: GCC's inlined unused
                # frame decoder reports maybe-uninitialized in protocol.c.
                # Keep that accepted dependency at O0, without disabling errors.
                dependency_flags=['-O0'] if source==native/'protocol/coh_protocol.c' else []
                run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffunction-sections','-fdata-sections',*flags,*dependency_flags,
                     '-I'+str(native/'include'),'-I'+str(native/'engine/initial-capture'),'-I'+str(work),'-c',source,'-o',obj])
            run(['cc',*flags,*objects,'-Wl,--gc-sections','-o',exe])
            results[name]=json.loads(run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));unchanged()
    print(json.dumps({'passed':True,'source_cases':count,'checks':results,'empty_plaintext_md5':digest,'source_producer':proof,'candidate_sha256':{str(p.relative_to(candidate)) if p.is_relative_to(candidate) else str(p):sha(b) for p,b in frozen.items()},'sockets_opened':False,'actual_server_or_Thor_measured':False},sort_keys=True))
if __name__=='__main__':main()
