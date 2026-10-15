# Execute-only ancestor candidate - closed, unexecuted research checkpoint

This checkpoint preserves a proposed two-file compatibility correction while the
shared executor is offline. It is **unexecuted and independently unreviewed**.
It contains no new binary, workflow change, runtime admission, APK, player-data
change, or claim that an Android device has passed.

The original producer source remains at
`2d030678e7013891547ecd7d35fc0cf40ffabff9`. Its core opens every host ancestor
with `O_RDONLY`, which can demand directory read permission where Android permits
only search through system parents. The proposed core uses `O_PATH` for nonfinal
components, retaining `O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC`. The final app root
continues to open read-only and retains exact device/inode/UID and full namespace
revalidation. This is a proposal, not a qualified compatibility guarantee.

The test proposal contains nine actual-kernel controls. A child drops all
effective/permitted/inheritable capabilities and sets no-new-privileges before
exec. It must prove the capability state, real `EACCES` on an execute-only
ancestor, readable final FD flags, final-readability refusal, missing-search and
symlink refusal, initial and post-row ancestor retarget refusal, terminal
post-row fallback prohibition, and descriptor cleanup. None has executed.

The first attempt to create a nonroot UID65534 fixture failed at `chown` with
`EINVAL` before any child/native control ran. This is a host setup refusal,
not a reproduced native failure and not passing qualification.

After the executor recovers, reconstruct the complete finite
`tools/native_live_directory/` baseline from the exact original commit into an
isolated stage, then overlay only these two candidate files. The preserved files
here alone intentionally omit unchanged compilation dependencies. Reproduce the
old behavior using the exact retained CEC249/B264121 host libraries with the
capability-free DAC child, then run the focused and original host controls.
Require independent source review before one source-justified new ARM ABI build.
Android/PRoot/Wine fixture parity and physical testing remain later gates.

The existing qualified producer, binaries and original receipts retain their
original identities. Main, the draft gameplay PR and active production source
are not changed by this research checkpoint.
