#ifndef COH_COMBINED_INTEROP_NETWORK_H
#define COH_COMBINED_INTEROP_NETWORK_H
/* Capture diagnostic only: one genuine pre-ACK INITIAL payload, not a stream
 * archive. The 88-byte little-endian header precedes at most 64 KiB of bytes:
 * magic COHIRP01; u32 headerBytes,payloadBytes; u64 logicalBits,postCommandCursor,
 * appearanceSelectorCursor; u32 byteAlignedMode,selectedCostumeIndex (UINT32_MAX
 * if not observed),CLIENTBodyPartCount,normalizedCommand; payloadSHA256[32]. */
#define COH_INITIAL_REPLAY_BYTES 65536u
#define COH_INITIAL_REPLAY_HEADER_BYTES 88u
#endif
