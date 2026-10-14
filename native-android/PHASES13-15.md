# Phases 13–15: compressed audio, UDP transport and interactive source scene

This batch starts from physical Thor acceptance of gates 10–12 at
`0a5eed1a388ed53da1e19e7d6b2b571c067b82b9`. It builds one isolated
`org.coh.integrationprobe` APK, version `0.1.0-phases13-15`. The prior probes,
accepted native kernels, original source and device receipts stay unchanged.

| Gate | New execution | Qualification boundary |
| --- | --- | --- |
| 13 | Decode the authentic headset Ogg on Android using the original pinned Xiph codec revisions and unchanged source memory callbacks; compare and play the newly decoded PCM through accepted AAudio | One bounded source asset; reference PCM is used for comparison. Client sound scheduling, streaming, mixing and spatial audio remain separate. |
| 14 | Send and receive accepted clear/encrypted packet frames through two real IPv4 UDP loopback endpoints; malformed datagrams, endpoint identity, timeout, cancellation, close and reopen | Only `127.0.0.1` with ephemeral ports. Server login, authentication, ACK/reliability, commands and replication remain separate. |
| 15 | Feed current touch/right-stick input through accepted source editor-look and camera kernels into the authentic Atlas bench renderer | Controlled camera look over one authored branch. Full Atlas, character motion, collision, gameplay lighting and performance remain separate. |

## Source and host evidence

The [decoder contract](decode/README.md) pins Ogg 1.3.6 and Vorbis 1.3.7 to
the original dependency revisions. The four memory callback bodies and
`ov_read(...,0,2,1)` contract remain unchanged. Original codec sources are
verified before a separately audited unsigned-shift overlay removes inherited
undefined behavior without changing the observed PCM. BSD notices ship in the
APK. Decoder output owns its COHAUD11 blob and is the only playback input.

The host source oracle is byte-identical to the new pinned-codec output.
Against the earlier accepted system-codec reference, 20 of 36,336 signed16
samples differ by one LSB; maximum error is 1 and RMS error is
`0.023460995672`. The fixed one-LSB comparison bound was declared before
testing. Metadata and complete frame/sample counts remain exact. The
[sanitized proof](decode/host-proof.json) includes all 12,930 truncated prefixes,
CRC-valid hostile identification/payload cases, callback bounds and repeated
decode/compare/release. Android sample errors are measured separately.

The [UDP contract](transport/README.md) reuses accepted bitstream, framing and
Blowfish kernels. A successful host run exchanges 84 real UDP datagrams,
checks 66 clear/encrypted frames and 18 expected rejections, closes/reopens
worker-owned sockets, and proves cancellation during a blocked native poll.
Normal checks and explicit Home waits have separate cancellation receipts.
Generic parity/backend failures cannot become harmless when Home occurs later.
The [host proof](transport/evidence/host-proof.json) contains sanitizers,
threaded lifecycle cases, actual descriptor-error injection and negative controls.

The [interactive scene contract](interactive-world/README.md) reuses the
accepted world renderer and precise shader sources directly. Each fresh
context checks six original CPU/GPU camera references. Current input then
drives native matrices for 450 rendered frames. Every signed direction needs
CPU motion, GPU parity and changed-image evidence. Released input must settle.
The explicitly declared adapter limits pitch/yaw changes to ±12 degrees about
the authored camera and preserves immediate reversal at the bounds.

The host camera proof compares 4,106 original editor steps and 114,968 original
camera components exactly, checks transactional malformed inputs and catches
reversed-pitch/disconnected-yaw controls. Another 16,007 ASan/UBSan checks
exercise the accepted input-to-camera pipeline. These are source proofs;
Android callbacks and GPU execution require the combined device report.

## Combined application

The screen has one authentic scene, decoded sound playback, native loopback
checks and a single immutable JSON export. Its installed APK version, byte
count and SHA256 are recorded. A single render worker owns each Surface/EGL
lifetime and consumes input once per frame. The UI reads its cached sample.
Native request tickets and Java view epochs reject queued or completed stale
work. Genuine numeric/GL/backend failures remain sticky through cancellation.

**Home check** starts decoded audio and a real empty UDP poll together. The
user waits for READY and presses Android Home while audio is active. Acceptance
requires cancellation/cleanup of those exact runs, cleared input, fresh native
checks, a fresh successful rendered view and complete decoded playback after
return. Resizing, recreating and Reset invalidate current view proof. The
document picker cannot replace genuine Home evidence or alter its frozen export.

Build, lint, package identity and Android 13 emulator qualification are run by
the dedicated native integration workflow. Physical Thor stick behavior and
audibility remain separate observations. See the
[one combined test sequence](integration-probe/THOR-TEST.md).
