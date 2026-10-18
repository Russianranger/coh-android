#include "fresh_probe_policy.h"
#include <string.h>
typedef struct { char pad; FreshProbeMapPolicy value; } PolicyAlignment;
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static uint64_t le64(const uint8_t *p) {
    return (uint64_t)le32(p)|(uint64_t)le32(p+4)<<32;
}
static int nonzero(const uint8_t *p,size_t bytes) {
    uint8_t sum=0;size_t i;for(i=0;i<bytes;i++)sum|=p[i];return sum!=0;
}
static int overlaps(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    return x<=y?y-x<an:x-y<bn;
}
CohStatus fresh_probe_decode_policy(CohBytes record,FreshProbeMapPolicy *out) {
    const uint8_t *p=record.data;FreshProbeMapPolicy result;
    uint32_t auth_port;
    if(!out||(uintptr_t)out%offsetof(PolicyAlignment,value)||!p||
       record.size!=FRESH_PROBE_POLICY_BYTES||overlaps(p,record.size,out,sizeof(*out)))return COH_INVALID;
    if(memcmp(p,"COHFRC01",8)||le32(p+8)!=1)return COH_INVALID;
    auth_port=le32(p+12);
    if(auth_port<20000||auth_port>59999||le32(p+16)!=1||
       p[20]!=127||p[21]||p[22]||p[23]!=1||le32(p+24)!=7001||
       !le32(p+28)||!le64(p+32)||!nonzero(p+40,32)||!nonzero(p+72,16)||nonzero(p+88,8))return COH_INVALID;
    memset(&result,0,sizeof(result));
    result.auth_endpoint=(CohNetEndpoint){{127,0,0,1},(uint16_t)auth_port};
    result.map_endpoint=(CohNetEndpoint){{127,0,0,1},7001};
    result.map_id=le32(p+16);result.map_pid=le32(p+28);
    result.map_creation_filetime=le64(p+32);
    memcpy(result.map_executable_sha256,p+40,32);memcpy(result.operation_nonce,p+72,16);
    memcpy(out,&result,sizeof(result));coh_auth_wipe(&result,sizeof(result));return COH_OK;
}
