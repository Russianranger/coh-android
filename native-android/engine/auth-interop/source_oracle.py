"""Unmodified DbServer auth-cache and checksum functions on synthetic records."""
import json
import re
import subprocess
from pathlib import Path


def extract(source, name):
    match = re.search(r'(?m)^[^\n;{}]*\b' + re.escape(name) + r'\([^;{}]*\)\s*\{', source)
    if not match:
        raise ValueError('Missing pinned source function')
    start = match.start()
    cursor = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[start:cursor]


def qualify(repo, output):
    auth = (repo / 'upstream/ouroboros/DBServer/src/authcomm.c').read_text()
    checksum = (repo / 'upstream/ouroboros/Common/ClientLogin/clientcommLogin.c').read_text()
    entry = re.search(r'typedef struct\s*\{.*?\}\s*AuthEntry;', auth, re.S).group(0)
    code = '''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
typedef uint32_t U32;typedef uint8_t U8;
#define AUTH_BYTES 128
#define AUTH_CACHE_SIZE 4096
#define AUTH_CACHE_MASK (AUTH_CACHE_SIZE-1)
#define stricmp strcasecmp
#define LOG_OLD(...) ((void)0)
#define LOG_OLD_ERR(...) ((void)0)
'''
    code += entry + '\nstatic AuthEntry auth_cache[AUTH_CACHE_SIZE];\n'
    code += extract(auth, 'trimTrailingWhitespace') + '\n' + extract(auth, 'authValidLogin')
    code += '\nstatic U32 correct_game_checksum[4],ignore_checksum;\n'
    code += extract(checksum, 'clientCommLoginVerifyChecksum')
    code += r'''
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"source oracle failed line %d\n",__LINE__);return 1;}}while(0)
static void seed(void){
 memset(auth_cache,0,sizeof(auth_cache));AuthEntry *e=&auth_cache[0x345];e->id=42;e->cookie=0x12345;
 strcpy(e->name,"fixture");memset(e->user_data,0xa5,128);e->loyalty=11;e->loyaltyLegacy=12;e->pay_stat=13;
}
int main(void){
 U8 data[128];U32 loyalty,legacy,pay;char name[32];
 for(unsigned i=0;i<7;i++){
  seed();memset(data,0x5a,sizeof(data));loyalty=legacy=pay=0xdeadbeef;strcpy(name,"fixture");
  U32 uid=42,cookie=0x12345;if(i==0)uid=0;if(i==1)uid=43;if(i==2)cookie++;if(i==3)cookie+=4096;
  if(i==4)strcpy(name,"other");if(i==5)strcpy(name,"FIXTURE");if(i==6)strcpy(name,"fixture   ");
  int accepted=authValidLogin(uid,cookie,name,data,&loyalty,&legacy,&pay);
  CHECK(accepted==(i>=5));
  if(i<5){CHECK(data[0]==0x5a&&data[127]==0x5a&&loyalty==0xdeadbeef&&legacy==0xdeadbeef&&pay==0xdeadbeef);
   CHECK(auth_cache[0x345].id==42);
  }else{
   CHECK(data[0]==0xa5&&data[127]==0xa5&&loyalty==11&&legacy==12&&pay==13&&!strcmp(name,"fixture"));
   CHECK(!auth_cache[0x345].id&&!auth_cache[0x345].cookie);
   CHECK(!authValidLogin(uid,cookie,name,data,&loyalty,&legacy,&pay));
  }
 }
 U32 match[4]={1,2,3,4},mismatch[4]={4,3,2,1};memcpy(correct_game_checksum,match,sizeof(match));ignore_checksum=0;
 CHECK(sizeof(void*)==4||sizeof(void*)==8);
 CHECK(!clientCommLoginVerifyChecksum(match));CHECK(!clientCommLoginVerifyChecksum(mismatch));
 printf("{\"passed\":true,\"checks\":%u,\"synthetic_auth_cache_records\":true,\"original_auth_cache_binding\":true,\"original_auth_cache_one_shot\":true,\"upstream_checksum_sizeof_pointer_defect_observed\":true,\"real_account_login_verified\":false}\n",checks);
 return 0;
}
'''
    source = output / 'original_auth_boundary.c'
    binary = output / 'original_auth_boundary'
    source.write_text(code)
    subprocess.run(['cc', '-std=c11', '-O0', '-w', str(source), '-o', str(binary)], check=True,
                   capture_output=True, text=True, timeout=60)
    result = subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=30)
    return json.loads(result.stdout)
