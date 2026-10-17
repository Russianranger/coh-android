# Complete catalog as native protocol seed

An original CLIENT cache execution is not required merely to possess omitted
sendDef-visible inputs. A same-generation complete COHCAT already contains the
unchanged original sendDef serialization of EVERY allocated definition, including
saved omissions and tombstones. COHRTS supplies root ownership/matrices and actual
external future objects. The compact graph resolves those exact records and
retains raw optional metadata. The optional eligibility witness checks that each
actual emitted update is byte equal to the corresponding retained catalog record.
Therefore seeding every retained record and applying those equal updates leaves
the complete logical protocol-wire input unchanged. Omissions need not be invented
or reloaded from a CLIENT cache just to obtain these inputs.

`coh_catalog_seed_visit` implements that narrow substitution. Before any seed
callback, it validates the full immutable witness/packet and exact owners, stages
a bounded emitted-node mask and checks source definition/reference CRC validation.
It then visits all allocated original slots and captured external futures with
exact wire spans and explicit emitted/source-only status. A saved omission is
retained. A tombstone is retained. An external future remains a separately owned
external identity, not a fabricated ordinary file slot. Callback stages are
provisional until final success and must be discarded on ANY refusal. Report and
reader are transactional; scratch can change on failure. There are no allocations.
This prepares a native raw serialization seed, not a copied CLIENT GroupDef image.

This does not claim that COHCAT contains all CLIENT state. The original
`receiveDef` resets its struct, reads protocol fields, finds/creates canonical
future children, decodes matrices, then invokes setClientFlags,
groupLoadRequiredLibsForDef, getGeo/groupSetTrickFlags, groupSetDrawInfo,
groupSetBounds and groupSetVisBounds. Textures, TexWord, material/trick-derived
flags, model/auto-LOD, visibility caches, library loaded flags and resource owners
are outside the raw wire seed. worldReceive subsequently recalculates bounds and
updates/activates trackers, collision and other systems. None is fabricated here.
A downstream native adapter must interpret the preserved fields and resolve the
required source-qualified CLIENT dependencies before publishing any world.

For NEW_WORLD the original CLIENT resets group state, creates/names file0 and
passes it as loadto; receiveGroupFile calls groupLoadTo for that file. Other files
use an existing file or attempt objectLibraryLoadBoundsFile, falling back to
full loading if it fails. Thus executing that particular cache path is one way
the original CLIENT obtains preexisting definitions and derived state. It is not
a protocol requirement to run that implementation when an alternative native
import supplies the required inputs and qualified derived state. This change
establishes only the raw protocol-input alternative. It does not assert byte-equal
CLIENT memory, equivalent resource side effects or complete rendering state.
Existing native eager imports already specify complete borrowed original slot
catalogs; this visitor preserves the compact bounded ownership approach.

## What the checksums actually cover

Original groupInfoCrcDefs hashes each allocated definition's active name, or
NAMELESS for an allocated inactive/nameless slot, in original file/slot order.
It does not hash definition fields or bounds. groupInfoCrcRefs hashes each active
root's name and its first child's name where present, not matrices or every child.
The compact graph already independently verifies these algorithms and separately
checks full source wire and root matrix association. SHA256 pins cover the actual
catalog/snapshot bytes. Matching CRCs alone cannot prove complete field identity
or a live source generation.

A file bounds_checksum is different. objectLibraryWriteBoundsFileIfDifferent
returns for file0; for other files it visits groupIsPublic definitions in source
slot order, hashes raw sizeof(GroupBounds) bytes beginning at def->min, then the
public name WITHOUT its terminating NUL. Public means active/named, not grp-prefix
(case insensitive), owned by an object_library-prefix file (case insensitive),
and not a private name ending '&'. file_idx is not used for public selection.
The exact raw GroupBounds prefix is60 bytes in the qualified Win32 layout and
includes bitfield/padding bits. The library .bounds reader independently hashes
its raw cached bounds/name entries in that same order. A cached checksum hit can
return without reading the file; a successful cold read installs library bounds.

`coh_source_bounds_checksum` provides this exact pure byte calculation and
expected-value refusal for independently authenticated raw60-byte observations.
It preserves high padding bits/NaNs and source prefix rules; it does not substitute
numerically reconstructed min/max or named flags. It refuses file0 because the
original writer does not compute that checksum there. 256 unchanged original
public-selection/writer cases qualify byte order, public/private selection,
case/prefix behavior and all raw bits. The original cryptographic adapter's
Crypto++ digest-byte order remains independently qualified by existing oracles.

COHCAT records each file's observed checksum token, but contains no raw ordinary
GroupBounds images. COHRTS contains named-field bounds only for the seven observed
external futures, not ordinary saved slots; its named flags do not independently
preserve unknown native padding bits. COHRES carries MODEL min/max/scale/radius
and trick metadata, not complete GroupDef GroupBounds. Existing numerical source
bounds diagnose root-reachable boxes; they do not supply exact original raw public
bounds for all allocated library definitions, including unreachable ones. Thus
actual per-file bounds checksums CANNOT currently be recomputed from the retained
three artifacts. This is an exact data limit, not a reason to invent bounds or
rerun the original cache merely to possess raw protocol fields.

If claiming original bounds-cache equivalence is required, a future genuinely
new combined observation must add each ordinary public definition's exact file,
slot, canonical name, original public decision, GroupBounds sizeof/layout identity
and raw60 bytes at the SAME source boundary as the actual GROUPS eligibility and
packet. Preserve original slot order and raw padding, source/build/run identities
and whole-record digests. Observe groupIsPublic directly and independently recheck
its source rule. This is new data; no existing catalog/runtime capture should be
repeated merely to reproduce known bytes. Alternatively, independently qualified
native CLIENT-derived state can avoid using the original cache as an authority;
that path still requires same-generation source ownership and live packet binding.
The checksum token equality gates remain unchanged, and no recomputation is claimed
when only that token is available.

The retained authentic input audit enumerates508 files/40225 active allocated
wire records, no holes,33 roots and7 external futures. Its complete original
public-selection list identifies14346 ordinary public definitions across507
library files, requiring at least860760 raw bounds bytes plus identity/order to
recompute cache checksums. File0's observed token is0. Library file507,
object_library/Special_Buildings/Shop_interiors/Shop_int_magic/shop_int_magic.txt,
also has token0 with39 public slots. No current-state raw-bounds equality is
inferred from an observed token: the original loader can take its cached-checksum
fast path, including an initial zero. A future cache-equivalence claim must also
establish which cache/source state and checksum computation generation the token
represents; newly captured current raw bounds must refuse if they do not match,
never normalize or replace the observed token.

All source-generation, CLIENT-derived state, bounds-cache recomputation, assets,
world publication and actor/ACK authority remain false. Historic Thor343112-bit
raw bytes are absent. This component does not establish a real live session,
Android build, emulator execution, physical Thor test or accepted APK successor.
