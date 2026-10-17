/* NONSHIPPING: include in groupnetsend.c after original declarations.
 * Read-only PRE-worldSendUpdate observer. Exclusive owner thread, no yield,
 * lazy loads or callbacks into the engine; every output is provisional.
 * Records do not establish a catalog generation or live receive authority.
 */
#ifndef COH_SOURCE_GROUPS_ELIGIBILITY_INCLUDED
#define COH_SOURCE_GROUPS_ELIGIBILITY_INCLUDED
#define COH_GROUPS_ELIGIBILITY_MAX_FILES 4096u
#define COH_GROUPS_ELIGIBILITY_MAX_DEFS 65536u
#define COH_GROUPS_ELIGIBILITY_MAX_REFS 65536u
/* Fixed 64-byte LE records; kind1 begin,2 file,3 definition,4 root,5 end.
 * No native pointers, struct padding, inferred saved state or default flags. */
typedef int (*CohGroupsEligibilityOutput)(void*,const unsigned char*,unsigned);
typedef struct CohGroupsEligibilityReport {
 unsigned records,files,slots,roots,present_files,emitted_defs,emitted_roots;
} CohGroupsEligibilityReport;
static int coh_groups_file_present(const GroupFile*f,const NetLink*l,int full)
{ return !((!full && f->mod_time<=l->last_update_time)&&!f->force_reload); }
static int coh_groups_def_present(const GroupFile*f,const GroupDef*d,const NetLink*l,int full)
{
 if(!coh_groups_file_present(f,l,full))return 0;
 if(!f->force_reload){
  if(!full&&d->mod_time<=l->last_update_time)return 0;
  if(!f->modified_on_disk&&d->file_idx&&d->saved)return 0;
 }
 return 1;
}
static int coh_groups_eligibility_record(CohGroupsEligibilityOutput fn,void*ctx,unsigned*v)
{
 unsigned char raw[64];unsigned i;
 for(i=0;i<16;i++){raw[i*4]=(unsigned char)v[i];raw[i*4+1]=(unsigned char)(v[i]>>8);raw[i*4+2]=(unsigned char)(v[i]>>16);raw[i*4+3]=(unsigned char)(v[i]>>24);}
 return fn(ctx,raw,64)==1;
}
/* Returns 1 success,0 arguments/unsupported/limits/output refusal. out is only
 * committed after the final record succeeds; callback bytes must be discarded
 * on any failure. A successful sink still needs exact packet + same-boundary
 * catalog/runtime/run identity binding before admission. */
static int coh_source_groups_eligibility(const NetLink*link,int full_update,
 unsigned observation_id,CohGroupsEligibilityOutput fn,void*ctx,
 CohGroupsEligibilityReport*out)
{
 CohGroupsEligibilityReport r;unsigned v[16],f,i,total=0,active=0;GroupFile*file;GroupDef*d;DefTracker*ref;
 if(!link||!fn||!out||!observation_id||(full_update!=0&&full_update!=1)||g_isBaseRaid||group_info.file_count<0||(unsigned)group_info.file_count>COH_GROUPS_ELIGIBILITY_MAX_FILES||group_info.ref_count<0||(unsigned)group_info.ref_count>COH_GROUPS_ELIGIBILITY_MAX_REFS||(group_info.file_count&&!group_info.files)||(group_info.ref_count&&!group_info.refs))return 0;
 /* Preflight every pointer and special-file branch before emitting anything.
  * Caller owns valid original structs and disjoint report/sink/context. */
 for(f=0;f<(unsigned)group_info.file_count;f++){
  file=group_info.files[f];if(!file||file->count<0||(unsigned)file->count>COH_GROUPS_ELIGIBILITY_MAX_DEFS-total||(file->count&&!file->defs)||file->base)return 0;
  total+=(unsigned)file->count;
  for(i=0;i<(unsigned)file->count;i++)if(!file->defs[i])return 0;
 }
 for(i=0;i<(unsigned)group_info.ref_count;i++){if(!group_info.refs[i])return 0;active+=(group_info.refs[i]->def!=NULL);}
 memset(&r,0,sizeof(r));memset(v,0,sizeof(v));
 v[0]=1;v[1]=1;v[2]=observation_id;v[3]=(unsigned)full_update;v[4]=link->last_update_time;v[5]=(unsigned)link->last_world_id;v[6]=(unsigned)world_id;v[7]=(unsigned)group_info.file_count;v[8]=total;v[9]=(unsigned)group_info.ref_count;v[10]=active;v[13]=(unsigned)(link->last_world_id!=world_id);
 if(!coh_groups_eligibility_record(fn,ctx,v))return 0;r.records++;
 /* Source send order: files1..N-1 then0. Preserve slot order incl inactive. */
 for(f=0;f<(unsigned)group_info.file_count;f++){
  unsigned index=(f+1u)%(unsigned)group_info.file_count;
  file=group_info.files[index];memset(v,0,sizeof(v));v[0]=2;v[1]=index;v[2]=file->mod_time;v[3]=(unsigned)file->force_reload;v[4]=(unsigned)file->modified_on_disk;v[5]=(unsigned)file->count;v[6]=file->bounds_checksum;v[7]=(unsigned)coh_groups_file_present(file,link,full_update);
  if(!coh_groups_eligibility_record(fn,ctx,v))return 0;r.records++;r.files++;r.present_files+=v[7];
  for(i=0;i<(unsigned)file->count;i++){
   d=file->defs[i];memset(v,0,sizeof(v));v[0]=3;v[1]=index;v[2]=i;v[3]=(unsigned)d->id;v[4]=d->mod_time;v[5]=(unsigned)d->file_idx;v[6]=(unsigned)d->saved;v[7]=(unsigned)d->in_use;v[8]=(unsigned)coh_groups_def_present(file,d,link,full_update);
   if(!coh_groups_eligibility_record(fn,ctx,v))return 0;r.records++;r.slots++;r.emitted_defs+=v[8];
  }
 }
 for(i=0;i<(unsigned)group_info.ref_count;i++){
  ref=group_info.refs[i];memset(v,0,sizeof(v));v[0]=4;v[1]=i;v[2]=ref->mod_time;v[3]=(unsigned)(ref->def!=NULL);v[4]=(unsigned)(full_update||ref->mod_time>link->last_update_time);
  if(!coh_groups_eligibility_record(fn,ctx,v))return 0;r.records++;r.roots++;r.emitted_roots+=v[4];
 }
 memset(v,0,sizeof(v));v[0]=5;v[1]=r.records+1;v[2]=r.files;v[3]=r.slots;v[4]=r.roots;v[5]=r.present_files;v[6]=r.emitted_defs;v[7]=r.emitted_roots;
 if(!coh_groups_eligibility_record(fn,ctx,v))return 0;r.records++;*out=r;return 1;
}
#endif
