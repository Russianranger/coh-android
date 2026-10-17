#include "coh_wr_tex_inputs.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#define MEMORY_MAX (256u*1024u*1024u)
typedef struct{const CohAssetBlob*blob;char path[256],directory[256],key[128];CohAssetTexture texture;uint8_t hash[32];}Header;
typedef struct{const CohAssetBlob*blob;char path[256];uint8_t hash[32];}Raw;
struct CohWrTexInputs{CohAssetLoader*loader;CohWrTexInputsReport report;Header*headers;Raw*raw;uint32_t*header_index,*raw_index;uint32_t header_pins,raw_pins;};
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int compare(const char*a,const char*b){while(*a&&*b){int d=(int)fold((unsigned char)*a++)-(int)fold((unsigned char)*b++);if(d)return d;}return (unsigned char)*a-(unsigned char)*b;}
static CohStatus length(const char*s,size_t max,size_t*n){if(!s)return COH_INVALID;for(size_t k=0;k<=max;k++){unsigned c=(unsigned char)s[k];if(!c){*n=k;return COH_OK;}if(c<32||c>126)return COH_UNSUPPORTED;}return COH_LIMIT;}
static int disjoint(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int output_ok(const CohWrTexInputs*r,const void*out,size_t n){
 if(!disjoint(r,r->report.owned_bytes,out,n))return 0;
 for(uint32_t k=0;k<r->header_pins;k++){CohBytes b=coh_asset_bytes(r->headers[k].blob);if(!disjoint(b.data,b.size,out,n))return 0;}
 for(uint32_t k=0;k<r->raw_pins;k++){CohBytes b=coh_asset_bytes(r->raw[k].blob);if(!disjoint(b.data,b.size,out,n))return 0;}
 return 1;
}
static int nonzero(const uint8_t*h){unsigned n=0;for(unsigned k=0;k<32;k++)n|=h[k];return n!=0;}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static int add(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static int room(CohAssetLoader*l,const CohWrTexInputsLimits*b,size_t owned,size_t inputs,size_t*total){
 size_t n=b->external_bytes;if(!add(&n,COH_WR_TEX_INPUTS_PREPARATION_RESERVE)||coh_asset_stats(l).peak_allocated_bytes>b->loader_reservation||!add(&n,b->loader_reservation)||!add(&n,owned)||!add(&n,inputs)||n>b->aggregate_limit)return 0;*total=n;return 1;
}
static CohStatus header_name(const char*original,char directory[256],char key[128]){
 size_t n;CohStatus s=length(original,255,&n);if(s!=COH_OK)return s;
 const char prefix[]="texture_library";if(n<=sizeof(prefix)-1)return COH_UNSUPPORTED;
 for(unsigned k=0;k<sizeof(prefix)-1;k++)if(fold((unsigned char)original[k])!=(unsigned)prefix[k])return COH_UNSUPPORTED;
 if(original[sizeof(prefix)-1]!='/')return COH_UNSUPPORTED;
 const char*start=original+sizeof(prefix)-1;while(*start=='/')start++;
 memcpy(directory,start,strlen(start)+1);char*slash=strrchr(directory,'/');if(slash)*slash=0;
 const char*basename=strrchr(original,'/');if(!basename||!basename[1])return COH_INVALID;basename++;
 char temp[256];n=strlen(basename);memcpy(temp,basename,n+1);
 if(n>=4){if(temp[n-4]=='.')temp[n-4]=0;else if(n<8)return COH_UNSUPPORTED;else if(temp[n-8]=='.')temp[n-8]=0;}
 n=strlen(temp);if(!n)return COH_INVALID;if(n>127)return COH_LIMIT;memcpy(key,temp,n+1);return COH_OK;
}
static const char*sort_key(const CohWrTexInputs*r,uint32_t row,int raw){return raw?r->raw[row].path:r->headers[row].key;}
static void sift(const CohWrTexInputs*r,uint32_t*idx,uint32_t count,uint32_t root,int raw){
 for(;;){uint32_t child=root*2+1;if(child>=count)return;if(child+1<count&&compare(sort_key(r,idx[child],raw),sort_key(r,idx[child+1],raw))<0)child++;if(compare(sort_key(r,idx[root],raw),sort_key(r,idx[child],raw))>=0)return;uint32_t tmp=idx[root];idx[root]=idx[child];idx[child]=tmp;root=child;}
}
static CohStatus sort(CohWrTexInputs*r,uint32_t*idx,uint32_t count,int raw,CohCancel c){
 for(uint32_t k=0;k<count;k++)idx[k]=k;
 for(uint32_t k=count/2;k>0;k--){if(cancelled(c))return COH_CANCELLED;sift(r,idx,count,k-1,raw);}
 for(uint32_t n=count;n>1;n--){if(cancelled(c))return COH_CANCELLED;uint32_t tmp=idx[0];idx[0]=idx[n-1];idx[n-1]=tmp;sift(r,idx,n-1,0,raw);}
 for(uint32_t k=1;k<count;k++)if(!compare(sort_key(r,idx[k-1],raw),sort_key(r,idx[k],raw)))return COH_STATE;
 return COH_OK;
}
void coh_wr_tex_inputs_release(CohWrTexInputs**p){if(!p||!*p)return;CohWrTexInputs*r=*p;for(uint32_t k=0;k<r->header_pins;k++)coh_asset_release(r->loader,r->headers[k].blob);for(uint32_t k=0;k<r->raw_pins;k++)coh_asset_release(r->loader,r->raw[k].blob);free(r);*p=NULL;}
CohStatus coh_wr_tex_inputs_build(CohAssetLoader*l,const CohWrTexInputsRequest*q,const CohWrTexInputsLimits*b,CohCancel c,CohWrTexInputs**out){
 if(!l||!q||!b||!out||!q->digest||!q->input_generation||(!q->texture_count&&!q->raw_trick_count)||(q->texture_count&&!q->textures)||(q->raw_trick_count&&!q->raw_tricks))return COH_INVALID;
 if(!disjoint(q,sizeof(*q),out,sizeof(*out))||!disjoint(b,sizeof(*b),out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 if(q->texture_count>COH_WR_TEX_INPUTS_MAX||q->raw_trick_count>COH_WR_TEX_INPUTS_MAX||!b->owned_limit||!b->aggregate_limit||b->aggregate_limit>MEMORY_MAX||!b->loader_reservation)return COH_LIMIT;
 if(!disjoint(q->textures,(size_t)q->texture_count*sizeof(*q->textures),out,sizeof(*out))||!disjoint(q->raw_tricks,(size_t)q->raw_trick_count*sizeof(*q->raw_tricks),out,sizeof(*out)))return COH_INVALID;
 size_t inputs=sizeof(*q)+(size_t)(q->texture_count+q->raw_trick_count)*sizeof(CohWrTexInputPin);
 for(unsigned kind=0;kind<2;kind++){const CohWrTexInputPin*p=kind?q->raw_tricks:q->textures;uint32_t count=kind?q->raw_trick_count:q->texture_count;
  for(uint32_t k=0;k<count;k++){size_t n;CohStatus s=length(p[k].asset.path,255,&n);if(s!=COH_OK)return s;if(!disjoint(p[k].asset.path,n+1,out,sizeof(*out)))return COH_INVALID;if(!n||!nonzero(p[k].sha256)||p[k].asset.generation!=q->input_generation)return COH_INVALID;if(!add(&inputs,n+1))return COH_LIMIT;
   const char*prefix=kind?"data/tricks/":"data/texture_library/";size_t pn=strlen(prefix);if(n<=pn||strncmp(p[k].asset.path,prefix,pn))return COH_UNSUPPORTED;const char*suffix=kind?".txt":".texture";size_t sn=strlen(suffix);if(n<sn||compare(p[k].asset.path+n-sn,suffix))return COH_UNSUPPORTED;
   if(!kind){const char*component=p[k].asset.path+pn;for(const char*at=component;;at++){if(at==component&&*at=='_')return COH_UNSUPPORTED;if(!*at)break;if(*at=='/')component=at+1;}const char*file=strrchr(p[k].asset.path,'/');if(!file||strlen(file+1)>127)return COH_UNSUPPORTED;}
  }
 }
 size_t owned=sizeof(CohWrTexInputs)+(size_t)q->texture_count*sizeof(Header)+(size_t)q->raw_trick_count*sizeof(Raw)+(size_t)(q->texture_count+q->raw_trick_count)*sizeof(uint32_t),total;
 if(owned>b->owned_limit||!room(l,b,owned,inputs,&total))return COH_LIMIT;
 if(cancelled(c))return COH_CANCELLED;
 CohWrTexInputs*r=calloc(1,owned);if(!r)return COH_LIMIT;r->loader=l;r->report=(CohWrTexInputsReport){q->texture_count,q->raw_trick_count,q->input_generation,1,owned,inputs,total,b->loader_reservation,COH_WR_TEX_INPUTS_PREPARATION_RESERVE};
 r->headers=(Header*)(r+1);r->raw=(Raw*)(r->headers+q->texture_count);r->header_index=(uint32_t*)(r->raw+q->raw_trick_count);r->raw_index=r->header_index+q->texture_count;
 CohStatus status=COH_OK;
 for(unsigned kind=0;kind<2;kind++){const CohWrTexInputPin*p=kind?q->raw_tricks:q->textures;uint32_t count=kind?q->raw_trick_count:q->texture_count;
  for(uint32_t k=0;k<count;k++){
   if(cancelled(c)){status=COH_CANCELLED;goto fail;}const CohAssetBlob*blob=NULL;status=coh_asset_acquire(l,p[k].asset,c,&blob);if(status!=COH_OK)goto fail;
   if(kind){r->raw[k].blob=blob;r->raw_pins++;}else{r->headers[k].blob=blob;r->header_pins++;}
   if(!room(l,b,owned,inputs,&total)){status=COH_LIMIT;goto fail;}CohAssetId id=coh_asset_identity(blob);if(id.generation!=p[k].asset.generation||strcmp(id.path,p[k].asset.path)){status=COH_STATE;goto fail;}
   CohBytes bytes=coh_asset_bytes(blob);if(!disjoint(bytes.data,bytes.size,out,sizeof(*out))){status=COH_INVALID;goto fail;}uint8_t hash[32];status=q->digest(q->digest_context,bytes,hash);if(status!=COH_OK)goto fail;if(memcmp(hash,p[k].sha256,32)){status=COH_INVALID;goto fail;}
   if(kind){if(!bytes.size||memchr(bytes.data,0,bytes.size)){status=COH_INVALID;goto fail;}memcpy(r->raw[k].path,id.path,strlen(id.path)+1);memcpy(r->raw[k].hash,hash,32);}
   else{Header*h=r->headers+k;status=coh_asset_texture(bytes,&h->texture);if(status!=COH_OK)goto fail;if(!h->texture.name||h->texture.alpha>1){status=COH_INVALID;goto fail;}
    /* Original texFillInBind accepts sizeof(TextureFileHeader)+1024 bytes. */
    uint32_t header_size=(uint32_t)bytes.data[0]|(uint32_t)bytes.data[1]<<8|(uint32_t)bytes.data[2]<<16|(uint32_t)bytes.data[3]<<24;if(header_size>1056){status=COH_UNSUPPORTED;goto fail;}status=header_name(h->texture.name,h->directory,h->key);if(status!=COH_OK)goto fail;
    const char*file=strrchr(id.path,'/')+1;size_t stem_bytes=strlen(file)-8;char stem[128];memcpy(stem,file,stem_bytes);stem[stem_bytes]=0;if(compare(stem,h->key)){status=COH_INVALID;goto fail;}
    memcpy(h->path,id.path,strlen(id.path)+1);memcpy(h->hash,hash,32);}
  }
 }
 status=sort(r,r->header_index,q->texture_count,0,c);if(status!=COH_OK)goto fail;status=sort(r,r->raw_index,q->raw_trick_count,1,c);if(status!=COH_OK)goto fail;if(cancelled(c)){status=COH_CANCELLED;goto fail;}*out=r;return COH_OK;
fail:coh_wr_tex_inputs_release(&r);return status;
}
CohStatus coh_wr_tex_inputs_report(const CohWrTexInputs*r,CohWrTexInputsReport*out){if(!r||!out||!output_ok(r,out,sizeof(*out)))return COH_INVALID;*out=r->report;return COH_OK;}
CohStatus coh_wr_tex_inputs_header(const CohWrTexInputs*r,uint32_t row,CohWrTexHeaderInput*out){if(!r||!out||!output_ok(r,out,sizeof(*out)))return COH_INVALID;if(row>=r->report.texture_count)return COH_NOT_FOUND;const Header*h=r->headers+row;CohWrTexHeaderInput v;memset(&v,0,sizeof(v));v.asset=(CohAssetId){h->path,r->report.input_generation};memcpy(v.sha256,h->hash,32);v.input_ordinal=row;v.unresolved_client_semantics=1;v.original_name=h->texture.name;v.directory=h->directory;v.basic_key=h->key;v.cached_flags=h->texture.flags;v.width=h->texture.width;v.height=h->texture.height;memcpy(v.cached_fade,h->texture.fade,sizeof(v.cached_fade));v.cached_alpha=h->texture.alpha;*out=v;return COH_OK;}
CohStatus coh_wr_tex_inputs_find_basic(const CohWrTexInputs*r,const char*key,CohWrTexHeaderInput*out){if(!r||!out||!output_ok(r,out,sizeof(*out)))return COH_INVALID;size_t n;CohStatus s=length(key,127,&n);if(s!=COH_OK)return s;if(!n||!disjoint(key,n+1,out,sizeof(*out)))return COH_INVALID;uint32_t lo=0,hi=r->report.texture_count;while(lo<hi){uint32_t mid=lo+(hi-lo)/2;int d=compare(key,r->headers[r->header_index[mid]].key);if(d>0)lo=mid+1;else if(d<0)hi=mid;else return coh_wr_tex_inputs_header(r,r->header_index[mid],out);}return COH_NOT_FOUND;}
CohStatus coh_wr_tex_inputs_raw_trick(const CohWrTexInputs*r,uint32_t row,CohWrRawTrickInput*out){if(!r||!out||!output_ok(r,out,sizeof(*out)))return COH_INVALID;if(row>=r->report.raw_trick_count)return COH_NOT_FOUND;const Raw*x=r->raw+row;CohWrRawTrickInput v;memset(&v,0,sizeof(v));v.asset=(CohAssetId){x->path,r->report.input_generation};memcpy(v.sha256,x->hash,32);v.input_ordinal=row;v.raw=coh_asset_bytes(x->blob);*out=v;return COH_OK;}
