#!/usr/bin/env python3
"""Pinned original packet producer plus independent zlib/OpenSSL goldens.

The original x86-oriented bit writer runs only on trusted, aligned host data
without sanitizers. Native parsing is separately checked under ASan/UBSan.
"""
from pathlib import Path
import argparse, ctypes as C, ctypes.util, hashlib, json, re, struct, subprocess, tempfile, zlib
ROOT=Path(__file__).resolve().parents[2]
REV='61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d'
CRYPTO='b5242667a24e3db8e4600e77b2e502ef204e5280'
PATHS={
 'BitStream.c':'upstream/ouroboros/libs/UtilitiesLib/src/components/BitStream.c',
 'BitStream.h':'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/BitStream.h',
 'netio_core.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/netio_core.c',
 'netio_send.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/netio_send.c',
 'net_packet.c':'upstream/ouroboros/libs/UtilitiesLib/src/network/net_packet.c',
 'net_packet.h':'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/network/net_packet.h',
 'net_structdefs.h':'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
 'crypt.cpp':'upstream/ouroboros/libs/UtilitiesLib/src/network/crypt.cpp',
 'CryptoPP.cmake':'upstream/ouroboros/cmake/dependencies/CryptoPP.cmake',
 'adler32.cpp':'external:weidai11/cryptopp/adler32.cpp@'+CRYPTO,
}
FUNCTIONS={'BitStream.c':['initBitStream','bsSetByteAlignment','bsWriteBits','bsReadBits','bsWriteBitsArray','bsWriteBitsPack','bsReadBitsPack','bsRewind','bsAlignByte','bsGetCursorBitPosition','bsGetBitLength','bsSetCursorBitPosition','bsSetEndOfStreamPosition'],
 'net_packet.c':['pktSetByteAlignment','pktSendBits','pktSendBitsPack','pktGetBitsPack','pktSendBitsArray'],
 'netio_core.c':['pktSendAcks','pktWrap','blowfishPad'], 'crypt.cpp':['cryptAdler32'],
 'adler32.cpp':['Adler32::Update','Adler32::TruncatedFinal']}
