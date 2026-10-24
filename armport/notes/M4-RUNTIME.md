# M4 runtime integration work

M4 is not complete. This branch starts with a runtime boot probe while M3's
texture-load fix and replay review continue on `armport/m3-atlas`.

## Existing app path

Source inspection (`rg -n 'launcher_command|Xtigervnc|presentation-socket'
android/guest/*.py` and `ClientRuntime.java`):

- `android/interactive/.../ClientRuntime.java:runCharacter` starts the app's
  PRoot with its Bookworm rootfs, Wine, private state, data and display-socket
  bindings. It invokes the character creation/reopen Python guest.
- `android/guest/client_interactive_diagnostic.py:launcher_command` selects
  the current `client-launcher.exe` and `CityOfHeroes.exe` in the worktree.
- `android/guest/presentation_diagnostic.py:PresentationDiagnostic` starts
  Xtigervnc with TCP disabled and exports `view.sock` through the private
  `/presentation-socket` binding. The Android wrapper receives RFB frames.
- The current x86 worktree/package validators pin the executable and data.
  ARM64 needs an explicit separate client option/package, not replacement of
  the accepted x86 pins or mixing x86 DLLs with the ARM64 executable.

The earlier in-guest attempt failed in
[run 39795786028](https://github.com/Russianranger/coh-android/actions/runs/39795786028),
job 119887720825: client exit 1, `BadWindow`, `X_UnmapWindow`, resource
`0x800003`. That log does not establish the cause. Host Wine startup succeeds
in the M2 jobs; it does not qualify the app guest/display path.

## First probe

`armport/app/runtime_host.py` downloads and verifies the exact base/Wine
archives from `android/runtime-lock.json`. It extracts them with the app's
Java extractor, builds the existing pinned PRoot source for Linux ARM64,
and runs the client in a private loopback-only network namespace. No server
or APK is built by this workflow.

`runtime_guest.py` reuses `PresentationDiagnostic.start_wine` and cleanup.
It verifies ARM64 PE32+ client binaries, starts the original client on the
guest display, requires login stage 0 and a mapped game window, then waits
for three fresh host RFB captures. The host uses the existing app-transport
handshake and framebuffer decoder. The report requires guest success and
owned cleanup, and explicitly records `m4_complete: false`.

Local checks before the first push:

- `python3 -m py_compile armport/app/runtime_host.py armport/app/runtime_guest.py`: exit 0.
- `python3 tools/android/client/test_host_transport.py`: four tests passed.
- A synthetic PE-header check accepted ARM64 PE32+ and rejected i686; guest
  imports completed. This validates the architecture preflight, not execution.
- Both changed workflow YAML files parsed with PyYAML; `git diff --check`
  passed. Runtime evidence is pending CI.

Next after this probe: inspect its actual RFB images, fix any guest/display
failure, add the Android client choice and package staging using the same
guest launch path, and qualify that integration on the ARM64 runner. M3
must still pass its own exits and review. Building/signing an APK remains a
separate approval step under HANDOFF section 6; no keys are used here.

## App display path result

[Run 40034280752](https://github.com/Russianranger/coh-android/actions/runs/40034280752),
head c2e1ca2d872a571a864aa1f45481c2ac8ef8a2ee, completed the runtime probe.
`host-report.json`: passed true, guest_exit 0, m4_complete false. The guest
reported login stage 0, a mapped 800x600 City of Heroes window, the client
alive after frame capture, zero surviving owned workers, and all cleanup
checks true. The three RFB PNGs have SHA-256
3e968bdba2433c0ab758f089644404d9cc6cc2a2e2a16dab5e6b39f78a9b8c6a.
Visual inspection shows the actual login screen with the first-run graphics
settings dialog, not Atlas. Artifact 12537065650 was downloaded and checked
against API digest 86a90e23d9e4cb3799f2054d0ca45079271305cca7e28cc0effe9e126029ec4c.

Next probe builds the app's unchanged `android/native/client-launcher.c` for
ARM64 and requires its real child PID and console-membership observations.
This tests the launcher used by the interactive app rather than assuming
that direct Wine startup qualifies its console supervision.

[Run 40036045979](https://github.com/Russianranger/coh-android/actions/runs/40036045979)
passed that launcher probe: Windows child PID 404, matching session and
`attached: true` console marker, login stage 0, mapped 800x600 game window,
and complete cleanup. The artifact's API digest is
1853fcfde401a4e6fbf984f09b6ea4f5dbe14a800553855f8cf171fb8b82fb71;
it was checked after download. The Release window title omits the PID.
The ARM64-only launcher build now exposes its already-resolved owned PID
in that window's diagnostic title for the existing app identity check.

## App option being qualified

The selector defaults to x86. ARM64 selects a separate package/directory,
its own generated bins and ARB shaders, and the 64-bit GameProgress registry
view. The existing verified x86 data tree remains available for server
preparation; its executable and DLLs are never copied into the ARM64 tree.
Both clients retain the existing character-profile, local server, RFB/input,
save-evidence and cleanup paths. ARM64 currently selects Software/standard
graphics and Atlas only; return the saved character to Atlas with x86 before
switching. Zone-travel asset synchronization is not yet qualified.

`stage_app_assets.py` assembles extracted runtime assets and extends the
existing input manifests. It does not build or sign an APK. Its inputs are
the retained app assets and the CI `armport-app-client-package` artifact.
The Android Java compile job likewise produces classes only. Building the
installable APK still requires the user's signing approval.

Local checks: `python3 armport/tests/test_client_package.py` passes four
cases (separate ARM64 bins, x86 DLL refusal, changed payload refusal, unsafe
extra member refusal); Python modules compile, launcher compiles for ARM64
with warnings enabled, and `git diff --check` passes. These do not yet prove
the complete interactive guest/server path or milestone completion.

First attempt [40033778230](https://github.com/Russianranger/coh-android/actions/runs/40033778230)
never launched the guest: `armport-client-bins` had not yet been uploaded by
run 40032719161. The workflow now separates executable and data donor IDs:
Release from 40032719161; completed bins/Cg from 40011219458. The only native
patch between these builds is 0049's texture-queue diagnostics; no data,
serialization or shader changes were made. The host report records both IDs.

## Startup evidence regression (40037067863)

Run 40037067863 failed because the probe kept only the final 1 MiB of the
client log. The artifact contains 1,397,688 bytes: OpenGL Renderer and Renderer
initialization complete are present near its beginning and absent from the
probe tail. GameProgress reached game_mainLoop, all data loaded and the owned
800x600 window was mapped. This was an observation failure, not proof of a
renderer failure.

The probe and app wrapper now share a complete-log reader bounded to 16 MiB.
`python3 -m unittest discover -s armport/tests -p 'test_client*.py' -v`
passes five tests, including renderer evidence before more than 1 MiB of asset
noise and rejection above the existing 16 MiB bound. The rerun passed in 40040922125, guest-boot 120711625618 (2026-10-23
23:46 UTC). The evidence artifact 12538814705 was checked against SHA-256
e490d2ae902b0f503975eedfe2668adae430278c51235e207245cf959d77ca1f.
Its host report records passed=true, guest_exit=0, m4_complete=false.
The guest reports Mesa/X.org llvmpipe LLVM 15.0.6, GL 4.5, renderer initialized,
all data loaded, game_mainLoop reached and owned PID 420 mapped at 800x600.
The client was alive after the RFB capture, its console was attached and all
three cleanup checks passed. This resolves the startup observation regression;
it does not qualify the complete interactive guest/server flow or M4.

## Actual creation/reopen command routing

`python3 -m unittest discover -s armport/tests -p 'test_client*.py' -v`
passes nine tests. The four additional checks import the actual creation and
reopen guest classes and execute their launcher_command inheritance: x86
remains the default with its original worktree, ARM64 selects its separate
launcher/client/worktree, creation/manual mode survives the wrapper, and
unknown architectures or unqualified zoning fail. No Wine/server process
is started by these host tests; full interactive execution remains pending.

Next: incorporate the qualified M3 client, then run the real creation/reopen
server flow through the selected ARM64 app guest and retain its SQL/save,
RFB/input and cleanup evidence. Do not substitute the startup-only result
for that integration check. Building/signing an APK still requires approval.

## Preparation order and app acceptance

The command-routing check exposed two untested integration boundaries. The
ARM64 overlay had been copied in initialize(), before optional visual/animation
inputs are installed after server preparation. Also, the app's exact stage
validator did not recognize armport_client_data. An ARM64 run could therefore
miss late-installed data and still be rejected after successful execution.

ArmPortClient.start_wine now lets the existing server prepare first, installs
the existing client-only visual/animation inputs, then creates the ARM64 tree.
The original x86 producer opt-ins remain disabled for the ARM64 executable.
ClientAcceptance selects the exact stage sequence using the app's selected
architecture, requires all four pinned ARM64 package/helper inputs and the
successful ARM64 preparation stage after optional visual/zone stages. Merely
including the ARM64 package in an x86-selected app does not change that path.

Validation command `python3 -m unittest discover -s armport/tests -p
'test_client*.py' -v` passes 11 tests. One uses the real overlay packager to
prove a visual file added after server preparation reaches the ARM64 tree.
Another compiles and executes the actual app ClientAcceptance class with 13
positive/negative cases: missing/failed/misordered ARM64 preparation, missing
package pins, missing visual stages, invalid architecture, and retained x86
selection. No APK is compiled or signed; interactive runtime evidence remains
pending and M4 remains incomplete.

## Full interactive guest qualification under development

Run 40055653259 at f0714bb7 passed app-sources and guest-boot, including the
new stage/ordering host tests. This is still a startup probe, not an interactive
or M4 pass. The next workflow packages the newer Release/bins/ARB inputs from
40054327137 and adds a dependent interactive-guest job.

interactive_host.py extracts only the assets of the retained 0.10.0 donor
(run 36920583713, artifact 11192425448), requiring the frozen full APK and
build-report hashes from android-character-reopen-qualified-apk.yml. The API
still reports that artifact available through 2026-12-30. Its binary runtime,
server packages and data inputs remain retained; stage_app_assets refreshes
the current creation/reopen helper dependencies and adds the separate ARM64
overlay. This is an assembled guest-assets test, not an exact old/new APK test.

The host reuses the existing Java data importer, private RFB input observer,
creation/save checks, reopening/powers/costume checks, profile continuity and
owned cleanup. Each session uses the existing private network isolation
helper. It checks the complete current helper/package inventory, ARM64 digest
and successful preparation stage before applying the original persistence
validators to their existing field subset. The complete unmodified report is
retained. This avoids claiming ARM64 identity from an x86-only report.

Local validation: 15 test_client host tests pass, including isolated imports
from just the retained helper set plus its explicit current dependencies,
rejection of wrong ARM64 binaries/missing inputs/failed or misplaced stages,
and preservation of the original report. Python syntax, workflow YAML and
two-compiler/dependency checks pass. Interactive execution remains pending;
all host results retain m4_complete=false until the full evidence is reviewed.

## Retained donor compatibility fixes (2026-10-24)

Run 40087554038 at aef0c566 passed app-sources and guest-boot. The interactive
job 120855148929 reached the private Xtigervnc/RFB display and Wine/ODBC,
then failed local_dbserver_startup with `No module named 'zone_asset_package'`.
Artifact 12557642717 was downloaded and checked against API SHA-256
a9c6eb028365d867347ec8228b7396e3dbce5706b7abe3c7731aa00c47f19087.
This is not an interactive pass or M4 completion.

The earlier world-package mismatch was fixed by binding only six literal
payload constants from the authenticated retained atlas_world_assets helper
into the current helper. Its validation code and bounds stay current. Tests
reject missing/duplicate/executable constants and preserve the current code.
The retained world predates the current 27-texture extension; changing its
expected digest without changing the payload would reject the donor bytes.

Commit ddaccd4 adds zone_asset_package.py to the staged helper dependencies.
LocalCharacterServer.prepare_runtime imports it unconditionally to check
whether optional zone/audio payloads exist. The helper alone does not enable
those optional packages; partial ZIP/manifest pairs still fail. Tests exercise
these actual presence checks. `python3 -m unittest discover -s armport/tests
-p 'test_client*.py' -v` passes 18 tests at ddaccd4.

Run 40090844692 at ddaccd4 passes app-sources and guest-boot. The first
interactive attempt (120864873702) failed before guest launch: build_proot.py
reported HTTP 503 downloading a dependency. Only that failed job was retried.
This attempt does not exercise the helper fix. Creation, save, reopen,
persistence, private RFB/input and cleanup
must all pass before this path can qualify. No APK, Android surface, Thor or
M4 completion is claimed by the startup result.

The failed interactive retry (120865719209) again received HTTP 503 from the
talloc download before guest launch. The workflow now uses the repository's
existing extract_talloc_source.py to recover the exact SHA-pinned source
from run 36364550345's accepted runtime/source artifacts, caching that source.
GitHub's artifacts API confirms both inputs unexpired on 2026-10-24. The
build recipe still verifies the same talloc hash and uses two make workers.
The interactive job now consumes a tar of the exact PRoot/loader/source
receipt built and used by its successful guest-boot dependency, preserving
executable modes; it no longer repeats the network download/build. This
workflow change needs fresh CI; it is not a runtime success claim.


## Review 5638651994 / VBO runtime correction (2026-10-24)

Run 40098262167 at ddceae53 passes app compilation and guest boot. Its
interactive client reaches renderer initialization, all data loaded and the
main loop, then crashes during character creation after the costume input.
Retained artifact 12562338334 SHA256
4d8ad44362966f27c30cd9e3c8165e67c167fc8cd980561fbd49e5b8cebc1bda
contains client-console.log: unhandled read 007A000642C587A0 at 0x140231A94.
The exact executable SHA256 is
0392424f466ceb6cbcb31d6c40252eace3570319db071369711ef35b74a6a00f.
`llvm-symbolizer --obj=CityOfHeroes.exe 0x140231a94` resolves createVboDirect,
rt_model_cache.c:79:41. Source producer model_cache.c writes an eight-byte
pointer then overwrites its upper four bytes with TexID at offset four.
Patch 0064 on PR #6 / 285f913c fixes allocation and both producer/consumer
header offsets. Original/patched host controls fail/pass pointer and payload
identity as expected; both ARM64/i686 Game links pass. Fresh runtime CI must
exercise it before claiming resolution.

This branch pins the new Release to build run 40105902326 and data/shaders to
completed run 40100355259. Both source commits contain the deterministic
Appearance fix; 0064 changes rendering only. Every package records both run
IDs and executable/archive SHA256.

Review M2: prepare() reports shared_data_bytes, data_copy_seconds and
preparation_seconds. Private regular copies remain necessary for this tested
PRoot path; a separate read-only data root is a future optimization requiring
verification of the original client's writes and search precedence.
Review L5: bounded CI notices now include guest failures and client fault
lines, not only the outer RFB close. Against the retained failure artifact the
notice shows the original VBO fault and the separate incomplete owned-cleanup
failure. Ownership and cleanup checks remain unchanged and fail closed.
`python3 -m unittest discover -s armport/tests -p 'test_client*.py'`: 23 tests OK
(m4-round4-tests.log). No APK/signing, Thor run or M4 completion is claimed.

## Power-customization fault after the VBO correction

Run 40106299491 at a5d78afd passes guest boot, but interactive job
120910487842 fails with a read at 0x0000010000000010, PC 0x14007457c.
Artifact 12565996723 SHA-256
`a897c9492bd28a64d30cfc0d647db2b8040098167103cfb046e95390065d3f30`
and the packaged executable SHA-256
`0e82dd6656a91e0e09eadb2a685de9c1dfb59e7573f22f6fa6d04e9c4dcf0844`
were independently verified. `llvm-symbolizer --obj=CityOfHeroes.exe
0x14007457c` reports `searchPowerCustomizations`, power_customization.c:159.
Disassembly identifies the failing load as `(*power)->crcFullName`, the search
key, rather than the candidate customization. Its origin is not established.
The interactive launcher now enables the same Wine SEH diagnostics as the boot
probe so a rerun retains registers/caller evidence. No NULL bypass, pointer
repair or acceptance change is made. All 23 client host tests pass.
