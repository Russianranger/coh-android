# Retained helper with normal SystemDrive inheritance

Actual [39154121730](https://github.com/Russianranger/coh-android/actions/runs/39154121730)
reported `FILES / PROFILE_ROOT_PATH / PATH_FORM`, with complete inner/outer
cleanup and no child process launch. This proves that the profile-root string
failed the unchanged local path-form predicate. It does not reveal the string,
the failed disjunct or the reason the API returned that form.

The supervisor's helper environment omitted the normal `SystemDrive` variable.
The candidate permits that one additional normal variable in a separate fixed
mode. It requires the host value to be a single alphabetic drive plus colon,
and requires both `SystemRoot` and `WINDIR` to be local absolute Windows
directory paths on the same drive, ignoring letter case. No other environment
variable is added. Original modes retain their four-variable environment.
All helper path, ownership, ACL, identity, authentication and cleanup guards
remain unchanged. The observed failure and the changed-environment comparison
must remain separate; actual causality is pending the next execution.

Use `supervise_inert.py --profile-system-drive`. It reuses the exact50395-byte
profile observer source/38400-byte PE already compiled in39154121730, together
with the original accepted39106023132 probe/model artifact. No C# compiler,
model, old qualifier or service is replayed. Root must independently admit
artifact12145434474:33239-byte ZIP SHA256
`0d9a6e2870c18f463a73df37b8c16dc27b793cafa52d7c9d941efe5551720cf5`.
Its exact four static members go under the accepted artifact's `profile-path`
directory. The PE hash remains
`c6df10d121ea73e2ed8675465593b704f2a97b35289bc00d24ac1b7ee4219069`.

The native receipt schema remains the fixed profile-path diagnostic schema.
The supervisor distinguishes `system_drive_environment_requested` and
`retained_profile_helper_reused`, with zero new compiler invocations and false
compiler/model-reexecution flags. Runtime upload remains only the two fixed
public receipts; private paths, identities, journals and output remain private.

Five new controls and33 shared regressions passed, with exact output retained
in the SystemDrive qualification directory. They cover allowed keys, malformed
or mismatched drives, exact actual helper admission, no compilation claim,
mode conflicts and the preserved actual failure/cleanup scope. No helper,
compiler, Windows API or service ran in these controls. Actual changed-env
success and original service readiness remain pending.
