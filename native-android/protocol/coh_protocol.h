#ifndef COH_PROTOCOL_H
#define COH_PROTOCOL_H
#include <stddef.h>
#include <stdint.h>
#include "coh_native_core.h"
/* Selected legacy NetLink v0 framing profile: untyped, uncompressed,
 * unordered, no siblings and no piggyback acknowledgements. No socket API. */
#define COH_PROTOCOL_FRAME_MAX 1472u
#define COH_PROTOCOL_PAYLOAD_MAX 1200u
typedef struct { uint8_t *data; size_t capacity, bit_length, cursor; int writing; } CohProtocolBits;
typedef struct { uint32_t packet_id, payload_bits; size_t payload_bytes; uint8_t payload[COH_PROTOCOL_PAYLOAD_MAX]; } CohProtocolPacket;
typedef struct { uint32_t passed, checks, wire_cases, bit_cases, malformed_cases, unaligned_cases; } CohProtocolProof;
int coh_protocol_bits_init(CohProtocolBits *, uint8_t *, size_t, size_t bit_length, int writing);
/* Failed calls preserve cursor/output. Width is 0..32; packed width 1..32.
 * Only the requested bit span is changed. Initialize producer storage to zero
 * for source byte parity; legacy incidental stores beyond the span are omitted. */
int coh_protocol_write(CohProtocolBits *, unsigned width, uint32_t value);
int coh_protocol_read(CohProtocolBits *, unsigned width, uint32_t *);
int coh_protocol_write_pack(CohProtocolBits *, unsigned min_width, uint32_t);
int coh_protocol_read_pack(CohProtocolBits *, unsigned min_width, uint32_t *);
/* Both functions preserve all caller outputs on failure, tolerate unaligned
 * byte buffers, and have a fixed 1472-byte upper bound. Zero padding is a
 * deliberate deterministic producer policy; the source reused stale bytes. */
int coh_protocol_encode(CohBlowfish *, int encrypted, uint32_t packet_id,
    const uint8_t *payload, uint32_t payload_bits, uint8_t *frame, size_t capacity, size_t *frame_bytes);
int coh_protocol_decode(CohBlowfish *, int encrypted, const uint8_t *frame,
    size_t frame_bytes, CohProtocolPacket *);
int coh_protocol_selftest(CohProtocolProof *);
#endif
