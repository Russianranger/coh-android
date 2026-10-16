/* Trusted inputs for exact original GROUPS producer. No body padding, fake
 * tail, imported assets, real account data or authoritative client state. */
static GroupDef oracle_defs[256];
static GroupDef *oracle_def_ptrs[256],*oracle_library_ptrs[2],*oracle_other_ptrs[2];
static GroupFile oracle_files[3];
static GroupFile *oracle_file_ptrs[3];
static DefTracker oracle_refs[4];
static DefTracker *oracle_ref_ptrs[4];
static GroupEnt oracle_children[256][2];
static OracleStash oracle_properties[256];
static PropertyEnt oracle_prop_entries[256][2];
static DefTexSwap oracle_swaps[2]={{"oracle_original_a","oracle_replacement_a",0},{"oracle_original_b","oracle_replacement_b",1}};
static DefTexSwap *oracle_swap_ptrs[2];
static Model oracle_model={"oracle_geometry__source_fixture"};
static char oracle_names[256][64],oracle_values[256][256];
static char *oracle_pages[2]={"loading/oracle_page_a","loading/oracle_page_b"};

static void oracle_identity(Mat4 matrix){copyMat4(unitmat,matrix);}
static void oracle_raw(Mat4 matrix){oracle_identity(matrix);matrix[0][1]=0.125f;matrix[1][2]=-0.375f;matrix[3][0]=1.125f;matrix[3][1]=-2.25f;matrix[3][2]=3.75f;}
static void oracle_position(Mat4 matrix){oracle_identity(matrix);matrix[3][0]=1.5f;matrix[3][1]=-2.0f;matrix[3][2]=3.125f;}
int groups_matrix_probe(float angle,int zero_x,U32 *flags){
 Mat4 matrix;Vec3 pyr={0,angle,0};PackMat packed;oracle_identity(matrix);
 createMat3YPR(matrix,pyr);if(zero_x)for(int i=0;i<3;i++)matrix[i][0]=0;
 int result=packMat(matrix,&packed);flags[0]=packed.has_pos;flags[1]=packed.has_pyr;flags[2]=packed.has_scale;
 return result;
}
static void oracle_simple(GroupDef *def,int id,char *name){memset(def,0,sizeof(*def));def->id=id;def->in_use=1;def->name=name;def->mod_time=100;def->type_name="";}
static void oracle_rich(GroupDef *def,int i){
 oracle_simple(def,i,oracle_names[i]);
 def->count=2;def->entries=oracle_children[i];
 oracle_raw(def->entries[0].mat);oracle_position(def->entries[1].mat);
 def->lod_scale=1.5f;def->lod_near=2;def->lod_far=400;def->lod_nearfade=3;def->lod_farfade=10;
 def->lod_fadenode=3;def->parent_fade=1;def->child_parent_fade=1;def->no_fog_clip=1;def->no_coll=1;
 def->open_tracker=1;def->child_light=1;def->child_ambient=1;def->child_volume=1;def->child_beacon=1;def->child_no_fog_clip=1;
 def->sound_radius=32;def->shadow_dist=64;def->type_name="oracle_type";
 def->has_light=1;def->has_ambient=1;def->lib_ungroupable=1;def->light_radius=16;
 for(int c=0;c<8;c++)((U8*)def->color)[c]=(U8)(c*29+7);
 def->has_cubemap=1;def->cubemapGenSize=128;def->cubemapCaptureSize=256;def->cubemapBlurAngle=0.5f;def->cubemapCaptureTime=4.25f;
 def->has_sound=1;def->sound_name="oracle_sound";def->sound_script_filename="sound/oracle.script";def->sound_vol=123;def->sound_ramp=2.5f;def->sound_exclude=1;
 def->has_fog=1;def->fog_near=8;def->fog_far=1000;def->fog_radius=128;def->fog_speed=0.25f;
 def->has_volume=1;def->box_scale[0]=2;def->box_scale[1]=3;def->box_scale[2]=4;
 def->has_beacon=1;def->beacon_name="oracle_beacon";def->beacon_radius=5.5f;
 def->has_tint_color=1;def->has_tex=3;def->tex_names[0]="oracle_texture_a";def->tex_names[1]="oracle_texture_b";
 def->has_alpha=1;def->groupdef_alpha=0.75f;def->has_properties=1;
 def->properties=&oracle_properties[i];def->properties->count=2;
 snprintf(oracle_prop_entries[i][0].name_str,64,"OracleString");
 snprintf(oracle_prop_entries[i][1].name_str,64,"OracleRadius");
 oracle_prop_entries[i][0].value_str=oracle_values[i];oracle_prop_entries[i][0].type=0;
 oracle_prop_entries[i][1].value_str="12.5";oracle_prop_entries[i][1].type=1;
 for(int p=0;p<2;p++)def->properties->entries[p]=&oracle_prop_entries[i][p];
 def->def_tex_swaps=oracle_swap_ptrs;def->model=&oracle_model;def->hideForGameplay=1;
}

