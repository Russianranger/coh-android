#include "coh_public_bounds.h"
#include <stdlib.h>
#include <string.h>
#define TRY(x) do{CohStatus st_=(x);if(st_!=COH_OK)return st_;}while(0)
typedef struct {uint32_t first,slots,checksum;} RawFile;
struct CohPublicBounds {CohCatalogOwner*catalog;uint8_t*bytes;uint32_t*offsets;RawFile*files;uint32_t refs;CohPublicBoundsBinding binding;CohPublicBoundsReport report;};
static uint32_t u32(const uint8_t*p){return(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int span(size_t n,size_t at,size_t bytes){return at<=n&&bytes<=n-at;}
static int disjoint(const void*a,size_t an,const void*b,size_t bn){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;if(!an||!bn)return 1;if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 0;return x+an<=y||y+bn<=x;}
static int nonzero(const uint8_t*p){unsigned n=0;for(unsigned i=0;i<32;i++)n|=p[i];return n!=0;}
static int binding_equal(const CohCatalogBinding*a,const CohCatalogBinding*b){return a->owner_generation==b->owner_generation&&a->catalog_generation==b->catalog_generation&&a->asset_generation==b->asset_generation&&a->map_generation==b->map_generation&&!memcmp(a->catalog_sha256,b->catalog_sha256,32)&&!memcmp(a->source_sha256,b->source_sha256,32)&&!memcmp(a->inventory_sha256,b->inventory_sha256,32)&&!memcmp(a->map_sha256,b->map_sha256,32);}
static int prefix(const char*s,const char*p){for(;*p;p++,s++){unsigned c=(unsigned char)*s;if(!c)return 0;if(c>='A'&&c<='Z')c+='a'-'A';if(c!=(unsigned char)*p)return 0;}return 1;}
static int is_public(const char*file,const char*name,uint32_t live){size_t n=strlen(name);return live&&n&&!prefix(name,"grp")&&prefix(file,"object_library")&&name[n-1]!='&';}
static CohStatus string(const uint8_t*p,size_t n){if(!n||n>COH_REP_NAME_MAX||p[n-1]||memchr(p,0,n-1))return COH_STATE;for(size_t i=0;i+1<n;i++)if(p[i]<32||p[i]>126)return COH_UNSUPPORTED;return COH_OK;}
static CohStatus decode(CohPublicBounds*t,size_t size){
 const uint8_t*p=t->bytes;size_t at=96;uint32_t ordinal=0,public_rows=0;
 for(uint32_t f=0;f<t->report.files;f++){
  CohCatalogFileView file;TRY(coh_catalog_owner_file(t->catalog,f,&file));if(!span(size,at,24))return COH_LIMIT;
  const uint8_t*h=p+at;uint32_t name=u32(h+16);if(u32(h)!=f||u32(h+4)!=f||u32(h+8)!=file.bounds_checksum||u32(h+12)!=file.slots||u32(h+20))return COH_STATE;at+=24;
  if(!span(size,at,name))return COH_LIMIT;
  TRY(string(p+at,name));if(strcmp((const char*)p+at,file.name))return COH_STATE;at+=name;
  t->files[f]=(RawFile){ordinal,file.slots,file.bounds_checksum};
  for(uint32_t slot=0;slot<file.slots;slot++,ordinal++){
   if(ordinal>=t->report.slots||!span(size,at,32))return COH_LIMIT;
   h=p+at;t->offsets[ordinal]=(uint32_t)at;at+=32;
   uint32_t id=u32(h+4),allocated=u32(h+8),live=u32(h+12),selected=u32(h+16),names=u32(h+20),raw=u32(h+24);CohCatalogRecordIdentity ci;TRY(coh_catalog_owner_record(t->catalog,f,slot,&ci));
   if(u32(h)!=slot||allocated!=ci.allocated||live!=ci.in_use||selected>1||u32(h+28)||id!=(allocated?slot:UINT32_MAX)||names>(uint32_t)COH_REP_NAME_MAX||raw!=(selected?60u:0u))return COH_STATE;
   if(!span(size,at,(size_t)names+raw))return COH_LIMIT;
   if(live){TRY(string(p+at,names));if(strcmp((const char*)p+at,ci.name))return COH_STATE;}else if(names)return COH_STATE;
   if(selected!=(uint32_t)is_public(file.name,live?(const char*)p+at:"",live))return COH_STATE;
   at+=(size_t)names+raw;public_rows+=selected;
  }
 }
 if(at!=size||ordinal!=t->report.slots||public_rows!=t->report.public_rows)return COH_STATE;
 return COH_OK;
}
void coh_public_bounds_release(CohPublicBounds*t){if(!t||--t->refs)return;coh_catalog_owner_release(t->catalog);free(t->bytes);free(t->files);free(t->offsets);free(t);}
CohStatus coh_public_bounds_retain(CohPublicBounds*t){if(!t)return COH_INVALID;if(t->refs==UINT32_MAX)return COH_LIMIT;t->refs++;return COH_OK;}
static int output_disjoint(const CohPublicBounds*t,const void*out,size_t size){
 CohBytes catalog;if(coh_catalog_owner_bytes(t->catalog,&catalog)!=COH_OK)return 0;
 return disjoint(out,size,t,sizeof(*t))&&disjoint(out,size,t->bytes,u32(t->bytes+16))&&disjoint(out,size,t->files,(size_t)t->report.files*sizeof(RawFile))&&disjoint(out,size,t->offsets,(size_t)t->report.slots*sizeof(uint32_t))&&disjoint(out,size,catalog.data,catalog.size);
}
CohStatus coh_public_bounds_binding(const CohPublicBounds*t,CohPublicBoundsBinding*out){if(!t||!out||!output_disjoint(t,out,sizeof(*out)))return COH_INVALID;*out=t->binding;return COH_OK;}
CohStatus coh_public_bounds_report(const CohPublicBounds*t,CohPublicBoundsReport*out){if(!t||!out||!output_disjoint(t,out,sizeof(*out)))return COH_INVALID;*out=t->report;return COH_OK;}
CohStatus coh_public_bounds_create(const CohPublicBounds*old,CohCatalogOwner*catalog,CohBytes input,const CohPublicBoundsBinding*b,const CohPublicBoundsBudget*budget,const CohCatalogDigest*d,CohPublicBounds**out,CohPublicBoundsReport*report){
 if(!catalog||!input.data||!b||!budget||!d||!d->sha256||!out||!report)return COH_INVALID;
 CohBytes cat;CohCatalogBinding actual;TRY(coh_catalog_owner_bytes(catalog,&cat));TRY(coh_catalog_owner_binding(catalog,&actual));
 const void*p[]={input.data,b,budget,d,out,report,cat.data};size_t n[]={input.size,sizeof(*b),sizeof(*budget),sizeof(*d),sizeof(*out),sizeof(*report),cat.size};
 for(unsigned i=0;i<7;i++)for(unsigned j=i+1;j<7;j++)if(!disjoint(p[i],n[i],p[j],n[j]))return COH_INVALID;
 if(old)for(unsigned i=0;i<6;i++)if(!output_disjoint(old,p[i],n[i]))return COH_INVALID;
 if(*out||!b->generation||(old&&(old->binding.generation==UINT32_MAX||b->generation!=old->binding.generation+1u))||(!old&&b->generation!=1u)||!binding_equal(&actual,&b->catalog)||!nonzero(b->raw_sha256)||!nonzero(b->run_sha256))return COH_STATE;
 if(old&&(b->catalog.catalog_generation<old->binding.catalog.catalog_generation||(b->catalog.catalog_generation==old->binding.catalog.catalog_generation&&!binding_equal(&b->catalog,&old->binding.catalog))))return COH_STATE;
 if(input.size<96)return COH_LIMIT;
 if(input.size>COH_PUBLIC_BOUNDS_INPUT_MAX||cat.size<48)return COH_LIMIT;
 const uint8_t*h=input.data;uint32_t files=u32(h+80),slots=u32(h+84),rows=u32(h+88);
 if(memcmp(h,"COHRBW01",8)||u32(h+8)!=1||u32(h+12)!=96||u32(h+16)!=input.size||u32(h+20)!=actual.catalog_generation||u32(h+24)!=1||u32(h+28)!=60||memcmp(h+32,cat.data,48)||files!=u32(cat.data+24)||files>1024||slots>65536||rows>slots||u32(h+92))return COH_STATE;
 size_t owned=sizeof(CohPublicBounds)+input.size+(size_t)files*sizeof(RawFile)+(size_t)slots*sizeof(uint32_t),total=budget->retained_bytes,limit=budget->aggregate_limit;
 if(!limit||limit>COH_SG_TRANSACTION_MAX||budget->owned_limit>COH_SG_MEMORY_MAX||owned>budget->owned_limit||total>limit)return COH_LIMIT;
 size_t add[]={owned,input.size,coh_catalog_owner_owned_bytes(catalog),old?old->report.owned_bytes:0,old&&old->catalog!=catalog?coh_catalog_owner_owned_bytes(old->catalog):0,COH_PUBLIC_BOUNDS_STACK_RESERVE};
 for(unsigned i=0;i<sizeof(add)/sizeof(add[0]);i++){if(add[i]>limit-total)return COH_LIMIT;total+=add[i];}
 CohPublicBounds*t=calloc(1,sizeof(*t));if(!t)return COH_LIMIT;t->refs=1;t->binding=*b;t->report=(CohPublicBoundsReport){files,slots,rows,60,owned,total,0,0,0,0};
 t->bytes=malloc(input.size);t->files=files?calloc(files,sizeof(RawFile)):NULL;t->offsets=slots?calloc(slots,sizeof(uint32_t)):NULL;
 if(!t->bytes||(files&&!t->files)||(slots&&!t->offsets)){coh_public_bounds_release(t);return COH_LIMIT;}memcpy(t->bytes,input.data,input.size);
 uint8_t hash[32];CohStatus status=d->sha256(d->context,(CohBytes){t->bytes,input.size},hash);if(status==COH_OK&&memcmp(hash,b->raw_sha256,32))status=COH_STATE;
 if(status==COH_OK)status=coh_catalog_owner_retain(catalog);
 if(status==COH_OK){t->catalog=catalog;status=decode(t,input.size);}
 if(status!=COH_OK){coh_public_bounds_release(t);return status;}
 *out=t;*report=t->report;return COH_OK;
}
CohStatus coh_public_bounds_row(const CohPublicBounds*t,uint32_t file,uint32_t slot,CohPublicBoundsRow*out){
 if(!t||!out||!output_disjoint(t,out,sizeof(*out)))return COH_INVALID;
 if(file>=t->report.files||slot>=t->files[file].slots)return COH_STATE;
 const uint8_t*p=t->bytes+t->offsets[t->files[file].first+slot];uint32_t n=u32(p+20),raw=u32(p+24);CohPublicBoundsRow r={file,slot,u32(p+8),u32(p+12),u32(p+16),n?(const char*)p+32:NULL,{raw?p+32+n:NULL,raw}};*out=r;return COH_OK;
}
static uint32_t adler(uint32_t v,const uint8_t*p,size_t n){uint32_t a=v&65535u,b=v>>16;for(size_t i=0;i<n;i++){a=(a+p[i])%65521u;b=(b+a)%65521u;}return b<<16|a;}
CohStatus coh_public_bounds_compare_token(const CohPublicBounds*t,uint32_t file,CohPublicBoundsToken*out){
 if(!t||!out||!output_disjoint(t,out,sizeof(*out)))return COH_INVALID;
 if(!file)return COH_UNSUPPORTED;
 if(file>=t->report.files)return COH_STATE;
 if(!disjoint(out,sizeof(*out),t,sizeof(*t))||!disjoint(out,sizeof(*out),t->bytes,u32(t->bytes+16))||!disjoint(out,sizeof(*out),t->files,(size_t)t->report.files*sizeof(RawFile))||!disjoint(out,sizeof(*out),t->offsets,(size_t)t->report.slots*sizeof(uint32_t)))return COH_INVALID;
 CohPublicBoundsToken result={0};uint32_t crc=1;
 for(uint32_t s=0;s<t->files[file].slots;s++){CohPublicBoundsRow row;TRY(coh_public_bounds_row(t,file,s,&row));if(!row.is_public)continue;size_t n=strlen(row.name);crc=adler(crc,row.raw.data,60);crc=adler(crc,(const uint8_t*)row.name,n);result.public_rows++;result.bytes_hashed+=60+n;}
 result.checksum=crc<<24|(crc&0xff00u)<<8|(crc&0xff0000u)>>8|crc>>24;
 if(result.checksum!=t->files[file].checksum)return COH_STATE;
 *out=result;return COH_OK;
}
