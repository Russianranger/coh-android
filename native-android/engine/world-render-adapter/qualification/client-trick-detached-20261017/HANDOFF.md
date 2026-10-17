# Detached exact Trick subtree

Source commit `035357a0d`; host receipt SHA256 `55b11b9b3093ad72d8cfdc2858bafba876fe8369a1f3b56e68e571715e098ff5`. Eight new source/test/contract files; existing whole-cache reader/API unchanged.

Retained exact suffix: original offset12,769,880, bytes767,172, SHA256e82e825340e7abb16ccb3d34a756a991b73eeab33bc291021a608822620c65a5. It contains the original count and all3,644 length-prefixed rows/children with no reencoding. New host64 owner occupies956,892bytes total (189,720metadata +767,172exactbytes), compared with old208,600metadata plus a13,537,052-byte cache lease. Source wholebody SHA remains cf9595e54bc65a40d2dddc3a5a13c475d7c2ce07a96420e6001b0e2312926bc1. Full source and copied suffix hashes are both verified before publication; translated offsets preserve names/files/age/order/children and historical generation provenance.

Release/ASan/UBSan each pass70,060controls including complete unchanged original typed-reader parity for3,644 raw/projected rows,106StAnim and273AutoLOD children. Checked mechanical core generation preserves the frozen decoder/getters; the independent production object exposes only the nine intended public functions. Exact byte equality to the original suffix, budget boundaries, both digest failures, allocation failure, cancellation stages, source/hash/generation refusal, aliases and atomic handle transfer are exercised.

Fixture staging configures16MiBloader total/reservation,64MiBexternal,1MiBowned cap and96MiBaggregate cap. Charged preparation total84,875,740bytes. This is a named source-module reservation, not processRSS or an allocator/system library closure. Peak staging includes the old source and full cache, plus the new allocation; it does not assume an instantaneous in-place shrink. Same loader reservations are deliberately charged twice. Native64 metadata sizes are observations; other target layouts need their own build/execution qualification.

Only final success consumes/releases the old Trick owner; every failure preserves it. No loader pin remains in the detached owner. TexOpt still pins the wholecache independently: test trim while TexOpt is live preserves13,537,052residentbytes. After TexOpt retires, trim returns resident bytes to0 and allocatedbytes to the empty post-mount baseline, then the loader/provider are destroyed and detached views remain valid. **Do not count cache savings while any other owner still pins it.** This tranche does not detach TexOpt or discard needed material inputs.

No animation/AutoLOD resource binding, activeCLIENT generation, material/world authority, Android execution or physical qualification. LeakSanitizer remains disabled for the established container limitation. All source/body dependencies are hash-bound before helper execution and readmitted after the qualification.

Reproduce using a fresh output path:

```sh
mkdir -p /dev/coh-build-scratch
TMPDIR=/dev/coh-build-scratch python native-android/engine/world-render-adapter/check_trick_detached.py --actual-cache /workspace/scratch/9174d12e2a11/tex-parser-authentic/tricks.bin --output /tmp/FRESH-trick-detached.json
```
