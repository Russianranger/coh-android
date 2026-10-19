#!/usr/bin/env python3
"""Focused original ordered-fragment compatibility; no server/Android/gate claim."""
from pathlib import Path
import argparse, ctypes as C, gzip, hashlib, importlib.util, io, json, os, subprocess, tarfile, tempfile
HERE=Path(__file__).resolve().parent; NATIVE=HERE.parents[1]; ROOT=NATIVE.parent

def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(cmd,**kw):
 p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,**kw)
 if p.returncode: raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
 return p.stdout

def oracle(directory):
 h=load('fragment_original_helper',NATIVE/'tools/protocol_fixture/prepare.py')
 old=load('fragment_existing_check',HERE/'check.py'); expected=json.loads((HERE/'source-pins.json').read_text())['files']
 originals={key:(ROOT/path).read_bytes().replace(b'\r\n',b'\n').decode() for key,path in old.FILES.items()}
 for key,raw in originals.items():
  if sha(raw.encode())!=expected[key]['sha256_lf']:raise ValueError('ORIGINAL_SOURCE_'+key)
 pre=h.PREAMBLE.replace('typedef struct {BitStream stream;U32 checksum,truncatedID,sib_count,sib_partnum,sib_id,hasDebugInfo,compress,ordered,ordered_id;} Packet;',r'''
typedef float F32;
typedef struct {BitStream stream;U32 checksum,truncatedID,sib_count,sib_partnum,sib_id,hasDebugInfo,compress,ordered,ordered_id,id,UID,xferTime,inSendQueue,reliable;} Packet;
typedef struct {Packet *items[16];unsigned count;} TestQueue;
''').replace('typedef struct {int ack_count;U32 ids_toack[32];int compressionAllowed,orderedAllowed;} NetLink;',r'''
typedef struct {int ack_count;U32 ids_toack[32];int compressionAllowed,orderedAllowed;unsigned socket,type,nextID,nextSibID,sendQueuePacketMax,sendQueuePacketCount,last_ordered_sent_id,reliablePacketsQueued,overflow,totalQueuedBytes;float runningCompressionRatio;void *zstream_pack;TestQueue *sendQueue2;struct {unsigned sin_port;struct {struct {unsigned S_addr;}S_un;}sin_addr;}addr;} NetLink;
''').replace('static int pktGetLengthBitsPack(Packet *p,int n,U32 v){(void)p;(void)n;(void)v;assert(0);return 0;}',
 'int bsGetLengthWriteBitsPack(BitStream*,int,U32);static int pktGetLengthBitsPack(Packet*p,int n,U32 v){return bsGetLengthWriteBitsPack(&p->stream,n,v);}')
 pre=pre.replace('static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}',
 'void pktSendBitsAuto(Packet*,U32);int auto_bins[]={2,10,24,32};')
 pre+=r'''
#include <zlib.h>
#define MEM_DBG_PARMS
#define LOG(...)
#define verify(x) (x)
#define NLT_NONE 0
#define NLT_UDP 1
#define NLT_TCP 2
#define netioEnterCritical() ((void)0)
#define netioLeaveCritical() ((void)0)
#define timerCpuTicks() 1
#define lnkAddSendTime(...) ((void)0)
#define lnkFlushAddLink(...) ((void)0)
static int g_assert_on_netlink_overflow=0,total_sendqueue_overflows=0;
static int sendPacketBufferSize=1236;
static const char *makeIpStr(unsigned a){(void)a;return "synthetic";}
static int qEnqueue(TestQueue *q,Packet*p){assert(q->count<16);q->items[q->count++]=p;return 1;}
void initBitStream(BitStream*,U8*,unsigned int,BitStreamMode,unsigned int,MemoryAllocator);
static Packet *pktCreate(void){Packet*p=calloc(1,sizeof(*p));assert(p);U8*b=calloc(16384,1);assert(b);initBitStream(&p->stream,b,16384,Write,0,0);return p;}
static void pktFree(Packet*p){free(p->stream.data);free(p);}
static void bsCompress(BitStream*s,int dbg,void*z){(void)s;(void)dbg;(void)z;assert(0);}
'''
 # Exact unchanged original function bodies. Allocation, OS, queue and timing
 # dependencies above are explicit test providers, never original services.
 names={
 'BitStream.c':h.FUNCTIONS['BitStream.c']+['bsGetLengthWriteBits','bsGetLengthWriteBitsPack','bsGetLength'],
 'net_packet.c':h.FUNCTIONS['net_packet.c']+['pktMakeCompatible','pktGetSize'],
 'net_packetutil.c':['pktSendBitsAuto'],
 'netio_core.c':['pktSendAcks','pktWrap','blowfishPad','lnkAddToSendQueue'],
 'netio_send.c':['pktSendDbg']}
 snippets='\n'.join(h.extract(originals[file],name) for file,functions in names.items() for name in functions)
 wrapper=r'''
void original_produce(U32 bytes,U32 ordered,U8*frames,U32*sizes,U32*metadata,U32*count,U32*result){
 TestQueue queue={0};NetLink link={0};link.socket=1;link.type=NLT_UDP;link.nextID=101;link.compressionAllowed=1;link.orderedAllowed=1;link.sendQueue2=&queue;
 Packet *in=pktCreate();in->reliable=1;in->ordered=ordered;
 U32 data[4096]={0};for(U32 i=0;i<bytes;i++)((U8*)data)[i]=(U8)(i*17);((U8*)data)[0]=0x57;
 bsWriteBitsArray(&in->stream,bytes*8,data);*result=pktSendDbg(&in,&link);assert(!in);*count=queue.count;
 for(U32 i=0;i<queue.count;i++){
  Packet *p=queue.items[i];U32 output[512]={0};BitStream stream;initBitStream(&stream,(U8*)output,sizeof(output),Write,0,0);assert(pktWrap(p,&link,&stream));
  sizes[i]=blowfishPad((stream.bitLength+7)/8);assert(sizes[i]<=1472);memcpy(frames+i*1472,output,sizes[i]);
  metadata[i*5]=p->id;metadata[i*5+1]=p->sib_count;metadata[i*5+2]=p->sib_partnum;metadata[i*5+3]=p->sib_id;metadata[i*5+4]=p->ordered_id;pktFree(p);
 }
}
'''
 path=directory/'original-fragments.c';path.write_text(pre+snippets+wrapper)
 libpath=directory/'original-fragments.so';run(['cc','-std=c99','-O0','-shared','-fPIC','-w','-I'+str(NATIVE/'include'),path,'-lz','-o',libpath])
 lib=C.CDLL(str(libpath));lib.original_produce.argtypes=[C.c_uint32,C.c_uint32,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p]
 cases=[]
 for size in (1199,1200,1201,2400,2401,8192):
  for ordered in (0,1):
   frames=C.create_string_buffer(16*1472);sizes=(C.c_uint32*16)();metadata=(C.c_uint32*80)();count=C.c_uint32();result=C.c_uint32()
   lib.original_produce(size,ordered,frames,sizes,metadata,C.byref(count),C.byref(result))
   import struct,zlib
   parts=[]
   for i in range(count.value):
    raw=bytearray(frames.raw[i*1472:i*1472+sizes[i]]);raw[4:8]=struct.pack('>I',zlib.adler32(raw[8:])&0xffffffff)
    parts.append({'metadata':list(metadata[i*5:i*5+5]),'wire':bytes(raw)})
   assert count.value==(size+1199)//1200
   assert result.value==(1 if size<1200 else 0)
   if size==1200:assert parts[0]['metadata'][1]==1
   if ordered:assert [p['metadata'][4] for p in parts]==[1]+[0]*(count.value-1)
   cases.append({'bytes':size,'ordered':ordered,'count':count.value,'return':result.value,'parts':parts})
 lines=['/* Exact original pktSendDbg + lnkAddToSendQueue + pktWrap; explicit host providers. */']
 for i,case in enumerate(cases):
  for j,p in enumerate(case['parts']):lines.append('static const uint8_t fragment_%d_%d[]={%s};'%(i,j,','.join(str(v)for v in p['wire'])))
 lines.append('static const OriginalFragmentCase fragment_cases[]={')
 for i,case in enumerate(cases):
  lines.append('{%du,%du,%du,{%s},{%s}},'%(case['bytes'],case['ordered'],case['count'],','.join('fragment_%d_%d'%(i,j) for j in range(case['count'])),','.join('sizeof(fragment_%d_%d)'%(i,j)for j in range(case['count']))))
 lines.append('};');(directory/'fragment_goldens.h').write_text('\n'.join(lines)+'\n')
 return {'original_function_sha256_lf':{name:sha(h.extract(originals[file],name).encode())for file,functions in names.items()for name in functions},'original_source_sha256_lf':{old.FILES[file]:sha(raw.encode())for file,raw in originals.items()},'original_send_cases':len(cases),'original_function_bytes_unchanged':True,'original_uncompressed_send_queue_and_wrap_executed':True,'original_compression_executed':False,'explicit_original_dependencies':['zeroed packet/bit-buffer allocator','bounded host queue','owned dummy UDP link','no-op OS locking/timing/flush','zlib Adler32 wire checksum'],'fixture_sha256':sha((directory/'fragment_goldens.h').read_bytes())}

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 unit=HERE/'tests/test_fragment_compat.c';base=[HERE/'coh_net.c',HERE/'coh_net_frame.c',HERE/'coh_net_zip.c',NATIVE/'protocol/coh_protocol.c',NATIVE/'src/coh_blowfish.c',unit]
 mirror=load('fragment_tx_preservation',NATIVE/'engine/initial-capture/check_request_tx.py').preservation()
 inputs=[*base,HERE/'coh_net.h',HERE/'coh_net_zip_internal.h',NATIVE/'engine/initial-capture/coh_request_tx_net.c',NATIVE/'engine/initial-capture/check_request_tx.py',Path(__file__),NATIVE/'tools/protocol_fixture/prepare.py',HERE/'source-pins.json',HERE/'check.py',NATIVE/'include/coh_native_core.h',NATIVE/'engine/coh_contracts.h',NATIVE/'protocol/coh_protocol.h']
 pins={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in inputs};modes={};executed={}
 with tempfile.TemporaryDirectory(prefix='coh-fragment-focused-')as t:
  d=Path(t);proof=oracle(d)
  for mode,san in [('release',[]),('asan',['-fsanitize=address']),('ubsan',['-fsanitize=undefined'])]:
   objects=[]
   for i,path in enumerate(base):
    obj=d/(mode+'-'+str(i)+'.o');flags=['-std=c99','-O0'if path.name in ('coh_protocol.c','coh_blowfish.c')else'-O2','-g','-Wall','-Wextra','-Werror','-fno-omit-frame-pointer','-fno-pie','-I'+str(HERE),'-I'+str(NATIVE/'protocol'),'-I'+str(NATIVE/'include'),'-I'+str(d),*san]
    run(['cc',*flags,'-c',path,'-o',obj]);objects.append(obj)
   binary=d/(mode+'-fragment-test');run(['cc','-no-pie',*san,*objects,'-lz','-o',binary]);executed[mode]=binary.read_bytes()
   env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1');modes[mode]=json.loads(run([binary],env=env))
  if pins!={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in inputs}:raise ValueError('INPUT_CHANGED')
  archive=io.BytesIO()
  with tarfile.open(fileobj=archive,mode='w')as out:
   for name,raw in {**{mode+'/test-fragment':data for mode,data in executed.items()},'original-fragments.c':(d/'original-fragments.c').read_bytes(),'original-fragments.so':(d/'original-fragments.so').read_bytes(),'fragment_goldens.h':(d/'fragment_goldens.h').read_bytes()}.items():
    entry=tarfile.TarInfo(name);entry.size=len(raw);entry.mode=0o700 if name.endswith('.so')or'/test-'in name else 0o600;entry.mtime=0;out.addfile(entry,io.BytesIO(raw))
  raw=gzip.compress(archive.getvalue(),mtime=0);(a.output/'executed-proof.tar.gz').write_bytes(raw)
 proof.update(schema='coh-original-fragment-focused-v1',passed=True,source_sha256=pins,modes=modes,request_tx_preservation=mirror,executed_proof={'bytes':len(raw),'sha256':sha(raw)},unchanged_limits={'fragments':16,'wire_reassembly':16384,'decoded':4194304},original_server_transaction_executed=False,android_compiled=False,android_executed=False,whole_process_memory_measured=False,transport_ack_is_application_ack=False,world_authority=False,gates25_27_open=True)
 (a.output/'qualification.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n');print(json.dumps({'passed':True,'modes':modes,'original_send_cases':proof['original_send_cases']}))
if __name__=='__main__':main()
