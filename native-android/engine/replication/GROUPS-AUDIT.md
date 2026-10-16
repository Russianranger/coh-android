# Original GROUPS scene-tail audit

This is a source audit for the next bounded native decoder. It is not evidence
of a complete scene decoder, an authenticated session, server-authoritative
rendering, or physical Thor acceptance. The existing scene-prefix parser stops
before the group-file count. Accepting that prefix cannot establish that its
remaining scene body is valid or that a selected character has been received.

## Audited source

Paths below are relative to `upstream/ouroboros/`. The producer is
`MapServer/src/group/groupnetsend.c`: `worldSendUpdate`, `sendGroupFile`, and
`sendDef`. The matching consumer is `Game/src/group/groupnetrecv.c`:
`worldReceiveGroups`, `receiveGroupFile`, and `receiveDef`.

Their normalized LF SHA256 values, respectively, match the existing
`source-pins.json` entries:

```text
groupnetsend.c cd739e2a1b424bf089017be73d3c42adef0f23aca7563e8577cfc98ecdfebff9
groupnetrecv.c f4cccb5a51acea3448191965470eaa349034c4f6fa1c729fa52aed0888c7004d
```

The consumer was read from an available worktree containing its full source;
the hash was checked against the pinned source, rather than inferring its
behavior from the producer alone. Additional audited helpers are:

| Source | Functions / purpose | LF SHA256 |
|---|---|---|
| `Common/group/group.c` | `groupInfoCrcDefs`, `groupInfoCrcRefs`, `groupInfoRefCount` | `dc7c70b59b565a0a358fbedfba291e6018805efa6442d0ad0419e52f3908f7d7` |
| `Common/group/groupProperties.c` | `WriteGroupPropertiesToPacket`, `ReadGroupPropertiesFromPacket` | `88975a6c74122a64ded79a860d60592814cdf79579b6a39357bbca79066673a1` |
| `Common/group/groupProperties.h` | Property type and 64-byte name storage | `5522e0e664baab38fb369b59a8d68afd806083cb28c11bda6d58c26d475ab74e` |
| `libs/UtilitiesLib/src/network/netcomp.c` | `sendMat4`, `getMat4`, `packMat`, `unpackMat`, compressed float helpers | `cddb9d5176cdf1b05b434395ebd16247f9f12001948885b4bd0a86143fd30370` |
| `libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h` | Raw matrix is four ordered Vec3 values | `822e3698ab8cf76a7344ed3effe607dcda542099382e8ed1a63c2c1d1df4257c` |
| `libs/UtilitiesLib/src/network/crypt.cpp` | Source Adler32 wrapper and numeric digest conversion | `cde2d5acd0bd23cf2b681d968f3b241ace148afc31f7a8af353920087e812b60` |

The existing pinned `net_packetutil.c`, `BitStream.c`, `clientcomm.c`, and
`svr_tick.c` supply optional floats, both bitstream representations, and the
request/ready sequence. Adding any helper to an executable oracle should pin
its actual source explicitly; this document does not change the current pin
checker or qualify these additional routines by execution.

## Encoding notation and outer order

`bits(n)` is `pktSendBits(n)`, `pack(n)` is `pktSendBitsPack(n)`, `auto` is
`pktSendBitsAuto`, `str` is the original NUL-terminated string representation,
and `f32` is an original 32-bit float. Widths describe logical source calls:
the decompressed byte-aligned representation rounds scalar bit widths to
whole bytes and encodes packed integers as 32 bits. It must not be parsed as
the packed LSB-first representation. A full world update requests compression
with `pktSetCompression`; compression/decompression and representation belong
to the transport contract before this decoder is entered.

The message order is:

