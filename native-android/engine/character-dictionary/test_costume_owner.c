#define OPENSSL_API_COMPAT 0x10100000L
#include "coh_costume_owner.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,allocations,frees,fail_allocation,digests,digest_fail;
void *__real_calloc(size_t,size_t);void __real_free(void *);
void *__wrap_calloc(size_t n,size_t s){allocations++;if(fail_allocation==allocations)return NULL;return __real_calloc(n,s);}
void __wrap_free(void *p){if(p)frees++;__real_free(p);}
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint8_t cdi[4096],body[65536],save_cdi[4096],save_body[65536];static size_t cn,bn;
static CohCostumeImportPins pins;static CohCostumeBodyPins bpins;
static CohCostumeOwnerReceipt receipt,prior;
static CohCostumeOwner *owner;
static CohStatus digest(void *context,CohBytes bytes,uint8_t out[32]){SHA256_CTX c;(void)context;digests++;if(digest_fail==digests)return COH_IO;return SHA256_Init(&c)&&SHA256_Update(&c,bytes.data,bytes.size)&&SHA256_Final(out,&c)?COH_OK:COH_IO;}
static CohCostumeImportDigest provider={digest,NULL,0,16384};
static void putword(uint8_t *p,uint32_t v){unsigned i;for(i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));}
static void word(uint8_t *p,size_t *at,uint32_t v){putword(p+*at,v);*at+=4;}
static void text(uint8_t *p,size_t *at,const char *v){size_t n=v?strlen(v):65535;p[(*at)++]=(uint8_t)n;p[(*at)++]=(uint8_t)(n>>8);if(v){memcpy(p+*at,v,n);*at+=n;}}
static void hashes(void){unsigned n=digests;digest_fail=0;CHECK(digest(NULL,(CohBytes){cdi,cn},pins.payload_sha256)==COH_OK);CHECK(digest(NULL,(CohBytes){body,bn},bpins.payload_sha256)==COH_OK);digests=n;}
static void build(void){
 unsigned i,j;memset(&pins,0,sizeof(pins));memset(&bpins,0,sizeof(bpins));
 pins.generation=17;pins.body_parts=2;pins.body_types=9;memcpy(pins.source_sha256,coh_costume_import_source_id,32);
 memset(pins.inventory_sha256,1,32);memset(pins.profile_sha256,2,32);memset(pins.run_sha256,3,32);
 memset(bpins.source_sha256,4,32);memset(bpins.build_sha256,5,32);memcpy(bpins.profile_sha256,pins.profile_sha256,32);memcpy(bpins.run_sha256,pins.run_sha256,32);
 memcpy(cdi,"COHCDI1\0",8);cn=8;word(cdi,&cn,1);word(cdi,&cn,pins.generation);word(cdi,&cn,2);word(cdi,&cn,9);
 for(i=0;i<3;i++)word(cdi,&cn,8);
 word(cdi,&cn,2);word(cdi,&cn,1);word(cdi,&cn,1);
 memcpy(cdi+cn,pins.source_sha256,32);cn+=32;memcpy(cdi+cn,pins.inventory_sha256,32);cn+=32;memcpy(cdi+cn,pins.profile_sha256,32);cn+=32;memcpy(cdi+cn,pins.run_sha256,32);cn+=32;
 for(i=0;i<8;i++)text(cdi,&cn,i==2?"":i==5?"SM_Chest.geo":NULL);
 for(i=0;i<8;i++)text(cdi,&cn,i==1?"Chest":NULL);
 for(i=0;i<8;i++){cdi[cn++]=(uint8_t)(i==6);word(cdi,&cn,i==6?0xff030201:0);}
 memcpy(body,"COHBW1\0\0",8);bn=8;
 {uint32_t header[8]={1,2,2,0,2,2,0,0};for(i=0;i<8;i++)word(body,&bn,header[i]);}
 memcpy(body+bn,bpins.source_sha256,32);bn+=32;memcpy(body+bn,bpins.build_sha256,32);bn+=32;memcpy(body+bn,bpins.profile_sha256,32);bn+=32;memcpy(body+bn,bpins.run_sha256,32);bn+=32;
 text(body,&bn,"/isolated/bin/BodyParts.bin");
 for(i=0;i<2;i++){
  word(body,&bn,0xffffffff);word(body,&bn,0x80000000);word(body,&bn,i);word(body,&bn,1+i);word(body,&bn,0xffffffff-i);word(body,&bn,255);
  for(j=0;j<5;j++)text(body,&bn,j==0?NULL:j==1?"":j==2?"texture":j==3?"base":"defs/body.def");
 }
 hashes();memcpy(save_cdi,cdi,cn);memcpy(save_body,body,bn);
}
static CohStatus candidate(size_t cap,size_t retained){return coh_costume_owner_candidate((CohBytes){cdi,cn},(CohBytes){body,bn},&pins,&bpins,&provider,&owner,&receipt,cap,retained);}
static void refuse(size_t cap,size_t retained){prior=receipt;CHECK(!owner);CHECK(candidate(cap,retained)!=COH_OK);CHECK(!owner&&!memcmp(&receipt,&prior,sizeof(receipt)));}
typedef struct{uint8_t data[4096];size_t bit;unsigned mode;} Writer;
static void bits(Writer *w,unsigned n,uint32_t v){unsigned i;if(w->mode)n=((n+7)/8)*8;for(i=0;i<n;i++){w->data[w->bit/8]|=((v>>i)&1)<<(w->bit%8);w->bit++;}}
static void pack(Writer *w,unsigned n,uint32_t v){CHECK(v<((1u<<n)-1));bits(w,w->mode?32:n,v);}
static void string(Writer *w,int index){bits(w,1,0);bits(w,1,index>=0);if(index>=0){bits(w,1,1);pack(w,3,(uint32_t)index);}}
static CohEntCostumeWorkspace workspace;static CohEntCostume costume,previous;
static void wire(const CohEntCostumeDictionary *d,unsigned mode,int hole){
 Writer w={{0},0,mode};CohRepReader r,before;CohEntFailure failure;CohStatus s;unsigned i;
 bits(&w,1,0);bits(&w,1,0);pack(&w,6,0);bits(&w,32,0xff102030);bits(&w,1,0);bits(&w,3,0);bits(&w,1,1);
 for(i=0;i<72;i++)bits(&w,32,0);
 for(i=0;i<30;i++)bits(&w,32,0);
 bits(&w,1,1);pack(&w,4,1);string(&w,hole?4:5);string(&w,2);string(&w,-1);string(&w,-1);bits(&w,1,0);
 bits(&w,1,0);bits(&w,1,1);pack(&w,3,6);bits(&w,1,0);bits(&w,1,0);bits(&w,32,0);
 bits(&w,1,1);bits(&w,1,1);pack(&w,3,1);bits(&w,1,0);
 r=(CohRepReader){{w.data,(w.bit+7)/8},w.bit,0,mode,0};before=r;memset(&costume,0xa5,sizeof(costume));previous=costume;
 s=coh_ent_costume(&r,d,17,&workspace,&costume,&failure);
 if(hole){CHECK(s==COH_NOT_FOUND);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&costume,&previous,sizeof(costume)));}
 else{CHECK(s==COH_OK);CHECK(r.cursor==w.bit&&costume.part_count==1);CHECK(!strcmp(costume.parts[0].geometry.value,"SM_Chest.geo"));CHECK(costume.parts[0].texture1.present&&!costume.parts[0].texture1.value[0]);CHECK(!costume.parts[0].texture2.present);CHECK(costume.parts[0].colors[0]==0xff030201);CHECK(!strcmp(costume.parts[0].region.value,"Chest"));}
}
static void lifecycle(void){
 CohCostumeOwnerLease leases[COH_COSTUME_OWNER_LEASE_MAX]={{0}},copy={0},extra={0};CohCostumeOwnerView view;
 CohCostumeOwner *other=NULL,*same;unsigned i;uint8_t packet[4]={0};uint32_t counts[2]={111,222};
 CohCostumePacketBinding binding={{packet,sizeof(packet)},32,0,&packet,&pins,&bpins,&provider,17};
 CHECK(candidate(COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_OK);CHECK(owner&&receipt.body_parts==2&&receipt.body_types==9);
 CHECK(receipt.dictionary.slots[0]==8&&receipt.dictionary.present[0]==2&&receipt.dictionary.present[1]==1&&receipt.dictionary.present[2]==1);
 CHECK(receipt.owner_bytes==coh_costume_owner_bytes(owner));CHECK(!receipt.dictionary.capture_origin_verified&&!receipt.dictionary.actor_authority);
 CHECK(coh_costume_owner_query(NULL,&binding,&counts[0],&counts[1])==COH_NOT_FOUND);
 CHECK(coh_costume_owner_query(owner,&binding,&counts[0],&counts[1])==COH_UNSUPPORTED);CHECK(counts[0]==111&&counts[1]==222);
 binding.generation++;CHECK(coh_costume_owner_query(owner,&binding,&counts[0],&counts[1])==COH_STATE);binding.generation--;
 binding.generation_owner=NULL;CHECK(coh_costume_owner_query(owner,&binding,&counts[0],&counts[1])==COH_STATE);binding.generation_owner=&provider;
 binding.packet.data=(const uint8_t*)(uintptr_t)(UINTPTR_MAX-1);CHECK(coh_costume_owner_query(owner,&binding,&counts[0],&counts[1])==COH_INVALID);binding.packet.data=packet;
 CHECK(coh_costume_owner_query(owner,&binding,&counts[0],&counts[0])==COH_INVALID);
 for(i=0;i<COH_COSTUME_OWNER_LEASE_MAX;i++)CHECK(coh_costume_owner_borrow(owner,&leases[i],&view)==COH_OK);
 CHECK(view.body_parts==2&&view.body_types==9&&view.body_witness.size==bn&&!memcmp(view.body_witness.data,body,bn));CHECK(view.bodytype_definitions.size==1383);
 CHECK(coh_costume_owner_output_disjoint(owner,owner,1)==COH_INVALID);
 CHECK(coh_costume_owner_output_disjoint(owner,view.body_witness.data+view.body_witness.size-1,2)==COH_INVALID);
 CHECK(coh_costume_owner_output_disjoint(owner,view.dictionary,1)==COH_INVALID);
 CHECK(coh_costume_owner_output_disjoint(owner,view.bodytype_definitions.data,1)==COH_INVALID);
 CHECK(coh_costume_owner_output_disjoint(owner,(const void*)(uintptr_t)(UINTPTR_MAX-1),3)==COH_INVALID);
 CHECK(coh_costume_owner_output_disjoint(NULL,packet,sizeof(packet))==COH_OK);
 CHECK(coh_costume_owner_output_disjoint(NULL,NULL,1)==COH_INVALID);
 CHECK(coh_costume_owner_borrow(owner,(CohCostumeOwnerLease*)(void*)view.body_witness.data,&view)==COH_INVALID);
 CHECK(coh_costume_owner_query(owner,&binding,(uint32_t*)(void*)view.dictionary,&counts[1])==COH_INVALID);
 CHECK(coh_costume_owner_output_disjoint(owner,&leases[0],sizeof(leases[0]))==COH_INVALID);
 CHECK(coh_costume_owner_borrow(owner,(CohCostumeOwnerLease*)(void*)((uint8_t*)&leases[0]+8),&view)==COH_INVALID);
 CHECK(coh_costume_owner_borrow(owner,&extra,(CohCostumeOwnerView*)(void*)&leases[0])==COH_INVALID);
 CHECK(coh_costume_owner_borrow(owner,&extra,&view)==COH_LIMIT);copy=leases[0];
 CHECK(coh_costume_owner_release(&copy)==COH_STATE);
 CHECK(coh_costume_owner_destroy(&owner)==COH_STATE&&owner);
 same=owner;owner=NULL;CHECK(candidate(COH_COSTUME_IMPORT_BUDGET_MAX,coh_costume_owner_bytes(same))==COH_OK);other=owner;owner=same;
 CHECK(coh_costume_owner_replace(&owner,&other)==COH_STATE&&owner==same&&other);
 /* Source data destruction cannot affect copied row bytes, keys or holes. */
 memset(cdi,0,cn);memset(body,0,bn);CHECK(!memcmp(view.body_witness.data,save_body,bn));wire(view.dictionary,0,0);wire(view.dictionary,1,0);wire(view.dictionary,0,1);wire(view.dictionary,1,1);
 CHECK(coh_costume_owner_retire(owner)==COH_OK);CHECK(coh_costume_owner_query(owner,&binding,&counts[0],&counts[1])==COH_STATE);CHECK(coh_costume_owner_borrow(owner,&extra,&view)==COH_STATE);
 wire(view.dictionary,0,0);CHECK(!memcmp(view.body_witness.data,save_body,bn));
 for(i=0;i<COH_COSTUME_OWNER_LEASE_MAX;i++)CHECK(coh_costume_owner_release(&leases[i])==COH_OK);
 CHECK(coh_costume_owner_release(&copy)==COH_STATE);CHECK(coh_costume_owner_release(&leases[0])==COH_STATE);
 CHECK(coh_costume_owner_replace(&owner,&other)==COH_OK&&owner&&other==NULL);CHECK(coh_costume_owner_destroy(&owner)==COH_OK&&!owner);
 memcpy(cdi,save_cdi,cn);memcpy(body,save_body,bn);
}
static void maximum(void){
 unsigned i,j;char value[260];CohCostumeOwnerLease lease={0};CohCostumeOwnerView view;
 size_t saved=bn;uint8_t saved_hash[32];memcpy(saved_hash,pins.payload_sha256,32);
 pins.body_parts=29;putword(cdi+16,29);putword(body+28,29);bn=168;text(body,&bn,"/isolated/bin/BodyParts.bin");memset(value,'x',259);value[259]=0;
 for(i=0;i<29;i++){word(body,&bn,0xffffffff);word(body,&bn,0x80000000);word(body,&bn,i);word(body,&bn,i%2+1);word(body,&bn,0xffffffff-i);word(body,&bn,255);for(j=0;j<5;j++)text(body,&bn,value);}
 hashes();CHECK(candidate(COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_OK);CHECK(receipt.body_parts==29&&receipt.body_witness_bytes==bn&&receipt.charged_peak_bytes<=COH_COSTUME_IMPORT_BUDGET_MAX);
 CHECK(coh_costume_owner_borrow(owner,&lease,&view)==COH_OK&&!memcmp(view.body_witness.data,body,bn));CHECK(coh_costume_owner_release(&lease)==COH_OK);CHECK(coh_costume_owner_destroy(&owner)==COH_OK);
 /* Original source's larger capacities are deliberately unsupported here. */
 pins.body_parts=30;putword(cdi+16,30);putword(body+28,30);hashes();refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);
 pins.body_parts=2;memcpy(cdi,save_cdi,cn);bn=saved;memcpy(body,save_body,bn);memcpy(pins.payload_sha256,saved_hash,32);hashes();
}
int main(void){
 unsigned i,before_calls,before_allocs;size_t saved_bn,peak,bytes;CohCostumeOwnerReceipt old;
 build();CHECK(candidate(COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_OK);peak=receipt.charged_peak_bytes;bytes=receipt.owner_bytes;CHECK(coh_costume_owner_destroy(&owner)==COH_OK);
 before_calls=digests;before_allocs=allocations;refuse(peak-1,0);CHECK(digests==before_calls&&allocations==before_allocs);CHECK(candidate(peak,0)==COH_OK);CHECK(coh_costume_owner_destroy(&owner)==COH_OK);
 before_calls=digests;refuse(COH_COSTUME_IMPORT_BUDGET_MAX,SIZE_MAX);CHECK(digests==before_calls);
 for(i=1;i<=3;i++){fail_allocation=allocations+i;old=receipt;CHECK(candidate(COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_LIMIT);CHECK(!owner&&!memcmp(&old,&receipt,sizeof(old)));fail_allocation=0;}
 for(i=1;i<=2;i++){digest_fail=digests+i;refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);digest_fail=0;}
 saved_bn=bn;for(bn=0;bn<saved_bn;bn++)refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);bn=saved_bn;
 for(i=0;i<bn;i++){body[i]^=1;hashes();old=receipt;CohStatus status=candidate(COH_COSTUME_IMPORT_BUDGET_MAX,0);if(status==COH_OK){CHECK(coh_costume_owner_destroy(&owner)==COH_OK);}else CHECK(!owner&&!memcmp(&receipt,&old,sizeof(old)));body[i]^=1;}hashes();
 bpins.payload_sha256[0]^=1;refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);bpins.payload_sha256[0]^=1;
 pins.profile_sha256[0]^=1;refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);pins.profile_sha256[0]^=1;
 pins.run_sha256[0]^=1;refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);pins.run_sha256[0]^=1;
 bpins.build_sha256[0]^=1;refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);bpins.build_sha256[0]^=1;
 pins.body_parts=3;refuse(COH_COSTUME_IMPORT_BUDGET_MAX,0);pins.body_parts=2;
 prior=receipt;CHECK(coh_costume_owner_candidate((CohBytes){cdi,cn},(CohBytes){cdi,bn},&pins,&bpins,&provider,&owner,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);CHECK(!owner&&!memcmp(&receipt,&prior,sizeof(receipt)));
 CHECK(coh_costume_owner_candidate((CohBytes){cdi,cn},(CohBytes){body,bn},&pins,&bpins,&provider,(CohCostumeOwner**)(void*)body,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);
 for(i=0;i<128;i++)lifecycle();
 maximum();CHECK(allocations==frees+3);printf("{\"passed\":true,\"checks\":%u,\"cycles\":128,\"body_rows\":2,\"maximum_body_rows\":29,\"body_witness_bytes\":%zu,\"owned_bytes\":%zu,\"named_peak_bytes\":%zu,\"calloc_calls\":%u,\"free_calls\":%u,\"injected_allocation_failures\":3,\"runtime_admitted\":false,\"application_ack\":false}\n",checks,bn,bytes,peak,allocations,frees);return 0;
}
