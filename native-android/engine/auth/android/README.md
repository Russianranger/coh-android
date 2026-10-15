# Public Android crypto dependency for native authentication

This additive build makes the existing `coh_auth_openssl.c` provider linkable
against an application-owned Android `libcrypto.a`. The provider, accepted auth
wire kernels and source-derived cryptography are unchanged. This is a crypto
integration contract; it does not establish an authenticated server session.

## Reviewed dependency

The [official source index](https://openssl-library.org/source/) identifies
OpenSSL **3.5.9**, released **29 September 2026**, as the current 3.5 LTS patch.
The [release policy](https://openssl-library.org/policies/releasestrat/) maintains
3.5 through **8 April 2030**. These facts were checked on 15 October 2026.
`openssl-source.json` pins the official archive URL, its independently downloaded
published SHA256 and the source license SHA256. The official archive was
downloaded and its hash matched that published checksum. This is hash pinning,
not a claim of PGP signature verification.

OpenSSL 3.5 is [Apache-2.0 licensed](https://openssl-library.org/source/license/).
`OPENSSL-LICENSE.txt` is the exact release license. Keep it with redistributed
libraries and APK notices. Generated build output also includes the license.
No third-party source tree, binary or generated object is committed here.

The driver follows the release's
[Android notes](https://github.com/openssl/openssl/blob/openssl-3.5.9/NOTES-ANDROID.md):
explicit Android targets, `ANDROID_NDK_ROOT`, NDK toolchain PATH and selected API.
It does not use Android's private platform `libcrypto`. OpenSSL's built-in
default provider supplies MD5, SHA512 and RSA-OAEP SHA1/MGF1-SHA1, while its
constant-time BIGNUM path provides the original source's fixed DH group.
These legacy primitives are required for source protocol compatibility; this
build makes no FIPS claim.

## Build and qualify

The driver requires Linux, Python 3.11.4+, curl, Perl, make and the public Android
NDK. The recorded build uses NDK **28.2.13676358**, API **26** and produces both
ARM64 and x86_64 Android Bionic artifacts:

```sh
python3 native-android/engine/auth/android/build.py \
  --ndk /absolute/path/android-ndk-r28c \
  --output /absolute/path/crypto-build --jobs 3
```

Extract the NDK ZIP with a tool that preserves its Unix symlinks. A Python ZIP
extraction in this environment initially made 31 link placeholders into regular
files; restoring their verified archive metadata fixed the linker path. The
completed ARM64 dependency build was preserved and only its final link retried.

Downloads go into a scratch cache. `--source-archive` supports an already
downloaded archive, with the same mandatory pin check. Existing outputs cause
an explicit error; `--rebuild` deliberately replaces only the selected generated
ABI outputs and their build trees. Every ABI receives its own extracted source
tree. The driver never mutates the accepted provider or a shared source tree.

`no-shared no-module no-dso no-engine` produce a static, self-contained crypto
dependency. Automatic external configuration loading is disabled. No provider
module, host OpenSSL config, host compiler overrides or dynamic `libcrypto.so`
is admitted by this build. Source date and compiled-in installation paths are
fixed; compiler and source versions plus artifact hashes are recorded. This
supports reproducible rebuilding with the recorded toolchain; cross-host byte
identity is not asserted without a separate comparison.

Each ABI output contains:

| Artifact | Purpose |
| --- | --- |
| `include/openssl/` and `lib/libcrypto.a` | Public headers and pinned Android crypto |
| `lib/libcoh_auth_android_crypto.a` | Existing provider only; links to the accepted auth/core modules |
| `lib/libcoh_auth_android_check.so` | Complete Android compile/link check with no undefined symbols |
| `test_auth_android` | Existing 1,920-check suite plus 10,000 malformed-input cases |
| `receipt.json` | Source, toolchain, configuration, artifact hashes and explicit acceptance boundaries |
| `OPENSSL-LICENSE.txt` | Exact pinned dependency license |

The existing `auth/check.py --sanitize` remains the host oracle. Its raw output
correctly describes only its own host run; its historical
`android_crypto_provider_available: false` field does not describe these
separate Android artifacts. The host oracle independently compares 80 credential
derivations, 64 DH secrets and 140 original-source framing cases.

An explicit Android execution is a separate qualification step:

```sh
python3 native-android/engine/auth/android/run_android.py \
  --adb /absolute/path/adb --serial emulator-5554 \
  --artifacts /absolute/path/crypto-build/x86_64 \
  --output /absolute/path/crypto-emulator.json
```

The runner verifies the executable hash, ABI and emulator/physical classification,
executes the unchanged auth suite, removes its isolated temporary device files,
and writes a separate execution receipt. Physical-device execution requires
`--device-kind physical`; it never automatically marks Thor acceptance. The
suite exercises real Android entropy, DH pair exchange and peer rejection,
digest derivation, randomized RSA-OAEP encrypt/decrypt with disposable keys,
framing, bounded serializers and malformed cases. It uses no account or network
server. Do not turn a passed crypto test into a login claim.

## Integrated build contract

After adding the accepted `engine/auth` target, add this directory and set
`COH_OPENSSL_ROOT` to the selected ABI's output directory. CMake checks the
recorded ABI, exact dependency pin and static archive hash before defining
`coh_auth_android_crypto`. Link that target into the native client, then pass
`coh_auth_openssl_provider()` to the existing auth/transport interfaces.

The caller continues to own private-key/session wipe, socket lifecycle,
authentication state and protocol compatibility. There is no encryption
downgrade. AuthServer/DbServer/MapServer interoperability, full character
selection and live replication still require separate real-server evidence.

Recorded `evidence/` covers both Android ABI builds, public CMake target links,
ABI/pin intake rejection and the unchanged host suite with ASan/UBSan. Android
execution is recorded separately when run; a cross-built executable alone is
not emulator qualification. A separate read-only review found no concrete
build/link blocker or acceptance-status overclaim.
