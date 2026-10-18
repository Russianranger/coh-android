#ifndef COH_FRESH_SOURCE_PROFILE_API_H
#define COH_FRESH_SOURCE_PROFILE_API_H
#include "coh_fresh_folder_profile_api.h"
typedef enum {
 COH_FRESH_STAGE_INSTALL,COH_FRESH_STAGE_NORMAL_ENABLE,COH_FRESH_STAGE_SEAL,
 COH_FRESH_STAGE_BOUNDARY,COH_FRESH_STAGE_QUIET,COH_FRESH_STAGE_OWNER,
 COH_FRESH_STAGE_OPEN,COH_FRESH_STAGE_CATALOG,COH_FRESH_STAGE_RUNTIME,
 COH_FRESH_STAGE_RESOURCES,COH_FRESH_STAGE_BOUNDS,COH_FRESH_STAGE_ELIGIBILITY,
 COH_FRESH_STAGE_PACKET,COH_FRESH_STAGE_QUIET_RELEASE,COH_FRESH_STAGE_COMMIT,
 COH_FRESH_STAGE_ABORT
} CohFreshSourceStage;
/* Exact original failure atoms, in evaluation order. The fresh-only stager
 * wraps each atom once; enum/name expansions do not evaluate these tokens. */
#define COH_FRESH_OWNER_PREDICATES(X) \
 X(INPUT_LINK,!link) \
 X(INPUT_OUTPUT,!out) \
 X(LIST_ABSENT,!net_links.links) \
 X(LIST_EMPTY,net_links.links->size<=0) \
 X(LIST_LIMIT,(unsigned)net_links.links->size>COH_SOURCE_GROUPS_OWNER_MAX_LINKS) \
 X(LIST_STORAGE,!net_links.links->storage) \
 X(LIST_CAPACITY,net_links.links->maxSize<net_links.links->size) \
 X(OUTPUT_LINK_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),link,sizeof(*link))) \
 X(OUTPUT_LIST_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),&net_links,sizeof(net_links))) \
 X(OUTPUT_ARRAY_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),net_links.links,sizeof(*net_links.links))) \
 X(OUTPUT_STORAGE_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),net_links.links->storage,(size_t)net_links.links->size*sizeof(*net_links.links->storage))) \
 X(OUTPUT_WORLD_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),&world_id,sizeof(world_id))) \
 X(OUTPUT_ENTITIES_MAX_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),&entities_max,sizeof(entities_max))) \
 X(OUTPUT_ENTITY_TABLE_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),entities,(size_t)MAX_ENTITIES_PRIVATE*sizeof(*entities))) \
 X(OUTPUT_ENTITY_STATE_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),entity_state,(size_t)MAX_ENTITIES_PRIVATE*sizeof(*entity_state))) \
 X(CLIENT_ABSENT,!client) \
 X(CLIENT_BACKLINK,client->link!=link) \
 X(OUTPUT_CLIENT_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),client,sizeof(*client))) \
 X(ENTITY_ABSENT,!entity) \
 X(OUTPUT_ENTITY_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),entity,sizeof(*entity))) \
 X(ENTITY_BACKLINK,entity->client!=client) \
 X(ENTITY_DBID,entity->db_id<=0) \
 X(ENTITY_ID,!entity->id) \
 X(ENTITY_SLOT_LOW,entity->owner<1) \
 X(ENTITY_SLOT_HIGH,entity->owner>=MAX_ENTITIES_PRIVATE) \
 X(ENTITY_TABLE_SIZE_LOW,entities_max<1) \
 X(ENTITY_TABLE_SIZE_HIGH,entities_max>MAX_ENTITIES_PRIVATE) \
 X(ENTITY_NOT_IN_USE,!entInUse(entity->owner)) \
 X(ENTITY_TABLE_MISMATCH,entities[entity->owner]!=entity) \
 X(CHARACTER_ABSENT,!character) \
 X(OUTPUT_CHARACTER_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),character,sizeof(*character))) \
 X(CHARACTER_UNINITIALIZED,!character_IsInitialized(entity->pchar)) \
 X(CHARACTER_PARENT,character->entParent!=entity) \
 X(LINK_TYPE,link->type!=NLT_UDP) \
 X(LINK_NOT_CONNECTED,!link->connected) \
 X(LINK_PENDING,link->pending) \
 X(LINK_CONNECTING,link->connecting) \
 X(LINK_DISCONNECTED,link->disconnected) \
 X(LINK_DESTROYED,link->destroyed) \
 X(LINK_REMOVED,link->removedFromMasterList) \
 X(LINK_PROTOCOL,link->protocolVersion>5u) \
 X(CLIENT_STATE_LOW,(int)client->ready<(int)CLIENTSTATE_NOT_READY) \
 X(CLIENT_STATE_HIGH,(int)client->ready>(int)CLIENTSTATE_RE_REQALLENTS) \
 X(LIST_ENTRY_ABSENT,!entry) \
 X(OUTPUT_LIST_ENTRY_ALIAS,!coh_source_owner_disjoint(out,sizeof(*out),entry,sizeof(*entry))) \
 X(LINK_INCIDENCE,incidence!=1u) \
 X(CLIENT_INCIDENCE,client_incidence!=1u)
/* Additional fresh-only alternate eligibility refusals. No original value,
 * pointer, player name, state number or ownership identity is exported. */
#define COH_FRESH_INITIAL_OWNER_FAILURES(X) \
 X(INITIAL_SLOT_OUTSIDE_TABLE) \
 X(INITIAL_STATE) \
 X(INITIAL_OUTPUT_ENTINFO_ALIAS) \
 X(INITIAL_NOT_PLAYER) \
 X(INITIAL_NOT_OWNED) \
 X(INITIAL_PLAYER_ABSENT) \
 X(INITIAL_CLIENT_STATE) \
 X(INITIAL_ENTITY_READY) \
 X(INITIAL_RELAY) \
 X(INITIAL_TRANSFER_LOGIN) \
 X(INITIAL_TRANSFER_ACTIVE) \
 X(INITIAL_TRANSFER_WAITING) \
 X(INITIAL_TRANSFER_STEP)
typedef enum {
 COH_FRESH_OWNER_NONE,
#define COH_FRESH_OWNER_ENUM(name,expression) COH_FRESH_OWNER_##name,
 COH_FRESH_OWNER_PREDICATES(COH_FRESH_OWNER_ENUM)
#undef COH_FRESH_OWNER_ENUM
#define COH_FRESH_INITIAL_OWNER_ENUM(name) COH_FRESH_OWNER_##name,
 COH_FRESH_INITIAL_OWNER_FAILURES(COH_FRESH_INITIAL_OWNER_ENUM)
#undef COH_FRESH_INITIAL_OWNER_ENUM
 COH_FRESH_OWNER_COUNT
} CohFreshOwnerFailure;
int coh_fresh_source_owner_failed(int,CohFreshOwnerFailure);
void coh_fresh_source_probe_step(CohFreshSourceStage);
void coh_fresh_source_probe_loader(unsigned,unsigned);
void coh_fresh_source_profile_install(void);
void coh_fresh_source_profile_seal_after_normal_enable(void);
#endif
