# New dormant guest-owner successor — not recovered revision 3

This directory is new source work after recovery from the October 14 execution
environment failure. It does **not** reproduce or replace the unrecovered
`android/guest/client_live_fixture_owner.py` revision 3 (28,072 bytes,
`e3b9dd1cbf830e52f4cdf09d38d6be117fae70882ed50e6ef7d6e3df2cf3a8d9`)
or its 27,980-byte test (`3a87e490c26c767a4a2dd07a0ed5cfd6f866fed960e1a78af82f289f6c2438d4`).
The old 44 local controls and earlier independent 41/37 counts are historical;
none is inherited by this new suite. Original staged source and pins remain
unchanged. No active guest/Android path, workflow, asset or runtime is modified.

Durable inputs were the execution block in `docs/HANDOFF.md`, the reviewed
fixture/control boundary in `research/native-live-client-fixture-037/source/`,
and the held-current-operation contracts in
`research/native-live-client-operation-037/`. Those inputs support a finite
POSIX custody prototype; they do not recover the missing Wine owner adapter.

`owner.py` creates a new exclusive disposable directory beneath an explicit
0700 current-UID parent. It holds nofollow/close-on-exec directory descriptors
for every ancestor and compares named/held device, inode, UID and mode around
operations. Private regular child documents require 0600, one link, current
UID/device, exact bounded size and unchanged inode/timestamps. Strict ASCII JSON
rejects duplicate/unknown keys, nonfinite values, wrong types and old operation
identities. Membership scans stop after nine entries. Documents are bounded to
4 KiB, and private redaction memory is bounded to 128 nonce values.

At most **eight tickets may be issued for the complete owner lifetime**, even
when all eight are consumed. The ninth refusal precedes RNG, redaction, IO and
state changes. Tickets use current operation fields plus a fresh nonce and
opaque object identity. An attempted consume burns the ticket before document
IO; a failure poisons the owner. Successful consume removes that exact admitted
credential document. Errors/receipts contain fixed reason codes and no secrets
or paths. Registry/owner/ticket pickling is refused; repr omits credentials.
Python introspection by code in the same interpreter is outside this boundary.

Cleanup removes only admitted own regular files and the exact empty named root;
it never recursively deletes unknown entries. Retargeted names, extra entries,
shared inodes, replaced FDs and failed root admission prevent complete-cleanup
claims. Unrelated replacement FDs remain open. If creation gets past mkdir but
cannot admit a root FD, the fixed `fixture_creation_cleanup_incomplete` refusal
reports possible disposable leftovers without guessing which path to delete.
A foreign PID refuses use before acquiring an inherited mutex; foreign cleanup
closes admitted inherited descriptors and never unlinks the parent's fixture.

Run the new suite from repository root:

```sh
python3 -W error::ResourceWarning -m unittest discover -s research/native-live-recovery-037/guest-owner-successor -p 'test_owner.py' -v
```

The tests perform actual Linux temporary-file/descriptor IO. Parser corruption
controls explicitly repin a synthetic document to isolate parsing; ordinary
custody never accepts that repinning. PID-change/locked-mutex controls mock PID
observation and do not execute a Wine child. Permission checks assert the policy
for metadata modes; these controls run as the current host UID and are not proof
of Android DAC/SELinux isolation.

## Closed gates and exact integration gaps

There is no caller in the launcher or active guest tree, and no subprocess,
network, mount, JNI, Wine, FEX, PRoot, Game, database or player-data operation.
No Android admission or device-performance result follows from these controls.

The original owner API, finalized guest control path schema, native PID/thread
and start identity verifier, current installed-package/probe/SDK provenance,
Wine namespace bindings, seven data-root identities, native NT output ownership,
process wait/reap/termination, bounded console/packet cleanup and JNI orchestration
still need genuine source recovery or separately reviewed implementation.
This prototype supplies none of those authorities and cannot enable LIVE.

Held-FD/path bracketing detects the controlled symlink/rename/retarget cases; it
does not create an atomic compare-and-unlink primitive or exclude another actor
of the same UID. Current UID metadata does not prove absence of earlier writable
descriptors, writable mappings or unexpected writers. Host hardlink/mode refusals
are not native NT sharing qualification. An externally enforced writer/lifecycle
owner and genuine concurrent native alias/sharing/retarget controls remain
required before any current Wine/Android integration or production admission.
Do not convert this experimental custody boundary into runtime authority.
