# Recovery, reservation phases and independent qualification

Worker F began at `d96354411d2f69ec325b1bfe9d0e14999626ba91` in independent
`recovery-f`. Changes remain in this diagnostic directory. No runtime caching,
persistence, accepted APK, shared build, profile or server source was changed.

## Recovered source inventory

`recovery-bytes.json` records a sequential read-only byte inventory of **24,212**
regular files in eight preserved trees under `/workspace/scratch/78494e933b7f`.
Scope is explicitly `native-android`, `tools` and `.github/workflows`; other
historical files/artifacts are preserved but not exhaustively audited here.
Each old `.git` points into absent `/workspace/scratch/9c69943dc291/coh-next`.
The old bundle-check repository also has no objects and a broken alternate.
The inventory compares Git blob bytes, including 100 actual published history
trees, rather than treating an old worker commit ID as a published commit ID.

| Preserved tree | Files | Identical at pin | Exact older published bytes | Other older snapshots |
| --- | ---: | ---: | ---: | ---: |
| worker-a | 2,920 | 2,869 | 51 | 0 |
| worker-b | 2,908 | 2,855 | 49 | 4 |
| worker-c | 2,933 | 2,879 | 51 | 3 |
| worker-d | 2,943 | 2,885 | 58 | 0 |
| worker-e | 3,161 | 3,094 | 67 | 0 |
| worker-f | 2,908 | 2,847 | 61 | 0 |
| integration | 2,930 | 2,854 | 76 | 0 |
| published | 3,509 | 3,462 | 47 | 0 |

All **703** entries in five old publication manifests are exact current or
older published blobs. `unclassified-source-review.json` independently records
the seven nonidentical snapshots. Current compact-graph files add bounded
missing-reference diagnostics and stack qualification; current world-capture
files add alias rejection, whole-source provenance and correct map identity
qualification. These old snapshots must not replace the accepted newer files.
No confirmed unpublished qualified implementation was found in this scope.

The thin 179,282-byte continuation bundle initially could not import because
the partial clone lacked delta bases. Fifteen exact base blobs were recovered
from preserved old files by their actual Git hashes, and written only to a
**new** private audit repository. The bundle then imported successfully:
13 old commits, head `becbff99e52dc197c787bfeaf2583da081d3d2e1`, prerequisite
`cda93d96f8696e6a0f2ec6940a0c96e5b852f281`. No old index/object/alternate was
edited. `bundle-recovery.json` preserves identities and recovery inputs.
The identical bundle is already committed at
`combined-client/evidence/20261016/six-worker-continuation/worker-history.bundle`;
it was not needlessly duplicated.

The new byte-audit tool refuses lazy Git fetches, follows no file symlinks,
bounds files/count/history, and checks each regular file's identity across its
read. It is a sequential inventory, not an atomic snapshot or qualification
certificate. Three targeted Python controls pass.

## Executable parent reservation ordering

`qualify_phase_replay.py` verifies nine existing source receipts and executes
the actual unchanged `coh_working_set.c` through source-derived phase costs.
Its new harness uses **synthetic billing keys**, never source objects. It adds
the measured 19,000-byte parent reservation exactly once and partitions the
old aggregate into disjoint billing amounts without claiming owner discovery.

| Executed accounting phase | Named bytes |
| --- | ---: |
| Old world plus known dictionaries and parent | 97,681,474 |
| Old/candidate seal overlap with those dictionaries | 100,074,681 |
| Candidate committed, old external owners still charged | 100,058,297 |
| Explicit synthetic old/GEO retirement, then power sets | 67,361,231 |

The actual parent API refuses power sets both before and during the seal
transition. Duplicate-owner and excessive-retained late failures keep the
entire candidate reservation; abort restores current charges and retains the
observed peak. Successful seal commit removes only its temporary reserve.
It does **not** release old geometry, loader or provider accounting. Wrong-key
retirement refuses. The final phase becomes possible only after explicit old
copy and GEO-reservation release calls. A real adapter may make those calls
only after actual qualified external cleanup.

All **64 checks** pass independently in release, ASan and UBSan. Maximum emitted
parent frames are 32/176/48 bytes respectively; parent frame sums 96/472/312
remain within the existing 16 KiB reserve. LeakSanitizer is disabled as in the
existing environment qualification. No source object, resource provider, actor,
material, packet or GPU allocation is constructed by this harness. It closes
reservation-order execution coverage, **not** the missing global child adapters
or actual integrated allocation/retirement measurement. The final 33,302,065
bytes of allowance are unassigned named reservation space, not device RAM.

## Startup and memory evidence carried forward

No real game runtime or Android toolchain is available locally. Environment
availability is recorded in `environment.json`; GCC/C++/Python can qualify
host code, while Wine/PostgreSQL/adb/emulator/MinGW are absent. No new process
overlap, Android RSS/PSS, allocation failure cause or startup improvement is
claimed. Existing one-shot owned-process sampling already exists and was not
duplicated.

