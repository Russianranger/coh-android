# Independent entity authority review

Reviewed revision: `3e8b5c9f5b794b58a66c6d8c62a593b926a10873`.
This is an additive, nonshipping review. No entity implementation, accepted APK,
active worker tree, protocol controller or renderer was changed.

## Concrete findings

1. `engine/entities/coh_entities.c:424` refuses the very-rare record at power
   customization before reaching its later character/rare fields. Standalone
   appearance, power-custom, titles and taskforce success does not compose them
   into this record. `:441` rejects a present teammate-buff body. The independently
   active tree `/workspace/scratch/9174d12e2a11/entities-isolated` contains an
   untracked teammate-buff implementation and an edited closure ledger; it was
   inspected read-only and is **not** integrated or independently qualified here.
2. `coh_ent_full_update_tail` at `:540` unconditionally returns UNSUPPORTED for a
   valid reader. No complete self transaction or authoritative actor can result.
   Existing staging-list DBID/self checks are useful but insufficient authority.
3. Original `Game/src/clientcomm/clientcomm.c:1493` sends application-level
   `CLIENTINP_ACK_FULL_UPDATE` **before** `entReceiveUpdate`. Copying this historical
   behavior would violate the required native admission contract. Transport packet
   acknowledgments used to avoid retransmission are a distinct mechanism.
4. The original dispatcher at `clientcomm.c:1507–1522` consumes optional embedded
   game commands **after** `entReceiveUpdate`. Therefore the end of the entity tail
   is not necessarily the exact packet end. Complete admission must either decode
   the permitted embedded-command grammar transactionally, or explicitly refuse
   packets carrying it. Scanning for a zero/sentinel is unsafe. An unconditional
   end check immediately after the entity tail would incorrectly reject valid
   original packets; accepting the tail while ignoring residual bytes is unsafe.
5. `coh_map_serialize` intentionally knows READY and REQALLENTS wire forms; this
   is a low-level encoder, not an authority gate. Current controller sends only
   CONNECT, REQSHORTCUTS and REQSCENE. It does not enable entity requests, READY or
   application completion ACKs. No active bypass was found in this bounded path.
6. `world-render-adapter/coh_world_render.h` explicitly labels prerequisite flags
   as caller attestations and digests as supplied identities. `coh_wr_prepare`
   validates consistency and memory ownership; it is not an initial-transaction
   verifier. A future coordinator must mint receipt data from qualified owners,
   never from arbitrary user booleans or an offline fixture promoted to live.

## Source-backed implementation sequence

The producer `MapServer/src/entity/entsend.c:4480–4600` agrees with consumer
`Game/src/entity/entrecv.c:3750–3885` on this dependency chain:

1. Complete the selected-self entity record in source order: appearance and
   power-custom/title composition, ragdoll/stats, self inventory sizes, remaining
   very-rare fields (including supergroup/leveling pact/logout), teammate buffs.
   Preserve prior-state retain/clear behavior and late-record rollback. The active
   teammate-buff worker owns that independent seam; do not recreate it here.
2. Compose global debug-profile handling, control state and deletes. TEST_CLIENT
   control fixtures do not establish the shipping non-TEST_CLIENT debug grammar.
3. Decode full `receiveCharacterFromServer`: server/auth fields; dictionary-bound
   class/origin/build/powers/inventory; original powerset names; ally/PvP/stats;
   tray/name/strings/help/window records; rewards; chat/keybind/options/friends and
   remaining UI/account fields. Standalone `character_Send` metadata lacks this
   enclosing application and dictionary ownership.
4. Decode PowerInfoUpdate, power modes, badges and full-update badge monitors,
   inventory/invention/workshop, conditional team, super stats, conditional
   league, optional attribute descriptions, dynamic groups, sky fade and optional
   slave rotation. These are mandatory wire *boundaries* even where their flags
   legitimately select an absent body. Never infer absence from default fixtures.
5. Decode/refuse the embedded command tail, then check exact end and packet/session
   generation, unique self and selected DBID, dictionary/resource identities,
   delete ordering and aggregate retained/temporary memory. Publish the complete
   immutable actor and global state atomically; a late failure preserves the
   previous published generation. Only this completed transaction may authorize
   application completion signals.

Exact initial packets, matching dictionaries and source profiles remain needed
for authentic replay. Source grammar work above can proceed without another
server launch. Runtime scene-snapshot success cannot close these actor gaps.

## Executable review boundary

Run `python native-android/engine/snapshot-admission/reviews/c/check_boundary.py`.
It hashes five reviewed source files, checks both original outer-tail call orders,
retains the original early-ACK/embedded-command warning, and verifies the current
native refusal/controller command surfaces. Six in-memory regression mutations
must be rejected (false tail success, premature READY/REQALLENTS, variable command,
omitted PowerInfo and ignored embedded commands). Source comments cannot spoof
anchors. This is a narrow source regression audit, not a C parser, protocol
oracle, sanitizer result, Android execution or whole-call-graph proof. No new
production API consumes this report and it cannot grant publication authority.

The retained `boundary-review.json` records success and source hashes. All live
world, complete-update and actor acceptance flags intentionally remain false.
