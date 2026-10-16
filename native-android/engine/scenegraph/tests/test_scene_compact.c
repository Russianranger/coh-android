#include "coh_scene_compact.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"compact check failed %s:%d: %s\n",__FILE__,__LINE__,#x);abort();}}while(0)
#ifdef COH_COMPACT_STANDALONE
#include "catalog_fixtures.h"
void*__real_malloc(size_t);void*__real_calloc(size_t,size_t);void __real_free(void*);
static size_t live,calls,fail_at,live_bytes,peak_bytes,capture_call,captured_bytes;
static struct {void*p;size_t bytes;} allocations[256];
static void track(void*p,size_t n){if(!p)return;for(unsigned i=0;i<256;i++)if(!allocations[i].p){allocations[i].p=p;allocations[i].bytes=n;live++;live_bytes+=n;if(live_bytes>peak_bytes)peak_bytes=live_bytes;return;}abort();}
void*__wrap_malloc(size_t n){calls++;if(calls==fail_at)return NULL;void*p=__real_malloc(n);track(p,n);if(calls==capture_call)captured_bytes=n;return p;}
void*__wrap_calloc(size_t n,size_t z){calls++;if(calls==fail_at)return NULL;void*p=__real_calloc(n,z);track(p,n*z);if(calls==capture_call)captured_bytes=n*z;return p;}
void __wrap_free(void*p){if(p){unsigned i;for(i=0;i<256&&allocations[i].p!=p;i++){}if(i==256||!live)abort();live--;live_bytes-=allocations[i].bytes;allocations[i].p=NULL;}__real_free(p);}
static void coh_compact_test_fail_next(void){fail_at=calls+1;}
#else
void coh_compact_test_fail_next(void);
#endif
typedef struct {size_t count,stop;} Stop;
static int cancel(void*context){Stop*s=context;return ++s->count==s->stop;}
static CohSgCompactBinding binding(uint32_t generation){CohSgCompactBinding b={1,generation,7,{1},{2}};return b;}
static CohSgCompactBudget budget={COH_SG_TRANSACTION_MAX,0};
static void rejected(const CohSgCompact*old,CohBytes input,const CohSgCompactBinding*b,const CohSgCompactBudget*limit,const CohCancel*c,CohStatus expected){
    CohSgCompact*candidate=NULL;CohSgCompactReport report;memset(&report,0xa5,sizeof(report));unsigned char before[sizeof(report)];memcpy(before,&report,sizeof(report));
    CohStatus status=coh_sg_compact_build(old,input,b,limit,c,&candidate,&report);CHECK(status!=COH_OK);if(expected!=COH_OK)CHECK(status==expected);
    CHECK(candidate==NULL);CHECK(!memcmp(before,&report,sizeof(report)));
}
static void audit_rejected(CohBytes input,const CohSgCompactBinding*b,const CohSgCompactBudget*limit,const CohCancel*c,CohStatus expected){
    CohSgCompactAudit audit;memset(&audit,0xa5,sizeof(audit));unsigned char before[sizeof(audit)];memcpy(before,&audit,sizeof(audit));
    CHECK(coh_sg_compact_audit(input,b,limit,c,&audit)==expected);CHECK(!memcmp(before,&audit,sizeof(audit)));
}
static CohSgCompactReport stress_report;
unsigned coh_scene_compact_tests(CohBytes input,uint32_t generation){
    checks=0;CohSgCompactBinding b=binding(generation);CohSgCompact*g=NULL;CohSgCompactReport report;
    CHECK(coh_sg_compact_build(NULL,input,&b,&budget,NULL,&g,&report)==COH_OK);stress_report=report;
    CHECK(report.owned_bytes<COH_SG_MEMORY_MAX&&report.aggregate_peak_bytes<=COH_SG_TRANSACTION_MAX);
    CHECK(!report.roots_bound&&!report.assets_bound&&report.input_bytes==input.size);
    CHECK(report.aggregate_peak_bytes==report.owned_bytes+report.input_bytes+report.peak_record_bytes+report.stack_reserve);
    CohSgCompactAudit audit;CHECK(coh_sg_compact_audit(input,&b,&budget,NULL,&audit)==COH_OK);
    CHECK(audit.complete_name_closure&&audit.definitions_crc_verified&&!audit.references_crc_verified);
    CHECK(audit.references_checked==report.children&&!audit.missing_references&&!audit.missing_stored&&!audit.diagnostics_truncated);
    CHECK(audit.topology.owned_bytes==report.owned_bytes&&audit.topology.retained_bytes==sizeof(audit));
    CHECK(audit.topology.aggregate_peak_bytes==report.aggregate_peak_bytes+sizeof(audit));
    CHECK(!audit.topology.roots_bound&&!audit.topology.assets_bound);
    CohSgCompactBudget audit_limit={audit.topology.aggregate_peak_bytes-1,0};audit_rejected(input,&b,&audit_limit,NULL,COH_LIMIT);
    audit_limit.aggregate_limit++;CHECK(coh_sg_compact_audit(input,&b,&audit_limit,NULL,&audit)==COH_OK);
    {CohSgCompactBinding wrong=b;wrong.generation++;audit_rejected(input,&wrong,&budget,NULL,COH_STATE);}
    uint32_t children=0,active=0,slots=0,holes=0;
    for(uint32_t f=0;f<report.files;f++){
        CohSgCompactFile file;CHECK(coh_sg_compact_file(g,f,&file)==COH_OK);
        CHECK(file.name&&file.generation==generation);slots+=file.slots;
        for(uint32_t j=0;j<file.slots;j++){uint32_t row=UINT32_MAX;CohStatus status=coh_sg_compact_slot(g,f,j,&row);
            CHECK(status==COH_OK||status==COH_NOT_FOUND);if(status==COH_NOT_FOUND){CHECK(row==UINT32_MAX);holes++;}}
    }
    CHECK(slots==report.slots&&holes==report.slots-report.definitions);
    for(uint32_t i=0;i<report.definitions;i++){
        CohSgCompactDefinition d;uint32_t found;CHECK(coh_sg_compact_definition(g,i,&d)==COH_OK);
        CHECK(coh_sg_compact_slot(g,d.file,d.slot,&found)==COH_OK&&found==i);
        CohRepReader r;CohSgDefinition decoded={0};size_t owned;
        CHECK(coh_rep_reader_bounded(&r,d.wire,d.wire_bits,(int)d.aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
        CHECK(coh_scenegraph_definition_read(&decoded,&r,d.file,COH_SG_MEMORY_MAX,&owned)==COH_OK&&r.cursor==d.wire_bits);
        CHECK(decoded.id==d.slot&&decoded.in_use==d.in_use&&decoded.child_count==d.child_count&&decoded.mod_time==d.mod_time);
        if(d.in_use){active++;CHECK(!strcmp(d.name,decoded.name));CHECK(coh_sg_compact_name(g,d.name,&found)==COH_OK&&found==i);}
        else CHECK(d.name==NULL);
        for(uint32_t j=0;j<d.child_count;j++){
            CohSgCompactChild child;CHECK(coh_sg_compact_child(g,d.child_first+j,&child)==COH_OK);
            CHECK(coh_sg_compact_name(g,decoded.children[j].name,&found)==COH_OK&&found==child.resolved);
            CHECK(!memcmp(child.matrix,decoded.children[j].matrix,sizeof(child.matrix)));children++;
        }
        coh_scenegraph_definition_dispose(&decoded);
    }
    CHECK(children==report.children);
    uint32_t unchanged=123;CHECK(coh_sg_compact_slot(g,report.files,0,&unchanged)==COH_NOT_FOUND&&unchanged==123);
    CHECK(coh_sg_compact_name(g,"MissingNameQualifiedControl",&unchanged)==COH_NOT_FOUND&&unchanged==123);
    CohSgCompactBudget exact={report.aggregate_peak_bytes-1,0};rejected(NULL,input,&b,&exact,NULL,COH_LIMIT);
    exact.aggregate_limit++;CohSgCompact*candidate=NULL;CHECK(coh_sg_compact_build(NULL,input,&b,&exact,NULL,&candidate,NULL)==COH_OK);coh_sg_compact_free(candidate);candidate=NULL;
    exact.retained_bytes=1;rejected(NULL,input,&b,&exact,NULL,COH_LIMIT);
    size_t span=(size_t)report.files+report.slots;
    if(span&&active){size_t stops[]={1,span/2+1,span,span+1,span*2,span*2+1};
        for(unsigned i=0;i<sizeof(stops)/sizeof(*stops);i++){Stop stop={0,stops[i]};CohCancel c={cancel,&stop};rejected(NULL,input,&b,&budget,&c,COH_CANCELLED);}}
    coh_compact_test_fail_next();rejected(NULL,input,&b,&budget,NULL,COH_LIMIT);
    coh_compact_test_fail_next();audit_rejected(input,&b,&budget,NULL,COH_LIMIT);
    {Stop stop={0,1};CohCancel c={cancel,&stop};if(report.files)audit_rejected(input,&b,&budget,&c,COH_CANCELLED);}
    for(size_t n=0;n<input.size;n+=input.size/13+1)rejected(NULL,(CohBytes){input.data,n},&b,&budget,NULL,COH_OK);
    b.generation=2;CohSgCompactReport replacement;
    {CohSgCompactBinding bad=b;bad.catalog_generation--;rejected(g,input,&bad,&budget,NULL,COH_STATE);
     bad=b;bad.asset_generation--;rejected(g,input,&bad,&budget,NULL,COH_STATE);
     bad=b;bad.catalog_sha256[1]^=1;rejected(g,input,&bad,&budget,NULL,COH_STATE);
     bad=b;bad.source_sha256[1]^=1;rejected(g,input,&bad,&budget,NULL,COH_STATE);}
    CHECK(coh_sg_compact_build(g,input,&b,&budget,NULL,&candidate,&replacement)==COH_OK);
    CHECK(replacement.prior_input_bytes==input.size&&replacement.prior_owned_bytes==report.owned_bytes);
    CHECK(replacement.aggregate_peak_bytes==report.aggregate_peak_bytes+input.size+report.owned_bytes);
    CohSgCompact*retired=NULL,*prior=g;CHECK(coh_sg_compact_publish(&g,&candidate,&retired)==COH_OK&&retired==prior&&!candidate);
    CHECK(coh_sg_compact_report(retired,&report)==COH_OK&&report.definitions==replacement.definitions);
    b.generation=3;CHECK(coh_sg_compact_build(g,input,&b,&budget,NULL,&candidate,NULL)==COH_OK);
    CHECK(coh_sg_compact_publish(&g,&candidate,&retired)==COH_STATE&&candidate&&retired==prior);coh_sg_compact_free(candidate);candidate=NULL;
    coh_sg_compact_free(retired);retired=NULL;
    CohSgCompactBinding other_binding=binding(generation);other_binding.catalog_sha256[0]^=1;CohSgCompact*other=NULL;
    CHECK(coh_sg_compact_build(NULL,input,&other_binding,&budget,NULL,&other,NULL)==COH_OK);
    other_binding.generation=2;CohSgCompact *other_next=NULL,*other_retired=NULL;
    CHECK(coh_sg_compact_build(other,input,&other_binding,&budget,NULL,&other_next,NULL)==COH_OK);
    CHECK(coh_sg_compact_publish(&other,&other_next,&other_retired)==COH_OK);coh_sg_compact_free(other_retired);
    b.generation=3;CHECK(coh_sg_compact_build(g,input,&b,&budget,NULL,&candidate,NULL)==COH_OK);
    CHECK(coh_sg_compact_publish(&other,&candidate,&retired)==COH_STATE&&candidate&&!retired);
    coh_sg_compact_free(candidate);coh_sg_compact_free(other);
    if(report.definitions==12192){
        CohSgCompactDefinition d;CHECK(coh_sg_compact_definition(g,0,&d)==COH_OK&&d.in_use&&d.child_count);
        CohRepReader r;uint32_t v;char text[COH_REP_NAME_MAX];
        CHECK(coh_rep_reader_bounded(&r,d.wire,d.wire_bits,(int)d.aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
        CHECK(coh_rep_pack(&r,1,&v)==COH_OK&&coh_rep_read(&r,1,&v)==COH_OK&&coh_rep_string(&r,text,sizeof(text))==COH_OK);
        CHECK(coh_rep_read(&r,32,&v)==COH_OK&&coh_rep_pack(&r,1,&v)==COH_OK);
        size_t offset=(size_t)(d.wire.data-input.data)+r.cursor/8;
        CHECK(coh_rep_string(&r,text,sizeof(text))==COH_OK&&strlen(text)==strlen(d.name));
        unsigned char*copy=malloc(input.size);CHECK(copy);memcpy(copy,input.data,input.size);
        memcpy(copy+offset,d.name,strlen(d.name)+1);CohSgCompactBinding initial=binding(generation);
        rejected(NULL,(CohBytes){copy,input.size},&initial,&budget,NULL,COH_INVALID);
        copy[offset]='?';rejected(NULL,(CohBytes){copy,input.size},&initial,&budget,NULL,COH_NOT_FOUND);free(copy);
        copy=malloc(input.size);CHECK(copy);memcpy(copy,input.data,input.size);
        for(unsigned missing=0;missing<COH_SG_COMPACT_DIAGNOSTICS_MAX+1;missing++){
            CHECK(coh_sg_compact_definition(g,missing,&d)==COH_OK&&d.in_use&&d.child_count);
            CHECK(coh_rep_reader_bounded(&r,d.wire,d.wire_bits,(int)d.aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);
            CHECK(coh_rep_pack(&r,1,&v)==COH_OK&&coh_rep_read(&r,1,&v)==COH_OK&&coh_rep_string(&r,text,sizeof(text))==COH_OK);
            CHECK(coh_rep_read(&r,32,&v)==COH_OK&&coh_rep_pack(&r,1,&v)==COH_OK);
            offset=(size_t)(d.wire.data-input.data)+r.cursor/8;copy[offset]='?';
        }
        CHECK(coh_sg_compact_audit((CohBytes){copy,input.size},&initial,&budget,NULL,&audit)==COH_NOT_FOUND);
        CHECK(audit.references_checked==report.children&&audit.missing_references==COH_SG_COMPACT_DIAGNOSTICS_MAX+1);
        CHECK(audit.missing_stored==COH_SG_COMPACT_DIAGNOSTICS_MAX&&audit.diagnostics_truncated&&!audit.complete_name_closure);
        CHECK(audit.definitions_crc_verified&&!audit.references_crc_verified&&!audit.topology.roots_bound&&!audit.topology.assets_bound);
        for(unsigned missing=0;missing<audit.missing_stored;missing++)CHECK(audit.missing[missing].file==0&&audit.missing[missing].slot==missing&&audit.missing[missing].child==0&&audit.missing[missing].name[0]=='?');
        audit_rejected((CohBytes){copy,input.size-1},&initial,&budget,NULL,COH_INVALID);free(copy);
    }
    coh_sg_compact_free(g);return checks;
}
#ifdef COH_COMPACT_STANDALONE
static uint32_t u32(const unsigned char*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
int main(int argc,char**argv){
    unsigned total=0,accepted=0;size_t large_owned=0,large_peak=0,actual_owned=0,actual_payload_peak=0;CohSgCompactAudit actual_audit={0};
    for(size_t i=0;i<sizeof(catalog_fixtures)/sizeof(*catalog_fixtures);i++){
        const CatalogFixture*f=&catalog_fixtures[i];
        total+=coh_scene_compact_tests((CohBytes){f->catalog,f->bytes},7);checks=0;accepted++;CHECK(live==0);total+=checks;checks=0;
        if(i==6){
            CohSgCompactBinding b=binding(7);CohSgCompact *temporary=NULL;size_t before=calls;
            CHECK(coh_sg_compact_build(NULL,(CohBytes){f->catalog,f->bytes},&b,&budget,NULL,&temporary,NULL)==COH_OK);
            size_t points=calls-before;coh_sg_compact_free(temporary);
            for(size_t point=1;point<=points;point++){fail_at=calls+point;rejected(NULL,(CohBytes){f->catalog,f->bytes},&b,&budget,NULL,COH_LIMIT);fail_at=0;CHECK(live==0);}
            CohSgCompactAudit audit;before=calls;
            CHECK(coh_sg_compact_audit((CohBytes){f->catalog,f->bytes},&b,&budget,NULL,&audit)==COH_OK);points=calls-before;CHECK(live==0);
            for(size_t point=1;point<=points;point++){fail_at=calls+point;audit_rejected((CohBytes){f->catalog,f->bytes},&b,&budget,NULL,COH_LIMIT);fail_at=0;CHECK(live==0);}
            total+=checks;checks=0;
        }
        if(f->which==20){large_owned=stress_report.owned_bytes;large_peak=stress_report.aggregate_peak_bytes;}
    }
    if(argc==2){
        FILE*f=fopen(argv[1],"rb");CHECK(f);CHECK(fseek(f,0,SEEK_END)==0);long n=ftell(f);CHECK(n>48&&n<=32*1024*1024);rewind(f);
        unsigned char*bytes=malloc((size_t)n);CHECK(bytes&&fread(bytes,1,(size_t)n,f)==(size_t)n);CHECK(fclose(f)==0);
        CohSgCompactBinding b=binding(u32(bytes+20));peak_bytes=live_bytes;capture_call=calls+1;rejected(NULL,(CohBytes){bytes,(size_t)n},&b,&budget,NULL,COH_NOT_FOUND);actual_owned=captured_bytes;actual_payload_peak=peak_bytes;capture_call=0;
        CohSgCompactAudit audit;CHECK(coh_sg_compact_audit((CohBytes){bytes,(size_t)n},&b,&budget,NULL,&audit)==COH_NOT_FOUND);
        CHECK(audit.references_checked==130314&&audit.missing_references==7&&audit.missing_stored==7&&!audit.diagnostics_truncated);
        CHECK(!audit.complete_name_closure&&audit.definitions_crc_verified&&!audit.references_crc_verified);
        CHECK(audit.topology.files==508&&audit.topology.slots==40225&&audit.topology.definitions==40225);
        CHECK(audit.topology.source_defs_crc==3173822562u&&audit.topology.source_refs_crc==3649375123u&&audit.topology.source_active_roots==33);
        CHECK(!audit.topology.roots_bound&&!audit.topology.assets_bound);
        static const char*expected[]={"_cot_warpgate_base","_cot_warpgate_glow","_mmayhem_curtain_8_01c","_mmayhem_curtain_8_02c","_mmayhem_curtain_8_03c","_mmayhem_curtain_16_01c","_mmayhem_curtain_16_02c"};
        for(unsigned i=0;i<7;i++)CHECK(!strcmp(audit.missing[i].name,expected[i])&&audit.missing[i].file==(i<2?110u:376u)&&audit.missing[i].slot==(i<2?61u:30u+i)&&audit.missing[i].child==(i==1?2u:1u));
        memcpy(&actual_audit,&audit,sizeof(audit));free(bytes);CHECK(live==0&&live_bytes==0);
    }else CHECK(argc==1);
    printf("{\"passed\":true,\"checks\":%u,\"source_fixtures_accepted\":%u,\"stress_owned_bytes\":%zu,\"stress_aggregate_bytes\":%zu,\"live_allocations\":%zu,\"actual_capture_expected_missing_ref\":%s,\"actual_candidate_reserved_bytes\":%zu,\"actual_peak_live_payload_bytes\":%zu,\"world_ready\":false,\"actual_references_checked\":%u,\"actual_missing_count\":%u,\"actual_missing_stored\":%u,\"actual_diagnostics_truncated\":%u,\"actual_audit_named_peak_bytes\":%zu,\"actual_missing_names\":[",total+checks,accepted,large_owned,large_peak,live,argc==2?"true":"false",actual_owned,actual_payload_peak,actual_audit.references_checked,actual_audit.missing_references,actual_audit.missing_stored,actual_audit.diagnostics_truncated,actual_audit.topology.aggregate_peak_bytes);
    /* Captured names are independently compared with the exact printable
     * identifiers above before formatting this test receipt. */
    for(unsigned i=0;i<actual_audit.missing_stored;i++)printf("%s\"%s\"",i?",":"",actual_audit.missing[i].name);
    puts("]}");return 0;
}
#endif
