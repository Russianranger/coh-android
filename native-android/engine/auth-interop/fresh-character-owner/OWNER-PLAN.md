# New opaque fresh-character composition owner

This interface/source plan follows the new C-owned public creation primitives.
It does not implement a controller, open sockets or execute a qualifier. C's
frozen core90513eb3 applies exactly the reviewedfa2ac4 patch to the C50 baseline;
its focused qualification is still separate. Root's immutable scene launch has
released the core hold, but no new owner or deployment runtime is admitted here.

New files will be confined to this directory: `fresh_character_owner.h`, an
independently implemented `fresh_character_owner.c`, a new focused C harness,
new Python qualifier, and new source/proof documentation. Existing completed
empty-list owner, pure serializers, workflows and Windows profile helpers are
not edited. The new implementation will include headers only and call public
`CohLogin` and `CohDbSession` operations. It will not copy/fork the secure owner,
include a `.c`, rename symbols, read private component structs, or add a raw
receipt/list/controller/handoff setter or getter.

## Header for review

`fresh_character_owner.h` declares one opaque owner, config, fixed scalar
diagnostics, one begin, monotonic service, timeout/cancel/close/destroy and a
transactional diagnostics copy. Its configuration accepts an admitted Auth
endpoint/provider, fresh nonzero transport nonce, actual measured probe digest
and actual owned Map endpoint/id. None is account/character identity. First
scope fixes registered shard1/DB loopback7000, Atlas Map1 and loopback Map UDP7001.
No caller supplies UID, cookie, DBID, slot, receipt, list, controller
or handoff. The actual private fixture UID is asserted against the genuine Auth
authorization; it is never used to fill missing authorization.

Credentials are borrowed only by begin. The new authored name is copied into a
bounded private owner buffer because it must survive the asynchronous Auth/list
phases. No name is exported. The parsed list is one temporary public-API copy,
validated and wiped in the same call; it is never kept as an external DTO or
published. Its first actual eligible wire slot is selected internally. The
first scope requires the whole current list to be EMPTY/unlocked/nonvisitor/
noninvalid with nonzero base capacity, exactly one list and matching actual UID;
it does not reinterpret a placeholder as a populated/resumable character.

## Intended state and ownership transitions

| Stage | Private evidence and action | Consumption and refusal |
| --- | --- | --- |
| Begin | Create one public Auth controller and submit fresh credentials. | Latch begin before validation/copy/allocation/component calls; never reset. |
| Auth | Service same Auth controller with original protocol and exact clean framing diagnostics. Read actual registered/up shard1 loopback7000; select it once. | Latch shard attempt before choose; no retry on component refusal. |
| Private bridge | Read authorization from that same AUTHORIZED controller, require the exact protocol/shard/current fixture UID and nonzero actual cookie. Create ordinary DB login/receipt privately from those actual fields. | Latch bridge before any fallible component operation; poll cancel immediately before begin. Receipt generation1 labels this owner, not an independently minted grant. Wipe authorization/login/receipt on every path. |
| DB list | Create the public DB session with encryption required, original session DH callback, exact provider lifetime and original protocol20110614. Service until exactly one complete matching list. | Refuse queue, unsupported traffic, repeated list, unexpected phase/generation, local/fake auth, extra login, choice or handoff. No independent-command budget or body skipping is added. |
| Empty creation | From actual list and public diagnostics construct `CohDbEmptyCreationRequest`: actual slot, current session/list generation, private bridge's receipt label, copied authored name and source AtlasHero1. | Wipe list before return. Latch creation before the public primitive; poll cancel immediately before call. Request generation fields compare actual state and are not identity authority. Wipe name after this attempt, whether it queues or refuses. |
| Wait offer | Continue same ordinary DB session under its unchanged parser/service behavior. | Require one login/list/choice/handoff, no queue/unsupported, unchanged session and selection generations. Any extra/invalid event is terminal. A queued request sets persistent-allocation-possible even without an observed offer. |
| Retire | On genuine HANDOFF_READY call only `coh_db_session_retire_created_offer` with actual owned Map policy. | Latch retirement before call; poll cancel immediately before it. Require the exact fixed returned summary/generations and its terminal DB CANCELLED phase. Never invoke raw or typed ordinary handoff takes. |
| Complete | Close/destroy Auth and cancel/destroy DB; wipe new name and all new bridge/list temporaries; poll cancellation again. | Publish fixed scalar success only after those steps. Preserve observed HANDOFF_READY separately from final CANCELLED. No Map socket/body/READY/ACK or later continuation. |

The header retains separate observed and post-cleanup controller phases. Cleanup
must not replace the first cause or pre-retirement observation with a later
CANCELLED/CLOSED sample. Terminal close is idempotent and never upgrades a failed
or cancelled transaction to success. Explicit cancel, timeout, malformed input,
allocation failure, callback reentry and lifecycle closure all retire the same
attempt. The callback/context and crypto/provider lease remain valid until both
controllers are destroyed. Every public method busy-refuses callback reentry,
including diagnostics, close, cancel, timeout and destroy; output/destroy pointer
storage is unchanged on refusal.

