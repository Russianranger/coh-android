# Gate 12: bounded offline source packet framing

This gate executes a new Android-native byte-safe packet/bitstream kernel. It
uses the accepted fixed-width Blowfish core. It has no socket API and does not
establish a server connection or qualify authentication, character login,
reliability, entity replication or gameplay.

The selected UtilitiesLib NetLink profile has `hasDebugInfo=0`, `sib_count=0`,
no piggyback acknowledgements, `compressionAllowed=0`, and `orderedAllowed=0`.
Those are real branches in the original `pktWrap` implementation. Support for
newer compression/ordering negotiation, typed debug fields, sibling assembly,
ACK handling and reliable retransmission remains separate work. The kernel
treats the payload as opaque bytes plus a logical bit length; it does not claim
to validate a game command. Fixture payloads begin with a valid packed zero
command so the original producer's command peek stays within bounds.

## Frozen wire contract

| Field | Selected encoding |
|---|---|
| Total logical bit length | Four little-endian bytes, unencrypted |
| Checksum | Four CryptoPP Adler32 digest bytes, high to low |
| Debug flag | One zero bit |
| Packet ID | 32 bits, least significant bit first |
| Sibling count | `BitsPack(1,0)`, one zero bit |
| ACK count | `BitsPack(1,0)`, one zero bit |
| Payload start | Byte aligned at offset 13 |
| Payload | 1–9,600 logical bits, up to 1,200 bytes |
| Final physical length | `4 + round_up_8(ceil(total_bits/8) - 4)` |
| Checksum coverage | Bytes 8 through the end, including padding |
| Optional encryption | Blowfish from offset 4 through the padded end; explicit little-endian word loading |

`BitsPack` emits an all-one sentinel at the current width, subtracts that
sentinel from the value, doubles the width up to 32, and emits the final
remainder. The native parser defines all 32-bit shifts and rejects accumulated
packed values above `UINT32_MAX`. It checks every cursor/length before access,
works with unaligned byte buffers, and preserves caller output on failure.
Bit calls preserve storage outside the requested logical span. Byte parity
uses zero-initialized producer storage, as the source oracle and compiled
goldens do; incidental legacy word stores into unused future storage are
deliberately excluded from the checked API contract.
The absolute frame cap is 1,472 bytes from the original packet header; the
selected payload cap of 1,200 is a bounded probe policy below the original
1,264-byte send-buffer limit.

The original sender reused padding bytes and explicitly comments on sending
uninitialized data. This producer initializes padding to zero. The original
producer oracle is supplied the same defined zero-filled backing buffer; this
qualifies its framing calculation without reproducing stale process memory.
The receiver accepts checksum-valid nonzero padding and retains the final
physical payload byte, including any unused bits, as the original array copy
does. Its exact padded-length rule is deliberately stricter than the original
UDP receive path's allowance of up to seven extra bytes.

## Evidence and source boundary

`tools/protocol_fixture/source-pins.json` pins ten complete original files and
24 unchanged function bodies. Game source is pinned to repository revision
`61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d`. CryptoPP's Adler32 implementation is
pinned to the exact `CryptoPP.cmake` dependency revision
`b5242667a24e3db8e4600e77b2e502ef204e5280`. Its `TruncatedFinal` byte order and
the unchanged `cryptAdler32` wrapper prevent confusing the digest bytes with a
little-endian numeric Adler32 value.

`prepare.py --check` executes unchanged original bit/packet/ACK dispatch and
Adler bodies on trusted, aligned, zero-filled Linux host buffers. Minimal
struct/type shims select the documented profile; unsupported typed/debug and
auto-length helpers trap if reached. The original bit writer includes x86
aligned word stores and legacy signed-shift behavior, so this observational
host oracle is compiled at `-O0` without sanitizers and is never shipped. It
does not claim a complete original Windows process or a defined C model for
its unsafe paths. Wei Dai's original Adler32 source is public domain; the
accepted Blowfish file retains Paul Kocher's original author notice.

An independent Python bit-list implementation, zlib Adler32, and OpenSSL
Blowfish build the compiled goldens. Sixteen original plaintext frames match
1,736 bytes; 32 clear/encrypted wire fixtures and 66 packed integer goldens
match. Eight independently checksummed/encrypted negative frames exercise
unsupported debug/sibling/ACK profiles and packed-overflow rejection.

The same compiled selftest runs on Android and under host ASan/UBSan. It checks
32 wire fixtures at eight byte alignments, 66 packed goldens, all 0–32-bit
field widths at eight bit offsets, exact-allocation truncations, corruptions,
negative profiles and transactional failures. Host-only work adds 12,000
exact-allocation raw/mutated frame cases. Host and Android receipts remain
separate; LeakSanitizer is disabled on the restricted host.

Run the source oracle with:

```sh
python3 native-android/tools/protocol_fixture/prepare.py --source-dir SOURCE_DIR --check --output protocol-original-proof.json
python3 native-android/tools/protocol_fixture/check.py --output protocol-host-proof.json
```

`SOURCE_DIR` contains the ten exact files listed in the pin manifest. CI copies
checked-out original game files and separately retrieves the pinned CryptoPP
file with a bounded download and a checked LF-normalized SHA256.
