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

First attempt [40033778230](https://github.com/Russianranger/coh-android/actions/runs/40033778230)
never launched the guest: `armport-client-bins` had not yet been uploaded by
run 40032719161. The workflow now separates executable and data donor IDs:
Release from 40032719161; completed bins/Cg from 40011219458. The only native
patch between these builds is 0049's texture-queue diagnostics; no data,
serialization or shader changes were made. The host report records both IDs.
