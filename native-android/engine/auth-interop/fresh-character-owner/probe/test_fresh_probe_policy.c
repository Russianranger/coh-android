#include "fresh_probe_policy.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do {checks++;if(!(x))abort();}while(0)
void coh_auth_wipe(void *p,size_t n) {volatile uint8_t *b=p;while(n--)*b++=0;}
static void put32(uint8_t *p,uint32_t value) {
    unsigned i;for(i=0;i<4;i++)p[i]=(uint8_t)(value>>(i*8));
}
static void fixture(uint8_t record[96]) {
    memset(record,0,96);memcpy(record,"COHFRC01",8);put32(record+8,1);
    put32(record+12,25000);put32(record+16,1);record[20]=127;record[23]=1;
    put32(record+24,7001);put32(record+28,17);put32(record+32,23);
    record[40]=37;record[72]=41;
}
static void refused(uint8_t *record,size_t bytes) {
    FreshProbeMapPolicy output,saved;memset(&output,0xa5,sizeof(output));saved=output;
    CHECK(fresh_probe_decode_policy((CohBytes){record,bytes},&output)==COH_INVALID);
    CHECK(!memcmp(&saved,&output,sizeof(output)));
}
int main(void) {
    uint8_t record[97];FreshProbeMapPolicy out;unsigned i,j;
    union { FreshProbeMapPolicy align;uint8_t bytes[256]; } alias;
    fixture(record);CHECK(fresh_probe_decode_policy((CohBytes){record,96},&out)==COH_OK);
    CHECK(out.auth_endpoint.port==25000&&out.map_endpoint.port==7001&&out.map_id==1&&
          out.map_pid==17&&out.map_creation_filetime==23&&out.map_executable_sha256[0]==37&&
          out.operation_nonce[0]==41&&out.map_endpoint.address[0]==127&&out.map_endpoint.address[3]==1);
    for(i=0;i<96;i++)refused(record,i);
    refused(record,97);refused(NULL,96);
    CHECK(fresh_probe_decode_policy((CohBytes){record,96},NULL)==COH_INVALID);
    fixture(alias.bytes);CHECK(fresh_probe_decode_policy((CohBytes){alias.bytes,96},&alias.align)==COH_INVALID);
    fixture(alias.bytes+32);CHECK(fresh_probe_decode_policy((CohBytes){alias.bytes+32,96},&alias.align)==COH_INVALID);
    fixture(alias.bytes);CHECK(fresh_probe_decode_policy((CohBytes){alias.bytes,96},(FreshProbeMapPolicy *)(void *)(alias.bytes+1))==COH_INVALID);
    for(i=0;i<8;i++){fixture(record);record[i]^=1;refused(record,96);}
    for(i=8;i<12;i++)for(j=0;j<8;j++){fixture(record);record[i]^=(uint8_t)(1u<<j);refused(record,96);}
    for(i=16;i<28;i++)for(j=0;j<8;j++){fixture(record);record[i]^=(uint8_t)(1u<<j);refused(record,96);}
    for(i=88;i<96;i++)for(j=0;j<8;j++){fixture(record);record[i]^=(uint8_t)(1u<<j);refused(record,96);}
    fixture(record);memset(record+28,0,4);refused(record,96);
    fixture(record);memset(record+32,0,8);refused(record,96);
    fixture(record);memset(record+40,0,32);refused(record,96);
    fixture(record);memset(record+72,0,16);refused(record,96);
    for(i=0;i<4;i++) {
        static const uint32_t ports[]={0,19999,60000,UINT32_MAX};
        fixture(record);put32(record+12,ports[i]);refused(record,96);
    }
    for(i=0;i<2;i++) {
        fixture(record);put32(record+12,i?59999:20000);
        CHECK(fresh_probe_decode_policy((CohBytes){record,96},&out)==COH_OK);
    }
    /* Every hash/nonce position can carry the sole nonzero octet. These are
     * syntactic pins; the decoder does not invent executable/entropy proof. */
    for(i=0;i<32;i++) {
        fixture(record);memset(record+40,0,32);record[40+i]=1;
        CHECK(fresh_probe_decode_policy((CohBytes){record,96},&out)==COH_OK);
    }
    for(i=0;i<16;i++) {
        fixture(record);memset(record+72,0,16);record[72+i]=1;
        CHECK(fresh_probe_decode_policy((CohBytes){record,96},&out)==COH_OK);
    }
    printf("{\"schema\":\"coh-fresh-private-policy-parser-test-v1\",\"checks\":%u,\"windows_execution\":false,\"world_authority\":false}\n",checks);
    return 0;
}
