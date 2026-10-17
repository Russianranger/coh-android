# Compact source forward power join

`coh_power_join_prepare` consumes the already bounded category, set, and full-power
owners. It preserves original category/set/power reference order and resolves the
declared BasePower by original lowercase/slash-normalized CRC. It reads that
power's actual short name, builds `set.fullname + '.' + power.shortname`, and
performs the original case-sensitive fullname decision before an alternate CRC
lookup. A short name may itself contain periods. A fullname suffix split is not
an equivalent operation.

Missing sets, declared powers or required alternate identities refuse the whole
join. The original source logs and continues; this owner deliberately requires a
complete reference graph and never certifies the source's shortened arrays. It
never constructs missing `DuplicateMissingPowers` clones. Raw allocated rows not
referenced by categories remain in their original owners. Set and power parent
projection follows the source's reverse overwrite precedence. Nested modifier
parents and dictionary finalization are separate work.

The owner and workspace have fixed capacities. All existing owners, the leased
set input, the streamed power provider context/scratch, caller-retained bytes and
16 KiB native stack reserve are charged before any callback under a literal
8 MiB standalone cap. No 62 MB power graph is materialized. Names use bounded
provider reads; immutable file/provider/input leases must outlive the join.
Provider failure, cancellation, unsupported local limits, malformed owners and
budget/alias failures preserve the complete output. Runtime and actor flags stay
false. Historical matching bodies do not admit current CLIENT/SERVERONLY cache
selection, a live generation, semantic class/power application, or an ACK.

`check_power_join.py --cache-zip EXACT.zip --output NEW.json.gz --sanitize`
executes unchanged whole original `SetForwardPointers`, `SetBackPointers`, power
lookup/fullname/CRC functions on compact source fixture objects. Lookup arrays
and earray/heap storage are explicit fixture adapters. The previously qualified
stash/index constructors are not repeated. An independent projection compares
all ordered references and parent precedence. Exact historical cache inputs go
through the actual native bounded importers. Synthetic small powers are read and
written byte-identically by the original complete record codec; synthetic
category/set containers use the prior pinned binary grammar. These fixtures do
not execute the original complete loader, cache startup or live object graph.

The exact retained corpus currently closes this **historical forward-reference**
profile: 186 categories, 6,527 ordered category references, 6,547 allocated sets,
20,241 ordered reached power references and 20,241 allocated BasePowers. All
required names resolve; the exact original short-name decision requires zero
alternate lookups in this corpus. The twenty allocated sets outside the category
references remain retained. This finding replaces assumptions based on fullname
suffix splitting; real short names can contain dots.

The independent qualifier covers eleven original join scenarios plus two native
local-limit refusals. The source oracle also executes two explicit fixture
modifiers per power through the whole source inner backpointer loop; these are
fixture storage, not the authentic nested template payloads and not native
modifier application. Aggregate scan/hash/probe/name-copy/parent-link work is
precharged under 64 MiB work units. A compact admitted graph requesting at least
268,435,456 parent writes refuses atomically. A source-supported 300-byte short
name separately refuses the native <=259-byte name profile. These refusals do
not raise caps or truncate references. Release, ASan and UBSan match; native
stack and C++ linkage are checked. Original host oracles remain unsanitized,
LSAN/Win32/Android/live cache generation remain unqualified.
