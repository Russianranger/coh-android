#include "coh_world_live.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define ROW_BYTES 96u
#define ROW_MAX 65536u
struct CohWorldLive {CohAssetSource source;CohWorldLiveStats stats;uint32_t endpoints;};
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const unsigned char *p){uint32_t u=u32(p);float f;memcpy(&f,&u,4);return f;}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static CohStatus row(CohWorldLive *live,uint32_t ordinal,CohWorldInstance *out,float bounds[4]){
    unsigned char raw[ROW_BYTES];CohStatus s=live->source.read_at(live->source.context,64u+(uint64_t)ordinal*ROW_BYTES,raw,sizeof raw);live->stats.reads++;if(s!=COH_OK)return s;live->stats.read_bytes+=sizeof raw;
    CohWorldInstance next={0};next.node=u32(raw);next.endpoint=u32(raw+4);if(next.node!=ordinal||next.endpoint>=live->endpoints)return COH_INVALID;
    for(unsigned i=0;i<12;i++){next.world[i]=f32(raw+8+i*4);if(!isfinite(next.world[i])||fabsf(next.world[i])>10000000)return COH_INVALID;}
    for(unsigned i=0;i<6;i++){next.tint[i]=f32(raw+56+i*4);if(!isfinite(next.tint[i])||next.tint[i]<0||next.tint[i]>1)return COH_INVALID;}
    for(unsigned i=0;i<4;i++){bounds[i]=f32(raw+80+i*4);if(!isfinite(bounds[i])||fabsf(bounds[i])>10000000)return COH_INVALID;}
    if(bounds[3]<0||bounds[3]>1000000)return COH_INVALID;
    *out=next;return COH_OK;
}
CohStatus coh_world_live_open(CohAssetSource source,uint32_t endpoints,CohCancel cancel,CohWorldLive **out){
    if(!out||!source.read_at||!source.generation||source.size<64||!endpoints||endpoints>COH_WORLD_MAX_ENDPOINTS)return COH_INVALID;
    if((uintptr_t)out>UINTPTR_MAX-sizeof *out)return COH_INVALID;
    unsigned char header[64];CohStatus s=source.read_at(source.context,0,header,sizeof header);if(s!=COH_OK)return s;
    uint32_t count=u32(header+20);if(memcmp(header,"COHLIVE1",8)||u32(header+8)!=1||u32(header+12)!=64||u32(header+16)!=source.size||!count||count>ROW_MAX||u32(header+24)!=ROW_BYTES||u32(header+28)||source.size!=64u+(uint64_t)count*ROW_BYTES)return COH_INVALID;
    CohWorldLive *live=calloc(1,sizeof *live);if(!live)return COH_LIMIT;live->source=source;live->endpoints=endpoints;live->stats=(CohWorldLiveStats){sizeof *live,count,1,sizeof header,0};
    for(uint32_t i=0;i<count;i++){if(cancelled(cancel)){free(live);return COH_CANCELLED;}CohWorldInstance instance;float bounds[4];s=row(live,i,&instance,bounds);if(s!=COH_OK){free(live);return s;}}
    *out=live;return COH_OK;
}
static int separate(const void *a,size_t an,const void *b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-an&&y<=UINTPTR_MAX-bn&&(x>=y+bn||y>=x+an);}
CohStatus coh_world_live_query(CohWorldLive *live,const float center[3],float radius,CohWorldInstance *out,uint32_t capacity,uint32_t *count,CohCancel cancel){
    if(!live||!center||!count||(!out&&capacity)||capacity>COH_WORLD_MAX_INSTANCES||!isfinite(radius)||radius<0||radius>96)return COH_INVALID;
    for(unsigned i=0;i<3;i++)if(!isfinite(center[i])||fabsf(center[i])>10000000)return COH_INVALID;
    size_t bytes=(size_t)capacity*sizeof *out;if(!separate(live,sizeof *live,count,sizeof *count)||!separate(live,sizeof *live,out,bytes)||!separate(count,sizeof *count,out,bytes)||!separate(center,3*sizeof *center,out,bytes)||!separate(center,3*sizeof *center,count,sizeof *count))return COH_INVALID;
    CohWorldInstance next[COH_WORLD_MAX_INSTANCES];uint32_t found=0;
    for(uint32_t i=0;i<live->stats.rows;i++){
        if(cancelled(cancel))return COH_CANCELLED;
        CohWorldInstance instance;float bounds[4];CohStatus s=row(live,i,&instance,bounds);if(s!=COH_OK)return s;double distance=0;
        for(unsigned j=0;j<3;j++){double d=(double)bounds[j]-center[j];distance+=d*d;}
        double reach=(double)radius+bounds[3];if(distance<=reach*reach){if(found==capacity)return COH_LIMIT;next[found++]=instance;}
    }
    if(cancelled(cancel))return COH_CANCELLED;
    if(found)memcpy(out,next,(size_t)found*sizeof *out);
    *count=found;live->stats.queries++;return COH_OK;
}
CohWorldLiveStats coh_world_live_stats(const CohWorldLive *live){CohWorldLiveStats s={0};return live?live->stats:s;}
void coh_world_live_free(CohWorldLive *live){free(live);}

size_t coh_world_live_allocation_bytes(void){return sizeof(CohWorldLive);}