1. `pack(1)` command `SERVER_GROUPS` with the negotiated command-number profile.
2. `pack(1)` undo count, then `pack(1)` redo count.
3. `bits(1)` new-world flag. If set: `bits(2)` mission-map kind;
   `pack(1)` instance ID; `pack(1)` no-auto-group; `pack(1)` base-map ID;
   `auto` intro zone; `pack(3)` team area; `bits(1)` loadscreen-pages-present
   followed, if set, by `auto` count and that many `str` page names;
   `str` loadscreen; `str` map file name.
4. `bits(1)` beacons-loaded flag.
5. `pack(1)` transmitted group-file count and that many group-file records.
   For ordinary worlds, the record slots are **1 through N-1, then 0**.
   A base raid transmits one slot, file 0, through its special grammar.
6. Root-reference update records, terminated by `pack(1)` `UINT32_MAX`
   (the original signed consumer tests the resulting index for `< 0`).
7. Footer: `pack(1)` **file count**, `pack(1)` active root-reference count,
   `bits(32)` definitions checksum, `bits(32)` references checksum.

The consumer names footer field 1 `defCount`, but `worldSendUpdate` writes
`group_info.file_count`. It is not a count of transmitted definition records.
The wire record order is also not the in-memory file order used for checksums.
The new-world flag depends on `last_world_id`, while full-update behavior is
an argument to the producer: they are related session concepts, not one shared
wire flag. An incremental update may contain only changed files/defs/refs.

## Normal group-file record

| Order | Encoding | Meaning |
|---|---|---|
| 1 | `bits(1)` | Record present. Zero ends this slot immediately. |
| 2 | `str` | File full name, retained by the consumer at its server file slot. |
| 3 | `bits(32)` | File bounds checksum, passed to asset/library bounds loading. |
| 4 | `bits(1)` | Base-file flag. One selects a different, nested base grammar. |
| 5 | Repeated `pack(1)` | Normal-file definition ID plus one; zero terminates the file. |
| 6 | Definition body | For each nonzero ID, decode the body below at ID minus one. |

There is no definition count or byte length around the normal-file body.
`receiveGroupFile` may load matching bounds/library data or the original map
file before applying transmitted changes. `sendGroupFile` intentionally omits
saved library definitions with a nonzero file index when the file is unmodified
on disk, even for a full update, unless force-reload is active. Thus the wire
body alone need not define every referenced piece of geometry. A complete
native asset graph needs the matching imported source assets and file-slot
identity; unresolved names cannot be substituted with the accepted offline
preview and called a server scene.

If the base-file flag is one, the next bit is base-raid. A normal base invokes
`baseSendAll` / `baseReceive`; a raid additionally sends 32-bit raid type and
base count, per-base IDs (except the last base), three offsets, and nested base
bodies. These bodies are not normal definition sequences and have no generic
length to skip. A decoder that does not implement the base schema must return
unsupported at this branch and leave its published scene unchanged.

## Definition body in exact producer order

The enclosing file supplies `id + 1`. `bits(1)` `in_use` is first. Zero is a
definition removal and ends the body immediately; there is no name or remaining
payload. For an in-use definition:

| Order | Fields |
|---|---|
| 1 | `str` name; `bits(32)` modification time. |
| 2 | `pack(1)` child-entry count; each entry is `str` child definition name followed by `sendMat4`. |
| 3 | `bits(1)` LOD block present; if set, five optional floats (`lod_scale`, `lod_near`, `lod_far`, `lod_nearfade`, `lod_farfade`), `bits(2)` fade node, then four `bits(1)` values: parent fade, child-parent fade, no-fog-clip, no-collision. |
| 4 | `bits(1)` child/tracker block present; if set, six `bits(1)` values: open tracker, child light, child ambient, child volume, child beacon, child no-fog-clip. |
| 5 | Optional float sound radius, then optional float shadow distance. |
| 6 | `bits(1)` tricks block present, with its fields listed below. |
| 7 | `pack(1)` texture-swap count; each swap is `str` source texture, `str` replacement texture, `bits(1)` composite. |
| 8 | `bits(1)` model present; if set, `str` model name. |
| 9 | `bits(1)` hide-for-gameplay. |

