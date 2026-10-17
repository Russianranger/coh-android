# Source-owned DB handoff to Map begin

`coh_map_client_begin_owned` is an optional, separately linked strong bridge. It
accepts only an actual opaque DB handoff owner from the validated DBSession take.
Expected DB-session and selection generations refuse stale transactions; they
never replace metadata. Slot, selected DBID, local-development scope and the
sensitive Map handoff derive from the actual owner/one-shot claim. Endpoint
access still requires explicit caller authorization and the existing exact peer
address/port check. Receipt generation is caller attestation, not evidence of an
encrypted AuthServer login. A source-owned selected DBID is an expected identity;
complete Map entity/character validation remains required before any application
acknowledgement, actor/render publication or world authority.

The bridge preflights the actual client and reads actual owner metadata before
claiming. Stale generations, invalid endpoint authorization or an inadmissible
client phase do not consume the handoff. It retains the real owner, checks
cancellation, and consumes the private claim once. Both sensitive handoff and
Map authorization stack DTOs are volatile-wiped after every claimed attempt.
After claim, Map begin refusal/cancellation irreversibly retires the owner and
closes any candidate Map transport. A successful client adopts that retained
reference only after a private typed check of the actual claimed/nonretired owner
against the begun client fields. There is no metadata or callback setter.

The client retains the owner after DB close/destruction and creator-reference
release. Service and actual scene-loan getters recheck its actual metadata.
External retirement refuses further owner-bound service/loans and closes the
client. Disconnect, close, timeout, suspend, cancellation and destruction retire
and release the retained owner, clearing source-selection flags. Other references
observe irreversible retirement. Final owner deallocation remains the approved
DB owner's whole-allocation wipe. Access/refs/callbacks require one owner thread;
callbacks may mutate only their own context. Private attachment is exclusively
for this qualified bridge, not an alternative public admission API. Opaque owner,
client and control allocations must remain caller-disjoint.

Raw `coh_map_client_begin` retains its existing DTO contract and always leaves
selected_dbid_owner_bound0. Actual-current receive leases copy owner-bound DB
session/receipt generations only after checking the retained source owner.
Source-generation/world/character flags remain unchanged. IDs/generations remain
local owner/transport observations rather than globally unique session tokens.

## Linkage contract

The core's optional metadata/retire/release dependencies are typed ELF weak
references only on supported GCC/Clang compilers defining `__ELF__`. Raw standalone
MapClient links and runs without DBSession. The private preflight/attach paths
refuse UNSUPPORTED if the complete weak function set is absent/incomplete or the
compiler/format guard is disabled. No callback replacement is installed.

The PUBLIC owned begin lives in `coh_mapclient_owned.c` with STRONG references to
the actual DB claim/retain/metadata/retire/release functions. A caller using that
entry must link this bridge; deliberately omitting it gives a link error, rather
than pretending that weak references extract a DB object from a static archive.
Place archive dependencies in normal static-link order (bridge/DB archive before
core/dependency archive, or a qualified linker group). Calling the owned API then
extracts the bridge and actual DBSession object; merely using raw core APIs does
not. No shipping CMake/JNI/linker policy is changed here. Other object formats or
DSO unloading are not qualified by these ELF controls.

Host qualification uses actual scripted UDP DB receipt/list/choice/Map handoff
and Map connect/shortcut/GROUPS exchanges, including provisional development auth.
It tests owner survival after DB/client creator retirement, actual callbacks,
stale/refused/duplicate claims, cancellation before/after claim, peer mismatch,
external retirement and terminal cleanup, with the owner's zeroing deallocator
and socket-count controls. Direct and static-archive links exercise the same
source-owned path; standalone and incomplete-dependency probes fail closed. These
are original-source-layout synthetic peers, not a real authenticated server,
Android execution or physical Thor acceptance.
