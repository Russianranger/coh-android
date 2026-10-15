#!/usr/bin/env python3
"""Pinned unchanged DB request producer oracle plus bounded parser fixtures.

The unchanged original x86 bit writer executes only trusted aligned inputs.
Synthetic character lists are source-layout fixtures, never server captures.
ASan/UBSan separately cover new code and all malformed input checks.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, re, struct, subprocess, tempfile
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FILES=[
 'Common/auth/auth.h','Common/comm_backend.h','Common/entity/gametypes.h',
 'Game/src/clientcomm/dbclient.c','Game/src/clientcomm/dbclient.h',
 'libs/UtilitiesLib/src/components/BitStream.c',
 'libs/UtilitiesLib/src/network/net_packet.c',
 'libs/UtilitiesLib/src/network/net_packetutil.c',
 'libs/UtilitiesLib/src/network/netcomp.c',
 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
]
def run(cmd,**kw):
 p=subprocess.run([str(v) for v in cmd],text=True,capture_output=True,**kw)
 if p.returncode:raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
 return p.stdout
def oracle(repo,tmp):
 spec=importlib.util.spec_from_file_location('accepted_bit_reference',repo/'native-android/tools/protocol_fixture/prepare.py')
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 sources={f:(repo/'upstream/ouroboros'/f).read_text().replace('\r\n','\n') for f in FILES}
 pins={f:hashlib.sha256(v.encode()).hexdigest() for f,v in sources.items()}
 if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('DB original source pin mismatch')
 pre=helper.PREAMBLE
 pre=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',pre)
 pre+='\n#include <zlib.h>\n#define DBSERVER_CLIENT_PROTOCOL_VERSION 20110614\n#define DBGAMECLIENT_LOGIN 2\n#define DBGAMECLIENT_CHOOSE_PLAYER 3\n#define DISABLE_RENDER_TELEMETRY\n#define PERFINFO_AUTO_STOP(...)\n#define ARRAY_SIZE_CHECKED(a) (sizeof(a)/sizeof((a)[0]))\n'
 pre+='static void bsTypedWriteString(BitStream *b,const char *s){(void)b;(void)s;assert(0);}\n'
 bits=sources['libs/UtilitiesLib/src/components/BitStream.c']
 code=pre+'\n'.join(helper.extract(bits,n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsAlignByte','bsGetCursorBitPosition','bsWriteBitsArray','bsWriteString'])
 code+='\n'.join(helper.extract(sources['libs/UtilitiesLib/src/network/net_packet.c'],n) for n in ['pktSendBits','pktSendBitsPack','pktSendBitsArray','pktSendString'])
 code+=re.search(r'int auto_bins\[\] = \{[^}]+\};',sources['libs/UtilitiesLib/src/network/net_packetutil.c']).group(0)+'\n'
 code+=helper.extract(sources['libs/UtilitiesLib/src/network/net_packetutil.c'],'pktSendBitsAuto')
 code+='\n'.join(helper.extract(sources['libs/UtilitiesLib/src/network/netcomp.c'],n) for n in ['pktSendZippedAlready','pktSendZipped'])
 # Exact contiguous producer statements, without changing field order or values.
 db=sources['Game/src/clientcomm/dbclient.c'];start=db.index('        pak = pktCreateEx(&db_comm_link,DBGAMECLIENT_LOGIN);');end=db.index('        pktSend(&pak,&db_comm_link);',start)
 login=db[start:end]
 start=db.index('    pak = pktCreateEx(&db_comm_link,DBGAMECLIENT_CHOOSE_PLAYER);');end=db.index('    pktSend(&pak,&db_comm_link);',start)
 choose=db[start:end]
 code+='''
static U32 storage[16384];static Packet packet;static int db_comm_link,old_profile;
static struct {int local_map_server;} game_state;
static struct {U8 auth_user_data[128];struct{char name[64];} players[64];} db_info;
static char *getExecutablePatchVersion(void *p){(void)p;return "disposable-native-test";}
static char *regGetPatchValue(void){return "updater fixture";}
static int encryptedKeyedAccessLevel(void){return 7;}
char *encrypedKeyIssuedTo="authorized test fixture";
static Packet *pktCreateEx(void *link,int cmd){(void)link;memset(storage,0,sizeof(storage));memset(&packet,0,sizeof(packet));initBitStream(&packet.stream,(U8*)storage,sizeof(storage),Write,old_profile&1,0);pktSendBitsPack(&packet,1,cmd+((old_profile&2)?5:0));return &packet;}
void original_login(int profile,U8 *out,U32 *length){
 old_profile=profile;Packet *pak;char *auth_name="fixture";int user_id=0x12345678,cookie=(int)0x89abcdef,no_version_check=0,no_timeout=1;U32 checksum[4];
 for(unsigned i=0;i<128;i++)db_info.auth_user_data[i]=(U8)(i^0xa5);
 for(unsigned i=0;i<16;i++)((U8*)checksum)[i]=(U8)(i*13);
'''+login+'''
 *length=packet.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_choose(int profile,U8 *out,U32 *length){
 old_profile=profile;Packet *pak;int slot_number=3,createLocation=0;U32 local_map_ip=0x0100007f;strcpy(db_info.players[3].name,"Native Fixture");
'''+choose+'''
 *length=packet.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_fields(const int *widths,const U32 *values,U32 count,int aligned,U8 *out,U32 *length){
 memset(storage,0,sizeof(storage));BitStream stream;initBitStream(&stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 for(U32 i=0;i<count;i++){if(widths[i]==-99){U8 b=(U8)values[i];bsWriteBitsArray(&stream,8,&b);}else if(widths[i]<0)bsWriteBitsPack(&stream,-widths[i],values[i]);else bsWriteBits(&stream,widths[i],values[i]);}
 *length=stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
'''
 path=tmp/'oracle.c';path.write_text(code);libfile=tmp/'oracle.so'
 run(['cc','-std=c99','-O0','-fwrapv','-fPIC','-shared','-w','-I'+str(repo/'native-android/include'),path,'-lz','-o',libfile])
 lib=C.CDLL(str(libfile))
 lib.original_login.argtypes=lib.original_choose.argtypes=[C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
 lib.original_fields.argtypes=[C.c_void_p,C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
 return lib,pins
def fixtures(lib,tmp):
 def u(n,v):return [(n,v)]
 def p(v):return [(-1,v)]
 def s(v):return [(8,c) for c in v.encode()+b'\0']
 def f(v):return u(32,struct.unpack('<I',struct.pack('<f',v))[0])
 def auto(v):
  widths=[2,10,24,32];b=next(i for i,n in enumerate(widths) if v<(1<<n));return u(2,b)+u(widths[b],v)
 def array(v):return [(-99,c) for c in v]
 def produce(fields,mode):
  widths=(C.c_int*len(fields))(*(x[0] for x in fields));values=(C.c_uint32*len(fields))(*(x[1] for x in fields))
  out=(C.c_uint8*65536)();n=C.c_uint32();lib.original_fields(widths,values,len(fields),mode,out,C.byref(n));return bytes(out[:(n.value+7)//8]),n.value
 content=[];count=0
 def emit(label,data,bits):
  nonlocal count
  content.append('static const unsigned char '+label+'[]={'+','.join(str(c) for c in data)+'};\n#define '+label+'_bits '+str(bits)+'u\n');count+=1
 def players(mode,legacy=False,badscale=False,badlock=False,overslots=False,count=5):
  fields=p(2+(5 if legacy else 0))+auto(12345)+s('remote command must not execute')+u(1,1)+u(1,0)+u(1,1)+p(8)+p(65 if overslots else count)+p(2)+p(1)+p(0)
  if overslots:return produce(fields,mode)
  for i in range(count):
   fields+=p(9+i)+s(['Native Fixture','EMPTY','Visitor:OtherShard','Invalid Character','Locked Character'][i] if i<5 else 'Additional Fixture '+str(i))+s('' if i==3 else 'Class_Blaster')+s('Magic')+p(8)+p(0)+p(1)+auto(3)+p(0)+s('Primary.Power')+s('Secondary.Power')+p(0)+(u(32,0x7fc00000) if badscale else f(.25))+f(-.5)+u(32,0x11223344)+s('maps/City_Zones/City_01_01/City_01_01.txt')+p(12)+u(32,7)+u(32,123456789)+u(2,3 if badlock else (2 if i==4 else 0))
  fields+=array(bytes(i^0x31 for i in range(128)))+array(bytes(i^0x78 for i in range(128)))
  return produce(fields,mode)
 for mode in [0,1]:
  for legacy in [False,True]:
   suffix=('_old' if legacy else '')+str(mode)
   for kind in ['login','choose']:
    out=(C.c_uint8*65536)();n=C.c_uint32();getattr(lib,'original_'+kind)(mode+(2 if legacy else 0),out,C.byref(n));emit(kind+suffix,bytes(out[:(n.value+7)//8]),n.value)
   emit('players'+suffix,*players(mode,legacy))
  emit('queue'+str(mode),*produce(p(20)+auto(3)+auto(10),mode))
  emit('large'+str(mode),*players(mode,count=64))
  for legacy in [False,True]:
   suffix=('_old' if legacy else '')+str(mode)
   emit('map'+suffix,*produce(p(4+(5 if legacy else 0))+p(17)+p(1)+p(0x0100007f)+p(0)+p(7002)+p(7003)+p(123456),mode))
   emit('error'+suffix,*produce(p(3+(5 if legacy else 0))+s('disposable server rejection'),mode))
  emit('badmap'+str(mode),*produce(p(4)+p(17)+p(1)+p(0x0100007f)+p(0)+p(7002)+p(7003)+p(1),mode))
 for name,kw in [('overslots',{'overslots':True}),('badscale',{'badscale':True}),('badlock',{'badlock':True})]:emit(name+'0',*players(0,**kw))
 (tmp/'fixtures.h').write_text(''.join(content));return count
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=REPO);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output',type=Path);ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);args=ap.parse_args()
 if args.android_output and not args.ndk:ap.error('--android-output requires --ndk')
 repo=args.source_root.resolve()
 with tempfile.TemporaryDirectory(prefix='coh-dbclient-') as d:
  tmp=Path(d);lib,pins=oracle(repo,tmp);count=fixtures(lib,tmp)
  common=[HERE/'coh_dbclient.c',repo/'native-android/protocol/coh_protocol.c',repo/'native-android/src/coh_blowfish.c',HERE.parent/'auth/coh_auth.c']
  session_sources=[HERE/'coh_db_session.c',*[HERE.parent/'network'/f for f in ['coh_net.c','coh_net_frame.c','coh_net_udp.c','coh_net_zip.c']]]
  flags=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(tmp),'-I'+str(repo/'native-android/include')]
  modes=[('release',['-O2'])]
  if args.sanitize:modes+=[('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  checks={}
  for name,options in modes:
   # Keep accepted scalar/crypto dependencies at O0: GCC13's O2 inlining
   # emits a preexisting maybe-uninitialized warning in unused frame decode.
   # New DB code remains optimized and strict; sanitizer instrumentation covers
   # these unchanged dependencies as well.
   objects=[]
   for source in common[1:]:
    obj=tmp/(name+'-'+source.stem+'.o');run(['cc',*flags,*options,'-O0','-c',source,'-o',obj]);objects.append(obj)
   binary=tmp/name;run(['cc',*flags,*options,common[0],*objects,HERE/'tests/test_dbclient.c','-lz','-lm','-o',binary])
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
   checks[name]=json.loads(run([binary],env=env))
   session_binary=tmp/(name+'-session');run(['cc',*flags,*options,common[0],*objects,*session_sources,HERE/'tests/test_db_session.c','-lz','-lm','-o',session_binary])
   checks[name]['session']=json.loads(run([session_binary],env=env))
  result={'schema':1,'passed':True,'scope':'pinned original login/choose producer blocks and bit writer; synthetic full source-layout player lists and actual OS UDP session peer; no real authenticated server or capture',
   'source_files':len(pins),'source_producer_profiles':4,'fixtures':count,'checks':checks,'android_arm64_built':False,'emulator_qualified':False,'physical_thor_accepted':False,'actual_server_interoperability_verified':False,
   'leak_sanitizer_enabled':False,'leak_sanitizer_limitation':'Disabled for executor /proc task-walk compatibility; ASan address checks and explicit socket descriptor before/after cleanup checks remain enabled.'}
  if args.ndk:
   target=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang'
   run([target,'-std=c99','-Wall','-Wextra','-Werror','-fPIC','-shared','-I'+str(repo/'native-android/include'),*common,*session_sources,'-lz','-lm','-Wl,--no-undefined','-o',tmp/'libcoh_dbclient.so'])
   result['android_arm64_built']=True;result['android_library_sha256']=hashlib.sha256((tmp/'libcoh_dbclient.so').read_bytes()).hexdigest()
   result['ndk_revision']=(args.ndk/'source.properties').read_text().split('Pkg.Revision = ')[1].splitlines()[0]
   if args.android_output:
    args.android_output.mkdir(parents=True,exist_ok=True);artifacts=[]
    fixture=(tmp/'fixtures.h').read_bytes();(args.android_output/'fixtures.h').write_bytes(fixture)
    result['android_fixture_sha256']=hashlib.sha256(fixture).hexdigest()
    for abi,triple in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
     target=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/triple
     for label,sources,test in [('wire',common,HERE/'tests/test_dbclient.c'),('session',common+session_sources,HERE/'tests/test_db_session.c')]:
      output=args.android_output/('coh-db-'+label+'-'+abi)
      # Accepted Blowfish uses C11 _Static_assert; Clang correctly rejects
      # that extension with C99 -pedantic. Compile the executable as C11.
      run([target,*flags,'-std=c11','-O2',*sources,test,'-lz','-lm','-o',output])
      artifacts.append({'abi':abi,'kind':label,'file':output.name,'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'built':True,'executed':False})
    receipt={'schema':1,'module':'dbclient','artifacts':artifacts,'fixture_sha256':result['android_fixture_sha256'],'android_execution_qualified':False,'actual_server_interoperability_verified':False}
    (args.android_output/'android-build.json').write_text(json.dumps(receipt,indent=2)+'\n');result['android_artifacts']=artifacts
  serialized=json.dumps(result,indent=2,sort_keys=True)+'\n'
  if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(serialized)
  print(serialized,end='')
if __name__=='__main__':main()