`CohLogin`'s AUTHORIZED result is a frozen receipt, not revocation/TTL monitoring.
The new owner must not infer live server process ownership from a matching
endpoint or a locally labelled generation. That proof remains in the future
hosted driver. Its whole fresh database cleanup also remains external: native
cancellation/secret wiping is not persistent rollback. Successful retirement
only witnesses the source route to a deliberately UNINITIALIZED allocation
offer, not initialized/saved/full-character acceptance.

## Independent implementation shape

The source will use a small owner-local phase dispatcher with single-entry
consumption flags and explicit terminal cleanup. It will directly configure the
public controllers and construct the new public request/summary objects. It
will not call the completed-list owner's methods or import its private helpers.
Shared protocol/provider definitions are reused through their ordinary public
headers. Same-UID matching, shard verification and private bridge operations
necessarily follow those public contracts; that is composition, not a second
Auth/DB protocol or a secure-owner fork.

Normal version/checksum-reference acceptance remains false. The bounded original
development request stays explicit (`no_version_check=1`, a source-labelled
development patch string, measured probe checksum). Whether the server actually
took its development exception is not internally observed. Public fields keep
that distinction. No version file, reference executable, registry value, grant
or ID is synthesized to pass a remote predicate.

The new diagnostics carry only fixed phase/cause/status values, booleans and
generation labels. They contain no raw native error, system error string,
account/new name, packet bytes, UID, DBID, cookie, endpoint, slot, list or
controller pointer. `controllers_destroyed` proves only this composition's
component lifetime; platform handles/jobs/profile/database retirement are
separate obligations. Existing Windows UDP close-accounting caveats remain.

## New focused qualification scope

Only new source is qualified. C separately owns real-session/parser/UDP queue
transactions for its primitive. This owner's new harness uses controlled public
Auth/DB controller doubles with actual API signatures, drives the real new owner
source, and observes only test-side call order/private fixture state. It must
label all grants, parsed lists and server allocations synthetic. It must not
claim original controller/parser/network/server execution from those doubles.
A separate link-only closure against the real public controllers can establish
API compatibility once the C source/proof is frozen; it is not a replay of the
old Auth, list, C50,17-TU, receiver or platform suites.

After those new controls, at least one additional NEW integrated transaction
must drive the actual public `CohLogin`, `CohDbSession` and new owner against
synthetic loopback Auth/DB wire peers. It must reach the real reliable queue,
real source-layout MAP_CONNECT parser and terminal retirement. Use admitted
original writer fixtures and label any deterministic test crypto/provider and
server allocation as synthetic. This executes the new controller composition;
it is distinct from doubles/link-only and from a genuine Auth/DB/Map deployment.
No old suite/main is invoked. Actual server interoperability remains false.

Required new transactions include:

- Success through actual owner phases, same-controller private grant bridge,
  full matching EMPTY list, derived real wire slot, one primitive call, one actual
  returned creation-specific summary, terminal cancellation and destruction
  before success. Check generations, API call order and unchanged outputs.
- Wrong Auth protocol/shard/endpoint/status/UID/cookie/framing state, missing or
  reused authorization, provider or endpoint rejection, extra frames/failure
  markers. No missing field gets filled with a fixture constant.
- DB begin failure, local-auth marker, wrong/missing/repeated/mismatched list,
  no capacity, nonempty/locked/visitor/invalid/wrong-index slots, extra login,
  queue/unsupported/choice/handoff and unexpected controller phases/generations.
- Invalid begin credentials/name/config, all known input/output/provider/owner
  span aliases, every new allocation failure and each component refusal. Any
  admitted outer begin/bridge/creation/retire attempt is one-shot even when the
  corresponding component fails or cancellation arrives immediately before it.
- Wrong/missing offer/retire summary, stale session/receipt/selection generation,
  wrong owned Map policy, cancellation before/after queue and before/after
  retirement, duplicate service/completion/destroy and monotonic clock/timeout
  boundaries. Existing raw/typed handoff APIs must never be called.
- Callback reentry into every public method during each cancellation poll and
  controlled component/cleanup callback. Busy refusals leave outputs, owner
  pointer and first terminal cause unchanged. Provider context stays live through
  final DB destroy and only then may the caller release it.
- Test-side secret/name copies are wiped at each transition and every terminal
  path. Preserve a synthetic server row once queue processing allocates it;
  cancellation and success must keep rollback false. No controller-close count
  is promoted to complete OS/profile/SQL cleanup.
- New actual owner allocation/size/stack/budget measurements, release and
  ASan/UBSan runs with exact source/executable provenance. There is no memory-fit
  or platform/runtime claim before those measurements and independent review.

The source plan introduces no common build/workflow change and no live run.
Same-backend Map READY observation, fresh Windows-user/profile launcher and
complete assets/DLL admission remain independent unqualified deployment work.
