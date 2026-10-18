#include "../coh_wr_texwords.c"
#include "texwords_fixture.h"
#include <openssl/sha.h>
#include <stdalign.h>

static unsigned checks,comparisons,record_comparisons,polls,stop_at,hash_error,read_error,lying_hash;
static unsigned allocations,fail_allocation,live_count,loader_retirements,provider_holds,provider_drops,unsafe_queries;
static void *live[4096];static CohAssetLoader *observed_loader;
static void *watched_candidate;static size_t watched_bytes;static int cancel_after_dictionary;
static uint8_t expected_hash[32];
static unsigned cancellation_controls,allocation_controls,authentic_provider_retirements;
static size_t original_workspace,namespace_owned,namespace_reservations,overlap_aggregate;
typedef struct {uint8_t *data;size_t size;} Memory;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"texwords line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
void *__real_calloc(size_t,size_t);void __real_free(void*);
void *__wrap_calloc(size_t n,size_t bytes){allocations++;if(fail_allocation&&allocations==fail_allocation)return NULL;void*p=__real_calloc(n,bytes);if(p){CHECK(live_count<4096);live[live_count++]=p;if(n*bytes==watched_bytes)watched_candidate=p;}return p;}
void __wrap_free(void*p){if(p==watched_candidate)watched_candidate=NULL;for(unsigned i=0;i<live_count;i++)if(live[i]==p){live[i]=live[--live_count];break;}__real_free(p);}
static CohStatus read_at(void *context,uint64_t at,void *out,size_t n){Memory*m=context;if(read_error)return COH_IO;if(at>m->size||n>m->size-at)return COH_IO;memcpy(out,m->data+(size_t)at,n);return COH_OK;}
static CohStatus digest(void *context,CohBytes bytes,uint8_t out[32]){(void)context;if(hash_error)return COH_IO;if(lying_hash)memcpy(out,expected_hash,32);else SHA256(bytes.data,bytes.size,out);return COH_OK;}
static int cancel(void *context){(void)context;polls++;if(observed_loader&&coh_asset_stats(observed_loader).pinned_blobs){CohAssetLoader*before=observed_loader;CHECK(coh_asset_destroy(&observed_loader)==COH_STATE&&observed_loader==before);}if(cancel_after_dictionary&&watched_candidate&&((CohWrTexWords*)watched_candidate)->report.keys)return 1;return stop_at&&polls==stop_at;}
static CohStatus hold(void *context){(void)context;provider_holds++;return COH_OK;}
static void drop(void *context){(void)context;provider_drops++;}
static void put(uint8_t*p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static uint32_t get(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static Memory read_file(const char *path){FILE*f=fopen(path,"rb");CHECK(f&&!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&n<16*1024*1024);rewind(f);Memory m={malloc((size_t)n),(size_t)n};CHECK(m.data&&fread(m.data,1,m.size,f)==m.size&&fclose(f)==0);return m;}
static CohAssetLoader *loader_for(Memory *m){
 CohAssetLimits limits={8*1024*1024,2*1024*1024,2*1024*1024,2*1024*1024,8,2,1};
 CohAssetLoader*l=NULL;CHECK(coh_asset_create(&limits,&l)==COH_OK);
 CHECK(coh_asset_mount_file(l,"data/bin/texWords.bin",(CohAssetSource){read_at,m,m->size,77})==COH_OK);return l;
}
static CohWrTexWordsRequest request_for(Memory *m,const char *locale,unsigned eu,unsigned edit,unsigned production,unsigned verbose){
 CohWrTexWordsRequest q={0};q.asset=(CohAssetId){"data/bin/texWords.bin",77};q.bytes=m->size;
 SHA256(m->data,m->size,q.sha256);memcpy(expected_hash,q.sha256,32);q.digest=digest;
 q.config=(CohWrTexWordsConfig){locale,eu,edit,production,verbose,1,0,0};return q;
}
static CohWrTexWordsLimits limits_for(const Memory *m){return(CohWrTexWordsLimits){4*1024*1024,64*1024*1024,8*1024*1024,m->size+sizeof(*m)+16*1024*1024,4096,65536};}
static CohWrTexWords *create(Memory *m,const char *locale,unsigned eu,unsigned edit,unsigned production,unsigned verbose){
 CohAssetLoader*l=loader_for(m);CohWrTexWordsRequest q=request_for(m,locale,eu,edit,production,verbose);CohWrTexWordsLimits lim=limits_for(m);CohWrTexWords*c=NULL;
 CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&c)==COH_OK&&c);
 CHECK(!coh_asset_stats(l).pinned_blobs&&coh_asset_destroy(&l)==COH_OK&&!l);
 loader_retirements++;return c;
}
static CohWrTexNamespace *namespace_for(const char *key,Memory *body){
 char path[256];int length=snprintf(path,sizeof(path),"texture_library/test/%s.texture",key);CHECK(length>0&&(size_t)length<sizeof(path));
 CohWrTexNamespaceFile f={path,11,0,{read_at,body,body->size,7}};
 CohWrTexNamespaceRoot root={&f,1,7,"/owned/native/provider/data"};CohWrTexNamespaceRequest q={0};
 q.roots=&root;q.root_count=1;q.input_generation=91;q.mode=COH_WR_TEX_NS_I_LIKE_PIGS;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;
 CohWrTexNamespaceLimits lim={0};lim.owned_limit=1024*1024;lim.aggregate_limit=16*1024*1024;lim.external_bytes=body->size+sizeof(*body)+2*1024*1024;
 lim.record_limit=16;lim.node_limit=16;lim.basic_limit=2;lim.body_lease_limit=1;lim.loader=(CohAssetLimits){1024*1024,128*1024,128*1024,128*1024,8,2,1};
 CohWrTexNamespace*ns=NULL;CHECK(coh_wr_tex_namespace_build(&q,&lim,(CohCancel){0},&ns)==COH_OK);
 CohWrTexNamespaceReport report;CHECK(coh_wr_tex_namespace_report(ns,&report)==COH_OK);namespace_owned+=report.owned_bytes;namespace_reservations+=report.aggregate_reserved_bytes;
 CohWrTexNamespaceBasic b;CHECK(coh_wr_tex_namespace_find(ns,key,&b)==COH_OK);return ns;
}
static Memory basic_body(const Memory *grey,const char *key){
 char name[128];int n=snprintf(name,sizeof(name),"texture_library/test/%s.dds",key);CHECK(n>0&&(size_t)n<sizeof(name));
 uint32_t original=get(grey->data);CHECK(original<grey->size);size_t payload=grey->size-original,header=32+(size_t)n+1+3;
 Memory m={calloc(1,header+payload),header+payload};CHECK(m.data);
 put(m.data,(uint32_t)header);put(m.data+4,(uint32_t)payload);put(m.data+8,8);put(m.data+12,8);
 memcpy(m.data+29,"TX2",3);memcpy(m.data+32,name,(size_t)n+1);memcpy(m.data+header-3,"TX2",3);memcpy(m.data+header,grey->data+original,payload);return m;
}
static CohWrTexWordQueryLimits query_limits(CohWrTexWords*c,const CohWrTexNamespace*ns){
 size_t external=c->allocation+16*1024*1024;
 if(ns){CohWrTexNamespaceReport r;CHECK(coh_wr_tex_namespace_report(ns,&r)==COH_OK);external+=r.aggregate_reserved_bytes;}
 return(CohWrTexWordQueryLimits){external+1024*1024,external};
}
static void compare_query(CohWrTexWords*c,const CohWrTexNamespace*ns,const char *name,int search){
 CohWrTexWordQueryLimits lim=query_limits(c,ns);CohWrTexWordSelection out;
 CHECK(coh_wr_texwords_find(c,ns,name,search,&lim,&out)==COH_OK);
 uint32_t queries,original=original_texwords_find(ns,name,search,&queries);comparisons++;
 CHECK(out.matched==(original!=UINT32_MAX)&&out.source_ordinal==original&&out.namespace_queries==queries);
 CHECK(out.source_generation==77&&out.layout_composition_unqualified==1&&out.current_generation_unqualified==1);
}
static void compare_owner(CohWrTexWords*c,const CohWrTexNamespace*ns,const CohWrTexWordsConfig *configuration_input){
 original_texwords_initialize((CohBytes){c->data,c->allocation-(size_t)(c->data-(uint8_t*)c)});
 original_texwords_configure(configuration_input->locale,configuration_input->region_eu,configuration_input->texword_edit,configuration_input->production_mode,configuration_input->verbose);
 char locale[32],secondary[32],search[80];original_texwords_configuration(locale,secondary,search);
 CHECK(!strcmp(locale,c->report.locale)&&!strcmp(secondary,c->report.secondary_locale)&&!strcmp(search,c->report.search_path));
 TexWordsOracleStats stats=original_texwords_stats();size_t measured=original_texwords_workspace();if(measured>original_workspace)original_workspace=measured;
 CHECK(stats.records==c->row_count&&stats.nodes==c->report.nested_structs&&stats.fields==c->report.fields);
 for(uint32_t i=0;i<c->row_count;i++){
  TexWordOracleRecord expected;CohWrTexWordRecord actual;original_texwords_record(i,&expected);
  CHECK(coh_wr_texwords_record(c,i,&actual)==COH_OK);record_comparisons++;
  CHECK(actual.source_name.size==expected.source_name.size&&!memcmp(actual.source_name.data,expected.source_name.data,expected.source_name.size));
  CHECK((size_t)(actual.serialized_record.data-c->data)==expected.offset&&actual.serialized_record.size==expected.bytes);
  const char*stem=c->rows[i].stem;size_t n=strlen(stem);
  if(n<3||n>122||strpbrk(stem,"./\\!#")){unsafe_queries++;continue;}
  char query[128];
  for(unsigned kind=0;kind<3;kind++)for(int search=0;search<2;search++){
   int wrote=snprintf(query,sizeof(query),"%s%s",stem,kind==0?"":kind==1?"#Base":"#French");
   if(wrote<0||(size_t)wrote>=sizeof(query)){unsafe_queries++;continue;}
   compare_query(c,ns,query,search);
  }
 }
 original_texwords_destroy();
}
/* Controlled complete Parse6 records, written from the exact schema adapter.
 * The unchanged original reader must independently admit every positive case. */
