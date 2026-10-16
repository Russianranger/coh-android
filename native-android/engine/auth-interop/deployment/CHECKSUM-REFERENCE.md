# Isolated client checksum reference candidate

The exact public 0.13.34 donor APK was downloaded and its complete bytes verified.
`inspect_client_reference.py` reproduces bounded read-only inspection from that
APK; it never extracts files into a server directory, creates an alias, starts a
service or approves a compatibility profile. Its receipt keeps
`deployment_profile_admitted=false` and `native_reference_compatibility_approved=false`.

| Inspected input | Identity |
| --- | --- |
| Public donor | `coh-atlas-gameplay-v0.13.34/COH-Atlas-Gameplay-0.13.34.apk`, 42,048,020 bytes; SHA256 `c2d859621476e22add673a76c4b6aae65c2143671e50c085d020108b6e19d95e` |
| Nested client archive | `assets/runtime/client-runtime.zip`, 8,702,383 bytes; SHA256 `5636fe9b3d45c313b062ac83ba954bfb3b1b160af4aec1b34f046c8c2b421509` |
| Client executable | `CityOfHeroes.exe`, 9,499,648 bytes; SHA256 `5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b` |
| Whole-file MD5 | `3102c83178c9bca4385aa9bcc5e003bb`; independently matched Python hashlib and OpenSSL CLI |
| Imported original source | `0b75ade0c801735e10c5798f641948a45cc50488` |
| Declared final client build | `c512e912a004b66886a7667640aa1a967e95de64`, role `bounded_client_render_queue`; canonical manifest SHA256 `84a9a9d5d56d819aae04731d5dcf2a0a8ef4c119918a15b63622cef1f361a8b1` |

Both package-level and final-build manifests identify the exact inspected client.
This executable includes documented graphical-client changes; it is not described
as an unchanged original binary. The inspector validates original source hashes
and records exact relevant function hashes separately. Whole-file MD5 was measured
with public implementations; no independently executed original CryptoPP or
`checksumFile` comparison is claimed here.

```sh
python3 native-android/engine/auth-interop/deployment/inspect_client_reference.py \
  --source-root . --apk /private/COH-Atlas-Gameplay-0.13.34.apk \
  --output /tmp/client-reference-inspection.json
COH_AUTH_REFERENCE_APK=/private/COH-Atlas-Gameplay-0.13.34.apk \
  python3 -m unittest discover -s native-android/engine/auth-interop/deployment \
  -p 'test_client_reference.py' -v
```

The two artifact tests explicitly skip when this public APK is not supplied;
skipping does not qualify a reference. Local execution supplied the exact pinned
APK and passed the positive scope and altered-identity refusal controls.

The original graphical client `dbConnect` hashes its executing file and sends all
16 digest bytes. Original DB `initGameChecksum` instead opens `Ouroboros.exe` in
the parent of `fileDataDir()`. `cryptMD5Final` emits digest bytes directly without
another endian swap. The native probe requires an explicit nonzero 16-byte
checksum; using a graphical-client checksum represents a declared interoperability
reference, not a checksum of the native ELF/APK. That compatibility policy needs
an explicit source-bound isolated profile before service execution.

The inspected client archive contains neither `Ouroboros.exe` nor `version.ini`.
A byte-identical server-side alias is therefore only a proposed deployment step,
not an existing accepted reference. No alias was created. A normal version cannot
be inferred from the PE hash or source commit. Original version resolution can
return a development value depending on installation/data context, then consults
`version.ini` and registry state. The isolated profile must demonstrate its actual
non-`dev:` `getCompatibleGameVersion` result, match the native request explicitly,
disable fake authentication and pass version/checksum negative controls. Missing
version/reference inputs block deployment; they are not defaults to bypass.

## Reversible DbServer checksum build plan

The existing `checksum_candidate.py` emits the exact separately declared patch:
compare all 16 digest bytes and reject a missing checksum file. Its original and
candidate source controls already passed both host and Win32 executions. It does
not patch the accepted DbServer, and the original defect must remain distinguished
from the corrected candidate.

For a new build, the coordinator must first bind the chosen disposable DbServer
source/overlay manifest, persistence fixture, normal version policy, explicit
reference alias and native compatibility policy. The public donor's PostgreSQL
and startup overlays are not silently substituted by an unmodified MSSQL target.
Preserve the already compiled baseline executable and its receipt; do not rebuild
that unchanged original binary. Archive the exact source into a new private
directory, verify every baseline overlay hash, and apply only the declared
checksum patch after checking its original file identity. Build the resulting
`DbServer` target as Win32 OptDebug and record patch, source tree, CMake inputs,
build logs, PE/import identity and new binary SHA256. Keep it in that disposable
directory; rollback is deletion of the owned candidate, without copying anything
to the Thor or accepted runtime.

No corrected complete DbServer executable was built in this continuation. The
local environment cannot execute the qualified Windows/MSVC build, and the
required native/reference/nondevelopment-version service profile is not yet
established. Compilation alone would not approve that profile. Before a real
account run, independently execute exact native/original packet controls against
the corrected binary: valid request, invalid protocol/version, each changed
checksum byte, absent checksum file, wrong password/account, corrupt encrypted
frame, stale/reused auth cookie and selected DBID binding. The native probe also
needs a qualified Windows or WSL execution environment alongside the services.
Only the actual encrypted account exchange and authenticated DB-to-Map handoff
can advance the real-authentication gate.
