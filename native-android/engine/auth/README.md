# Native authentication protocol building blocks

This additive module implements source-derived protocol pieces. **It has not
authenticated to an AuthServer, retrieved a real character, or entered a live
MapServer. Gate 26 remains incomplete.** No credential, password, private key,
session token, or encrypted authentication payload is included in diagnostics.

## Implemented scope

| Component | Evidence and limit |
| --- | --- |
| NetLink DH | Exact original DER group, generator 2, unsigned 64-byte big endian keys and shared secret; MD5 of all 64 secret bytes becomes existing Blowfish key |
| Crypto provider | OpenSSL 3 host backend: secure RNG, constant-time private exponentiation, peer range and subgroup validation, MD5, SHA512, RSAES-OAEP SHA1/MGF1-SHA1; not a stock Android dependency |
| Auth TCP framing | Global-auth fixed Blowfish key, little endian inclusive U16 length, XOR checksum, bounded incremental stream assembler; sockets/lifecycle are caller-owned and not implemented here |
| Auth response bodies | Bounded hello, login OK, play OK and shard-list parsing with explicit protocol versions; protocol 0 maps to global as source does |
| Login request | Global/reactivation/Ouroboros account normalization, Lineage2 password transform, MD5 challenge, salted SHA512 and RSA-OAEP envelope; this is a request builder, not login acceptance |
| Selection requests | Source server-list and about-to-play serializers, group requests only for Ouroboros protocol 2 |
| Map handoff | Source `dbOrMapConnect` seven-field payload, packed and already-decompressed byte-aligned profiles; preserves both addresses, checks ports and failure cookies |

USA and Asia authentication, queue handoff messages, unsupported protocol
versions, and oversized fields fail explicitly. This module does not implement
the complete DB login packet, executable/version admission policy, character
list decoding/selection, MapServer initial world message, or connection state
machine. All parsers preserve output on error. They cannot themselves mark a
connection authenticated.

The incoming AuthServer buffer may contain previous pooled-buffer bytes in
padding and its reserved trailer DWORD. The decoder checks the source checksum
while accepting that residue. Outbound data always zeroes padding and the
reserved DWORD. A parser accepts at most seven trailing padding bytes. The
original `authGetPacket` ignored checksum failure; this adapter rejects it.

For the login request, the account must fit 14 ASCII bytes before normalization
and the password 16 bytes; oversize input is rejected rather than silently
truncated. Leading/trailing ASCII spaces are removed and ASCII letters lower
cased. This is the documented narrow account profile. The original U32 session
challenge passed to `itoa(int)` is interpreted as signed decimal, including
values with the high bit set. `cryptSHA512Final` reverses each eight-byte digest
word on little endian source hosts; that transformation is preserved.

## Android crypto integration contract

`coh_auth.c` compiles with the stock NDK and has no OpenSSL dependency.
`coh_auth_openssl.c` is a separate optional host backend requiring OpenSSL 3.
The integrated Android link must install a reviewed `CohAuthCrypto` provider or
remain explicitly unavailable for encrypted sessions. It must never silently
downgrade encryption or treat a missing provider as success. Do not use Android
private platform `libcrypto` APIs.

Provider `shared` must validate subgroup membership and private range, perform
constant-time private exponentiation, and leave output unchanged on error.
Providers use secure randomness; the original timing-seeded CryptoPP LC_RNG is
not reused. All DH values are fixed 64-byte big endian bytes, not host integers.
The caller wipes private keys and provider-owned contexts on cancel/close.

Example transport integration: generate local pair for encrypted SERVER_ACK,
send CLIENT_ACK with the local public key under the previous clear framing,
derive the Blowfish context, then admit encrypted receive frames; activate
encrypted transmission only after SERVER_ACK_ACK, as the source does. The
transport must bound retries, handle repeated control packets, and clear its
key state on disconnect. A successful local handshake fixture is not evidence
of actual source-server interoperability.

## Qualification

```sh
python native-android/engine/auth/check.py --source-root . --sanitize \
  --ndk /absolute/path/android-ndk-r28c \
  --output native-android/engine/auth/evidence/host.json
```

The driver verifies pinned original-source hashes, extracts the original
Lineage2 transform and Auth framing function, and compares independently
constructed fixtures. It compares all 94 login plaintext bytes in 80 cases,
including signed challenges; 64 DH secrets against Python modular exponentiation;
and 140 clean/dirty original framing cases. New native tests additionally cover
10,000 malformed inputs, truncated messages, subgroup-invalid keys, genuine
randomized RSA-OAEP encrypt/decrypt with disposable keys, output preservation,
both map handoff profiles, stream segmentation, checksum rejection, limits,
and unsupported versions.

ASan address checks and UBSan pass. LeakSanitizer is disabled in the recorded
run because the execution environment blocks `/proc` thread inspection; no leak
qualification is claimed. `evidence/host.json` separately records portable
ARM64 object compilation. This module has no emulator, Thor, real server login,
or real character-selection acceptance.

Next required work: reviewed Android crypto provider, Auth TCP connection and
state/lifecycle integration, complete DB login with version policy and character
messages, explicit MapServer handoff integration, and authorized disposable
Auth/DB/Map services plus synthetic test accounts for actual interoperability.
