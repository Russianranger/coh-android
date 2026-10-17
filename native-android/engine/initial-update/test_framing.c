/* Exercise the exact private native tail implementation without expanding its
 * public API. Unused whole-owner sections are discarded by the host linker. */
#include "coh_initial_update.c"
#include <stdio.h>
#include <stdlib.h>
static unsigned long checks,cuts;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"tail check %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static unsigned word(FILE*f){unsigned char p[4];if(fread(p,1,4,f)!=4)abort();return (unsigned)p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
static CohStatus tail(const unsigned char*wire,unsigned bytes,unsigned bits,unsigned mode,unsigned begin,CohInitialUpdateReport*out,size_t*end){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){wire,bytes},bits,mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK);r.cursor=begin;memset(out,0,sizeof(*out));CohStatus status=command_tail(&r,out);*end=r.cursor;CHECK(!out->validated.complete_initial_update&&!out->validated.actor_publication&&!out->validated.ack_permitted);return status;}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;unsigned count=word(f),success=0,limit=0;CohInitialUpdateReport*out=malloc(sizeof(*out));if(!out)abort();
 for(unsigned i=0;i<count;i++){
  unsigned bytes=word(f),bits=word(f),begin=word(f),mode=word(f),markers=word(f);unsigned char*wire=calloc(bytes+8,1);if(!wire||fread(wire,1,bytes,f)!=bytes)abort();size_t end=0;CohStatus status=tail(wire,bytes,bits,mode,begin,out,&end);
  if(markers<256){CHECK(status==COH_OK&&end==bits&&out->validated.transport_end_verified&&out->validated.command_count==markers);success++;}
  else{CHECK(status==COH_LIMIT&&!out->validated.transport_end_verified&&out->validated.command_count==256);limit++;}
  for(unsigned bit=begin;bit<bits;bit++){status=tail(wire,bytes,bit,mode,begin,out,&end);CHECK(status!=COH_OK&&!out->validated.transport_end_verified);cuts++;}
  status=tail(wire,bytes+8,bits+1,mode,begin,out,&end);CHECK(status!=COH_OK&&!out->validated.transport_end_verified);
  free(wire);
 }
 CHECK(fgetc(f)==EOF);fclose(f);free(out);printf("{\"checks\":%lu,\"cases\":%u,\"admitted_narrow_framing\":%u,\"local_marker_limit_refused\":%u,\"strict_truncations\":%lu,\"actor_publication\":false,\"ack_permitted\":false}\n",checks,count,success,limit,cuts);return 0;
}
