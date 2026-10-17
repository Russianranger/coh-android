#include "source_groups_eligibility.inc"
int main(int argc,char**argv){unsigned mode;assert(argc==2);
 for(mode=0;mode<4;mode++){
  SnapshotOutput cat={snapshot_catalog,0,sizeof(snapshot_catalog),0},side={snapshot_sidecar,0,sizeof(snapshot_sidecar),0};CohSourceSnapshotReport sr;CohGroupsEligibilityReport er;unsigned char raw[65536];SnapshotOutput witness={raw,0,sizeof(raw),0};NetLink link={0};char name[80];unsigned f,i;
  snapshot_setup(0,0);
  for(f=0;f<(unsigned)group_info.file_count;f++){group_info.files[f]->force_reload=0;group_info.files[f]->modified_on_disk=0;for(i=0;i<(unsigned)group_info.files[f]->count;i++){group_info.files[f]->defs[i]->saved=0;group_info.files[f]->defs[i]->file_idx=0;}}
  if(mode){group_info.files[0]->defs[0]->saved=1;group_info.files[0]->defs[0]->file_idx=65535;}
  if(mode==2)group_info.files[0]->force_reload=1;
  if(mode==3)group_info.files[0]->modified_on_disk=1;
  assert(snapshot_pair(&cat,&side,&sr)==0);
  assert(coh_source_groups_eligibility(&link,1,7,snapshot_write,&witness,&er));
  worldSendUpdate(&link,1);assert(oracle_packet.stream.bitLength%8==0);
  snprintf(name,sizeof(name),"witness-%u.cohcat",mode);snapshot_save(argv[1],name,cat.data,cat.size);
  snprintf(name,sizeof(name),"witness-%u.cohrts",mode);snapshot_save(argv[1],name,side.data,side.size);
  snprintf(name,sizeof(name),"witness-%u.groups",mode);snapshot_save(argv[1],name,(unsigned char*)oracle_storage,oracle_packet.stream.bitLength/8);
  snprintf(name,sizeof(name),"witness-%u.eligibility",mode);snapshot_save(argv[1],name,witness.data,witness.size);
 }
 puts("{\"fixtures\":4,\"original_world_producer\":true,\"actual_server\":false}");return 0;
}
