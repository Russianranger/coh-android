# Atomic security for newly created private files

Actual Windows run [39124469057](https://github.com/Russianranger/coh-android/actions/runs/39124469057)
returned `FILES`, `JOURNAL_ACL`, `ACL_OWNER` before account creation. Its exact
fixed receipt reports complete inner cleanup; outer supervision reports exact
process/job/handle cleanup and empty-parent retirement. The observation proves
the journal's owner failed the existing runner-or-SYSTEM predicate. It does not
publish the actual owner SID or prove any particular other SID was the owner.

The root directories already receive the explicit runner owner and protected
DACL at creation. The four private files used token-default ownership through
ordinary `FileStream` constructors. Windows uses the creating token's default
owner when an explicit security descriptor is absent; that owner can differ
from the token user. Therefore the candidate supplies the existing exact SDDL
through the `FileStream` constructor's `FileSecurity` argument at `CreateNew`.
It changes the journal, copied probe image, private probe input and empty probe
result. Requested read/write access and sharing behavior remain the same.

`prepare_file_owner.py` starts from the exact actually observed diagnostic
helper (47405 bytes, SHA256
`3f556f65fa8a6182797c2d42bc0d1ea1c0a57aa54b5de058fe1f7a8c6cec2514`).
Five exact reversible replacements add one private creation helper and replace
the four creation expressions. The generated successor is47790 bytes, SHA256
`53add195056ce87c445de347bd6d0fa8996ff3c5842a59a69172587b649ec933`.
The original source, observation generator, old build recipes, inert probe and
accepted model remain byte-identical. Existing owner/ACL methods, path/hash/
identity guards, one-shot process semantics and cleanup methods are preserved.
No existing object's ACL or default token owner is changed.

`build-file-owner.ps1` checks the selected installed compiler/reference bytes
against the accepted39106023132 build receipt, then compiles only the new helper
once. It never recompiles or executes the accepted probe/model. Root must admit
the original accepted artifact exactly before this build. Generated source,
preparation receipt, new helper and `owner-build.json` form the static compile
artifact; raw compiler outputs are private and excluded.

`supervise_inert.py --file-owner` admits the separate `file-owner` directory,
its exact source predecessor/successor and new image, then uses the same outer
suspended process/job owner and fixed inert receipt parser. This mode and the
prior `--file-diagnostic` mode are mutually exclusive. Upload only the existing
two fixed runtime receipts. Keep failed/private owner journals out of artifacts.

Six new host control methods passed: exact reversal, altered-source refusal,
whole existing guard/launch/cleanup preservation,16 receipt-field mutations plus
image replacement, conflicting-mode refusal before artifact/Windows calls,
and preservation of the actual first cause/cleanup scope. These controls run no
compiler, Windows API, accepted model, inert helper or service. A focused actual
Windows successor execution remains required. An inert pass would establish
only its explicit profile/process/HKCU/cleanup scope; original Auth/Db/Map
service readiness, normal checksum/version policy and world authority remain
unqualified.

Official sources read for the candidate:

- [Owner of a New Object](https://learn.microsoft.com/en-us/windows/win32/secauthz/owner-of-a-new-object)
- [FileStream creation with FileSecurity](https://learn.microsoft.com/en-us/dotnet/api/system.io.filestream.-ctor?view=netframework-4.8.1)
- [TOKEN_OWNER](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_owner)
