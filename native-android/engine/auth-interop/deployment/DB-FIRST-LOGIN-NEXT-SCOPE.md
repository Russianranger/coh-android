# Original DB login and empty-slot creation: next source scope

This is a read-only source proposal after actual registration run `39081746280`.
It does not change the selected-play scope, source policies, binary, registry,
installation files or profiles. Byte pins for 13 original files, 22 functions,
five native files and four retained inventories are in
`../evidence/db-first-login-next-scope-20261018/audit.json`.

## Genuine version and checksum inputs remain missing

`AppVersion.c::getExecutablePatchVersionInternal` tests
`!isExecutableInInstallDir() && fileIsUsingDevData()` before loading
`version.ini`. The latter predicate caches the absence of the exact CWD path
`./piggs/texts.pigg`. `dbinit.c` calls `FolderCacheChooseMode()` before parsing
`-productionmode`; that flag changes `isProductionMode()`, whereas the version
provider calls `fileIsUsingDevData()` directly. Neither the flag nor a version
file alone prevents the original development-return branch.

A source-consistent future alternative is an ordinary **owned installation**
association: the private nonce `ClientProject` registry key's original
`Installation Directory` value equals the actual Db executable directory.
That would let the provider reach its original version-file lookup without
changing the development FolderCache mode. A helper would need to refuse a
preexisting key, use and verify the actual Win32 registry view, install and
read back only that nonce-owned value before process startup, and delete and
verify absence during teardown. It must leave other project keys unchanged.
This association supplies no version value and is not currently admitted.

The remaining genuine input is an exact independently identified installed
`version.ini` value, or qualified original `CurrentVersion` provenance, matching
the actual same-process provider result and native request. A package release
label, source/build hash, PE resource version or invented experiment token does
not establish that provider input. Overrides, the missing-registry sentinel and
development values remain refused. Install all admitted inputs before process
startup; both installation and version-file lookups have original caches.

The original `initGameChecksum` opens `Ouroboros.exe` beside the main data
directory and hashes the complete file. The admitted candidate compares all
16 bytes and refuses a missing reference. The native request needs a genuine,
exact, independently admitted reference and an explicit native interoperability
policy. Neither a made-up checksum nor relabeling an unapproved file is part
of this proposal.

The independently rehashed retained `client-runtime.zip` is 8,702,383 bytes,
SHA256 `5636fe9b3d45c313b062ac83ba954bfb3b1b160af4aec1b34f046c8c2b421509`.
None of its 22 members is `version.ini`, `Ouroboros.exe` or `texts.pigg`.
The retained local donor APK copy is truncated and was not opened or rehydrated.
`thor-asset-index.json` identifies a genuine 683,463-byte `texts.pigg` with
745 entries, but explicitly records no payload or integrity check. The later
foundation receipt pins 101,842 bytes of metadata, not the whole PIGG. No local
whole payload or full-file SHA was found in the two retained scratch roots.
Historical HTTP403 inventory entries make no current availability claim.
No download is needed to preserve these bounded findings.

## Small authentic native protocol steps after input admission

1. A new private probe must retain its own current `CohLoginAuthorization` and
   bind the actual selected shard, account, UID and cookie directly to
   `coh_db_session_begin`. Do not use `begin_local`, serialize a grant, import a
   prior selected-play receipt or treat the public `verified` attestation field
   as authentication. The current selected-only probe deliberately wipes its
   grant and cannot donate a later session.
2. The original `handleLogin` enforces protocol, checksum and version before
   calling `authValidLogin`. A same-process version observation still needs an
   actual qualified channel. The existing ServerMonitor body contract excludes
   TCP framing; it is not an executable observer. The original
   `WrongVersionPatcher` rejection is another source-defined result path, but
   any private observer for it would be a new protocol scope with its own
   bounded parser and fresh Auth ownership. It is not an existing result.
3. Admit a complete genuine `SEND_PLAYERS` list with a matching nonzero UID.
   The normal paid fixture already resolves to original VIP status and the
   original default 12 base slots; no new entitlement or character row needs
   to be fabricated.
4. Propose an additive native session creation API separate from existing
   character choice. It may accept only an actual parsed, unlocked empty slot,
   a bounded nonempty name and a source-defined creation location. It reuses
   the existing `coh_db_choose_encode` wire grammar. The original server
   validates/reserves the name, checks available slots and allocates the DBID
   inside its empty-slot `CHOOSE_PLAYER` branch. Source-based controls must
   cover nonempty/locked/visitor/out-of-range slots, stale list/session state,
   duplicate creation, cancellation and cleanup before this API can run.
5. The current registration stage owns no Launcher or MapServer and starts with
   `-start 0`. Original creation calls `setNewMap`; an unavailable launcher can
   return `NoLaunchersRunning` and delete a just-created container. An actual
   Map cookie appears only after a genuine MapServer receives the original
   container and returns its response. A separately pinned owned Map runtime
   and real map data are therefore required before Map handoff. Preserve the
   existing opaque session/selection generation and one-shot handoff owner;
   neither a generic link ID nor a caller-supplied DBID supplies authority.

No original source function, compiler, registry API, native protocol, server,
character creation or Map transaction was executed for this review.
