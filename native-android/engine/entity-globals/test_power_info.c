#include "coh_power_info.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {const unsigned char*bytes;size_t size,bits;unsigned aligned,prefix,scenario;uint64_t expected;}Fixture;
#include "power_info_fixtures.h"
static unsigned checks,truncations,mutations,randomized;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"PowerInfo check %s:%d: %s\n",__FILE__,__LINE__,#x);abort();}}while(0)
static CohPowerInfoUpdate*out,*before;static CohPowerInfoWorkspace*work;
static uint64_t hash(const void*p,size_t n){const unsigned char*b=p;uint64_t h=UINT64_C(14695981039346656037);for(size_t i=0;i<n;i++){h^=b[i];h*=UINT64_C(1099511628211);}return h;}
static CohStatus parse(CohRepReader*r,size_t retained,size_t limit){return coh_global_power_info(r,out,work,retained,limit);}
static void refused(CohRepReader*r,size_t retained,size_t limit){CohRepReader saved=*r;memcpy(before,out,sizeof(*out));CHECK(parse(r,retained,limit)!=COH_OK);CHECK(!memcmp(r,&saved,sizeof(saved)));CHECK(!memcmp(out,before,sizeof(*out)));}
static void fixture(const Fixture*f){
    CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->bytes,f->size},f->bits,f->aligned,65536)==COH_OK);r.cursor=f->prefix;
    CHECK(parse(&r,0,COH_POWER_INFO_LIMIT)==COH_OK);CHECK(r.cursor==f->bits);CHECK(out->end_bit==f->bits&&out->begin_bit==f->prefix);
    if(hash(out,sizeof(*out))!=f->expected)fprintf(stderr,"fixture scenario%u aligned%u prefix%u hash=%llu expected=%llu size=%zu\n",f->scenario,f->aligned,f->prefix,(unsigned long long)hash(out,sizeof(*out)),(unsigned long long)f->expected,sizeof(*out));
    CHECK(hash(out,sizeof(*out))==f->expected);
    if(f->scenario<2){CHECK(out->has_updates==0);CHECK(out->range_count==(f->scenario?2u:0u));}
    if(f->scenario==5)CHECK(out->ranges[0].crc==0); /* Original basepower_Send(NULL/CRC0) consumes a word. */
    size_t exact=sizeof(*out)+sizeof(*work)+8192u+f->size;
    r.cursor=f->prefix;refused(&r,0,exact-1);CHECK(parse(&r,0,exact)==COH_OK);
    r.cursor=f->prefix;refused(&r,1,exact);CHECK(parse(&r,1,exact+1)==COH_OK);
    for(size_t cut=f->prefix;cut<f->bits;cut++){
        CHECK(coh_rep_reader_bounded(&r,(CohBytes){f->bytes,f->size},cut,f->aligned,65536)==COH_OK);r.cursor=f->prefix;refused(&r,0,COH_POWER_INFO_LIMIT);truncations++;
    }
    unsigned char*copy=malloc(f->size+3);CHECK(copy);memcpy(copy,f->bytes,f->size);memset(copy+f->size,0,3);
    for(unsigned i=0;i<16;i++){size_t bit=f->bits+i;unsigned mask=1u<<(bit%8);if((0xa55au>>i)&1)copy[bit/8]|=(unsigned char)mask;else copy[bit/8]&=(unsigned char)~mask;}
    CHECK(coh_rep_reader_bounded(&r,(CohBytes){copy,f->size+3},f->bits+16,f->aligned,65536)==COH_OK);r.cursor=f->prefix;CHECK(parse(&r,0,COH_POWER_INFO_LIMIT)==COH_OK);uint32_t tail;CHECK(coh_rep_read(&r,16,&tail)==COH_OK&&tail==0xa55a);
    for(size_t i=0;i<f->size;i++){
        memcpy(copy,f->bytes,f->size);copy[i]^=0x80;CHECK(coh_rep_reader_bounded(&r,(CohBytes){copy,f->size},f->bits,f->aligned,65536)==COH_OK);r.cursor=f->prefix;CohRepReader saved=r;memcpy(before,out,sizeof(*out));CohStatus s=parse(&r,0,COH_POWER_INFO_LIMIT);if(s!=COH_OK){CHECK(!memcmp(&r,&saved,sizeof(r)));CHECK(!memcmp(out,before,sizeof(*out)));}else CHECK(r.cursor<=f->bits);mutations++;
    }free(copy);
}
typedef struct {unsigned char data[65536];size_t bits;unsigned aligned;}Writer;
static void put(Writer*w,unsigned n,uint32_t v){if(w->aligned)n=(n+7)&~7u;for(unsigned i=0;i<n;i++){size_t b=w->bits++;CHECK(b<sizeof(w->data)*8);if((v>>i)&1)w->data[b/8]|=(unsigned char)(1u<<(b%8));}}
static void pack(Writer*w,unsigned n,uint32_t v){if(w->aligned){put(w,32,v);return;}while(n<32&&v>=((1u<<n)-1)){uint32_t m=(1u<<n)-1;put(w,n,m);v-=m;n=n*2>32?32:n*2;}put(w,n,v);}
static void automatic(Writer*w,uint32_t v){unsigned b=v<4?0:v<1024?1:v<(1u<<24)?2:3;static const unsigned widths[]={2,10,24,32};put(w,2,b);put(w,widths[b],v);}
static void writer_refuse(Writer*w){CohRepReader r;CHECK(coh_rep_reader_bounded(&r,(CohBytes){w->data,(w->bits+7)/8},w->bits,w->aligned,65536)==COH_OK);refused(&r,0,COH_POWER_INFO_LIMIT);}
static void negatives(void){
    for(unsigned aligned=0;aligned<2;aligned++){
        Writer w={.aligned=aligned};put(&w,1,1);put(&w,4,8);writer_refuse(&w);
        memset(&w,0,sizeof(w));w.aligned=aligned;put(&w,1,1);put(&w,4,0);put(&w,1,0);pack(&w,1,COH_POWER_INFO_DEFINITIONS+1);writer_refuse(&w);
        memset(&w,0,sizeof(w));w.aligned=aligned;put(&w,1,0);for(unsigned i=0;i<=COH_POWER_INFO_EVENTS;i++){put(&w,1,1);automatic(&w,i);put(&w,32,0);}put(&w,1,0);writer_refuse(&w);
        memset(&w,0,sizeof(w));w.aligned=aligned;put(&w,1,0);put(&w,1,1);automatic(&w,0);put(&w,32,0x7fc00000);put(&w,1,0);writer_refuse(&w);
    }
    const Fixture*f=&fixtures[0];CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){f->bytes,f->size},f->bits,0)==COH_OK);
    memcpy(before,out,sizeof(*out));CohRepReader saved=r;CHECK(coh_global_power_info(&r,out,(CohPowerInfoWorkspace*)out,0,COH_POWER_INFO_LIMIT)==COH_INVALID);CHECK(!memcmp(out,before,sizeof(*out))&&!memcmp(&r,&saved,sizeof(r)));
    CHECK(coh_global_power_info((CohRepReader*)out,out,work,0,COH_POWER_INFO_LIMIT)==COH_INVALID);CHECK(!memcmp(out,before,sizeof(*out)));
    CHECK(coh_global_power_info(&r,(CohPowerInfoUpdate*)f->bytes,work,0,COH_POWER_INFO_LIMIT)==COH_INVALID);CHECK(!memcmp(&r,&saved,sizeof(r)));
    CHECK(coh_global_power_info(NULL,out,work,0,COH_POWER_INFO_LIMIT)==COH_INVALID);
    uint32_t seed=0x52415750;unsigned char bytes[64];
    for(unsigned j=0;j<2000;j++){
        for(unsigned i=0;i<sizeof(bytes);i++){seed=seed*1664525u+1013904223u;bytes[i]=(unsigned char)(seed>>24);}
        CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},seed%513,j%2)==COH_OK);saved=r;memcpy(before,out,sizeof(*out));CohStatus s=parse(&r,0,COH_POWER_INFO_LIMIT);if(s!=COH_OK){CHECK(!memcmp(&r,&saved,sizeof(r)));CHECK(!memcmp(out,before,sizeof(*out)));}else CHECK(r.cursor<=r.bits);randomized++;
    }
}
int main(void){out=malloc(sizeof(*out));before=malloc(sizeof(*before));work=malloc(sizeof(*work));CHECK(out&&before&&work);memset(out,0xa5,sizeof(*out));for(unsigned i=0;i<sizeof(fixtures)/sizeof(*fixtures);i++)fixture(&fixtures[i]);negatives();printf("{\"passed\":true,\"checks\":%u,\"fixtures\":%zu,\"truncations\":%u,\"mutations\":%u,\"randomized\":%u,\"output_bytes\":%zu,\"workspace_bytes\":%zu,\"aggregate_limit\":%u,\"whole_initial_update\":false,\"actor_publication\":false,\"acknowledgments_enabled\":false}\n",checks,sizeof(fixtures)/sizeof(*fixtures),truncations,mutations,randomized,sizeof(*out),sizeof(*work),COH_POWER_INFO_LIMIT);free(work);free(before);free(out);return 0;}
