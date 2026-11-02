Modern Thor MapServer runtime on ARM CI

Verdict: viable with the existing ARM64 Wine/FEX/PRoot runtime. No new server port,
ODBC driver, schema, PostgreSQL version or signing is needed. The present
armport-app-runtime workflow does not attempt this: its donor and admission rules
are explicitly retained_progress only. Merely changing the server ZIP is refused.

Verified inputs

- .36 public donor: release asset 635975286; 42,076,692 bytes; SHA256
  14d88da1796d155dc1b98e45ac642c7702ff3286e7ef0f2a0772f8e48693b12f.
  Downloaded and every packaged runtime member checked against its manifest.
- .36 runtime inventory 89 files, inner client inventory 81. Nineteen runtime
  payloads are deliberately external.
- Embedded Assets 1.0.0 manifest: 23 files, 4,786,799,760 payload bytes in Base,
  Reference, Zones and Audio. It contains all supported map/animation/collision,
  visual, audio, caches and original import indexes/text inputs.
- Current .47 armport client package and server-metrics-thor-certified-startup.zip
  must come from the same exact successful native build. Reuse the runtime stage's
  exact armport-app-proot-linux and armport-app-client-package artifacts.
- Existing tools/android/interactive/qualify_runtime_asset_preflight.ensure_assets
  authenticates/downloads Reference/Base/Zones; qualify_full_startup_preflight.
  extra_inputs adds Audio, indexes and client visual metadata. These are reusable
  input retrieval functions, not native runtime evidence.

Minimal integration

1. Add a modern-guest job after retained interactive-guest in the same runtime
   workflow. Use ubuntu-24.04-arm and existing PRoot, client, native ZIP downloads.
   Hydrate .36 runtime from its embedded inventories and exact external payloads.
   Use a fresh work directory and disposable database; never accept a player DB.
   Stage via stage_app_assets.stage(..., server_variant='thor_certified_startup').
   The helper modern_runtime_donor.py in this directory drafts that hydration.
   Full hydration was executed successfully on the real .36 APK and all 23
   external leaves; see hydration-report.json. No native runtime was executed.
2. Add an explicit modern mode to interactive_host. Retained mode stays unchanged.
   Reuse its actual Java import, creation RFB driver, owned cleanup, independent
   protocol/SQL checks and persisted profile identity continuity.
3. Extend server_pipeline.guest_admission to accept the explicitly requested
   modern variant and bind actual PE hash/run/source/package pins to that variant.
   Keep retained-session qualification unchanged. Record modern execution only
   after a separate successful modern host result; never infer it from a build.
4. The legacy host validators require an exact old 12-stage list. Modern assets
   add client_visual_assets, client_animation_pack, client_all_zone_assets and
   client_all_zone_audio. Validate all four successful stages and exact component
   pins/counts/preservation receipts before a narrow legacy projection to the
   unchanged character/save/cleanup checks. Do not drop arbitrary unknown stages.
5. .36 embeds task-gate.json. Default ordinary reopen would require completing
   its authored task; the retained RFB script does not do that. Prefer the shipped
   explicit --zoning route for modern reopen (normal ARM app route), which selects
   LocalCharacterZoningServer while retaining save, identity and server behavior.
   Its owned map label is local-character-zoning-1, not local-character-atlas; host
   validation must first bind that actual owned process/PE before projecting its
   label. Leave the task-gate file and default task behavior intact.
   --startup-only is an existing separate timing diagnostic and could be used for
   a narrower smoke, but must not be reported as the normal zoning route.
6. Retain existing guest report success, full SQL commit, ordinary logout, cleanup,
   distinct creation/reopen IDs, profile inode/hash continuity, powers, costume,
   selected-row and native-position preservation checks. Extend the existing
   qualification artifact's modern fields only with this real evidence.

Scope and limitations

- A modern creation+reopen run proves Atlas initialization/client connectivity,
  ordinary save/reopen and the matching modern PE, not King's Row combat/zoning.
  Follow with the actual existing native monorail path for map5 and return, then
  combat/rewards/collision/NPC checks. Do not claim complete Gate D from Atlas only.
- Native-ready can be observed using existing live progress + translated DbServer
  -getstatus protocol guard; new native phase logs and supervisor trace add timing.
  Native ready publication alone remains insufficient.
- Exact app source/helper staging matters. No smaller data projection is needed or
  permitted for a full-runtime claim. Preparation-only tools explicitly stub
  process/readiness boundaries and cannot replace a live map run.
- Cache all four public volumes between runs but use fresh private work/profile for
  creation; reuse that same profile only for the paired reopen. All native starts
  and cleanup remain supervised. Disk consumption includes ~4.8 GB compressed
  volumes, ~4.8 GB payloads, original 2.98 GB import, rootfs/Wine and prepared data.
  Check actual runner free disk before staging and delete redundant authenticated
  transport copies only after extraction/pin checks. Do not remove required data.
- Software graphics in CI retain the current host profile and do not establish
  Thor startup/thermal/FPS behavior. Any <=60s ARM runner result remains CI only.


Implemented supporting qualifier checkpoint

- modern_runtime_host.py imports all production code from a separate clean exact
  candidate checkout, stages the exact modern native ZIP, drives real creation
  and explicit --zoning reopen, and retains the unchanged SQL/save/continuity and
  cleanup validators. Supporting test source identity is recorded separately.
- modern_validation.py admits exact modern PE/run/source/session proof, independently
  decodes raw progress records and checks fresh DbServer protocol readiness,
  validates the four modern asset stages, then performs only the documented
  stage/owned-label projection. Task-gate bytes are verified before/after.
- test_modern_runtime.py: nine tests pass. These are admission/projection/budget
  controls with metadata fixtures; they do not claim server execution.
- Each actual guest retains its own existing 5,400-second budget. Reopen gets a
  fresh budget after first-session cleanup. The supporting job cap is 240 minutes.
  These are correctness bounds, never a <=60-second performance qualification.
- modern-runtime.yml is the supporting workflow draft. Copy it as
  .github/workflows/armport-modern-runtime.yml on
  armport/mapserver-modern-runtime-qualification, and copy the four Python source
  files to armport/modern-runtime. Pin the successful candidate runtime run ID
  before pushing; placeholder 0 fails before runtime work. Native build41363927704
  and candidate e563fe5664cd13570899800695c7e9680ac68877 are explicit inputs.
- Full Assets1.0.0 retrieval and real donor hydration passed locally. Runtime89,
  client81 and external23 pins passed. The original four-file importer input
  contract also passed: 173,011 leaves /2,977,730,517 bytes. This is input/staging
  proof; Java import, native processes and database execution remain separate.
- Copy only the named Python sources, YAML and optional small evidence/notes.
  This temporary directory also contains multi-gigabyte authenticated data;
  never add that data or APK to the supporting source branch.

Implementation now complete: nine admission controls pass. Full local donor hydration and exact original importer contract passed; see armport/evidence/modern-runtime-donor-hydration.json. Native execution is still pending. Before a workflow-only kickoff, pin BOTH runtime-ID zero placeholders to the successful runtime of candidate e563fe5664cd13570899800695c7e9680ac68877/native build41363927704. Setup uses [skip ci]; no production candidate source is changed. Each modern guest retains its own existing 5400-second correctness bound; no 60-second acceptance is implied.
