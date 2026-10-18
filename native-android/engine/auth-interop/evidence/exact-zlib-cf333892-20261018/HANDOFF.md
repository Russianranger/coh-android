# Exact Chromium zlib source recovery

The missing source input for the separately authorized Auth-to-DB diagnostic probe is recovered from the repository pinned by the existing project recipe: `https://chromium.googlesource.com/chromium/src/third_party/zlib`, commit `cf333892c34ab6dbaed37c38a1d5aa6da7b2f99d`. This is source admission only. No patch was applied, no library was built, no compiler or application runtime executed, and no Windows platform closure was qualified. Existing source trees, archives and profiles are unchanged.

The immutable upstream archive and primary Gitiles commit/root metadata were downloaded once on 2026-10-18. Their combined 314,201 bytes are below the authorized 20 MiB cap. The archive contains 111 regular files (1,216,944 bytes), 32 headers, and all 21 translation units selected by the existing x64 SIMD CMake patch. It contains no symlinks, hardlinks or other special file entries. Every Git blob ID, executable mode and recursively reconstructed tree is recorded in `admission.json`. The computed root `62224db151a2af4f2c66110d634ef8dc3607a155` equals the exact primary commit's tree ID; the complete root entry list also matches the primary tree JSON.

| Retained bytes | Size | SHA256 |
| --- | ---: | --- |
| `source.tar.gz` | 306,531 | `2f776d3abe636e302a98216fc81410622feb1be958315223d0d3442496365938` |
| `commit.json` | 1,645 | `f27da76043e1ffc76c0da5f07d36adc3b34b659cf98ae092ae897ef1d9317eda` |
| `tree.json` | 6,025 | `2b03a4e4d7edd236b5e1185b5a76013af77135355cd4342e8f347a5cbe7bb527` |
| `admission.json` | 51,645 | `d104eafafe30e26d63072adef5a454e86d83d7280513c1add3d8478b1feebfd6` |
| `Zlib.cmake` | 281 | `dbabf749271e73e4bb5eb62c5d914ace1259520f6e8b52bbcf2600371b5d50be` |
| `chromium-zlib-cmake.patch` | 2,337 | `55273bf390fd1093718d28f1141979fa97d23d1f071a1d90653f801cd425a107` |

Primary endpoints:

- `https://chromium.googlesource.com/chromium/src/third_party/zlib/+archive/cf333892c34ab6dbaed37c38a1d5aa6da7b2f99d.tar.gz`
- `https://chromium.googlesource.com/chromium/src/third_party/zlib/+/cf333892c34ab6dbaed37c38a1d5aa6da7b2f99d?format=JSON`
- `https://chromium.googlesource.com/chromium/src/third_party/zlib/+/cf333892c34ab6dbaed37c38a1d5aa6da7b2f99d/?format=JSON`

The retained project recipe and patch are byte-exact copies of the existing files, whose hashes were checked before and after recovery. The x64 recipe includes the original SIMD/optimized sources and flags; no alternate zlib version, generic replacement or unadmitted DLL is substituted. Future Windows compiler, SDK/intrinsic headers, flags, objects, linker inputs and execution still need their own admission. The old 3dsmax import library and historical checkout logs were not promoted into build authority.

`admit.py` reproduces the source-only archive/blob/tree/header/patch checks without downloading, extracting, applying a patch, building or executing source code. It reads only the retained evidence and existing project recipe/patch. An optional materialized root checks the already recovered local copy against the exact inventory. Run from any directory:

```sh
python native-android/engine/auth-interop/evidence/exact-zlib-cf333892-20261018/admit.py
```

The actual unpacked source remains available for D at `/workspace/scratch/7ed1da2a7e55/zlib-exact-cf333892/source`. That absolute path in the original admission receipt describes the recovery location; it is not required for portable archive readmission. The immutable archive plus Git mappings reconstruct the original source without retaining a second full file copy in git.
