#include "runtime_snapshot.h"
#include "runtime_graph.h"
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
static CohRuntimeGraphReport graph_qualified;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"snapshot check failed %s:%d: %s\n",__FILE__,__LINE__,#x);abort();}}while(0)
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);void __real_free(void*);
static size_t live,calls,fail_at,live_bytes,peak_bytes;
static struct {void*p;size_t bytes;} allocations[256];
static void track(void*p,size_t n){if(!p)return;for(unsigned i=0;i<256;i++)if(!allocations[i].p){allocations[i].p=p;allocations[i].bytes=n;live++;live_bytes+=n;if(live_bytes>peak_bytes)peak_bytes=live_bytes;return;}abort();}
void*__wrap_malloc(size_t n){calls++;if(calls==fail_at)return NULL;void*p=__real_malloc(n);track(p,n);return p;}
void*__wrap_calloc(size_t n,size_t z){calls++;if(calls==fail_at)return NULL;void*p=__real_calloc(n,z);track(p,n*z);return p;}
void __wrap_free(void*p){if(p){unsigned i;for(i=0;i<256&&allocations[i].p!=p;i++){}if(i==256||!live)abort();live--;live_bytes-=allocations[i].bytes;allocations[i].p=NULL;}__real_free(p);}
static CohStatus digest(void*context,CohBytes bytes,uint8_t out[32]){(void)context;return SHA256(bytes.data,bytes.size,out)?COH_OK:COH_IO;}
static void put(uint8_t*p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(i*8));}
static uint32_t get(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void json_string(const char*s){putchar('"');for(;*s;s++){unsigned c=(unsigned char)*s;if(c=='"'||c=='\\')putchar('\\');putchar((int)c);}putchar('"');}
static int unhex(const char*s,uint8_t*out){if(strlen(s)!=64)return 0;for(unsigned i=0;i<32;i++){unsigned a=(unsigned char)s[i*2],b=(unsigned char)s[i*2+1];a=a>='0'&&a<='9'?a-'0':a>='a'&&a<='f'?a-'a'+10:16;b=b>='0'&&b<='9'?b-'0':b>='a'&&b<='f'?b-'a'+10:16;if(a>15||b>15)return 0;out[i]=(uint8_t)(a*16+b);}return 1;}
static CohBytes read_file(const char*path,size_t limit){FILE*f=fopen(path,"rb");CHECK(f);CHECK(!fseek(f,0,SEEK_END));long n=ftell(f);CHECK(n>0&&(size_t)n<=limit);rewind(f);uint8_t*p=malloc((size_t)n);CHECK(p);CHECK(fread(p,1,(size_t)n,f)==(size_t)n);CHECK(!fclose(f));return(CohBytes){p,(size_t)n};}
static void rejected(CohBytes catalog,CohBytes snapshot,const CohRuntimeSnapshotPins*pins,const CohRuntimeSnapshotBudget*budget,const CohCancel*cancel,CohStatus expected){
    CohRuntimeSnapshotReport out,before;memset(&out,0xa5,sizeof(out));before=out;size_t allocations_before=live;
    CohStatus status=coh_runtime_snapshot_audit(catalog,snapshot,pins,budget,cancel,&out);
    CHECK(status!=COH_OK);if(expected!=COH_OK)CHECK(status==expected);CHECK(!memcmp(&out,&before,sizeof(out)));CHECK(live==allocations_before);
}
typedef struct {unsigned calls,stop;} Stop;
static int cancelled(void*context){Stop*s=context;return ++s->calls==s->stop;}
static void test(CohBytes catalog,CohBytes snapshot,const CohRuntimeSnapshotPins*original,const CohRuntimeSnapshotBudget*budget,const CohRuntimeSnapshotReport*report){
    CohRuntimeSnapshotPins pins=*original;size_t initial=live;
    CHECK(report->definitions_crc_verified&&report->references_crc_verified&&report->complete_source_name_closure);
    CHECK(report->root_matrices_verified==report->active_roots);
    CHECK(!report->graph_published&&!report->assets_admitted&&!report->groups_received&&!report->actor_admitted&&!report->world_authority);
    CHECK(report->aggregate_peak_bytes<=budget->aggregate_limit);
    CHECK(report->aggregate_peak_bytes==catalog.size+snapshot.size+sizeof(*report)+budget->retained_bytes+report->stack_reserve+report->owned_bytes+report->peak_record_bytes);
    CohRuntimeSnapshotBudget tight={report->aggregate_peak_bytes-1,budget->retained_bytes};rejected(catalog,snapshot,&pins,&tight,NULL,COH_LIMIT);
    tight.aggregate_limit++;CohRuntimeSnapshotReport repeat;CHECK(coh_runtime_snapshot_audit(catalog,snapshot,&pins,&tight,NULL,&repeat)==COH_OK);CHECK(!memcmp(&repeat,report,sizeof(repeat)));
    tight.retained_bytes++;rejected(catalog,snapshot,&pins,&tight,NULL,COH_LIMIT);
    pins.catalog_sha256[0]^=1;rejected(catalog,snapshot,&pins,budget,NULL,COH_STATE);pins=*original;
    pins.snapshot_sha256[0]^=1;rejected(catalog,snapshot,&pins,budget,NULL,COH_STATE);pins=*original;
    memset(pins.run_sha256,0,32);rejected(catalog,snapshot,&pins,budget,NULL,COH_INVALID);pins=*original;
    pins.asset_generation++;rejected(catalog,snapshot,&pins,budget,NULL,COH_STATE);pins=*original;
    for(size_t n=0;n<snapshot.size;n++){CohBytes cut={snapshot.data,n};CHECK(digest(NULL,cut,pins.snapshot_sha256)==COH_OK);rejected(catalog,cut,&pins,budget,NULL,COH_OK);}pins=*original;
    uint8_t*copy=malloc(snapshot.size+1);CHECK(copy);CohBytes changed={copy,snapshot.size};
    const unsigned header_offsets[]={0,8,12,16,20,24,28,32,36,40,44,48,52,56,60,64,79};
    for(unsigned i=0;i<sizeof(header_offsets)/sizeof(*header_offsets);i++){memcpy(copy,snapshot.data,snapshot.size);copy[header_offsets[i]]^=0x80;CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_OK);}
    memcpy(copy,snapshot.data,snapshot.size);copy[snapshot.size]=0;changed.size++;put(copy+16,(uint32_t)changed.size);CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_INVALID);changed.size--;
    size_t at=80;uint32_t roots=get(snapshot.data+44);
    for(uint32_t i=0;i<roots;i++){
        const uint8_t*p=snapshot.data+at;uint32_t present=get(p+4),name=get(p+20),bytes=get(p+28);
        memcpy(copy,snapshot.data,snapshot.size);put(copy+at,i+1);CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_INVALID);
        if(present){
            const unsigned offsets[]={8,12,16,20,24,28};for(unsigned j=0;j<sizeof(offsets)/sizeof(*offsets);j++){memcpy(copy,snapshot.data,snapshot.size);copy[at+offsets[j]]^=0x80;CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_OK);}
            memcpy(copy,snapshot.data,snapshot.size);put(copy+at+32+name+36,0x7fc00000u);CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_INVALID);
            memcpy(copy,snapshot.data,snapshot.size);put(copy+at+32+name+36,0x7149f2cau);CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_INVALID);
            at+=32+name+48+bytes;
        }else{memcpy(copy,snapshot.data,snapshot.size);put(copy+at+8,1);CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_INVALID);at+=32;}
    }
    uint32_t ext=get(snapshot.data+52);
    for(uint32_t i=0;i<ext;i++){
        uint32_t name=get(snapshot.data+at+16),bytes=get(snapshot.data+at+24),path=get(snapshot.data+at+32);
        const unsigned offsets[]={0,4,8,12,16,20,24,28,32};for(unsigned j=0;j<sizeof(offsets)/sizeof(*offsets);j++){memcpy(copy,snapshot.data,snapshot.size);copy[at+offsets[j]]^=0x80;CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_OK);}
        memcpy(copy,snapshot.data,snapshot.size);put(copy+at+36,0x7fc00000u);CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_INVALID);
        memcpy(copy,snapshot.data,snapshot.size);put(copy+at+36+56,1u<<26);CHECK(digest(NULL,changed,pins.snapshot_sha256)==COH_OK);rejected(catalog,changed,&pins,budget,NULL,COH_UNSUPPORTED);
        at+=36+120+name+path+bytes;
    }
    CHECK(at==snapshot.size);free(copy);pins=*original;
    Stop stop={0,0};CohCancel cancel={cancelled,&stop};CHECK(coh_runtime_snapshot_audit(catalog,snapshot,&pins,budget,&cancel,&repeat)==COH_OK);
    unsigned polls=stop.calls;for(unsigned i=1;i<=polls;i++){stop=(Stop){0,i};rejected(catalog,snapshot,&pins,budget,&cancel,COH_CANCELLED);}
    size_t before=calls;CHECK(coh_runtime_snapshot_audit(catalog,snapshot,&pins,budget,NULL,&repeat)==COH_OK);size_t count=calls-before;
    for(size_t i=1;i<=count;i++){fail_at=calls+i;rejected(catalog,snapshot,&pins,budget,NULL,COH_LIMIT);fail_at=0;}
    CHECK(live==initial);
}
static void graph_test(CohBytes catalog,CohBytes snapshot,const CohRuntimeSnapshotPins*pins,const CohRuntimeSnapshotBudget*budget,int exhaustive){
    size_t initial=live;CohRuntimeGraphBinding binding={1,1,*pins};
    CohRuntimeGraph*g=NULL,*next=NULL,*retired=NULL;CohRuntimeGraphReport report;
    size_t before=calls;CHECK(coh_runtime_graph_build(NULL,catalog,snapshot,&binding,budget,NULL,&g,&report)==COH_OK);size_t allocations_count=calls-before;graph_qualified=report;
    CHECK(report.source.complete_source_name_closure&&report.nodes==report.source.definitions+report.source.external_count);
    CHECK(!report.source.world_authority&&!report.source.assets_admitted&&!report.source.groups_received);
    CHECK(report.aggregate_peak_bytes<=budget->aggregate_limit);
    uint32_t reachable=0,externals=0,edges=0;
    for(uint32_t i=0;i<report.nodes;i++){
        CohRuntimeGraphNode node;CHECK(coh_runtime_graph_node(g,i,&node)==COH_OK);CHECK(node.wire.size&&node.wire_bits);
        if(node.in_use){uint32_t found;CHECK(coh_runtime_graph_name(g,node.name,&found)==COH_OK&&found==i);}
        if(node.external){externals++;CHECK(node.file==UINT32_MAX);CHECK(node.empty_owned_future==(!node.source_model_present&&!node.child_count));}
        else{uint32_t found;CHECK(coh_runtime_graph_slot(g,node.file,node.slot,&found)==COH_OK&&found==i);}
        if(exhaustive){
            CohRepReader reader;CohSgDefinition decoded={0};size_t owned;
            CHECK(coh_rep_reader_bounded(&reader,node.wire,node.wire_bits,(int)node.aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
            CHECK(coh_scenegraph_definition_read(&decoded,&reader,node.external?0:node.file,COH_SG_MEMORY_MAX,&owned)==COH_OK);
            CHECK(reader.cursor==node.wire_bits&&decoded.child_count==node.child_count);
            for(uint32_t j=0;j<node.child_count;j++){CohRuntimeGraphChild child;CHECK(coh_runtime_graph_child(g,node.child_first+j,&child)==COH_OK);CHECK(!memcmp(child.matrix,decoded.children[j].matrix,sizeof(child.matrix)));}
            coh_scenegraph_definition_dispose(&decoded);
        }
        if(node.reachable)reachable++;
        for(uint32_t j=0;j<node.child_count;j++){CohRuntimeGraphChild child;CHECK(coh_runtime_graph_child(g,node.child_first+j,&child)==COH_OK&&child.target<report.nodes);edges++;}
    }
    CHECK(reachable==report.source.reachable_definitions+report.source.reachable_external&&externals==report.source.external_count&&edges==report.edges);
    for(uint32_t i=0;i<report.source.root_slots;i++){CohRuntimeGraphRoot root;CHECK(coh_runtime_graph_root(g,i,&root)==COH_OK);if(root.active){CohRuntimeGraphNode node;CHECK(coh_runtime_graph_node(g,root.node,&node)==COH_OK&&node.reachable);}}
    size_t root_at=80;
    for(uint32_t i=0;i<report.source.root_slots;i++){
        const uint8_t*raw=snapshot.data+root_at;uint32_t present=get(raw+4),name=get(raw+20),bytes=get(raw+28);CohRuntimeGraphRoot root;
        CHECK(coh_runtime_graph_root(g,i,&root)==COH_OK&&root.active==present);
        if(present){for(unsigned c=0;c<4;c++)for(unsigned r=0;r<3;r++){uint32_t expected=get(raw+32+name+(c*3+r)*4),actual;memcpy(&actual,&root.matrix[c][r],4);CHECK(actual==expected);}root_at+=32+name+48+bytes;}else root_at+=32;
    }
    uint32_t found=123;CHECK(coh_runtime_graph_name(g,"__not_present__",&found)==COH_NOT_FOUND&&found==123);
    CohRuntimeGraph*current=NULL;CHECK(coh_runtime_graph_publish(&current,&g,&retired)==COH_OK&&!g&&!retired);
    binding.generation=2;CohRuntimeSnapshotBudget tight={report.aggregate_peak_bytes-1,budget->retained_bytes};
    CohRuntimeGraphReport unchanged;memset(&unchanged,0xa5,sizeof(unchanged));CohRuntimeGraphReport saved=unchanged;
    CHECK(coh_runtime_graph_build(current,catalog,snapshot,&binding,&tight,NULL,&next,&unchanged)==COH_LIMIT&&!next&&!memcmp(&saved,&unchanged,sizeof(saved)));
    binding.pins.run_sha256[0]^=1;CHECK(coh_runtime_graph_build(current,catalog,snapshot,&binding,budget,NULL,&next,&unchanged)==COH_STATE&&!next);binding.pins=*pins;
    CHECK(coh_runtime_graph_build(current,catalog,snapshot,&binding,budget,NULL,&next,&report)==COH_OK);
    CHECK(report.prior_owned_bytes&&report.prior_input_bytes==catalog.size+snapshot.size);
    CHECK(coh_runtime_graph_publish(&current,&next,&retired)==COH_OK&&!next&&retired);
    coh_runtime_graph_free(retired);coh_runtime_graph_free(current);CHECK(live==initial);
    binding.generation=1;
    if(!exhaustive)return;
    for(size_t i=1;i<=allocations_count;i++){size_t baseline=live;fail_at=calls+i;CohStatus status=coh_runtime_graph_build(NULL,catalog,snapshot,&binding,budget,NULL,&g,&unchanged);fail_at=0;CHECK(status==COH_LIMIT&&!g&&live==baseline);CHECK(!memcmp(&saved,&unchanged,sizeof(saved)));}
    Stop stop={0,0};CohCancel cancel={cancelled,&stop};CHECK(coh_runtime_graph_build(NULL,catalog,snapshot,&binding,budget,&cancel,&g,&report)==COH_OK);unsigned polls=stop.calls;coh_runtime_graph_free(g);g=NULL;
    for(unsigned i=1;i<=polls;i++){stop=(Stop){0,i};CHECK(coh_runtime_graph_build(NULL,catalog,snapshot,&binding,budget,&cancel,&g,&unchanged)==COH_CANCELLED&&!g&&live==initial);}
}

int main(int argc,char**argv){
    if(argc!=9&&argc!=10)return 2;
    CohBytes catalog=read_file(argv[1],32u*1024u*1024u),snapshot=read_file(argv[2],COH_RUNTIME_SNAPSHOT_INPUT_MAX);
    CohRuntimeSnapshotPins pins={0};char*end;unsigned long generation=strtoul(argv[3],&end,10);CHECK(!*end&&generation>0&&generation<=UINT32_MAX);pins.asset_generation=(uint32_t)generation;pins.digest=digest;
    CHECK(unhex(argv[4],pins.catalog_sha256)&&unhex(argv[5],pins.snapshot_sha256)&&unhex(argv[6],pins.source_sha256)&&unhex(argv[7],pins.run_sha256));
    int expected=atoi(argv[8]);CHECK(expected>=0&&expected<=7);
    CohRuntimeSnapshotBudget budget={COH_SG_TRANSACTION_MAX,256u*1024u};CohRuntimeSnapshotReport report;
    if(expected){rejected(catalog,snapshot,&pins,&budget,NULL,(CohStatus)expected);
        CohRuntimeGraphBinding binding={1,1,pins};CohRuntimeGraph*g=NULL;CohRuntimeGraphReport report,before;memset(&report,0xa5,sizeof(report));before=report;size_t baseline=live;
        CHECK(coh_runtime_graph_build(NULL,catalog,snapshot,&binding,&budget,NULL,&g,&report)==(CohStatus)expected);CHECK(!g&&live==baseline&&!memcmp(&report,&before,sizeof(report)));
        printf("{\"passed\":true,\"expected_refusal\":%d,\"checks\":%u}",expected,checks);}
    else{
        CohStatus status=coh_runtime_snapshot_audit(catalog,snapshot,&pins,&budget,NULL,&report);
        if(status!=COH_OK)fprintf(stderr,"runtime snapshot admission status=%u\n",(unsigned)status);
        CHECK(status==COH_OK);size_t measured_peak=peak_bytes;
        CHECK(measured_peak==catalog.size+snapshot.size+report.owned_bytes+report.peak_record_bytes);
        if(argc==10){CHECK(!strcmp(argv[9],"--test"));test(catalog,snapshot,&pins,&budget,&report);}
        graph_test(catalog,snapshot,&pins,&budget,argc==10);
        printf("{\"passed\":true,\"checks\":%u,\"files\":%u,\"slots\":%u,\"definitions\":%u,\"children\":%u,\"root_slots\":%u,\"active_roots\":%u,\"external_count\":%u,\"reachable_definitions\":%u,\"reachable_external\":%u,\"reachable_edges\":%u,\"maximum_depth\":%u,\"source_defs_crc\":%u,\"source_refs_crc\":%u,\"definitions_crc_verified\":%u,\"references_crc_verified\":%u,\"root_matrices_verified\":%u,\"owned_bytes\":%zu,\"peak_record_bytes\":%zu,\"stack_reserve\":%zu,\"harness_retained_bytes\":%zu,\"aggregate_peak_bytes\":%zu,\"external\":[",checks,report.files,report.slots,report.definitions,report.children,report.root_slots,report.active_roots,report.external_count,report.reachable_definitions,report.reachable_external,report.reachable_edges,report.maximum_depth,report.source_defs_crc,report.source_refs_crc,report.definitions_crc_verified,report.references_crc_verified,report.root_matrices_verified,report.owned_bytes,report.peak_record_bytes,report.stack_reserve,report.retained_bytes,report.aggregate_peak_bytes);
        for(uint32_t i=0;i<report.external_count;i++){CohRuntimeExternalDiagnostic*e=&report.external[i];printf("%s{\"name\":",i?",":"");json_string(e->name);printf(",\"library_path\":");json_string(e->library_path);printf(",\"original_id\":%u,\"references\":%u,\"reachable\":%u,\"model_present\":%u,\"bounds_lookup_found\":%u}",e->original_id,e->referenced,e->reachable,e->model_present,e->bounds_lookup_found);}
        printf("],\"source_graph_checked\":true,\"graph_nodes\":%u,\"graph_edges\":%u,\"graph_owned_bytes\":%zu,\"graph_aggregate_peak_bytes\":%zu,\"measured_native_peak_bytes\":%zu,\"graph_published\":false,\"groups_received\":false,\"assets_admitted\":false,\"actor_admitted\":false,\"world_authority\":false}",graph_qualified.nodes,graph_qualified.edges,graph_qualified.owned_bytes,graph_qualified.aggregate_peak_bytes,measured_peak);
    }
    free((void*)catalog.data);free((void*)snapshot.data);CHECK(!live&&!live_bytes);puts("");return 0;
}
