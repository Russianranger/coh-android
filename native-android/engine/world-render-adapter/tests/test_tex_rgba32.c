#include "../coh_wr_tex_rgba32.c"
#include "tex_rgba32_fixture.h"
#include <openssl/sha.h>
#include <stdio.h>
static uint32_t checks,comparisons,holds,drops,allocations,fail_allocation,polls,stop_at,hash_failure,reentry,read_failure,hash_mismatch,two_rows;
static CohWrTexNamespace*observed;
static void*live_calloc[4096];static uint32_t live_count;
static uint8_t*watched_candidate;static size_t watched_bytes;static uint8_t final_pixel[4];static uint32_t cancel_after_written;
static uint32_t authentic_case;static size_t grey_owned[4],grey_aggregate[4],grey_source_aggregate[4],maximum_owned;
typedef struct {uint8_t*data;size_t size;} Memory;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"rgba32 line%d %s\n",__LINE__,#x);exit(1);}}while(0)
void*__real_calloc(size_t,size_t);
void __real_free(void*);
void*__wrap_calloc(size_t n,size_t size){allocations++;if(fail_allocation&&allocations==fail_allocation)return NULL;void*p=__real_calloc(n,size);if(p){CHECK(live_count<4096);live_calloc[live_count++]=p;if(watched_bytes&&n==1&&size==watched_bytes)watched_candidate=p;}return p;}
void __wrap_free(void*p){if(p==watched_candidate)watched_candidate=NULL;for(uint32_t i=0;i<live_count;i++)if(live_calloc[i]==p){live_calloc[i]=live_calloc[--live_count];break;}__real_free(p);}
static void put(uint8_t*p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static CohStatus readat(void*v,uint64_t at,void*out,size_t n){Memory*m=v;if(read_failure)return COH_IO;if(at>m->size||n>m->size-at)return COH_IO;memcpy(out,m->data+(size_t)at,n);return COH_OK;}
static CohStatus digest(void*v,CohBytes b,uint8_t out[32]){(void)v;if(hash_failure)return COH_IO;SHA256(b.data,b.size,out);if(hash_mismatch)out[0]^=1;return COH_OK;}
static CohStatus hold(void*v){(void)v;holds++;return COH_OK;}
static void drop(void*v){(void)v;drops++;}
static int cancel(void*v){(void)v;polls++;if(reentry){CohWrTexNamespace*before=observed;CHECK(coh_wr_tex_namespace_destroy(&observed)==COH_STATE&&observed==before);}if(cancel_after_written&&watched_candidate){CohWrTexRgba32*candidate=(CohWrTexRgba32*)watched_candidate;if(candidate->view.mip_count){CohWrTexRgba32Mip*last=candidate->view.mips+candidate->view.mip_count-1;if(last->rgba.data&&last->rgba.size>=4&&!memcmp(last->rgba.data+last->rgba.size-4,final_pixel,4))return 1;}}return stop_at&&polls==stop_at;}
static CohWrTexNamespace*namespace_for(Memory*m){
 CohWrTexNamespaceFile f[2]={{"texture_library/world/filler/grey.texture",11,0,{readat,m,m->size,7}},{"texture_library/zz/grey.texture",11,0,{readat,m,m->size,7}}};
 CohWrTexNamespaceRoot root={f,two_rows?2:1,7,"/actual/immutable/native/data"};
 CohWrTexNamespaceRequest q={0};q.roots=&root;q.root_count=1;q.input_generation=33;q.mode=COH_WR_TEX_NS_I_LIKE_PIGS;q.development_data=1;q.digest=digest;q.provider_hold=hold;q.provider_drop=drop;
 CohWrTexNamespaceLimits lim={0};lim.owned_limit=1024*1024;lim.aggregate_limit=8*1024*1024;lim.external_bytes=m->size+sizeof(*m)+256*1024;lim.record_limit=64;lim.node_limit=64;lim.basic_limit=4;lim.body_lease_limit=1;lim.loader=(CohAssetLimits){1024*1024,128*1024,128*1024,128*1024,8,2,1};
 CohWrTexNamespace*r=NULL;CHECK(coh_wr_tex_namespace_build(&q,&lim,(CohCancel){0},&r)==COH_OK);return r;
}
static CohWrTexRgba32Limits limits_for(CohWrTexNamespace*r){CohWrTexNamespaceReport s;CHECK(coh_wr_tex_namespace_report(r,&s)==COH_OK);return(CohWrTexRgba32Limits){1024*1024,16*1024*1024,s.aggregate_reserved_bytes};}
static Memory controlled(uint32_t w,uint32_t h,uint32_t base_only,uint32_t seed){
 uint32_t levels=1,t=w>h?w:h;while(t>1){levels++;t>>=1;}if(base_only)levels=1;
 size_t payload=128;uint32_t x=w,y=h;for(uint32_t i=0;i<levels;i++){payload+=(size_t)x*y*4;x=x>1?x/2:1;y=y>1?y/2:1;}
 const char*name="texture_library/world/filler/grey.dds";size_t head=32+strlen(name)+1+3;
 Memory m={calloc(1,head+payload),head+payload};CHECK(m.data);put(m.data,(uint32_t)head);put(m.data+4,(uint32_t)payload);put(m.data+8,w);put(m.data+12,h);memcpy(m.data+29,"TX2",3);memcpy(m.data+32,name,strlen(name)+1);memcpy(m.data+head-3,"TX2",3);
 uint8_t*p=m.data+head;memcpy(p,"DDS ",4);put(p+4,124);put(p+8,0x81007);put(p+12,h);put(p+16,w);put(p+20,w*h*4);put(p+28,base_only?0:levels);put(p+76,32);put(p+80,0x41);put(p+88,32);put(p+92,0xff0000);put(p+96,0xff00);put(p+100,0xff);put(p+104,0xff000000);put(p+108,0x401008);
 for(size_t i=128;i<payload;i++){seed=seed*1664525u+1013904223u;p[i]=(uint8_t)(seed>>24);}return m;
}
static void check_case(Memory*m,uint32_t skip){
 uint8_t before[32],after[32];SHA256(m->data,m->size,before);CohWrTexNamespace*r=namespace_for(m);CohWrTexRgba32Limits lim=limits_for(r);CohWrTexRgba32*out=NULL;CHECK(coh_wr_tex_rgba32_build(r,0,skip,&lim,(CohCancel){0},&out)==COH_OK&&out);
 CohWrTexRgba32View v;CHECK(coh_wr_tex_rgba32_view(out,&v)==COH_OK);CHECK(v.source_row==0&&v.source_input_generation==33&&v.asset.generation==7&&!strcmp(v.asset.path,"texture_library/world/filler/grey.texture")&&!memcmp(v.sha256,before,32));
 if(v.owned_bytes>maximum_owned)maximum_owned=v.owned_bytes;
 if(authentic_case){grey_owned[authentic_case-1]=v.owned_bytes;grey_aggregate[authentic_case-1]=v.aggregate_reserved_bytes;grey_source_aggregate[authentic_case-1]=lim.external_bytes;}
 size_t head=word(m->data);Rgba32Oracle oracle[2];for(int bgra=0;bgra<2;bgra++){
  CHECK(original_rgba32((CohBytes){m->data+head,m->size-head},skip,bgra,&oracle[bgra]));CHECK(oracle[bgra].format==7&&oracle[bgra].count==v.mip_count&&oracle[bgra].source_mip_count==v.source_mip_count-skip);size_t total=0;
  for(uint32_t i=0;i<v.mip_count;i++){comparisons++;CHECK(v.mips[i].width==oracle[bgra].mips[i].width&&v.mips[i].height==oracle[bgra].mips[i].height&&v.mips[i].rgba.size==oracle[bgra].mips[i].bytes&&v.mips[i].source_level==i+skip);CHECK(!memcmp(v.mips[i].rgba.data,oracle[bgra].rgba+oracle[bgra].mips[i].offset,v.mips[i].rgba.size));total+=v.mips[i].rgba.size;}CHECK(total==oracle[bgra].bytes);
 }
 CHECK(!memcmp(&oracle[0],&oracle[1],sizeof(oracle[0])));SHA256(m->data,m->size,after);CHECK(!memcmp(before,after,32));
 /* Success copied pixels/identity: source owner/provider can actually retire. */
 CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK&&!r);memset(m->data,0,m->size);CHECK(coh_wr_tex_rgba32_view(out,&v)==COH_OK);for(uint32_t i=0;i<v.mip_count;i++)CHECK(!memcmp(v.mips[i].rgba.data,oracle[0].rgba+oracle[0].mips[i].offset,v.mips[i].rgba.size));
 CohWrTexRgba32View old;memset(&old,0xa5,sizeof(old));CohWrTexRgba32View sentinel=old;CHECK(coh_wr_tex_rgba32_view(NULL,&old)==COH_INVALID&&!memcmp(&old,&sentinel,sizeof(old)));CHECK(coh_wr_tex_rgba32_view(out,(CohWrTexRgba32View*)out)==COH_INVALID);
 /* A REAL owner handle stored inside its own allocation, not a forged handle. */
 out->view.asset.path=(const char*)out;CHECK(coh_wr_tex_rgba32_destroy((CohWrTexRgba32**)out)==COH_INVALID);out->view.asset.path=out->path;CHECK(coh_wr_tex_rgba32_destroy(&out)==COH_OK&&!out);
}
static void expect_refusal(Memory*m,CohStatus wanted,uint32_t skip){CohWrTexNamespace*r=namespace_for(m);CohWrTexRgba32Limits lim=limits_for(r);CohWrTexRgba32*out=NULL;CHECK(coh_wr_tex_rgba32_build(r,0,skip,&lim,(CohCancel){0},&out)==wanted&&!out);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);}
int main(int argc,char**argv){
 CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f);Memory grey={malloc(894),894};CHECK(grey.data&&fread(grey.data,1,894,f)==894&&fgetc(f)==EOF&&fclose(f)==0);uint8_t*saved=malloc(894);CHECK(saved);memcpy(saved,grey.data,894);
 for(uint32_t skip=0;skip<4;skip++){authentic_case=skip+1;memcpy(grey.data,saved,894);check_case(&grey,skip);}authentic_case=0;free(saved);free(grey.data);
 for(uint32_t w=1;w<=64;w=w<8?w+1:w*2)for(uint32_t h=1;h<=64;h=h<8?h+1:h*2)for(uint32_t base=0;base<2;base++){
  uint32_t count=1,t=w>h?w:h;while(t>1){count++;t>>=1;}if(base)count=1;
  for(uint32_t skip=0;skip<count;skip++){Memory m=controlled(w,h,base,w*1009+h*101+skip);check_case(&m,skip);free(m.data);}
 }
 /* Distinct refusal for original-assumed-but-noncanonical masks, padding,
  * nonterminating chains, dimensional mismatch and non2D formats. */
 const uint32_t offsets[]={4,76,80,84,88,92,96,100,104,24,112,28,16,12,20};
 const uint32_t values[]={123,31,0x40,0x30315844,24,0xff,0xff0000,0xff00,0,2,0x200,2,4,4,17};
 const CohStatus statuses[]={COH_INVALID,COH_INVALID,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_UNSUPPORTED,COH_INVALID,COH_INVALID,COH_UNSUPPORTED};
 for(size_t i=0;i<sizeof(offsets)/sizeof(*offsets);i++){Memory m=controlled(8,8,0,1);put(m.data+word(m.data)+offsets[i],values[i]);expect_refusal(&m,statuses[i],0);free(m.data);}
 Memory m=controlled(8,8,0,9);expect_refusal(&m,COH_INVALID,4);m.data[word(m.data)]='X';expect_refusal(&m,COH_INVALID,0);free(m.data);
 m=controlled(8,8,0,9);m.size--;expect_refusal(&m,COH_INVALID,0);free(m.data);
 m=controlled(8,8,0,9);put(m.data+4,word(m.data+4)-4);expect_refusal(&m,COH_INVALID,0);free(m.data);
 m=controlled(8,8,0,9);m.size-=4;put(m.data+4,word(m.data+4)-4);expect_refusal(&m,COH_INVALID,0);free(m.data);
 m=controlled(8,8,0,9);uint8_t*larger=malloc(m.size+1);CHECK(larger);memcpy(larger,m.data,m.size);free(m.data);m.data=larger;m.data[m.size++]=0;put(m.data+4,word(m.data+4)+1);expect_refusal(&m,COH_INVALID,0);free(m.data);
 m=controlled(8,8,0,9);put(m.data+word(m.data)+28,0);expect_refusal(&m,COH_INVALID,0);free(m.data);
 m=controlled(8,8,0,9);uint32_t head=word(m.data);put(m.data+head+8,0x100f);put(m.data+head+20,8*4);check_case(&m,0);free(m.data);
 m=controlled(8,8,0,9);CohWrTexNamespace*r=namespace_for(&m);CohWrTexRgba32Limits lim=limits_for(r);CohWrTexRgba32*out=NULL;observed=r;reentry=1;polls=0;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){cancel,NULL},&out)==COH_OK);uint32_t cancel_points=polls;CHECK(cancel_points>15);CHECK(coh_wr_tex_rgba32_destroy(&out)==COH_OK);
 for(uint32_t i=1;i<=cancel_points;i++){polls=0;stop_at=i;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){cancel,NULL},&out)==COH_CANCELLED&&!out);}stop_at=0;reentry=0;observed=NULL;
 /* Independently trigger cancellation AFTER the final actual pixel store.
  * Merely rediscovering poll counts would miss a removed final poll. */
 memcpy(final_pixel,m.data+m.size-4,4);uint8_t red=final_pixel[2];final_pixel[2]=final_pixel[0];final_pixel[0]=red;CHECK(final_pixel[0]||final_pixel[1]||final_pixel[2]||final_pixel[3]);watched_bytes=sizeof(*out)+340;cancel_after_written=1;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){cancel,NULL},&out)==COH_CANCELLED&&!out&&!watched_candidate);cancel_after_written=0;watched_bytes=0;
 allocations=0;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},&out)==COH_OK);uint32_t allocation_points=allocations;CohWrTexRgba32View v;CHECK(coh_wr_tex_rgba32_view(out,&v)==COH_OK);CHECK(coh_wr_tex_rgba32_destroy(&out)==COH_OK);
 for(uint32_t i=1;i<=allocation_points;i++){allocations=0;fail_allocation=i;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},&out)==COH_LIMIT&&!out);}fail_allocation=0;
 CohWrTexRgba32Limits bad=lim;bad.owned_limit=v.owned_bytes-1;CHECK(coh_wr_tex_rgba32_build(r,0,0,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);bad=lim;bad.aggregate_limit=v.aggregate_reserved_bytes-1;CHECK(coh_wr_tex_rgba32_build(r,0,0,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);bad=lim;bad.external_bytes--;CHECK(coh_wr_tex_rgba32_build(r,0,0,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);bad=lim;bad.external_bytes=SIZE_MAX;CHECK(coh_wr_tex_rgba32_build(r,0,0,&bad,(CohCancel){0},&out)==COH_LIMIT&&!out);
 CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},(CohWrTexRgba32**)&lim)==COH_INVALID);CHECK(coh_wr_tex_rgba32_build(r,1,0,&lim,(CohCancel){0},&out)==COH_NOT_FOUND&&!out);
 hash_failure=1;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},&out)==COH_IO&&!out);hash_failure=0;hash_mismatch=1;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},&out)==COH_INVALID&&!out);hash_mismatch=0;
 const CohWrTexNamespaceBody*lease=NULL;CHECK(coh_wr_tex_namespace_acquire(r,0,(CohCancel){0},&lease)==COH_OK);CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},&out)==COH_LIMIT&&!out);CHECK(coh_wr_tex_namespace_release(r,&lease)==COH_OK);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);free(m.data);
 m=controlled(8,8,0,9);two_rows=1;r=namespace_for(&m);two_rows=0;lim=limits_for(r);read_failure=1;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},&out)==COH_IO&&!out);read_failure=0;CHECK(coh_wr_tex_rgba32_build(r,0,0,&lim,(CohCancel){0},&out)==COH_OK);CHECK(coh_wr_tex_rgba32_destroy(&out)==COH_OK);CHECK(coh_wr_tex_namespace_destroy(&r)==COH_OK);free(m.data);CHECK(holds==drops);
 CHECK(!live_count);printf("{\"checks\":%u,\"original_mip_comparisons\":%u,\"authentic_grey_skip_cases\":4,\"allocation_failure_points\":%u,\"cancellation_failure_points\":%u,\"source_provider_holds\":%u,\"source_provider_drops\":%u,\"tracked_calloc_blocks_still_live\":%u,\"source_owner_actually_retired_after_copy\":true,\"grey_owned_bytes_by_skip\":[%zu,%zu,%zu,%zu],\"grey_aggregate_reserved_bytes_by_skip\":[%zu,%zu,%zu,%zu],\"grey_source_full_aggregate_reservation_by_skip\":[%zu,%zu,%zu,%zu],\"maximum_controlled_owned_bytes\":%zu}\n",checks,comparisons,allocation_points,cancel_points,holds,drops,live_count,grey_owned[0],grey_owned[1],grey_owned[2],grey_owned[3],grey_aggregate[0],grey_aggregate[1],grey_aggregate[2],grey_aggregate[3],grey_source_aggregate[0],grey_source_aggregate[1],grey_source_aggregate[2],grey_source_aggregate[3],maximum_owned);return 0;
}
