/* Trusted host-only original-source inputs. Never linked into an application. */
static void pktFree(Packet *p){assert(p==&oracle_packet);}
#include "source_export.inc"
typedef struct {U8 *out;U32 size,capacity,fail_after,mutate;} CatalogSink;
static int catalog_output(void *context,const unsigned char *bytes,unsigned int n){
 CatalogSink *s=context;if(s->fail_after&&s->size+n>s->fail_after)return 0;
 assert(n<=s->capacity-s->size);memcpy(s->out+s->size,bytes,n);s->size+=n;
 if(s->mutate==1){group_info.file_count++;s->mutate=0;}
 if(s->mutate==3){group_info.ref_count=65537;group_info.refs=(DefTracker **)1;s->mutate=0;}return 1;
}
static GroupDef catalog_large_defs[508*24];
static GroupDef *catalog_large_ptrs[508*24];
static GroupFile catalog_large_files[508];static GroupFile *catalog_large_files_ptrs[508];
static GroupEnt catalog_large_children[508*24][5];
static DefTracker catalog_large_refs[33];static DefTracker *catalog_large_refptrs[33];
static char catalog_large_names[508*24][32],catalog_large_filenames[508][64];
static void catalog_large(unsigned edges){
 memset(catalog_large_defs,0,sizeof(catalog_large_defs));memset(catalog_large_files,0,sizeof(catalog_large_files));
 group_info.file_count=508;group_info.files=catalog_large_files_ptrs;group_info.ref_count=33;group_info.refs=catalog_large_refptrs;
 for(int f=0;f<508;f++){
  GroupFile *file=&catalog_large_files[f];catalog_large_files_ptrs[f]=file;
  snprintf(catalog_large_filenames[f],64,f?"object_library/stress/library_%04d.txt":"maps/oracle_world.txt",f);
  file->fullname=catalog_large_filenames[f];file->count=24;file->defs=catalog_large_ptrs+f*24;file->mod_time=100;file->bounds_checksum=0x11223344u+f;
  for(int n=0;n<24;n++){
   int i=f*24+n;GroupDef *def=&catalog_large_defs[i];catalog_large_ptrs[i]=def;
   snprintf(catalog_large_names[i],32,"catalog_stress_%05d",i);oracle_simple(def,n,catalog_large_names[i]);def->file_idx=1;def->saved=1;
   if(i<508*24-3){def->count=edges;def->entries=catalog_large_children[i];for(unsigned j=0;j<edges;j++){def->entries[j].def=&catalog_large_defs[508*24-1];oracle_identity(def->entries[j].mat);}}
  }
 }
 catalog_large_defs[508*24-3].in_use=0;
 for(int i=0;i<33;i++){catalog_large_refptrs[i]=&catalog_large_refs[i];catalog_large_refs[i].def=&catalog_large_defs[i*24];catalog_large_refs[i].mod_time=100;oracle_identity(catalog_large_refs[i].mat);}
}
/* mode 1 mutates snapshot through a deliberately hostile test callback; mode2
 * rejects callback output after its header; mode3 changes root slots beyond
 * admission after the header and supplies an inaccessible tracker pointer. Neither produces accepted output. */
int catalog_original(U32 which,U32 aligned,U32 legacy,U32 mode,U8 *out,U32 *size,U8 *wire,U32 *bits,U32 *source_report){
 U32 footer[4];if(!groups_original((which==20||which==22)?1:which==21?2:which,aligned,legacy,wire,bits,footer))return -1;
 if(which==20||which==22){catalog_large(which==22?5:3);NetLink link={0};worldSendUpdate(&link,aligned?1:0);*bits=oracle_packet.stream.bitLength;memcpy(wire,oracle_storage,(*bits+7)/8);}
 if(which==21)oracle_def_ptrs[1]=NULL;
 CatalogSink sink={out,0,32u*1024u*1024u,mode==2?48u:0u,(mode==1||mode==3)?mode:0};CohSourceCatalogExportReport report;
 int result=coh_source_catalog_export(catalog_output,&sink,7,&report);*size=sink.size;
 source_report[0]=report.files;source_report[1]=report.definitions;source_report[2]=report.slots;source_report[3]=report.children;source_report[4]=report.wire_bytes;source_report[5]=report.total_bytes;source_report[6]=report.emitted_bytes;
 return result;
}
/* Independent unchanged sendDef invocation for byte-for-byte exporter checks. */
int catalog_record_original(U32 file,U32 slot,U8 *out,U32 *size){
 if(file>=(U32)group_info.file_count||slot>=(U32)group_info.files[file]->count||!group_info.files[file]->defs[slot])return 0;
 Packet *p=pktCreate();pktSetCompression(p,1);sendDef(p,group_info.files[file]->defs[slot]);assert(!p->stream.errorFlags);
 *size=(p->stream.bitLength+7)/8;memcpy(out,p->stream.data,*size);pktFree(p);return 1;
}
unsigned catalog_source_negatives(U8 *wire){
 unsigned accepted=0;U32 bits,footer[4];
 for(unsigned kind=0;kind<7;kind++){
  assert(groups_original(2,1,0,wire,&bits,footer));
  if(kind==1)oracle_files[1].fullname=oracle_files[0].fullname;
  if(kind==2)oracle_defs[0].id++;
  if(kind==3)oracle_files[0].fullname="maps/nonascii_\177.txt";
  if(kind==4)oracle_children[0][0].def=NULL;
  if(kind==5)oracle_defs[0].name="invalid\001name";
  if(kind==6){group_info.ref_count=65537;group_info.refs=(DefTracker **)1;}
  CatalogSink sink={wire,0,1u<<20,0,0};CohSourceCatalogExportReport report;
  int status=coh_source_catalog_export(catalog_output,&sink,kind?7:0,&report);
  assert(status==(kind==6?COH_SOURCE_CATALOG_LIMIT:kind?COH_SOURCE_CATALOG_SOURCE:COH_SOURCE_CATALOG_ARGUMENT));assert(!sink.size);accepted++;
 }
 return accepted;
}
