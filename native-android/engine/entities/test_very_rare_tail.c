#include "coh_very_rare_tail.h"
#include "tail_observation.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint64_t checks,truncations,mutations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed %s:%d: %s\n",__FILE__,__LINE__,#x);exit(1);}}while(0)
typedef struct {const unsigned char *data;size_t bytes,bits,start;unsigned mode,scenario;CohStatus status;const unsigned char *normal;size_t normal_bytes;const unsigned char *stale;size_t stale_bytes;} TailFixture;
#include "tail_fixtures.h"
static CohEntVeryRareTail *value,*prior;
static CohEntVeryRareTailWorkspace *workspace;
static TailObservation *observation;
static uint32_t random_state=0x13579bdfu;
static uint32_t rand32(void){random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;return random_state;}
static const char *string_at(const CohEntVeryRareTail *v,CohEntTailString s){CHECK(s.offset<v->strings_bytes&&s.bytes<v->strings_bytes-s.offset);CHECK(v->strings[s.offset+s.bytes]==0);return v->strings+s.offset;}
#define TEXT(field) string_at(v,(field))
static void native_observe_mission(TailObservation *o,const CohEntVeryRareTail *v) {
    const CohEntTailMission *m=&v->mission;
    const uint32_t words[]={m->owner_dbid,m->context,m->subhandle,m->level,m->alliance,
        m->difficulty_level_adjust,m->difficulty_team_size,m->dont_reduce_boss,m->always_av,
        m->timeout,m->timezero,m->timer_type,m->fail_on_timeout,m->complete,m->mission,m->running_mission,m->sg_mission,
        m->zone_transfer,m->teleport_on_complete,m->enforce_time_limit,m->abandonable,m->zowie,m->location_present,1};
    for(unsigned i=0;i<sizeof(words)/sizeof(words[0]);i++)observe_word(o,words[i]);
    observe_text(o,m->filename_present?TEXT(m->filename):"",256);observe_text(o,TEXT(m->description),256);
    observe_text(o,TEXT(m->owner),128);observe_text(o,TEXT(m->state),256);
    for(unsigned i=0;i<3;i++)observe_float(o,m->position[i]);
    observe_word(o,m->location_type);observe_text(o,m->location_present||m->explicit_map_present?TEXT(m->location_map):"",512);
    observe_text(o,m->location_present?TEXT(m->location_name):"",256);
    observe_word(o,m->zinfo);observe_word(o,m->zseed);observe_word(o,m->zmap_id);
    observe_text(o,m->zowie?TEXT(m->ztype):"",128);observe_text(o,m->zowie?TEXT(m->zname):"",128);
    int pools[8]={0};if(m->zowie){char copy[1024];strcpy(copy,TEXT(m->zpool_sizes));char *next=strtok(copy," ");unsigned n=0;while(next){CHECK(n<8);pools[n++]=atoi(next);next=strtok(NULL," ");}}
    for(unsigned i=0;i<8;i++)observe_word(o,(uint32_t)pools[i]);
}
static void native_observe(const CohEntVeryRareTail *v,unsigned stale,TailObservation *o) {
    memset(o,0,sizeof(*o));unsigned group=v->supergroup_update&&v->supergroup_id;
    observe_word(o,v->supergroup_update?v->supergroup_id:99);
    observe_text(o,!v->supergroup_update?"PriorGroup":group&&!stale?TEXT(v->supergroup_name):"",64);
    const char *emblem=group?TEXT(v->supergroup_emblem):"";
    observe_text(o,!v->supergroup_update?"PriorEmblem":group&&!stale&&!strcmp(emblem,"KnownEmblem")?emblem:"",128);
    observe_word(o,group&&!stale?v->colors[0]:0x11);observe_word(o,group&&!stale?v->colors[1]:0x22);observe_word(o,group!=0);
    if(group) {
        observe_word(o,v->spaces_for_items);observe_word(o,v->mission_present);
        if(v->mission_present)native_observe_mission(o,v);
        unsigned first[256],last[256],n=0;
        for(unsigned i=0;i<v->token_count;i++){const char *name=TEXT(v->tokens[i].name);if(!*name)continue;unsigned j;for(j=0;j<n;j++)if(!strcmp(name,TEXT(v->tokens[first[j]].name)))break;if(j==n){first[n]=i;n++;}last[j]=i;}
        observe_word(o,n);for(unsigned j=0;j<n;j++){observe_text(o,TEXT(v->tokens[first[j]].name),2048);observe_word(o,v->tokens[last[j]].value);observe_word(o,v->tokens[last[j]].time);}
        n=0;
        for(unsigned i=0;i<v->recipe_count;i++){const CohEntTailRecipe *r=&v->recipes[i];const char *name=TEXT(r->name);if((strcmp(name,"RecipeA")&&strcmp(name,"RecipeB"))||(!r->unlimited&&!r->count))continue;unsigned j;for(j=0;j<n;j++)if(!strcmp(name,TEXT(v->recipes[first[j]].name)))break;if(j==n){first[n]=i;n++;}last[j]=i;}
        observe_word(o,n);for(unsigned j=0;j<n;j++){const CohEntTailRecipe *r=&v->recipes[last[j]];observe_text(o,TEXT(r->name),2048);observe_word(o,r->unlimited?UINT32_MAX:r->count);}
        n=0;for(unsigned i=0;i<v->detail_count;i++){const char *name=TEXT(v->details[i].name);if(!strcmp(name,"DetailA")||!strcmp(name,"DetailB"))first[n++]=i;}
        observe_word(o,n);for(unsigned j=0;j<n;j++){const CohEntTailDetail *d=&v->details[first[j]];observe_text(o,TEXT(d->name),2048);observe_word(o,d->creation_time);observe_word(o,d->expiration_time);observe_word(o,d->flags);observe_word(o,1);}
    }
    observe_word(o,v->pact_update?v->pact_id:88);observe_word(o,v->pact_update&&v->pact_id);
    if(v->pact_update&&v->pact_id){observe_word(o,v->pact_count);for(unsigned i=0;i<v->pact_count;i++){const CohEntTailPactMember *m=&v->pact[i];observe_word(o,m->dbid);observe_text(o,m->name_present?TEXT(m->name):m->dbid==777?"CachedMember":"",64);observe_word(o,!m->name_present);}}
    observe_word(o,v->logout_update&&!stale?v->logout_bad_connection:1);
    observe_float(o,v->logout_update&&!stale?(float)(30u*v->logout_quanta):270.0f);
}
#undef TEXT
static CohRepReader make_reader(const void *data,size_t bytes,size_t bits,unsigned mode,size_t start) {
    CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){data,bytes},bits,(int)mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=start;return r;
}
static CohStatus parse(CohRepReader *r){return coh_ent_very_rare_tail(r,value,workspace,0,COH_ENT_TAIL_AGGREGATE_MAX);}
static void bad(const void *data,size_t bytes,size_t bits,unsigned mode,size_t start,CohStatus expected) {
    CohRepReader r=make_reader(data,bytes,bits,mode,start),old=r;
    memset(value,0xa5,sizeof(*value));memcpy(prior,value,sizeof(*prior));
    CohStatus s=parse(&r);if(expected!=COH_OK)CHECK(s==expected);else CHECK(s!=COH_OK);
    CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));
}
static void source_fixtures(void) {
    for(unsigned i=0;i<sizeof(tail_fixtures)/sizeof(tail_fixtures[0]);i++) {
        const TailFixture *f=&tail_fixtures[i];CohRepReader r=make_reader(f->data,f->bytes,f->bits,f->mode,f->start),old=r;
        memset(value,0xa5,sizeof(*value));memcpy(prior,value,sizeof(*prior));CohStatus status=parse(&r);
        if(status!=f->status)fprintf(stderr,"fixture %u scenario %u mode %u got %d expected %d\n",i,f->scenario,f->mode,status,f->status);
        CHECK(status==f->status);
        if(status!=COH_OK){CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));continue;}
        CHECK(value->begin_bit==f->start&&value->end_bit==f->bits&&r.cursor==f->bits);
        native_observe(value,0,observation);CHECK(observation->used==f->normal_bytes);CHECK(!memcmp(observation->bytes,f->normal,f->normal_bytes));
        native_observe(value,1,observation);CHECK(observation->used==f->stale_bytes);CHECK(!memcmp(observation->bytes,f->stale,f->stale_bytes));
        if(f->scenario==11)CHECK(value->mission.description.bytes==999&&value->mission.state.bytes==999);
        if(f->scenario==3)CHECK(value->token_count==4&&value->recipe_count==3&&value->detail_count==2); /* ordered raw empty/duplicate events survive */
        unsigned char *copy=malloc(f->bytes+2);CHECK(copy!=NULL);memcpy(copy,f->data,f->bytes);memset(copy+f->bytes,0xa5,2);
        r=make_reader(copy,f->bytes+2,f->bits+8,f->mode,f->start);CHECK(parse(&r)==COH_OK);CHECK(r.cursor==f->bits);free(copy);
        /* Exhaust every truncation at the two canonical alignment profiles.
         * All other starting offsets have exact source/state comparisons. */
        if(f->start==0) {
            for(size_t bit=0;bit<f->bits;bit++){bad(f->data,f->bytes,bit,f->mode,0,COH_OK);truncations++;}
            copy=malloc(f->bytes);CHECK(copy!=NULL);
            for(size_t at=0;at<f->bytes;at++){memcpy(copy,f->data,f->bytes);copy[at]^=0xff;r=make_reader(copy,f->bytes,f->bits,f->mode,0);old=r;memset(value,0xa5,sizeof(*value));memcpy(prior,value,sizeof(*prior));status=parse(&r);mutations++;if(status!=COH_OK){CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));}else CHECK(r.cursor<=f->bits);}
            free(copy);
        }
    }
}
typedef struct {unsigned char data[4096];size_t bits;unsigned mode;} Writer;
static void write_bits(Writer *w,unsigned n,uint32_t v){if(w->mode)n=(n+7)&~7u;CHECK(w->bits+n<=sizeof(w->data)*8);for(unsigned i=0;i<n;i++){if(v&(UINT32_C(1)<<i))w->data[w->bits/8]|=(unsigned char)(1u<<(w->bits%8));w->bits++;}}
static void write_pack(Writer *w,unsigned n,uint32_t v){if(w->mode){write_bits(w,32,v);return;}while(n<32&&v>=(UINT32_C(1)<<n)-1u){uint32_t step=(UINT32_C(1)<<n)-1u;write_bits(w,n,step);v-=step;n=n>16?32:n*2;}write_bits(w,n,v);}
static void write_auto(Writer *w,uint32_t v){static const unsigned widths[]={2,10,24,32};unsigned i=0;while(i<3&&v>=(UINT32_C(1)<<widths[i]))i++;write_bits(w,2,i);write_bits(w,widths[i],v);}
static void group_prefix(Writer *w){write_bits(w,1,1);write_pack(w,2,1);write_bits(w,8,0);write_bits(w,8,0);write_bits(w,32,0);write_bits(w,32,0);write_pack(w,2,0);write_bits(w,1,0);}
static void reject_writer(Writer *w,CohStatus status){bad(w->data,(w->bits+7)/8,w->bits,w->mode,0,status);}
static void malformed(void) {
    for(unsigned mode=0;mode<2;mode++) {
        for(unsigned index=0;index<3;index++){Writer w={{0},0,mode};group_prefix(&w);for(unsigned i=0;i<index;i++)write_auto(&w,0);write_auto(&w,257);reject_writer(&w,COH_LIMIT);}
        Writer w={{0},0,mode};group_prefix(&w);write_auto(&w,0);write_auto(&w,1);write_pack(&w,1,2);reject_writer(&w,COH_INVALID);
        w=(Writer){{0},0,mode};write_bits(&w,1,0);write_bits(&w,1,1);write_auto(&w,1);write_auto(&w,3);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};write_bits(&w,1,0);write_bits(&w,1,1);write_auto(&w,1);write_auto(&w,1);write_auto(&w,3);write_bits(&w,1,1);for(unsigned i=0;i<64;i++)write_bits(&w,8,'p');write_bits(&w,8,0);reject_writer(&w,COH_LIMIT);
        w=(Writer){{0},0,mode};write_bits(&w,1,1);write_pack(&w,2,1);for(unsigned i=0;i<1024;i++)write_bits(&w,8,'s');write_bits(&w,8,0);reject_writer(&w,COH_LIMIT);
        if(mode){w=(Writer){{0},0,1};write_bits(&w,1,2);reject_writer(&w,COH_INVALID);w=(Writer){{0},0,1};write_bits(&w,1,0);write_bits(&w,1,1);write_bits(&w,2,4);reject_writer(&w,COH_INVALID);}
    }
    /* Mutate a unique exact original producer location word, preserving every
     * surrounding branch. Both transport alignments reject infinity and NaN. */
    for(unsigned i=0;i<sizeof(tail_fixtures)/sizeof(tail_fixtures[0]);i++){
        const TailFixture *f=&tail_fixtures[i];if(f->scenario!=4||f->start)continue;
        size_t found=SIZE_MAX;unsigned count=0;
        for(size_t bit=0;bit+32<=f->bits;bit++){uint32_t word=0;for(unsigned j=0;j<32;j++)word|=(uint32_t)((f->data[(bit+j)/8]>>((bit+j)%8))&1u)<<j;if(word==0x41480000u){found=bit;count++;}}
        CHECK(count==1);unsigned char *copy=malloc(f->bytes);CHECK(copy!=NULL);
        for(unsigned k=0;k<2;k++){memcpy(copy,f->data,f->bytes);uint32_t word=k?0x7fc00000u:0x7f800000u;for(unsigned j=0;j<32;j++){size_t bit=found+j;copy[bit/8]=(unsigned char)((copy[bit/8]&~(1u<<(bit%8)))|(((word>>j)&1u)<<(bit%8)));}bad(copy,f->bytes,f->bits,f->mode,0,COH_INVALID);}free(copy);
    }
}
static void budgets_and_aliases(void) {
    const TailFixture *f=&tail_fixtures[0];CohRepReader r=make_reader(f->data,f->bytes,f->bits,f->mode,f->start),old=r;
    size_t budget=sizeof(*value)+sizeof(*workspace)+COH_ENT_TAIL_STACK_RESERVE+f->bytes;
    CHECK(coh_ent_very_rare_tail(&r,value,workspace,0,budget)==COH_OK);
    r=old;memset(value,0xa5,sizeof(*value));memcpy(prior,value,sizeof(*prior));
    CHECK(coh_ent_very_rare_tail(&r,value,workspace,0,budget-1)==COH_LIMIT);CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));
    CHECK(coh_ent_very_rare_tail(&r,value,workspace,SIZE_MAX,budget)==COH_LIMIT);
    CHECK(coh_ent_very_rare_tail(&r,value,workspace,1,budget)==COH_LIMIT);
    CHECK(coh_ent_very_rare_tail(&r,value,workspace,1,budget+1)==COH_OK);
    r=old;CHECK(coh_ent_very_rare_tail(&r,&workspace->candidate,workspace,0,COH_ENT_TAIL_AGGREGATE_MAX)==COH_INVALID);CHECK(!memcmp(&r,&old,sizeof(r)));
    CHECK(coh_ent_very_rare_tail(&r,value,(CohEntVeryRareTailWorkspace*)value,0,COH_ENT_TAIL_AGGREGATE_MAX)==COH_INVALID);
    memcpy(value->strings,f->data,f->bytes);r=make_reader(value->strings,f->bytes,f->bits,f->mode,f->start);old=r;memcpy(prior,value,sizeof(*prior));
    CHECK(parse(&r)==COH_INVALID);CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));
    memcpy(workspace->candidate.strings,f->data,f->bytes);r=make_reader(workspace->candidate.strings,f->bytes,f->bits,f->mode,f->start);old=r;
    CHECK(parse(&r)==COH_INVALID);CHECK(!memcmp(&r,&old,sizeof(r)));
    CHECK(coh_ent_very_rare_tail(NULL,value,workspace,0,1)==COH_INVALID);CHECK(coh_ent_very_rare_tail(&r,NULL,workspace,0,1)==COH_INVALID);CHECK(coh_ent_very_rare_tail(&r,value,NULL,0,1)==COH_INVALID);
    r=make_reader(f->data,f->bytes,f->bits,f->mode,f->start);CHECK(coh_ent_very_rare_tail(&r,value,workspace,0,0)==COH_INVALID);CHECK(coh_ent_very_rare_tail(&r,value,workspace,0,COH_ENT_TAIL_AGGREGATE_MAX+1)==COH_INVALID);
    r.cursor=r.bits+1;old=r;CHECK(parse(&r)==COH_INVALID);CHECK(!memcmp(&r,&old,sizeof(r)));
}
static void fuzz(void) {
    for(unsigned i=0;i<10000;i++){unsigned char data[384];for(unsigned j=0;j<sizeof(data);j++)data[j]=(unsigned char)rand32();unsigned mode=rand32()&1u;size_t bits=rand32()%(sizeof(data)*8+1);CohRepReader r=make_reader(data,sizeof(data),bits,mode,0),old=r;memset(value,0x5a,sizeof(*value));memcpy(prior,value,sizeof(*prior));CohStatus status=parse(&r);randomized++;if(status!=COH_OK){CHECK(!memcmp(&r,&old,sizeof(r)));CHECK(!memcmp(value,prior,sizeof(*value)));}else CHECK(r.cursor<=bits);}
}
int main(void) {
    value=malloc(sizeof(*value));prior=malloc(sizeof(*prior));workspace=malloc(sizeof(*workspace));observation=malloc(sizeof(*observation));CHECK(value&&prior&&workspace&&observation);
    source_fixtures();malformed();budgets_and_aliases();fuzz();
    printf("{\"passed\":true,\"checks\":%llu,\"truncations\":%llu,\"mutations\":%llu,\"randomized\":%llu,\"fixtures\":%zu,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"aggregate_limit\":%u,\"full_update_complete\":false,\"actor_publication\":false}\n",(unsigned long long)checks,(unsigned long long)truncations,(unsigned long long)mutations,(unsigned long long)randomized,sizeof(tail_fixtures)/sizeof(tail_fixtures[0]),sizeof(*value),sizeof(*workspace),COH_ENT_TAIL_AGGREGATE_MAX);
    free(value);free(prior);free(workspace);free(observation);return 0;
}
