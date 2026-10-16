#!/usr/bin/env python3
"""Declared, nonshipping checksum correction; never edits upstream in place."""
import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from source_audit import CHECKSUM, digest, extract, pinned_sources

CALLER = 'upstream/ouroboros/DBServer/src/clientcomm.c'
CANDIDATE = '''int clientCommLoginVerifyChecksum(U32 game_checksum[])
{
    /* Nonshipping isolated-auth candidate: missing checksum fails closed. */
    if (ignore_checksum)
        return 1;
    return memcmp(game_checksum,correct_game_checksum,sizeof(correct_game_checksum))!=0;
}'''


def prepare(root, directory):
    values, identities = pinned_sources(root)
    original = extract(values[CHECKSUM], 'clientCommLoginVerifyChecksum')
    function = extract(values[CALLER], 'handleLogin')
    start = function.index('    {\n        int            dont_check_version')
    end = function.index('\n\n    // DGNOTE', start)
    block = function[start:end]
    if not block.endswith('    }') or 'authValidLogin' in block:
        raise ValueError('original_login_policy_boundary_changed')
    replacement = values[CHECKSUM].replace(original, CANDIDATE)
    if values[CHECKSUM].count(original) != 1:
        raise ValueError('original_checksum_function_not_unique')
    patch = ''.join(difflib.unified_diff(values[CHECKSUM].splitlines(True), replacement.splitlines(True),
                                       fromfile='a/' + CHECKSUM, tofile='b/' + CHECKSUM))
    (directory / 'checksum-failclosed.patch').write_text(patch)
    preamble = r'''#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#ifdef _WIN32
#define stricmp _stricmp
#define strnicmp _strnicmp
#else
#include <strings.h>
#define stricmp strcasecmp
#define strnicmp strncasecmp
#endif
typedef uint32_t U32; typedef uint8_t U8;
#define AUTH_BYTES 128
#define DBSERVER_CLIENT_PROTOCOL_VERSION SOURCE_PROTOCOL
#define LOG_OLD_ERR(...) ((void)0)
#define Strncpyt(dst,src) snprintf(dst,sizeof(dst),"%s",src)
typedef struct {char account_name[100];void *link;} GameClientLink;
typedef struct {U32 sum[4];int protocol,no_version;char version[100];unsigned strings,packs,arrays;} Packet;
static struct {int fake_auth;} server_cfg;
static U32 correct_game_checksum[4]={0x12345678,0x9abcdef0,0x87654321,0xfedcba98},ignore_checksum;
static const char *getCompatibleGameVersion(void){return "auth-qualification-1";}
static void sendMsg(void *a,const char *b,GameClientLink *c){(void)a;(void)b;(void)c;}
static char *strstri(char *a,const char *b){(void)a;(void)b;return NULL;}
static const char *strstriConst(const char *a,const char *b){(void)a;(void)b;return NULL;}
static char *pktGetString(Packet *p){return p->strings++ ? p->version : "probe";}
static U32 pktGetBitsPack(Packet *p,int n){(void)n;unsigned k=p->packs++;return k==0?42:(k==1?(U32)p->protocol:(U32)p->no_version);}
static U32 pktGetBits(Packet *p,int n){(void)p;(void)n;return 0x12345;}
static void pktGetBitsArray(Packet *p,size_t bits,void *out){if(p->arrays++)memcpy(out,p->sum,bits/8);else memset(out,0,bits/8);}
'''
    protocol = re.search(r'^#define DBSERVER_CLIENT_PROTOCOL_VERSION\s+(\d+)', values['upstream/ouroboros/Common/comm_backend.h'], re.M)
    if not protocol:
        raise ValueError('original_protocol_constant_missing')
    preamble = preamble.replace('SOURCE_PROTOCOL', protocol[1])
    suffix = r'''
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"policy control failed at %d\n",__LINE__);return 1;}}while(0)
static void seed(Packet *p){memset(p,0,sizeof(*p));memcpy(p->sum,correct_game_checksum,16);p->protocol=DBSERVER_CLIENT_PROTOCOL_VERSION;strcpy(p->version,getCompatibleGameVersion());ignore_checksum=0;server_cfg.fake_auth=0;}
int main(void){Packet p;GameClientLink client={0};
 seed(&p);CHECK(login_policy(&p,&client)==1);
 for(unsigned bit=0;bit<128;bit++){seed(&p);((U8*)p.sum)[bit/8]^=(U8)(1u<<(bit%8));CHECK(login_policy(&p,&client)==EXPECT_ORIGINAL);}
 seed(&p);memset(p.sum,0,16);CHECK(login_policy(&p,&client)==EXPECT_ORIGINAL);
 seed(&p);ignore_checksum=1;CHECK(login_policy(&p,&client)==EXPECT_ORIGINAL);
 for(int bypass=0;bypass<2;bypass++){seed(&p);p.no_version=bypass;strcpy(p.version,"wrong-version");CHECK(!login_policy(&p,&client));}
 seed(&p);p.protocol--;CHECK(!login_policy(&p,&client));
 seed(&p);p.no_version=1;p.sum[3]^=0x80000000;CHECK(login_policy(&p,&client)==EXPECT_ORIGINAL);
 printf("{\"passed\":true,\"checks\":%u,\"original_defect_expected\":%s,\"network_execution\":false,\"real_account_login_verified\":false}\n",checks,EXPECT_ORIGINAL?"true":"false");return 0;}
'''
    for name, implementation in [('original', original), ('candidate', CANDIDATE)]:
        text = preamble + implementation + '\nstatic int login_policy(Packet *pak,GameClientLink *client) { U32 cookie,auth_id; U8 test_auth_data[AUTH_BYTES];\n'
        text += block + '\n(void)cookie;(void)auth_id;return 1;}\n'
        text += f'#define EXPECT_ORIGINAL {int(name == "original")}\n' + suffix
        (directory / (name + '-policy.c')).write_text(text)
    return {'schema': 'coh-auth-checksum-candidate-v1', 'source_identities': identities,
            'original_function_sha256': digest(original.encode()), 'candidate_function_sha256': digest(CANDIDATE.encode()),
            'original_db_login_policy_block_sha256': digest(block.encode()),
            'patch_sha256': digest(patch.encode()),
            'scope': 'Original checksum function and unchanged first handleLogin policy block; synthetic field getters, not original packet decoding or full login.',
            'declared_changes': ['Compare all 16 checksum bytes, removing pointer-size guard.',
                                 'Reject when initGameChecksum could not read the checksum file; isolated candidate has no development skip.'],
            'upstream_worktree_modified': False, 'patched_dbserver_built': False,
            'deployed_binary_inspected': False, 'real_account_login_verified': False}


def qualify(root, directory, sanitize=False):
    proof = prepare(root, directory)
    modes = [('release', ['-O2'])]
    if sanitize:
        modes.append(('asan_ubsan', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-pie', '-no-pie']))
    proof['executions'] = {}
    for mode, flags in modes:
        for name in ('original', 'candidate'):
            binary = directory / (name + '-' + mode)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-sizeof-array-argument', '-Wno-sizeof-pointer-memaccess',
                            *flags, str(directory / (name + '-policy.c')), '-o', str(binary)],
                           check=True, capture_output=True, timeout=60)
            result = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=30,
                                    env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1'))
            proof['executions'][name + '-' + mode] = json.loads(result.stdout)
    proof['passed'] = True
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-checksum-candidate-') as tmp:
        proof = qualify(args.source_root.resolve(), Path(tmp), args.sanitize)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': True, 'checks': {key: value['checks'] for key, value in proof['executions'].items()}, 'real_account_login_verified': False}))


if __name__ == '__main__':
    main()
