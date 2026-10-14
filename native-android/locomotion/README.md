# Authored offline locomotion

`COHLOCO1` keeps its qualified forward-only Ready/RunCycle/RunPost behavior.
`COHLOCO2` extends the same native session client with authored Huge RunPre,
backward and lateral Pres/Cycles, interrupted-Pre Idle_Walk_Post and Idle_Ready,
and source transition interpolation. Both envelopes preserve unchanged original
encoded animation bytes in validated `COHRIG01` views; neither bakes pose palettes.

The source-defined selected ground graph contains:

| Move | Original clip | Authored range | Completion/release |
| --- | --- | --- | --- |
| Ready | Huge/Skel_ready | 1–60 | Deterministic Ready loop |
| RunPre | Huge/run | 18–25 | RunCycle / Idle_Walk_Post |
| RunCycle | Huge/run | 1–25 | Loop / RunPost |
| Run_Back_Pre | Huge/runback | 1–24 | Run_Back_Cycle / Idle_Walk_Post |
| Run_Back_Cycle | Huge/runback | 1–24 | Loop / RunPost |
| Run_Left_Pre | Huge/run_left | 15–25 | Run_Left_Cycle / Idle_Walk_Post |
| Run_Left_Cycle | Huge/run_left | 1–25 | Loop / RunPost |
| Run_Right_Pre | Huge/run_right | 1–25 | Run_Right_Cycle / Idle_Walk_Post |
| Run_Right_Cycle | Huge/run_right | 1–25 | Loop / RunPost |
| RunPost | Huge/postrun | 1–23 | Ready |
| Idle_Walk_Post | male/walk | 47–48 | Idle_Ready |
| Idle_Ready | male/skel_ready2 | 1–60 | Ready when IDLE requirement fails |

Huge's source TypeDef explicitly inherits male. Parent fallback clips use their
unchanged male animation base while runtime attaches their encoded tracks to the
actor's Huge hierarchy, computes source frame-zero track-to-Huge-base deltas,
and retains the accepted Huge inverse-bind translations and Wretch morphology.
Wretch's selected offline state sets HUGE without IDLE: interrupted Pres briefly
visit Idle_Ready and then return Ready. No fictional directional post clips exist.

`coh_locomotion_step_directional` accepts desired local input flags FORWARD1,
BACKWARD2, STEPLEFT4 and STEPRIGHT8, and the length of **actual achieved movement**.
The source interruption member groups and priority ties govern quick taps,
reversals and diagonals. Equal-priority ties use the source incrementor and
ascending original state-bit order. Strict authored ends use `frame > last`,
and cyclic transitions preserve phase only under source `seqSetMove` conditions.

Wall contact retains desired input flags, as original `pmotionSetState` derives
these from input velocity. Completely blocked motion still animates at source
minimum rate `.25`, and release enters the appropriate early or normal stop.
Actual displacement divided by unscaled engine TIMESTEP and authored MoveRate
(`.7`, backward `.525`) gives MoveScale clamped `.25..2`. Predictable character
size scaling separately caps inverse height `.5..1.5`. HIPS bone0 uses original
SmoothSprint Y reference3.3 above rate1.05.

`coh_locomotion_sample_directional` maintains a separate bounded display cache.
Source default interpolation is5 engine frames (`seqload.c`), while RunPost is8.
It recursively blends the last displayed local pose, uses source shortest-arc
normalized quaternion interpolation, independent per-bone rotation/translation
convergence flags, and then composes the morphology-adjusted Huge hierarchy.
The display cache stores the pre-SmoothSprint local pose, matching original
source operation order. Reset/restoration clears this cache; it never changes
movement coordinates or stores authoritative gameplay state.

The API caps each simulation/render increment at3 engine frames (.1seconds).
Callers own pause/resume clocks and persistence; long lifecycle backlogs are not
advanced. Parsed views borrow immutable caller-owned bytes. The new canonical
bundle is147103B, below its512KiB bound; heap growth and per-frame asset loading
are not required.

This remains a bounded offline adapter. Full Ready2 random idles, combat, weapon,
swim, airborne graphs, footfall PlayFx and authoritative live-server sequencing
remain future work. Grounded WALK collision is integrated separately. Host
qualification executes unchanged hash-pinned original selected sequencer kernels,
encoded-key samplers and interpolation functions, plus standalone ASan/UBSan
truncation/mutation and repeated render/state checks. Physical device acceptance
is a separate Thor report gate.
