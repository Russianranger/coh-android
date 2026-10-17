/* Appended to generated host original-source oracle, never shipping renderer. */
static void reset(void){load_calls=errors=lock_calls=unlock_calls=0;observed_load=0;observed_key[0]=0;skeleton_absent=0;expected_shared=0;}
static void free_lods(ModelLODInfo*m){for(unsigned i=0;i<eaSize(&m->lods);i++)free(m->lods[i]);free(m->lods);m->lods=NULL;}
int main(void){
 reset();CHECK(setStAnim(NULL)==0);CHECK(load_calls==0);
 for(unsigned n=0;n<sizeof(actual_st_names)/sizeof(*actual_st_names);n++)for(unsigned delivery=0;delivery<6;delivery++)for(unsigned shared=0;shared<2;shared++){
  reset();expected_shared=(int)shared;tracks[0].id=delivery==3?0:7;tracks[1].id=delivery==4?1:8;if(delivery==5){tracks[0].id=0;tracks[1].id=1;}skeleton=(SkeletonAnimTrack){delivery==1?0:2,tracks};skeleton_absent=delivery==0;
  StAnim first={0},second={0};first.name=(char*)actual_st_names[n];second.name="must_not_load_second";StAnim*children[]={&first,&second,NULL};TrickInfo trick={0};trick.stAnim=children;
  original_setup_animation(&trick,(int)shared);char key[256];int written=snprintf(key,sizeof(key),"tscroll/%s",actual_st_names[n]);CHECK(written>0&&(unsigned)written<sizeof(key));CHECK(load_calls==1);CHECK(!strcmp(observed_key,key));CHECK(lock_calls==shared&&unlock_calls==shared);
#ifdef SERVER
  CHECK(observed_load==LOAD_ALL_SHARED);
#else
  CHECK(observed_load==LOAD_ALL);
#endif
  int ok=delivery>=3;CHECK(!!(trick.tnode.flags2&TRICK2_STANIMATE)==ok);CHECK(errors==(unsigned)!ok);CHECK(second.btTex0==NULL&&second.btTex1==NULL);CHECK((first.btTex0!=NULL)==(delivery==3||delivery==5));CHECK((first.btTex1!=NULL)==(delivery==4||delivery==5));
 }
 reset();TrickInfo empty={0};original_setup_animation(&empty,1);CHECK(load_calls==0&&unlock_calls==0&&lock_calls==0);
 for(unsigned row=0;row<sizeof(actual_lod_cases)/sizeof(*actual_lod_cases);row++)for(unsigned force=0;force<2;force++)for(unsigned nolod=0;nolod<2;nolod++)for(unsigned present=0;present<3;present++){
  AutoLOD*ptrs[257];unsigned count=actual_lod_cases[row].count;CHECK(count<256);for(unsigned i=0;i<count;i++)ptrs[i]=actual_lod_cases[row].rows+i;ptrs[count]=NULL;TrickInfo trick={0};trick.auto_lod=present==2?NULL:ptrs;ModelLODInfo model={0};model.force_auto=(int)force;
  original_copy_branch(&model,(int)nolod,present==0?NULL:&trick,321.f,45.f);int active=!force&&!nolod&&present==1;CHECK(model.bits.is_from_trick==(unsigned)active);CHECK(eaSize(&model.lods)==(active?count:0));
  int done=0;for(unsigned i=0;i<(active?count:0);i++){AutoLOD want=*ptrs[i];if(!done){if(!want.lod_far){want.lod_far=321.f;done=1;}if(!want.lod_farfade){want.lod_farfade=45.f;done=1;}}AutoLOD*got=model.lods[i];CHECK(got!=ptrs[i]);CHECK(got->max_error==want.max_error&&got->lod_near==want.lod_near&&got->lod_nearfade==want.lod_nearfade&&got->lod_far==want.lod_far&&got->lod_farfade==want.lod_farfade);CHECK(got->flags==want.flags&&got->lod_modelname==want.lod_modelname&&got->lod_filename==NULL&&!got->modelname_specified);}free_lods(&model);
 }
 /* First-missing far/fade pair stops replacement on later children. */
 AutoLOD a={0},b={0};AutoLOD*parts[]={&a,&b,NULL};TrickInfo t={0};t.auto_lod=parts;ModelLODInfo m={0};original_copy_branch(&m,0,&t,9.f,3.f);CHECK(m.lods[0]->lod_far==9.f&&m.lods[0]->lod_farfade==3.f);CHECK(m.lods[1]->lod_far==0&&m.lods[1]->lod_farfade==0);free_lods(&m);
 printf("{\"passed\":true,\"checks\":%u,\"actual_stanim_keys\":%zu,\"actual_autolod_rows\":%zu,\"storage_loader_observers\":true,\"actual_animation_resource_loaded\":false}\n",checks,sizeof(actual_st_names)/sizeof(*actual_st_names),sizeof(actual_lod_cases)/sizeof(*actual_lod_cases));return 0;
}
