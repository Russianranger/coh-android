# Proposed fresh allocation-offer probe and driver boundary

This is a source/API draft, not a built CLI or a deployment qualification.
`fresh_character_probe.proposed.c` composes only the new public owner. Its
platform declarations have no implementation yet. No existing empty-list
owner, probe, profile or workflow is changed, and no old qualifier is called.

Proposed invocations are exactly:

```text
fresh-character-probe --platform-preflight
fresh-character-probe --allocate-offer PRIVATE_POLICY_FILE
```

Runtime stdin supplies exactly three printable-ASCII LF-terminated lines and
EOF: account1..14, password1..16 and authored new name1..63. They never appear
in argv, output or diagnostics. The name is new user content, not an existing
identity or a DBID. No endpoint, UID, cookie, DBID, slot, list, grant or handoff
is accepted from stdin. The probe submits one begin and wipes all three local
buffers immediately after it. The owner itself derives its actual private
authorization, complete list, slot and current generations.

The new private driver must create the exact policy file only after admitting
the new probe/build, current Auth/DB/SQL generations and the independently owned
same-realm Map process and READY receipt. The file is a fixed96-byte LE record;
there is no generic JSON parser, path, version value or checksum override in it.

| Offset | Field | Exact scope |
| --- | --- | --- |
| 0 | Magic8 | ASCII`COHFRC01` |
| 8 | Format u32 | 1 |
| 12 | Auth TCP port u32 | 20000..59999, exact owned current endpoint |
| 16 | Map id u32 | 1, original Atlas route |
| 20 | IPv4 bytes4 | 127.0.0.1 |
| 24 | Map UDP port u32 | 7001 |
| 28 | Map PID u32 | Actual owned current process, nonzero; private only |
| 32 | Process creation FILETIME u64 | Exact held process generation, nonzero |
| 40 | Map executable SHA25632 | Exact admitted actual Map file, nonzero |
| 72 | Operation nonce16 | Fresh driver entropy, nonzero; not authorization |
| 88 | Reserved8 | All zero |

The proposed platform implementation will admit the regular nonreparse policy
file through an exclusive-to-writers retained handle and exact EOF/length. The
driver owns private ACLs, creation and deletion; the probe never opens another
profile or writes registry values. It opens and retains the actual Map process
handle, checks wait-state/PID/creation time, reads its actual executable path
privately, measures that regular nonreparse file and compares the private pin.
Generation/file admission repeats before owner begin and after owner/controller
destruction. It closes those retained handles independently even after failure.
It must fail conservatively on process exit, mismatch or late close failure.

These checks do not prove READY_FOR_PLAYERS, current DB registration, loaded
image pages, account ownership or whole process-tree cleanup. The independently
owned driver must establish and bracket those facts from the real same-realm
source-backed observers and process/job/profile leases. The native receipt says
only that its supplied Map policy and process/file generation checks passed.
It never converts a file nonce or matching endpoint into authentication.

The platform backend will reuse the accepted TCP/UDP adapter source unchanged,
the retained admitted static OpenSSL provider and exact source-owned x64 zlib
closure. Its new code must measure this actual probe's MD5 privately using a
regular nonreparse file handle that excludes concurrent writes/deletion, and
must compare the current probe PE SHA256 independently in the driver before
and after execution. Measured MD5 is not an authentic reference checksum.
Fresh nonzero connect entropy comes from the provider/OS, not from the policy.
The borrowed provider stays live through both controller destructions.

`--platform-preflight` exercises only the new platform's entropy, self-file
measurement, Winsock initialization and cleanup with no owner, credentials,
policy file, Map handle or UDP socket. It emits a distinct schema. Actual
Windows APIs/headers/build/load remain unqualified until separately reviewed.

The source draft retains first owner failure through cleanup, closes/destroys
the owner before transport/platform finalization and publishes success only if
all independent finalizers and post-generation observations succeed. Fixed
public output contains schema, fixed stage/status/phase/failure values,
generation labels and booleans. No account/name/UID/DBID/cookie, PID/TID/time,
path/hash/nonce, frame/list/body/string, arbitrary exception or SQL is exported.

A successful operation stops after a source-parsed UNINITIALIZED allocation
offer has been privately retired. It cannot be resumed into the existing Map
controller, and it sends no Map CONNECT/body/READY/RECEIVED_CHARACTER/ACK. Queue
success keeps persistent-allocation-possible true even after later failure.
Neither native cancel nor handle cleanup is SQL rollback. The driver must own
the whole fresh SQL database lifetime and remove it after all original services
and the isolated Map process have stopped, without editing identity ownership.

The future hosted driver is separate from accepted list/selected/readiness
paths. It requires an explicit typed fresh-creation scope and provisional
development label, current source/build admission and exact original server
policy. It must refuse until the fresh-profile Windows launcher, original Map
DLL/assets and same-realm READY observation are admitted. No actual run is
authorized by this draft, and there is no reason to repeat the completed Auth
or empty-list cases. Normal client version/reference-checksum gates stay false.

Before implementation, review the fixed record, process/file observation and
first-failure/finalizer contracts below. New platform/CLI controls will be
separate from the passed owner127-case and encrypted controller transaction;
they must not re-execute those accepted entrypoints merely to qualify I/O.
