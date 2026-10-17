/* NONSHIPPING read-only original MapServer owner preparation. Include only after
 * actual original NetLink/ClientLink/Entity/Character/Array declarations and
 * character_IsInitialized/entInUse declarations. No hook, sink or installation.
 * Single exclusive original client/entity/link owner thread; no yield/lazy load.
 * All original objects/tables must be valid, stable and caller-disjoint. */
#ifndef COH_SOURCE_GROUPS_OWNER_INCLUDED
#define COH_SOURCE_GROUPS_OWNER_INCLUDED
#include <stdint.h>
#include <limits.h>
#include <string.h>
#if UINT_MAX != 0xffffffffu
#error source_owner_requires_32_bit_unsigned
#endif
#define COH_SOURCE_GROUPS_OWNER_BYTES 192u
#define COH_SOURCE_GROUPS_OWNER_MAX_LINKS 65536u
typedef struct CohSourceGroupsOwner {
 unsigned char wire[COH_SOURCE_GROUPS_OWNER_BYTES];
 unsigned links_scanned,link_slot,dbid,entity_id,server_index,protocol_version;
} CohSourceGroupsOwner;
static int coh_source_owner_disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
/* Output commits only after all checks. Source-only association of actual owned
 * client entity, NOT viewed/slave entity, crypto/native decode/world admission.
 * Narrow future capture policy: registered unique connected clean UDP link,
 * valid original initialized Character and exact table/backlink chain.
 * This is deliberately stricter than worldSendUpdate's generic call surface. */
static int coh_source_groups_prepare_owner(const NetLink*link,CohSourceGroupsOwner*out){
 const ClientLink*client;const Entity*entity;const Character*character;unsigned i,slot=0,incidence=0,client_incidence=0;unsigned words[46];CohSourceGroupsOwner candidate;
 if(!link||!out||!net_links.links||net_links.links->size<=0||(unsigned)net_links.links->size>COH_SOURCE_GROUPS_OWNER_MAX_LINKS||!net_links.links->storage||net_links.links->maxSize<net_links.links->size)return 0;
 if(!coh_source_owner_disjoint(out,sizeof(*out),link,sizeof(*link))||!coh_source_owner_disjoint(out,sizeof(*out),&net_links,sizeof(net_links))||!coh_source_owner_disjoint(out,sizeof(*out),net_links.links,sizeof(*net_links.links))||!coh_source_owner_disjoint(out,sizeof(*out),net_links.links->storage,(size_t)net_links.links->size*sizeof(*net_links.links->storage))||!coh_source_owner_disjoint(out,sizeof(*out),&world_id,sizeof(world_id))||!coh_source_owner_disjoint(out,sizeof(*out),&entities_max,sizeof(entities_max))||!coh_source_owner_disjoint(out,sizeof(*out),entities,(size_t)MAX_ENTITIES_PRIVATE*sizeof(*entities))||!coh_source_owner_disjoint(out,sizeof(*out),entity_state,(size_t)MAX_ENTITIES_PRIVATE*sizeof(*entity_state)))return 0;
 client=(const ClientLink*)link->userData;
 if(!client||client->link!=link||!coh_source_owner_disjoint(out,sizeof(*out),client,sizeof(*client)))return 0;
 entity=client->entity;
 if(!entity||!coh_source_owner_disjoint(out,sizeof(*out),entity,sizeof(*entity))||entity->client!=client||entity->db_id<=0||!entity->id||entity->owner<1||entity->owner>=MAX_ENTITIES_PRIVATE||entities_max<1||entities_max>MAX_ENTITIES_PRIVATE||!entInUse(entity->owner)||entities[entity->owner]!=entity)return 0;
 character=entity->pchar;
 if(!character||!coh_source_owner_disjoint(out,sizeof(*out),character,sizeof(*character))||!character_IsInitialized(entity->pchar)||character->entParent!=entity)return 0;
 if(link->type!=NLT_UDP||!link->connected||link->pending||link->connecting||link->disconnected||link->destroyed||link->removedFromMasterList||link->protocolVersion>5u||(int)client->ready<(int)CLIENTSTATE_NOT_READY||(int)client->ready>(int)CLIENTSTATE_RE_REQALLENTS)return 0;
 for(i=0;i<(unsigned)net_links.links->size;i++){
  const NetLink*entry=(const NetLink*)net_links.links->storage[i];
  if(!entry||!coh_source_owner_disjoint(out,sizeof(*out),entry,sizeof(*entry)))return 0;
  if(entry==link){slot=i;incidence++;}if(entry->userData==client)client_incidence++;
 }
 if(incidence!=1u||client_incidence!=1u)return 0;
 memset(&candidate,0,sizeof(candidate));memset(words,0,sizeof(words));
 words[0]=1;words[1]=COH_SOURCE_GROUPS_OWNER_BYTES;words[2]=(unsigned)entity->db_id;words[3]=entity->id;words[4]=(unsigned)entity->owner;words[5]=(unsigned)client->ready;words[6]=(unsigned)entity->ready;
 words[7]=link->UID;words[8]=link->connection_id;words[9]=link->connect_id;words[10]=link->protocolVersion;words[11]=(unsigned)link->type;words[12]=(unsigned)link->opType;words[13]=(unsigned)net_links.links->size;words[14]=slot;
 words[15]=link->connected;words[16]=link->pending;words[17]=link->connecting;words[18]=link->disconnected;words[19]=link->destroyed;words[20]=link->removedFromMasterList;
 words[21]=link->compressionAllowed;words[22]=link->compressionDefault;words[23]=link->orderedAllowed;words[24]=link->orderedDefault;words[25]=link->controlCommandsSeparate;words[26]=link->cookieSend;words[27]=link->cookieEcho;
 words[28]=link->last_update_time;words[29]=(unsigned)link->last_world_id;words[30]=(unsigned)world_id;words[31]=link->last_processed_id;words[32]=link->last_recv_id;words[33]=link->last_ordered_recv_id;words[34]=client->lastSentFullUpdateID;words[35]=client->ackedFullUpdateID;words[36]=(unsigned)entity->map_id;words[37]=(unsigned)entity->static_map_id;words[38]=1;words[39]=1;words[40]=1;words[45]=entity->auth_id;
 memcpy(candidate.wire,"COHOWN01",8);for(i=0;i<46;i++){unsigned v=words[i];candidate.wire[8+i*4]=(unsigned char)v;candidate.wire[9+i*4]=(unsigned char)(v>>8);candidate.wire[10+i*4]=(unsigned char)(v>>16);candidate.wire[11+i*4]=(unsigned char)(v>>24);}
 candidate.links_scanned=(unsigned)net_links.links->size;candidate.link_slot=slot;candidate.dbid=(unsigned)entity->db_id;candidate.entity_id=entity->id;candidate.server_index=(unsigned)entity->owner;candidate.protocol_version=link->protocolVersion;*out=candidate;return 1;
}
#endif
