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
noise and rejection above the existing 16 MiB bound. Runtime rerun pending.
