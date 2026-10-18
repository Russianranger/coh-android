#include "../coh_wr_tex_namespace_lookup.h"
#include "defaults_actual.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
void original_namespace_rows(unsigned,const char*const*);
int original_namespace_lookup(const char*,unsigned,char[128],unsigned*,unsigned*);
typedef struct{uint8_t*data;size_t size;} Memory;
typedef struct{Memory memory[16];CohWrTexNamespaceFile files[16];char paths[16][260];CohWrTexNamespaceRoot root;CohWrTexNamespace*source;unsigned count,held;size_t bytes;} Fixture;
static unsigned checks,comparisons,holds,drops,reads,digests,allocations,frees,live,query_count;
static void*blocks[4096];
static unsigned busy_observation;static Fixture*observed;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"namespace lookup line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_calloc(size_t,size_t);void __real_free(void*);
void*__wrap_calloc(size_t n,size_t m){void*p=__real_calloc(n,m);allocations++;if(p){CHECK(live<4096);blocks[live++]=p;}return p;}
void __wrap_free(void*p){if(p){frees++;for(unsigned i=0;i<live;i++)if(blocks[i]==p){blocks[i]=blocks[--live];break;}}__real_free(p);}
static CohStatus readat(void*v,uint64_t at,void*out,size_t n){Memory*m=v;reads++;if(at>m->size||n>m->size-at)return COH_IO;memcpy(out,m->data+(size_t)at,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes bytes,uint8_t out[32]){(void)v;digests++;if(busy_observation){CohWrTexNamespaceLookup value,before;memset(&value,0xa5,sizeof(value));before=value;CohWrTexNamespaceLookupLimits limits={32*1024*1024,16*1024*1024,1};CHECK(coh_wr_tex_namespace_lookup(observed->source,"white",&limits,&value)==COH_STATE&&!memcmp(&value,&before,sizeof(value)));}SHA256(bytes.data,bytes.size,out);return COH_OK;}
static CohStatus hold(void*v){Fixture*f=v;CHECK(!f->held);f->held=1;holds++;return COH_OK;}
static void drop(void*v){Fixture*f=v;CHECK(f->held);f->held=0;drops++;}
static void add(Fixture*f,const char*path,const uint8_t*body,size_t size){unsigned i=f->count++;CHECK(i<16&&strlen(path)<260);strcpy(f->paths[i],path);f->memory[i]=(Memory){malloc(size),size};CHECK(f->memory[i].data);memcpy(f->memory[i].data,body,size);f->bytes+=size;f->files[i]=(CohWrTexNamespaceFile){f->paths[i],11,0,{readat,f->memory+i,size,7}};}
static void put(uint8_t*p,unsigned n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static void controlled(Fixture*f,const char*dir,const char*key){char name[260],path[260];CHECK(snprintf(name,sizeof(name),"texture_library/%s/%s.dds",dir,key)>0);CHECK(snprintf(path,sizeof(path),"texture_library/%s/%s.texture",dir,key)>0);uint8_t b[400]={0};size_t header=33+strlen(name);CHECK(header+1<sizeof(b));put(b,(unsigned)header);put(b+4,1);put(b+8,8);put(b+12,8);memcpy(b+29,"TX2",3);memcpy(b+32,name,strlen(name)+1);b[header]=91;add(f,path,b,header+1);}
static void build(Fixture*f){f->root=(CohWrTexNamespaceRoot){f->files,f->count,7,"/controlled/complete/finite/native/data"};CohWrTexNamespaceRequest request={0};request.roots=&f->root;request.root_count=1;request.input_generation=33;request.mode=COH_WR_TEX_NS_I_LIKE_PIGS;request.development_data=1;request.digest=digest;request.provider_hold=hold;request.provider_drop=drop;request.provider_context=f;CohWrTexNamespaceLimits limits={0};limits.owned_limit=1024*1024;limits.aggregate_limit=16*1024*1024;limits.external_bytes=f->bytes+sizeof(*f)+16514+256*1024;limits.record_limit=64;limits.node_limit=128;limits.basic_limit=32;limits.body_lease_limit=4;limits.loader=(CohAssetLimits){1024*1024,128*1024,128*1024,128*1024,32,20,16};CHECK(coh_wr_tex_namespace_build(&request,&limits,(CohCancel){0},&f->source)==COH_OK);}
static CohWrTexNamespaceLookupLimits limits_for(Fixture*f,unsigned guarded){CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(f->source,&report)==COH_OK);return(CohWrTexNamespaceLookupLimits){32*1024*1024,report.aggregate_reserved_bytes,guarded};}
static CohWrTexNamespaceLookup query(Fixture*f,const char*name,unsigned guarded){
 CohWrTexNamespaceLookupLimits limits=limits_for(f,guarded);CohWrTexNamespaceLookup result;memset(&result,0xa5,sizeof(result));CohWrTexNamespaceLookup before=result;
 unsigned old_reads=reads,old_digests=digests,old_allocations=allocations,old_frees=frees,old_holds=holds,old_drops=drops;query_count++;
 const char*plain=name&&name[0]=='!'?name+1:name;size_t n=plain?strlen(plain):0;int unsafe=plain&&n>=4&&n<8&&plain[n-4]!='.';
 CohStatus status=coh_wr_tex_namespace_lookup(f->source,name,&limits,&result);
 CHECK(reads==old_reads&&digests==old_digests&&allocations==old_allocations&&frees==old_frees&&holds==old_holds&&drops==old_drops);
 if(!guarded&&unsafe){CHECK(status==COH_UNSUPPORTED&&!memcmp(&result,&before,sizeof(result)));return result;}
 CHECK(status==COH_OK);char key[128];unsigned flags,lookups;int row=original_namespace_lookup(name,guarded,key,&flags,&lookups);comparisons++;
 CHECK(!strcmp(key,result.key)&&flags==result.format_flags&&lookups==(name?1u:0u));
 CHECK(result.branch==(!name?COH_WR_TEX_NS_LOOKUP_NULL:row<0?COH_WR_TEX_NS_LOOKUP_ABSENT:COH_WR_TEX_NS_LOOKUP_FOUND));
 CHECK(result.current_CLIENT_unqualified==1&&result.guarded_short_keys==guarded&&result.source_input_generation==33);
 CHECK(result.aggregate_reserved_bytes==limits.external_bytes+16384+sizeof(limits)+sizeof(result)+(name?strlen(name)+1:0));
 if(row>=0){CohWrTexNamespaceBasic b;CHECK(coh_wr_tex_namespace_basic(f->source,(unsigned)row,&b)==COH_OK);CHECK(result.row==(unsigned)row&&result.first_owner_row==b.first_owner_row&&result.asset_generation==b.asset.generation&&!strcmp(result.asset_path,b.asset.path)&&!memcmp(result.sha256,b.sha256,32));}
 else CHECK(result.row==UINT32_MAX&&result.first_owner_row==UINT32_MAX&&!result.asset_generation&&!result.asset_path[0]);
 return result;
}
static void refuse(Fixture*f,const char*name,CohWrTexNamespaceLookupLimits*limits,CohStatus expected){CohWrTexNamespaceLookup out;memset(&out,0x5a,sizeof(out));CohWrTexNamespaceLookup before=out;CHECK(coh_wr_tex_namespace_lookup(f->source,name,limits,&out)==expected&&!memcmp(&out,&before,sizeof(out)));}
int main(void){
 Fixture f={0};for(unsigned i=0;i<7;i++)add(&f,actual_defaults[i].path,actual_defaults[i].data,actual_defaults[i].size);
 controlled(&f,"aaa","WHITE");controlled(&f,"zzz","white");controlled(&f,"extras","abc");controlled(&f,"extras","PORTAL");controlled(&f,"extras","!white");build(&f);
 CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(f.source,&report)==COH_OK&&report.basic_rows==12);const char*keys[32];for(unsigned i=0;i<report.basic_rows;i++){CohWrTexNamespaceBasic b;CHECK(coh_wr_tex_namespace_basic(f.source,i,&b)==COH_OK);keys[i]=b.basic_key;}original_namespace_rows(report.basic_rows,keys);
 static const char*suffixes[]={"",".dds",".tga",".jpg",".texture",".DDS",".TGA",".JPG",".TEXTURE",".xyz",".abcdefg",".dds.foo"};
 for(unsigned policy=0;policy<2;policy++){
  query(&f,NULL,policy);query(&f,"",policy);query(&f,"!",policy);query(&f,"!!white",policy);query(&f,"texture_library/white.dds",policy);query(&f,"missing",policy);query(&f,"WHITE",policy);
  for(unsigned i=0;i<report.basic_rows;i++)for(unsigned j=0;j<sizeof(suffixes)/sizeof(suffixes[0]);j++){char name[260];CHECK(snprintf(name,sizeof(name),"%s%s",keys[i],suffixes[j])>0);query(&f,name,policy);char bang[260];CHECK(snprintf(bang,sizeof(bang),"!%s",name)>0);query(&f,bang,policy);}
  for(unsigned length=0;length<=127;length++){char name[129];memset(name,'q',length);name[length]=0;query(&f,name,policy);if(length>=4){name[length-4]='.';query(&f,name,policy);}if(length>=8){name[length-4]='q';name[length-8]='.';query(&f,name,policy);}}
 }
 CohWrTexNamespaceLookup saved=query(&f,"white",1);CohWrTexNamespaceLookupLimits limits=limits_for(&f,1),bad=limits;bad.external_bytes--;refuse(&f,"white",&bad,COH_LIMIT);bad=limits;bad.external_bytes=SIZE_MAX;refuse(&f,"white",&bad,COH_LIMIT);bad=limits;bad.aggregate_limit=saved.aggregate_reserved_bytes-1;refuse(&f,"white",&bad,COH_LIMIT);bad=limits;bad.guarded_short_keys=2;refuse(&f,"white",&bad,COH_UNSUPPORTED);
 char long_name[130];memset(long_name,'q',129);long_name[129]=0;refuse(&f,long_name,&limits,COH_LIMIT);char high[]={ 'w',(char)0xff,0};refuse(&f,high,&limits,COH_UNSUPPORTED);char length128[129];memset(length128,'q',128);length128[128]=0;refuse(&f,length128,&limits,COH_LIMIT);length128[0]='!';query(&f,length128,1);
 union{CohWrTexNamespaceLookup out;CohWrTexNamespaceLookupLimits limits;} alias;alias.limits=limits;CHECK(coh_wr_tex_namespace_lookup(f.source,"white",&alias.limits,&alias.out)==COH_INVALID);
 CohWrTexNamespaceBasic first;CHECK(coh_wr_tex_namespace_basic(f.source,0,&first)==COH_OK);CHECK(coh_wr_tex_namespace_lookup(f.source,"white",&limits,(CohWrTexNamespaceLookup*)(void*)first.original_name)==COH_INVALID);
 union{CohWrTexNamespaceLookup out;char name[sizeof(CohWrTexNamespaceLookup)];} query_alias;strcpy(query_alias.name,"white");CHECK(coh_wr_tex_namespace_lookup(f.source,query_alias.name,&limits,&query_alias.out)==COH_INVALID);
 const CohWrTexNamespaceBody*body=NULL;observed=&f;busy_observation=1;CHECK(coh_wr_tex_namespace_acquire(f.source,saved.row,(CohCancel){0},&body)==COH_OK);busy_observation=0;CHECK(coh_wr_tex_namespace_release(f.source,&body)==COH_OK&&!body);
 CHECK(coh_wr_tex_namespace_destroy(&f.source)==COH_OK&&!f.source&&!f.held);for(unsigned i=0;i<f.count;i++){memset(f.memory[i].data,0,f.memory[i].size);free(f.memory[i].data);}CHECK(saved.branch==COH_WR_TEX_NS_LOOKUP_FOUND&&saved.asset_generation==7&&saved.asset_path[0]&&saved.sha256[0]);CHECK(holds==drops&&!live);
 printf("{\"checks\":%u,\"queries\":%u,\"whole_original_comparisons\":%u,\"authentic_source_bodies\":7,\"controlled_rows\":5,\"provider_holds\":%u,\"provider_drops\":%u,\"tracked_calloc_blocks_live\":%u,\"query_callbacks_allocations_and_io\":0,\"source_full_reservation\":%zu,\"lookup_reserved_bytes\":%zu,\"copied_scalar_identity_survives_actual_provider_retirement\":true}\n",checks,query_count,comparisons,holds,drops,live,limits.external_bytes,saved.aggregate_reserved_bytes);
 return 0;
}
