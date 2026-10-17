#include <strings.h>
#define strnicmp strncasecmp
static int objectLibraryLoadBoundsFile(const char*n,U32 c){(void)n;(void)c;return 1;}
static void objectLibraryWriteBoundsFile(GroupFile*f){(void)f;abort();}
/* ORIGINAL_PUBLIC_FUNCTIONS */
#include "source_public_bounds.inc"
static unsigned char raw_output[1u<<20];
int main(int argc,char**argv){unsigned mode,f,i;assert(argc==2);
 for(mode=0;mode<8;mode++){
  CohSourceCatalogExportReport catalog;CohSourcePublicBoundsReport report;SnapshotOutput cat={snapshot_catalog,0,sizeof(snapshot_catalog),0},raw={raw_output,0,sizeof(raw_output),0};char path[80];
  snapshot_setup(0,0);
  if(mode==2)group_info.files[1]->fullname="OBJECT_LIBRARYX/mixed.txt";
  if(mode==3)group_info.files[1]->defs[0]->name="GRP_local";
  if(mode==4)group_info.files[1]->defs[0]->name="Private&";
  if(mode==5)group_info.files[1]->defs[0]->in_use=0;
  if(mode==6)group_info.files[1]->defs[0]=NULL;
  for(f=0;f<(unsigned)group_info.file_count;f++){
   GroupFile*file=group_info.files[f];file->idx=(int)f;
   for(i=0;i<(unsigned)file->count;i++){GroupDef*d=file->defs[i];if(d)((unsigned char*)d->min)[59]|=0x80;}
   objectLibraryWriteBoundsFileIfDifferent(file);
  }
  if(mode==1)group_info.files[1]->bounds_checksum^=1u;
  if(mode==7)group_info.files[1]->bounds_checksum=0;
  assert(coh_source_catalog_export(snapshot_write,&cat,20261016u,&catalog)==0);
  assert(coh_source_public_bounds_export(snapshot_write,&raw,cat.data,&catalog,&report)==0);
  assert(report.total_bytes==raw.size&&report.emitted_bytes==raw.size&&report.public_rows);
  snprintf(path,sizeof(path),"public-%u.cohcat",mode);snapshot_save(argv[1],path,cat.data,cat.size);snprintf(path,sizeof(path),"public-%u.cohrbw",mode);snapshot_save(argv[1],path,raw.data,raw.size);
  /* Every emitted source prefix is compared directly with its actual object. */
  {unsigned at=96,publics=0;
   for(f=0;f<(unsigned)group_info.file_count;f++){
    GroupFile*file=group_info.files[f];at+=24+coh_snapshot_u32(raw.data+at+16);
    for(i=0;i<(unsigned)file->count;i++){
     unsigned selected=coh_snapshot_u32(raw.data+at+16),names=coh_snapshot_u32(raw.data+at+20),bytes=coh_snapshot_u32(raw.data+at+24);at+=32+names;
     assert(selected==(unsigned)groupIsPublic(file->defs[i])&&bytes==(selected?60u:0u));
     if(selected){assert(!memcmp(raw.data+at,file->defs[i]->min,60));assert(raw.data[at+59]&0x80);publics++;}at+=bytes;
    }
   }assert(at==raw.size&&publics==report.public_rows);
  }
  /* Callback failure discards provisional stream; preflight has no callbacks. */
  {SnapshotOutput failed={raw_output,0,sizeof(raw_output),1};assert(coh_source_public_bounds_export(snapshot_write,&failed,cat.data,&catalog,&report)==COH_SOURCE_CATALOG_OUTPUT);assert(!failed.size);}
  {int saved=group_info.files[1]->idx;group_info.files[1]->idx=0;raw.size=0;assert(coh_source_public_bounds_export(snapshot_write,&raw,cat.data,&catalog,&report)==COH_SOURCE_CATALOG_SOURCE&&!raw.size);group_info.files[1]->idx=saved;}
  {unsigned char saved=cat.data[20];((unsigned char*)cat.data)[20]=0;((unsigned char*)cat.data)[21]=0;((unsigned char*)cat.data)[22]=0;((unsigned char*)cat.data)[23]=0;raw.size=0;assert(coh_source_public_bounds_export(snapshot_write,&raw,cat.data,&catalog,&report)==COH_SOURCE_CATALOG_SOURCE&&!raw.size);((unsigned char*)cat.data)[20]=saved;}
 }
 puts("{\"fixtures\":8,\"original_public_selection_and_writer\":true,\"source_raw_bytes_compared\":true,\"actual_win32_layout\":false,\"actual_server\":false}");return 0;}
