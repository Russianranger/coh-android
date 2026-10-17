/* Host-only candidate-body/source-observation comparison. No generation permit. */
#include "coh_resource_index.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static CohStatus digest(void *ctx,CohBytes b,uint8_t out[32]){(void)ctx;return SHA256(b.data,b.size,out)?COH_OK:COH_IO;}
static int hex(const char *s,uint8_t out[32]){if(strlen(s)!=64)return 0;for(unsigned i=0;i<32;i++){unsigned a=(unsigned char)s[2*i],b=(unsigned char)s[2*i+1];a=a>='0'&&a<='9'?a-'0':a>='a'&&a<='f'?a-'a'+10:16;b=b>='0'&&b<='9'?b-'0':b>='a'&&b<='f'?b-'a'+10:16;if(a>15||b>15)return 0;out[i]=(uint8_t)(16*a+b);}return 1;}
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static CohStatus read_at(void *context,uint64_t offset,void *dst,size_t count){FILE *file=context;if(offset>0x7fffffffu||fseek(file,(long)offset,SEEK_SET)||fread(dst,1,count,file)!=count)return COH_IO;return COH_OK;}
int main(int argc,char **argv){
 if(argc!=7)return 2;
 uint8_t expected[32],actual[32];CohResourceBinding binding={0};binding.generation=1;binding.asset_generation=(uint32_t)strtoul(argv[6],NULL,10);
 if(!binding.asset_generation||!hex(argv[2],expected)||!hex(argv[3],binding.source_sha256)||!hex(argv[4],binding.run_sha256))return 2;
 FILE*input=fopen(argv[1],"rb");if(!input)return 2;
 if(fseek(input,0,SEEK_END)){fclose(input);return 2;}long size=ftell(input);if(size<=0||(unsigned long)size>COH_RESOURCE_INPUT_MAX){fclose(input);return 2;}rewind(input);
 uint8_t *raw=malloc((size_t)size);CohResourceSource *sources=calloc(COH_RESOURCE_ROWS_MAX,sizeof(*sources)),*selected=calloc(COH_RESOURCE_ROWS_MAX,sizeof(*selected));
 if(!raw||!sources||!selected){fclose(input);free(raw);free(sources);free(selected);return 2;}
 size_t got=fread(raw,1,(size_t)size,input);int closed=fclose(input);if(got!=(size_t)size||closed||digest(NULL,(CohBytes){raw,(size_t)size},actual)!=COH_OK||memcmp(actual,expected,32))return 2;
 size_t at=0,count=0;while(at<(size_t)size){if((size_t)size-at<192||count==COH_RESOURCE_ROWS_MAX)return 2;uint32_t n=u32(raw+at+16);if(n<192||n>(size_t)size-at)return 2;CohResourceView v;sources[count].record=(CohBytes){raw+at,n};if(coh_resource_source_view(sources[count].record,binding.asset_generation,&v)!=COH_OK||digest(NULL,sources[count].record,sources[count].sha256)!=COH_OK)return 2;count++;at+=n;}
 FILE *table=fopen(argv[5],"rb");if(!table)return 2;char line[8192];unsigned ordinal=0;
 while(fgets(line,sizeof(line),table)){
  size_t len=strlen(line);if(!len||line[len-1]!='\n'||ordinal==512)return 2;line[len-1]=0;char *field[5];field[0]=line;unsigned fields=1;for(char*p=line;*p;p++)if(*p=='\t'){if(fields==5)return 2;*p=0;field[fields++]=p+1;}if(fields!=5)return 2;
  size_t n=0;for(size_t k=0;k<count;k++){CohResourceView v;if(coh_resource_source_view(sources[k].record,binding.asset_generation,&v)!=COH_OK)return 2;if(v.model_present&&!strcmp(v.geo_name,field[0]))selected[n++]=sources[k];}
  if(!n)return 2;
  CohResourceGeoPin pin={field[0],{field[1],binding.asset_generation},{0}};if(!hex(field[3],pin.sha256)||!hex(field[4],binding.manifest_sha256))return 2;
  FILE *file=fopen(field[2],"rb");if(!file)return 2;if(fseek(file,0,SEEK_END))return 2;long bytes=ftell(file);if(bytes<=0||bytes>16*1024*1024)return 2;rewind(file);
  CohAssetLoader *loader=NULL;CohResourceIndex *index=NULL;CohResourceReport report={0};CohAssetLimits limits={32u<<20,16u<<20,16u<<20,16u<<20,16,4,4};CohStatus status=coh_asset_create(&limits,&loader);if(status!=COH_OK)return 2;
  status=coh_asset_mount_file(loader,field[1],(CohAssetSource){read_at,file,(uint64_t)bytes,binding.asset_generation});if(status!=COH_OK)return 2;
  CohResourceBudget budget={32u<<20,96u<<20,(size_t)size+2u*COH_RESOURCE_ROWS_MAX*sizeof(*sources)+65536u,32u<<20};CohCancel never={NULL,NULL};
  status=coh_resource_index_build(NULL,loader,selected,n,&pin,1,&binding,&budget,digest,NULL,never,&index,&report);
  char headerhex[65]="";size_t headerbytes=0;
  if(status==COH_OK){CohResourceView v;CohBytes h;uint8_t hd[32];if(coh_resource_source_view(selected[0].record,binding.asset_generation,&v)!=COH_OK||coh_resource_index_header(index,v.owner_kind,v.file,v.slot,&h)!=COH_OK||digest(NULL,h,hd)!=COH_OK)return 2;headerbytes=h.size;for(unsigned k=0;k<32;k++)sprintf(headerhex+2*k,"%02x",hd[k]);}
  printf("{\"ordinal\":%u,\"status\":%d,\"source_rows\":%zu,\"owned_bytes\":%zu,\"aggregate_reserved_bytes\":%zu,\"lookup_work\":%u,\"candidate_body_core_header_model_partition_equal\":%s,\"uncompressed_header_bytes\":%zu,\"uncompressed_header_sha256\":\"%s\",\"source_generation_admitted\":false,\"assets_admitted\":false}\n",ordinal,status,n,report.owned_bytes,report.aggregate_reserved_bytes,report.lookup_work_units,status==COH_OK?"true":"false",headerbytes,headerhex);
  coh_resource_index_free(index);coh_asset_trim(loader);if(coh_asset_destroy(&loader)!=COH_OK||fclose(file))return 2;ordinal++;
 }
 if(ferror(table)||fclose(table))return 2;
 free(selected);free(sources);free(raw);return 0;
}
