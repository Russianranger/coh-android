# Closed native ARM current-directory backend

This stage implements a read-only current-metadata backend and explicit JNI
lifetime. It has no registration, APK packaging, source/provider authority,
Game activation, database access, process launch or physical performance claim.
It is based on `270ad89b4f2f85333692f54446901cc4da3cb4e4` and the reviewed Wine
`b073859675060c9211fcbccfd90e4e87520dc2c2`/PRoot
`7266fb3e8516535682f5a9c8f3a7e70f6506eddb` field recipe.

The owner supplies only the exact finalized directory bind table and actual
host device/inode/UID pins. The C core holds O_NOFOLLOW roots, verifies their
pathname and held identities before and after each batch, and resolves ordinary
ASCII paths, relative links and guest-absolute links through that table. Root
and leaf UID/device must match the actual process and one physical filesystem.
Host absolute symlink resolution, unknown guest roots, unsupported .l2s aliases,
cross-device or foreign-UID objects, invalid names and special files refuse.
No generic case conversion or short-name guessing occurs. Narrow branch-case
canonicalization still requires the native authorization inode join.

Names are snapshotted once, with `.`/`..` first and ASCII uppercase fold then raw
case tie. Metadata is acquired only while filling the requested 8 KiB-equivalent
batch. Overflow rows are reacquired on the next request. Current readonly,
hidden/system DOS xattrs, directory zero size and last-write FILETIME are emitted
for the literal FolderCache constructor. Creation/access/alternate/reserved
fields are canonical zero and explicitly nonauthoritative. Unsupported xattr
formats/errors conservatively refuse instead of guessing absence or attributes.
Ordinary Game `_AltStat`, native timestamp conversion and leaf reads stay stock.

The actual Wine directory authorization handle is mandatory outside this core.
OPEN must compare its complete native FileInternalInformation inode to the
helper's exact held-FD identity before returning rows. Registered same-device
custody supplies the device join. Tokens are correlation fields, not authority.
The root service must reject file/passthrough bind shadows and unknown native
ignored identities. These are additional admission gates; this core does not
infer them from a guest path string.

Registered pathname semantics are conservative: if the resolved requested
directory or its canonical guest target changes, the core refuses. A held FD
surviving rename is not evidence that the PRoot pathname still identifies it.
Before the first emitted frame, unsupported scope may use the stock provider.
After any frame containing rows, every error is terminal. It cannot return
success EOF, restart the directory, duplicate callbacks or authorize relocation.

Bounds are 32 directory roots, 16 cursors, 8,192 names including dot aliases,
259 bytes per ASCII basename, 1,023 bytes per guest/host path and 16 followed
symlinks. One namespace owns at most 32 MiB tracked C heap, including temporary
growth allocations. The JNI facade permits one namespace per process, rejects
stale generation handles and closes all owned cursors with the namespace.
Creation additionally owns at most64KiB of native root-string copies. Java frame
arrays and VM/thread overhead are outside the core heap counter; this is not a
total RSS/PSS bound. A
frame is 64-byte COHLIVE1 plus at most85 canonical328-byte rows, at most27,944
bytes. Metadata acquisition and namespace validation add real native work; they
are not described as zero-cost cache reuse.

`test_native_live_directory_core.py` builds and executes real Linux C functions
with test-only allocation/open/list/stat/readlink/xattr failures and controlled
kernel mutation fixtures. The test interposer is never linked into JNI delivery.
`native_live_fixture.c` executes the same finite read-only core under the host
libc and a pinned NDK27.2 static Bionic ARM64 build through QEMU user mode.
`NativeLiveDirectoryFixture.java` loads the actual host JNI library and checks
identity, live batches, stale handles, exceptions and namespace cleanup.

The CI lane compiles the Android ARM64 shared JNI library separately and audits
ELF architecture, eight JNI exports and libc-only dynamic dependencies. Static
Bionic execution under Linux/QEMU proves only that compiled core/ABI fixture;
it is not Android OS, actual app UID, retained PRoot/Wine/FEX, network service,
native SDK/Game, full corpus or Thor qualification. Exact retained-runtime WFD
field/batch/native-authorization fixtures and consumer/report integration remain
mandatory before opt-in Game compilation or publication.