int groups_original(U32 which,U32 aligned,U32 legacy,U8 *out,U32 *bits,U32 *footer){
 if(which>10||aligned>1||legacy>1)return 0;
 memset(&group_info,0,sizeof(group_info));memset(&db_state,0,sizeof(db_state));memset(&server_state,0,sizeof(server_state));
 memset(oracle_defs,0,sizeof(oracle_defs));memset(oracle_files,0,sizeof(oracle_files));memset(oracle_refs,0,sizeof(oracle_refs));
 memset(oracle_children,0,sizeof(oracle_children));memset(oracle_properties,0,sizeof(oracle_properties));
 oracle_array_count=0;oracle_aligned=aligned;oracle_groups_command=legacy?11:6;
 world_id=17;g_MapIsTutorial=0;g_isBaseRaid=0;g_activemission=0;oracle_has_spec=1;oracle_base_header_only=which==6;
 db_state.is_static_map=1;db_state.local_server=1;db_state.instance_id=7;db_state.base_map_id=1;
 oracle_spec.teamArea=2;oracle_spec.loadScreenPages=oracle_pages;oracle_static_info.introZone=4;
 register_array(oracle_pages,2);oracle_swap_ptrs[0]=&oracle_swaps[0];oracle_swap_ptrs[1]=&oracle_swaps[1];register_array(oracle_swap_ptrs,2);
 group_info.files=oracle_file_ptrs;group_info.refs=oracle_ref_ptrs;group_info.loadscreen="loading/oracle";
 for(int i=0;i<256;i++){snprintf(oracle_names[i],64,"oracle_large_%04d",i);memset(oracle_values[i],'a'+i%23,192);oracle_values[i][192]=0;oracle_def_ptrs[i]=&oracle_defs[i];}
 for(int i=0;i<3;i++){oracle_file_ptrs[i]=&oracle_files[i];oracle_files[i].fullname=i==0?"maps/oracle_world.txt":i==1?"object_library/oracle_saved.txt":"object_library/oracle_other.txt";oracle_files[i].mod_time=100;oracle_files[i].bounds_checksum=0x11223344u+i;}
 for(int i=0;i<4;i++){oracle_ref_ptrs[i]=&oracle_refs[i];oracle_refs[i].mod_time=100;oracle_identity(oracle_refs[i].mat);}
 /* A full update unconditionally requests compression in worldSendUpdate,
  * therefore packed fixtures must exercise the real incremental path. Every
  * ordinary fixture record has mod_time100 above this zero checkpoint. */
 NetLink link={0};int full_update=aligned?1:0;
 if(which==1){
  group_info.file_count=1;group_info.ref_count=1;oracle_files[0].count=1;oracle_files[0].defs=oracle_def_ptrs;
  oracle_simple(&oracle_defs[0],0,"oracle_root");oracle_refs[0].def=&oracle_defs[0];
 }else if(which==2||which==3||which==8){
  group_info.file_count=3;group_info.ref_count=4;
  oracle_files[0].count=3;oracle_files[0].defs=oracle_def_ptrs;
  oracle_files[1].count=1;oracle_files[1].defs=oracle_library_ptrs;oracle_library_ptrs[0]=&oracle_defs[3];
  oracle_files[2].count=1;oracle_files[2].defs=oracle_other_ptrs;oracle_other_ptrs[0]=&oracle_defs[4];
  oracle_rich(&oracle_defs[0],0);oracle_defs[0].name="oracle_rich";
  oracle_simple(&oracle_defs[1],1,"oracle_deleted");oracle_defs[1].in_use=0;
  oracle_simple(&oracle_defs[2],2,"oracle_future");
  oracle_simple(&oracle_defs[3],0,"oracle_saved_library");oracle_defs[3].file_idx=1;oracle_defs[3].saved=1;
  oracle_simple(&oracle_defs[4],0,"oracle_other_file");
  oracle_children[0][0].def=&oracle_defs[2];oracle_children[0][1].def=&oracle_defs[3];
  oracle_refs[0].def=&oracle_defs[0];oracle_raw(oracle_refs[0].mat);
  oracle_refs[1].def=0;oracle_refs[2].def=&oracle_defs[2];oracle_position(oracle_refs[2].mat);
  oracle_refs[3].def=&oracle_defs[4];
  if(which==3)link.last_world_id=world_id;
  if(which==8)oracle_files[1].force_reload=1;
 }else if(which==4){
  full_update=0;link.last_world_id=world_id;link.last_update_time=50;
  group_info.file_count=2;group_info.ref_count=4;
  oracle_files[0].count=2;oracle_files[0].defs=oracle_def_ptrs;
  oracle_files[1].count=1;oracle_files[1].defs=oracle_library_ptrs;oracle_files[1].mod_time=10;oracle_library_ptrs[0]=&oracle_defs[2];
  oracle_simple(&oracle_defs[0],0,"oracle_root");oracle_defs[0].mod_time=10;
  oracle_simple(&oracle_defs[1],1,"oracle_deleted");oracle_defs[1].in_use=0;
  oracle_simple(&oracle_defs[2],0,"oracle_saved_library");oracle_defs[2].file_idx=1;oracle_defs[2].saved=1;
  oracle_refs[0].def=&oracle_defs[0];oracle_refs[0].mod_time=10;
  oracle_refs[1].mod_time=10;oracle_refs[2].def=0;oracle_refs[3].def=&oracle_defs[2];
 }else if(which==5){
  group_info.file_count=1;group_info.ref_count=4;oracle_files[0].count=192;oracle_files[0].defs=oracle_def_ptrs;
  for(int i=0;i<192;i++){oracle_rich(&oracle_defs[i],i);oracle_children[i][0].def=&oracle_defs[(i+1)%192];oracle_children[i][1].def=&oracle_defs[(i+2)%192];}
  for(int i=0;i<4;i++){oracle_refs[i].def=&oracle_defs[i];if(i%2)oracle_raw(oracle_refs[i].mat);else oracle_position(oracle_refs[i].mat);}
 }else if(which==6){
  /* Exact sendGroupFile emits base flag+normal-base flag. The trusted service
   * shim omits the unsupported nested base body. This is a HEADER negative,
   * never a complete base/world grammar or a full scene success fixture. */
  group_info.file_count=1;oracle_files[0].defs=oracle_def_ptrs;oracle_files[0].base=&g_base;
 }else if(which==7){
  group_info.file_count=1;group_info.ref_count=3;oracle_files[0].count=1;oracle_files[0].defs=oracle_def_ptrs;
  oracle_simple(&oracle_defs[0],0,"oracle_matrix");
  for(int i=0;i<3;i++)oracle_refs[i].def=&oracle_defs[0];
  Vec3 angle0={0,0.25f,0},angle1={0,0.5f,0},angle2={0,0,0};
  createMat3YPR(oracle_refs[0].mat,angle0);createMat3YPR(oracle_refs[1].mat,angle1);
  oracle_refs[1].mat[3][0]=0.5f;oracle_refs[1].mat[3][1]=-3.5f;oracle_refs[1].mat[3][2]=1.25f;
  createMat3YPR(oracle_refs[2].mat,angle2);for(int i=0;i<3;i++)oracle_refs[2].mat[i][0]=0;
  for(int i=0;i<3;i++){PackMat p;assert(packMat(oracle_refs[i].mat,&p));assert(p.has_pyr);assert(p.has_scale==(i==2));}
 }else if(which==9){
  group_info.file_count=1;oracle_files[0].count=3;oracle_files[0].defs=oracle_def_ptrs;
  oracle_simple(&oracle_defs[0],0,"oracle_trick_empty");oracle_defs[0].type_name="oracle_type_only";
  oracle_defs[0].no_coll=1;oracle_defs[0].open_tracker=1;
  oracle_simple(&oracle_defs[1],1,"oracle_ambient");oracle_defs[1].has_ambient=1;
  oracle_defs[1].has_tex=1;oracle_defs[1].tex_names[0]="oracle_texture_a";
  oracle_defs[1].has_properties=1;oracle_defs[1].properties=&oracle_properties[1];
  oracle_simple(&oracle_defs[2],2,"oracle_light");oracle_defs[2].has_light=1;
  oracle_defs[2].has_tex=2;oracle_defs[2].tex_names[1]="oracle_texture_b";
  oracle_defs[2].has_alpha=1;oracle_defs[2].groupdef_alpha=0;
 }else if(which==10){
  oracle_has_spec=0;db_state.is_static_map=0;g_MapIsTutorial=1;group_info.loadscreen=0;
 }
 worldSendUpdate(&link,full_update);
 assert(oracle_packet.stream.byteAlignedMode==aligned);
 assert(oracle_packet.compress==aligned);
 *bits=oracle_packet.stream.bitLength;
 assert(*bits<sizeof(oracle_storage)*8-64);memcpy(out,oracle_storage,(*bits+7)/8);
 footer[0]=group_info.file_count;footer[1]=groupInfoRefCount();footer[2]=groupInfoCrcDefs();footer[3]=groupInfoCrcRefs();
 return 1;
}
