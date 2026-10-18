#include "../coh_wr_tex_namespace.c"
#include "tex_namespace_fixture.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <zlib.h>
static uint32_t checks,comparisons,holds,drops,reads,fail_read,hashes,fail_hash,fail_allocation,allocations,polls,stop_at,reentries,fail_hold;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"namespace line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_calloc(size_t,size_t);
void*__wrap_calloc(size_t n,size_t size){allocations++;if(fail_allocation&&allocations==fail_allocation)return NULL;return __real_calloc(n,size);}
typedef struct{uint8_t*data;size_t size;}Memory;
typedef struct{const char*path,*filename;size_t bytes;uint8_t sha256[32];}Authentic;
#include "tex-namespace-authentic.h"
#include "tex-namespace-projected-paths.h"
static CohWrTexNamespace*observed;
static const CohWrTexNamespaceBody*observed_body;
static void reentry(void){
 if(!observed)return;
 reentries++;CohWrTexNamespace*before=observed;const CohWrTexNamespaceBody*body=NULL,*copy=observed_body;CohWrTexNamespaceReport report,unchanged;memset(&unchanged,0xa5,sizeof(unchanged));report=unchanged;
 CHECK(coh_wr_tex_namespace_destroy(&observed)==COH_STATE&&observed==before);CHECK(coh_wr_tex_namespace_acquire(observed,0,(CohCancel){0},&body)==COH_STATE&&!body);CHECK(coh_wr_tex_namespace_release(observed,&copy)==COH_STATE&&copy==observed_body);CHECK(coh_wr_tex_namespace_report(observed,&report)==COH_STATE&&!memcmp(&report,&unchanged,sizeof(report)));
 CohWrTexNamespaceBasic basic,old;memset(&old,0xa5,sizeof(old));basic=old;CHECK(coh_wr_tex_namespace_basic(observed,0,&basic)==COH_STATE&&!memcmp(&basic,&old,sizeof(old)));CHECK(coh_wr_tex_namespace_find(observed,"white",&basic)==COH_STATE&&!memcmp(&basic,&old,sizeof(old)));
 if(observed_body){CohBytes bytes={NULL,99},before_bytes=bytes;CHECK(coh_wr_tex_namespace_body(observed_body,&bytes)==COH_STATE&&!memcmp(&bytes,&before_bytes,sizeof(bytes)));}
}
static CohStatus readat(void*v,uint64_t off,void*out,size_t count){Memory*m=v;reentry();reads++;if(fail_read&&reads==fail_read)return COH_IO;if(off>m->size||count>m->size-off)return COH_IO;memcpy(out,m->data+(size_t)off,count);return COH_OK;}
static CohStatus digest(void*v,CohBytes bytes,uint8_t out[32]){(void)v;reentry();hashes++;if(fail_hash&&hashes==fail_hash)return COH_IO;SHA256(bytes.data,bytes.size,out);return COH_OK;}
static CohStatus hold(void*v){(void)v;reentry();if(fail_hold)return COH_IO;holds++;return COH_OK;}
static void drop(void*v){(void)v;reentry();drops++;}
static int poll(void*v){(void)v;reentry();polls++;return stop_at&&polls==stop_at;}
static void put32(uint8_t*p,uint32_t value){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(value>>(i*8));}
static Memory texture(const char*name,uint32_t tag,uint32_t flags,uint8_t alpha,int tx2){size_t n=strlen(name)+1,header=32+n+(tx2?7:0);Memory m={calloc(1,header+5),header+5};CHECK(m.data);put32(m.data,(uint32_t)header);put32(m.data+4,5);put32(m.data+8,tag);put32(m.data+12,tag+1);put32(m.data+16,flags);m.data[28]=alpha;memcpy(m.data+29,tx2?"TX2":"TEX",3);memcpy(m.data+32,name,n);if(tx2)memcpy(m.data+32+n,"cached!",7);memcpy(m.data+header,"codec",5);return m;}
static CohAssetSource source(Memory*m,uint32_t generation){return(CohAssetSource){readat,m,m->size,generation};}
static Memory pig(const NamespaceOracleFile*files,uint32_t count,int packed){
 size_t names=0,payload=0;for(uint32_t i=0;i<count;i++){names+=4+strlen(files[i].path)+1;payload+=(size_t)compressBound((uLong)files[i].body.size);}
 size_t total=16+(size_t)count*48+12+names+12+payload;Memory m={calloc(1,total),total};CHECK(m.data);put32(m.data,0x123);m.data[4]=m.data[6]=2;m.data[8]=16;m.data[10]=48;put32(m.data+12,count);size_t pool_at=16+(size_t)count*48;put32(m.data+pool_at,0x6789);put32(m.data+pool_at+4,count);put32(m.data+pool_at+8,(uint32_t)names);size_t name_at=pool_at+12,data_at=pool_at+12+names+12;put32(m.data+data_at-12,0x9abc);
 for(uint32_t i=0;i<count;i++){
  uint8_t*r=m.data+16+(size_t)i*48;size_t length=strlen(files[i].path)+1;put32(m.data+name_at,(uint32_t)length);memcpy(m.data+name_at+4,files[i].path,length);name_at+=4+length;
  put32(r,0x3456);put32(r+4,i);put32(r+8,(uint32_t)files[i].body.size);put32(r+12,(uint32_t)files[i].timestamp);put32(r+16,(uint32_t)data_at);put32(r+24,UINT32_MAX);
  if(packed){uLongf n=compressBound((uLong)files[i].body.size);CHECK(compress2(m.data+data_at,&n,files[i].body.data,(uLong)files[i].body.size,6)==Z_OK);put32(r+44,(uint32_t)n);data_at+=(size_t)n;}
  else{memcpy(m.data+data_at,files[i].body.data,files[i].body.size);data_at+=files[i].body.size;}
 }
 m.size=data_at;return m;
}
static CohWrTexNamespaceLimits limits(uint32_t records){CohWrTexNamespaceLimits b={96u<<20,192u<<20,1u<<20,{32u<<20,8u<<20,1u<<20,1u<<20,records,records,records},records,records*4+8,records*2,8};return b;}
static void compare_row(const CohWrTexNamespaceBasic*a,const NamespaceOracleBasic*b){
 CHECK(!strcmp(a->basic_key,b->key));CHECK(!strcmp(a->directory,b->directory));CHECK(!strcmp(a->original_name,b->original));CHECK(a->first_owner_row==b->first);CHECK(a->width==b->width&&a->height==b->height);CHECK(a->initial_basic_flags==b->flags);CHECK(a->cached_mips.size==b->mip_bytes&&!memcmp(a->cached_mips.data,b->mips,b->mip_bytes));CHECK(a->file_offset==b->offset&&a->file_bytes==b->bytes);CHECK(a->virtual_location==b->location&&a->timestamp==b->timestamp&&a->file_index==b->file_index);comparisons++;
}
static void compare_owner(CohWrTexNamespace*r,const NamespaceOracleFile*entries,uint32_t count,uint32_t mode,uint32_t quick,const char*const*prefixes,uint32_t prefix_count,uint32_t active,uint32_t stage,const NamespaceOracleBasic*prior,uint32_t prior_count,NamespaceOracleBasic*out,uint32_t*out_count){
 original_namespace(entries,count,mode,quick,prefixes,prefix_count,active,stage,prior,prior_count,out,out_count);CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(r,&report)==COH_OK&&report.basic_rows==*out_count);
 for(uint32_t i=0;i<*out_count;i++){CohWrTexNamespaceBasic view,found;CHECK(coh_wr_tex_namespace_basic(r,i,&view)==COH_OK);compare_row(&view,out+i);CHECK(coh_wr_tex_namespace_find(r,view.basic_key,&found)==COH_OK&&found.row==view.first_owner_row);const CohWrTexNamespaceBody*body=NULL;CHECK(coh_wr_tex_namespace_acquire(r,i,(CohCancel){0},&body)==COH_OK);CohBytes bytes;CHECK(coh_wr_tex_namespace_body(body,&bytes)==COH_OK);uint8_t hash[32];SHA256(bytes.data,bytes.size,hash);CHECK(!memcmp(hash,view.sha256,32));CHECK(coh_wr_tex_namespace_destroy(&r)==COH_STATE&&r);CHECK(coh_wr_tex_namespace_release(r,&body)==COH_OK&&!body);}
}
static Memory load(const char*path){FILE*f=fopen(path,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<1<<20);rewind(f);Memory m={calloc(1,(size_t)n),(size_t)n};CHECK(m.data&&fread(m.data,1,m.size,f)==m.size&&!fclose(f));return m;}
static void authentic_cases(const char*directory){
 const uint32_t count=(uint32_t)(sizeof(authentic)/sizeof(authentic[0]));Memory*memory=calloc(count,sizeof(*memory));CohWrTexNamespaceFile*files=calloc(count,sizeof(*files));NamespaceOracleFile*input=calloc(count,sizeof(*input));NamespaceOracleBasic*output=calloc(count,sizeof(*output));CHECK(memory&&files&&input&&output);
 for(uint32_t i=0;i<count;i++){
  char physical[2048];CHECK(snprintf(physical,sizeof(physical),"%s/%s",directory,authentic[i].filename)>0);memory[i]=load(physical);CHECK(memory[i].size==authentic[i].bytes);uint8_t hash[32];SHA256(memory[i].data,memory[i].size,hash);CHECK(!memcmp(hash,authentic[i].sha256,32));files[i]=(CohWrTexNamespaceFile){authentic[i].path,0,0,source(memory+i,77)};input[i]=(NamespaceOracleFile){authentic[i].path,{memory[i].data,memory[i].size},0,0,-1,0};
 }
 CohWrTexNamespaceRoot root={files,count,77,"/controlled-native-subset-with-authentic-bodies/data"};CohWrTexNamespaceRequest q;memset(&q,0,sizeof(q));q.roots=&root;q.root_count=1;q.mode=2;q.input_generation=77;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;CohWrTexNamespaceLimits b=limits(count+16);CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);uint32_t rows=0;compare_owner(r,input,count,2,0,NULL,0,0,0,NULL,0,output,&rows);CHECK(rows==count);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);
 for(uint32_t i=0;i<count;i++)free(memory[i].data);
 free(memory);free(files);free(input);free(output);
}
static void projected_path_cases(void){
 const uint32_t count=(uint32_t)(sizeof(projected_paths)/sizeof(projected_paths[0]));Memory*memory=calloc(count,sizeof(*memory));CohWrTexNamespaceFile*files=calloc(count,sizeof(*files));NamespaceOracleFile*input=calloc(count,sizeof(*input));NamespaceOracleBasic*output=calloc(count,sizeof(*output));CHECK(memory&&files&&input&&output);
 for(uint32_t i=0;i<count;i++){
  const char*p=projected_paths[i];size_t n=strlen(p);CHECK(n>=8&&n<260);char name[260];memcpy(name,p,n-8);memcpy(name+n-8,".dds",5);memory[i]=texture(name,4,0,0,0);files[i]=(CohWrTexNamespaceFile){p,0,0,source(memory+i,88)};input[i]=(NamespaceOracleFile){p,{memory[i].data,memory[i].size},0,0,-1,0};
 }
 CohWrTexNamespaceRoot root={files,count,88,"/controlled-single-root-path-projection/data"};CohWrTexNamespaceRequest q;memset(&q,0,sizeof(q));q.roots=&root;q.root_count=1;q.mode=2;q.input_generation=88;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;CohWrTexNamespaceLimits b=limits(count+16);b.external_bytes=64u<<20;CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);uint32_t rows=0;compare_owner(r,input,count,2,0,NULL,0,0,0,NULL,0,output,&rows);CHECK(rows==count);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);
 for(uint32_t i=0;i<count;i++)free(memory[i].data);
 free(memory);free(files);free(input);free(output);
}
static void maximum_depth_case(void){
 char path[260]="texture_library/",name[260];for(unsigned i=0;i<115;i++)strcat(path,"a/");strcat(path,"deep.texture");CHECK(strlen(path)==258);strcpy(name,path);strcpy(name+strlen(name)-8,".dds");Memory memory=texture(name,4,0,0,0);CohWrTexNamespaceFile file={path,0,0,source(&memory,91)};CohWrTexNamespaceRoot root={&file,1,91,"/controlled-deep-tree/data"};CohWrTexNamespaceRequest q;memset(&q,0,sizeof(q));q.roots=&root;q.root_count=1;q.mode=2;q.input_generation=91;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;CohWrTexNamespaceLimits b=limits(32);CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);NamespaceOracleFile input={path,{memory.data,memory.size},0,0,-1,0};NamespaceOracleBasic output;uint32_t count;compare_owner(r,&input,1,2,0,NULL,0,0,0,NULL,0,&output,&count);CHECK(count==1);CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(r,&report)==COH_OK&&report.tree_nodes==117);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);free(memory.data);
}
static void refusal_cases(void){
 Memory memory=texture("texture_library/check/good.dds",4,0,0,0);CohWrTexNamespaceFile file={"texture_library/check/good.texture",0,0,source(&memory,93)};CohWrTexNamespaceRoot root={&file,1,93,"/controlled-refusal/data"};CohWrTexNamespaceRequest q;memset(&q,0,sizeof(q));q.roots=&root;q.root_count=1;q.mode=2;q.input_generation=93;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;CohWrTexNamespaceLimits b=limits(32);CohWrTexNamespace*r=NULL;uint8_t saved[32];memcpy(saved,memory.data,32);
 const struct{uint32_t at,value;CohStatus status;}bad[]={{0,1057,COH_INVALID},{4,UINT32_MAX,COH_INVALID},{8,0,COH_INVALID},{20,0x7fc00000,COH_UNSUPPORTED},{28,2,COH_INVALID}};
 for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++){put32(memory.data+bad[i].at,bad[i].value);CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==bad[i].status&&!r&&holds==drops);memcpy(memory.data,saved,32);}
 file.path="texture_library/check/wrong.texture";CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&holds==drops);file.path="../texture_library/check/good.texture";uint32_t before=holds;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_INVALID&&!r&&holds==before);file.path="texture_library/check/good.texture";
 CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);coh_asset_trim(r->loader);memory.data[memory.size-1]^=1;const CohWrTexNamespaceBody*body=NULL;CHECK(coh_wr_tex_namespace_acquire(r,0,(CohCancel){0},&body)==COH_INVALID&&!body&&coh_asset_stats(r->loader).pinned_blobs==0);memory.data[memory.size-1]^=1;CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);free(memory.data);
}
static void prefix_and_underscore_case(void){
 const char*paths[]={"texture_library/ab_lower/one.texture","texture_library/AB_UPPER/two.texture","texture_library/Ab_mixed/three.texture","texture_library/_private/four.texture"};Memory memory[4];CohWrTexNamespaceFile files[4];NamespaceOracleFile input[4];
 for(unsigned i=0;i<4;i++){char name[260];strcpy(name,paths[i]);strcpy(name+strlen(name)-8,".dds");memory[i]=texture(name,4,0,0,0);files[i]=(CohWrTexNamespaceFile){paths[i],0,0,source(memory+i,95)};input[i]=(NamespaceOracleFile){paths[i],{memory[i].data,memory[i].size},0,0,-1,0};}
 const char*prefixes[]={"ab_"};CohWrTexNamespaceRoot root={files,4,95,"/controlled-prefix/data"};CohWrTexNamespaceRequest q;memset(&q,0,sizeof(q));q.roots=&root;q.root_count=1;q.mode=2;q.input_generation=95;q.development_data=1;q.ignore_prefixes=prefixes;q.ignore_prefix_count=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;CohWrTexNamespaceLimits b=limits(32);CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);NamespaceOracleBasic output[4];uint32_t count;compare_owner(r,input,4,2,0,prefixes,1,0,0,NULL,0,output,&count);CHECK(count==1&&!strcmp(output[0].key,"three"));CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);for(unsigned i=0;i<4;i++)free(memory[i].data);
}
static void directory_filter_cases(void){
 Memory memory[]={texture("texture_library/A/foo.dds",4,0,0,0),texture("texture_library/B/bar.dds",5,0,0,0),texture("texture_library/P/baz.dds",6,0,0,0)};
 CohWrTexNamespaceFile files[]={{"texture_library/A/foo.texture",100,0,{0}},{"texture_library/B/bar.texture",100,0,{0}}};for(unsigned i=0;i<2;i++)files[i].bytes=source(memory+i,96);CohWrTexNamespaceRoot root={files,2,96,"/snapshot/data"};NamespaceOracleFile input[]={{files[0].path,{memory[0].data,memory[0].size},100,0,-1,0},{files[1].path,{memory[1].data,memory[1].size},100,0,-1,0},{"texture_library/P/baz.texture",{memory[2].data,memory[2].size},100,-1,0,0}};Memory archive=pig(input+2,1,1);CohAssetSource pig_source=source(&archive,97);
 CohWrTexNamespaceRequest q;memset(&q,0,sizeof(q));q.roots=&root;q.root_count=1;q.piggs=&pig_source;q.pigg_count=1;q.mode=2;q.input_generation=96;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;CohWrTexNamespaceLimits b=limits(32);CohWrTexNamespace*r=NULL;NamespaceOracleBasic output[3];uint32_t count;
 q.disallow_overrides=1;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,input,3,3,0,NULL,0,0,0,NULL,0,output,&count);CHECK(count==1);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);q.disallow_overrides=0;
 root.root_path="/snapshot/OBJECT_LIBRARY";CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,input,3,3,0,NULL,0,0,0,NULL,0,output,&count);CHECK(count==1);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);root.root_path="/snapshot/data";
 q.folder_exclusion=1;q.exclusion_folder="a";CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,input+1,2,2,0,NULL,0,0,0,NULL,0,output,&count);CHECK(count==2);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);
 q.folder_exclusion=2;q.exclusion_folder="other";CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,input,3,3,0,NULL,0,0,0,NULL,0,output,&count);CHECK(count==1);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);
 q.mode=1;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,input,3,1,0,NULL,0,0,0,NULL,0,output,&count);CHECK(count==2);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);
 q.folder_exclusion=1;q.exclusion_folder="texture_library";CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,input,3,1,0,NULL,0,0,0,NULL,0,output,&count);CHECK(count==2);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);for(unsigned i=0;i<3;i++)free(memory[i].data);free(archive.data);
}
int main(int argc,char**argv){
 CHECK(argc==2);
 Memory bodies[10];bodies[0]=texture("texture_library/A/collision.dds",11,0,1,0);bodies[1]=texture("texture_library/A/collision.dds",12,0,0,1);bodies[2]=texture("texture_library/A/collision.dds",13,SOURCE_TEXOPT_FADE,1,0);bodies[3]=texture("texture_library/A/collision.dds",14,SOURCE_TEXOPT_BUMPMAP,0,0);bodies[4]=texture("texture_library/a/inside.jpg",15,1u<<17,0,0);bodies[5]=texture("texture_library/a.dds",16,0,0,0);bodies[6]=texture("texture_library/B/shared.tga",17,0,0,0);bodies[7]=texture("texture_library/Z/SHARED.dds",18,0,1,0);bodies[8]=texture("texture_library/P/onlyCubemap.dds",19,SOURCE_TEXOPT_CUBEMAP,0,0);bodies[9]=texture("texture_library/d_skip/file.dds",20,0,0,0);
 CohWrTexNamespaceFile low[]={
  {"texture_library/A/collision.texture",100,0,{0}}, {"texture_library/a/inside.texture",100,0,{0}}, {"texture_library/a.texture",100,0,{0}}, {"texture_library/Z/shared.texture",100,0,{0}}, {"texture_library/d_skip/file.texture",100,0,{0}}
 };
 const unsigned low_body[]={0,4,5,7,9};for(unsigned i=0;i<5;i++)low[i].bytes=source(bodies+low_body[i],10);
 CohWrTexNamespaceFile high[]={ {"texture_library/A/collision.texture",200,0,{0}}, {"texture_library/B/shared.texture",100,0,{0}}};high[0].bytes=source(bodies+1,11);high[1].bytes=source(bodies+6,11);
 CohWrTexNamespaceRoot roots[]={ {high,2,11,"/snapshot/high/data"}, {low,5,10,"/snapshot/base/data"}};
 NamespaceOracleFile pig0[]={ {"texture_library/A/collision.texture",{bodies[2].data,bodies[2].size},200,-1,0,0}, {"texture_library/P/onlyCubemap.texture",{bodies[8].data,bodies[8].size},100,-1,1,0}, {"texture_library/a/inside.texture",{bodies[4].data,bodies[4].size},3700,-1,2,0}};
 NamespaceOracleFile pig1[]={ {"texture_library/A/collision.texture",{bodies[3].data,bodies[3].size},1,-2,0,0}, {"texture_library/a/inside.texture",{bodies[4].data,bodies[4].size},100,-2,1,0}};
 Memory archives[]={pig(pig0,3,0),pig(pig1,2,1)};CohAssetSource pigs[]={source(archives,20),source(archives+1,21)};
 NamespaceOracleFile entries[12];uint32_t entry_count=0;
 for(unsigned reverse=2;reverse;reverse--){unsigned k=reverse-1;for(unsigned j=0;j<roots[k].count;j++){const CohWrTexNamespaceFile*f=roots[k].files+j;Memory*m=f->bytes.context;entries[entry_count++]=(NamespaceOracleFile){f->path,{m->data,m->size},f->timestamp,(int32_t)(1-k),-1,0};}}
 memcpy(entries+entry_count,pig0,sizeof(pig0));entry_count+=3;memcpy(entries+entry_count,pig1,sizeof(pig1));entry_count+=2;
 const char*prefixes[]={"d_"};CohWrTexNamespaceRequest q;memset(&q,0,sizeof(q));q.roots=roots;q.root_count=2;q.piggs=pigs;q.pigg_count=2;q.input_generation=31;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;q.ignore_prefixes=prefixes;q.ignore_prefix_count=1;
 CohWrTexNamespaceLimits b=limits(32);NamespaceOracleBasic oracle[64];uint32_t oracle_count;
 for(uint32_t mode=0;mode<4;mode++)for(uint32_t quick=0;quick<2;quick++){
  q.mode=mode;q.quickload=quick;CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,entries,entry_count,mode,quick,prefixes,1,0,0,NULL,0,oracle,&oracle_count);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&!r);CHECK(holds==drops);
 }
 /* Exhaustive ordered time/priority matrix, including directional +3600 and
  * signed source-domain endpoints. Every body is opened from the winning
  * declared source by the unchanged original consumer and native loader. */
 const int32_t times[]={0,1,100,3599,3600,3700,7200,INT32_MAX};
 CohWrTexNamespaceFile matrix_files[2]={{"texture_library/A/collision.texture",0,0,{0}},{"texture_library/A/collision.texture",0,0,{0}}};matrix_files[0].bytes=source(bodies,40);matrix_files[1].bytes=source(bodies+1,41);
 CohWrTexNamespaceRoot matrix_roots[2]={{matrix_files+1,1,41,"/snapshot/high"},{matrix_files,1,40,"/snapshot/low"}};
 NamespaceOracleFile matrix_entries[3]={{"texture_library/A/collision.texture",{bodies[0].data,bodies[0].size},0,0,-1,0},{"texture_library/A/collision.texture",{bodies[1].data,bodies[1].size},0,1,-1,0},{"texture_library/A/collision.texture",{bodies[2].data,bodies[2].size},0,-1,0,0}};
 Memory matrix_archive=pig(matrix_entries+2,1,1);CohAssetSource matrix_pig=source(&matrix_archive,42);CohWrTexNamespaceRequest matrix=q;matrix.roots=matrix_roots;matrix.piggs=&matrix_pig;matrix.pigg_count=1;matrix.quickload=0;
 for(unsigned a=0;a<8;a++)for(unsigned c=0;c<8;c++)for(unsigned d=0;d<8;d++)for(uint32_t mode=0;mode<4;mode++){
  matrix_files[0].timestamp=matrix_entries[0].timestamp=times[a];matrix_files[1].timestamp=matrix_entries[1].timestamp=times[c];matrix_entries[2].timestamp=times[d];put32(matrix_archive.data+16+12,(uint32_t)times[d]);matrix.mode=mode;
  CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&matrix,&b,(CohCancel){0},&r)==COH_OK);compare_owner(r,matrix_entries,3,mode,0,prefixes,1,0,0,NULL,0,oracle,&oracle_count);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&!r&&holds==drops);
 }
 free(matrix_archive.data);
 /* A real predecessor produced by this module, not a fabricated raw-row list,
  * supplies later LWC table state. Old rows survive even if newer PIGG bytes
  * would win the folder-cache path; filename-key membership skips that load. */
 q.mode=2;q.quickload=0;q.lwc_active=1;q.lwc_last_completed_stage=1;q.pigg_count=1;
 CohWrTexNamespace*old=NULL,*later=NULL;NamespaceOracleBasic prior[64];uint32_t prior_count=0;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&old)==COH_OK);compare_owner(old,entries,entry_count-2,2,0,prefixes,1,1,1,NULL,0,prior,&prior_count);
 q.predecessor=old;q.pigg_count=2;q.lwc_last_completed_stage=2;q.input_generation=32;uint32_t held_before=holds;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&later)==COH_LIMIT&&!later&&holds==held_before);CohWrTexNamespaceReport old_report;CHECK(coh_wr_tex_namespace_report(old,&old_report)==COH_OK);b.external_bytes=old_report.owned_bytes+b.loader.total_bytes+(1u<<20);observed=old;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){poll,NULL},&later)==COH_OK);observed=NULL;compare_owner(later,entries,entry_count,2,0,prefixes,1,1,2,prior,prior_count,oracle,&oracle_count);CHECK(coh_wr_tex_namespace_destroy(&old)==COH_OK);CohWrTexNamespaceBasic retained;CHECK(coh_wr_tex_namespace_basic(later,0,&retained)==COH_OK);CHECK(coh_wr_tex_namespace_destroy(&later)==COH_OK&&holds==drops);q.predecessor=NULL;q.lwc_active=0;q.lwc_last_completed_stage=0;q.input_generation=31;b.external_bytes=1u<<20;
 q.mode=2;q.quickload=0;CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(r,&report)==COH_OK&&report.duplicates_retained==1);compare_owner(r,entries,entry_count,2,0,prefixes,1,0,0,NULL,0,oracle,&oracle_count);
 CohWrTexNamespaceBasic untouched,view;memset(&untouched,0xa5,sizeof(untouched));view=untouched;CHECK(coh_wr_tex_namespace_find(r,"absent",&view)==COH_NOT_FOUND&&!memcmp(&view,&untouched,sizeof(view)));CHECK(coh_wr_tex_namespace_report(r,(CohWrTexNamespaceReport*)r)==COH_INVALID);CHECK(coh_wr_tex_namespace_basic(r,0,&view)==COH_OK);CHECK(coh_wr_tex_namespace_basic(r,0,(CohWrTexNamespaceBasic*)view.original_name)==COH_INVALID);
 const CohWrTexNamespaceBody*lease=NULL;CHECK(coh_wr_tex_namespace_acquire(r,0,(CohCancel){0},&lease)==COH_OK);CohBytes bytes;CHECK(coh_wr_tex_namespace_body(lease,&bytes)==COH_OK);CHECK(coh_wr_tex_namespace_report(r,(CohWrTexNamespaceReport*)bytes.data)==COH_INVALID);CHECK(coh_wr_tex_namespace_release(r,&lease)==COH_OK);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);
 CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);CHECK(coh_wr_tex_namespace_acquire(r,0,(CohCancel){0},&observed_body)==COH_OK);observed=r;coh_asset_trim(r->loader);const CohWrTexNamespaceBody*another=NULL;CHECK(coh_wr_tex_namespace_acquire(r,1,(CohCancel){poll,NULL},&another)==COH_OK);observed=NULL;CHECK(coh_wr_tex_namespace_release(r,&another)==COH_OK);CHECK(coh_wr_tex_namespace_release(r,&observed_body)==COH_OK);observed=r;CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&!r);observed=NULL;CHECK(reentries>0&&holds==drops);
 fail_hold=1;held_before=holds;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_IO&&!r&&holds==held_before&&holds==drops);fail_hold=0;
 allocations=reads=hashes=polls=0;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){poll,NULL},&r)==COH_OK);uint32_t allocation_points=allocations,read_points=reads,hash_points=hashes,cancel_points=polls;CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);
 for(uint32_t at=1;at<=cancel_points;at++){uint32_t before=holds-drops;polls=0;stop_at=at;CohStatus status=coh_wr_tex_namespace_build(&q,&b,(CohCancel){poll,NULL},&r);CHECK(status==COH_CANCELLED&&!r);CHECK(holds-drops==before);}stop_at=0;
 for(uint32_t at=1;at<=allocation_points;at++){allocations=0;fail_allocation=at;CohStatus status=coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r);CHECK(status==COH_LIMIT&&!r);CHECK(holds==drops);}fail_allocation=0;
 for(uint32_t at=1;at<=read_points;at++){reads=0;fail_read=at;CohStatus status=coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r);CHECK(status==COH_IO&&!r);CHECK(holds==drops);}fail_read=0;
 for(uint32_t at=1;at<=hash_points;at++){hashes=0;fail_hash=at;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_IO&&!r&&holds==drops);}fail_hash=0;
 CohWrTexNamespaceLimits small=b;small.aggregate_limit=1;uint32_t before=holds;CHECK(coh_wr_tex_namespace_build(&q,&small,(CohCancel){0},&r)==COH_LIMIT&&!r&&holds==before);small=b;small.owned_limit=1;CHECK(coh_wr_tex_namespace_build(&q,&small,(CohCancel){0},&r)==COH_LIMIT&&!r&&holds==before);
 q.mode=4;CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r);q.mode=2;
 small=b;small.owned_limit=report.peak_owned_bytes-1;CHECK(coh_wr_tex_namespace_build(&q,&small,(CohCancel){0},&r)==COH_LIMIT&&!r&&holds==drops);small=b;small.aggregate_limit=report.aggregate_reserved_bytes-1;CHECK(coh_wr_tex_namespace_build(&q,&small,(CohCancel){0},&r)==COH_LIMIT&&!r&&holds==drops);
 /* Original PigFileGetFileName uses pool ordinal while PigFileFind asserts
  * name_id==ordinal. The more general shared loader is not authority to relax
  * that CLIENT invariant. Refuse a swapped mapping atomically. */
 put32(archives[0].data+16+4,1);put32(archives[0].data+16+48+4,0);CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_UNSUPPORTED&&!r&&holds==drops);put32(archives[0].data+16+4,0);put32(archives[0].data+16+48+4,1);
 CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},&r)==COH_OK);hashes=0;fail_hash=1;lease=NULL;CHECK(coh_wr_tex_namespace_acquire(r,0,(CohCancel){0},&lease)==COH_IO&&!lease&&coh_asset_stats(r->loader).pinned_blobs==0);fail_hash=0;CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&holds==drops);
 CHECK(coh_wr_tex_namespace_build(&q,&b,(CohCancel){0},(CohWrTexNamespace**)&q)==COH_INVALID);
 authentic_cases(argv[1]);projected_path_cases();maximum_depth_case();refusal_cases();prefix_and_underscore_case();directory_filter_cases();
 for(unsigned i=0;i<10;i++)free(bodies[i].data);
 free(archives[0].data);free(archives[1].data);
 printf("{\"passed\":true,\"checks\":%u,\"original_row_comparisons\":%u,\"authentic_cached_header_bodies\":%zu,\"reference_path_only_projected_rows\":%zu,\"calloc_failure_points\":%u,\"source_read_failure_points\":%u,\"digest_failure_points\":%u,\"cancellation_points\":%u,\"reentry_refusal_callbacks\":%u,\"actual_current_provider\":false}\n",checks,comparisons,sizeof(authentic)/sizeof(authentic[0]),sizeof(projected_paths)/sizeof(projected_paths[0]),allocation_points,read_points,hash_points,cancel_points,reentries);
}
