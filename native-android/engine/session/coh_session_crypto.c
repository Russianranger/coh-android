#include "coh_session_crypto.h"
#include <string.h>
CohStatus coh_session_key_exchange(void *context, const uint8_t peer[64],
    uint8_t own[64], CohBlowfish *out) {
    const CohAuthCrypto *provider=(const CohAuthCrypto *)context;
    uint8_t private_key[64]={0}, public_key[64]={0};
    CohBlowfish key;
    CohStatus status;
    if(!provider || !peer || !own || !out)return COH_INVALID;
    memset(&key,0,sizeof(key));
    status=coh_auth_dh_keypair(provider,private_key,public_key);
    if(status==COH_OK)status=coh_auth_dh_blowfish(provider,private_key,peer,&key);
    if(status==COH_OK){memcpy(own,public_key,64);*out=key;}
    coh_auth_wipe(private_key,sizeof(private_key));
    coh_auth_wipe(public_key,sizeof(public_key));
    coh_auth_wipe(&key,sizeof(key));
    return status;
}
