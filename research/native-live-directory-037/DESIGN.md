# Live per-directory client metadata: closed source prototype

This is an implementable alternative to persistent whole-tree census replay. It
has no production registration, source lease, current provider authority, or APK
publication authority. The prototype does not launch Game, Wine, FEX, PRoot or a
database. Ordinary `_AltStat`, `CreateFileA(GENERIC_READ, FILE_SHARE_READ |
FILE_SHARE_WRITE)`, by-handle information, and sharing/readability checks remain
the original implementation.

## Concrete implementation boundary

The unchanged `FolderCacheAddFolderToNode` enumerates one directory completely,
closes its handle, and then recurses into its child directories. Its row body
consumes the name, low size, write FILETIME and directory/readonly/hidden/system
attributes. Leave `FolderNodeAdd`, callbacks, exclusions, provider priority,
counting, links, hash membership and recursion intact. Replace only its scoped
enumeration provider with a current-directory service, after native admission.

The service captures directory names once and keeps the exact owned directory
descriptor open. It reads metadata when the consumer requests the next bounded
batch. It never retains metadata across directories, native processes, launcher
operations or reopen. No full census/proof/encode/recheck pass belongs on this
path. File bodies and player data are never read or changed by this service.

Wine b073 already sorts cached names by Unicode case-insensitive comparison,
then case-sensitive comparison, preserving dot aliases at the front. It obtains
current lstat/stat/xattr information while filling each successive 8 KiB
FileBothDirectoryInformation buffer. A name whose metadata lookup fails is
skipped; an overflow entry can be examined again on the next query. Our ASCII
packet geometry uses the 94-byte FileBoth prefix, UTF-16 name length and eight
byte alignment. Actual native conversions, short names, ignored inodes, dot
configuration and overflow lookup behavior remain qualification requirements.

The first usable Game-only stage should use current metadata batches, preserve
native order and all defined consumed fields, and restrict admission to the
known global cache/main thread, one verified loose provider and the five existing
selected branches. Keep arbitrary/unregistered providers on the original path.
No callback, update policy, PIG mounting, native freshness rule or file lookup is
relaxed by the batch reader. The protocol's tokens are correlation data; they do
not independently authenticate a provider or process.

## Bounded protocol and failure behavior implemented here

`coh_live_directory_batch.h` implements a 64-byte fixed header, 16-byte operation
token, 16-byte directory token, exact sequence/first-row ordinals, terminal flag,
explicit total length and canonical 328-byte row records containing 320-byte
WFD projections. A frame contains at most 85 rows and the 8 KiB NT geometry must
fit independently. Maximum wire/storage size is 27,944 bytes. A current directory
is bounded to 8,192 names; an oversized or unsupported directory is unknown and
uses the original provider before returning any row. The largest historical
directory has 6,852 names.

The cursor validates a complete private copy before returning its first row.
Malformed/stale/truncated/oversized/noncanonical frames authorize no row. Caller
transport storage can be reused without mutating the admitted frame. Frames
cannot replace a partially consumed batch. An initial failure allows ordinary
enumeration; once any row was returned, a failure permanently stops that cursor.
It cannot restart a partially consumed directory, reissue callbacks, duplicate
nodes/counters or revive after another valid frame arrives. The launcher must
fail startup, stop only owned native processes, preserve the database and export
current diagnostics. Actual report integration is not implemented by this
research header.

## Why the Android mapping gate is real

The audited .36 runtime lock pins Android Wine b073859675060c9211fcbccfd90e4e87520dc2c2,
FEX 320c5f18475b0c8a7e99c51a5fdc5b5e35b147ab and their full runtime archive SHA
030f38066af7b786c142e199cb84adec037840b0f029338849e43f99203a93e1. Hosted
capture's distro Wine is a different, unauthenticated source/build mapping.
Proving fields under that distro does not establish Android runtime parity.

The current Android launcher uses PRoot 7266fb3e8516535682f5a9c8f3a7e70f6506eddb
with `--link2symlink`, guest UID 1000, a `/state` bind and the exact imported
generation bound under `/opt/coh-game-data/<generation>`. `prepare_worktree`
creates absolute guest-path symlinks. A helper outside PRoot cannot raw-stat
these paths: the same `/state/...` or imported guest path does not exist in the
native host view. The fresh kernel control demonstrates this failure.

A prospective native ARM service must receive the actual finalized bind recipe
from its owning Java operation and own FDs for those exact app-private roots.
It resolves only admitted guest targets under those roots, reproducing longest
guest binding, relative links, directory ancestry and the pinned link2symlink
view. Unknown root/alias/legacy l2s intermediates are unknown, never proof of
absence. Exact PRoot l2s source can replace the stat result and link count;
ordinary root-mode fake UID mapping changes UID/GID, while the separate USERLAND
configuration can change mode. The present build recipe does not enable
USERLAND. These source observations do not replace a real native PRoot test.

