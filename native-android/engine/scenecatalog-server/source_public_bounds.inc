/* UNINSTALLED NONSHIPPING raw source prefix observer. Include after the actual
 * original GroupBounds/GroupDef/GroupFile types and catalog exporter. The caller
 * holds exclusive group ownership and the real model-quiet lease continuously
 * with owner/eligibility/packet observations. Callbacks copy only, never yield,
 * load/mutate/reenter. No native layout or generation authority is inferred. */
#ifndef COH_SOURCE_PUBLIC_BOUNDS_INCLUDED
#define COH_SOURCE_PUBLIC_BOUNDS_INCLUDED
#include <stddef.h>
#define COH_RAW_BOUNDS_MAX_BYTES (32u*1024u*1024u)
#define COH_RAW_BOUNDS_HEADER_BYTES 96u
#define COH_RAW_BOUNDS_BYTES 60u
#define COH_RAW_LAYOUT_ASSERT(n,test) typedef char CohRawLayout_##n[(test)?1:-1]
COH_RAW_LAYOUT_ASSERT(float4,sizeof(F32)==4);
COH_RAW_LAYOUT_ASSERT(int4,sizeof(int)==4);
COH_RAW_LAYOUT_ASSERT(bounds60,sizeof(GroupBounds)==60);
#define COH_RAW_PREFIX(n,at) COH_RAW_LAYOUT_ASSERT(bounds_##n,offsetof(GroupBounds,n)==at);COH_RAW_LAYOUT_ASSERT(def_##n,offsetof(GroupDef,n)==at)
COH_RAW_PREFIX(min,0);COH_RAW_PREFIX(max,12);COH_RAW_PREFIX(mid,24);
COH_RAW_PREFIX(vis_dist,36);COH_RAW_PREFIX(radius,40);COH_RAW_PREFIX(lod_scale,44);
COH_RAW_PREFIX(shadow_dist,48);COH_RAW_PREFIX(recursive_count,52);
#undef COH_RAW_PREFIX
#undef COH_RAW_LAYOUT_ASSERT
static unsigned coh_raw_bounds_u32(const unsigned char*p)
{return(unsigned)p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
typedef struct CohSourcePublicBoundsReport {unsigned status,total_bytes,emitted_bytes,files,slots,public_rows;} CohSourcePublicBoundsReport;
static int coh_source_public_bounds_export(CohSourceCatalogOutputFn output,void*context,
 const unsigned char catalog_header[48],const CohSourceCatalogExportReport*catalog,
 CohSourcePublicBoundsReport*report)
{
 unsigned pass,f,i,total=96,slots=0,public_rows=0,emitted=0,one=1;
 unsigned char header[96],fields[32];GroupFile*file;GroupDef*d;unsigned name,selected,allocated,active,n;
 if(!report)return COH_SOURCE_CATALOG_ARGUMENT;
 memset(report,0,sizeof(*report));
 if(!output||!catalog_header||!catalog||catalog->status||catalog->total_bytes!=catalog->emitted_bytes||((unsigned char*)&one)[0]!=1u)return report->status=COH_SOURCE_CATALOG_ARGUMENT;
 if(memcmp(catalog_header,"COHCAT01",8)||coh_raw_bounds_u32(catalog_header+8)!=1||coh_raw_bounds_u32(catalog_header+12)!=48||coh_raw_bounds_u32(catalog_header+16)!=catalog->total_bytes||!coh_raw_bounds_u32(catalog_header+20)||group_info.file_count<0||(unsigned)group_info.file_count>COH_SOURCE_CATALOG_MAX_FILES||catalog->files!=(unsigned)group_info.file_count||coh_raw_bounds_u32(catalog_header+24)!=catalog->files||(group_info.file_count&&!group_info.files))return report->status=COH_SOURCE_CATALOG_SOURCE;
 for(pass=0;pass<2;pass++){
  unsigned pass_slots=0,pass_public=0,pass_bytes=96;
  for(f=0;f<(unsigned)group_info.file_count;f++){
   file=group_info.files[f];
   if(!file||file->idx!=(int)f||file->count<0||(unsigned)file->count>COH_SOURCE_CATALOG_MAX_SLOTS-pass_slots||(file->count&&!file->defs))return report->status=COH_SOURCE_CATALOG_SOURCE;
   name=coh_source_catalog_name_bytes(file->fullname);if(!name)return report->status=COH_SOURCE_CATALOG_SOURCE;
   if(24u+name>COH_RAW_BOUNDS_MAX_BYTES-pass_bytes)return report->status=COH_SOURCE_CATALOG_LIMIT;
   pass_bytes+=24u+name;
   if(pass){memset(fields,0,24);coh_source_catalog_put_u32(fields,f);coh_source_catalog_put_u32(fields+4,(unsigned)file->idx);coh_source_catalog_put_u32(fields+8,file->bounds_checksum);coh_source_catalog_put_u32(fields+12,(unsigned)file->count);coh_source_catalog_put_u32(fields+16,name);if(output(context,fields,24)!=1||output(context,(const unsigned char*)file->fullname,name)!=1)return report->status=COH_SOURCE_CATALOG_OUTPUT;emitted+=24u+name;}
   for(i=0;i<(unsigned)file->count;i++){
    d=file->defs[i];allocated=d!=NULL;active=d&&d->in_use;name=0;selected=0;
    if(d&&(d->id!=(int)i||(active&&d->file!=file)))return report->status=COH_SOURCE_CATALOG_SOURCE;
    if(active){name=coh_source_catalog_name_bytes(d->name);if(!name)return report->status=COH_SOURCE_CATALOG_SOURCE;}
    selected=(unsigned)(groupIsPublic(d)!=0);if(selected&&!active)return report->status=COH_SOURCE_CATALOG_SOURCE;
    n=32u+name+(selected?60u:0u);if(n>COH_RAW_BOUNDS_MAX_BYTES-pass_bytes)return report->status=COH_SOURCE_CATALOG_LIMIT;pass_bytes+=n;pass_public+=selected;pass_slots++;
    if(pass){memset(fields,0,sizeof(fields));coh_source_catalog_put_u32(fields,i);coh_source_catalog_put_u32(fields+4,d?(unsigned)d->id:0xffffffffu);coh_source_catalog_put_u32(fields+8,allocated);coh_source_catalog_put_u32(fields+12,active);coh_source_catalog_put_u32(fields+16,selected);coh_source_catalog_put_u32(fields+20,name);coh_source_catalog_put_u32(fields+24,selected?60u:0u);
     if(output(context,fields,32)!=1||(name&&output(context,(const unsigned char*)d->name,name)!=1)||(selected&&output(context,(const unsigned char*)d->min,sizeof(GroupBounds))!=1))return report->status=COH_SOURCE_CATALOG_OUTPUT;emitted+=n;
    }
   }
  }
  if(!pass){total=pass_bytes;slots=pass_slots;public_rows=pass_public;if(slots!=catalog->slots)return report->status=COH_SOURCE_CATALOG_CHANGED;
   memset(header,0,sizeof(header));memcpy(header,"COHRBW01",8);coh_source_catalog_put_u32(header+8,1);coh_source_catalog_put_u32(header+12,96);coh_source_catalog_put_u32(header+16,total);coh_source_catalog_put_u32(header+20,coh_raw_bounds_u32(catalog_header+20));coh_source_catalog_put_u32(header+24,1);coh_source_catalog_put_u32(header+28,60);memcpy(header+32,catalog_header,48);coh_source_catalog_put_u32(header+80,catalog->files);coh_source_catalog_put_u32(header+84,slots);coh_source_catalog_put_u32(header+88,public_rows);
   if(output(context,header,sizeof(header))!=1)return report->status=COH_SOURCE_CATALOG_OUTPUT;emitted=96;
  }else if(pass_bytes!=total||pass_slots!=slots||pass_public!=public_rows)return report->status=COH_SOURCE_CATALOG_CHANGED;
 }
 report->total_bytes=total;report->emitted_bytes=emitted;report->files=catalog->files;report->slots=slots;report->public_rows=public_rows;return 0;
}
#endif
