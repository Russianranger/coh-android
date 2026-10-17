#include "coh_wr_rigid_source.h"
#include "coh_wr_rigid_internal.h"
#include "../scenecatalog/coh_resource_geo_source.h"
static CohStatus source_open(CohBytes bytes,uint8_t *workspace,size_t capacity,
 uint32_t maximum,CohAssetGeo *out){
 uint32_t zero_rows=0;
 return coh_resource_geo_source_open(bytes,workspace,capacity,maximum,out,&zero_rows);
}
CohStatus coh_wr_rigid_source_acquire(CohAssetLoader*l,const CohWrRigidRequest*q,
 const CohWrRigidLimits*b,CohCancel cancel,CohWrRigidResource**out){
 return coh_wr_rigid_acquire_using(l,q,b,cancel,out,source_open,coh_resource_geo_source_model);
}
