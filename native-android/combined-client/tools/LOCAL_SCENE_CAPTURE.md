# Owned local scene capture

This nonshipping POSIX executable supplies the native receiving half of a future
same-transaction MapServer comparison. It uses the existing local DB session,
selects a wire slot from the actual character list, and lets the opaque DB owner
carry the selected DBID and one-use Map handoff. There is no raw DBID, cookie,
server-address override, fabricated authorization, or application completion ACK.

Build and qualify from the repository root:

```sh
python3 native-android/combined-client/tools/check_local_scene_capture.py \
  --output /tmp/coh-local-capture-build --test --sanitize
```

For an authorized disposable loopback server already running with the documented
local development policy, put its existing account name in a private regular
file owned by the invoking user, mode 0600. The executable accepts these ordered
arguments:

```text
coh-capture-local-scene PORT WIRE_SLOT ACCOUNT_FILE NEW_OUTPUT_DIR TIMEOUT_MS VERSION ENCRYPTED COMPRESSED
```

Timeout is bounded to 600,000 ms. Version is 0..5; the final two settings are
explicit booleans matching the disposable server's qualified transport policy.
The output directory must not exist. The client streams the exact synchronous
borrowed decoded allocation to `groups.bin`, hashes those same bytes, and retains
only numeric metadata. `capture.json` commits after both owned sockets close.
It contains the original logical bit end, post-command cursor, alignment,
transport/message/selection observations, owner-derived selected DBID, footer
CRCs and allocation SHA256. Source-build/run provenance comes from the separate
build receipt and runtime supervisor; connection IDs are correlation data.

Any callback, timeout, signal, write, flush, report or cleanup failure refuses
success and removes only provisional files created by this run. Existing output
directories, files and symlinks are refused. Account values are wiped and are
absent from console output and capture metadata. No copied packet is retained
after callback return, and no global memory/RSS measurement is claimed.

The host qualifier uses the existing scripted, source-derived UDP peer. Release,
ASan and UBSan each pass 39 checks covering the large compressed scene, true
handoff ownership, exact hash/bit scope, permissions, destination preservation,
invalid account files, deadline and signal cleanup. ASan leak walking is disabled
for this executor; this is not a leak-sanitizer qualification. It does not execute
a real MapServer, Android application or Thor session. Source generation, actor
identity, authenticated login and world authority remain false. A live source
capture plus independently admitted build/run/session association and complete
resource/player transactions are still required before world publication.
