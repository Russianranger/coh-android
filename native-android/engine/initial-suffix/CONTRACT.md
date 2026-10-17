# Initial GLOBAL suffix diagnostic composition

This composer starts precisely at the full-update receiveCharacterFromServer
body, after the enclosing entity list, debugging, control and deletes. It reads
all six outer-character groups, complete PowerInfo, power modes, badges and
full-update badge monitor, inventory/invention/workshop, social flags and lists,
optional monitor attributes, diagnostic dynamic groups, then sky/slave fields.
Source producer and consumer function files, whole-function hashes and ordered
call sequences are pinned. full_update must be1; full-update social skip bits
are impossible in the original producer and are refused. This does not infer
full_update or selected entity identity from the character fixture.

A huge permanent union cannot satisfy the badge decoder's4MiB total budget after
reserving approximately6MiB for character parsing. The caller instead supplies
serialized scratch acquire/release loans. Each stage invokes its qualified child
and releases storage before the next. Loan charged_bytes must cover the entire
resident allocation, including unused capacity. acquire receives a maximum
charged allowance BEFORE any allocation and must refuse before exceeding it,
including padding/allocator overhead. The allowance already respects the
stricter4MiB badge limit; over-budget scratch is not allocated speculatively. The provider declares a disjoint context span, charged once and excluded from
loan aliasing. Other callback metadata or allocations
retained between loans belong in retained_bytes. A persistently reserved6MiB
union remains6MiB charged even during badges and is refused; no cap is raised.
Acquisition failure must return either a zero descriptor with no ownership or
a populated partial loan. Any nonzero descriptor is released exactly once even
on acquisition error; release must accept that partial descriptor. Hidden owned
storage omitted from the descriptor is forbidden. Each successful acquisition
is also released exactly once on every later path. Callbacks must be serialized and
mutate only their own declared owner/loan, never packet or explicit arguments.

Results are compact observations and immutable packet-backed bit spans. The
caller must retain unchanged packet bytes under its explicit lease token until
all reports/spans are discarded; the token is a lifetime label, not ownership or
source authentication. No child POD, account auth bytes, arbitrary commands or
strings are copied into reports or logged. Clients can reparse validated spans
under the same exact profile if raw details are required. Full input storage is
charged by every child rather than only the current span.

Active invention and full attribute mode refuse immediately. There is no admitted
dynamic runtime occurrence/generation owner interface. Therefore the diagnostic
composer may finish raw syntax validation through sky/slave but ALWAYS returns
UNSUPPORTED for unowned dynamic data, preserving caller output and reader. Its
separate report records validated spans with complete_initial_update, selected
entity, dictionary, dynamic ownership, transport end, actor and ACK all false.
The original server can append byte-aligned commands; exact suffix end is never
presented as a transport packet end. Missing prefix/framing semantics cannot be
supplied through a context boolean or numeric expected count.

Budget includes full input, explicit reader/context/provider/output/report,
active charged loan,64KiB conservative native stack reserve and retained bytes
within8MiB. Child-specific lower budgets remain enforced. This is named storage,
not process RSS; allocator overhead must be included by the provider, and external
callback/zlib stack and external zlib sanitizer closure remain unqualified.
All explicit memory spans and input are pairwise disjoint, overflow checked;
loan storage must be aligned/disjoint from them and internal candidates.

Tests concatenate separately unchanged-original-produced bodies at matching
absolute bit offsets. This is not whole original entSendUpdate/entReceiveUpdate
execution or a live packet capture. Controls cover active invention/full attribute
headers/impossible full-update skip, every stage boundary truncation, selected
byte mutations, trailing commands, every acquisition failure, misaligned/aliased/
undercharged loans and truthfully oversized scratch, with atomic output/reader
and exactly matched releases. Release/ASan/UBSan and C++ linkage run; native frame
sum is measured separately. Android, selected actor and whole initial update
remain unqualified.