Each opened directory must bind to the actual consumer's native handle/view,
including case resolution, share/access checks and replacement races. Keep a
real Wine directory authorization handle. A Game-only service that precomputes
the whole directory cannot claim identical races to successive Wine buffers.
The bounded protocol removes this avoidable early read, but exact observation
boundaries still require controlled native mutation comparisons. A stronger
implementation can keep Wine's own name cache/handle/filter/projection and
offload its raw metadata acquisition to ARM; that preserves Windows semantics
more directly but requires a separately built and fully qualified Wine runtime.
Neither route is enabled in this prototype.

## Fresh controls and measurements

The portable C program uses the complete actual extracted stock constructor and
`FolderNodeAdd` against the SHA-authenticated historical 55,574,000-byte source
packet from failed run 38505762421. All five branch paths produce identical
parents/children/tails, sibling order, provider, file index, timestamp, size,
directory/writeable/hidden/system/seen/hash/delete flags, file/folder counters
and namespace digest. It consumes 167,937 rows and 9,315 batches; the five extra
packet rows belong to its partial root anchor and are not constructors. Largest
actual wire batch is 22,696 bytes. Fourteen decoder refusals and four terminal
failure/private-custody controls pass. The current owned cursor is 28,040 bytes
on this 64-bit portable ABI; actual 32-bit native allocation remains unmeasured.

`portable-live-parity-results.json` records actual C process wall/CPU/RSS.
It deliberately loads the entire 55.574 MB historical packet and keeps two
controlled node trees for comparison; its roughly 77 MiB RSS is not live-service
memory or Game memory. The live cursor itself needs no whole packet. Directory
name storage is separate: the largest captured directory uses 213,581 raw name
bytes; its index/allocator/runtime overhead has not been measured. The 8,192-name
bound permits at most 2,129,920 fixed 260-byte name slots before overhead.

Eight historical Linux temporary-file controls independently show current metadata
after the preceding batch, fixed names after open, deletion before metadata,
held-FD identity after replacement, outside-hardlink mode change, preexisting
mmap change, failure of raw host guest-link resolution, and the zero directory
size projection. They establish controlled POSIX behavior. They do not execute
Wine WFD conversion, native `_FileTimeToUnixTime`, socket IPC, PRoot or FEX.
Both constructor paths deliberately use the same timestamp fixture stub;
native timestamp conversion remains an explicit gate. Callback-enabled native
admission has not been qualified; the proposed initial stage admits no callbacks.

The follow-up model closes its exact owned directory descriptor if initial
listing or sorting fails before construction completes. One fresh injected EIO
control observes EBADF on that descriptor, confirms the original exception is
preserved, and confirms an unrelated guard descriptor remains open. The eight
earlier successful-path results and their exact original model/report text are
retained as historical evidence inside `controlled-live-batch-results.json`.
The C/header/generator and their earlier parity results are unchanged and were
not rerun for this Python-only cleanup repair.

The earlier full source proof took 56.079222 seconds: capture 29.161624,
recheck 26.857710, encode 0.059885. Its explicit producer API requests total
513,703 per pass, 1,027,406 for both passes. These are API request counts, not
measured kernel syscall counts. This C decoder performs no filesystem proof
requests and no corpus encoding; the controlled parity fixture's one input
packet read is separate. The future live ARM service still performs current
directory enumeration/stat/xattr requests. Their wall time, syscall counts,
memory, IPC overhead and actual net startup saving have not been measured.
No 56-second speedup, sub-minute client startup or Thor benefit is claimed.

## Next independently qualified stages

1. Build a standalone native POSIX helper against controlled direct/relative/
   guest-absolute/legacy-l2s links, xattrs, case aliases, directory replacement,
   permission/access failures and mutations at buffer boundaries. Bind exact
   operation/helper PID/UID/start-time and opaque consumer identity separately.
   Keep metadata live; measure total helper startup and request work.
2. Run the actual retained Android Wine/FEX/PRoot runtime and WFD probe against
   the same finalized roots. Match consumed fields, ordering, native timestamps,
   row omissions and handle/error semantics. Test socket failure before/after a
   row and verify preserved SQL plus usable outer diagnostics. Distro Wine alone
   is insufficient. Unknown mappings retain the original provider.
3. Compile one opt-in Game constructor stage only after those gates. Compare
   exact namespace/node/freshness/PIG/renderer/login/native save behavior and
   whole-operation preparation + Game time + helper memory. Leave `_AltStat`
   unchanged. Publish only if native qualification and actual critical-path
   measurements support it; physical Thor targets remain acceptance tests.

Primary source references are the locally pinned repository files recorded in
`source-freeze.json`, Wine's b073 kernelbase/file.c and ntdll/unix/file.c, and
the recovered exact Git blobs under PRoot's pinned source. These research files
are additive and isolated from the existing root, main, native donors and draft
PR #1. No SDK or native Game/MapServer binary is rebuilt here.
