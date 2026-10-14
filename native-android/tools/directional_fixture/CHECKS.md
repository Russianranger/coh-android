# Directional source qualification

`check.py` compiles unchanged original `seqProcessInst`, `seqSearchInterrupts`,
`seqAInterruptsB`, `getSetBits`, `seqSetMove`, `seqStep`, `seqCycleFrame`,
`seqGetAnimScale`, and `seqGetMovementSpeedAnimScale`. It supplies portable
container/platform stubs and parses the selected move declarations directly
from hash-pinned source data. The native implementation is compiled separately.

The 12-move graph includes all four Pres and cycles, shared RunPost, Ready,
Idle_Walk_Post and Idle_Ready. Wretch has no synthetic IDLE state. The forced
early-stop path therefore displays Idle_Ready before its failed cyclic IDLE
requirement returns it to Ready. The omitted random Ready2 graph is replaced
with a deterministic selected Ready loop while preserving ComplexCycle's
effect on phase retention. Other movement modes, attacks, footfall FX and
server authority are excluded.

The source's actual state indices are FORWARD=1, BACKWARD=2, STEPLEFT=3,
STEPRIGHT=4 and IDLE=12. Candidate cache order follows authored move order
within each ascending state bit. Tied priorities use the original
anim_incrementor, rather than a substitute dominant-axis policy.

`sampler_check.py` runs the accepted original raw-key, morphology and matrix
functions together with original `animateGfxNodeBone` and
`animInterpNodeWithLastPosition`. It checks every Huge hierarchy node while
reproducing independent rotation/translation blending flags, early blend
termination, source double-literal threshold comparisons, retained last
translations before SmoothSprint, and male-parent motion retargeting.

The source files are acquired at:

- [Code revision](https://github.com/Thunderspies/CityOfHeroes/tree/0b75ade0c801735e10c5798f641948a45cc50488)
- [Data revision](https://github.com/Thunderspies/i24/tree/d51533ec8e6a9cf726b9214968077a05fdcf19f3)

The original `seqregistration.c` uses CP1252 bullet comments. Connector text
retrieval converted those two bytes to UTF8, creating a four-byte difference
in the initial local cache. The directional manifest now uses the canonical
34,480-byte original file, SHA256 `9ccf1b75e4def1a549e7bc2adc9227548111140807ab969ededacc031bdddb98`,
matching the earlier accepted actor pin. Its Git blob SHA
`44ff63fd244e88afb5f6e64304a233e4a2bbe6fa` independently confirms the exact
canonical bytes. All 23 source inputs were checked against their repository
blob identities; byte/hash validation occurs before text decoding. Both
reused scaleBone/unscaleBone function hashes remain unchanged, as do earlier
source pins and evidence.

## Reproduce

Acquire the pinned source files and corpus using the fixture workflow, then:

```sh
python native-android/tools/directional_fixture/check.py \
  --fixture /absolute/path/locomotion.bin \
  --source-directory /absolute/path/directional-source \
  --corpus /absolute/path/directional-corpus \
  --morph /absolute/path/morph.bin \
  --output /absolute/path/host-directional-proof.json

python native-android/tools/directional_fixture/sampler_check.py \
  --fixture /absolute/path/locomotion.bin \
  --source-directory /absolute/path/directional-source \
  --corpus /absolute/path/directional-corpus \
  --morph /absolute/path/morph.bin \
  --output /absolute/path/host-directional-sampler-proof.json
```

The first driver enables ASan, UBSan and LSan when `--morph` is supplied.
`--disable-leak-sanitizer` is an explicit local override for environments that
restrict `/proc`/ptrace; ASan and UBSan still execute. CI should use the default.

## Local result

On the integrated runtime, 4,470 graph ticks produced 31,290 exact source
comparisons with zero error; 537 equal-priority counter changes were exercised.
Ten invalid graph inputs failed without mutating state. The sanitizer driver
passed 128 exact header truncations, 20,000 step/sample/reset sequences and
6,396 full-bundle byte mutations. Local LSan was disabled for the sandbox's
`/proc` restriction, as recorded in the proof.

The sampler compared 1,165 poses across all 60 reachable bones. All 279,600
quaternion components and 209,700 flag/clock components matched exactly.
Local-position error was at most 2.3842e-7 source units; hierarchy error was
at most 9.5368e-7. Twelve invalid sampler inputs preserved output/cache bytes.

These are host scalar qualifications. They do not establish Android display
performance, physical Thor acceptance, full original-client execution, or
live server interoperability.
