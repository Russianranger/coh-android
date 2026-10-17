#include "source_groups_eligibility.inc"
#include "source_groups_transaction.inc"
static unsigned checks,seen,fail_at;
static unsigned hook_begins,hook_ends,hook_aborts,hook_bits,hook_mode,hook_compress,hook_refuse;
static unsigned char hook_wire[1<<20];
static unsigned hook_begin(void*c,const NetLink*l,int full){(void)c;assert(l->last_world_id!=world_id);assert(full==1);hook_begins++;return 81;}
static int hook_finish(void*c,unsigned id,const unsigned char*p,unsigned bits,unsigned aligned,unsigned compress,const CohGroupsEligibilityReport*r){(void)c;assert(id==81&&r->records==seen);assert((bits+7)/8<sizeof(hook_wire));memcpy(hook_wire,p,(bits+7)/8);hook_bits=bits;hook_mode=aligned;hook_compress=compress;hook_ends++;return !hook_refuse;}
static void hook_abort(void*c,unsigned id){(void)c;assert(id==81);hook_aborts++;}
static unsigned char records[1024][64],actual[4096];
static unsigned word(const unsigned char*p,unsigned n){p+=n*4;return (unsigned)p[0]|((unsigned)p[1]<<8)|((unsigned)p[2]<<16)|((unsigned)p[3]<<24);}
static int write_record(void*ctx,const unsigned char*raw,unsigned n){(void)ctx;assert(n==64&&seen<1024);if(fail_at&&seen+1==fail_at)return 0;memcpy(records[seen++],raw,n);return 1;}
#define CHECK(x) do {assert(x);checks++;}while(0)
int main(void){
 unsigned tmpbits,footer[4],f,d,full,force,modified,saved,idx,live,ft,dt,lt,actual_bits,expected_bits,mod,expected_mod,n;NetLink link;GroupFile before;GroupDef defbefore;CohGroupsEligibilityReport out,guard;Packet*p;
 unsigned times[3]={0,1,0xffffffffu};unsigned char setup[1<<20];CHECK(groups_original(1,1,0,setup,&tmpbits,footer));
 for(full=0;full<2;full++)for(force=0;force<2;force++)for(modified=0;modified<2;modified++)for(saved=0;saved<2;saved++)for(idx=0;idx<2;idx++)for(live=0;live<2;live++)for(ft=0;ft<3;ft++)for(dt=0;dt<3;dt++)for(lt=0;lt<3;lt++){
  GroupFile*file=&oracle_files[0];GroupDef*def=&oracle_defs[0];
  file->force_reload=force;file->modified_on_disk=modified;file->mod_time=times[ft];def->mod_time=times[dt];def->saved=saved;def->file_idx=idx;def->in_use=live;link.last_update_time=times[lt];link.last_world_id=world_id;
  before=*file;defbefore=*def;seen=fail_at=0;memset(&out,0xcc,sizeof(out));CHECK(coh_source_groups_eligibility(&link,full,7,write_record,NULL,&out));CHECK(!memcmp(&before,file,sizeof(before))&&!memcmp(&defbefore,def,sizeof(defbefore)));CHECK(out.records==5&&seen==5&&word(records[0],4)==times[lt]&&word(records[2],7)==live);
  p=pktCreate();mod=0;sendGroupFile(file,&link,full,p,&mod);actual_bits=p->stream.bitLength;CHECK((actual_bits+7)/8<sizeof(actual));memcpy(actual,oracle_storage,(actual_bits+7)/8);*file=before;
  p=pktCreate();expected_mod=0;f=word(records[1],7);d=word(records[2],8);pktSendBits(p,1,f);
  if(f){pktSendString(p,file->fullname);pktSendBits(p,32,file->bounds_checksum);pktSendBits(p,1,0);if(d){if(def->mod_time>expected_mod)expected_mod=def->mod_time;sendDef(p,def);}pktSendBitsPack(p,1,0);}
  expected_bits=p->stream.bitLength;CHECK(actual_bits==expected_bits&&!memcmp(actual,oracle_storage,(actual_bits+7)/8)&&mod==expected_mod);CHECK(file->force_reload==before.force_reload);
 }
 seen=0;fail_at=0;link.last_update_time=0;link.last_world_id=0;CHECK(coh_source_groups_eligibility(&link,1,9,write_record,NULL,&out));n=seen;
 for(f=1;f<=n;f++){memset(&out,0xa5,sizeof(out));guard=out;seen=0;fail_at=f;CHECK(!coh_source_groups_eligibility(&link,1,9,write_record,NULL,&out)&&!memcmp(&out,&guard,sizeof(out)));}
 fail_at=0;g_isBaseRaid=1;seen=0;CHECK(!coh_source_groups_eligibility(&link,1,9,write_record,NULL,&out)&&!seen);g_isBaseRaid=0;
 oracle_files[0].base=&g_base;CHECK(!coh_source_groups_eligibility(&link,1,9,write_record,NULL,&out)&&!seen);oracle_files[0].base=NULL;
 CHECK(!coh_source_groups_eligibility(&link,2,9,write_record,NULL,&out));CHECK(!coh_source_groups_eligibility(&link,1,0,write_record,NULL,&out));
 seen=0;fail_at=0;{GroupDef*save=oracle_files[0].defs[0];oracle_files[0].defs[0]=NULL;guard=out;CHECK(!coh_source_groups_eligibility(&link,1,9,write_record,NULL,&out)&&!seen&&!memcmp(&guard,&out,sizeof(out)));oracle_files[0].defs[0]=save;}
 {int save=group_info.ref_count;group_info.ref_count=65537;CHECK(!coh_source_groups_eligibility(&link,1,9,write_record,NULL,&out)&&!seen);group_info.ref_count=save;}
 coh_groups_transaction_hooks.begin=hook_begin;coh_groups_transaction_hooks.record=write_record;coh_groups_transaction_hooks.finish=hook_finish;coh_groups_transaction_hooks.abort=hook_abort;
 seen=fail_at=0;CHECK(groups_original(8,1,0,setup,&tmpbits,footer));CHECK(hook_begins==1&&hook_ends==1&&!hook_aborts&&!coh_groups_transaction_active);CHECK(tmpbits==hook_bits&&hook_mode==1&&hook_compress==1&&!memcmp(setup,hook_wire,(tmpbits+7)/8));
 /* Exact source-order pre-state captured before force_reload reset. */
 CHECK(word(records[1],0)==2&&word(records[1],1)==1&&word(records[1],3)==1&&oracle_files[1].force_reload==0);
 seen=0;fail_at=2;CHECK(groups_original(8,1,0,setup,&tmpbits,footer));CHECK(hook_begins==2&&hook_ends==1&&hook_aborts==1&&!coh_groups_transaction_active);
 seen=fail_at=0;hook_refuse=1;CHECK(groups_original(8,1,0,setup,&tmpbits,footer));CHECK(hook_begins==3&&hook_ends==2&&hook_aborts==2&&!coh_groups_transaction_active);
 coh_groups_transaction_active=81;oracle_packet.stream.bitLength=0xffffffffu;coh_groups_transaction_finish(&oracle_packet);CHECK(hook_aborts==3&&!coh_groups_transaction_active&&hook_ends==2);
 printf("{\"checks\":%u,\"producer_cases\":1728,\"shipping_changed\":false,\"live_groups_captured\":false}\n",checks);return 0;
}
