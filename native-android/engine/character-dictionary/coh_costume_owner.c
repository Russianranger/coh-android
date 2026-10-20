#include "coh_costume_owner.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include "costume_owner_bodytypes.inc"
typedef struct {const void *p;size_t n;} Span;
typedef struct {CohBytes bytes;size_t at;} Cursor;
struct CohCostumeOwner {
 CohEntCostumeDictionary *dictionary;size_t bytes,body_bytes;
 uint32_t parts,types,retired,borrowers;uint64_t serial,leases[COH_COSTUME_OWNER_LEASE_MAX];
 CohCostumeOwnerLease *lease_addresses[COH_COSTUME_OWNER_LEASE_MAX];
 CohCostumeBodyPins body_pins;CohCostumeImportPins dictionary_pins;
 unsigned char body[];
};
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:s.n==0;}
static int separate(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int nonzero(const uint8_t *s){unsigned i;uint8_t v=0;for(i=0;i<32;i++)v|=s[i];return v!=0;}
static int add(size_t *n,size_t v,size_t cap){if(v>cap||*n>cap-v)return 0;*n+=v;return 1;}
static void wipe(void *p,size_t n){volatile unsigned char *v=p;while(n--)*v++=0;}
static const uint8_t *take(Cursor *c,size_t n){const uint8_t *p;if(n>c->bytes.size-c->at)return NULL;p=c->bytes.data+c->at;c->at+=n;return p;}
static uint32_t word(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int string(Cursor *c,int path){const uint8_t *p=take(c,2);size_t n;if(!p)return 0;n=(size_t)p[0]|(size_t)p[1]<<8;if(n==65535)return !path;if(n>259)return 0;p=take(c,n);return p&&!memchr(p,0,n);}
static CohStatus witness(CohBytes bytes,const CohCostumeBodyPins *pins,uint32_t expected_parts){
 Cursor c={bytes,0};const uint8_t *p;uint32_t h[8],i,j;size_t path_at;
 p=take(&c,8);if(!p||memcmp(p,"COHBW1\0\0",8))return COH_INVALID;
 for(i=0;i<8;i++){p=take(&c,4);if(!p)return COH_INVALID;h[i]=word(p);}
 if(h[0]!=1)return COH_UNSUPPORTED;
 if(h[1]<1||h[1]>3||h[2]>2||h[3]>1||h[4]!=2||!h[5]||h[5]>=COH_COSTUME_PART_MAX||h[6]||h[7])return COH_STATE;
 if(h[5]!=expected_parts)return COH_STATE;
 if((h[1]==1&&(h[2]||h[3]))||(h[1]!=1&&!(h[2]==2||h[3]))||(h[2]==2&&h[3]))return COH_STATE;
 for(i=0;i<4;i++){
  const uint8_t *pin=i==0?pins->source_sha256:i==1?pins->build_sha256:i==2?pins->profile_sha256:pins->run_sha256;
  p=take(&c,32);if(!p||!nonzero(pin)||memcmp(p,pin,32))return COH_STATE;
 }
 path_at=c.at;if(!string(&c,1))return COH_INVALID;
 if(h[1]==1&&c.at!=path_at+2)return COH_STATE;
 if(h[2]==2&&c.at==path_at+2)return COH_STATE;
 for(i=0;i<h[5];i++){
  p=take(&c,24);if(!p)return COH_INVALID;
  /* Preserve all signed32 bone/cost bits. Postload index is original order;
   * source supports one/two bones; DontClear originates from U8. */
  if(word(p+8)!=i||(word(p+12)!=1&&word(p+12)!=2)||word(p+20)>255)return COH_STATE;
  for(j=0;j<5;j++)if(!string(&c,0))return COH_INVALID;
 }
 return c.at==bytes.size?COH_OK:COH_INVALID;
}
CohStatus coh_costume_owner_candidate(CohBytes dictionary,CohBytes body,
 const CohCostumeImportPins *pins,const CohCostumeBodyPins *bodypins,
 const CohCostumeImportDigest *digest,CohCostumeOwner **out,CohCostumeOwnerReceipt *receipt,
 size_t budget,size_t retained){
 Span s[8];size_t i,j,reserve,allocation;CohStatus status;CohCostumeOwner *owner;
 CohCostumeOwnerReceipt result;uint8_t hash[32];
 if(!dictionary.data||!body.data||!pins||!bodypins||!digest||!out||!receipt)return COH_INVALID;
 if(!body.size||body.size>COH_COSTUME_OWNER_BODY_MAX||dictionary.size>COH_COSTUME_IMPORT_INPUT_MAX)return COH_LIMIT;
 s[0]=(Span){dictionary.data,dictionary.size};s[1]=(Span){body.data,body.size};s[2]=(Span){pins,sizeof(*pins)};
 s[3]=(Span){bodypins,sizeof(*bodypins)};s[4]=(Span){digest,sizeof(*digest)};s[5]=(Span){out,sizeof(*out)};s[6]=(Span){receipt,sizeof(*receipt)};
 for(i=0;i<7;i++){if(!valid(s[i]))return COH_INVALID;for(j=0;j<i;j++)if(!separate(s[i],s[j]))return COH_INVALID;}
 if(*out||!digest->sha256)return COH_STATE;
 s[7]=(Span){digest->context,digest->context_bytes};if(!valid(s[7]))return COH_INVALID;
 for(i=0;i<7;i++)if(!separate(s[i],s[7]))return COH_INVALID;
 if(!pins->generation||!pins->body_parts||pins->body_parts>=COH_COSTUME_PART_MAX||pins->body_types!=9||
    !nonzero(bodypins->payload_sha256)||memcmp(pins->profile_sha256,bodypins->profile_sha256,32)||memcmp(pins->run_sha256,bodypins->run_sha256,32))return COH_STATE;
 status=witness(body,bodypins,pins->body_parts);if(status!=COH_OK)return status;
 if(!budget||budget>COH_COSTUME_IMPORT_BUDGET_MAX)return COH_LIMIT;
 allocation=sizeof(*owner)+body.size;reserve=retained;
 /* Conservative duplicate control/stack charges include this wrapper while
  * the unchanged importer charges its own input/digest/temporary closure. */
 if(!add(&reserve,allocation,budget)||!add(&reserve,sizeof(bodytype_definitions),budget)||!add(&reserve,COH_COSTUME_OWNER_STACK_RESERVE,budget)||!add(&reserve,sizeof(result)+sizeof(hash),budget)||
    !add(&reserve,COH_COSTUME_OWNER_LEASE_MAX*(sizeof(CohCostumeOwnerLease)+sizeof(CohCostumeOwnerView)),budget))return COH_LIMIT;
 for(i=0;i<8;i++)if(!add(&reserve,s[i].n,budget))return COH_LIMIT;
 /* Bound the importer maximum dictionary and fixed stack before either
  * digest call; its exact temporary-slot preflight repeats before allocation. */
 {size_t pre=reserve,temp;uint32_t slots[3];
  if(dictionary.size<176)return COH_INVALID;
  for(i=0;i<3;i++){slots[i]=word(dictionary.data+24+i*4);if(slots[i]<2||slots[i]>COH_COSTUME_DICTIONARY_SLOT_MAX||(slots[i]&(slots[i]-1)))return COH_LIMIT;}
  temp=((size_t)slots[0]+slots[1])*sizeof(CohBytes)+(size_t)slots[2]*5;
  if(!add(&pre,COH_COSTUME_DICTIONARY_BYTES_MAX,budget)||!add(&pre,COH_COSTUME_IMPORT_STACK_RESERVE,budget)||!add(&pre,digest->scratch_reserve,budget)||!add(&pre,temp,budget))return COH_LIMIT;
  /* The importer also charges these independent input/control spans. */
  if(!add(&pre,dictionary.size,budget)||!add(&pre,sizeof(*pins)+sizeof(*digest)+sizeof(owner->dictionary)+sizeof(result.dictionary)+digest->context_bytes,budget))return COH_LIMIT;
 }
 status=digest->sha256(digest->context,body,hash);if(status!=COH_OK)return status;
 if(memcmp(hash,bodypins->payload_sha256,32))return COH_STATE;
 owner=calloc(1,allocation);if(!owner)return COH_LIMIT;
 owner->bytes=allocation;owner->body_bytes=body.size;owner->parts=pins->body_parts;owner->types=pins->body_types;
 owner->body_pins=*bodypins;owner->dictionary_pins=*pins;memcpy(owner->body,body.data,body.size);
 memset(&result,0,sizeof(result));
 status=coh_costume_import(dictionary,pins,digest,&owner->dictionary,&result.dictionary,budget,reserve);
 if(status!=COH_OK){wipe(owner,allocation);free(owner);return status;}
 result.owner_bytes=allocation+result.dictionary.dictionary_bytes;result.body_witness_bytes=body.size;
 result.charged_peak_bytes=result.dictionary.charged_peak_bytes;result.body_parts=owner->parts;result.body_types=owner->types;
 *receipt=result;*out=owner;return COH_OK;
}
size_t coh_costume_owner_bytes(const CohCostumeOwner *owner){return owner?owner->bytes+coh_ent_costume_dictionary_bytes(owner->dictionary):0;}
static CohStatus immutable_disjoint(const CohCostumeOwner *owner,const void *out,size_t n){
 Span s={out,n};if(!valid(s))return COH_INVALID;
 if(!separate(s,(Span){bodytype_definitions,sizeof(bodytype_definitions)}))return COH_INVALID;
 if(owner&&(!separate(s,(Span){owner,owner->bytes})||!separate(s,(Span){owner->dictionary,coh_ent_costume_dictionary_bytes(owner->dictionary)})))return COH_INVALID;
 return COH_OK;
}
CohStatus coh_costume_owner_output_disjoint(const CohCostumeOwner *owner,const void *out,size_t n){
 unsigned i;Span s={out,n};CohStatus status=immutable_disjoint(owner,out,n);if(status!=COH_OK)return status;
 if(owner)for(i=0;i<COH_COSTUME_OWNER_LEASE_MAX;i++)if(owner->leases[i]&&!separate(s,(Span){owner->lease_addresses[i],sizeof(CohCostumeOwnerLease)}))return COH_INVALID;
 return COH_OK;
}
CohStatus coh_costume_owner_borrow(CohCostumeOwner *owner,CohCostumeOwnerLease *lease,CohCostumeOwnerView *view){
 unsigned i;Span s[3];
 if(!owner||!lease||!view)return COH_INVALID;
 s[0]=(Span){owner,owner->bytes};s[1]=(Span){lease,sizeof(*lease)};s[2]=(Span){view,sizeof(*view)};
 for(i=0;i<3;i++)if(!valid(s[i]))return COH_INVALID;
 if(coh_costume_owner_output_disjoint(owner,lease,sizeof(*lease))!=COH_OK||coh_costume_owner_output_disjoint(owner,view,sizeof(*view))!=COH_OK)return COH_INVALID;
 if(!separate(s[0],s[1])||!separate(s[0],s[2])||!separate(s[1],s[2])||
    !separate((Span){owner->dictionary,coh_ent_costume_dictionary_bytes(owner->dictionary)},s[1])||
    !separate((Span){owner->dictionary,coh_ent_costume_dictionary_bytes(owner->dictionary)},s[2]))return COH_INVALID;
 if(owner->retired||lease->owner||owner->serial==UINT64_MAX)return COH_STATE;
 for(i=0;i<COH_COSTUME_OWNER_LEASE_MAX;i++)if(!owner->leases[i])break;
 if(i==COH_COSTUME_OWNER_LEASE_MAX)return COH_LIMIT;
 owner->leases[i]=++owner->serial;owner->lease_addresses[i]=lease;owner->borrowers++;
 *lease=(CohCostumeOwnerLease){owner,i,owner->serial};
 *view=(CohCostumeOwnerView){owner->dictionary,{owner->body,owner->body_bytes},{(const uint8_t*)bodytype_definitions,sizeof(bodytype_definitions)-1},owner->parts,owner->types};return COH_OK;
}
CohStatus coh_costume_owner_release(CohCostumeOwnerLease *lease){
 CohCostumeOwner *owner;if(!lease||!lease->owner)return COH_STATE;owner=lease->owner;
 if(immutable_disjoint(owner,lease,sizeof(*lease))!=COH_OK)return COH_INVALID;
 if(lease->slot>=COH_COSTUME_OWNER_LEASE_MAX||!lease->serial||owner->leases[lease->slot]!=lease->serial||owner->lease_addresses[lease->slot]!=lease||!owner->borrowers)return COH_STATE;
 owner->leases[lease->slot]=0;owner->lease_addresses[lease->slot]=NULL;owner->borrowers--;memset(lease,0,sizeof(*lease));return COH_OK;
}
CohStatus coh_costume_owner_retire(CohCostumeOwner *owner){if(!owner)return COH_INVALID;owner->retired=1;return COH_OK;}
CohStatus coh_costume_owner_destroy(CohCostumeOwner **slot){
 CohCostumeOwner *owner;size_t bytes;if(!slot||!valid((Span){slot,sizeof(*slot)}))return COH_INVALID;
 owner=*slot;if(!owner)return COH_OK;
 if(coh_costume_owner_output_disjoint(owner,slot,sizeof(*slot))!=COH_OK)return COH_INVALID;
 if(owner->borrowers)return COH_STATE;
 bytes=owner->bytes;coh_ent_costume_dictionary_free(owner->dictionary);wipe(owner,bytes);free(owner);*slot=NULL;return COH_OK;
}
CohStatus coh_costume_owner_replace(CohCostumeOwner **current,CohCostumeOwner **candidate){
 unsigned i,j;Span slots[2],owners[4];
 if(!current||!candidate||!valid((Span){current,sizeof(*current)})||!valid((Span){candidate,sizeof(*candidate)})||!separate((Span){current,sizeof(*current)},(Span){candidate,sizeof(*candidate)}))return COH_INVALID;
 if(!*candidate||*current==*candidate||(*candidate)->retired||(*candidate)->borrowers||(*current&&(*current)->borrowers))return COH_STATE;
 slots[0]=(Span){current,sizeof(*current)};slots[1]=(Span){candidate,sizeof(*candidate)};
 owners[0]=(Span){*candidate,(*candidate)->bytes};owners[1]=(Span){(*candidate)->dictionary,coh_ent_costume_dictionary_bytes((*candidate)->dictionary)};
 owners[2]=(Span){*current,*current?(*current)->bytes:0};owners[3]=(Span){*current?(*current)->dictionary:NULL,*current?coh_ent_costume_dictionary_bytes((*current)->dictionary):0};
 for(i=0;i<2;i++){
  if(coh_costume_owner_output_disjoint(*candidate,slots[i].p,slots[i].n)!=COH_OK||coh_costume_owner_output_disjoint(*current,slots[i].p,slots[i].n)!=COH_OK)return COH_INVALID;
  for(j=0;j<4;j++)if(!separate(slots[i],owners[j]))return COH_INVALID;
 }
 if(*current)coh_costume_owner_destroy(current);
 *current=*candidate;*candidate=NULL;return COH_OK;
}
CohStatus coh_costume_owner_query(const CohCostumeOwner *owner,const CohCostumePacketBinding *binding,uint32_t *parts,uint32_t *types){
 Span s[5];unsigned i,j;
 if(!owner)return COH_NOT_FOUND;
 if(!binding||!parts||!types)return COH_INVALID;
 s[0]=(Span){owner,owner->bytes};s[1]=(Span){binding,sizeof(*binding)};s[2]=(Span){parts,sizeof(*parts)};s[3]=(Span){types,sizeof(*types)};
 for(i=0;i<4;i++){if(!valid(s[i]))return COH_INVALID;for(j=0;j<i;j++)if(!separate(s[i],s[j]))return COH_INVALID;}
 if(coh_costume_owner_output_disjoint(owner,parts,sizeof(*parts))!=COH_OK||coh_costume_owner_output_disjoint(owner,types,sizeof(*types))!=COH_OK)return COH_INVALID;
 s[4]=(Span){binding->packet.data,binding->packet.size};if(!valid(s[4]))return COH_INVALID;
 for(i=0;i<4;i++)if(!separate(s[i],s[4]))return COH_INVALID;
 for(i=1;i<5;i++)if(!separate(s[i],(Span){owner->dictionary,coh_ent_costume_dictionary_bytes(owner->dictionary)}))return COH_INVALID;
 if(owner->retired)return COH_STATE;
 if(!binding->packet.data||!binding->packet.size||binding->packet.size>COH_REP_BOUNDED_MESSAGE_MAX||binding->bit_length>binding->packet.size*8||!binding->bit_length||binding->compressed>1)return COH_INVALID;
 if(!binding->loan_owner||!binding->session_owner||!binding->source_owner||!binding->generation_owner||!binding->generation||binding->generation!=owner->dictionary_pins.generation)return COH_STATE;
 /* COHBW1 explicitly encodes zero generation/authority. COHCDI1 labels and a
  * matching packet generation cannot supply an authentic source runtime lease.
  * No caller-provided bit can cross this boundary. */
 return COH_UNSUPPORTED;
}