def sha(b): return hashlib.sha256(b).hexdigest()
def extract(text,name):
 m=re.search(r'^(?:static\s+)?(?:unsigned\s+int|void|int|U32)\s+'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
 if not m: raise ValueError('Source function missing: '+name)
 begin=text.index('{',m.start()); depth=1; at=begin+1
 while depth:
  depth += (text[at]=='{')-(text[at]=='}'); at+=1
 return text[m.start():at]+'\n'
class BF(C.Structure): _fields_=[('P',C.c_uint32*18),('S',C.c_uint32*1024)]
def oracle_cipher(key,plain):
 lib=C.CDLL(ctypes.util.find_library('crypto'))
 lib.BF_set_key.argtypes=[C.POINTER(BF),C.c_int,C.c_void_p]; lib.BF_encrypt.argtypes=[C.POINTER(C.c_uint32),C.POINTER(BF)]
 context=BF(); lib.BF_set_key(C.byref(context),len(key),key); out=bytearray()
 for at in range(0,len(plain),8):
  pair=(C.c_uint32*2)(*struct.unpack('<II',plain[at:at+8])); lib.BF_encrypt(pair,C.byref(context)); out.extend(struct.pack('<II',*pair))
 return bytes(out)
class Bits:
 def __init__(self): self.bits=[]
 def write(self,n,v): self.bits.extend((v>>i)&1 for i in range(n))
 def pack(self,n,v):
  while n<32 and v>=(1<<n)-1:
   self.write(n,(1<<n)-1); v-=(1<<n)-1; n=min(n*2,32)
  self.write(n,v)
 def bytes(self):
  out=bytearray((len(self.bits)+7)//8)
  for at,b in enumerate(self.bits): out[at//8] |= b<<(at%8)
  return bytes(out)
def independent_frame(key,encrypted,ident,payload,bit_length,debug=0,siblings=0,acks=0,overflow_ack=False):
 b=Bits(); b.write(1,debug); b.write(32,ident); b.pack(1,siblings)
 if siblings: b.pack(1,0); b.write(32,0x11223344)
 if overflow_ack:
  for width in [1,2,4,8,16,32]:b.write(width,(1<<width)-1)
 else:b.pack(1,acks)
 if acks:b.write(32,0x22334455)
 body=b.bytes()+payload; total=64+len(b.bytes())*8+bit_length
 out=bytearray(struct.pack('<I',total)+bytes(4)+body); out.extend(bytes((4+((len(out)-4+7)//8)*8)-len(out)))
 out[4:8]=struct.pack('>I',zlib.adler32(out[8:])&0xffffffff)
 if encrypted: out[4:]=oracle_cipher(key,bytes(out[4:]))
 return bytes(out)
PREAMBLE=r'''
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "coh_native_core.h"
typedef uint32_t U32;typedef uint8_t U8;
typedef enum {Read,Write} BitStreamMode;
typedef enum {BSE_NOERROR,BSE_OVERFLOW,BSE_OVERRUN,BSE_TYPEMISMATCH,BSE_COMPRESSION} BitStreamError;
typedef struct {unsigned int byte,bit;} BitStreamCursor;
typedef struct BitStream BitStream;typedef int (*MemoryAllocator)(BitStream*);
struct BitStream {BitStreamMode mode;BitStreamCursor cursor;unsigned char *data;unsigned int size,maxSize,bitLength;MemoryAllocator memAllocator;void *userData;unsigned int byteAlignedMode;BitStreamError errorFlags;};
typedef struct {BitStream stream;U32 checksum,truncatedID,sib_count,sib_partnum,sib_id,hasDebugInfo,compress,ordered,ordered_id;} Packet;
typedef struct {int ack_count;U32 ids_toack[32];int compressionAllowed,orderedAllowed;} NetLink;
#define false 0
#define true 1
#define BSASSERT(x) assert(x)
#define MAX(a,b) ((a)>(b)?(a):(b))
#define ROUND_BITS_UP(x) (((x)+7)&~7)
#define PACKET_MISCINFO_SIZE_WITH_DEBUG 200
#define PACKET_MISCINFO_SIZE_WITHOUT_DEBUG 36
#define COMM_CONNECT 1
#define MAX_PKTACKS 32
static unsigned int g_packetsizes_one[33],g_packetsizes_success[33],g_packetsizes_failed[33];
static int count_bits(unsigned int val){int n=0;do{val>>=1;n++;}while(val);return n;}
void bsAlignByte(BitStream*);unsigned int bsGetCursorBitPosition(BitStream*);unsigned int bsGetBitLength(BitStream*);
void bsWriteBits(BitStream*,int,unsigned int);void bsWriteBitsPack(BitStream*,int,unsigned int);unsigned int bsReadBitsPack(BitStream*,int);
static int printPacketSendData=0,printPacketGetData=0;
static void bsTypedWriteBits(BitStream *b,int n,U32 v){(void)b;(void)n;(void)v;assert(0);}
static void bsTypedWriteBitsPack(BitStream *b,int n,U32 v){(void)b;(void)n;(void)v;assert(0);}
static U32 bsTypedReadBitsPack(BitStream *b,int n){(void)b;(void)n;assert(0);return 0;}
static void bsTypedWriteBitsArray(BitStream *b,int n,const void *v){(void)b;(void)n;(void)v;assert(0);}
static int pktGetLengthBitsPack(Packet *p,int n,U32 v){(void)p;(void)n;(void)v;assert(0);return 0;}
static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}
static int cmpU32(const void *a,const void *b){return *(const U32*)a>*(const U32*)b;}
extern U32 cryptAdler32(U8*,int);
'''
CPP_PREAMBLE=r'''
#include <stdint.h>
#include <assert.h>
#include <stddef.h>
typedef uint8_t byte;typedef uint16_t word16;typedef uint8_t U8;typedef uint32_t U32;
#define CRYPTOPP_ASSERT assert
#define endianSwapIfBig(type,x) (x)
class Adler32 {word16 m_s1=1,m_s2=0;public:void Update(const byte*,size_t);void TruncatedFinal(byte*,size_t);void ThrowIfInvalidTruncatedSize(size_t size){assert(size<=4);}void Reset(){m_s1=1;m_s2=0;}void Final(byte *out){TruncatedFinal(out,4);}};
static Adler32 adler_instance;static Adler32 *adler32=&adler_instance;
'''
def original_library(sources,pins,directory):
 for filename,names in FUNCTIONS.items():
  for name in names:
   if sha(extract(sources[filename],name).encode())!=pins['functions'][name]['sha256_lf']: raise ValueError('Function pin differs: '+name)
 snippets='\n'.join(extract(sources[file],name) for file in ['BitStream.c','net_packet.c','netio_core.c'] for name in FUNCTIONS[file])
 wrapper=r'''
void original_wrap(U32 id,const U8 *payload,U32 bits,U8 *out,U32 *length){
 U32 in_memory[512]={0},out_memory[512]={0};Packet in={0};NetLink link={0};BitStream stream;
 initBitStream(&in.stream,(U8*)in_memory,sizeof(in_memory),Read,0,0);memcpy(in_memory,payload,(bits+7)/8);in.stream.bitLength=bits;in.stream.size=(bits+7)/8;in.truncatedID=id;
 initBitStream(&stream,(U8*)out_memory,sizeof(out_memory),Write,0,0);assert(pktWrap(&in,&link,&stream));
 *length=blowfishPad((stream.bitLength+7)/8);
 U32 checksum=cryptAdler32((U8*)out_memory+8,*length-8);memcpy((U8*)out_memory+4,&checksum,4);memcpy(out,out_memory,*length);
}
void original_bits(unsigned width,U32 value,U8 *out,U32 *bits){U32 memory[512]={0};BitStream stream;initBitStream(&stream,(U8*)memory,sizeof(memory),Write,0,0);bsWriteBitsPack(&stream,width,value);*bits=stream.bitLength;memcpy(out,memory,(*bits+7)/8);}
'''
 cpp=CPP_PREAMBLE+'\n'+extract(sources['adler32.cpp'],'Adler32::Update')+extract(sources['adler32.cpp'],'Adler32::TruncatedFinal')+'\nextern "C" {\n'+extract(sources['crypt.cpp'],'cryptAdler32')+'}\n'
 cfile=directory/'original.c';cppfile=directory/'adler.cpp';cfile.write_text(PREAMBLE+snippets+wrapper);cppfile.write_text(cpp)
 subprocess.run(['cc','-std=c11','-O0','-fPIC','-w','-I'+str(ROOT/'include'),'-c',str(cfile),'-o',str(directory/'original.o')],check=True)
 subprocess.run(['c++','-std=c++11','-O0','-fPIC','-c',str(cppfile),'-o',str(directory/'adler.o')],check=True)
 path=directory/'original.so';subprocess.run(['c++','-shared',str(directory/'original.o'),str(directory/'adler.o'),'-o',str(path)],check=True)
 lib=C.CDLL(str(path));lib.original_wrap.argtypes=[C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)];lib.original_bits.argtypes=[C.c_uint,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)];return lib
def cbytes(b): return '{'+','.join('0x%02x'%v for v in b)+'}'
def prepare(source_dir,initialize=False):
 sources={}
 for filename,relative in PATHS.items():
  if source_dir: path=source_dir/filename
  elif relative.startswith('external:'): raise ValueError('Explicit source-dir needed for exact pinned external CryptoPP source')
  else: path=ROOT.parent/relative
  sources[filename]=path.read_bytes().replace(b'\r\n',b'\n').decode()
 pins={'repository':'Russianranger/coh-android','source_revision':REV,'crypto_repository':'weidai11/cryptopp','crypto_revision':CRYPTO,'sources':{file:{'path':relative,'sha256_lf':sha(sources[file].encode())} for file,relative in PATHS.items()},'functions':{name:{'file':file,'sha256_lf':sha(extract(sources[file],name).encode())} for file,names in FUNCTIONS.items() for name in names}}
 pinpath=Path(__file__).with_name('source-pins.json')
 if initialize: pinpath.write_text(json.dumps(pins,indent=2)+'\n')
 else:
  if json.loads(pinpath.read_text())!=pins: raise ValueError('Original source pins differ')
 if CRYPTO not in sources['CryptoPP.cmake']: raise ValueError('CryptoPP dependency differs')
 key=bytes(range(16)); cases=[]; bit_cases=[]; copied_bytes=0
 with tempfile.TemporaryDirectory(prefix='coh-protocol-original-') as d:
  original=original_library(sources,pins,Path(d))
  for index,bits in enumerate([1,2,7,8,9,31,32,33,63,64,65,255,256,511,512,9600]):
   payload=bytes((((at*73+index*19)|1)&255)&(254 if at==0 else 255) for at in range((bits+7)//8));ident=[0,1,0x7fffffff,0x80000000,0xffffffff][index%5]
   plain=independent_frame(key,False,ident,payload,bits); out=C.create_string_buffer(1472);length=C.c_uint32()
   original.original_wrap(ident,payload,bits,out,C.byref(length));actual=out.raw[:length.value]
   if actual!=plain: raise ValueError('Original packet producer differs at bits '+str(bits))
   copied_bytes+=len(plain)
   for encrypted in [False,True]: cases.append({'id':ident,'payload_bits':bits,'payload_hex':payload.hex(),'encrypted':encrypted,'wire_hex':independent_frame(key,encrypted,ident,payload,bits).hex()})
  for n in [1,2,3,4,5,8,16,31,32]:
   for v in sorted(set([0,1,(1<<n)-2,(1<<n)-1,min((1<<n),0xffffffff),0x7fffffff,0x80000000,0xffffffff])):
    b=Bits();b.pack(n,v);out=C.create_string_buffer(64);count=C.c_uint32();original.original_bits(n,v,out,C.byref(count));original_bytes=out.raw[:(count.value+7)//8]
    if count.value!=len(b.bits) or original_bytes!=b.bytes(): raise ValueError('Original packed bits differ: '+str((n,v)))
    bit_cases.append({'width':n,'value':v,'bit_count':len(b.bits),'hex':b.bytes().hex()})
 negatives=[]
 for name,settings in [('debug',{'debug':1}),('siblings',{'siblings':1}),('acks',{'acks':1}),('packed_ack_overflow',{'overflow_ack':True})]:
  for encrypted in [False,True]:negatives.append({'name':name,'encrypted':encrypted,'wire_hex':independent_frame(key,encrypted,0,b'\x00',1,**settings).hex()})
 lines=['/* Generated by tools/protocol_fixture/prepare.py; zlib/OpenSSL independent goldens. */','#ifndef COH_PROTOCOL_GOLDENS_H','#define COH_PROTOCOL_GOLDENS_H','static const uint8_t protocol_key[16]='+cbytes(key)+';']
 for index,c in enumerate(cases):
  lines += ['static const uint8_t protocol_payload_%d[]='%index+cbytes(bytes.fromhex(c['payload_hex']))+';','static const uint8_t protocol_wire_%d[]='%index+cbytes(bytes.fromhex(c['wire_hex']))+';']
 lines+=['typedef struct {uint32_t id,bits;int encrypted;const uint8_t *payload,*wire;size_t wire_bytes;} ProtocolGolden;','static const ProtocolGolden protocol_goldens[]={']
 for index,c in enumerate(cases):lines.append('{%du,%du,%d,protocol_payload_%d,protocol_wire_%d,sizeof(protocol_wire_%d)},'%(c['id'],c['payload_bits'],c['encrypted'],index,index,index))
 lines+=['};','typedef struct {unsigned width;uint32_t value,bits;uint8_t bytes[16];} ProtocolBitGolden;','static const ProtocolBitGolden protocol_bit_goldens[]={']
 for c in bit_cases:lines.append('{%du,%du,%du,%s},'%(c['width'],c['value'],c['bit_count'],cbytes(bytes.fromhex(c['hex']))))
 lines+=['};']
 for index,c in enumerate(negatives):lines.append('static const uint8_t protocol_negative_%d[]='%index+cbytes(bytes.fromhex(c['wire_hex']))+';')
 lines+=['typedef struct {int encrypted;const uint8_t *wire;size_t wire_bytes;} ProtocolNegative;','static const ProtocolNegative protocol_negatives[]={']
 for index,c in enumerate(negatives):lines.append('{%d,protocol_negative_%d,sizeof(protocol_negative_%d)},'%(c['encrypted'],index,index))
 lines+=['};','#endif','']
 header='\n'.join(lines).encode()
 receipt={'schema':'coh-native-protocol-reference-v1','passed':True,'scope':'host original producer functions plus independent zlib/OpenSSL algorithm reference; no Android or live handshake','source_functions':len(pins['functions']),'plain_source_cases':16,'source_frame_bytes_compared':copied_bytes,'wire_cases':len(cases),'bit_cases':len(bit_cases),'authenticated_negative_cases':len(negatives),'key_hex':key.hex(),'source_profile':{'debug':False,'siblings':False,'acks':False,'compression_allowed':False,'ordered_allowed':False,'zero_padding_producer_policy':True},'original_harness':'unchanged source bodies including packet/ACK dispatch; unsupported typed/debug/length-auto helpers trap if reached; aligned zero-initialized trusted buffers, O0 without sanitizers; unsafe original writer is not shipped','header_sha256':sha(header),'cases':cases,'bits':bit_cases,'negatives':negatives}
 return header,(json.dumps(receipt,indent=2)+'\n').encode()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-dir',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 header,receipt=prepare(args.source_dir,args.initialize_pins);target=ROOT/'protocol/protocol_goldens.h'
 if args.check:
  if target.read_bytes()!=header:raise ValueError('Compiled protocol goldens differ')
 else:target.write_bytes(header)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(receipt)
 print(json.dumps({'passed':True,'wire_cases':32,'header_sha256':sha(header),'receipt':str(args.output)}))
if __name__=='__main__':main()
