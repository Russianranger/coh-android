#define _POSIX_C_SOURCE 200809L
#define OPENSSL_API_COMPAT 0x10100000L
#include "../costume-import/coh_costume_import.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern int diagnostic_export(unsigned,size_t,unsigned char*,size_t*);
extern int diagnostic_sink(const char*);
extern int diagnostic_sink_fault(const char*,unsigned);
static unsigned checks;
#define CHECK(x)do{checks++;if(!(x)){fprintf(stderr,"%d %s\n",__LINE__,#x);exit(1);}}while(0)
static CohStatus digest(void*c,CohBytes bytes,uint8_t out[32]){SHA256_CTX s;(void)c;return SHA256_Init(&s)&&SHA256_Update(&s,bytes.data,bytes.size)&&SHA256_Final(out,&s)?COH_OK:COH_IO;}
int main(int argc,char**argv){
 unsigned char bytes[4096],before[4096];size_t n=0,old;CohCostumeImportPins pins={0};CohCostumeImportReceipt receipt;CohEntCostumeDictionary*d=NULL;CohCostumeImportDigest provider={digest,NULL,0,16384};
 CHECK(argc==2);CHECK(!diagnostic_export(0,sizeof(bytes),bytes,&n));CHECK(n==265);memcpy(before,bytes,n);
 pins.generation=9;pins.body_parts=1;pins.body_types=9;memcpy(pins.source_sha256,coh_costume_import_source_id,32);memset(pins.inventory_sha256,1,32);memset(pins.profile_sha256,2,32);memset(pins.run_sha256,3,32);CHECK(digest(NULL,(CohBytes){bytes,n},pins.payload_sha256)==COH_OK);
 CHECK(coh_costume_import((CohBytes){bytes,n},&pins,&provider,&d,&receipt,COH_COSTUME_IMPORT_BUDGET_MAX,sizeof(bytes)-n)==COH_OK);CHECK(receipt.slots[0]==8&&receipt.slots[1]==8&&receipt.slots[2]==8);CHECK(receipt.present[0]==2&&receipt.present[1]==1&&receipt.present[2]==1);CHECK(!receipt.capture_origin_verified&&!receipt.actor_authority);coh_ent_costume_dictionary_free(d);
 for(size_t cap=0;cap<n;cap++){old=0x13579;CHECK(diagnostic_export(0,cap,bytes,&old)!=0);CHECK(old==0x13579);}
 for(unsigned scenario=1;scenario<=4;scenario++){old=0x2468;CHECK(diagnostic_export(scenario,sizeof(bytes),bytes,&old)!=0);CHECK(old==0x2468);}
 old=0;CHECK(!diagnostic_export(0,sizeof(bytes),bytes,&old)&&old==n&&!memcmp(before,bytes,n));
 char path[512];CHECK(snprintf(path,sizeof(path),"%s/dictionary.cohcdi",argv[1])>0);CHECK(!diagnostic_sink(path));FILE*f=fopen(path,"rb");CHECK(f!=NULL);CHECK(fread(bytes,1,sizeof(bytes),f)==n);CHECK(!memcmp(before,bytes,n));CHECK(!fclose(f));CHECK(diagnostic_sink(path)!=0);f=fopen(path,"rb");CHECK(f!=NULL);CHECK(fread(bytes,1,sizeof(bytes),f)==n&&!memcmp(before,bytes,n));CHECK(!fclose(f));CHECK(!unlink(path));CHECK(diagnostic_sink_fault(path,1)==1);CHECK(access(path,F_OK)!=0);CHECK(diagnostic_sink_fault(path,3)==3);CHECK(access(path,F_OK)==0);CHECK(!unlink(path));CHECK(diagnostic_sink("relative-file.cohcdi")!=0);CHECK(diagnostic_sink("/tmp/../unsafe.cohcdi")!=0);
 printf("{\"passed\":true,\"checks\":%u,\"capacity_refusals\":%zu,\"export_bytes\":%zu,\"original_builder_executed\":false,\"actor_authority\":false}\n",checks,n,n);return 0;
}