Accepted current warm readiness remains **387,340 ms**, with DB **70,678 ms**
and Atlas **271,736 ms**. Internal phase timings are nested and must not be
added to these boundaries. Beacon handling's 24.258 seconds still lacks an
exported cache hit/refusal/decode/hash breakdown; the accepted receipt does not
establish that it decoded or missed a cache. Existing final report projection
is the safe observation point, with fixed-status/scalar allowlists and no
additional hash/inventory pass. Warm schema restoration already costs only
0.183 seconds. Production cache/persistence changes remain unjustified.

The existing 466 accepted memory samples contain no pressure samples. Historical
self/reaped-child high-water RSS and Java/system headroom cannot establish
simultaneous native DB/Atlas/launcher memory or a historical Android kill cause.

## Independent worker reviews

B's committed `1c8d770284e38154efe30b4964fb9a334a89046a` was independently
reviewed and re-executed against the exact retained resource capture:
**74,366 checks**, **17,799 original/native cases** per release/ASan/UBSan;
all five semantic mutations refuse. Loop/read/output bounds and exact original
triangle-count ordering are preserved. The 3,083 real SERVER numeric model
observations are explicit absent-array source projections; actual CLIENT
reduction arrays, dictionary precedence, reduced meshes and current generation
remain absent. `independent-b-autolod.json` records this execution.

E's presentation source was independently reviewed. F found that nonempty
create/prepare outputs could overwrite caller leases; E added refusal and
sentinel preservation tests. F also requested the allocation claim be narrowed:
adapter consumption allocates/frees no heap, but renderer shader cache misses,
evictions and Surface cleanup may invoke backend/driver allocation/destruction.
Those remain external and unmeasured. Pending and active leases are separate;
complete resource bind precedes submit, failed multi-batch draw retains old CPU
state, and control-thread collection owns all lease destruction. Already drawn
pixels cannot be rolled back. New source generation or actor authority is not
granted by this consumer.

Committed E source `2917fbfbfc4906f32a476cb548ef8abc1406f20a` was then
independently re-executed: **34,465 checks** per release/ASan/UBSan, clean source
before/after and unchanged exact inputs. This includes 512 concurrent prepared
publications, complete bind/fallback and late draw failure, lifecycle, lease
retirement and caller-output preservation. `independent-e-presentation.json`
records this fixture/backend qualification; no GLES driver/device ran.

A's same-thread source sink has bounded chunks/counters, no-replace publication,
and commits only after the existing actual quiet guard releases successfully.
Its inspector explicitly marks source/run/native-receive association unproven.
F requested robust Python cleanup if output flush/close fails so partial owned
extraction cleanup continues. A applied that fix and explicit 0600 outputs.
Committed A source `2ade98333` was independently hash-bound and re-executed:
**12,340 native sink checks/142 I/O refusals** per release/ASan/UBSan, plus
**6,253 inspector checks/6,226 corruption refusals**. Mocked write/flush/close
failure preserves the first error and attempts every cleanup; FD counts close.
No real Win32 build or live capture is inferred
from a host fixture using substituted WinAPI/quiet/owner/resource observers.

C's `031792ef4b97749035d9f0b3cfa2bb2c1a9df46e` was independently source-reviewed;
all 62 receipt hash entries (61 normalized unique inputs) were checked against
that actual committed source. Its final worker receipt reports **170,281 checks**
per release/ASan/UBSan in 13 cases; F did not independently repeat this full
corpus execution. Pre-callback span/owner/provider/stack budget admission,
bounded name/hash/probe/read/record work, explicit reverse-parent work refusal,
borrowed lease lifetime and atomic output publication have no review blocker.
This remains historical forward/parent projection, without current generation,
`DuplicateMissingPowers`, nested AttribMod finalization or authoritative actor.
`independent-c-power-join.json` preserves exact review/proof provenance.

The coordinator's native local receive CLI uses the existing opaque owner and
streams its synchronous loan directly to a fresh private directory. F requested
report-file ownership tracking on rollback, account short-read rejection and
complete build-helper/original provenance. The coordinator applied these fixes.
This diagnostic remains explicit local-development authentication; its numeric
inspection report is not a source generation receipt or full-update ACK.

## Reproduction and status

```sh
python3 -m unittest discover -s native-android/combined-client/diagnostics/continuation-f-20261017 -p 'test_*.py' -v
python3 native-android/combined-client/diagnostics/continuation-f-20261017/audit_recovery.py --source-root . --preserved-root /path/to/preserved-root --revision d96354411d2f69ec325b1bfe9d0e14999626ba91 --output /fresh/recovery.json
python3 native-android/combined-client/diagnostics/continuation-f-20261017/qualify_phase_replay.py --source-root . --output /fresh/parent-phases.json
```

Qualification is implemented and host/source qualified within these diagnostic
scopes. No new Android ARM64 build, Android emulator qualification, physical
Thor acceptance, full encrypted handoff, authoritative world/player publication
or APK is established by F. Current live generation, complete source dictionaries
and initial update, CLIENT material/LOD resources, global child adapters and
actual combined renderer/runtime measurement remain distinct blocking work.
