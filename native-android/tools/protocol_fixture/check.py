#!/usr/bin/env python3
"""Run the exact Android protocol selftest on host under ASan/UBSan.

Also probes exact-size arbitrary/mutated byte allocations; arbitrary bytes
may legitimately parse, so the invariant is valid bounded output or unchanged
failure output, not rejection of every random byte sequence.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
DRIVER=r'''
#include "coh_protocol.h"
#include "protocol_goldens.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t state=0x434f480c;
static uint32_t next(void){state^=state<<13;state^=state>>17;state^=state<<5;return state;}
static int untouched(const void *p,size_t bytes){const uint8_t *b=p;for(size_t i=0;i<bytes;i++)if(b[i]!=0xa5)return 0;return 1;}
int main(void){
 CohProtocolProof proof;if(coh_protocol_selftest(&proof)||!proof.passed)return 1;
 CohBlowfish ctx;if(coh_bf_init(&ctx,protocol_key,sizeof(protocol_key)))return 2;
 unsigned fuzz_cases=0;
 for(unsigned i=0;i<12000;i++){
  size_t n=next()%(COH_PROTOCOL_FRAME_MAX+1);uint8_t *bytes=malloc(n?n:1);if(!bytes)return 3;
  for(size_t at=0;at<n;at++)bytes[at]=(uint8_t)next();
  if(i%2){const ProtocolGolden *g=protocol_goldens+(next()%(sizeof(protocol_goldens)/sizeof(protocol_goldens[0])));n=g->wire_bytes;free(bytes);bytes=malloc(n);if(!bytes)return 4;memcpy(bytes,g->wire,n);bytes[next()%n]^=(uint8_t)(1u<<(next()%8));}
  CohProtocolPacket out;memset(&out,0xa5,sizeof(out));int result=coh_protocol_decode(&ctx,(int)(i%2),bytes,n,&out);free(bytes);
  if(result){if(!untouched(&out,sizeof(out)))return 5;}
  else if(out.payload_bytes>COH_PROTOCOL_PAYLOAD_MAX || !out.payload_bits || out.payload_bits>COH_PROTOCOL_PAYLOAD_MAX*8 || out.payload_bytes!=(out.payload_bits+7)/8)return 6;
  fuzz_cases++;
 }
 printf("{\"passed\":true,\"checks\":%u,\"wire_cases\":%u,\"bit_cases\":%u,\"malformed_cases\":%u,\"unaligned_cases\":%u,\"fuzz_cases\":%u,\"pointer_bytes\":%zu,\"long_bytes\":%zu}\n",proof.checks,proof.wire_cases,proof.bit_cases,proof.malformed_cases,proof.unaligned_cases,fuzz_cases,sizeof(void*),sizeof(long));return 0;
}
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 paths=[ROOT/'protocol'/file for file in ['coh_protocol.c','coh_protocol_selftest.c','protocol_goldens.h','coh_protocol.h']]+[ROOT/'src/coh_blowfish.c']
 with tempfile.TemporaryDirectory(prefix='coh-protocol-host-') as d:
  d=Path(d);source=d/'driver.c';source.write_text(DRIVER);binary=d/'protocol-host'
  command=['cc','-std=c11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(ROOT/'include'),'-I'+str(ROOT/'protocol'),str(ROOT/'protocol/coh_protocol.c'),str(ROOT/'protocol/coh_protocol_selftest.c'),str(ROOT/'src/coh_blowfish.c'),str(source),'-o',str(binary)]
  subprocess.run(command,check=True)
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  result=subprocess.run([str(binary)],check=True,env=env,text=True,capture_output=True);proof=json.loads(result.stdout)
  proof.update(schema='coh-native-protocol-host-proof-v1',scope='Linux host LP64 native kernel, independent compiled goldens; no Android or unchanged-server handshake',sanitizers=['AddressSanitizer','UndefinedBehaviorSanitizer'],leak_sanitizer=False,source_sha256={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths})
  args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