An optional float is `bits(1)` present and, when set, one `f32`; otherwise its
value is zero. This is distinct from the compressed half-integer float used
inside packed matrices. `child_properties` is explicitly not transmitted.
Child names may refer forward to a definition received later; the source
consumer creates future placeholders. Final graph resolution must therefore
occur after staging the whole body and required source library assets, rather
than rejecting every forward reference immediately.

The tricks block is:

1. `str` type name, then `bits(1)` library-ungroupable.
2. `bits(1)` has-light and `bits(1)` has-ambient. If either is set, an
   optional float light radius is present only for has-light, followed by
   **eight** `bits(8)` color bytes.
3. `bits(1)` has-cubemap; if set, two `bits(16)` sizes followed by `f32`
   blur angle and `f32` capture time.
4. `bits(1)` has-sound; if set, `str` sound name, `str` script filename,
   `bits(8)` volume, `f32` ramp, `bits(1)` exclude.
5. `bits(1)` has-fog; if set, four `f32` values (near, far, radius, speed),
   then **eight** `bits(8)` color bytes.
6. `bits(1)` has-volume; if set, three `f32` box-scale components.
7. `bits(1)` has-beacon; if set, `str` name, then `f32` radius.
8. `bits(1)` has-tint; if set, three `bits(8)` color-0 bytes followed by
   three `bits(8)` color-1 bytes.
9. `pack(1)` texture mask. Bit 0 selects `str` texture 0, bit 1 selects `str`
   texture 1, in that order. Other bits have no source consumer schema here.
10. `bits(1)` has-alpha; if set, one `f32` alpha.
11. `pack(1)` has-properties; if nonzero, **`bits(32)`** property count,
    then exactly that many triples: `str` name, `str` value, `bits(1)` type.

The property count is neither `pack(1)` nor implied by has-properties. Property
names use a 64-byte source buffer (at most 63 bytes plus NUL); values use dynamic
strings. Property iteration follows the source stash table, so property order
is not a canonical lexical ordering. The two property types are String and
Radius; the one-bit type is not a byte-sized enum in packed representation.

## Matrix and root-reference grammar

`sendMat4` starts with `bits(1)` packed. When zero, twelve `f32` components
follow in source `mat[0]`, `mat[1]`, `mat[2]`, `mat[3]` order, three components
each; the fourth Vec3 is translation. This is a 4-by-3 affine structure, not a
16-float homogeneous matrix.

When packed is one, three `bits(1)` flags select position, pitch/yaw/roll, and
scale, in that order. Position and angles each contain three compressed floats.
Each compressed float starts with `bits(1)` half-integer: if set, `bits(1)` sign
and `pack(5)` magnitude encode signed magnitude divided by two; otherwise one
`f32` follows. Scale, if present, is three ordinary `f32` values. Missing
components reconstruct identity rotation/unit scale/zero translation.
`unpackMat` uses `createMat3YPR` then `scaleMat3Vec3`; native reconstruction must
match those source conventions rather than reinterpret the angles as another
Euler order. A structural parser can retain raw components or skip them after
finite-value validation without claiming transform equivalence.

Each root update starts with `pack(1)` index. Exact `UINT32_MAX` ends the list.
Other unsupported signed-range indices should be rejected deliberately rather
than accepted as a second terminator. A nonempty `str` definition name is
followed by `sendMat4`. An empty name deletes that root and has **no matrix**.
Root indices are sparse identities, not ordinal positions in this update.
An update can touch a high index without adding that many active roots.

## Count/checksum oracle and its limits

The authentic source checksum routines support a useful future oracle only
after a complete staged graph plus imported library definitions is available:

- `groupInfoCrcDefs`: traverse in-memory files 0 through N-1 and each file's
  definition slots in order. A non-null in-use named definition contributes
  its name bytes without NUL. A non-null inactive or nameless definition
  contributes eight bytes `NAMELESS`. A null definition contributes nothing.
