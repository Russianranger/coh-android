#include "coh_original_rare_receive.h"
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define ALIGN(T) offsetof(struct{char byte;T value;},value)
static int span(const void *p,size_t n){return p&&(uintptr_t)p<=UINTPTR_MAX-n;}
static int apart(const void*a,size_t an,const void*b,size_t bn){return(uintptr_t)a+an<=(uintptr_t)b||(uintptr_t)b+bn<=(uintptr_t)a;}
static int charge(size_t *n,size_t add,size_t budget){if(add>budget||*n>budget-add)return 0;*n+=add;return 1;}
static void wipe(void *p,size_t n){volatile unsigned char *v=p;while(n--)*v++=0;}
CohStatus coh_original_rare_receive(const CohRepReader *reader,CohOriginalRareWorkspace *workspace,CohOriginalRareReport *out,size_t budget,size_t retained){
 const void *spans[4];size_t sizes[4],needed=COH_ORIGINAL_RARE_STACK_RESERVE,child_retained;CohRepReader r;CohEntFailure failure={0};CohOriginalRareReport report={0};CohStatus status;uint32_t unused;
 if(!budget||budget>COH_ORIGINAL_RARE_AGGREGATE_MAX||!span(reader,sizeof(*reader))||!span(workspace,sizeof(*workspace))||!span(out,sizeof(*out))||(uintptr_t)reader%ALIGN(CohRepReader)||(uintptr_t)workspace%ALIGN(CohOriginalRareWorkspace)||(uintptr_t)out%ALIGN(CohOriginalRareReport))return COH_INVALID;
 spans[0]=reader;sizes[0]=sizeof(*reader);spans[1]=workspace;sizes[1]=sizeof(*workspace);spans[2]=out;sizes[2]=sizeof(*out);spans[3]=reader->bytes.data;sizes[3]=reader->bytes.size;
 for(unsigned i=0;i<4;i++){if(!span(spans[i],sizes[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],sizes[i],spans[j],sizes[j]))return COH_INVALID;}
 r=*reader;if(coh_rep_read(&r,0,&unused)!=COH_OK)return COH_INVALID;
 for(unsigned i=0;i<4;i++)if(!charge(&needed,sizes[i],budget))return COH_LIMIT;
 if(!charge(&needed,retained,budget))return COH_LIMIT;
 memset(workspace,0,sizeof(*workspace));report.begin_bit=r.cursor;report.packet_bits=r.bits;report.stage=COH_ORIGINAL_RARE_PREFIX;report.failure_cursor_exact=1;
 status=coh_ent_rare_prefix(&r,&workspace->prefix,&failure);
 if(status!=COH_OK){report.failure_bit=failure.bit;goto done;}
 report.prefix_complete=1;report.prefix_end_bit=r.cursor;report.power_crc_present=workspace->prefix.power_present;report.power_crc=workspace->prefix.power_crc;
 report.stage=COH_ORIGINAL_RARE_TAIL;report.failure_bit=r.cursor;report.failure_cursor_exact=0;
 child_retained=needed-reader->bytes.size-sizeof(workspace->tail)-sizeof(workspace->tail_workspace)-COH_ENT_TAIL_STACK_RESERVE;
 status=coh_ent_very_rare_tail(&r,&workspace->tail,&workspace->tail_workspace,child_retained,COH_ENT_TAIL_AGGREGATE_MAX);
 if(status!=COH_OK)goto done;
 report.rare_complete=1;report.rare_end_bit=r.cursor;report.supergroup_id=workspace->tail.supergroup_id;report.token_count=workspace->tail.token_count;report.recipe_count=workspace->tail.recipe_count;report.detail_count=workspace->tail.detail_count;report.pact_count=workspace->tail.pact_count;
 report.stage=COH_ORIGINAL_RARE_BUFFS;report.failure_bit=r.cursor;
 child_retained=needed-reader->bytes.size-sizeof(workspace->buffs)-sizeof(workspace->buffs_workspace)-COH_ENT_BUFF_STACK_RESERVE;
 status=coh_ent_teammate_buffs(&r,&workspace->buffs,&workspace->buffs_workspace,child_retained,COH_ENT_BUFF_AGGREGATE_MAX);
 if(status!=COH_OK)goto done;
 report.buffs_complete=1;report.buff_count=workspace->buffs.count;report.buff_mod_count=workspace->buffs.mods_count;report.entity_suffix_complete=1;report.stage=COH_ORIGINAL_RARE_COMPLETE;report.failure_cursor_exact=1;report.failure_bit=r.cursor;
 done:report.status=status;report.end_bit=r.cursor;*out=report;wipe(workspace,sizeof(*workspace));return status;
}
