/* Independent wire writer: no original oracle, dictionary or float arithmetic. */
#include "coh_power_ranges.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;assert(x);}while(0)
typedef struct{unsigned char data[256];size_t at;unsigned aligned;} Writer;
static void put(Writer*w,unsigned n,uint32_t value){if(w->aligned)n=(n+7u)&~7u;for(unsigned i=0;i<n;i++,w->at++)if(value&(UINT32_C(1)<<i))w->data[w->at/8]|=(unsigned char)(1u<<(w->at%8));}
static CohStatus parse(unsigned outer,CohRepReader*r,CohPowerRanges*out,CohPowerRangesWorkspace*w,size_t retained){return outer?coh_power_info_no_changes(r,out,w,retained,COH_POWER_RANGES_AGGREGATE_MAX):coh_power_ranges(r,out,w,retained,COH_POWER_RANGES_AGGREGATE_MAX);}
int main(void){
    static const uint32_t crc[]={0,0xdeadbeef,0xdeadbeef,3,1023,1024,0xffffff,0xffffffff};
    static const uint32_t raw[]={0,0x80000000,0x7fa12345,0x7fc12345,0x7f800000,0xff800000,0xbf800000,1};
    static const unsigned widths[]={2,10,24,32};
    CohPowerRanges*out=malloc(sizeof(*out)),*old=malloc(sizeof(*old));CohPowerRangesWorkspace*workspace=malloc(sizeof(*workspace));CHECK(out&&old&&workspace);
    for(unsigned mode=0;mode<2;mode++)for(unsigned prefix=0;prefix<(mode?2u:8u);prefix++)for(unsigned outer=0;outer<2;outer++){
        Writer w={{0},mode?prefix*8u:prefix,mode};size_t start=w.at;if(outer)put(&w,1,0);
        for(unsigned i=0;i<8;i++){
            put(&w,1,1);unsigned bin=0;while(bin<3&&crc[i]>((UINT32_C(1)<<widths[bin])-1u))bin++;
            /* Noncanonical wide zero is still legal to original receiver. */
            if(!i){bin=3;}
            put(&w,2,bin);put(&w,widths[bin],crc[i]);put(&w,32,raw[i]);
        }
        put(&w,1,0);size_t end=w.at;put(&w,32,0xfeedface);
        CohRepReader r;CHECK(coh_rep_reader(&r,(CohBytes){w.data,sizeof(w.data)},w.at,mode)==COH_OK);r.cursor=start;CohRepReader initial=r;
        CHECK(parse(outer,&r,out,workspace,0)==COH_OK);CHECK(r.cursor==end&&out->begin_bit==start&&out->end_bit==end&&out->count==8);
        for(unsigned i=0;i<8;i++)CHECK(out->ranges[i].power_crc==crc[i]&&out->ranges[i].range_word==raw[i]);
        for(size_t bit=start;bit<end;bit++){
            r=initial;r.bits=bit;CohRepReader before=r;memset(out,0xa5,sizeof(*out));*old=*out;
            CHECK(parse(outer,&r,out,workspace,0)!=COH_OK);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(out,old,sizeof(*out)));
        }
        r=initial;CohRepReader before=r;memset(out,0xa5,sizeof(*out));*old=*out;
        CHECK(parse(outer,&r,out,workspace,SIZE_MAX)==COH_LIMIT);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(out,old,sizeof(*out)));
        /* The unsupported true branch must not scan a tempting valid tail. */
        Writer unsupported={{0},mode?prefix*8u:prefix,mode};put(&unsupported,1,1);put(&unsupported,1,0);put(&unsupported,32,0);
        CHECK(coh_rep_reader(&r,(CohBytes){unsupported.data,sizeof(unsupported.data)},unsupported.at,mode)==COH_OK);r.cursor=start;before=r;
        CHECK(parse(1,&r,out,workspace,0)==COH_UNSUPPORTED);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(out,old,sizeof(*out)));
    }
    free(workspace);free(old);free(out);printf("{\"passed\":true,\"checks\":%u,\"independent_writer\":true,\"dictionary_authority\":false,\"full_update_complete\":false}\n",checks);return 0;
}
