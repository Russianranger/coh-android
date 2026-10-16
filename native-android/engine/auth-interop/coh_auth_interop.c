#include "coh_auth_interop.h"
#include <stdio.h>
#include <string.h>
static int endpoint(CohNetEndpoint e) {
    return e.port && e.address[0] && e.address[0] < 224 &&
           !(e.address[0]==255&&e.address[1]==255&&e.address[2]==255&&e.address[3]==255);
}
static int same(CohNetEndpoint a, CohNetEndpoint b) {
    return a.port==b.port&&!memcmp(a.address,b.address,4);
}
static int nonzero(const void *p, size_t n) {
    const unsigned char *b=p;unsigned char v=0;
    for(size_t i=0;i<n;i++)v|=b[i];
    return v!=0;
}
static CohStatus reject(CohAuthInteropPolicyFailure *out,CohAuthInteropPolicyFailure f) {
    if(out)*out=f;
    return COH_INVALID;
}
CohStatus coh_auth_interop_validate(const CohAuthInteropProfile *p,CohAuthInteropPolicyFailure *out) {
    if(!p||!endpoint(p->auth)||!endpoint(p->db)||!p->map_count||p->map_count>COH_INTEROP_MAPS_MAX)
        return reject(out,COH_INTEROP_POLICY_ENDPOINT);
    for(unsigned i=0;i<p->map_count;i++) {
        if(!endpoint(p->maps[i]))return reject(out,COH_INTEROP_POLICY_ENDPOINT);
        for(unsigned j=0;j<i;j++)if(same(p->maps[i],p->maps[j]))return reject(out,COH_INTEROP_POLICY_ENDPOINT);
    }
    if(!p->shard_id||p->character_slot>=COH_DB_SLOTS_MAX)return reject(out,COH_INTEROP_POLICY_SELECTION);
    if(p->db_policy.protocol_version!=COH_DB_PROTOCOL_VERSION)return reject(out,COH_INTEROP_POLICY_PROTOCOL);
    /* Original DbServer copies game_version into 100 bytes before comparison. */
    size_t length=0;
    while(length<sizeof(p->db_policy.patch_version)&&p->db_policy.patch_version[length])length++;
    if(!length||length>=100)return reject(out,COH_INTEROP_POLICY_VERSION);
    for(size_t i=0;i<length;i++)if((unsigned char)p->db_policy.patch_version[i]<32||
                                (unsigned char)p->db_policy.patch_version[i]>126)
        return reject(out,COH_INTEROP_POLICY_VERSION);
    if(!nonzero(p->db_policy.executable_checksum,16))return reject(out,COH_INTEROP_POLICY_CHECKSUM);
    if(nonzero(p->db_policy.account,sizeof(p->db_policy.account))||p->db_policy.user_id||p->db_policy.cookie||
       nonzero(p->db_policy.auth_user_data,sizeof(p->db_policy.auth_user_data)))
        return reject(out,COH_INTEROP_POLICY_AUTH_INJECTION);
    if(p->db_policy.no_version_check||p->db_policy.no_timeout||p->db_policy.keyed_access_level||
       nonzero(p->db_policy.keyed_access_issued_to,sizeof(p->db_policy.keyed_access_issued_to)))
        return reject(out,COH_INTEROP_POLICY_BYPASS);
    if(!memchr(p->db_policy.patch_message,0,sizeof(p->db_policy.patch_message))||
       !memchr(p->db_policy.system_spec,0,sizeof(p->db_policy.system_spec)))
        return reject(out,COH_INTEROP_POLICY_VERSION);
    if(p->timeout_ms<1000||p->timeout_ms>300000)return reject(out,COH_INTEROP_POLICY_TIMEOUT);
    if(out)*out=COH_INTEROP_POLICY_OK;
    return COH_OK;
}
CohStatus coh_auth_interop_approve_map(void *context,CohNetEndpoint e,uint32_t generation) {
    const CohAuthInteropProfile *p=context;
    if(!generation||coh_auth_interop_validate(p,NULL)!=COH_OK)return COH_INVALID;
    for(unsigned i=0;i<p->map_count;i++)if(same(e,p->maps[i]))return COH_OK;
    return COH_INVALID;
}
CohStatus coh_auth_interop_config(const CohAuthInteropProfile *p,const CohAuthCrypto *crypto,CohLiveConfig *out) {
    if(!out||!crypto||!crypto->keypair||!crypto->shared||!crypto->md5||!crypto->sha512||!crypto->rsa_oaep_sha1||
       coh_auth_interop_validate(p,NULL)!=COH_OK)return COH_INVALID;
    CohLiveConfig c;memset(&c,0,sizeof(c));
    c.login.crypto=crypto;c.login.connect_timeout_ms=p->timeout_ms;c.login.reply_timeout_ms=p->timeout_ms;c.login.receive_budget=8;
    c.authorized_auth=p->auth;
    /* Fixed normal-server encrypted profile. No development downgrade. */
    c.db.transport.link=(CohNetConfig){5,100,10,p->timeout_ms,p->timeout_ms,p->timeout_ms};
    c.db.transport.peer=p->db;c.db.transport.receive_budget=8;c.db.transport.encryption_required=1;
    c.db.request_timeout_ms=p->timeout_ms;
    c.map.udp=c.db.transport;c.map.udp.peer=p->maps[0];
    c.map.application_timeout_ms=p->timeout_ms;c.map.message_budget=8;
    c.approve_map=coh_auth_interop_approve_map;c.policy_context=(void*)p;
    *out=c;return COH_OK;
}
CohStatus coh_auth_interop_report(const CohLiveDiagnostics *d,uint64_t elapsed,int interrupted,char *out,size_t capacity,size_t *bytes) {
    if(!d||!out||!bytes||!capacity)return COH_INVALID;
    char result[2048];
    int n=snprintf(result,sizeof(result),
        "{\"schema\":\"coh-auth-interop-probe-v1\",\"phase\":%u,\"auth_state\":%u,\"db_phase\":%u,\"map_phase\":%u,"
        "\"status\":%u,\"elapsed_ms\":%llu,\"interrupted\":%s,\"auth_receipts\":%llu,\"shard_choices\":%llu,"
        "\"character_choices\":%llu,\"map_approvals\":%llu,\"policy_rejections\":%llu,\"failures\":%llu,"
        "\"opened_sockets\":%llu,\"closed_sockets\":%llu,\"cleanup_complete\":%s,"
        "\"encrypted_profile_required\":true,\"no_version_check\":false,\"peer_identity_verified\":false,"
        "\"real_account_login_verified\":false,\"native_live_world\":false,\"physical_thor_accepted\":false}\n",
        (unsigned)d->phase,(unsigned)d->auth_state,(unsigned)d->db_phase,(unsigned)d->map_phase,(unsigned)d->last_status,
        (unsigned long long)elapsed,interrupted?"true":"false",(unsigned long long)d->auth_receipts,
        (unsigned long long)d->shard_choices,(unsigned long long)d->character_choices,(unsigned long long)d->map_approvals,
        (unsigned long long)d->policy_rejections,(unsigned long long)d->failures,(unsigned long long)d->opened_sockets,
        (unsigned long long)d->closed_sockets,d->opened_sockets==d->closed_sockets?"true":"false");
    if(n<0||(size_t)n>=sizeof(result))return COH_LIMIT;
    if((size_t)n>=capacity)return COH_LIMIT;
    memcpy(out,result,(size_t)n+1);*bytes=(size_t)n;return COH_OK;
}
