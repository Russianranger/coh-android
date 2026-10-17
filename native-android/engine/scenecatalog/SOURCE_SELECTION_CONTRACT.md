# Immutable source-selection contract

The procedural source argument was independently reviewed in `2996e7591`.
The additive implementation is `coh_source_selection.[ch]`: immutable exact
profile association and a separate FILE-scoped actual-body lease. The original
index body-validation grammar remains in force. No CLIENT/live/world authority
is granted. Native factory qualification and source review are recorded separately
from that earlier source-argument review.

## Trust root and evidence classes

An arbitrary JSON witness is never an admission credential. The current checker
produces a diagnostic that binds a separately reviewed argument to exact bytes.
A future native factory must use an independently reviewed, compiled profile of
exact producer/source/run/fixture/manifest/leaf commitments. It must not accept
caller booleans, a caller-selected expected digest or a caller-selected registry
as its trust root. Hashing a caller's JSON and comparing it to the caller's own
hash proves no provenance.

The first profile would be restricted to disposable resource capture
38994607354 and asset generation 20261016:

| Binding | Exact identity |
| --- | --- |
| Producer source revision | a45c657fcc6b3bd8f3a70c59e9aa85ee19455f3f |
| Source identity SHA256 | 9b74823a341fe565a978f81516b3b13ea8741ec8ecc57bb2b8bfb40130943eaa |
| Run identity SHA256 | e6a25d7e6429fbb856fad617c5f8eeab75325c0fb7c0083be7f91348e5765ced |
| Resource stream SHA256 | 8500764939215b576e5ff88056ec85b475785038e09600019846ff5a06eb1cd6 |
| Control fixture SHA256 | 3be317b5cc4b24aad8b19cd93e18762f12270ad4284c31a81e7587e4e35fadc1 |
| Existing candidate document SHA256 | a52d6470847fc01a677cfa2822c0cf5eae23eecefcb52edb7e2789ecd5c637a6 |
| Canonical complete 391-body witness table SHA256 | b2c0623d2724e614165d492935183181741d99f6f15572aba037fc33b381314a |

The canonical table is JSON `bodies` from the final source-route witness, encoded
with sorted keys, compact comma/colon separators and no trailing newline. Each
entry binds an exact observed GEO name, canonical manifest asset path, byte
length, full-body SHA256 and observed source ordinals. It is not a claim that all
467 observed libraries have body coverage: this finite profile covers the 391
root-required libraries, including other observed owners of those same files.

Two evidence kinds must be distinct types, not interchangeable flags:

- **Direct open observation:** a separately qualified producer recorded the
  resolved physical leaf and digest over the opened bytes, bound to that exact
  source owner/run/observation interval. There is currently no such profile.
- **Procedural source derivation:** the exact preparation and original selection
  route determine the unique body, under the retained owned startup scope. The
  resolved physical leaf and open-time digest were not directly logged. The
  current proposed profile is this kind only.

A query must return the derivation kind and profile identity. It must never
report the two unobserved values as direct observations or synthesize a physical
path string from the logical asset name. Introducing another capture, revision,
manifest or proof route requires another reviewed profile. A source-generation
integer alone cannot select or widen a profile.

## Proposed factory and immutable owner

The factory takes the existing opaque retained catalog/snapshot/graph/resource
join owners, actual receipt byte spans and explicit memory/cancellation limits.
It selects only a built-in profile. Its output is an opaque immutable owner;
there is no public constructor for successful proof records.

It performs these operations before publishing any owner:

1. Verify exact raw receipt digests against the profile. Raw JSON need not be
   reparsed to trust its asserted booleans once the complete exact bytes are
   pinned; bounded parsing may be used for diagnostics only. Unknown profiles,
   oversized inputs, duplicate/trailing encodings or digest failures refuse.
2. Obtain source/run/generation/resource commitments from the actual opaque join
   and its actual retained owners. Match the profile, not caller labels. Preserve
   the existing exact borrowed catalog/snapshot-address checks and complete
   original slot/future-owner association. A tiny read-only join binding getter
   or actual join reference retention would need coordinator review separately.
3. Verify the compiled leaf table's commitment and build bounded exact-name and
   ordinal indexes. Every covered ordinal must equal the corresponding joined
   record's observed GEO name; omitted, duplicate, renamed or foreign ordinals
   refuse. A library table entry supplies no authority to an unjoined model.
