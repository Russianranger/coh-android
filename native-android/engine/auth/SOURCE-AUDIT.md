# Source audit — authentication and session boundaries

All source references below are pinned by SHA256 of LF-normalized content in
`source-pins.json`, from integration checkpoint
`2c32f5686246fa28cf3341e8e89dd1014eacd5f4`. No packet capture or live-server
evidence is available in this batch.

| Source | Contract recovered |
| --- | --- |
| `libs/UtilitiesLib/src/network/crypt.cpp`: `dh_hex_params`, `cryptMakeKeyPair`, `cryptMakeSharedSecret` | CryptoPP DH BER parameters encode a 512-bit modulus and generator2; key/public/shared lengths are64 bytes; `Agree(...,true)` validates public material |
| `libs/UtilitiesLib/src/network/net_link.c`: `netAckConnect`, control ACK cases | SERVER_ACK and CLIENT_ACK carry packed encryption flag followed by512 public-key bits; MD5(shared64), Blowfish key; clear CLIENT_ACK/final before sender encryption enable |
| `libs/UtilitiesLib/src/network/blowfish.c`: `cryptBlowfishInitU32` | Little endian original copies MD5 digest bytes directly to Blowfish key; native uses the same bytes independently of host endianness |
| `Common/auth/auth.c`: `authAllocPacket`, `authSendPacket`, `authSetKey`, Blowfish functions | Separate TCP AuthServer protocol; U16 inclusive frame size, command byte, fixed20-byte global Blowfish key, padded XOR checksum plus reserved DWORD |
| `Common/auth/auth.c`: `authEncryptLineage2` | Four32-bit multiply/add operations modulo2^32 plus byte chaining; native removes alignment/strict-alias/signed-overflow assumptions |
| `Game/src/clientcomm/authclient.c`: `acSendLoginMD5` | Normalize account; source password transform; MD5(hash16 + signed-decimal challenge); CryptoPP-swapped salted SHA512;94-byte plaintext; RSAES-OAEP-SHA1; subscription+flags |
| `crypt.cpp`: `cryptRSAEncrypt`, `cryptSHA512Final`, `cryptAdler32` | OAEP SHA1 and split blocks, SHA512 U64 swapping on little endian, CryptoPP Adler digest bytes interpreted as a little endian U32 for account salt |
| `Common/auth/auth.h`, `authconn.h` | Explicit protocol versions and auth command IDs |
| `authclient.c`: `acGetProtocolVer`, `acGetLoginOK`, `acGetPlayOK`, `acGetSendServerList` | Variable RSA parameters, session/update bytes, play handoff, shard entries and version-dependent names |
| `AuthServer/src/SocketServerEx.cpp` | Server emits RSA exponent+modulus, encrypted global framing and1152-bit RSA; secure login consumes94-byte plaintext |
| `AuthServer/src/util.cpp`, `IOBuffer.cpp` | Server pads pooled buffers without zeroing padding/reserved DWORD; native receiver must accept residue after checking checksum |
| `Game/src/clientcomm/dbclient.c`: `dbConnect` | Separate encrypted NetLink UDP; full DB login also needs executable checksum/version,128 auth bytes, cookie, zipped system spec and keyed access tail. Not silently fabricated by this module |
| `dbclient.c`: `dbChoosePlayer`, `dbOrMapConnect` | Character slot/name request then link/map/two IPs/UDP/TCP/cookie; this batch implements the bounded handoff payload parser only |

Protocol0 is treated as global to match the source. Although the checked-in
`acGetProtocolVer` old allow-list omits Ouroboros versions, the same client's
login/server-list code and the actual AuthServer support them. The new parser
admits only the explicit global/reactivation/Ouroboros versions implemented
here; it does not infer compatibility for future values.

AuthServer requires the source Windows/MSVC/ODBC/database deployment and is not
running in this execution environment. A fake-auth profile or a generated
fixture cannot qualify authentication. The implementation's host oracle and
crypto tests remain independent of any live AuthServer claim.
