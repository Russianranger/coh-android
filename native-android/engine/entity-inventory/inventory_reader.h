/* Private bounded scalar helpers. No original state/dictionary application. */
#include <math.h>
#include <string.h>
typedef struct {CohRepReader r;CohStatus status;}InventoryReader;
static int inventory_overlap(const void*a,size_t an,const void*b,size_t bn){uintptr_t aa=(uintptr_t)a,bb=(uintptr_t)b;if(!an||!bn)return 0;if(an>UINTPTR_MAX-aa||bn>UINTPTR_MAX-bb)return 1;return aa<bb+bn&&bb<aa+an;}
static uint32_t inventory_scalar(InventoryReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_read(&p->r,n,&v);if(p->status==COH_OK&&n<32&&v>=(UINT32_C(1)<<n))p->status=COH_INVALID;return v;}
static uint32_t inventory_pack(InventoryReader*p,unsigned n){uint32_t v=0;if(p->status==COH_OK)p->status=coh_rep_pack(&p->r,n,&v);return v;}
static uint32_t inventory_number(InventoryReader*p){uint32_t u=inventory_scalar(p,32);float f;memcpy(&f,&u,4);if(p->status==COH_OK&&!isfinite(f))p->status=COH_INVALID;return u;}
