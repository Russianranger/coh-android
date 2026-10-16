# Combined 0.1.7 continuation handoff

Target and publication branch: **native-android only**. Runtime source
`fe037348c9a184d98aff96f0803b2afc0e631b71`, tree
`93390b9fb6f765e4b864669eac66995e56c1f955`. The final evidence-only commit
is discoverable from branch history; no qualified binary is rebuilt by it.

## Recovery and previous acceptance

Initial recovery found the earlier execution at the qualified 0.1.5 handoff
`131c806cfff7fc0e162a51f47999ea8e30f4e705` (runtime
`5bf8d954190d3e924d3c23b51735eebe7a07c0e3`), rather than an unfinished
implementation requiring a clean restart. No actual stalled
build or emulator process was established. Process enumeration was unavailable
in the execution environment, so that absence is not proof that no process ever
stalled. Existing dirty worktrees and their unpublished files were retained,
including batch-immutable, coh-memory-policy, fix-combined-build-012,
fix-combined-build-012-qualified, fix-server-memory and fix-server-runtime.
They were compared rather than overwritten; no unrelated old changes were
silently applied to the current branch. Local implementation/qualification
histories remain on preserved branches. Successful qualification artifacts were
reused, and no history was reset or force-pushed.

The latest two native reports and current launcher ZIP establish successful
physical **0.1.6** bounded scene reception and explicit Return within
[their precise acceptance scope](../thor-0.1.6-acceptance/THOR-016-ACCEPTANCE.md).
The exact accepted APK remains available. The prior standalone Session Client
0.3.0 and gates 1–24 retain their documented physical acceptance. Its existing
[APK artifact](https://github.com/Russianranger/coh-android/actions/runs/38673357918/artifacts/11945445541)
and [Thor procedure](../../../../session-client/THOR-TEST.md) are preserved; no
repeat implementation or rebuild is needed.

## This batch

Six real isolated workers concurrently owned the parser, source oracle, Map/local
integration, Android build/qualification, physical acceptance and independent
review. All changes integrate toward native-android; ownership did not overlap.
The full normal-world GROUPS structure is now traversed with bounded CPU/string/
identity policies and no parser allocations. Numeric metadata is retained;
server strings, graph objects, transforms and packet bodies are not. Map releases
the decoded lease on every path. Existing transport, runtime, imported assets,
saved profile and accepted preview are preserved.

The oracle executes 41 unchanged functions, with 16 original source files pinned.
Release/ASan/UBSan each pass 2,473,492 parser checks; Map passes 31,480 and local
1,078 plus the complete headless peer chain. Independent parser/JNI review passes.
Fourteen consolidated host suites, 185 corrected strict driver controls, both ABI builds,
lint and package/source audits pass. Hosted runtime methods pass 76/76 with no
skips. Qualification details, exact package and Android evidence are in
[QUALIFICATION.md](../../../QUALIFICATION.md) and the accompanying receipts.
All 34/34 actual app Android13 checks pass in exact-package continuation
[38838677592](https://github.com/Russianranger/coh-android/actions/runs/38838677592),
using corrected driver `8e237b984c188dd19c171387914e795916712556`.
The two prior failed attempts are preserved: one Android UIAutomation crash,
then a driver assumption about lazy controller creation. Neither required an APK
change. The reviewed correction passes185 driver controls;38 reuse controls pin
both APKs, six native protocol/peer binaries and the whole production source tree.
Three screenshots were independently viewed and hash-bound. Separate successful
Android native crypto/DB/login/Map suites total130,830 checks, plus1,194 UDP checks;
their peers are controlled, rather than an authenticated original server.

| Scope | Current evidence |
| --- | --- |
| Gates 22–24 native preview/assets/renderer | Earlier physical acceptance preserved |
| Gate 25 transport and initial real local sessions | Existing deterministic/Android qualification and bounded real Thor DB/Map evidence; full real-session coverage remains incomplete |
| Gate 26 character list/selection and DB→Map | Physically observed with explicit local UseFakeAuth policy; encrypted AuthServer login pending |
| Gate 27 scene | Complete bounded normal-world structure host/Android qualified; new 0.1.7 physical test pending |
| Imported scene graph/checksums | Not resolved or verified |
| Authoritative selected identity/position/entities | Not implemented/accepted as a live world |

## Concurrent branch integration

A fresh final fetch found another agent's offline-support commit
`bae8cca2b4ae0e43070d5e86ca1c6f1df668bc00`. It is preserved as the publication
parent. Only this batch's completed evidence and handoff were cherry-picked on top;
none of its 116 changed paths overlap this handoff. The Combined and accepted
Session source prefixes are unchanged. All 80 checked tracked compiler/build
inputs from the qualified local ARM64 Ninja dependency database match the pinned
APK source. See [the integration audit](concurrent-integration.json).

That concurrent support code201 has separate qualification and is not added to
this already-qualified APK. Its appearance/UI, immutable collision neighborhood,
offline-world preparation and process-memory work remain available for a later
controlled integration into Combined. This handoff grants no extra physical or
Android qualification to that independent batch and does not start a second APK
build. The current single delivery remains Combined0.1.7 from runtime sourcefe037.

## Next physical test and parallel milestones

Install **CoH-Native-Combined-0.1.7-arm64.apk over Combined**, retaining data.
The [single consolidated Thor procedure](../../../THOR-TEST.md) covers actual
scene parsing, preview/controller/lifecycle regressions, Return, server Stop and
both report exports. `SCENE_INCOMPLETE` remains expected; the supported result
adds the scene-structure-decoded hint. Unsupported real variants must be driven
by the new numeric report rather than bypassing validation.

After the physical report, the next independent workstreams are:

1. Resolve saved library omissions and definition/root identities against the
   existing imported assets. Build a bounded owned graph, reconstruct original
   matrices and qualify footer checksums before publishing a renderer snapshot.
2. Extend original-source entity parsing and initial identity/position contracts
   independently. Integrate a server-selected character only when real identity,
   session and scene prerequisites are verified; do not display preview motion
   as server-authoritative state.
3. Integrate and qualify the existing encrypted AuthServer negotiation and
   account/character handoff
   against an authorized disposable server. Current UseFakeAuth interoperability
   is not encrypted authentication. Keep all credentials and keys out of reports.
4. Measure actual current warm/cold server startup and guest cleanup separately.
   The current 0.1.6 readiness is 392,192 ms; prior detailed cache measurements
   belong to an older session. Prior low-memory causes remain unresolved.

These contracts can develop concurrently, with graph/identity validation gating
live renderer integration. Base/raid scene variants, omitted library data,
unverified CRCs and missing authoritative entities remain blockers to a genuine
native world. Real encrypted authentication needs its own successful session
evidence. No public-server login or complete gameplay claim is made.
