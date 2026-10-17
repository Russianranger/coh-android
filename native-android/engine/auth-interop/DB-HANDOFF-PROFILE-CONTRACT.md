# Read-only profile prerequisites for an isolated authenticated DB experiment

This component qualifies metadata and bounded original-source functions. It does not admit a deployment, observe a channel, authenticate a new session, send a cookie or select a character. Accepted Auth-only `UserData=false`, shipping profiles and binaries remain unchanged. A new experiment needs a fresh encrypted session; historical successful login receipts cannot supply live credentials.

## Version and checksum policy

Original `DBServer/src/clientcomm.c::handleLogin` first rejects a mismatching protocol (`20110614`). It reads the full 16-byte checksum and cookie, then applies the checksum verifier. A checksum failure replaces the supplied version with a refusal string. For real authentication and a compatible version not starting `dev:`, the server forces version comparison even if the client requests skipping it. Comparison is case insensitive. Wrong versions produce the original WrongVersion/ WrongVersionPatcher refusal. The original separate branch suffix check applies when the client did not request skipping. The complete original function, packet grammar and post-login operations are not executed by this fixture.

The existing isolated checksum candidate compares all 16 bytes and refuses a missing reference. The original verifier's `sizeof(pointer)` guard skips verification on the tested ABI. The new policy matrix reuses that existing candidate and the exact original first login block; it substitutes bounded packet getters and a version provider. In each release and ASan/UBSan execution it checks 1,056 cases for each verifier: all development/normal, fake/real, client-skip combinations, valid and wrong versions, wrong protocol, each checksum bit and missing reference. Refusals additionally assert the original WrongProtocol command or WrongVersion command prefix emitted by the exact block. The candidate refuses all 256 checksum bit mutations in the normal real-auth combinations. Development or fake profiles still permit 384 mutation cases through the source's skip-version path. They cannot qualify this nondevelopment experiment.

`db_handoff_profile.declare_nondevelopment_policy` therefore requires real auth, matching bounded normal versions, an exact nonzero 16-byte checksum match and the exact candidate function identity. It deliberately refuses every `dev` version prefix (a narrower experiment policy than the source's `dev:` force-comparison test). Supplied version/reference hashes are metadata labels, not proof of their runtime contents. The immutable result always leaves actual version resolution, deployed DB binary verification and live admission false.

`getCompatibleGameVersion` calls `getExecutablePatchVersionInternal(regGetAppName())`. Actual version-file/application/registry resolution must be captured from the future owned DB process. A source hash or invented normal version cannot qualify that result. The candidate verifier must also be present in the actual isolated DBServer binary; this component does not build or replace it.

## Auth and game bit ownership

The oracle compiles the exact original `authUserBitMaskAuth`, `authUserBitMaskGame`, `authUserMaskAuthBits` and mask/OR block from `handleRecvGameData`. Each release and ASan/UBSan execution passes 397,313 checks, including all 1,024 single-bit positions for each input and both inputs, and deterministic mixed arrays. LeakSanitizer is disabled for these temporary host executables.

The source ownership masks overlap in **31 bits**. Correct merging masks each 128-byte input and ORs the results. The adapter does not invent exclusive ownership or overwrite precedence. The public masks are bound to the exact receipt and source blobs; forged dataclass mask bytes are refused. The resulting bytes are suitable for comparison with a future observed transaction, but do not prove message ordering or account ownership by themselves.

## Shard and channel declaration

Original AuthServer `CServerList::Load` reads the server table's ID, public and internal address; client port comes from that table when `dbHasClientPorts` is enabled. `SetServerSocketByAddress` matches the incoming socket address against the stored internal address and can assign multiple entries when addresses collide. `allowUnknownServers` can create an unregistered entry. The explicit-ID alternative is conditional on `gameServerSpecifiesId`. `handleVersion` and AS_SET_CONNECT establish further protocol/activation steps.

The read-only isolated declaration accepts at most 16 rows, unique IDs and internal addresses, explicit loopback IPv4 addresses, bounded ports, matching owner-generation labels, and the observed shard ID and peer-address labels. It requires unknown-server creation and explicit-ID mode disabled. Loopback-only and unique rows are deliberate experiment restrictions; this does not model every supported original deployment. The immutable result leaves live channel ownership, shard activation and deployment admission false. A supplied generation digest is an owner label, not authenticated provenance.

## Remaining live prerequisites

A future reviewed driver must create an owned disposable full `UserData=true`, nonqueue profile with the matching explicit user_data row; prove its SQL seed and cleanup; observe a registered shard/channel and activation; exercise the original auth/game merge and message order; bind a fresh one-shot UID/name/cookie match; observe actual nondevelopment version resolution; and use the corrected full-checksum DB binary and exact checksum reference. It must retain wrong protocol, wrong version, bad checksum, missing reference and wrong cookie refusals. Existing auth-only success proves none of these DB/Map operations. No Windows service, Android or physical qualification is claimed by this change.

## Reproduction

From the repository root:

```sh
python3 native-android/engine/auth-interop/deployment/qualify_auth_bit_merge.py --source-root . --output /tmp/auth-bit-merge.json
python3 native-android/engine/auth-interop/deployment/qualify_db_policy_matrix.py --source-root . --output /tmp/db-policy-matrix.json
python3 -m unittest discover -s native-android/engine/auth-interop/deployment -p test_db_handoff_profile.py -v
```

Original source tree: `f634e21e230009fa8edc91d15429cd4da69eee8c`. Exact receipts and source hashes are in `evidence/db-handoff-profile-contract-20261017/`. Android ARM64 build, emulator, Thor and live authenticated DB/Map acceptance: not performed for this standalone host metadata component.
