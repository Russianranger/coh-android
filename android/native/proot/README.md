# PRoot native launcher build

`tools/android/build_proot.py` builds the two executable files packaged under
`lib/arm64-v8a/` in the diagnostic APK. Android extracts these files to
`ApplicationInfo.nativeLibraryDir`; the supervisor executes `libproot.so` and
sets `PROOT_LOADER` to `libproot-loader.so`. These are executable ELF files, not
JNI libraries. Keep `android:extractNativeLibs="true"` and legacy JNI packaging.

The pinned [Termux PRoot source](https://github.com/termux/proot/tree/7266fb3e8516535682f5a9c8f3a7e70f6506eddb)
includes `--sysvipc`, `--kill-on-exit`, `--link2symlink` and guest UID/GID mapping.
No Termux app is needed. Use one PRoot lifecycle with `--sysvipc`,
`PROOT_NO_SECCOMP=1`, a private `PROOT_TMP_DIR`, and `-i 1000:1000` for the
PostgreSQL diagnostic. Guest UID mapping does not grant Android root privileges.
The rootfs must provide a passwd entry for guest UID 1000. Stop PostgreSQL before
stopping the owning PRoot process. Separate PRoot invocations do not share the
emulated SysV IPC namespace.

## Source and modifications

- PRoot commit `7266fb3e8516535682f5a9c8f3a7e70f6506eddb` is distributed under
  GPL-2.0-or-later, with individual source notices retained. Its `COPYING` records
  STMicroelectronics and other contributors. The complete exact Git tree is
  preserved in the generated corresponding-source bundle.
- [talloc 2.4.3](https://www.samba.org/ftp/talloc/talloc-2.4.3.tar.gz), SHA-256
  `dc46c40b9f46bb34dd97fe41f548b0e8b247b77a918576733c528e83abd854dd`, supplies the
  statically linked allocator. Its library source is LGPL-3.0-or-later; retain
  the full source archive and its per-file notices, including `talloc.h` and
  `lib/replace/`. The output bundles include these sources and the exact rebuild
  recipe rather than relying on the continued availability of a download URL.
- `0001-sysvipc-memfd.patch` is retained from
  [TRASC commit b3c9ed0d62f8b9584131897b0bd5269a3ddd4c2d](https://github.com/Russianranger/trasc-server-android/blob/b3c9ed0d62f8b9584131897b0bd5269a3ddd4c2d/native/proot-sysvipc.patch).
  It backs emulated SysV shared memory with `memfd_create` and `ftruncate` on
  modern Android, where the old `/dev/ashmem` route is unavailable. PRoot's
  GPL-2.0-or-later terms and source attribution apply to these modifications.
- The header and loader-offset patches reproduce the small compatibility fixes
  in that repository's pinned `scripts/build-proot.sh`. They add the missing
  `string.h` declaration and replace GNU-awk-specific symbol parsing with Python.
  The generated loader helper is GPL-2.0-or-later. No optional acceleration or
  graphics patches are included.
- The Android talloc cross answers follow the same pinned TRASC recipe, derived
  there from the Termux talloc build recipe. Android NDK **27.2.12479018**, API 26,
  and 16 KB ELF segment alignment are explicit build inputs. Linux CI uses the
  same PRoot modifications with its native ARM64 compiler and static talloc.

Run from the repository root on Linux:

```sh
python3 tools/android/build_proot.py --target android-arm64 --ndk "$ANDROID_NDK_HOME"
python3 tools/android/build_proot.py --target linux-arm64
```

Each target requires a new work directory. Android outputs are
`out/android/native/arm64-v8a/libproot.so` and `libproot-loader.so`; Linux outputs
are `out/android/native/linux-arm64/proot` and `proot-loader`. Each directory
also contains `proot-build-receipt.json`, copied license notices and
`proot-corresponding-sources.tar.gz`. Preserve the source bundle with published
binary artifacts. The receipt records exact source, patch, recipe and binary
hashes plus compiler identity. A successful build establishes packaging only;
the hosted guest smoke and Thor device run establish actual execution and
PostgreSQL/Win32 ODBC compatibility.
