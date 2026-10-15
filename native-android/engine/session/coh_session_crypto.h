#ifndef COH_SESSION_CRYPTO_H
#define COH_SESSION_CRYPTO_H
#include "../auth/coh_auth.h"
#include "../network/coh_net.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Direct CohNetKeyExchange callback. context borrows a CohAuthCrypto provider
 * for the owning NetLink lifetime. Each negotiation creates a fresh keypair;
 * no private key, account, password or shared secret is retained here.
 * No provider is selected implicitly, including on Android. */
CohStatus coh_session_key_exchange(void *context,
    const uint8_t peer_public[64], uint8_t own_public[64], CohBlowfish *key);
#ifdef __cplusplus
}
#endif
#endif
