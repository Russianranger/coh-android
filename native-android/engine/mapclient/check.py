#!/usr/bin/env python3
"""Source producer oracle and bounded actual-UDP controller tests.

All scripted peer packets are synthetic source-layout fixtures, never a server
capture/login. Legacy source is compiled unchanged at O0 on padded input only.
Sanitizers cover the new controller and accepted portable dependencies.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, shutil, subprocess, tempfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FILES=[
 'Common/comm_game.h', 'Common/entity/entVarUpdate.h',
 'Game/src/clientcomm/clientcomm.c', 'Game/src/clientcomm/dbclient.c',
 'MapServer/src/svr/svr_tick.c',
 'libs/UtilitiesLib/src/components/BitStream.c',
 'libs/UtilitiesLib/src/network/net_packet.c',
 'libs/UtilitiesLib/src/network/net_packetutil.c',
 'libs/UtilitiesLib/src/network/netio_send.c',
 'libs/UtilitiesLib/src/network/net_version.c',
 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
]

def run(cmd,**kwargs):
 p=subprocess.run([str(v) for v in cmd],text=True,capture_output=True,**kwargs)
 if p.returncode:raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
 return p.stdout

def oracle(repo,directory):
 spec=importlib.util.spec_from_file_location('accepted_bit_reference',repo/'native-android/tools/protocol_fixture/prepare.py')
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 sources={f:(repo/'upstream/ouroboros'/f).read_text().replace('\r\n','\n') for f in FILES}
 pins={f:hashlib.sha256(s.encode()).hexdigest() for f,s in sources.items()}
 if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('Mapclient source pin mismatch')
 pre=helper.PREAMBLE.replace('int compressionAllowed,orderedAllowed;',
     'int compressionAllowed,orderedAllowed,controlCommandsSeparate,cookieSend,cookieEcho;U32 cookie_send,cookie_recv,last_cookie_recv;')
 pre=pre.replace('static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}','')
 pre+='\n#define COMM_MAX_CMD 2\n#define COMM_OLDMAX_CMD 7\n#define devassert(x) assert(x)\n'
 code=pre
 for name in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsWriteBitsArray','bsAlignByte','bsGetCursorBitPosition']:
  code+=helper.extract(sources['libs/UtilitiesLib/src/components/BitStream.c'],name)
 for name in ['pktSendBits','pktSendBitsPack','pktSendBitsArray']:
  code+=helper.extract(sources['libs/UtilitiesLib/src/network/net_packet.c'],name)
 code+='int auto_bins[]={2,10,24,32};\n'+helper.extract(sources['libs/UtilitiesLib/src/network/net_packetutil.c'],'pktSendBitsAuto')
 code+=helper.extract(sources['libs/UtilitiesLib/src/network/netio_send.c'],'pktSendCmd')
 # Field ordering is pinned to commStart/commReqScene and svr_tick's complete
 # existing-character branch. sendCharacterCreate implementation is absent;
 # only its source server-consumed newCharacter=0 form is reconstructed.
 code+='''
void original_map(unsigned cmd,unsigned legacy,unsigned aligned,U32 cookie,U32 cod,U32 console,U32 initial,const U8 *md5,U8 *out,U32 *bits) {
 U32 storage[256]={0};Packet p={0};NetLink link={0};link.controlCommandsSeparate=!legacy;
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);pktSendCmd(&link,&p,cmd);
 if(cmd==9){pktSendBitsPack(&p,1,cookie);pktSendBits(&p,1,cod);pktSendBits(&p,1,0);}
 else if(cmd==3){pktSendBits(&p,1,0);}
 else if(cmd==6){pktSendBitsPack(&p,1,cookie);pktSendBitsPack(&p,1,console);pktSendBitsArray(&p,128,md5);pktSendBitsAuto(&p,initial);}
 *bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
'''
 path=directory/'source-oracle.c';path.write_text(code);library=directory/'source-oracle.so'
 run(['cc','-std=c99','-O0','-fPIC','-shared','-w','-I'+str(repo/'native-android/include'),path,'-o',library])
 lib=C.CDLL(str(library));lib.original_map.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_uint32,C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.POINTER(C.c_uint32)]
 return lib,pins

def fixtures(lib,directory):
 md5=bytes(range(16));lines=['typedef struct {unsigned cmd,legacy,aligned;uint32_t cookie,cod,console,initial,bits;unsigned char bytes[128];} MapGolden;','static const MapGolden goldens[]={']
 count=0
 for cmd in [9,4,3,5,6]:
  for legacy in [0,1]:
   for aligned in [0,1]:
    for cookie in [2,3,16,1024,0x7fffffff,0xffffffff]:
     for flag in [0,1]:
      out=(C.c_uint8*128)();bits=C.c_uint32()
      lib.original_map(cmd,legacy,aligned,cookie,flag,flag,flag,md5,out,C.byref(bits))
      lines.append('{%du,%du,%du,%du,%du,%du,%du,%du,{%s}},'%(cmd,legacy,aligned,cookie,flag,flag,flag,bits.value,','.join(str(v) for v in out[:(bits.value+7)//8])))
      count+=1
 lines+=['};'];(directory/'fixtures.h').write_text('\n'.join(lines)+'\n');return count

def command_fixtures(repo,directory):
 spec=importlib.util.spec_from_file_location('qualified_replication_commands',repo/'native-android/engine/replication/check.py')
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 target=directory/'replication';target.mkdir()
 lib,_=helper.oracle(repo,target);helper.fixtures(lib,target,repo)
 lines=(target/'fixtures.h').read_text().splitlines()
 (directory/'server-command-fixtures.h').write_text('\n'.join(line for line in lines if line.startswith(('#define SOURCE_ACCESSIBLE','static const unsigned char source_commands','#define source_commands')))+'\n')
 return 915

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,default=REPO);parser.add_argument('--sanitize',action='store_true');parser.add_argument('--output',type=Path);parser.add_argument('--ndk',type=Path)
 parser.add_argument('--android-output',type=Path,help='With --ndk, preserve fixtures and full ARM64/x86_64 test executables; builds only, never executes them')
 args=parser.parse_args()
 if args.android_output and not args.ndk:parser.error('--android-output requires --ndk')
 repo=args.source_root.resolve();native=repo/'native-android'
 with tempfile.TemporaryDirectory(prefix='coh-mapclient-') as tmp:
  directory=Path(tmp);lib,pins=oracle(repo,directory);count=fixtures(lib,directory);catalog_count=command_fixtures(repo,directory)
  sources=[HERE/'coh_mapclient.c',HERE/'tests/test_mapclient.c',native/'engine/replication/coh_replication.c',native/'engine/network/coh_net.c',native/'engine/network/coh_net_frame.c',native/'engine/network/coh_net_zip.c',native/'engine/network/coh_net_udp.c',native/'protocol/coh_protocol.c',native/'src/coh_blowfish.c']
  modes=[('release',['-O1'])]
  if args.sanitize:modes += [('asan',['-g','-O1','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-g','-O1','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  checks={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for name,flags in modes:
   binary=directory/name
   # Keep accepted protocol.c unchanged. GCC can diagnose its source decoder
   # local as maybe-uninitialized after inlining at higher optimization levels.
   # Only that accepted dependency uses O0; new controller/test code stays O1.
   objects=[]
   for index,source in enumerate(sources):
    obj=directory/(name+'-'+str(index)+'.o');objects.append(obj)
    dependency_flags=['-O0'] if source==native/'protocol/coh_protocol.c' else []
    run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,*dependency_flags,'-I'+str(directory),'-I'+str(HERE),'-I'+str(native/'include'),'-c',source,'-o',obj])
   run(['cc',*flags,*objects,'-lz','-lm','-o',binary])
   checks[name]=json.loads(run([binary],env=env))
  proof={'schema':1,'passed':True,'scope':'source producer parity plus actual OS UDP with scripted synthetic peer; no real server/authentication/capture','source_files':len(pins),'source_golden_packets':count,'source_accessible_command_upper_count':catalog_count,'checks':checks,'leak_sanitizer_enabled':False,'leak_sanitizer_note':'ASan addresses checked; descriptor lifetime checked through /proc/self/fd. LeakSanitizer process inspection is unavailable in this execution environment.','android_arm64_object_built':False,'emulator_qualified':False,'thor_accepted':False,'actual_server_interoperability':False,'full_scene_parser':False,'full_entity_parser':False,'render_spawn_handoff':False,'login_verified':False}
  if args.ndk:
   compiler=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang'
   run([compiler,'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-fPIC','-I'+str(native/'include'),'-c',HERE/'coh_mapclient.c','-o',directory/'mapclient-arm64.o'])
   proof['android_arm64_object_built']=True;proof['android_arm64_object_sha256']=hashlib.sha256((directory/'mapclient-arm64.o').read_bytes()).hexdigest()
   if args.android_output:
    destination=args.android_output.resolve();destination.mkdir(parents=True,exist_ok=True)
    shutil.copy2(directory/'fixtures.h',destination/'fixtures.h')
    shutil.copy2(directory/'server-command-fixtures.h',destination/'server-command-fixtures.h')
    shutil.copy2(directory/'source-oracle.c',destination/'source-oracle.c')
    ndk_revision=(args.ndk/'source.properties').read_text().split('Pkg.Revision = ')[1].splitlines()[0]
    manifest={'schema':1,'passed':True,'executed':False,'scope':'cross-built complete scripted-peer mapclient tests only; no execution, server session, login or live-world claim','ndk_revision':ndk_revision,'fixtures_sha256':hashlib.sha256((destination/'fixtures.h').read_bytes()).hexdigest(),'source_oracle_sha256':hashlib.sha256((destination/'source-oracle.c').read_bytes()).hexdigest(),'source_files_sha256':{str(source.relative_to(native)):hashlib.sha256(source.read_bytes()).hexdigest() for source in sources},'executables':{}}
    for abi,target,label in [('arm64-v8a','aarch64','arm64'),('x86_64','x86_64','x86_64')]:
     compiler=args.ndk/('toolchains/llvm/prebuilt/linux-x86_64/bin/'+target+'-linux-android26-clang')
     abi_directory=destination/abi;abi_directory.mkdir(parents=True,exist_ok=True)
     binary=abi_directory/'test_mapclient_android'
     # The accepted Blowfish dependency has C11 static assertions. Its source
     # is unchanged; the full Android driver uses the required C11 standard.
     run([compiler,'-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-fPIE','-pie','-I'+str(destination),'-I'+str(HERE),'-I'+str(native/'include'),*sources,'-lz','-lm','-o',binary])
     receipt={'schema':1,'abi':abi,'passed':True,'binary':binary.name,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'bytes':binary.stat().st_size,'api':26,'ndk_revision':ndk_revision,'android_executed':False,'source_fixtures_sha256':manifest['fixtures_sha256'],'scope':manifest['scope']}
     (abi_directory/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
     manifest['executables'][abi]={'file':str(binary.relative_to(destination)),'sha256':receipt['binary_sha256'],'bytes':receipt['bytes'],'api':26,'executed':False,'receipt':str((abi_directory/'receipt.json').relative_to(destination))}
    (destination/'android-build.json').write_text(json.dumps(manifest,indent=2)+'\n')
    proof['android_executables']=manifest['executables'];proof['android_executables_built']=True
    proof['android_fixtures_sha256']=manifest['fixtures_sha256']
  text=json.dumps(proof,indent=2)+'\n'
  if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
  print(text,end='')
if __name__=='__main__':main()
