#!/usr/bin/env python3
"""Source bit-writer/position-consumer oracle and bounded native tests.

Fixtures are deterministic synthetic source-layout inputs, never captures.
The unchanged original x86 bit code runs only on trusted padded/aligned input,
at -O0. Sanitizers cover the new module and test harness, not legacy code.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, struct, subprocess, tempfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FILES=[
 'Common/comm_game.h', 'Common/entity/entity_enum.h',
 'Common/entity/entVarUpdate.h', 'Common/cmdparse/cmdcommon.c',
 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
 'libs/UtilitiesLib/include/utilitieslib/network/netcomp.h',
 'libs/UtilitiesLib/src/components/BitStream.c',
 'libs/UtilitiesLib/src/network/netcomp.c',
 'libs/UtilitiesLib/src/network/net_packetutil.c',
 'libs/UtilitiesLib/src/utils/cmdoldparse.c',
 'Game/src/clientcomm/clientcomm.c', 'Game/src/clientcomm/clientcommreceive.c',
 'Game/src/entity/entrecv.c', 'Game/src/player/player.c',
 'Game/src/group/groupnetrecv.c', 'MapServer/src/group/groupnetsend.c',
 'MapServer/src/svr/svr_tick.c', 'MapServer/src/entity/entsend.c',
]
def run(cmd,**kw):
 p=subprocess.run(cmd,text=True,capture_output=True,**kw)
 if p.returncode:raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
 return p
def oracle(repo,directory):
 spec=importlib.util.spec_from_file_location('accepted_bit_reference',repo/'native-android/tools/protocol_fixture/prepare.py')
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 sources={f:(repo/'upstream/ouroboros'/f).read_text().replace('\r\n','\n') for f in FILES}
 pins={f:hashlib.sha256(v.encode()).hexdigest() for f,v in sources.items()}
 expected=json.loads((HERE/'source-pins.json').read_text())
 if pins!=expected['sha256_lf']:raise ValueError('Replication source pin mismatch')
 pre=helper.PREAMBLE.replace('hasDebugInfo,compress,ordered,ordered_id;', 'hasDebugInfo,compress,ordered,ordered_id,id;')
 names=['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsAlignByte','bsGetCursorBitPosition']
 bits=sources['libs/UtilitiesLib/src/components/BitStream.c']
 code=pre+'\n'.join(helper.extract(bits,n) for n in names)
 code+='''
#define POS_BITS 24
#define POS_SCALE 64.0f
#define START_BIT_COUNT(...)
#define STOP_BIT_COUNT(...)
#define PERFINFO_AUTO_START(...)
#define PERFINFO_AUTO_STOP(...)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define copyVec3(a,b) memcpy((b),(a),sizeof(*(a))*3)
typedef struct { U32 pkt_id_pos[24]; int net_ipos[3]; float net_pos[3]; } Entity;
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
'''
 code+=helper.extract(sources['Game/src/entity/entrecv.c'],'entGetPosition')
 code+='''
void original_fields(const int *widths,const U32 *values,U32 count,int aligned,U8 *out,U32 *length) {
 U32 storage[8192]={0};BitStream stream;initBitStream(&stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 for(U32 i=0;i<count;i++){if(widths[i]<0)bsWriteBitsPack(&stream,-widths[i],values[i]);else bsWriteBits(&stream,widths[i],values[i]);}
 *length=stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_position(const U8 *data,U32 length,int aligned,U32 id,U32 *packed,U32 *ids,float *position) {
 U32 storage[8192]={0};Packet p={0};Entity e={0};int sub=0,ooo=0;
 memcpy(e.net_ipos,packed,12);memcpy(e.pkt_id_pos,ids,96);
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(length+7)/8);p.stream.bitLength=length;p.id=id;
 entGetPosition(&p,&e,0,&sub,&ooo);memcpy(packed,e.net_ipos,12);memcpy(ids,e.pkt_id_pos,96);memcpy(position,e.net_pos,12);
}
'''
 cfile=directory/'source-oracle.c';cfile.write_text(code)
 libfile=directory/'source-oracle.so'
 run(['cc','-std=c99','-O0','-fPIC','-shared','-w','-I'+str(repo/'native-android/include'),str(cfile),'-o',str(libfile)])
 lib=C.CDLL(str(libfile));lib.original_fields.argtypes=[C.c_void_p,C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
 lib.original_position.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p]
 return lib,pins
def fixtures(lib,directory):
 def u(n,v):return [(n,v)]
 def p(v):return [(-1,v)]
 def f(v):return u(32,struct.unpack('<I',struct.pack('<f',v))[0])
 def s(v):return [(8,v) for v in v.encode()+b'\0']
 def auto(v):
  widths=[2,10,24,32];b=next(i for i,n in enumerate(widths) if v<(1<<n));return u(2,b)+u(widths[b],v)
 def produce(fields,aligned):
  widths=(C.c_int*len(fields))(*(x[0] for x in fields));values=(C.c_uint32*len(fields))(*(x[1] for x in fields))
  output=(C.c_uint8*32768)();length=C.c_uint32();lib.original_fields(widths,values,len(fields),aligned,output,C.byref(length))
  return bytes(output[:(length.value+7)//8]),length.value
 content=[];count=0
 def emit(name,fields,mode):
  nonlocal count
  data,bits=produce(fields,mode);label=name+str(mode)
  content.append('static const unsigned char '+label+'[]={'+','.join(str(x) for x in data)+'};\n#define '+label+'_bits '+str(bits)+'u\n')
  count+=1;return data,bits
 for mode in [0,1]:
  emit('connect',p(5)+p(1)+f(-6.0),mode)
  emit('connect_nan',p(5)+p(1)+u(32,0x7fc00000),mode)
  emit('reject',p(5)+p(0)+s('Disposable test rejection'),mode)
  emit('legacy_connect',p(10)+p(1)+f(-6.0),mode)
  emit('shortcuts',p(4)+p(1)+s('time')+p(2)+s('timescale')+p(3)+s('pause')+p(4)+s('svr_fog_color')+p(5)+s('not_source_supported')+p(0xffffffff)+p(2)+s('help')+s('quit'),mode)
  emit('duplicate_shortcuts',p(4)+p(1)+s('time')+p(1)+s('timescale')+p(0xffffffff)+p(0),mode)
  emit('long_shortcut',p(4)+p(1)+s('x'*256)+p(0xffffffff)+p(0),mode)
  emit('scene',p(6)+p(0)+p(0)+u(1,1)+u(2,0)+p(7)+p(0)+p(1)+auto(4)+[(-3,0)]+u(1,1)+auto(1)+s('loading/synthetic_page')+s('loading/synthetic')+s('maps/City_Zones/City_01_01/City_01_01.txt')+u(1,1)+p(0),mode)
  emit('update',p(3)+p(17)+u(1,1)+p(1)+f(12.5)+p(2)+f(1)+p(3)+p(0)+p(4)+f(.2)+f(.3)+f(.4)+p(0)+u(32,123456)+u(32,87654321)+u(1,1)+p(0)+u(1,1)+u(1,1),mode)
  emit('unknown',p(3)+p(17)+u(1,1)+p(5),mode)
  emit('update_debug',p(2)+u(1,0)+p(0)+u(32,1)+u(32,2)+u(1,0)+u(1,1)+u(1,1)+u(2,3)+u(2,2),mode)
  emit('scene_same',p(6)+p(1)+p(2)+u(1,0)+u(1,1),mode)
  emit('physics',u(1,1)+u(16,4321)+f(12.5)+f(-6.25)+f(128)+u(1,0)+u(1,1)+f(2.5)+u(1,0)+u(1,0),mode)
  emit('physics_recording',u(1,0)+u(1,0)+u(1,1),mode)
  emit('physics_id_only',u(1,0)+u(1,1)+u(16,65535)+u(1,0),mode)
  emit('physics_empty',u(1,0)+u(1,0)+u(1,0),mode)
  emit('pos_full',u(3,7)+u(24,(1<<23)+800)+u(24,(1<<23)-400)+u(24,(1<<23)+8192),mode)
  emit('pos_partial',u(3,3)+u(8,128)+u(8,64)+u(8,192),mode)
  emit('pos_older',u(3,7)+u(24,(1<<23)+2000)+u(24,(1<<23)-2000)+u(24,(1<<23)+4096),mode)
  # Compile fixture expectations from the unchanged original client consumer.
  packed=(C.c_uint32*3)(*[1<<23]*3);ids=(C.c_uint32*24)();position=(C.c_float*3)()
  for name,ident,fields in [('pos_full',10,u(3,7)+u(24,(1<<23)+800)+u(24,(1<<23)-400)+u(24,(1<<23)+8192)),('pos_partial',12,u(3,3)+u(8,128)+u(8,64)+u(8,192)),('pos_older',11,u(3,7)+u(24,(1<<23)+2000)+u(24,(1<<23)-2000)+u(24,(1<<23)+4096))]:
   data,bits=produce(fields,mode);lib.original_position(data,bits,mode,ident,packed,ids,position)
   label=name+str(mode)+'_expected'
   content.append('static const unsigned int '+label+'[]={'+','.join(str(v) for v in packed)+'};\n')
 (directory/'fixtures.h').write_text(''.join(content))
 return count
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=REPO);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--output',type=Path);args=ap.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-replication-') as d:
  directory=Path(d);lib,pins=oracle(args.source_root.resolve(),directory);n=fixtures(lib,directory)
  modes=[('release',['-O2'])]
  if args.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  checks={}
  for name,flags in modes:
   binary=directory/name;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(directory),'-I'+str(HERE),str(HERE/'coh_replication.c'),str(HERE/'test_replication.c'),'-lm','-o',str(binary)])
   # This sandbox denies LeakSanitizer's /proc task walk. The module allocates
   # no heap memory; AddressSanitizer still checks all memory accesses.
   env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
   checks[name]=json.loads(run([str(binary)],env=env).stdout)
  proof={'schema':1,'passed':True,'scope':'synthetic source-layout fixtures and original position consumer; no real server/capture/device','source_files':len(pins),'fixtures':n,'checks':checks,'actual_server_interoperability':False,'full_entity_parser':False,'render_spawn_handoff':False,'android_built':False,'emulator_qualified':False,'thor_accepted':False}
  if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
  print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
