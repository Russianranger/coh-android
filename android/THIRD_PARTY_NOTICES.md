# COH diagnostic runtime inputs

This diagnostic contains no game binaries or game assets. PostgreSQL runs as
ARM64 Linux/glibc code through a private PRoot filesystem; it is not a Bionic
port. Wine WoW64 and FEX translate the Win32 diagnostic programs.

- PostgreSQL: PostgreSQL License. The pinned source, license, exact build input
  and resulting files are recorded by `tools/android/prepare_pg_runtime.py` in
  the packaged `postgresql-build.json` and PostgreSQL overlay.
- PRoot and its loader: GPL-2.0-or-later; talloc: LGPL-3.0-or-later. The exact
  source and patch/build recipes are retained in `android/native/proot` and the
  PRoot source artifact produced by the Android workflow. See its packaged
  `proot-build.json` and `android/native/proot/README.md` for source pins.
- Debian Bookworm ARM64 environment: packages retain their copyright and license
  notices under `/usr/share/doc`. The unchanged binary and corresponding source
  bundle are pinned in `android/runtime-lock.json`, from the user's
  `lsb-android` release `runtime-probe-v1`.
- Wine 10: LGPL-2.1-or-later; FEX: MIT, with separately licensed dependencies.
  The unchanged `runtime-fex-v3` bundle includes notices under
  `/opt/wine/share/lsb-sources`; its corresponding Wine/FEX source bundle and
  component commits are pinned in `android/runtime-lock.json`.
- psqlODBC 18.00.0004: LGPL-2.0-or-later. The official x86 installer is unchanged
  and hash-pinned in `android/runtime-lock.json`. Its license and dependencies
  remain in the installed Windows prefix. Official source is available at the
  source URL in that lock file.
- The archive reader and SDK-only packaging approach are adapted from the user's
  `lsb-android` repository at `228fe927fd8668cd0cfcb5a7084882cd924557c0`.
  COH adds its own diagnostic, generation, shutdown and evidence handling. The
  PRoot patch attribution is recorded separately beside those patches.

The source URLs are included in the packaged lock file. No independent Android
or game compatibility is implied by these source or binary inputs. Build
artifacts retain PRoot source and PostgreSQL source/build records needed to
reproduce these packaged components.
