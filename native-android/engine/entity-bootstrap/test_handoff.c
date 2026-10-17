#include "../dbclient/coh_dbclient.h"
#include "source_fixtures.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks,cuts,mutations;
#define CHECK(v) do{checks++;if(!(v)){fprintf(stderr,"handoff source check%d: %s\n",__LINE__,#v);exit(1);}}while(0)
int main(void){
 for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++){
  const Fixture*f=&fixtures[i];CohAuthMapHandoff out={0},old;CHECK(coh_db_map_handoff_parse((CohBytes){f->data,f->bytes},f->bits,f->aligned,f->legacy,&out)==COH_OK);CHECK(out.link_id==f->words[0]&&out.map_id==f->words[1]&&out.address[0]==f->words[2]&&out.address[1]==f->words[3]&&out.udp_port==f->words[4]&&out.tcp_port==f->words[5]&&out.cookie==f->words[6]);
  for(size_t bit=0;bit<f->bits;bit++){memset(&out,0xa5,sizeof(out));old=out;CHECK(coh_db_map_handoff_parse((CohBytes){f->data,f->bytes},bit,f->aligned,f->legacy,&out)!=COH_OK);CHECK(!memcmp(&out,&old,sizeof(out)));cuts++;}
  uint8_t bad[128];CHECK(f->bytes<=sizeof(bad));for(size_t j=0;j<f->bytes;j++){memcpy(bad,f->data,f->bytes);bad[j]^=0x80;memset(&out,0xa5,sizeof(out));old=out;CohStatus s=coh_db_map_handoff_parse((CohBytes){bad,f->bytes},f->bits,f->aligned,f->legacy,&out);if(s!=COH_OK)CHECK(!memcmp(&out,&old,sizeof(out)));mutations++;}
 }
 printf("{\"passed\":true,\"checks\":%u,\"source_fixtures\":%zu,\"truncations\":%u,\"byte_mutations\":%u,\"generic_field_not_identity_authority\":true}\n",checks,sizeof(fixtures)/sizeof(fixtures[0]),cuts,mutations);return 0;}
