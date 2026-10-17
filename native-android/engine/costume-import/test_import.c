#include "coh_costume_import.h"
#define OPENSSL_API_COMPAT 0x10100000L
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint8_t* testsha(const void*p,size_t n,uint8_t*out){SHA256_CTX c;return SHA256_Init(&c)&&SHA256_Update(&c,p,n)&&SHA256_Final(out,&c)?out:NULL;}
#define SHA256 testsha
static unsigned checks,calls;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"line %d: %s\n",__LINE__,#v);exit(1);}}while(0)
static uint8_t blob[4096],original[4096];static size_t size;
static CohCostumeImportPins pins;static CohCostumeImportReceipt receipt,before;
static CohEntCostumeDictionary *dictionary;
static CohEntCostumeWorkspace workspace;static CohEntCostume costume,prior;
static unsigned fault;
static CohStatus digest(void*c,CohBytes b,uint8_t out[32]){(void)c;calls++;if(fault)return COH_IO;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static CohCostumeImportDigest provider={digest,NULL,0,16384};
static void hash(void){CHECK(SHA256(blob,size,pins.payload_sha256)!=NULL);}
static void byte(unsigned v){blob[size++]=(uint8_t)v;}
static void word(uint32_t v){for(unsigned i=0;i<4;i++)byte(v>>(i*8));}
static void text(const char*s){if(!s){byte(255);byte(255);}else{size_t n=strlen(s);byte((unsigned)n);byte((unsigned)n>>8);memcpy(blob+size,s,n);size+=n;}}
static CohStatus readblob(size_t n,size_t budget,size_t retained){return coh_costume_import((CohBytes){blob,n},&pins,&provider,&dictionary,&receipt,budget,retained);}
static void refused(size_t n,size_t budget,size_t retained){before=receipt;CHECK(dictionary==NULL);CHECK(readblob(n,budget,retained)!=COH_OK);CHECK(!dictionary&&!memcmp(&receipt,&before,sizeof(receipt)));}
static void build(void){
 memset(&pins,0,sizeof(pins));pins.generation=9;pins.body_parts=1;pins.body_types=9;memcpy(pins.source_sha256,coh_costume_import_source_id,32);
 memset(pins.inventory_sha256,1,32);memset(pins.profile_sha256,2,32);memset(pins.run_sha256,3,32);
 memcpy(blob,"COHCDI1\0",8);size=8;word(1);word(9);word(1);word(9);word(8);word(8);word(8);word(2);word(1);word(1);
 memcpy(blob+size,pins.source_sha256,32);size+=32;memcpy(blob+size,pins.inventory_sha256,32);size+=32;memcpy(blob+size,pins.profile_sha256,32);size+=32;memcpy(blob+size,pins.run_sha256,32);size+=32;
 for(unsigned i=0;i<8;i++)text(i==2?"":i==5?"SM_Chest.geo":NULL);
 for(unsigned i=0;i<8;i++)text(i==1?"Chest":NULL);
 for(unsigned i=0;i<8;i++){byte(i==6);word(i==6?0xff030201:0);}hash();memcpy(original,blob,size);
}
typedef struct {uint8_t data[4096];size_t bit;unsigned mode;} Writer;
static void bits(Writer*w,unsigned n,uint32_t v){if(w->mode)n=((n+7)/8)*8;for(unsigned i=0;i<n;i++){w->data[w->bit/8]|=((v>>i)&1)<<(w->bit%8);w->bit++;}}
static void pack(Writer*w,unsigned n,uint32_t v){CHECK(v<((1u<<n)-1));bits(w,w->mode?32:n,v);}
static void string(Writer*w,int index){bits(w,1,0);bits(w,1,index>=0);if(index>=0){bits(w,1,1);pack(w,3,(uint32_t)index);}}
static void wire(unsigned mode,int hole){
 Writer w={{0},0,mode};bits(&w,1,0);bits(&w,1,0);pack(&w,6,0);bits(&w,32,0xff102030);bits(&w,1,0);bits(&w,3,0);bits(&w,1,1);
 for(unsigned i=0;i<72;i++)bits(&w,32,0);
 for(unsigned i=0;i<30;i++)bits(&w,32,0);
 bits(&w,1,0);string(&w,hole?4:5);string(&w,2);string(&w,-1);string(&w,-1);bits(&w,1,0);
 bits(&w,1,0);bits(&w,1,1);pack(&w,3,6);bits(&w,1,0);bits(&w,1,0);bits(&w,32,0);
 bits(&w,1,1);bits(&w,1,1);pack(&w,3,1);bits(&w,1,0);
 CohRepReader r={{w.data,(w.bit+7)/8},w.bit,0,mode,0},old=r;CohEntFailure f;memset(&costume,0xa5,sizeof(costume));prior=costume;
 CohStatus s=coh_ent_costume(&r,dictionary,9,&workspace,&costume,&f);
 if(hole){CHECK(s==COH_NOT_FOUND);CHECK(!memcmp(&r,&old,sizeof(r))&&!memcmp(&costume,&prior,sizeof(costume)));}
 else{CHECK(s==COH_OK);CHECK(r.cursor==w.bit&&costume.part_count==1);CHECK(costume.parts[0].geometry.present&&!strcmp(costume.parts[0].geometry.value,"SM_Chest.geo"));CHECK(costume.parts[0].texture1.present&&!costume.parts[0].texture1.value[0]);CHECK(!costume.parts[0].texture2.present);CHECK(costume.parts[0].colors[0]==0xff030201&&!costume.parts[0].colors[1]);CHECK(!strcmp(costume.parts[0].region.value,"Chest"));}
}
static void putword(uint8_t*p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));}
static void largest(void){
 const size_t n=176+65536u*9;uint8_t*b=calloc(1,n);CHECK(b!=NULL);memcpy(b,original,176);
 for(unsigned i=0;i<3;i++){putword(b+24+i*4,65536);putword(b+36+i*4,0);}
 memset(b+176,255,65536u*4);CohCostumeImportPins pin=pins;CohCostumeImportReceipt r,old;CohEntCostumeDictionary*d=NULL;
 CHECK(SHA256(b,n,pin.payload_sha256)!=NULL);CHECK(coh_costume_import((CohBytes){b,n},&pin,&provider,&d,&r,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_OK);CHECK(r.slots[0]==65536&&r.slots[1]==65536&&r.slots[2]==65536);CHECK(r.dictionary_bytes<=COH_COSTUME_DICTIONARY_BYTES_MAX&&r.charged_peak_bytes<=COH_COSTUME_IMPORT_BUDGET_MAX);CHECK(!r.present[0]&&!r.present[1]&&!r.present[2]);coh_ent_costume_dictionary_free(d);d=NULL;
 old=r;calls=0;CHECK(coh_costume_import((CohBytes){b,n},&pin,&provider,&d,&r,r.charged_peak_bytes-1,0)==COH_LIMIT);CHECK(!calls&&!d&&!memcmp(&r,&old,sizeof(r)));
 /* Last-slot validity mismatch must refuse the entire already traversed input. */
 b[n-5]=1;putword(b+n-4,0xff030201);CHECK(SHA256(b,n,pin.payload_sha256)!=NULL);CHECK(coh_costume_import((CohBytes){b,n},&pin,&provider,&d,&r,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);CHECK(!d&&!memcmp(&r,&old,sizeof(r)));
 free(b);
}
int main(void){
 build();memset(&receipt,0xa5,sizeof(receipt));CHECK(readblob(size,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_OK);CHECK(dictionary&&receipt.generation==9&&receipt.body_types==9&&receipt.body_parts==1);CHECK(receipt.present[0]==2&&receipt.slots[0]==8&&receipt.present[1]==1&&receipt.present[2]==1);CHECK(!receipt.capture_origin_verified&&!receipt.actor_authority);CHECK(receipt.dictionary_bytes==coh_ent_costume_dictionary_bytes(dictionary));size_t peak=receipt.charged_peak_bytes;CHECK(peak<COH_COSTUME_IMPORT_BUDGET_MAX);
 wire(0,0);wire(1,0);wire(0,1);wire(1,1);
 /* The immutable allocation survives complete source bytes destruction. */
 memset(blob,0,size);wire(0,0);coh_ent_costume_dictionary_free(dictionary);dictionary=NULL;memcpy(blob,original,size);hash();
 calls=0;refused(size,peak-1,0);CHECK(!calls);refused(size,COH_COSTUME_IMPORT_BUDGET_MAX,SIZE_MAX);CHECK(!calls);CHECK(readblob(size,peak,0)==COH_OK);coh_ent_costume_dictionary_free(dictionary);dictionary=NULL;
 for(size_t n=0;n<size;n++){CHECK(SHA256(blob,n,pins.payload_sha256)!=NULL);refused(n,COH_COSTUME_IMPORT_BUDGET_MAX,0);}hash();
 for(size_t i=0;i<size;i++){blob[i]^=1;hash();before=receipt;CohStatus s=readblob(size,COH_COSTUME_IMPORT_BUDGET_MAX,0);if(s==COH_OK){CHECK(dictionary!=NULL);coh_ent_costume_dictionary_free(dictionary);dictionary=NULL;}else CHECK(!dictionary&&!memcmp(&receipt,&before,sizeof(receipt)));blob[i]^=1;}hash();
 pins.payload_sha256[0]^=1;refused(size,COH_COSTUME_IMPORT_BUDGET_MAX,0);pins.payload_sha256[0]^=1;
 pins.source_sha256[0]^=1;refused(size,COH_COSTUME_IMPORT_BUDGET_MAX,0);pins.source_sha256[0]^=1;
 pins.body_parts=30;refused(size,COH_COSTUME_IMPORT_BUDGET_MAX,0);pins.body_parts=1;
 pins.generation++;refused(size,COH_COSTUME_IMPORT_BUDGET_MAX,0);pins.generation--;
 fault=1;refused(size,COH_COSTUME_IMPORT_BUDGET_MAX,0);fault=0;
 CohCostumeImportDigest bad=provider;bad.context=blob;bad.context_bytes=size;before=receipt;CHECK(coh_costume_import((CohBytes){blob,size},&pins,&bad,&dictionary,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);CHECK(!memcmp(&receipt,&before,sizeof(receipt)));
 CHECK(coh_costume_import((CohBytes){blob,size},&pins,&provider,(CohEntCostumeDictionary**)(void*)blob,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);
 CHECK(coh_costume_import((CohBytes){(const uint8_t*)(uintptr_t)(UINTPTR_MAX-10),176},&pins,&provider,&dictionary,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);
 CHECK(coh_costume_import((CohBytes){blob,size},(const CohCostumeImportPins*)(const void*)blob,&provider,&dictionary,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);
 CHECK(coh_costume_import((CohBytes){blob,size},&pins,(const CohCostumeImportDigest*)(const void*)blob,&dictionary,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);
 CHECK(coh_costume_import((CohBytes){blob,size},&pins,&provider,&dictionary,(CohCostumeImportReceipt*)(void*)&pins,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);
 bad.context=&receipt;bad.context_bytes=sizeof(receipt);CHECK(coh_costume_import((CohBytes){blob,size},&pins,&bad,&dictionary,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_INVALID);
 dictionary=(CohEntCostumeDictionary*)(uintptr_t)1;before=receipt;CHECK(readblob(size,COH_COSTUME_IMPORT_BUDGET_MAX,0)==COH_STATE);CHECK(dictionary==(CohEntCostumeDictionary*)(uintptr_t)1&&!memcmp(&receipt,&before,sizeof(receipt)));dictionary=NULL;
 largest();
 printf("{\"passed\":true,\"checks\":%u,\"input_bytes\":%zu,\"budget_peak\":%zu,\"dictionary_bytes\":%zu,\"truncations\":%zu,\"byte_mutations\":%zu,\"actor_authority\":false}\n",checks,size,peak,receipt.dictionary_bytes,size,size);return 0;
}
