#include "coh_badges.h"
#include "badge_observation.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {
    const unsigned char *data;size_t bytes,bits,badge_bits;
    unsigned aligned,prefix,scenario;CohStatus status;const unsigned char *expected;
} BadgeFixture;
#ifdef COH_GLOBALS_BADGES
#define COH_BADGE_FIXTURES_ONLY
#include "fixtures.h"
#else
#include "badge_fixtures.h"
#endif
static unsigned checks,truncations,random_cases;
static CohBadgeUpdate *update,*saved;
static CohBadgeWorkspace *workspace;
#define CHECK(expr) do {checks++;if(!(expr)){fprintf(stderr,"badge check failed line %d: %s\n",__LINE__,#expr);exit(1);}} while(0)
static void init(CohRepReader *r,const unsigned char *data,size_t bytes,size_t bits,unsigned aligned,unsigned prefix) {
    CHECK(coh_rep_reader_bounded(r,(CohBytes){data,bytes},bits,(int)aligned,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r->cursor=prefix;
}
static CohStatus attempt(CohRepReader *r,size_t retained,size_t limit) {
    CohRepReader old;memcpy(&old,r,sizeof(old));memcpy(saved,update,sizeof(*saved));
    CohStatus s=coh_global_badges(r,update,workspace,retained,limit);
    if(s!=COH_OK){CHECK(!memcmp(r,&old,sizeof(old)));CHECK(!memcmp(update,saved,sizeof(*saved)));}
    else {
        CHECK(r->cursor>=old.cursor&&r->cursor<=r->bits);
        CHECK(update->player_count<=COH_BADGE_PLAYER_MAX&&update->supergroup_count<=COH_BADGE_SUPERGROUP_MAX);
        CHECK(update->history_count<=COH_BADGE_RECENT_MAX&&update->filenames_bytes<=COH_BADGE_FILENAMES_MAX);
    }
    return s;
}
static CohStatus monitor_attempt(CohRepReader *r,CohBadgeMonitor *m) {
    CohRepReader old;CohBadgeMonitor before;
    memcpy(&old,r,sizeof(old));memcpy(&before,m,sizeof(before));
    CohStatus s=coh_global_badge_monitor(r,m);
    if(s!=COH_OK){CHECK(!memcmp(r,&old,sizeof(old)));CHECK(!memcmp(m,&before,sizeof(before)));}
    else CHECK(r->cursor>=old.cursor&&r->cursor<=r->bits);
    return s;
}
static void observe(const CohBadgeUpdate *u,const CohBadgeMonitor *m,BadgeObservation *o) {
    badge_prior(o);o->debug_mode=u->debug_mode;
    for(unsigned i=0;i<u->player_count+u->supergroup_count;i++) {
        const CohBadgeRecord *b=u->records+i;unsigned sg=i>=u->player_count;
        CHECK(b->index>0&&b->index<(sg?COH_BADGE_SUPERGROUP_MAX:COH_BADGE_PLAYER_MAX));
        CHECK(!(b->flags&~15u)&&b->completion<=0xfffffu);
        uint32_t state=(b->flags&COH_BADGE_OWNED)?0xe00fffffu:
            ((b->flags&COH_BADGE_VISIBLE)?0x40000000u:0u)|((b->flags&COH_BADGE_KNOWN)?0x20000000u:0u)|b->completion;
        const char *filename=NULL;
        if(b->flags&COH_BADGE_FILENAME) {
            CHECK(b->filename_offset<u->filenames_bytes);
            CHECK(b->filename_bytes<u->filenames_bytes-b->filename_offset);
            filename=u->filenames+b->filename_offset;CHECK(strlen(filename)==b->filename_bytes);
        }
        if(sg){o->supergroup[b->index]=state;o->supergroup_filename[b->index]=badge_text_hash(filename);}
        else {o->player[b->index]=state;o->player_filename[b->index]=badge_text_hash(filename);}
    }
    if(u->history_present)memcpy(o->recent,u->recent,sizeof(o->recent));
    o->monitor=*m;
}
static void originals(void) {
    for(size_t i=0;i<sizeof(badge_fixtures)/sizeof(badge_fixtures[0]);i++) {
        const BadgeFixture *f=badge_fixtures+i;CohRepReader r;CohBadgeMonitor m;BadgeObservation observation;
        memset(update,0xa5,sizeof(*update));init(&r,f->data,f->bytes,f->bits,f->aligned,f->prefix);
        CohStatus s=attempt(&r,0,COH_BADGE_AGGREGATE_MAX);
        if(s!=f->status)fprintf(stderr,"scenario %u aligned %u prefix %u got %u expected %u\n",f->scenario,f->aligned,f->prefix,s,f->status);
        CHECK(s==f->status);if(s!=COH_OK)continue;
        CHECK(r.cursor==f->badge_bits);memset(&m,0xa5,sizeof(m));
        CHECK(monitor_attempt(&r,&m)==COH_OK);CHECK(r.cursor==f->bits);
        observe(update,&m,&observation);CHECK(!memcmp(&observation,f->expected,sizeof(observation)));
        /* A following complete wire body is deliberately present. Each parser
         * must stop at its own original consumer boundary, never packet end. */
        for(size_t cut=f->prefix;cut<f->badge_bits;cut++) {
            if(f->badge_bits-f->prefix>4096&&cut>f->prefix+64&&cut+64<f->badge_bits&&cut%257)continue;
            init(&r,f->data,f->bytes,cut,f->aligned,f->prefix);
            CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)!=COH_OK);truncations++;
        }
        for(size_t cut=f->badge_bits;cut<f->bits;cut++) {
            init(&r,f->data,f->bytes,cut,f->aligned,(unsigned)f->badge_bits);
            CHECK(monitor_attempt(&r,&m)!=COH_OK);truncations++;
        }
        size_t required=sizeof(*update)+sizeof(*workspace)+8192+f->bytes;
        init(&r,f->data,f->bytes,f->bits,f->aligned,f->prefix);
        CHECK(attempt(&r,0,required-1)==COH_LIMIT);
        CHECK(attempt(&r,1,required)==COH_LIMIT);
        CHECK(attempt(&r,0,required)==COH_OK);
    }
}
typedef struct {unsigned char data[8192];size_t bits;} Writer;
static void bits(Writer *w,unsigned width,uint32_t value) {
    CHECK(w->bits+width<=sizeof(w->data)*8);
    for(unsigned i=0;i<width;i++,w->bits++)if((value>>i)&1u)w->data[w->bits/8]|=(unsigned char)(1u<<(w->bits&7));
}
static void pack(Writer *w,unsigned width,uint32_t value) {
    while(width<32&&value>=((1u<<width)-1u)){uint32_t cap=(1u<<width)-1u;bits(w,width,cap);value-=cap;width=width>16?32:width*2;}
    bits(w,width,value);
}
static void malformed(void) {
    CohRepReader r;CohBadgeMonitor m={{0}};Writer w={{0},0};
    pack(&w,4,0);bits(&w,1,0);bits(&w,1,1);bits(&w,8,51);
    init(&r,w.data,(w.bits+7)/8,w.bits,0,0);CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_LIMIT);
    const uint32_t bad_indices[]={0,4096,0x80000000u,0xffffffffu};
    for(unsigned i=0;i<sizeof(bad_indices)/sizeof(bad_indices[0]);i++) {
        memset(&w,0,sizeof(w));pack(&w,4,0);bits(&w,1,1);pack(&w,6,bad_indices[i]);
        init(&r,w.data,(w.bits+7)/8,w.bits,0,0);CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    }
    /* Late malformed supergroup tail: preceding complete player record/history
     * must not leak into output or advance the enclosing reader. */
    memset(&w,0,sizeof(w));pack(&w,4,2);bits(&w,1,1);pack(&w,6,1);bits(&w,1,1);bits(&w,1,0);bits(&w,1,0);bits(&w,1,1);bits(&w,8,0);bits(&w,1,1);bits(&w,1,1);pack(&w,6,1050);
    init(&r,w.data,(w.bits+7)/8,w.bits,0,0);CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    unsigned char bad_boolean[]={0,0,0,0,2};
    init(&r,bad_boolean,sizeof(bad_boolean),40,1,0);CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    init(&r,bad_boolean+4,1,8,1,0);CHECK(monitor_attempt(&r,&m)==COH_INVALID);
    memset(&w,0,sizeof(w));bits(&w,1,1);bits(&w,8,255);bits(&w,16,65535);bits(&w,32,UINT32_MAX);
    init(&r,w.data,(w.bits+7)/8,w.bits,0,0);CHECK(monitor_attempt(&r,&m)==COH_INVALID);
    unsigned char absent[]={0};init(&r,absent,1,7,0,0);
    CHECK(attempt(&r,SIZE_MAX,COH_BADGE_AGGREGATE_MAX)==COH_LIMIT);
    CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX+1)==COH_INVALID);
    CHECK(attempt(&r,0,0)==COH_INVALID);
    r.cursor=8;CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    CHECK(coh_global_badges(NULL,update,workspace,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    CHECK(coh_global_badges(&r,NULL,workspace,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    CHECK(coh_global_badges(&r,update,NULL,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    CHECK(coh_global_badge_monitor(NULL,&m)==COH_INVALID);CHECK(coh_global_badge_monitor(&r,NULL)==COH_INVALID);
}
static void aliases(void) {
    unsigned char absent[]={0};CohRepReader r,old;
    memset(update,0,sizeof(*update));memcpy(saved,update,sizeof(*saved));init(&r,absent,1,7,0,0);
    memcpy(&old,&r,sizeof(old));
    CHECK(coh_global_badges(&r,update,(CohBadgeWorkspace *)update,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    CHECK(!memcmp(update,saved,sizeof(*saved))&&!memcmp(&r,&old,sizeof(old)));
    init(&r,(unsigned char *)update,sizeof(*update),7,0,0);CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    init(&r,(unsigned char *)workspace,sizeof(*workspace),7,0,0);CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    CohRepReader *alias=(CohRepReader *)update;init(alias,absent,1,7,0,0);memcpy(saved,update,sizeof(*saved));
    CHECK(coh_global_badges(alias,update,workspace,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);CHECK(!memcmp(update,saved,sizeof(*saved)));
    alias=(CohRepReader *)workspace;init(alias,absent,1,7,0,0);memcpy(&old,alias,sizeof(old));
    CHECK(coh_global_badges(alias,update,workspace,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);CHECK(!memcmp(alias,&old,sizeof(old)));
    init(&r,(unsigned char *)&r,sizeof(r),7,0,0);CHECK(attempt(&r,0,COH_BADGE_AGGREGATE_MAX)==COH_INVALID);
    union {CohRepReader reader;CohBadgeMonitor monitor;} shared,before;
    init(&shared.reader,absent,1,7,0,0);memcpy(&before,&shared,sizeof(before));
    CHECK(coh_global_badge_monitor(&shared.reader,&shared.monitor)==COH_INVALID);CHECK(!memcmp(&before,&shared,sizeof(before)));
    CohBadgeMonitor m={{0}};init(&r,(unsigned char *)&m,sizeof(m),10,0,0);CHECK(monitor_attempt(&r,&m)==COH_INVALID);
    init(&r,(unsigned char *)&r,sizeof(r),10,0,0);CHECK(monitor_attempt(&r,&m)==COH_INVALID);
}
static uint32_t rng=0x6421a7u;
static uint32_t next(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static void fuzz(void) {
    unsigned char data[128];
    for(unsigned i=0;i<10000;i++) {
        for(unsigned j=0;j<sizeof(data);j++)data[j]=(unsigned char)next();
        size_t bytes=next()%(sizeof(data)+1),nbits=bytes?next()%(bytes*8+1):0;
        unsigned aligned=i&1,prefix=aligned?0:next()%8;if(prefix>nbits)prefix=0;
        CohRepReader r;CohBadgeMonitor m={{0}};init(&r,data,bytes,nbits,aligned,prefix);
        (void)attempt(&r,0,COH_BADGE_AGGREGATE_MAX);
        init(&r,data,bytes,nbits,aligned,prefix);(void)monitor_attempt(&r,&m);random_cases++;
    }
}
unsigned coh_badges_run_tests(void) {
    checks=truncations=random_cases=0;
    update=malloc(sizeof(*update));saved=malloc(sizeof(*saved));workspace=malloc(sizeof(*workspace));
    CHECK(update&&saved&&workspace);CHECK(sizeof(BadgeObservation)==41612);
    originals();malformed();aliases();fuzz();
    free(update);free(saved);free(workspace);return checks;
}
void coh_badges_print_report(void) {
    printf("{\"passed\":true,\"checks\":%u,\"source_fixtures\":%u,\"truncations\":%u,\"random_cases\":%u,\"update_bytes\":%u,\"workspace_bytes\":%u,\"monitor_bytes\":%u,\"full_update_complete\":false,\"dictionary_bindings_verified\":false,\"acknowledgments_enabled\":false}",checks,(unsigned)(sizeof(badge_fixtures)/sizeof(badge_fixtures[0])),truncations,random_cases,(unsigned)sizeof(*update),(unsigned)sizeof(*workspace),(unsigned)sizeof(CohBadgeMonitor));
}
#ifndef COH_GLOBALS_BADGES
int main(void){coh_badges_run_tests();coh_badges_print_report();putchar('\n');return 0;}
#endif
