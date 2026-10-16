#include "coh_offline_world.h"
#include <math.h>
#include <string.h>
#define MAX_INSTANCES 65536u
#define MAX_CELLS 4096u
#define MAX_ASSETS 8192u
static int finite3(const float *v) { return isfinite(v[0])&&isfinite(v[1])&&isfinite(v[2]); }
static int cancel(CohCancel c) { return c.poll&&c.poll(c.context); }
static int valid_path(const char *s) {
    uint32_t n=0,start=0; if(!s||!s[0]||s[0]=='/')return 0;
    for(;n<COH_ASSET_PATH_MAX&&s[n];n++) {
        if((unsigned char)s[n]<32||s[n]=='\\'||s[n]==':')return 0;
        if(s[n]=='/') { if(n==start||(n-start==1&&s[start]=='.')||(n-start==2&&s[start]=='.'&&s[start+1]=='.'))return 0;start=n+1; }
    }
    return n<COH_ASSET_PATH_MAX&&n>start&&!(n-start==1&&s[start]=='.')&&!(n-start==2&&s[start]=='.'&&s[start+1]=='.');
}
static int equal_path(const char *a,const char *b) {
    while(*a&&*b) { unsigned char x=(unsigned char)*a++,y=(unsigned char)*b++;if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)return 0; }
    return *a==*b;
}
CohStatus coh_offline_validate(const CohOfflineWorld *w) {
    uint32_t i,j,k,first=0;
    if(!w||!w->generation||!w->instance_count||w->instance_count>MAX_INSTANCES||!w->cell_count||w->cell_count>MAX_CELLS||w->asset_count>MAX_ASSETS||w->dependency_count>MAX_INSTANCES*COH_OFFLINE_INSTANCE_DEPENDENCIES||!w->instances||!w->cells||(w->asset_count&&!w->assets)||(w->dependency_count&&!w->dependencies))return COH_INVALID;
    for(i=0;i<w->asset_count;i++) { if(!w->assets[i].generation||!valid_path(w->assets[i].path))return COH_INVALID;for(j=0;j<i;j++)if(w->assets[i].generation==w->assets[j].generation&&equal_path(w->assets[i].path,w->assets[j].path))return COH_INVALID; }
    for(i=0;i<w->cell_count;i++) {
        const CohOfflineCell *c=w->cells+i;
        if(!finite3(c->minimum)||!finite3(c->maximum)||c->first!=first||c->count>w->instance_count-first)return COH_INVALID;
        for(k=0;k<3;k++)if(c->minimum[k]>c->maximum[k])return COH_INVALID;
        for(j=first;j<first+c->count;j++) {
            const CohOfflineInstance *p=w->instances+j;
            if(p->cell!=i||p->ready>1||!finite3(p->center)||!isfinite(p->radius)||p->radius<0||p->radius>1e6f||p->dependency_count>COH_OFFLINE_INSTANCE_DEPENDENCIES||p->first_dependency>w->dependency_count||p->dependency_count>w->dependency_count-p->first_dependency||(p->ready&&!p->dependency_count))return COH_INVALID;
            for(k=0;k<12;k++)if(!isfinite(p->world[k])||fabsf(p->world[k])>1e7f)return COH_INVALID;
            for(k=0;k<3;k++)if((double)p->center[k]-p->radius<c->minimum[k]||(double)p->center[k]+p->radius>c->maximum[k])return COH_INVALID;
            for(k=0;k<p->dependency_count;k++)if(w->dependencies[p->first_dependency+k]>=w->asset_count)return COH_INVALID;
            /* IDs are sorted within the immutable packet for linear duplicate checks. */
            if(j&&p->source_id<=w->instances[j-1].source_id)return COH_INVALID;
        }
        first+=c->count;
    }
    return first==w->instance_count?COH_OK:COH_INVALID;
}
static int cell_near(const CohOfflineCell *c,const float *center,float radius) {
    double d=0;uint32_t k;for(k=0;k<3;k++) { double x=center[k];double a=x<c->minimum[k]?c->minimum[k]-x:x>c->maximum[k]?x-c->maximum[k]:0;d+=a*a; }return d<=(double)radius*radius;
}
void coh_offline_release(CohOfflineSelection *s) {
    uint32_t i;if(!s)return;for(i=0;i<s->pin_count;i++)coh_asset_release(s->loader,s->pins[i]);memset(s,0,sizeof(*s));
}
CohStatus coh_offline_select(const CohOfflineWorld *w,CohAssetLoader *loader,uint32_t generation,const float center[3],float radius,size_t budget,CohCancel stop,CohOfflineSelection *out,CohOfflineSelectionStats *stats) {
    CohOfflineSelection staged;CohOfflineSelectionStats local;uint32_t deps[COH_OFFLINE_DEPENDENCY_CAP];uint32_t i,j,k,n=0;CohStatus status=COH_OK;
    memset(&staged,0,sizeof(staged));memset(&local,0,sizeof(local));if(stats)*stats=local;
    if(!w||!loader||!out||!center||!finite3(center)||!isfinite(radius)||radius<0||radius>1e6f)return COH_INVALID;
    if(!generation||generation!=w->generation)return COH_STATE;
    /* validate once before publishing a World; this API requires immutable validated input. */
    staged.generation=generation;staged.loader=loader;
    for(i=0;i<w->cell_count;i++) {
        const CohOfflineCell *cell=w->cells+i;local.tested_cells++;
        if(cancel(stop)){status=COH_CANCELLED;goto fail;}
        if(!cell_near(cell,center,radius))continue;
        local.visible_cells++;
        for(j=cell->first;j<cell->first+cell->count;j++) {
            const CohOfflineInstance *p=w->instances+j;double d=0,r=(double)radius+p->radius;
            if((j-cell->first)%64u==0&&cancel(stop)){status=COH_CANCELLED;goto fail;}
            local.tested_instances++;
            for(k=0;k<3;k++){double q=(double)p->center[k]-center[k];d+=q*q;}
            if(d>r*r)continue;
            local.visible_instances++;
            if(!p->ready){local.unavailable_instances++;status=COH_NOT_FOUND;goto fail;}
            if(staged.count==COH_OFFLINE_SELECTION_CAP){status=COH_LIMIT;goto fail;}
            staged.instances[staged.count++]=j;
            for(k=0;k<p->dependency_count;k++) {
                uint32_t x=w->dependencies[p->first_dependency+k],a;
                for(a=0;a<n;a++)if(deps[a]==x)break;
                if(a==n){if(n==COH_OFFLINE_DEPENDENCY_CAP){status=COH_LIMIT;goto fail;}deps[n++]=x;}
            }
        }
    }
    local.unique_assets=n;
    for(i=0;i<n;i++) {
        CohAssetInfo info;status=coh_asset_lookup(loader,w->assets[deps[i]],&info);if(status!=COH_OK)goto fail;
        if(info.decoded_bytes>budget-local.required_bytes){status=COH_LIMIT;goto fail;}local.required_bytes+=info.decoded_bytes;
    }
    for(i=0;i<n;i++) {
        if(cancel(stop)){status=COH_CANCELLED;goto fail;}
        status=coh_asset_acquire(loader,w->assets[deps[i]],stop,&staged.pins[staged.pin_count]);if(status!=COH_OK)goto fail;staged.pin_count++;
    }
    if(cancel(stop)){status=COH_CANCELLED;goto fail;}
    staged.resident_bytes=local.required_bytes;coh_offline_release(out);*out=staged;if(stats)*stats=local;return COH_OK;
fail:
    coh_offline_release(&staged);if(stats)*stats=local;return status;
}
CohStatus coh_offline_transform(const CohOfflineWorld *w,uint32_t generation,uint32_t instance,float world[12]) {
    if(!w||!world||instance>=w->instance_count)return COH_INVALID;
    if(!generation||w->generation!=generation)return COH_STATE;
    memcpy(world,w->instances[instance].world,12*sizeof(float));return COH_OK;
}
