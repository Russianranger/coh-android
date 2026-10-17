#include "coh_groups.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "groups_fixtures.h"
static unsigned long checks;
static uint32_t fixture_files;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"visit line%d: %s\n",__LINE__,#x);exit(1);}}while(0)
typedef struct {const unsigned char *data;size_t bytes,last;unsigned mode;uint32_t files,defs,roots,nextfile,total,stop;} Stage;
static CohStatus observe(void *context,const CohGroupsEvent *e){
    Stage *s=context;s->total++;CHECK(e->span.bytes.data==s->data&&e->span.bytes.size==s->bytes);CHECK(e->span.compressed==s->mode);CHECK(e->span.cursor>=s->last&&e->span.cursor<e->span.bits);s->last=e->span.bits;
    CohRepReader r=e->span;uint32_t n;
    if(e->kind==COH_GROUPS_FILE_HEADER){CHECK(e->file==s->nextfile);s->files++;s->nextfile=e->file+1==fixture_files?0:e->file+1;CHECK(coh_rep_read(&r,1,&n)==COH_OK);if(n){char name[256];CHECK(coh_rep_string(&r,name,sizeof(name))==COH_OK);CHECK(coh_rep_read(&r,32,&n)==COH_OK);CHECK(coh_rep_read(&r,1,&n)==COH_OK&&n==0);}CHECK(r.cursor==r.bits);}
    else if(e->kind==COH_GROUPS_DEFINITION){s->defs++;CHECK(coh_rep_pack(&r,1,&n)==COH_OK&&n==e->slot+1);}
    else {CHECK(e->kind==COH_GROUPS_ROOT&&e->file==UINT32_MAX);s->roots++;CHECK(coh_rep_pack(&r,1,&n)==COH_OK&&n==e->slot);}
    return s->stop==s->total?COH_CANCELLED:COH_OK;
}
static CohStatus count_only(void *context,const CohGroupsEvent *e){(void)e;(*(unsigned*)context)++;return COH_OK;}
int main(void){
    for(size_t i=0;i<SOURCE_GROUPS_FIXTURES;i++){
        const SourceFixture *f=&source_fixtures[i];CohRepReader r;uint32_t cmd;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->data,f->bytes},f->bits,f->compressed,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);CHECK(coh_rep_pack(&r,1,&cmd)==COH_OK);CohRepReader initial=r,plain=r;
        CohGroupsInspection expected,out,prior;CohStatus status=coh_rep_groups(&plain,&expected,NULL);
        Stage s={0};s.data=f->data;s.bytes=f->bytes;s.mode=(unsigned)f->compressed;s.nextfile=status==COH_OK&&expected.files>1?1:0;
        /* FILE_HEADER numbering wraps to0 for the last file. The callback
         * receives source order, so use a specialized expected-file sequence. */
        unsigned calls=0;CohGroupsVisitor v={&calls,count_only};memset(&out,0x51,sizeof(out));prior=out;
        CHECK(coh_rep_groups_visit(&r,&v,&out,NULL)==status);
        if(status!=COH_OK){CHECK(calls==0&&!memcmp(&r,&initial,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));continue;}
        CHECK(!memcmp(&expected,&out,sizeof(out)));CHECK(calls==expected.files+expected.defs+expected.roots);
        /* Replay readable exact spans; last filewrap handled in observer by
         * a separate total-file field encoded below. */
        s.nextfile=expected.files>1?1:0;
        /* The source fixtures have up to1024 files, preserve full source order. */
        fixture_files=expected.files;
        v=(CohGroupsVisitor){&s,observe};r=initial;CHECK(coh_rep_groups_visit(&r,&v,&out,NULL)==COH_OK);CHECK(s.files==expected.files&&s.defs==expected.defs&&s.roots==expected.roots);
        for(unsigned k=0;k<3;k++)if(s.total){Stage refused={0};refused.data=f->data;refused.bytes=f->bytes;refused.mode=(unsigned)f->compressed;refused.nextfile=expected.files>1?1:0;refused.stop=k==0?1:k==1?s.total/2+1:s.total;v=(CohGroupsVisitor){&refused,observe};r=initial;out=prior;CHECK(coh_rep_groups_visit(&r,&v,&out,NULL)==COH_CANCELLED);CHECK(refused.total==refused.stop&&!memcmp(&r,&initial,sizeof(r))&&!memcmp(&out,&prior,sizeof(out)));}
        size_t step=(f->bits-initial.cursor)>8192?(f->bits-initial.cursor)/128:1;
        for(size_t end=initial.cursor;end<f->bits;end+=step){r=initial;r.bits=end;calls=0;v=(CohGroupsVisitor){&calls,count_only};out=prior;CHECK(coh_rep_groups_visit(&r,&v,&out,NULL)!=COH_OK);CHECK(calls==0&&!memcmp(&out,&prior,sizeof(out)));}
        r=initial;calls=0;v=(CohGroupsVisitor){&calls,count_only};CHECK(coh_rep_groups_visit(&r,&v,(CohGroupsInspection*)&r,NULL)==COH_INVALID);CHECK(calls==0&&!memcmp(&r,&initial,sizeof(r)));
        r=initial;CHECK(coh_rep_groups_visit(&r,(CohGroupsVisitor*)&r,&out,NULL)==COH_INVALID);CHECK(!memcmp(&r,&initial,sizeof(r)));
    }
    printf("{\"passed\":true,\"checks\":%lu,\"fixtures\":%zu,\"world_authority\":false}\n",checks,(size_t)SOURCE_GROUPS_FIXTURES);return 0;
}