- `groupInfoCrcRefs`: traverse root slots in index order. A non-null root
  definition contributes its active name, otherwise `NAMELESS`; if that
  definition has at least one child and its first child definition exists,
  additionally contribute the first child's name bytes without NUL.
- `groupInfoRefCount`: count roots whose definition pointer is non-null,
  including a non-null definition that is not in use. This is not ref capacity,
  highest root index plus one, or the number of update records.

The routines incrementally feed the source Crypto++ Adler32 wrapper, whose
`Final` writes digest bytes into a U32 and applies `endianSwapIfBig`. A future
portable oracle should test the exact wrapper's numeric byte order rather than
assume an arbitrary library's integer return is identical. Neither checksum
covers transforms, materials, property values or geometry contents. They are
source consistency checks, not a cryptographic authentication/integrity proof.

The original consumer reads all four footer fields but checks reference CRC
and active count only for new worlds in development local-server mode. Its
definition CRC check is compiled out. Those permissive legacy checks do not
justify marking the native asset graph valid without its own bounded checks.
The producer has commented-out `sendAllBounds`; it is not an additional active
tail after these four footer fields.

## Recommended bounded decoder contract

Keep traversal separate from asset resolution and publication. First validate
the complete supported normal-file wire grammar transactionally, with bounded
counts, strings, finite floats, IDs and exact logical end position. Record
explicit unsupported base/raid or future variants. Count work as well as bytes:
many small records can exhaust time before an overall body cap is reached.
Bound files, per-file IDs, total defs/children/properties/swaps/roots, individual
strings and total retained string bytes independently. Check arithmetic before
allocation. Current native 256-byte strings and other limits are admission
policies, not evidence every original map fits them.

An initial inspection result can safely retain numeric aggregate counts,
footer values and exact failure offset while discarding individual records.
Such a result must be labeled structural traversal, without claiming checksum
match, assets resolved, a renderable scene, or complete Gate 27. A later owned
scene staging object needs explicit session/world generation and an atomic
commit only after names resolve against bounded imported assets, transforms
match the source oracle, and the supported graph is complete. On any failure,
retain the previous accepted preview and diagnostics; do not publish a partial
authoritative scene.

Source-derived fixtures should cover both scalar representations, raw and
packed matrices, every conditional definition block, forward child names,
normal file order 1..N-1 then0, omitted saved definitions, deletion records,
zero files, sparse roots and both sentinels. A separate complete-graph fixture
can compare the exact original count/checksum helpers. Base/raid fixtures,
nonfinite values, count/string limits, every-bit truncation, and unknown masks
must fail within the stated transactional contract. These are deterministic
source-layout tests; actual captures and a real server remain separate evidence.

## Why prefix acceptance cannot advance to a live world

`Game/src/clientcomm/clientcomm.c:commReqScene` requests scene, consumes
`SERVER_GROUPS`, requests all entities, consumes `SERVER_ALLENTS`, loads relevant
resources, and then sends `CLIENT_READY` with its session fields. The MapServer
`CLIENT_REQALLENTS` branch describes the client as having loaded its map;
`CLIENT_READY` enters the normal entity-message loop and triggers another full
self update. `CLIENTINP_RECEIVED_CHARACTER` means the full self update was
received and the character was created. GROUPS contains no selected character
DB-ID proof or authoritative character spawn.

There are two different acknowledgement concepts. The original dispatch sends
NetLink idle/packet ACK traffic before its expensive GROUPS load, to stop
transport retransmits. It also emits `CLIENTINP_ACK_FULL_UPDATE` at the start
of the ALLENTS branch before calling its legacy entity parser. Native code
should continue valid transport acknowledgements while processing a large
reliable scene; it must not reinterpret those as semantic acceptance. Its
stricter native integration contract must withhold full-update application ACK,
ready and received-character notifications until the relevant bounded bodies
and selected self entity are actually validated. A valid GROUPS prefix alone
provides none of those guarantees.
