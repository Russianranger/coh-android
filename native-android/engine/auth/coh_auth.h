#ifndef COH_ENGINE_AUTH_H
#define COH_ENGINE_AUTH_H
#include "../coh_contracts.h"
#include "../../include/coh_native_core.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Fixed original CryptoPP DH group. Values are unsigned, big endian, padded
 * to 64 bytes, NOT host U32 arrays. This is legacy interoperability, not TLS. */
#define COH_AUTH_DH_BYTES 64u
#define COH_AUTH_BODY_MAX 1000u
#define COH_AUTH_RSA_MAX 512u
#define COH_AUTH_SHARDS_MAX 32u
extern const uint8_t coh_auth_dh_prime[COH_AUTH_DH_BYTES];
typedef struct {
    void *context;
    CohStatus (*keypair)(void *, uint8_t private_key[64], uint8_t public_key[64]);
    /* Provider MUST check subgroup membership, private range and constant-time
     * modular exponentiation. Rejected peer keys must never produce a key. */
    CohStatus (*shared)(void *, const uint8_t private_key[64],
        const uint8_t peer_key[64], uint8_t shared_secret[64]);
    CohStatus (*md5)(void *, CohBytes, uint8_t digest[16]);
    CohStatus (*sha512)(void *, CohBytes, uint8_t digest[64]);
    /* RSAES-OAEP SHA1/MGF1-SHA1, empty label. Source may split 94-byte
     * plaintext into multiple blocks for a small RSA modulus. */
    CohStatus (*rsa_oaep_sha1)(void *, CohBytes modulus, CohBytes exponent,
        CohBytes plain, uint8_t *, size_t capacity, size_t *bytes);
} CohAuthCrypto;
/* No default provider is installed. Android must supply an audited provider.
 * The optional OpenSSL implementation is a separately linked host backend. */
const CohAuthCrypto *coh_auth_openssl_provider(void);
void coh_auth_wipe(void *, size_t);
CohStatus coh_auth_dh_keypair(const CohAuthCrypto *, uint8_t private_key[64],
    uint8_t public_key[64]);
CohStatus coh_auth_dh_blowfish(const CohAuthCrypto *, const uint8_t private_key[64],
    const uint8_t peer_key[64], CohBlowfish *);
/* Zeroes outbound padding and enforces the XOR checksum that source
 * authGetPacket ignored. Inbound padding/reserved DWORD may contain source
 * pooled-buffer residue. Input/output may overlap; failed output unchanged. */
CohStatus coh_auth_global_encode(CohBytes body, uint8_t *frame, size_t capacity,
    size_t *bytes);
CohStatus coh_auth_global_decode(CohBytes frame, uint8_t *body, size_t capacity,
    size_t *padded_body_bytes);
/* Length-prefixed TCP assembler. It buffers one frame, preserves later input
 * through *consumed, and poisons malformed lengths until reset. No sockets,
 * retries or authentication success are implicit. */
typedef struct { size_t used, expected; uint8_t failed, data[COH_AUTH_BODY_MAX+2]; } CohAuthStream;
void coh_auth_stream_reset(CohAuthStream *);
CohStatus coh_auth_stream_feed(CohAuthStream *, CohBytes, size_t *consumed,
    CohBytes *frame);
enum { COH_AUTH_USA=30206, COH_AUTH_ASIA=30207, COH_AUTH_GLOBAL=30810,
    COH_AUTH_REACTIVATION=100903, COH_AUTH_OUROBOROS1=190516,
    COH_AUTH_OUROBOROS2=191021 };
typedef struct {
    uint32_t one_time_key, protocol;
    size_t modulus_bytes, exponent_bytes;
    uint8_t modulus[COH_AUTH_RSA_MAX], exponent[8];
} CohAuthHello;
typedef struct {
    uint8_t session[8], update_key[8];
    uint32_t pay_status, loyalty, remaining, quota, warning, login_flags, reactivation;
} CohAuthLoginOk;
typedef struct { uint32_t game_key, user_id; uint8_t shard_id; } CohAuthPlayOk;
typedef struct {
    uint8_t id, ipv4[4], age_limit, pk, status, vip;
    uint16_t port, current_users, maximum_users;
    uint32_t type;
    char name[256];
} CohAuthShard;
typedef struct { uint8_t count, last_shard; CohAuthShard shards[COH_AUTH_SHARDS_MAX]; } CohAuthShards;
/* Bodies include the command byte; parsers allow up to seven padding bytes.
 * These functions do not change a connection state or claim authentication. */
CohStatus coh_auth_parse_hello(CohBytes, CohAuthHello *);
CohStatus coh_auth_parse_login_ok(CohBytes, uint32_t protocol, CohAuthLoginOk *);
CohStatus coh_auth_parse_play_ok(CohBytes, CohAuthPlayOk *);
CohStatus coh_auth_parse_shards(CohBytes, uint32_t protocol, int extended, CohAuthShards *);
CohStatus coh_auth_server_list(const uint8_t session[8], uint32_t protocol,
    const uint32_t *groups, size_t group_count, uint8_t *, size_t capacity, size_t *bytes);
CohStatus coh_auth_about_to_play(const uint8_t session[8], uint8_t shard,
    uint8_t *, size_t capacity, size_t *bytes);
/* Implements only global/reactivation/Ouroboros login, rejects Asia/USA.
 * Account is ASCII, trimmed/lowercased, max14 bytes; password max16 bytes.
 * The wire body is still sensitive and must not be logged or retained. */
CohStatus coh_auth_login(const CohAuthCrypto *, const CohAuthHello *,
    const char *account, const char *password, uint32_t subscription,
    uint16_t flags, uint8_t *, size_t capacity, size_t *bytes);
/* Source dbOrMapConnect: seven packed(1) values, exact remaining bit count.
 * Both address candidates retained, ports checked, failure cookies rejected. */
typedef struct {
    uint32_t link_id, map_id, address[2], cookie;
    uint16_t udp_port, tcp_port;
} CohAuthMapHandoff;
CohStatus coh_auth_map_handoff(CohBytes, size_t bit_length, CohAuthMapHandoff *);
/* byte_aligned=1 for an already decompressed compressed-profile packet:
 * original bsReadBitsPack reads a fixed32-bit LE value in that mode. */
CohStatus coh_auth_map_handoff_profile(CohBytes, size_t bit_length,
    int byte_aligned, CohAuthMapHandoff *);
#ifdef __cplusplus
}
#endif
#endif
