#include "source_resources.inc"
static Model resource_models[2];static Model*resource_rows[3];static GeoLoadData resource_geo;
static TexID resource_tex[2];static TrickInfo resource_info;static TrickNode resource_trick;
static unsigned char resource_scratch[COH_RESOURCE_RECORD_MAX],resource_bytes[1u<<20];
static char *resource_textures[2]={"stone_base","stone_normal"};
static void resource_setup(void){
 unsigned f,i;snapshot_setup(2,0);
 for(f=0;f<(unsigned)group_info.file_count;f++)for(i=0;i<(unsigned)group_info.files[f]->count;i++)if(group_info.files[f]->defs[i])group_info.files[f]->defs[i]->model=NULL;
 memset(resource_models,0,sizeof(resource_models));memset(&resource_geo,0,sizeof(resource_geo));
 memset(&resource_info,0,sizeof(resource_info));memset(&resource_trick,0,sizeof(resource_trick));
 resource_models[0].name="other";resource_models[0].namelen_notrick=5;
 resource_models[1].name="piece__Stone";resource_models[1].namelen_notrick=5;
 resource_rows[0]=&resource_models[0];resource_rows[1]=&resource_models[1];
 resource_geo.modelheader.models=resource_rows;resource_geo.modelheader.model_count=2;
 strcpy(resource_geo.name,"object_library/resources/exact_loaded.geo");resource_geo.file_format_version=8;resource_geo.loadstate=4;
 resource_geo.texnames.strings=resource_textures;resource_geo.texnames.count=2;
 resource_models[1].gld=&resource_geo;resource_models[1].loadstate=4;resource_models[1].flags=0x1234;
 resource_models[1].vert_count=9;resource_models[1].tri_count=3;resource_models[1].tex_count=2;resource_models[1].tex_idx=resource_tex;
 resource_tex[0]=(TexID){1,1};resource_tex[1]=(TexID){0,2};
 resource_models[1].min[0]=-2;resource_models[1].max[0]=4;resource_models[1].radius=5;
 resource_models[1].scale[0]=resource_models[1].scale[1]=resource_models[1].scale[2]=1;
 resource_models[1].trick=&resource_trick;resource_trick.flags1=3;resource_trick.flags2=5;resource_trick.info=&resource_info;
 resource_info.name="Stone";resource_info.file_name="tricks/exact.txt";resource_info.model_flags=7;resource_info.group_flags=11;
 resource_info.lod_near=10;resource_info.lod_far=20;resource_info.lod_scale=2;resource_info.shadow_dist=12;
 oracle_defs[0].model=&resource_models[1];
}
static GeoLoadData*geoLoad(const char*filename,int load,int use){(void)filename;(void)load;(void)use;return &resource_geo;}
static void resource_expect(CohSourceCatalogExportReport*catalog,unsigned expected){
 SnapshotOutput out={resource_bytes,0,sizeof(resource_bytes),0};CohSourceResourceReport report;
 SNAP_CHECK(coh_source_resources_export(snapshot_write,&out,snapshot_catalog,catalog,resource_scratch,sizeof(resource_scratch),&report)==(int)expected);
 SNAP_CHECK(report.status==expected);SNAP_CHECK(expected==COH_SOURCE_CATALOG_OUTPUT||out.size==0);
}
/* Original modelFind/lookup comparison bodies are inserted here by checker. */
RESOURCE_ORIGINAL_MODEL_FIND
int main(int argc,char**argv){
 Model before_models[2];GeoLoadData before_geo;TrickInfo before_info;TrickNode before_trick;
 CohSourceCatalogExportReport catalog;CohSourceResourceReport report;SnapshotOutput cat,out;unsigned at,records=0,model_records=0,n,t,i;
 SNAP_CHECK(argc==2);resource_setup();
 SNAP_CHECK(modelFind("piece__RequestedDifferentTrick","exact",2,4)==&resource_models[1]);
 SNAP_CHECK(modelFind("PIECE","exact",2,4)==&resource_models[1]);SNAP_CHECK(modelFind("absent","exact",2,4)==NULL);
 cat=(SnapshotOutput){snapshot_catalog,0,sizeof(snapshot_catalog),0};
 SNAP_CHECK(coh_source_catalog_export(snapshot_write,&cat,20261016u,&catalog)==0);
 memcpy(before_models,resource_models,sizeof(before_models));before_geo=resource_geo;before_info=resource_info;before_trick=resource_trick;
 out=(SnapshotOutput){resource_bytes,0,sizeof(resource_bytes),0};
 SNAP_CHECK(coh_source_resources_export(snapshot_write,&out,snapshot_catalog,&catalog,resource_scratch,sizeof(resource_scratch),&report)==0);
 SNAP_CHECK(!memcmp(before_models,resource_models,sizeof(before_models)));SNAP_CHECK(!memcmp(&before_geo,&resource_geo,sizeof(before_geo)));
 SNAP_CHECK(!memcmp(&before_info,&resource_info,sizeof(before_info)));SNAP_CHECK(!memcmp(&before_trick,&resource_trick,sizeof(before_trick)));
 SNAP_CHECK(report.status==0&&report.records&&report.models==1&&report.textures==2&&!report.client_materials_available&&!report.client_lods_available&&!report.actual_runtime_executed);
 for(at=0;at<out.size;at+=n){unsigned char*p=out.data+at;unsigned kind=coh_snapshot_u32(p+24);n=coh_snapshot_u32(p+16);SNAP_CHECK(n>=COH_RESOURCE_HEADER&&n<=out.size-at&&!memcmp(p,"COHRES01",8));records++;
  SNAP_CHECK(coh_snapshot_u32(p+20)==20261016u&&coh_snapshot_u32(p+44)==1);
  if(coh_snapshot_u32(p+40)){unsigned pos=COH_RESOURCE_HEADER;model_records++;SNAP_CHECK(coh_snapshot_u32(p+68)==1&&coh_snapshot_u32(p+72)==8&&coh_snapshot_u32(p+96)==2);
   for(i=0;i<6;i++){unsigned offset=i<5?48+i*4:124;pos+=coh_snapshot_u32(p+offset);}for(t=0;t<2;t++){unsigned id=coh_snapshot_u32(p+pos),bytes=coh_snapshot_u32(p+pos+8);SNAP_CHECK(id==(t?0u:1u));SNAP_CHECK(!strcmp((char*)p+pos+12,resource_textures[id]));pos+=12+bytes;}SNAP_CHECK(pos==n);
  }else SNAP_CHECK(coh_snapshot_u32(p+68)==0xffffffffu);
  if(kind==2)SNAP_CHECK(coh_snapshot_u32(p+28)==0xffffffffu&&coh_snapshot_u32(p+36)==0);
 }
 {CohSnapshotState source;unsigned size=0,textures=0,remaining=1;memset(&source,0,sizeof(source));source.files=catalog.files;
  SNAP_CHECK(coh_resource_record(&source,&oracle_defs[0],20261016u,resource_scratch,&size,&textures,&remaining)==COH_SOURCE_CATALOG_LIMIT);
 }
 SNAP_CHECK(records==report.records&&model_records==1&&report.model_row_comparisons==2);snapshot_save(argv[1],"resources.cohres",out.data,out.size);
 for(i=0;i<14;i++){
  resource_setup();cat=(SnapshotOutput){snapshot_catalog,0,sizeof(snapshot_catalog),0};SNAP_CHECK(coh_source_catalog_export(snapshot_write,&cat,20261016u,&catalog)==0);
  if(i==0)resource_models[1].gld=NULL;
  if(i==1)resource_rows[1]=NULL;
  if(i==2){resource_rows[0]=&resource_models[1];}
  if(i==3)resource_tex[0].id=2;
  if(i==4)resource_geo.texnames.count=-1;
  if(i==5)resource_models[1].tex_count=257;
  if(i==6)resource_info.name=NULL;
  if(i==7)resource_models[1].vert_count=-1;
  if(i==8){unsigned nan=0x7fc00000u;memcpy(&resource_models[1].radius,&nan,4);}
  if(i==9)resource_geo.name[191]='x',memset(resource_geo.name,'x',191);
  if(i==10)resource_geo.modelheader.model_count=65537;
  if(i==11)resource_models[1].tex_idx=NULL;
  if(i==12)resource_geo.loadstate=2;
  if(i==13)resource_models[1].loadstate=2;
  resource_expect(&catalog,COH_SOURCE_CATALOG_SOURCE);
 }
 resource_setup();cat=(SnapshotOutput){snapshot_catalog,0,sizeof(snapshot_catalog),0};SNAP_CHECK(coh_source_catalog_export(snapshot_write,&cat,20261016u,&catalog)==0);
 catalog.emitted_bytes--;resource_expect(&catalog,COH_SOURCE_CATALOG_ARGUMENT);catalog.emitted_bytes++;
 snapshot_catalog[24]^=1;resource_expect(&catalog,COH_SOURCE_CATALOG_ARGUMENT);snapshot_catalog[24]^=1;
 snapshot_catalog[32]^=1;resource_expect(&catalog,COH_SOURCE_CATALOG_CHANGED);snapshot_catalog[32]^=1;
 out=(SnapshotOutput){resource_bytes,0,sizeof(resource_bytes),1};SNAP_CHECK(coh_source_resources_export(snapshot_write,&out,snapshot_catalog,&catalog,resource_scratch,sizeof(resource_scratch),&report)==COH_SOURCE_CATALOG_OUTPUT);
 SNAP_CHECK(report.status==COH_SOURCE_CATALOG_OUTPUT&&out.size==0);
 printf("{\"passed\":true,\"checks\":%u,\"original_model_find_executed\":true,\"source_observer_sanitized\":true,\"actual_runtime_executed\":false}\n",snapshot_checks);return 0;
}
