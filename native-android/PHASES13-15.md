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
drives native matrices for 180 rendered frames. Every signed direction needs
CPU motion, GPU parity and changed-image evidence. Released input must settle.
The explicitly declared adapter limits pitch/yaw changes to ±12 degrees about
the authored camera and preserves immediate reversal at the bounds. Each
bounded diagnostic round initializes this adapter from its first source
sample and recenters the authored view; persistent gameplay camera state is
outside this gate.

The host camera proof compares 4,106 original editor steps and 114,968 original
camera components exactly, checks transactional malformed inputs and catches
reversed-pitch/disconnected-yaw controls. Another 16,007 ASan/UBSan checks
exercise the accepted input-to-camera pipeline. These are source proofs;
Android callbacks and GPU execution require the combined device report.

The first hosted Android attempt completed 367 of 450 preview frames before
the unchanged 25-second deadline. All observed source/GPU comparisons, four
directions and cleanup passed. The bounded preview now renders 180 frames,
retaining fifteen scheduled GPU/image comparisons, immediate direction checks
and all six independent baseline cases. This is diagnostic coverage rather
than a frame-rate claim. The [first failure receipt](evidence/phases13-15/first-android-failure.json)
preserves the original result.

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
Preparation pauses the repeated preview and waits for worker-owned graphics
cleanup before starting either Home worker. The live screen shows a compact
summary; full immutable JSON snapshots are saved by one coalescing writer and
the detailed export retains its fixed pre-picker bytes.

The second hosted attempt passed scene directions, decoded playback, actual
Surface resize and recreation, but reached `onPause` 4.410 seconds after READY.
Both native workers had already finished. The app correctly withheld the
interruption receipt and recorded zero session failures. Logcat showed slow
main-thread rendering of the full report. The
[second failure receipt](evidence/phases13-15/second-android-failure.json)
preserves this timing miss. Qualification still requires interruption of the
exact active audio and blocked-poll runs, followed by their cleanup and fresh
foreground execution; a clean timeout or early cancellation is retryable.

The third hosted attempt exposed an automation error: its horizontal button
row was still moving when a tap intended for Resize activated Home check.
The app recorded the actual action and did not invent a Resize or Home pass.
The [test-driver failure receipt](evidence/phases13-15/third-android-test-failure.json)
preserves the result. Real button taps now wait for stable visible bounds and
scroll position across fresh snapshots, then still require the actual matching
button callback.

Build, lint, package identity and Android 13 emulator qualification are run by
the dedicated native integration workflow. Physical Thor stick behavior and
audibility remain separate observations. See the
[one combined test sequence](integration-probe/THOR-TEST.md).

## Qualified package and physical Thor acceptance

Source `e8d4b80b21088992bcbfa403f71bae3138a49e70` passed the
[integration workflow](https://github.com/Russianranger/coh-android/actions/runs/38603481231)
and the portable-core workflow. The
[qualification receipt](evidence/phases13-15/qualification.json) binds the
downloaded artifact, both signed APKs and the original reports to that source.
The ARM64 package is `CoH-Native-Integration-Probe-0.1.0-arm64.apk`, 750,186
bytes, SHA256 `1a2b3da7fedad2f3b78ec5673ce45e649e4e9cb5616f120c77a7770941c4ccba`.

The installed Android 13 x86_64 package passed three native checks, seven
180-frame scene rounds across two actual sizes and generations, all four
signed CPU/GPU/image directions, two complete decoded sound sequences and
seven real button taps. The genuine Home cycle interrupted decoded playback
after 13,824 submitted frames and a blocked native UDP poll, stopped/closed
the stream, closed both sockets, cleared input and reopened all subsystems.
Reset and the actual document picker required fresh current-view evidence.
The 132,040-byte exported JSON matched its frozen pre-picker hash. Session
failures, comparison mismatches and GL/EGL/backend errors were zero.

All 140 Java receipt, ordered-writer and tap-measurement host checks passed.

Physical AYN Thor Android 13/Adreno 740 acceptance passed on October 14. The
[Thor qualification receipt](evidence/phases13-15/thor-qualification.json)
audits the immutable
[uploaded report](evidence/phases13-15/COH-NativeIntegration-20261014-142958.json)
and the user's **All passed** confirmation. Its observed installed APK size and
SHA256 match the qualified ARM64 build exactly, and complete fixture metadata
matches the qualified emulator report. The original emulator checks were
retained, adapting only the physical device, controller and audible-confirmation
expectations.

Four native runs passed 108 decoder, 3,636 source-input and 1,320 real UDP
checks, exchanging 336 datagrams in each direction. The on-device decoder
compared all 36,336 signed16 samples per decode with maximum error one LSB
and only five differing samples. Seventeen complete source-renderer rounds
covered 3,060 frames across two actual sizes and two view generations. Four
rounds independently witnessed all four signed CPU/GPU/image directions;
released input settled for 245 frames. Both physical stick masks reached
15/15. Four complete decoded sound sequences played, with audible confirmation
linked to completed runs. All recorded comparison mismatches, session failures
and GL/EGL/audio/UDP backend errors were zero.

The first Home attempt occurred after its sound and bounded UDP wait had
finished; it remained a clean retry rather than interruption proof. The second
attempt measured a genuine pause while decoded audio run 4 and blocked UDP
wait run 2 were active. Audio cancelled after 29,391 submitted frames and
stopped/closed its stream; the actual blocked poll interrupted and both sockets
closed. Input cleared at pause. Fresh source checks, current-view rendering
and complete decoded playback passed after return. Resize and recreation
were also measured in the physical export.

Gates 13–15 are physically accepted within this isolated integration scope.
Full Atlas loading, persistent gameplay camera state, character movement,
collision, server interoperability, full audio scheduling/mixing and sustained
performance remain separate development milestones. The four complete audio
plays recorded four total xruns; underrun-free sustained audio is not claimed.
