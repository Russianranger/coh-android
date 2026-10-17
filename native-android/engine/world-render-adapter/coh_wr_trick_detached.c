#include "coh_wr_trick_detached.h"
#include "coh_wr_trick_types_internal.h"
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <stdint.h>
#include <math.h>
#include <stdbool.h>
#include "coh_wr_trick_detached_core.inc"
#define SOURCE_OFFSET 12769880u
#define SUFFIX_BYTES 767172u
void coh_wr_trick_detached_release(CohWrTrickDetached**out){if(out&&*out){free(*out);*out=NULL;}}
CohStatus coh_wr_trick_detached_report(const CohWrTrickDetached*c,CohWrTrickDetachedReport*out){if(!c||!out||!output(c,out,sizeof(*out)))return COH_INVALID;*out=c->detached;return COH_OK;}
CohStatus coh_wr_trick_detached_source_bytes(const CohWrTrickDetached*c,CohBytes*out){if(!c||!out||!output(c,out,sizeof(*out)))return COH_INVALID;*out=c->bytes;return COH_OK;}
CohStatus coh_wr_trick_detach(CohAssetLoader*loader,CohWrTrickCache**source,CohWrTexOptDigest digest,void*context,const CohWrTrickDetachedLimits*limits,CohCancel cancel,CohWrTrickDetached**out){
 if(!loader||!source||!*source||!digest||!limits||!out||!apart(source,sizeof(*source),out,sizeof(*out))||!apart(limits,sizeof(*limits),out,sizeof(*out))||!apart(limits,sizeof(*limits),source,sizeof(*source)))return COH_INVALID;
 if(*out)return COH_STATE;
 CohWrTrickReport original;CohStatus status=coh_wr_trick_report(*source,&original);if(status!=COH_OK)return status;
 if(original.count!=COUNT||!original.historical_input_generation||!apart(*source,original.owned_bytes,out,sizeof(*out))||!apart(*source,original.owned_bytes,source,sizeof(*source)))return COH_INVALID;
 size_t minimum=original.owned_bytes,owned=sizeof(CohWrTrickDetached),aggregate=limits->external_bytes;
 if(!add(&minimum,original.loader_reservation)||!add(&minimum,32768)||limits->external_bytes<minimum||!add(&owned,SUFFIX_BYTES)||owned>limits->owned_limit||!limits->loader_reservation||!add(&aggregate,limits->loader_reservation)||!add(&aggregate,owned)||!add(&aggregate,RESERVE)||aggregate>limits->aggregate_limit||coh_asset_stats(loader).peak_allocated_bytes>limits->loader_reservation)return COH_LIMIT;
 if(stop(cancel))return COH_CANCELLED;
 const CohAssetBlob*blob=NULL;CohWrTrickDetached*c=NULL;CohAssetId id={"data/bin/tricks.bin",original.historical_input_generation};status=coh_asset_acquire(loader,id,cancel,&blob);if(status!=COH_OK)return status;CohBytes body=coh_asset_bytes(blob);CohAssetId actual=coh_asset_identity(blob);
 if(coh_asset_stats(loader).peak_allocated_bytes>limits->loader_reservation){status=COH_LIMIT;goto fail;}
 if(!actual.path||strcmp(actual.path,id.path)||actual.generation!=id.generation||body.size!=SOURCE_OFFSET+SUFFIX_BYTES||!apart(body.data,body.size,out,sizeof(*out))||!apart(body.data,body.size,source,sizeof(*source))){status=COH_INVALID;goto fail;}
 static const uint8_t expected[32]={0xcf,0x95,0x95,0xe5,0x4b,0xc6,0x5a,0x40,0xd2,0xdd,0xdc,0x3a,0x5a,0x13,0xc4,0x75,0xd7,0xc2,0xce,0x07,0xa9,0x64,0x20,0xe6,0x00,0x1b,0x0e,0x23,0x12,0x92,0x6b,0xc1};
 static const uint8_t suffix_hash[32]={0xe8,0x2e,0x82,0x53,0x40,0xe7,0xab,0xb1,0x6c,0xcb,0x3d,0x34,0xa7,0x56,0xa9,0x91,0xb7,0x3e,0xea,0xb3,0x3b,0xc2,0x91,0x02,0x1a,0x60,0x88,0x22,0x62,0x0c,0x65,0xa5};
 uint8_t hash[32];status=digest(context,body,hash);if(status!=COH_OK)goto fail;if(memcmp(hash,expected,32)||memcmp(original.cache_sha256,expected,32)){status=COH_INVALID;goto fail;}
 if(stop(cancel)){status=COH_CANCELLED;goto fail;}c=calloc(1,owned);if(!c){status=COH_LIMIT;goto fail;}c->bytes=(CohBytes){(const uint8_t*)(c+1),SUFFIX_BYTES};
 for(size_t offset=0;offset<SUFFIX_BYTES;){if(stop(cancel)){status=COH_CANCELLED;goto fail;}size_t n=SUFFIX_BYTES-offset;if(n>4096)n=4096;memcpy((uint8_t*)c->bytes.data+offset,body.data+SOURCE_OFFSET+offset,n);offset+=n;}
 status=digest(context,c->bytes,hash);if(status!=COH_OK)goto fail;if(memcmp(hash,suffix_hash,32)){status=COH_INVALID;goto fail;}
 Reader r={c->bytes,0,c->bytes.size};uint32_t count;if(!word(&r,&count)||count!=COUNT){status=COH_INVALID;goto fail;}
 for(uint32_t i=0;i<COUNT;i++){
  if(stop(cancel)){status=COH_CANCELLED;goto fail;}uint32_t bytes;if(!word(&r,&bytes)||bytes>r.end-r.pos){status=COH_INVALID;goto fail;}Reader row={r.bytes,r.pos,r.pos+bytes};TrickInfo raw;Meta meta;memset(&raw,0,sizeof(raw));memset(&meta,0,sizeof(meta));status=table(&row,parse_trick,&raw,&meta,0);if(status!=COH_OK)goto fail;
  CohWrTrickView prior;status=coh_wr_trick_view(*source,i,&prior);if(status!=COH_OK)goto fail;
  if(row.pos!=row.end||meta.string_count!=2||meta.strings[0].size>=260||!ascii(meta.strings[0])||meta.strings[0].size!=prior.name.size||memcmp(meta.strings[0].data,prior.name.data,prior.name.size)||meta.strings[1].size!=prior.source_file.size||memcmp(meta.strings[1].data,prior.source_file.data,prior.source_file.size)||raw.fileAge!=prior.source_age||meta.st_count!=prior.stanim_count||meta.lod_count!=prior.autolod_count){status=COH_INVALID;goto fail;}
  c->rows[i]=(Row){(uint32_t)r.pos,bytes,(uint32_t)(meta.strings[0].data-r.bytes.data),(uint32_t)meta.strings[0].size,(uint32_t)(meta.strings[1].data-r.bytes.data),(uint32_t)meta.strings[1].size,raw.fileAge,meta.st_offset,meta.st_count,meta.lod_offset,meta.lod_count,0};c->index[i]=i;r.pos=row.end;
 }
 if(r.pos!=r.end){status=COH_INVALID;goto fail;}
 for(uint32_t k=COUNT/2;k>0;k--){sift(c,k-1,COUNT);}
 for(uint32_t k=COUNT;k>1;k--){if(stop(cancel)){status=COH_CANCELLED;goto fail;}uint32_t tmp=c->index[0];c->index[0]=c->index[k-1];c->index[k-1]=tmp;sift(c,0,k-1);}
 for(uint32_t start=0;start<COUNT;){if(stop(cancel)){status=COH_CANCELLED;goto fail;}uint32_t end=start+1,best=c->index[start];while(end<COUNT&&!order(c,c->index[start],c->index[end])){if(c->index[end]>best)best=c->index[end];end++;}for(uint32_t j=start;j<end;j++)c->rows[c->index[j]].winner=best;start=end;}
 c->report=original;c->detached.source_admission=original;memcpy(c->detached.retained_sha256,hash,32);c->detached.source_offset=SOURCE_OFFSET;c->detached.retained_bytes=SUFFIX_BYTES;c->detached.owned_bytes=owned;c->detached.preparation_aggregate_reserved_bytes=aggregate;c->detached.preparation_loader_reservation=limits->loader_reservation;
 if(stop(cancel)){status=COH_CANCELLED;goto fail;}coh_asset_release(loader,blob);coh_wr_trick_release(source);*out=c;return COH_OK;
fail:if(blob)coh_asset_release(loader,blob);free(c);return status;
}