static uint8_t builder[2*1024*1024];static size_t used;static uint32_t first_float,emit_layer;
static void emit_word(uint32_t v){CHECK(used+4<=sizeof(builder));put(builder+used,v);used+=4;}
static void emit_string(const char*s){size_t n=strlen(s);CHECK(n<16384&&used+n+6<=sizeof(builder));builder[used++]=(uint8_t)n;builder[used++]=(uint8_t)(n>>8);memcpy(builder+used,s,n);used+=n;while(used&3)builder[used++]=0;}
static void emit_table(const Table *t,const char *root_name,unsigned depth){
 CHECK(depth<20);size_t start=used;emit_word(0);
 for(unsigned i=0;t[i].type||t[i].name[0];i++){
  unsigned kind=t[i].type&255;if(!kind)continue;
  unsigned n=(t[i].type&K_FIXED)?(unsigned)t[i].param:1;
  if(t[i].type&K_ARRAY){
   if(emit_layer&&t==ParseTexWord&&t[i].subtable==ParseTexWordLayer){emit_word(1);emit_table(ParseTexWordLayer,NULL,depth+1);}
   else emit_word(0);
   continue;
  }
  for(unsigned j=0;j<n;j++){
   if(kind==K_STRUCT)emit_table(t[i].subtable,NULL,depth+1);
   else if(kind==K_STRING)emit_string(t==ParseTexWord&&i==1?root_name:"");
   else {if(kind==K_FLOAT&&!first_float)first_float=(uint32_t)used;emit_word(0);}
  }
 }
 put(builder+start,(uint32_t)(used-start-4));
}
static Memory controlled(const char *const *names,unsigned count){
 memset(builder,0,sizeof(builder));used=0;first_float=0;
 memcpy(builder,"CrypticS",8);used=8;emit_word(0x479da30a);emit_string("Parse6");emit_string("Files1");
 size_t file_size=used;emit_word(0);emit_word(count);for(unsigned i=0;i<count;i++){emit_string(names[i]);emit_word(11);}
 put(builder+file_size,(uint32_t)(used-file_size-4));size_t top=used;emit_word(0);emit_word(count);
 for(unsigned i=0;i<count;i++)emit_table(ParseTexWord,names[i],0);
 put(builder+top,(uint32_t)(used-top-4));Memory m={malloc(used),used};CHECK(m.data);memcpy(m.data,builder,used);return m;
}
static void expect_refusal(Memory*m,CohWrTexWordsRequest*q,CohWrTexWordsLimits*lim,CohStatus expected){
 CohAssetLoader*l=loader_for(m);CohWrTexWords*out=NULL;
 CHECK(coh_wr_texwords_create(l,q,lim,(CohCancel){0},&out)==expected&&!out);
 CHECK(!coh_asset_stats(l).pinned_blobs&&coh_asset_destroy(&l)==COH_OK);
}
static void refusal_controls(Memory*m){
 CohWrTexWordsRequest q=request_for(m,"English",0,0,0,0);CohWrTexWordsLimits lim=limits_for(m),bad=lim;
 CohAssetLoader*l=loader_for(m);CohWrTexWords*out=NULL;observed_loader=l;polls=0;
 CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){cancel,NULL},&out)==COH_OK);unsigned positions=polls;
 CHECK(positions>10&&coh_wr_texwords_destroy(&out)==COH_OK);
 for(unsigned i=1;i<=positions;i++){coh_asset_trim(l);polls=0;stop_at=i;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){cancel,NULL},&out)==COH_CANCELLED&&!out&&!coh_asset_stats(l).pinned_blobs);}cancellation_controls=positions;stop_at=0;observed_loader=NULL;
 allocations=0;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_OK);unsigned points=allocations;allocation_controls=points;size_t owned=out->allocation;CHECK(coh_wr_texwords_destroy(&out)==COH_OK);
 watched_bytes=owned;cancel_after_dictionary=1;observed_loader=l;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){cancel,NULL},&out)==COH_CANCELLED&&!out&&!watched_candidate);cancel_after_dictionary=0;watched_bytes=0;observed_loader=NULL;
 for(unsigned i=1;i<=points;i++){allocations=0;fail_allocation=i;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_LIMIT&&!out);}fail_allocation=0;
 CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},(CohWrTexWords**)&q)==COH_INVALID);
 CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},(CohWrTexWords**)(void*)((uint8_t*)&q+1))==COH_INVALID);
 hash_error=1;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_IO&&!out);hash_error=0;
 q.sha256[0]^=1;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_INVALID&&!out);q.sha256[0]^=1;
 bad.owned_limit=owned-1;CHECK(coh_wr_texwords_create(l,&q,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);
 bad=lim;bad.external_bytes=SIZE_MAX;CHECK(coh_wr_texwords_create(l,&q,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);
 bad=lim;bad.aggregate_limit=1;CHECK(coh_wr_texwords_create(l,&q,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);
 bad=lim;bad.node_limit=1;CHECK(coh_wr_texwords_create(l,&q,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);
 bad=lim;bad.record_limit=1;CHECK(coh_wr_texwords_create(l,&q,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);
 q.config.production_mode=1;q.config.texword_edit=1;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_UNSUPPORTED&&!out);
 q.config.production_mode=0;q.config.texword_edit=0;q.config.allow_loading=0;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_UNSUPPORTED&&!out);q.config.allow_loading=1;
 q.config.pending_compositors=1;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_UNSUPPORTED&&!out);q.config.pending_compositors=0;
 q.config.has_override=1;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_UNSUPPORTED&&!out);
 q=request_for(m,"English",0,0,0,0);q.asset.generation=78;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_NOT_FOUND&&!out);q.asset.generation=77;q.bytes--;CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_INVALID&&!out);q.bytes++;
 CHECK(coh_asset_destroy(&l)==COH_OK);
 read_error=1;l=loader_for(m);q=request_for(m,"English",0,0,0,0);CHECK(coh_wr_texwords_create(l,&q,&lim,(CohCancel){0},&out)==COH_IO&&!out&&!coh_asset_stats(l).pinned_blobs);read_error=0;CHECK(coh_asset_destroy(&l)==COH_OK);
 /* Syntax refusals use real digests over controlled complete/truncated bodies.
  * No malformed bytes are supplied to the unsafe original oracle. */
 const char*names[]={"TEXTS/BASE/ONE.TEXWORD","TEXTS/BASE/TWO.TEXWORD"};Memory test=controlled(names,2);
 const unsigned offsets[]={0,8,28,32,36};
 for(unsigned i=0;i<sizeof(offsets)/sizeof(*offsets);i++){
  unsigned at=offsets[i];uint8_t before=test.data[at];test.data[at]^=0xff;
  CohWrTexWordsRequest rq=request_for(&test,"English",0,0,0,0);CohWrTexWordsLimits rl=limits_for(&test);CohAssetLoader*bad_loader=loader_for(&test);CohWrTexWords*none=NULL;
  CHECK(coh_wr_texwords_create(bad_loader,&rq,&rl,(CohCancel){0},&none)!=COH_OK&&!none&&!coh_asset_stats(bad_loader).pinned_blobs);CHECK(coh_asset_destroy(&bad_loader)==COH_OK);test.data[at]=before;
 }
 for(size_t n=1;n<64;n++){Memory short_body={test.data,n};CohWrTexWordsRequest rq=request_for(&short_body,"English",0,0,0,0);CohWrTexWordsLimits rl=limits_for(&short_body);CohAssetLoader*bad_loader=loader_for(&short_body);CohWrTexWords*none=NULL;CHECK(coh_wr_texwords_create(bad_loader,&rq,&rl,(CohCancel){0},&none)!=COH_OK&&!none);CHECK(coh_asset_destroy(&bad_loader)==COH_OK);}
 free(test.data);
 /* Every nested layer/font/filter field is consumed before publication. */
 emit_layer=1;test=controlled(names,2);emit_layer=0;CHECK(first_float>0);
 CohWrTexWords *nested=create(&test,"English",0,0,0,0);CohWrTexWordsConfig cfg={"English",0,0,0,0,1,0,0};
 original_texwords_initialize((CohBytes){nested->data,test.size});original_texwords_configure("English",0,0,0,0);
 TexWordsOracleStats stats=original_texwords_stats();CHECK(stats.nodes==nested->report.nested_structs&&stats.fields==nested->report.fields);original_texwords_destroy();(void)cfg;
 CHECK(coh_wr_texwords_destroy(&nested)==COH_OK);put(test.data+first_float,0x7fc00000);
 CohWrTexWordsRequest finite=request_for(&test,"English",0,0,0,0);CohWrTexWordsLimits finite_limits=limits_for(&test);expect_refusal(&test,&finite,&finite_limits,COH_UNSUPPORTED);free(test.data);
 const char*duplicates[]={"TEXTS/BASE/A/ONE.TEXWORD","TEXTS/BASE/B/ONE.TEXWORD"};test=controlled(duplicates,2);CohWrTexWordsRequest rq=request_for(&test,"English",0,0,0,0);CohWrTexWordsLimits rl=limits_for(&test);expect_refusal(&test,&rq,&rl,COH_UNSUPPORTED);free(test.data);
}
int main(int argc,char**argv){
 CHECK(argc==3);Memory actual=read_file(argv[1]),grey=read_file(argv[2]);
 Memory present=basic_body(&grey,"ONLY#Base"),absent=basic_body(&grey,"white");
 CohWrTexNamespace*ns_present=namespace_for("ONLY#Base",&present),*ns_absent=namespace_for("white",&absent);
 const struct{const char*locale;unsigned eu,edit,production,verbose;} profiles[]={
  {"English",0,0,0,0},{"English",1,0,0,0},{"english",1,0,0,0},{"English",0,1,0,0},
  {"Base",0,0,0,1},{"UK",0,0,0,1},{"French",0,0,0,1},{"English",0,0,1,0},
  {"English",1,0,1,0},{"French",0,0,1,1}};
 size_t actual_owned=0,actual_preparation=0;unsigned actual_nodes=0,actual_fields=0;
 for(unsigned i=0;i<sizeof(profiles)/sizeof(*profiles);i++){
  Memory*provider=malloc(sizeof(*provider));CHECK(provider);provider->data=malloc(actual.size);CHECK(provider->data);provider->size=actual.size;memcpy(provider->data,actual.data,actual.size);
  CohWrTexWords*c=create(provider,profiles[i].locale,profiles[i].eu,profiles[i].edit,profiles[i].production,profiles[i].verbose);
  free(provider->data);free(provider);authentic_provider_retirements++;actual_owned=c->allocation;actual_preparation=c->report.preparation_aggregate_reserved_bytes;actual_nodes=c->report.nested_structs;actual_fields=c->report.fields;
  CohWrTexWordsConfig cfg={profiles[i].locale,profiles[i].eu,profiles[i].edit,profiles[i].production,profiles[i].verbose,1,0,0};compare_owner(c,ns_absent,&cfg);
  CohWrTexWordsReport report;CHECK(coh_wr_texwords_report(c,&report)==COH_OK&&report.records==725&&report.source_files==725);
  CHECK(coh_wr_texwords_report(c,(CohWrTexWordsReport*)c)==COH_INVALID);
  CHECK(coh_wr_texwords_record(c,0,(CohWrTexWordRecord*)c->data)==COH_INVALID);
  CHECK((uintptr_t)c->data%_Alignof(CohWrTexWords*)==0);CohWrTexWords **owned_slot=(CohWrTexWords**)(void*)c->data;*owned_slot=c;CHECK(coh_wr_texwords_destroy(owned_slot)==COH_INVALID&&*owned_slot==c);
  CHECK(coh_wr_texwords_destroy(&c)==COH_OK&&!c);
 }
 /* Both complete owners coexist: charge the known old owner in external.
  * No credit is taken for either source loader until it actually retires. */
 CohWrTexWords*old_owner=create(&actual,"English",0,0,0,0),*new_owner=NULL;CohAssetLoader*replacement_loader=loader_for(&actual);
 CohWrTexWordsRequest replacement_request=request_for(&actual,"English",1,0,0,0);CohWrTexWordsLimits replacement_limits=limits_for(&actual);replacement_limits.external_bytes+=old_owner->allocation;
 CHECK(coh_wr_texwords_create(replacement_loader,&replacement_request,&replacement_limits,(CohCancel){0},&new_owner)==COH_OK);overlap_aggregate=new_owner->report.preparation_aggregate_reserved_bytes;
 CHECK(overlap_aggregate==old_owner->report.preparation_aggregate_reserved_bytes+old_owner->allocation&&old_owner!=new_owner&&old_owner->row_count==new_owner->row_count);
 CHECK(coh_asset_destroy(&replacement_loader)==COH_OK&&!replacement_loader);loader_retirements++;
 CHECK(coh_wr_texwords_destroy(&old_owner)==COH_OK&&!old_owner);CohWrTexWordRecord survivor;CHECK(coh_wr_texwords_record(new_owner,724,&survivor)==COH_OK&&survivor.source_name.size>0);CHECK(coh_wr_texwords_destroy(&new_owner)==COH_OK);
 const char*names[]={"TEXTS/ENGLISH/SAMPLE.TEXWORD","TEXTS/UK/SAMPLE.TEXWORD","TEXTS/BASE/SAMPLE.TEXWORD","TEXTS/BASE/ONLY.TEXWORD","TEXTS/BASE/DUMMYLAYOUT.TEXWORD"};
 Memory test=controlled(names,5);CohWrTexWords*c=create(&test,"English",1,0,0,0);CohWrTexWordsConfig cfg={"English",1,0,0,0,1,0,0};compare_owner(c,ns_absent,&cfg);
 original_texwords_initialize((CohBytes){c->data,test.size});original_texwords_configure("English",1,0,0,0);
 compare_query(c,ns_present,"ONLY",0);compare_query(c,ns_absent,"ONLY",0);compare_query(c,NULL,"ONLY#Base",0);compare_query(c,NULL,"SAMPLE",0);
 CohWrTexWordQueryLimits qlim=query_limits(c,ns_absent);CohWrTexWordSelection out,before;memset(&out,0xa5,sizeof(out));before=out;
 CHECK(coh_wr_texwords_find(c,NULL,"ONLY",0,&qlim,&out)==COH_STATE&&!memcmp(&out,&before,sizeof(out)));
 const char*bad_names[]={"ab","has.dot","!leading","dir/name","dir\\name"};for(unsigned i=0;i<sizeof(bad_names)/sizeof(*bad_names);i++)CHECK(coh_wr_texwords_find(c,ns_absent,bad_names[i],0,&qlim,&out)==COH_UNSUPPORTED&&!memcmp(&out,&before,sizeof(out)));
 CHECK(coh_wr_texwords_find(c,ns_absent,"ONLY",2,&qlim,&out)==COH_INVALID&&!memcmp(&out,&before,sizeof(out)));
 CHECK(coh_wr_texwords_find(c,ns_absent,"ONLY",0,&qlim,(CohWrTexWordSelection*)c)==COH_INVALID);
 CohWrTexWordQueryLimits bad_qlim=qlim;bad_qlim.external_bytes=c->allocation;CHECK(coh_wr_texwords_find(c,ns_absent,"ONLY",0,&bad_qlim,&out)==COH_LIMIT&&!memcmp(&out,&before,sizeof(out)));
 original_texwords_destroy();CHECK(coh_wr_texwords_destroy(&c)==COH_OK);refusal_controls(&test);free(test.data);
 CHECK(coh_wr_tex_namespace_destroy(&ns_present)==COH_OK&&coh_wr_tex_namespace_destroy(&ns_absent)==COH_OK);free(present.data);free(absent.data);free(grey.data);free(actual.data);
 CHECK(provider_holds==provider_drops&&!live_count);
 printf("{\"passed\":true,\"checks\":%u,\"lookup_comparisons\":%u,\"record_comparisons\":%u,\"actual_records\":725,\"actual_profiles\":10,\"actual_owned_bytes\":%zu,\"actual_preparation_aggregate_reserved_bytes\":%zu,\"old_new_overlap_aggregate_reserved_bytes\":%zu,\"two_namespace_owned_bytes\":%zu,\"two_namespace_full_reservations\":%zu,\"original_oracle_requested_workspace_bytes\":%zu,\"static_builder_bytes\":%zu,\"constructor_cancel_positions\":%u,\"constructor_allocation_positions\":%u,\"actual_nested_structs\":%u,\"actual_fields\":%u,\"unsafe_query_rows_refused\":%u,\"source_loaders_actually_retired\":%u,\"authentic_provider_context_and_bytes_actually_freed\":%u,\"tracked_calloc_blocks_live\":%u,\"old_qualifiers_replayed\":false,\"current_generation\":false,\"layout_composition\":false,\"world_authority\":false}\n",checks,comparisons,record_comparisons,actual_owned,actual_preparation,overlap_aggregate,namespace_owned,namespace_reservations,original_workspace,sizeof(builder),cancellation_controls,allocation_controls,actual_nodes,actual_fields,unsafe_queries,loader_retirements,authentic_provider_retirements,live_count);
 return 0;
}
