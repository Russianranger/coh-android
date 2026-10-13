#!/usr/bin/env python3
"""Isolate the pinned algorithm; replace its buffer wrapper with checked byte operations."""
from pathlib import Path
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
PIN='7106020d77eea8313422b865ce3e8587ad7e733366429cf0e613427cdc191585'
def generate():
    src=ROOT.parent/'upstream/ouroboros/libs/UtilitiesLib/src/network/blowfish.c'
    raw=src.read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    s='\n'.join(x for x in raw.decode().splitlines() if not x.startswith('#include'))
    start=s.index('void cryptBlowfishEncrypt(BLOWFISH_CTX');end=s.index('void cryptBlowfishInit(BLOWFISH_CTX',start)
    s=s[:start]+s[end:];s=s[:s.index('void cryptBlowfishInitU32')]
    s=s.replace('unsigned long','uint32_t').replace('BLOWFISH_CTX','CohBlowfish').replace('INLINEDBG','inline')
    s=s.replace('void cryptBlowfishInit(', 'static void cryptBlowfishInit(').replace('unsigned char *key, int keyLen','const unsigned char *key, int keyLen')
    prefix='/* Generated; retain original author notice below. */\n#include "coh_native_core.h"\n#include "byte_reader.h"\nstatic inline uint32_t endianSwapU32(uint32_t v){return (v>>24)|((v>>8)&0xff00)|((v<<8)&0xff0000)|(v<<24);}\n_Static_assert(sizeof(CohBlowfish)==4168,"32-bit words");\n'
    suffix='''
int coh_bf_init(CohBlowfish *ctx,const uint8_t *key,size_t bytes){
    if(!ctx || !key || !bytes || bytes>56)return1;
    cryptBlowfishInit(ctx,key,(int)bytes);return0;
}
int coh_bf_crypt(CohBlowfish *ctx,uint8_t *mem,size_t bytes,int decrypt){
    if(!ctx || (!mem && bytes) || bytes%8 || (decrypt!=0 && decrypt!=1))return1;
    for(size_t at=0;at<bytes;at+=8){
        uint32_t l=u32(mem+at),r=u32(mem+at+4);
        if(decrypt)cryptBlowfishDecryptBlock(ctx,&l,&r,0);
        else cryptBlowfishEncryptBlock(ctx,&l,&r,0);
        put32(mem+at,l);put32(mem+at+4,r);
    }
    return0;
}
'''.replace('return1','return 1').replace('return0','return 0')
    result=(prefix+s+suffix).encode()
    receipt={'upstream_source_sha256':PIN,'generated_sha256':hashlib.sha256(result).hexdigest(),
             'producer':'fixed-width derivative + checked unaligned-safe game little-endian wrapper','shipping_source_modified':False}
    return result,(json.dumps(receipt,indent=2)+'\n').encode()
def main():
    a=argparse.ArgumentParser();a.add_argument('--check',action='store_true');args=a.parse_args()
    code,receipt=generate();cp=ROOT/'src/coh_blowfish.c';rp=ROOT/'source-pins/crypto.json'
    if args.check:assert cp.read_bytes()==code and rp.read_bytes()==receipt
    else:
        cp.parent.mkdir(parents=True,exist_ok=True);rp.parent.mkdir(parents=True,exist_ok=True)
        cp.write_bytes(code);rp.write_bytes(receipt)
    print(receipt.decode().strip())
if __name__=='__main__':main()
