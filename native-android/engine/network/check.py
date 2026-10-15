#!/usr/bin/env python3
"""Gate25 source producer + independent wire/codec reference + native checks.

The original x86 bit writer runs unchanged on trusted aligned inputs, -O0,
without sanitizers. Only the new native module is sanitizer qualified.
No socket opens, actual server or Android execution are implied by this test.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, random
import struct, subprocess, tempfile, zlib

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FILES={
 'BitStream.c':'upstream/ouroboros/libs/UtilitiesLib/src/components/BitStream.c',
 'net_packet.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/net_packet.c',
 'net_packetutil.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/net_packetutil.c',
 'netio_core.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/netio_core.c',
 'netio_send.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/netio_send.c',
 'netio_receive.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/netio_receive.c',
 'net_link.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/net_link.c',
 'net_version.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/net_version.c',
 'crypt.cpp':'upstream/ouroboros/libs/UtilitiesLib/src/network/crypt.cpp',
 'authclient.c':'upstream/ouroboros/Game/src/clientcomm/authclient.c',
 'dbclient.c':'upstream/ouroboros/Game/src/clientcomm/dbclient.c',
 'clientcomm.c':'upstream/ouroboros/Game/src/clientcomm/clientcomm.c',
}
def sha(data):return hashlib.sha256(data).hexdigest()
def load_helper():
 spec=importlib.util.spec_from_file_location('accepted_reference',ROOT/'tools/protocol_fixture/prepare.py')
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(cmd,**kw):
 result=subprocess.run(cmd,text=True,capture_output=True,**kw)
 if result.returncode:
  raise RuntimeError('Command failed: '+repr(cmd)+'\n'+result.stdout+result.stderr)
 return result
def reference(source_root,directory):
 helper=load_helper();sources={k:(source_root/v).read_bytes().replace(b'\r\n',b'\n').decode() for k,v in FILES.items()}
 pins={k:{'path':FILES[k],'sha256_lf':sha(v.encode())} for k,v in sources.items()}
 expected=json.loads((HERE/'source-pins.json').read_text())
 if pins!=expected['files']:raise ValueError('Original source SHA256 differs')
 names={
  'BitStream.c':helper.FUNCTIONS['BitStream.c']+['bsGetLengthWriteBits','bsGetLengthWriteBitsPack','bsCompress'],
  'net_packet.c':helper.FUNCTIONS['net_packet.c'],
  'net_packetutil.c':['pktSendBitsAuto'],
  'netio_core.c':['pktSendAcks','pktWrap','blowfishPad'],
  'netio_send.c':['calcTimeout'],
 }
 pre=helper.PREAMBLE
 pre=pre.replace('static int pktGetLengthBitsPack(Packet *p,int n,U32 v){(void)p;(void)n;(void)v;assert(0);return 0;}',
  'int bsGetLengthWriteBitsPack(BitStream*,int,U32);static int pktGetLengthBitsPack(Packet *p,int n,U32 v){return bsGetLengthWriteBitsPack(&p->stream,n,v);}')
 pre=pre.replace('static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}',
  'void pktSendBitsAuto(Packet*,U32);int auto_bins[]={2,10,24,32};')
 pre+='''
#include <zlib.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define timerCpuSpeed() 1000
#define SMALLEST_DATA_TO_COMPRESS 12
#define PERFINFO_AUTO_START(a,b)
#define PERFINFO_AUTO_STOP()
#define FatalErrorf(...) abort()
static int g_bAssertOnBitStreamError=0;
static const char *debugBytesToString(const void *p,unsigned long n,int c){(void)p;(void)n;(void)c;return "";}
'''
 snippets='\n'.join(helper.extract(sources[file],name) for file,functions in names.items() for name in functions)
 wrapper=r'''
void reference_wrap(U32 version,U32 id,U32 sibcount,U32 part,U32 sibid,U32 compressed,U32 ordered,U32 orderid,U32 connect,const U32 *acks,U32 count,const U8 *payload,U32 bits,U8 *out,U32 *length){
 U32 input[4096]={0},output[4096]={0};Packet in={0};NetLink link={0};BitStream stream;
 initBitStream(&in.stream,(U8*)input,sizeof(input),Read,0,0);memcpy(input,payload,(bits+7)/8);in.stream.bitLength=bits;in.stream.size=(bits+7)/8;
 in.truncatedID=id;in.sib_count=sibcount;in.sib_partnum=part;in.sib_id=sibid;in.compress=compressed;in.ordered=ordered;in.ordered_id=orderid;
 link.compressionAllowed=version>0;link.orderedAllowed=version>=5;link.ack_count=count;memcpy(link.ids_toack,acks,count*4);
 initBitStream(&stream,(U8*)output,sizeof(output),Write,0,0);assert(pktWrap(&in,&link,&stream));
 (void)connect;*length=blowfishPad((stream.bitLength+7)/8);memcpy(out,output,*length);
}
void reference_zip(U32 streaming,const U8 *data,U32 bytes,U8 *out,U32 *length){
 static z_stream persistent={0};static int ready=0;U32 memory[8192]={0};BitStream stream;
 if(!ready){assert(deflateInit(&persistent,Z_DEFAULT_COMPRESSION)==Z_OK);ready=1;}
 initBitStream(&stream,(U8*)memory,sizeof(memory),Write,1,0);memcpy(memory,data,bytes);stream.bitLength=bytes*8;stream.size=bytes;
 bsCompress(&stream,0,streaming?&persistent:NULL);assert(!stream.errorFlags);*length=stream.bitLength/8;memcpy(out,memory,*length);
}
'''
 source=directory/'original.c';source.write_text(pre+snippets+wrapper)
 run(['cc','-std=c99','-O0','-fPIC','-shared','-w','-I'+str(ROOT/'include'),str(source),'-lz','-o',str(directory/'original.so')])
 lib=C.CDLL(str(directory/'original.so'))
 lib.reference_wrap.argtypes=[C.c_uint32]*9+[C.POINTER(C.c_uint32),C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)]
 lib.calcTimeout.argtypes=[C.c_int,C.c_int,C.c_int];lib.calcTimeout.restype=C.c_uint
 lib.reference_zip.argtypes=[C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)]
 rng=random.Random(250143);cases=[];compared=0
 for index in range(80):
  ver=[0,1,2,4,5][index%5];sib=2+index%5 if index%4==0 else 0
  connect=index%19==0
  if connect:sib=0
  compressed=int(bool(ver and not connect and index%3==0));ordered=int(ver>=5 and not connect and index%2==0)
  orderid=[1,1024,0x123456,0x12345678][index%4] if ordered else 0
  ack=sorted(set([1,3,4][:index%4]));part=index%sib if sib else 0
  bits=[8,32,64,255,512,9600,9824,11488][index%8]
  if compressed:bits=(bits+7)&~7
  # Original producer peeks a command when there are no siblings. Force a
  # complete source packed command (0 or initial CONNECT) in the first byte.
  data=bytearray(rng.randrange(256) for _ in range((bits+7)//8));data[0]=1 if connect else data[0]&0xfe
  if connect:data[0]=1;bits=max(bits,8)
  b=helper.Bits();b.write(32,0);b.write(32,0);b.write(1,0);ident=index+1;b.write(32,ident);b.pack(1,sib)
  if sib:b.pack(1,part);b.write(32,index+1000)
  b.pack(1,len(ack))
  if ack:
   b.write(32,ack[0])
   for a,c in zip(ack,ack[1:]):b.pack(1,c-a-1)
  if ver and not connect:b.write(1,compressed)
  if ver>=5 and not connect:
   b.write(1,ordered)
   if ordered:
    bin_index=next(i for i,n in enumerate([2,10,24,32]) if orderid<1<<n)
    b.write(2,bin_index);b.write([2,10,24,32][bin_index],orderid)
  raw=bytearray(b.bytes()+data);total=len(b.bytes())*8+bits
  raw[:4]=struct.pack('<I',total);raw.extend(bytes((4+((len(raw)-4+7)//8)*8)-len(raw)))
  out=C.create_string_buffer(1472);length=C.c_uint32();acks=(C.c_uint32*max(1,len(ack)))(*ack)
  lib.reference_wrap(ver,ident,sib,part,index+1000 if sib else 0,compressed,ordered,orderid,connect,acks,len(ack),bytes(data),bits,out,C.byref(length))
  if out.raw[:length.value]!=raw:raise ValueError('Unchanged original producer differs at '+str(index))
  compared+=len(raw);raw[4:8]=struct.pack('>I',zlib.adler32(raw[8:])&0xffffffff)
  cases.append(dict(version=ver,id=ident,siblings=sib,part=part,sibling_id=index+1000 if sib else 0,compressed=compressed,ordered=ordered,ordered_id=orderid,connect=int(connect),acks=ack,bits=bits,payload=data.hex(),wire=raw.hex()))
 lines=['/* Generated independently from original pktWrap + Python bits/zlib. */']
 for i,c in enumerate(cases):
  for k in ['payload','wire']:lines.append('static const uint8_t g%d_%s[]={%s};'%(i,k,','.join(str(v) for v in bytes.fromhex(c[k]))))
 lines.append('static const Golden goldens[]={')
 for i,c in enumerate(cases):
  lines.append('{%du,{.id=%du,.sibling_id=%du,.sibling_count=%du,.sibling_part=%du,.ordered_id=%du,.ack_count=%du,.acks={%s},.payload_bits=%du,.compressed=%d,.ordered=%d,.connect=%d},g%d_payload,g%d_wire,sizeof(g%d_wire)},'%(
   c['version'],c['id'],c['sibling_id'],c['siblings'],c['part'],c['ordered_id'],len(c['acks']),','.join(str(v) for v in c['acks'])or'0',c['bits'],c['compressed'],c['ordered'],c['connect'],i,i,i))
 lines.append('};')
 (directory/'goldens.h').write_text('\n'.join(lines)+'\n')
 retries=[]
 for retry in range(5):
  for ping in [0,1,65,100,250,1000,5000]:
   for older in [0,1]:retries.append((retry,ping,older,lib.calcTimeout(retry,ping,older)))
 (directory/'retry_goldens.h').write_text('static const uint32_t retry_goldens[][4]={\n'+''.join('{%du,%du,%du,%du},\n'%v for v in retries)+'};\n')
 zip_lines=[];zip_cases=[];compressor=zlib.compressobj()
 for index in range(40):
  streaming=index%3!=0;tail=([0,11,12,25,1000,5000][index%6])
  data=struct.pack('<I',10)+bytes((j*17+index)%256 for j in range(tail))
  if tail<12:expected_wire=data
  else:expected_wire=data[:4]+struct.pack('<I',tail)+(compressor.compress(data[4:])+compressor.flush(zlib.Z_SYNC_FLUSH) if streaming else zlib.compress(data[4:]))
  out=C.create_string_buffer(32768);size=C.c_uint32();lib.reference_zip(streaming,data,len(data),out,C.byref(size))
  if out.raw[:size.value]!=expected_wire:raise ValueError('Original bsCompress differs at '+str(index))
  zip_lines+=['static const uint8_t zip%d_input[]={%s};'%(index,','.join(str(v) for v in data)),
   'static const uint8_t zip%d_wire[]={%s};'%(index,','.join(str(v) for v in expected_wire))]
  zip_cases.append((index,int(streaming)))
 zip_lines.append('static const ZipGolden zip_goldens[]={')
 for i,stream in zip_cases:zip_lines.append('{%d,zip%d_input,sizeof(zip%d_input),zip%d_wire,sizeof(zip%d_wire)},'%(stream,i,i,i,i))
 zip_lines.append('};');(directory/'zip_goldens.h').write_text('\n'.join(zip_lines)+'\n')
 return {'original_producer_cases':len(cases),'plaintext_bytes_compared':compared,'timeout_source_cases':len(retries),'original_compression_cases':len(zip_cases),'source_file_count':len(pins),'source_revision':expected['source_revision'],'fixture_sha256':sha(json.dumps(cases,sort_keys=True).encode()),'oracle':'unchanged original pktWrap/ACK/bit/auto/bsCompress/calcTimeout bodies; trusted aligned O0 host, never shipped'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');p.add_argument('--cc',default='cc');a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-gate25-') as tmp:
  d=Path(tmp);proof=reference(a.source_root,d)
  sources=[HERE/'coh_net.c',HERE/'coh_net_frame.c',HERE/'coh_net_zip.c',ROOT/'protocol/coh_protocol.c',ROOT/'src/coh_blowfish.c',HERE/'tests/test_net.c']
  flags=['-std=c99','-Wall','-Wextra','-Werror','-O1','-g','-I'+str(ROOT/'include'),'-I'+str(ROOT/'protocol'),'-I'+str(HERE),'-I'+str(d)]
  if a.sanitize:flags+=['-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-pie','-no-pie']
  binary=d/'net-test';build=run([a.cc,*flags,*map(str,sources),'-lz','-o',str(binary)])
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  result=run([str(binary)],env=env);native=json.loads(result.stdout)
  qualified=[*sources,HERE/'coh_net.h',HERE/'check.py',ROOT/'engine/coh_contracts.h']
  proof.update(schema='coh-native-gate25-host-v1',passed=True,native=native,native_sources_sha256={str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in qualified},sanitizers='ASan+UBSan; leak sanitizer disabled on restricted host' if a.sanitize else 'not requested',android_build=False,android_execution=False,live_server_interoperability=False)
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n')
  print(json.dumps(proof))
if __name__=='__main__':main()