4. Return proof-derived `CohResourceGeoPin` values only for covered libraries.
   Canonical paths and body hashes come from the profile table. No extension,
   public-name, suffix, directory-case or fallback path is invented.
5. The existing resource index must still acquire the actual protected-loader
   blob, verify its exact identity/generation/full digest, preserve every raw
   model row, verify the unique exact model name and original sort bucket, and
   compare geometry/partitions. Source proof does not bypass this body check.

The proof owner must retain its join/dependent source owners or use an explicit
borrowed lease that remains alive and immutable through proof retirement. A
lookup must never dereference a retired graph or join. Ownership strategy is an
implementation decision requiring review; merely retaining equal digest labels
on another object is insufficient. Once acquired, an index should retain the
proof owner rather than accepting transient derived pin arrays whose provenance
can be changed independently.

Receipt input copies/digests, static table spans, descriptor/name indexes,
actual source owners, old and candidate proof owners, loader reservations and
all preparation scratch must appear in the aggregate budget. Shared retained
owners are charged once by identity, distinct equal-byte owners separately.
Every loop has a work/cancellation bound; no lazy allocation or digest work is
allowed during render queries. All known control/source/workspace spans are
checked before writes. Failure preserves old/output/report and releases all
candidate references. Replacement is atomic only after all required checks.

## Coverage and outputs

The proof establishes one narrow relationship:

`exact captured observed owner → source-derived canonical full GEO body`.

It is not a resource draw permit. In particular, four admitted source identities
with zero draw counts remain explicit non-renderable metadata; empty references
are never silently erased. A root-closure query must separately demonstrate that
every root-reachable modeled node has a covered verified body. All 467-library
closure cannot be inferred from this 391-library profile.

Outputs retain source/run/fixture/manifest/profile pins and the evidence kind.
They keep CLIENT materials, effective texture binds/swaps, lighting, ModelLODInfo,
post-load bounds, actor authority, matching live GROUPS transaction, ACK and world
publication unavailable. This profile cannot authenticate physical Thor assets or
another server generation merely because their full body bytes agree.

## Required refusal controls before implementation acceptance

- Forged JSON with every success boolean true and a self-consistent caller hash.
- Correct witness/manifest bytes from a different source/run or equal-binding but
  distinct catalog/snapshot owners.
- Correct source name paired with another canonical path, leaf hash, ordinal,
  model owner or loader generation.
- Partial, repeated, out-of-order or foreign table rows; root model missing from
  covered closure; an unsupported non-root library queried as covered.
- Direct/procedural evidence-kind substitution and unsupported profile upgrades.
- Old/new proof lifetime order, graph/join retirement, cancellation at every
  preparation phase, allocation failure and aggregate old+new budget refusal.
- Source proof success followed by body/model/material-partition refusal: neither
  index nor renderer publication may occur and previous owners remain valid.

The existing offline checker verifies evidence pins and leaf bodies; it does not
implement this proposed native factory. Its eight negative controls are not a
substitute for the owner/lifetime/generation controls above.

## Implemented boundary and host qualification

The selector retains its exact join using the additive bounded join reference
API and copied dependency/pin getter. The join still borrows its graph: callers
must retain that actual graph until all selector/body/join references retire.
The registered 89,471-byte read-only binary table retains all391library identities
and3083root-ownerordinals; all8250matching joined model owners are derived by
exact name lookup and checked against the fixed complete resource-stream digest.
An independently valid equal-byte second import remains a distinct budgeted
catalog/snapshot/graph/join tree rather than being deduplicated by digest label.

Seven complete raw evidence documents are pinned by compiled sizes/SHA256 values.
The historical391body/header witness remains pinned to its original source; a
FILE lease additionally rechecks the currently acquired actual body with current
native parsing. The selector reports only profile_association_verified. The FILE
lease reports derived_origin_verified with PROCEDURAL_EXACT_COLD_CAPTURE and
explicit direct_open_observed=0. Its immutable index retains all matching owners,
including four Shop zero-draw owners. Clients cannot substitute expected hashes,
canonical paths, source ordinals or JSON success booleans.

Whole current-loader reservation and historical peak statistics are checked
before allocating descriptor/body scratch. Old/new loader reservations are
charged once by actual loader identity. Actual file acquisitions and source
records remain copied/pinned through index retirement; source order is preserved.
Qualification is host release/ASan/UBSan only. Android and physical-device
qualification have not occurred for this module, and there is no shipping client
integration or renderer publication implied by these APIs.
