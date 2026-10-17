/* Included only by the explicit integrated source→CPU-rigid qualifier.
 * Material pins/generation are FIXTURES, never admitted CLIENT state. */
typedef struct {CohSourceBody *body;uint32_t ordinal;unsigned pins,releases,bad_material;const char *model;} BridgeMaterial;
static CohStatus bridge_material(void *v,CohAssetId id,const char *model,uint32_t part,const CohAssetGeoMaterial *source,CohWrRigidMaterial *out){
 BridgeMaterial *m=v;CohSourceBodyLease lease;CHECK(coh_source_body_lease(m->body,m->ordinal,&lease)==COH_OK);CHECK(id.generation==20261016&&id.generation==lease.binding.asset_generation);CHECK(!strcmp(id.path,lease.geo.id.path)&&!strcmp(model,m->model)&&!strcmp(model,lease.model.model_name));CHECK(part==0&&source->triangle_count>0);
 memset(out,0,sizeof(*out));out->material=coh_renderer_default_material(COH_MAT_DUAL);for(unsigned k=0;k<2;k++)for(unsigned n=0;n<2;n++)out->uv_scale[k][n]=1;
 out->texture_id[0]=11;out->texture_id[1]=12;out->geometry_id=100;out->generation=19;out->unsupported_semantics=m->bad_material;memset(out->source_sha256,1,32);out->pin=m;m->pins++;return COH_OK;
}
static void bridge_release(void *v,void *pin){BridgeMaterial*m=v;CHECK(pin==m);CohSourceBodyLease lease;CHECK(coh_source_body_lease(m->body,m->ordinal,&lease)==COH_OK);m->releases++;}
static int after_material(void *v){BridgeMaterial *m=v;return m->pins>m->releases;}
static void rigid_refuses(CohSourceBody *input,const CohSourceRigidRequest *q,const CohSourceRigidLimits *b,CohCancel cancel){CohSourceBody *body=input;CohSourceRigid*out=NULL;CohSourceRigidReport report,before;memset(&report,0xa5,sizeof(report));before=report;size_t initial=live;CHECK(coh_source_rigid_create(&body,q,b,cancel,&out,&report)!=COH_OK);CHECK(body==input&&!out&&!memcmp(&before,&report,sizeof(report))&&live==initial);}
static void bridge_checks(CohSourceSelection *selection,CohSourceBody *neonbody,CohSourceBody *shopbody,uint32_t neon,uint32_t shop,CohAssetLoader *loader,CohSourceBodyBudget bb){
 const CohResourceIndex *ignored;CohSourceBodyReport nr,sr;CHECK(coh_source_body_view(neonbody,&ignored,&nr)==COH_OK);CHECK(coh_source_body_view(shopbody,&ignored,&sr)==COH_OK);
 uint32_t roof=UINT32_MAX,empty=UINT32_MAX,sign=UINT32_MAX;CohSourceBodyLease lease;
 for(uint32_t ordinal=0;ordinal<40232;ordinal++){
  CohStatus status=coh_source_body_lease(shopbody,ordinal,&lease);if(status==COH_OK){if(!strcmp(lease.model.model_name,"_shptlr_K_Roof__FLRSHPS_SHELLS"))roof=ordinal;if(!strcmp(lease.model.model_name,"LlegR"))empty=ordinal;}else CHECK(status==COH_NOT_FOUND);
  status=coh_source_body_lease(neonbody,ordinal,&lease);if(status==COH_OK&& !strcmp(lease.model.model_name,"_sign_Neon_BarVERT"))sign=ordinal;else CHECK(status==COH_OK||status==COH_NOT_FOUND);
 }
 CHECK(roof!=UINT32_MAX&&empty!=UINT32_MAX&&sign!=UINT32_MAX);
 CHECK(coh_source_body_lease(shopbody,roof,&lease)==COH_OK&&lease.graph_node<40232&&lease.source_ordinal==roof&&lease.loader==loader&&lease.loader_reservation==(32u<<20)&&lease.retained_owner_bytes>30000000);
 CHECK(coh_source_body_lease(shopbody,roof,(CohSourceBodyLease*)lease.model.model_name)==COH_INVALID);
 CohResourceOwnerSources owner;const CohResourceIndex *shopindex;CHECK(coh_source_body_view(shopbody,&shopindex,&sr)==COH_OK);CHECK(coh_resource_index_owner_sources(shopindex,lease.model.owner_kind,lease.model.file,lease.model.slot,&owner)==COH_OK);CHECK(owner.blob.size==252088&&owner.header.size==22124&&owner.record.size>192);
 CohResourceOwnerSources original_owner=owner;CHECK(coh_resource_index_owner_sources(shopindex,UINT32_MAX,UINT32_MAX,UINT32_MAX,&owner)==COH_NOT_FOUND&&!memcmp(&owner,&original_owner,sizeof(owner)));
 CohBytes source_spans[]={owner.record,owner.header,owner.blob};for(unsigned k=0;k<3;k++){CHECK(coh_resource_index_owner_sources(shopindex,lease.model.owner_kind,lease.model.file,lease.model.slot,(CohResourceOwnerSources*)source_spans[k].data)==COH_INVALID);CHECK(coh_source_body_lease(shopbody,roof,(CohSourceBodyLease*)source_spans[k].data)==COH_INVALID);}
 CHECK(coh_resource_index_owner_sources(shopindex,lease.model.owner_kind,lease.model.file,lease.model.slot,(CohResourceOwnerSources*)(UINTPTR_MAX-8))==COH_INVALID);CHECK(coh_source_body_lease(shopbody,roof,(CohSourceBodyLease*)(UINTPTR_MAX-8))==COH_INVALID);
 bb.retained_bytes+=nr.owned_bytes+sr.owned_bytes;
 CohSourceRigidLimits limits={96u<<20,262144+nr.owned_bytes+sr.owned_bytes,2u<<20,2u<<20,65536,65536,65536,512};
 CohSourceBody *input=NULL;CohSourceBodyReport br;CHECK(coh_source_body_create(NULL,selection,shop,loader,&bb,digest,NULL,(CohCancel){0},&input,&br)==COH_OK);
 BridgeMaterial material={input,roof,0,0,0,"_shptlr_K_Roof__FLRSHPS_SHELLS"};CohSourceRigidRequest q={roof,19,digest,NULL,bridge_material,bridge_release,&material};
 CohSourceRigid *badalias=NULL;CohSourceRigidReport alias_report;CohSourceBody *original_input=input;CohSourceBodyLease input_lease;CHECK(coh_source_body_lease(input,roof,&input_lease)==COH_OK);source_spans[0]=input_lease.actual_sources.record;source_spans[1]=input_lease.actual_sources.header;source_spans[2]=input_lease.actual_sources.blob;
 for(unsigned k=0;k<3;k++){CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},&badalias,(CohSourceRigidReport*)source_spans[k].data)==COH_INVALID&&input==original_input&&!badalias);CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},(CohSourceRigid**)source_spans[k].data,&alias_report)==COH_INVALID&&input==original_input);}
 CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},&badalias,(CohSourceRigidReport*)(UINTPTR_MAX-8))==COH_INVALID&&input==original_input&&!badalias);
 CohSourceRigidLimits tight=limits;CHECK(coh_source_body_lease(input,roof,&lease)==COH_OK);tight.aggregate_limit=lease.retained_owner_bytes+lease.loader_reservation-1;size_t beforecalls=calls;rigid_refuses(input,&q,&tight,(CohCancel){0});CHECK(calls==beforecalls);
 CohSourceRigidRequest wrong=q;wrong.source_ordinal=sign;rigid_refuses(input,&wrong,&limits,(CohCancel){0});CHECK(!material.pins);
 wrong.source_ordinal=empty;rigid_refuses(input,&wrong,&limits,(CohCancel){0});CHECK(!material.pins);
 wrong=q;wrong.digest=broken;rigid_refuses(input,&wrong,&limits,(CohCancel){0});CHECK(!material.pins);
 material.bad_material=1;rigid_refuses(input,&q,&limits,(CohCancel){0});CHECK(material.pins==material.releases);material.bad_material=0;
 rigid_refuses(input,&q,&limits,(CohCancel){after_material,&material});CHECK(material.pins==material.releases);
 /* Allocation count measured on a successful fresh transfer. */
 CohSourceRigid *rigid=NULL;CohSourceRigidReport report;size_t first=calls;CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},&rigid,&report)==COH_OK);size_t allocations=calls-first;CHECK(!input&&rigid&&report.derived_file_origin_verified&&report.unresolved_client_semantics&&!report.direct_open_observed&&!report.assets_admitted&&!report.client_materials_available&&!report.live_generation_admitted&&!report.world_authority);CHECK(report.source_ordinal==roof&&report.resource_owner_generation==lease.binding.generation&&report.graph_generation==lease.graph_generation&&report.catalog_generation==lease.catalog_generation&&report.asset_generation==20261016&&report.material_generation==19&&report.rigid.vertices==4&&report.rigid.triangles==2&&report.rigid.parts==1);
 CohRenderGeometry geo;CohWrRigidMaterial part;CHECK(coh_source_rigid_part(rigid,0,&geo,&part)==COH_OK);CHECK(geo.vertex_count==4&&geo.index_count==6&&geo.generation==20261016&&part.generation==19);CHECK(report.rigid.loader_reservation==(32u<<20)&&report.rigid.external_bytes>=lease.retained_owner_bytes&&report.aggregate_reserved_bytes<=limits.aggregate_limit);
 coh_asset_trim(loader);CHECK(coh_source_rigid_part(rigid,0,&geo,&part)==COH_OK);coh_source_rigid_free(rigid);CHECK(material.pins==material.releases);
 CHECK(coh_source_body_create(NULL,selection,shop,loader,&bb,digest,NULL,(CohCancel){0},&input,&br)==COH_OK);material.body=input;
 for(size_t n=1;n<=allocations;n++){fail_at=calls+n;rigid_refuses(input,&q,&limits,(CohCancel){0});fail_at=0;CHECK(material.pins==material.releases);}
 /* Existing nonNULL output cannot consume another body. */
 CohSourceRigid *nonnull=(CohSourceRigid*)input;CohSourceBody *saved=input;CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},&nonnull,&report)==COH_STATE&&input==saved&&nonnull==(CohSourceRigid*)saved);
 CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},(CohSourceRigid**)&input,&report)==COH_INVALID&&input==saved);
 CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},&rigid,(CohSourceRigidReport*)&q)==COH_INVALID&&input==saved);
 coh_source_body_free(input);input=NULL;
 /* Legacy-v0 root model uses source-derived labels too, not fixture geometryIDs. */
 CHECK(coh_source_body_create(NULL,selection,neon,loader,&bb,digest,NULL,(CohCancel){0},&input,&br)==COH_OK);material.body=input;material.ordinal=sign;material.model="_sign_Neon_BarVERT";q.source_ordinal=sign;rigid=NULL;
 CHECK(coh_source_rigid_create(&input,&q,&limits,(CohCancel){0},&rigid,&report)==COH_OK&&!input&&report.rigid.geo_version==0&&report.rigid.vertices==90&&report.rigid.triangles==56);coh_source_rigid_free(rigid);CHECK(material.pins==material.releases);bridge_completions=2;
}
