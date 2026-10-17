#include "coh_public_bounds.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static size_t alive,fault_at,fault_seen;
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);void __real_free(void*);
void*__wrap_malloc(size_t n){if(fault_at&&++fault_seen==fault_at)return NULL;void*p=__real_malloc(n);if(p)alive++;return p;}
void*__wrap_calloc(size_t n,size_t z){if(fault_at&&++fault_seen==fault_at)return NULL;void*p=__real_calloc(n,z);if(p)alive++;return p;}
void __wrap_free(void*p){if(p){if(!alive)abort();alive--;}__real_free(p);}
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"publicbounds line%d %s\n",__LINE__,#x);abort();}}while(0)
static CohBytes load(const char*name){FILE*f=fopen(name,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0);rewind(f);unsigned char*p=malloc((size_t)n);CHECK(p&&fread(p,1,(size_t)n,f)==(size_t)n);CHECK(!fclose(f));return(CohBytes){p,(size_t)n};}
static uint32_t read32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohStatus digest(void*c,CohBytes b,uint8_t out[32]){(void)c;return SHA256(b.data,b.size,out)?COH_OK:COH_INVALID;}
int main(int argc,char**argv){CHECK(argc==4);unsigned mismatch=(unsigned)atoi(argv[3]);CohBytes catalog=load(argv[1]),raw=load(argv[2]);
 CohCatalogBinding cb={0};cb.owner_generation=1;cb.catalog_generation=20261016u;cb.asset_generation=20261016u;memset(cb.source_sha256,0x11,32);memset(cb.inventory_sha256,0x22,32);CHECK(digest(NULL,catalog,cb.catalog_sha256)==COH_OK);
 CohCatalogOwner*owner=NULL;CohCatalogDigest d={NULL,digest};CohCatalogOwnerBudget ob={COH_SG_MEMORY_MAX,COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,131072};CohCatalogOwnerReport cr;CHECK(coh_catalog_owner_create(NULL,catalog,&cb,&ob,&d,&owner,&cr)==COH_OK);
 CohPublicBoundsBinding b={0};b.generation=1;b.catalog=cb;memset(b.run_sha256,0x44,32);CHECK(digest(NULL,raw,b.raw_sha256)==COH_OK);CohPublicBoundsBudget budget={COH_SG_MEMORY_MAX,COH_SG_TRANSACTION_MAX,131072};CohPublicBounds*out=NULL;CohPublicBoundsReport report,guard;memset(&report,0xa5,sizeof(report));guard=report;
 CHECK(coh_public_bounds_create(NULL,owner,raw,&b,&budget,&d,&out,&report)==COH_OK);CHECK(out&&report.public_rows&&!report.original_win32_layout_verified&&!report.source_generation_admitted&&!report.cache_equivalence_verified&&!report.world_authority);
 CohPublicBoundsRow row;unsigned seen=0,preserved=0;
 for(uint32_t f=0;f<report.files;f++){CohCatalogFileView file;CHECK(coh_catalog_owner_file(owner,f,&file)==COH_OK);for(uint32_t s=0;s<file.slots;s++){CHECK(coh_public_bounds_row(out,f,s,&row)==COH_OK);if(row.is_public){CHECK(row.raw.size==60&&(row.raw.data[59]&0x80));seen++;preserved++;}else CHECK(!row.raw.size&&!row.raw.data);}}
 CHECK(seen==report.public_rows&&preserved==seen);
 CHECK(coh_public_bounds_row(out,1,0,&row)==COH_OK);
 if(row.raw.size)CHECK(coh_public_bounds_row(out,1,0,(CohPublicBoundsRow*)(uintptr_t)row.raw.data)==COH_INVALID);
 CohPublicBoundsToken token;memset(&token,0xa5,sizeof(token));CohPublicBoundsToken prior=token;CHECK(coh_public_bounds_compare_token(out,0,&token)==COH_UNSUPPORTED&&!memcmp(&token,&prior,sizeof(token)));
 CHECK(coh_public_bounds_compare_token(out,1,&token)==(mismatch?COH_STATE:COH_OK));if(mismatch)CHECK(!memcmp(&token,&prior,sizeof(token)));
 size_t baseline=alive;CohPublicBounds*next=NULL;CohPublicBoundsReport failed;
 for(size_t n=0;n<raw.size;n++){failed=guard;CohBytes short_input={raw.data,n};CHECK(coh_public_bounds_create(NULL,owner,short_input,&b,&budget,&d,&next,&failed)!=COH_OK&&!next&&!memcmp(&failed,&guard,sizeof(failed))&&alive==baseline);}
 CohPublicBoundsBinding wrong=b;wrong.catalog.owner_generation++;failed=guard;CHECK(coh_public_bounds_create(NULL,owner,raw,&wrong,&budget,&d,&next,&failed)==COH_STATE&&!next&&!memcmp(&failed,&guard,sizeof(failed)));
 wrong=b;wrong.catalog.source_sha256[0]^=1;CHECK(coh_public_bounds_create(NULL,owner,raw,&wrong,&budget,&d,&next,&failed)==COH_STATE&&!next&&alive==baseline);
 wrong=b;wrong.raw_sha256[0]^=1;CHECK(coh_public_bounds_create(NULL,owner,raw,&wrong,&budget,&d,&next,&failed)==COH_STATE&&!next&&alive==baseline);
 CohPublicBoundsBudget tiny=budget;tiny.aggregate_limit=report.aggregate_reserved_bytes-1;CHECK(coh_public_bounds_create(NULL,owner,raw,&b,&tiny,&d,&next,&failed)==COH_LIMIT&&!next&&alive==baseline);
 CHECK(coh_public_bounds_create(NULL,owner,raw,&b,&budget,&d,(CohPublicBounds**)&failed,&failed)==COH_INVALID);
 for(size_t fault=1;fault<=4;fault++){fault_at=fault;fault_seen=0;CHECK(coh_public_bounds_create(NULL,owner,raw,&b,&budget,&d,&next,&failed)==COH_LIMIT&&!next&&!memcmp(&failed,&guard,sizeof(failed))&&alive==baseline);fault_at=0;}
 /* Rehash malformed copied bytes: digest success cannot bless wrong decisions. */
 unsigned char*copy=malloc(raw.size);CHECK(copy);memcpy(copy,raw.data,raw.size);copy[raw.size-1]^=0x80;CohBytes altered={copy,raw.size};wrong=b;CHECK(digest(NULL,altered,wrong.raw_sha256)==COH_OK);CHECK(coh_public_bounds_create(NULL,owner,altered,&wrong,&budget,&d,&next,&failed)==COH_OK); /* opaque raw bits preserved, never canonicalized */
 CHECK(coh_public_bounds_compare_token(next,2,&token)==COH_STATE);coh_public_bounds_release(next);next=NULL;copy[24]=2;CHECK(digest(NULL,altered,wrong.raw_sha256)==COH_OK);failed=guard;CHECK(coh_public_bounds_create(NULL,owner,altered,&wrong,&budget,&d,&next,&failed)==COH_STATE&&!next&&!memcmp(&failed,&guard,sizeof(failed)));
 /* Rehashed malformed file/slot/decision fields still refuse atomically. */
 memcpy(copy,raw.data,raw.size);
 size_t first_slot=120u+read32(raw.data+112);size_t mutations[]={0,8,12,20,24,28,32,80,84,88,92,96,100,104,108,112,116,first_slot,first_slot+4,first_slot+8,first_slot+12,first_slot+16,first_slot+20,first_slot+24,first_slot+28};
 for(size_t i=0;i<sizeof(mutations)/sizeof(mutations[0]);i++){size_t at=mutations[i];CHECK(at<raw.size);copy[at]^=1;wrong=b;CHECK(digest(NULL,altered,wrong.raw_sha256)==COH_OK);failed=guard;size_t live_before=alive;CHECK(coh_public_bounds_create(NULL,owner,altered,&wrong,&budget,&d,&next,&failed)!=COH_OK&&!next&&!memcmp(&failed,&guard,sizeof(failed))&&alive==live_before);copy[at]^=1;}
 free(copy);wrong=b;wrong.generation=2;CHECK(coh_public_bounds_create(out,owner,raw,&wrong,&budget,&d,&next,&failed)==COH_OK);coh_public_bounds_release(next);next=NULL;
 CHECK(coh_public_bounds_retain(out)==COH_OK);coh_catalog_owner_release(owner);owner=NULL;coh_public_bounds_release(out);CHECK(coh_public_bounds_row(out,1,0,&row)==COH_OK);coh_public_bounds_release(out);
 free((void*)raw.data);free((void*)catalog.data);CHECK(!alive);printf("{\"passed\":true,\"checks\":%u,\"source_generation_admitted\":false,\"cache_equivalence_verified\":false,\"actual_win32_layout\":false}\n",checks);return 0;}
