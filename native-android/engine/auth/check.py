#!/usr/bin/env python3
"""Pinned original-source auth wire oracle + independent Python crypto oracle.

ASan/UBSan cover new native module only; original x86 functions run separately
under -O0 -fwrapv, preserving original unsigned-machine arithmetic assumptions.
No actual authenticated session, server endpoint, or Android provider implied.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, json, os, random, re, struct, subprocess, tempfile, zlib

HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[1]
FILES=[
 'upstream/ouroboros/Common/auth/auth.c',
 'upstream/ouroboros/Common/auth/auth.h',
 'upstream/ouroboros/Common/auth/authconn.h',
 'upstream/ouroboros/Game/src/clientcomm/authclient.c',
 'upstream/ouroboros/Game/src/clientcomm/dbclient.c',
 'upstream/ouroboros/libs/UtilitiesLib/src/network/crypt.cpp',
 'upstream/ouroboros/libs/UtilitiesLib/src/network/net_link.c',
 'upstream/ouroboros/libs/UtilitiesLib/src/network/blowfish.c',
 'upstream/ouroboros/AuthServer/src/SocketServerEx.cpp',
 'upstream/ouroboros/AuthServer/src/util.cpp',
 'upstream/ouroboros/AuthServer/src/IOBuffer.cpp',
]
def run(cmd,**kw):
 p=subprocess.run([str(v) for v in cmd],text=True,capture_output=True,**kw)
 if p.returncode:raise RuntimeError('Command failed: '+repr(cmd)+'\n'+p.stdout+p.stderr)
 return p.stdout
def source(root,path):
 p=root/path
 data=p.read_bytes() if p.exists() else subprocess.check_output(['git','show','HEAD:'+path],cwd=root)
 return data.replace(b'\r\n',b'\n').decode()
def extract(src,name):
 # This helper covers the original definitions audited here, not arbitrary C.
 m=re.search(r'(?m)^[^\n;{}]*\b'+re.escape(name)+r'\([^;{}]*\)\s*\{',src)
 if not m:raise ValueError('Original definition missing: '+name)
 start=m.start();at=src.index('{',m.start());depth=1;i=at+1
 while depth:
  if src[i]=='{':depth+=1
  if src[i]=='}':depth-=1
  i+=1
 return src[start:i]
class Bytes(C.Structure):_fields_=[('data',C.c_void_p),('size',C.c_size_t)]
def span(b):return Bytes(C.cast(b,C.c_void_p),len(b))
def oracle(root,tmp,sources):
 cc=os.environ.get('CC','cc');inc=['-I'+str(NATIVE/'include')]
 shared=tmp/'native.so'
 common=[HERE/'coh_auth.c',HERE/'coh_auth_openssl.c',NATIVE/'src/coh_blowfish.c',NATIVE/'protocol/coh_protocol.c']
 run([cc,'-std=c99','-O2','-fPIC','-shared',*inc,*common,HERE/'tests/oracle_shim.c','-lcrypto','-o',shared])
 lib=C.CDLL(str(shared))
 lib.auth_test_plain.argtypes=[C.c_char_p,C.c_char_p,C.c_uint32,C.c_void_p]
 lib.auth_test_shared.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p]
 lib.coh_auth_global_encode.argtypes=[Bytes,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
 lib.coh_auth_global_decode.argtypes=[Bytes,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
 lib.coh_bf_init.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t]
 lib.coh_bf_crypt.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_int]
 auth=sources[FILES[0]]
 pre='''#include <stdint.h>\n#include <string.h>\n#include "coh_native_core.h"\n#define BLOWFISH_CTX CohBlowfish\n#define cryptBlowfishEncrypt(ctx,b,n) coh_bf_crypt(ctx,b,n,0)\nstatic struct {CohBlowfish blowfish_ctx;} auth_state;\n'''
 pre+=extract(auth,'authEncryptLineage2')+'\n'+extract(auth,'BlowfishEncryptPacket')
 pre+='''\nvoid original_frame(unsigned char *buf,int *len){static const uint8_t k[]={0xa4,0xde,0x6b,0x64,0xff,0x24,0xad,0x74,0x52,0xa0,0x6a,0x35,0xaf,0xf5,0x37,0x11,0xd3,0x5a,0xc8,0x42};coh_bf_init(&auth_state.blowfish_ctx,k,sizeof(k));BlowfishEncryptPacket(buf,len);}\n'''
 original=tmp/'original.c';original.write_text(pre)
 run([cc,'-std=c99','-O0','-fwrapv','-fPIC','-shared',*inc,original,NATIVE/'src/coh_blowfish.c','-o',tmp/'original.so'])
 ref=C.CDLL(str(tmp/'original.so'));ref.authEncryptLineage2.argtypes=[C.c_char_p,C.c_void_p,C.c_uint];ref.original_frame.argtypes=[C.c_void_p,C.POINTER(C.c_int)]
 rng=random.Random(260015);login_cases=0;dh_cases=0;frame_cases=0
 for index in range(80):
  account=(b' FIXTURE ' if index%2 else b'fixture');password=bytes(rng.randrange(33,127) for _ in range(index%17));key=[0,1234,0x7fffffff,0x80000000,0xffffffff][index%5]
  original_password=C.create_string_buffer(32);ref.authEncryptLineage2(password,original_password,16)
  normalized=account.strip().lower();session=str(key if key<2**31 else key-2**32).encode()
  md5=hashlib.md5(original_password.raw[:16]+session).digest()
  # CryptoPP Adler32::Final emits BE; cryptAdler32 U32 load is LE on Win32.
  salt=f'{int.from_bytes(struct.pack(">I",zlib.adler32(normalized)),"little"):08x}'.encode()
  sha=hashlib.sha512(password+salt).digest();swapped=b''.join(sha[n:n+8][::-1] for n in range(0,64,8))
  expected=normalized.ljust(14,b'\0')+md5+swapped
  output=C.create_string_buffer(94);assert lib.auth_test_plain(account,password,key,output)==0;assert output.raw==expected;login_cases+=1
 prime=bytes((C.c_ubyte*64).in_dll(lib,'coh_auth_dh_prime'));p=int.from_bytes(prime,'big');q=(p-1)//2
 der=re.search(r'dh_hex_params\[\]\s*=\s*"([0-9A-F]+)"',sources[FILES[5]]).group(1)
 assert bytes.fromhex(der)==b'\x30\x46\x02\x41\0'+prime+b'\x02\x01\x02'
 assert pow(2,q,p)==1
 for index in range(64):
  x=rng.randrange(2,q);y=rng.randrange(2,q);peer=pow(2,y,p);shared=C.create_string_buffer(64)
  a=C.create_string_buffer(x.to_bytes(64,'big'));b=C.create_string_buffer(peer.to_bytes(64,'big'))
  assert lib.auth_test_shared(a,b,shared)==0;assert shared.raw==pow(peer,x,p).to_bytes(64,'big');dh_cases+=1
 for size in list(range(1,65))+[93,94,144,512,985,992]:
  body=bytes(rng.randrange(256) for _ in range(size));native=C.create_string_buffer(1002);n=C.c_size_t()
  data=C.create_string_buffer(body,len(body));assert lib.coh_auth_global_encode(span(data),native,len(native),C.byref(n))==0
  original_buffer=(C.c_uint32*256)();C.memmove(original_buffer,body,len(body));length=C.c_int(size);ref.original_frame(original_buffer,C.byref(length))
  assert native.raw[2:n.value]==bytes(original_buffer)[:length.value]
  # Authentic pooled source buffers can have arbitrary alignment padding and
  # final reserved DWORD; the source checksum covers the padded body.
  dirty=(C.c_uint32*256)(*[rng.getrandbits(32) for _ in range(256)]);C.memmove(dirty,body,len(body));length=C.c_int(size);ref.original_frame(dirty,C.byref(length))
  frame=struct.pack('<H',length.value+2)+bytes(dirty)[:length.value];raw=C.create_string_buffer(frame,len(frame));plain=C.create_string_buffer(1000);m=C.c_size_t()
  assert lib.coh_auth_global_decode(span(raw),plain,len(plain),C.byref(m))==0;assert plain.raw[:size]==body;frame_cases+=2
 return {'credential_derivation_source_oracle_cases':login_cases,'dh_python_pow_oracle_cases':dh_cases,'global_auth_source_frame_cases':frame_cases,'source_dh_der_exact':True}
def main():
 a=argparse.ArgumentParser();a.add_argument('--source-root',type=Path,default=NATIVE.parent);a.add_argument('--sanitize',action='store_true');a.add_argument('--output',type=Path);a.add_argument('--ndk',type=Path);args=a.parse_args()
 sources={p:source(args.source_root,p) for p in FILES};pins={p:hashlib.sha256(s.encode()).hexdigest() for p,s in sources.items()}
 expected=json.loads((HERE/'source-pins.json').read_text());assert pins==expected['sha256_lf'],'Original source hash changed'
 with tempfile.TemporaryDirectory(prefix='coh-auth-') as d:
  tmp=Path(d);result=oracle(args.source_root,tmp,sources);cc=os.environ.get('CC','cc')
  flags=['-std=c99','-Wall','-Wextra','-Werror','-I'+str(NATIVE/'include')]
  if args.sanitize:flags+=['-g','-O1','-fno-omit-frame-pointer','-fsanitize=address,undefined','-fno-pie','-no-pie']
  else:flags+=['-O2']
  cmd=[cc,*flags,'-DCOH_AUTH_TEST_OPENSSL',HERE/'coh_auth.c',HERE/'coh_auth_openssl.c',HERE/'tests/test_auth.c',NATIVE/'src/coh_blowfish.c',NATIVE/'protocol/coh_protocol.c','-lcrypto','-o',tmp/'test_auth']
  run(cmd);env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1');result['native_tests']=json.loads(run([tmp/'test_auth'],env=env))
  result['leak_sanitizer_enabled']=False
  result['leak_sanitizer_limitation']='Execution environment blocks /proc task inspection; ASan address and UBSan remain enabled.' if args.sanitize else 'Not requested'
  result['sanitize']=args.sanitize;result['host_crypto_provider']='OpenSSL3';result['android_crypto_provider_available']=False
  result['actual_server_interoperability_verified']=False;result['physical_thor_accepted']=False;result['emulator_qualified']=False
  if args.ndk:
   target=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang'
   run([target,'-std=c99','-Wall','-Wextra','-Werror','-fPIC','-I'+str(NATIVE/'include'),'-c',HERE/'coh_auth.c','-o',tmp/'auth-arm64.o'])
   result['android_arm64_portable_object_built']=True;result['ndk_revision']=(args.ndk/'source.properties').read_text().split('Pkg.Revision = ')[1].splitlines()[0]
  else:result['android_arm64_portable_object_built']=False
  result['status']='PASS';result['source_pins_sha256']=hashlib.sha256((HERE/'source-pins.json').read_bytes()).hexdigest()
  serialized=json.dumps(result,indent=2,sort_keys=True)+'\n'
  if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(serialized)
  print(serialized,end='')
if __name__=='__main__':main()
