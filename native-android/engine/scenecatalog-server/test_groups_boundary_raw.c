/* Original catalog/runtime/raw/world producers; quiet, owner and resources are
 * explicitly substituted orchestration providers, NOT actual runtime proofs. */
#include <strings.h>
#define strnicmp strncasecmp
/* ORIGINAL_PUBLIC_FUNCTIONS */
#include "source_public_bounds.inc"
#include "source_groups_eligibility.inc"
#include "source_groups_transaction.inc"
BOUNDARY_EXTRA_TYPES
#define COH_RESOURCE_RECORD_MAX (128u*1024u)
#define COH_RESOURCE_TOTAL_MAX (64u*1024u*1024u)
static unsigned checks,quiet,opened,committed,aborted,mode,fail_kind,raw_fail_at,raw_calls,cap_fault;
static unsigned char outputs[7][1u<<20],packet_copy[1u<<20];static unsigned counts[7],packet_bits;
int folder_cache_update_enable=0,folder_cache_manual_callback_check=1;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"boundaryraw line%d: %s\n",__LINE__,#x);abort();}}while(0)
int coh_resource_quiescence_begin(void){CHECK(!quiet);quiet=1;return 1;}
int coh_resource_quiescence_end(void){CHECK(quiet);quiet=0;return 1;}
static int coh_source_groups_prepare_owner(const NetLink*link,CohSourceGroupsOwner*out){CHECK(quiet&&link);memset(out,0,sizeof(*out));memcpy(out->wire,"fixture-owned-entity",20);memcpy(out->wire+120,&link->last_update_time,4);memcpy(out->wire+124,&link->last_world_id,4);return 1;}
static int coh_source_resources_export(CohSourceCatalogOutputFn fn,void*c,const unsigned char*header,const CohSourceCatalogExportReport*catalog,unsigned char*scratch,unsigned capacity,CohSourceResourceReport*out){unsigned char raw[192]={0};CHECK(quiet&&header&&catalog&&scratch&&capacity==131072);memset(out,0,sizeof(*out));out->total_bytes=out->emitted_bytes=192;return fn(c,raw,192)?0:5;}
#include "source_groups_boundary.inc"
static int sink_open(void*c,unsigned id){(void)c;CHECK(id&&quiet&&!opened);opened=1;return 1;}
static int sink_write(void*c,unsigned id,unsigned kind,const unsigned char*raw,unsigned bytes){(void)c;CHECK(opened&&id&&quiet&&kind>=1&&kind<=6&&bytes&&raw);if(kind==6){raw_calls++;if(raw_fail_at&&raw_calls==raw_fail_at)return 0;}if(kind==fail_kind)return 0;CHECK(bytes<=sizeof(outputs[kind])-counts[kind]);memcpy(outputs[kind]+counts[kind],raw,bytes);counts[kind]+=bytes;if(cap_fault&&kind==4)coh_groups_boundary.bytes=COH_GROUPS_BOUNDARY_MAX_BYTES-128u-bytes;return 1;}
static int sink_packet(void*c,unsigned id,const unsigned char*bytes,unsigned bits,unsigned aligned,unsigned compressed,const CohGroupsEligibilityReport*elig,const CohSourceCatalogExportReport*cat,const CohSourceSnapshotReport*snap,const CohSourceResourceReport*res,const CohSourcePublicBoundsReport*raw){unsigned at=96,f,s,publics=0;const unsigned char*p=outputs[6];(void)c;(void)res;CHECK(id&&quiet&&opened&&aligned==1&&compressed==1&&bits);CHECK(raw->status==0&&raw->total_bytes==counts[6]&&raw->emitted_bytes==counts[6]&&raw->files==cat->files&&raw->slots==cat->slots&&cat->total_bytes==counts[2]&&snap->total_bytes==counts[3]&&elig->records*64u==counts[5]);CHECK(!memcmp(p,"COHRBW01",8)&&coh_raw_bounds_u32(p+20)==id&&!memcmp(p+32,outputs[2],48));
 for(f=0;f<(unsigned)group_info.file_count;f++){
  GroupFile*file=group_info.files[f];CHECK(coh_raw_bounds_u32(p+at)==f&&coh_raw_bounds_u32(p+at+4)==f&&coh_raw_bounds_u32(p+at+8)==file->bounds_checksum);at+=24+coh_raw_bounds_u32(p+at+16);
  for(s=0;s<(unsigned)file->count;s++){
   GroupDef*d=file->defs[s];unsigned selected=coh_raw_bounds_u32(p+at+16),names=coh_raw_bounds_u32(p+at+20),n=coh_raw_bounds_u32(p+at+24);CHECK(coh_raw_bounds_u32(p+at)==s&&selected==(unsigned)groupIsPublic(d));at+=32+names;if(selected){CHECK(n==60&&!memcmp(p+at,d->min,60)&&(p[at+59]&0x80));publics++;}else CHECK(!n);at+=n;
  }
 }
 CHECK(at==counts[6]&&publics==raw->public_rows);
 /* Eligibility observes force_reload before the original serializer resets it. */
 CHECK(coh_raw_bounds_u32(outputs[5]+64)==2&&coh_raw_bounds_u32(outputs[5]+68)==1&&coh_raw_bounds_u32(outputs[5]+76)==1&&!group_info.files[1]->force_reload);
 CHECK((bits+7u)/8u<=sizeof(packet_copy));memcpy(packet_copy,bytes,(bits+7u)/8u);packet_bits=bits;return mode!=1;
}
static int sink_commit(void*c,unsigned id){(void)c;CHECK(id&&!quiet&&opened);committed++;opened=0;return 1;}
static void sink_abort(void*c,unsigned id){(void)c;CHECK(id&&!quiet&&opened);aborted++;opened=0;}
static void setup(void){CohGroupsBoundarySink sink={sink_open,sink_write,sink_packet,sink_commit,sink_abort,NULL};unsigned f,i;
 CHECK(!quiet&&!opened);memset(&coh_groups_boundary,0,sizeof(coh_groups_boundary));memset(&coh_groups_transaction_hooks,0,sizeof(coh_groups_transaction_hooks));coh_groups_transaction_active=0;committed=aborted=mode=fail_kind=raw_fail_at=raw_calls=cap_fault=packet_bits=0;memset(counts,0,sizeof(counts));
 snapshot_setup(0,0);for(f=0;f<(unsigned)group_info.file_count;f++){GroupFile*file=group_info.files[f];file->idx=(int)f;for(i=0;i<(unsigned)file->count;i++)if(file->defs[i])((unsigned char*)file->defs[i]->min)[59]|=0x80;}group_info.files[1]->force_reload=1;CHECK(coh_groups_boundary_prepare(&sink,&coh_groups_transaction_hooks));CHECK(!quiet&&!opened);}
