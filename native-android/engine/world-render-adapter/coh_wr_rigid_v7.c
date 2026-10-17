#include "coh_wr_rigid_v7.h"
#include "coh_wr_rigid_internal.h"
#include "../scenecatalog/coh_resource_geo_source.h"
static CohStatus source_open(CohBytes bytes,uint8_t *workspace,size_t capacity,
 uint32_t maximum,CohAssetGeo *out){
 uint32_t zero=0;return coh_resource_geo_source_open(bytes,workspace,capacity,maximum,out,&zero);
}
CohStatus coh_wr_rigid_v7_acquire(CohAssetLoader*l,const CohWrRigidRequest*q,
 const CohWrRigidLimits*b,CohCancel cancel,CohWrRigidResource**out){
 return coh_wr_rigid_acquire_policy(l,q,b,cancel,out,source_open,coh_resource_geo_source_model,COH_WR_RIGID_EXACT_SOURCE_7);
}
