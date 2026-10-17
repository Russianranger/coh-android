#include "coh_character_prefix.h"
#include <string.h>
static int overlap(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;
    if(!an||!bn)return 0;
    if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;
    return aa<bb+bn&&bb<aa+an;
}
#define PACK(n,f) do { s=coh_rep_pack(&q,n,&v.f);if(s!=COH_OK)return s; }while(0)
#define READ(n,f) do { s=coh_rep_read(&q,n,&v.f);if(s!=COH_OK)return s; \
    if(v.f>=(UINT32_C(1)<<n))return COH_INVALID; }while(0)
CohStatus coh_character_prefix(CohRepReader *r,CohCharacterPrefix *out) {
    CohRepReader q;CohCharacterPrefix v;CohStatus s;uint32_t ignored;
    if(!r||!out)return COH_INVALID;
    q=*r;s=coh_rep_read(&q,0,&ignored);if(s!=COH_OK)return s;
    if(overlap(r,sizeof(*r),out,sizeof(*out))||
       overlap(r,sizeof(*r),q.bytes.data,q.bytes.size)||
       overlap(out,sizeof(*out),q.bytes.data,q.bytes.size))return COH_INVALID;
    memset(&v,0,sizeof(v));v.begin_bit=q.cursor;
    PACK(1,boost_diminishing);PACK(1,power_diminishing);PACK(1,no_base_edit);
    PACK(2,beta_base);PACK(1,base_raid);
    size_t pad=(8u-(q.cursor&7u))&7u;
    if(pad>q.bits-q.cursor)return COH_INVALID;
    q.cursor+=pad;
    if(COH_CHARACTER_AUTH_BYTES>(q.bits-q.cursor)/8)return COH_INVALID;
    memcpy(v.auth_user_data,q.bytes.data+q.cursor/8,COH_CHARACTER_AUTH_BYTES);
    q.cursor+=8u*COH_CHARACTER_AUTH_BYTES;
    READ(1,player_type);READ(2,player_subtype);READ(3,praetorian_progress);
    READ(1,player_type_by_location);
    v.end_bit=q.cursor;*out=v;*r=q;return COH_OK;
}