BOUNDARY_ORIGINAL_WORLD
int main(void){NetLink link={0};unsigned n,total_raw_calls;setup();link.last_update_time=0;link.last_world_id=0;worldSendUpdate(&link,1);CHECK(committed==1&&!aborted&&!quiet&&!opened&&packet_bits==oracle_packet.stream.bitLength&&!memcmp(packet_copy,oracle_storage,(packet_bits+7)/8));total_raw_calls=raw_calls;CHECK(total_raw_calls>5);
 for(n=1;n<=total_raw_calls;n++){setup();raw_fail_at=n;link.last_update_time=0;link.last_world_id=0;worldSendUpdate(&link,1);CHECK(aborted==1&&!committed&&!quiet&&!opened&&raw_calls==n);}
 for(n=1;n<=6;n++){setup();fail_kind=n;link.last_update_time=0;link.last_world_id=0;worldSendUpdate(&link,1);CHECK(aborted==1&&!committed&&!quiet&&!opened);}
 setup();cap_fault=1;link.last_update_time=0;link.last_world_id=0;worldSendUpdate(&link,1);CHECK(aborted==1&&!committed&&!quiet&&!raw_calls&&!counts[6]);
 setup();group_info.files[1]->idx=0;link.last_update_time=0;link.last_world_id=0;worldSendUpdate(&link,1);CHECK(aborted==1&&!committed&&!quiet&&!counts[6]);
 setup();mode=1;link.last_update_time=0;link.last_world_id=0;worldSendUpdate(&link,1);CHECK(aborted==1&&!committed&&!quiet&&counts[6]);
 printf("{\"passed\":true,\"checks\":%u,\"raw_callback_faults\":%u,\"original_catalog_runtime_raw_world_executed\":true,\"quiet_owner_resource_dependencies_substituted\":true,\"actual_capture_count\":0,\"win32_layout_verified\":false,\"world_authority\":false}\n",checks,total_raw_calls);return 0;}
