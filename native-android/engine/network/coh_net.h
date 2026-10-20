#ifndef COH_ENGINE_NET_H
#define COH_ENGINE_NET_H
#include "../coh_contracts.h"
#include "../../protocol/coh_protocol.h"
#ifdef __cplusplus
extern "C" {
#endif
/* Checked adapter of UtilitiesLib NetLink; no socket, JNI, credentials or game
 * commands are implicit. Single owner thread. Times are monotonic milliseconds. */
#define COH_NET_ACK_MAX 31u
#define COH_NET_PAYLOAD_MAX 1440u
#define COH_NET_FRAGMENT_MAX 16u
#define COH_NET_MESSAGE_MAX 16384u
/* Opt-in decoded receive ceiling only. Wire/reassembly, TX and legacy next()
 * remain 16 KiB. No queue slot or stack buffer uses this expanded bound. */
#define COH_NET_DECODED_MAX (4u*1024u*1024u)
#define COH_NET_TX_MAX 32u
#define COH_NET_RX_MAX 16u
#define COH_NET_GROUP_MAX 4u
#define COH_NET_WINDOW 16384u
typedef struct {
    uint32_t id, sibling_id, sibling_count, sibling_part, ordered_id;
    uint32_t ack_count, acks[COH_NET_ACK_MAX], payload_bits;
    uint8_t compressed, ordered, connect;
    uint8_t payload[COH_NET_PAYLOAD_MAX];
} CohNetPacket;
/* connect is explicit because the original initial CONNECT always omits
 * negotiated compression/ordered header flags, including retransmission. */
CohStatus coh_net_frame_encode(unsigned version, CohBlowfish *key, int encrypted,
    const CohNetPacket *, uint8_t *frame, size_t capacity, size_t *bytes);
CohStatus coh_net_frame_decode(unsigned version, CohBlowfish *key, int encrypted,
    int connect, CohBytes frame, CohNetPacket *);
/* Mirrors calcTimeout, in milliseconds; scheduling policy and retry budget are
 * explicit bounds added by this adapter, rather than a new wire protocol. */
uint32_t coh_net_retry_ms(unsigned retries, unsigned ping_ms, int older_than_ack);
typedef struct CohNetZip CohNetZip;
CohNetZip *coh_net_zip_create(void);
void coh_net_zip_destroy(CohNetZip *);
/* Original compressed payload convention: byte-aligned 32-bit command,
 * 32-bit raw-tail length, zlib tail; tiny (<12 byte tail) remains unchanged.
 * streaming=1 is required for ordered/reliable UDP; a malformed streaming
 * payload poisons that context and requires reconnect/recreate. */
CohStatus coh_net_zip_encode(CohNetZip *, int streaming, CohBytes input,
    uint8_t *output, size_t capacity, size_t *bytes);
CohStatus coh_net_zip_decode(CohNetZip *, int streaming, CohBytes input,
    uint8_t *output, size_t capacity, size_t *bytes);
size_t coh_net_zip_memory(const CohNetZip *);
typedef enum { COH_NET_IDLE, COH_NET_CONNECTING, COH_NET_WAIT_FINAL,
    COH_NET_CONNECTED, COH_NET_ENCRYPTION_REQUIRED, COH_NET_CLOSED,
    COH_NET_TIMED_OUT, COH_NET_CANCELLED, COH_NET_FAILED,
    COH_NET_DISCONNECTING } CohNetState;
typedef enum { COH_NET_DECODE_NONE, COH_NET_DECODE_HEADER,
    COH_NET_DECODE_BUDGET, COH_NET_DECODE_ALLOCATION,
    COH_NET_DECODE_STREAM } CohNetDecodeFailure;
typedef struct {
    CohNetDecodeFailure failure_kind;
    uint64_t compressed_bytes, declared_raw_bytes, output_budget;
    uint32_t normalized_command;
    uint8_t command_valid;
} CohNetDecodeReceipt;
typedef struct {
    uint64_t sent, received, retransmits, acknowledged, duplicates, malformed;
    uint64_t queue_limits, fragment_expirations, timeouts, unsupported;
    uint32_t tx_pending, rx_pending, fragment_groups;
    size_t storage_bytes, codec_bytes, high_water_retained_bytes;
    size_t owned_retained_bytes, owned_high_water_bytes;
    CohNetDecodeReceipt decode;
} CohNetDiagnostics;
typedef struct {
    unsigned version, ping_ms, max_retries;
    uint64_t connect_timeout_ms, idle_timeout_ms, fragment_timeout_ms;
} CohNetConfig;
typedef struct CohNet CohNet;
typedef struct {
    uint32_t id, ordered_id, payload_bits;
    uint8_t compressed, ordered;
    uint8_t payload[COH_NET_MESSAGE_MAX];
} CohNetMessage;
typedef struct {
    uint32_t id, ordered_id, payload_bits;
    uint8_t compressed, ordered;
    const uint8_t *payload;
    size_t payload_bytes;
    uint64_t generation;
} CohNetOwnedMessage;
/* callback borrows the frame for the call; success means the complete
 * datagram was accepted. It must not call back into this link. */
typedef CohStatus (*CohNetSend)(void *context, CohBytes datagram);
/* Optional Gate26 provider. peer/own are the original 64-byte CryptoPP DH
 * public values. Provider generates fresh private entropy, validates peer,
 * derives the shared64 MD5 and initializes the accepted Blowfish context.
 * Private/shared values must be erased by provider before returning. It must
 * not reenter this link or expose secrets in diagnostics. A callback alone is
 * not evidence of source DH compatibility or actual server interoperability. */
typedef CohStatus (*CohNetKeyExchange)(void *context,
    const uint8_t peer_public[64], uint8_t own_public[64], CohBlowfish *key);
CohNetConfig coh_net_default_config(void);
CohNet *coh_net_create(const CohNetConfig *);
/* IDLE only, 16 KiB..4 MiB inclusive. Default remains 16 KiB. This affects
 * next_owned() only and never permits a larger compressed wire message. */
CohStatus coh_net_set_decoded_budget(CohNet *, size_t bytes);
void coh_net_destroy(CohNet *);
CohNetState coh_net_state(const CohNet *);
/* IDLE only. required=1 rejects a clear SERVER_ACK; no fallback negotiation.
 * Null provider retains explicit encrypted-handshake unsupported behavior. */
CohStatus coh_net_set_key_exchange(CohNet *, CohNetKeyExchange, void *context,
    int required);
/* Emits source CONNECT(connect_id, requested_version), then handles clear
 * SERVER_ACK/CLIENT_ACK/FINAL transitions. Without a provider an encrypted
 * SERVER_ACK returns COH_UNSUPPORTED and ENCRYPTION_REQUIRED. With one, reply
 * stays clear, then receive decryption activates; send encryption activates
 * only after final SERVER_ACK_ACK. It never silently downgrades. */
CohStatus coh_net_begin(CohNet *, uint32_t connect_id, uint64_t now_ms);
CohStatus coh_net_queue(CohNet *, CohBytes payload, uint32_t bits,
    int reliable, int ordered, int compressed, uint64_t now_ms);
/* Same queue, packet IDs and original retry timing. A caller may reduce the
 * accepted retransmissions for this payload only (0..configured max_retries).
 * Existing queued packets and the link's configured policy are unchanged. */
CohStatus coh_net_queue_retries(CohNet *, CohBytes, uint32_t bits,
    int reliable, int ordered, int compressed, unsigned max_retries,uint64_t now_ms);
CohStatus coh_net_pump(CohNet *, uint64_t now_ms, CohNetSend, void *, CohCancel);
CohStatus coh_net_receive(CohNet *, CohBytes frame, uint64_t now_ms);
/* Output unchanged when no message. Decompression happens after sibling
 * merge and ordered delivery, matching source streaming dictionary order. */
CohStatus coh_net_next(CohNet *, CohNetMessage *);
/* One link-owned decoded allocation, published only after complete validation.
 * Release before another next call. Output is unchanged on every error.
 * Any close/cancel/timeout/disconnect/destroy invalidates and frees the view;
 * the owner thread must not retain or access it across another link call. */
CohStatus coh_net_next_owned(CohNet *, CohNetOwnedMessage *);
/* Clears the caller view even if cleanup already invalidated it (COH_STATE).
 * A stale/wrong generation can never release another outstanding allocation. */
CohStatus coh_net_owned_release(CohNet *, CohNetOwnedMessage *);
/* Source COMMCONTROL_DISCONNECT / ACK. Drops gameplay queues, then retries one
 * reliable disconnect until ACK or the configured connect-timeout budget.
 * The socket owner must continue pumping until CLOSED/TIMED_OUT. */
CohStatus coh_net_disconnect(CohNet *, uint64_t now_ms);
void coh_net_cancel(CohNet *);
void coh_net_close(CohNet *);
void coh_net_diagnostics(const CohNet *, CohNetDiagnostics *);
#ifdef __cplusplus
}
#endif
#endif
