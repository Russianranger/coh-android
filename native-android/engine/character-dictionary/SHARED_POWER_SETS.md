# Original ordered shared power-set layout

`coh_shared_power_sets_prepare` walks the finalized sorted category and local-set
references, applying original persisted U32→U8 Shared storage semantics. It
retains every matching reference in source order, including repeated references.
Counting allocated Shared rows is incorrect: the exact historical cache has27
Shared allocated rows but only26 are reached by original FindSharedPowersets.
The excluded N_Tutorial_Powers.Atlas_Normal_VisionPhase row remains raw-owned.

The source function appends to its global list and does not clear it. This owner
models a call from empty source fixture state or an append to the same immutable
ID/dictionary owner. A second call retains52 entries for the authentic profile.
Cross-dictionary prior lists refuse because their original retained pointers
need a different lifetime owner. Prior sequence, count and append-call metadata
are revalidated; overflow/capacity/alias/late-mutation errors preserve output.
The API cannot assert that a running process started empty or that a reload
preserved the same dictionary. No actual runtime branch is inferred.

The unsent g_numSharedPowersets controls omission of the first shared entries from builds1..7 in
original character_ReceivePowers, which copies the corresponding build0 pointers. This historical source layout closes its
ordered dictionary prerequisite. It does not mark a CohCharacterWireProfile as
bound, mint a current generation, apply a character, publish an actor or permit
an ACK. A current generation owner must separately witness actual cache/shared
startup and initial/reload state. All transitive owners/set input/provider leases
and scratch, optional prior, output/workspace, caller retained bytes and16KiB
stack are charged under a literal8MiB standalone cap. No file callback or heap
allocation occurs; bounded scan/validation work is precharged under64MiB units.

The qualifier executes whole original FindSharedPowersets twice on the qualified
finalized compact source fixture, plus whole original u8_readbin for every flag.
The binary-word and U8-storage interfaces are explicit fixture adapters. Exact
native cache importers are reused without a powers graph. An independent model
checks the reachable sorted traversal and append order, normal/shared/unreached
sets, repeats, no-shared sets and low-byte values256/257/255. Original runtime
process/global state and complete character semantics remain unqualified.
