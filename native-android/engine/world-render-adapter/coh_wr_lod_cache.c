#include "coh_wr_lod_cache.h"
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#define ROWS 4976u
#define FILES 738u
#define CHILDREN 9158u
#define BODY_BYTES 1059016u
#define CACHE_RESERVE 16384u
#define DICTIONARY_RESERVE 32768u
typedef struct {uint32_t name,size,file,file_size,children,count,force;} Row;
struct CohWrLodCache {CohAssetLoader*loader;const CohAssetBlob*blob;CohWrLodCacheReport report;Row rows[ROWS];};
typedef struct {uint32_t ordinal,winner;uint16_t path_length,model_length;char key[260];} Key;
struct CohWrLodDictionary {CohWrLodCache*source;CohWrLodDictionaryReport report;Key rows[ROWS];uint32_t index[ROWS];};
typedef struct {CohBytes body;size_t pos,end;} Reader;
_Static_assert(FILES*sizeof(CohBytes)+4096<=CACHE_RESERVE,"bounded source control reserve");
static int apart(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int add(size_t*n,size_t x){if(x>SIZE_MAX-*n)return 0;*n+=x;return 1;}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int compare(const char*a,const char*b){for(;*a&&*b;a++,b++){int d=(int)fold((unsigned char)*a)-(int)fold((unsigned char)*b);if(d)return d;}return(unsigned char)*a-(unsigned char)*b;}
static int word(Reader*r,uint32_t*out){if(r->pos>r->end||r->end-r->pos<4)return 0;const uint8_t*p=r->body.data+r->pos;*out=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;r->pos+=4;return 1;}
static int string(Reader*r,CohBytes*out){if(r->pos>r->end||r->end-r->pos<2)return 0;const uint8_t*p=r->body.data+r->pos;size_t n=p[0]|(size_t)p[1]<<8,extent=(n+5u)&~3u;if(n>=260||extent>r->end-r->pos)return 0;for(size_t i=0;i<n;i++)if(p[2+i]<32||p[2+i]>126)return 0;*out=(CohBytes){n?p+2:NULL,n};r->pos+=extent;return 1;}
static int scalar(Reader*r,float*out){uint32_t v;if(!word(r,&v))return 0;memcpy(out,&v,4);return isfinite(*out);}
static CohBytes raw(const CohWrLodCache*c){return coh_asset_bytes(c->blob);}
static int cache_output(const CohWrLodCache*c,const void*out,size_t n){CohBytes b=raw(c);return apart(c,sizeof(*c),out,n)&&apart(b.data,b.size,out,n);}
static int dictionary_output(const CohWrLodDictionary*d,const void*out,size_t n){return apart(d,sizeof(*d),out,n)&&cache_output(d->source,out,n);}
static int ascii(const char*s,size_t*length){if(!s)return 0;for(size_t i=0;i<260;i++){unsigned v=(unsigned char)s[i];if(!v){*length=i;return i!=0;}if(v<32||v>126)return 0;}return 0;}
static int span_equal(CohBytes a,CohBytes b){if(a.size!=b.size)return 0;for(size_t i=0;i<a.size;i++)if(fold(a.data[i])!=fold(b.data[i]))return 0;return 1;}
static CohStatus child(Reader*r,CohWrLodCacheChild*out){uint32_t bytes;if(!word(r,&bytes)||bytes>r->end-r->pos)return COH_INVALID;Reader q={r->body,r->pos,r->pos+bytes};CohWrLodCacheChild v={0};if(!scalar(&q,&v.max_error)||!scalar(&q,&v.lod_nearfade)||!scalar(&q,&v.lod_near)||!scalar(&q,&v.lod_far)||!scalar(&q,&v.lod_farfade)||!word(&q,&v.flags)||!string(&q,&v.model_name)||q.pos!=q.end)return COH_INVALID;r->pos=q.end;if(out)*out=v;return COH_OK;}
void coh_wr_lod_cache_release(CohWrLodCache**out){if(out&&*out){CohWrLodCache*c=*out;coh_asset_release(c->loader,c->blob);free(c);*out=NULL;}}
CohStatus coh_wr_lod_cache_open(CohAssetLoader*loader,CohAssetId id,CohWrTexOptDigest digest,void*context,const CohWrLodCacheLimits*limits,CohCancel cancel,CohWrLodCache**out){
 if(!loader||!id.path||strcmp(id.path,"data/bin/lods.bin")||!id.generation||!digest||!limits||!out||!apart(limits,sizeof(*limits),out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 size_t aggregate=limits->external_bytes;
 if(sizeof(CohWrLodCache)>limits->owned_limit||!limits->loader_reservation||!limits->aggregate_limit||limits->aggregate_limit>96u*1024u*1024u||!add(&aggregate,limits->loader_reservation)||!add(&aggregate,sizeof(CohWrLodCache))||!add(&aggregate,CACHE_RESERVE)||aggregate>limits->aggregate_limit||coh_asset_stats(loader).peak_allocated_bytes>limits->loader_reservation)return COH_LIMIT;
 if(cancelled(cancel))return COH_CANCELLED;
 CohWrLodCache*c=calloc(1,sizeof(*c));if(!c)return COH_LIMIT;c->loader=loader;CohStatus status=coh_asset_acquire(loader,id,cancel,&c->blob);if(status!=COH_OK)goto fail;
 CohBytes b=raw(c);CohAssetId actual=coh_asset_identity(c->blob);
 if(coh_asset_stats(loader).peak_allocated_bytes>limits->loader_reservation){status=COH_LIMIT;goto fail;}
 if(b.size!=BODY_BYTES||!actual.path||strcmp(actual.path,id.path)||actual.generation!=id.generation||!cache_output(c,out,sizeof(*out))){status=COH_INVALID;goto fail;}
 static const uint8_t expected[32]={0x13,0x80,0x02,0x55,0x78,0x11,0x38,0x24,0x82,0x26,0x34,0x0b,0xe3,0x16,0xcd,0x62,0x8e,0x98,0x80,0x0d,0x9b,0xa8,0x89,0xfe,0x1a,0xec,0xc9,0x02,0xe4,0x83,0xb6,0x6a};
 uint8_t hash[32];status=digest(context,b,hash);if(status!=COH_OK)goto fail;if(memcmp(hash,expected,32)){status=COH_INVALID;goto fail;}
 Reader r={b,8,b.size};uint32_t value,count;CohBytes marker;
 if(memcmp(b.data,"CrypticS",8)||!word(&r,&value)||value!=0xe8361497u||!string(&r,&marker)||marker.size!=6||memcmp(marker.data,"Parse6",6)||!string(&r,&marker)||marker.size!=6||memcmp(marker.data,"Files1",6)||!word(&r,&value)||value>r.end-r.pos){status=COH_INVALID;goto fail;}
 Reader files={b,r.pos,r.pos+value};CohBytes filenames[FILES];
 if(!word(&files,&count)||count!=FILES){status=COH_INVALID;goto fail;}
 for(uint32_t i=0;i<FILES;i++){if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}if(!string(&files,&filenames[i])||!filenames[i].size||!word(&files,&value)){status=COH_INVALID;goto fail;}}
 if(files.pos!=files.end){status=COH_INVALID;goto fail;}r.pos=files.end;
 if(!word(&r,&value)||value!=r.end-r.pos||!word(&r,&count)||count!=ROWS){status=COH_INVALID;goto fail;}
 uint32_t children=0,force=0;
 for(uint32_t i=0;i<ROWS;i++){
  if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}if(!word(&r,&value)||value>r.end-r.pos){status=COH_INVALID;goto fail;}
  Reader q={b,r.pos,r.pos+value};CohBytes name,file;if(!string(&q,&name)||!name.size||!string(&q,&file)||!file.size){status=COH_INVALID;goto fail;}
  int known=0;for(uint32_t j=0;j<FILES;j++)if(span_equal(file,filenames[j])){known=1;break;}if(!known){status=COH_INVALID;goto fail;}
  if(!word(&q,&count)||count>256||children>CHILDREN-count){status=COH_INVALID;goto fail;}
  Row row={(uint32_t)(name.data-b.data),(uint32_t)name.size,(uint32_t)(file.data-b.data),(uint32_t)file.size,(uint32_t)q.pos,count,0};children+=count;
  for(uint32_t j=0;j<count;j++)if((status=child(&q,NULL))!=COH_OK)goto fail;
  if(!word(&q,&row.force)||row.force>1||q.pos!=q.end){status=COH_INVALID;goto fail;}force+=row.force;c->rows[i]=row;r.pos=q.end;
 }
 if(r.pos!=r.end||children!=CHILDREN||force!=39){status=COH_INVALID;goto fail;}
 c->report=(CohWrLodCacheReport){id.generation,ROWS,children,FILES,force,sizeof(*c),limits->loader_reservation,aggregate,{0}};memcpy(c->report.cache_sha256,hash,32);
 if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}*out=c;return COH_OK;
fail:if(c->blob)coh_asset_release(loader,c->blob);free(c);return status;
}
CohStatus coh_wr_lod_cache_report(const CohWrLodCache*c,CohWrLodCacheReport*out){if(!c||!out||!cache_output(c,out,sizeof(*out)))return COH_INVALID;*out=c->report;return COH_OK;}
CohStatus coh_wr_lod_cache_row(const CohWrLodCache*c,uint32_t i,CohWrLodCacheRow*out){if(!c||!out||!cache_output(c,out,sizeof(*out)))return COH_INVALID;if(i>=ROWS)return COH_NOT_FOUND;Row r=c->rows[i];CohBytes b=raw(c);*out=(CohWrLodCacheRow){{b.data+r.name,r.size},{b.data+r.file,r.file_size},i,r.force,r.count,c->report.historical_input_generation};return COH_OK;}
CohStatus coh_wr_lod_cache_child(const CohWrLodCache*c,uint32_t i,uint32_t j,CohWrLodCacheChild*out){if(!c||!out||!cache_output(c,out,sizeof(*out)))return COH_INVALID;if(i>=ROWS||j>=c->rows[i].count)return COH_NOT_FOUND;Reader r={raw(c),c->rows[i].children,raw(c).size};CohWrLodCacheChild v;for(uint32_t n=0;n<=j;n++){CohStatus status=child(&r,&v);if(status!=COH_OK)return status;}*out=v;return COH_OK;}
static int order(const CohWrLodDictionary*d,uint32_t a,uint32_t b){return compare(d->rows[a].key,d->rows[b].key);}
static void sift(CohWrLodDictionary*d,uint32_t root,uint32_t n){for(;;){uint32_t child_index=root*2+1;if(child_index>=n)return;if(child_index+1<n&&order(d,d->index[child_index],d->index[child_index+1])<0)child_index++;if(order(d,d->index[root],d->index[child_index])>=0)return;uint32_t temp=d->index[root];d->index[root]=d->index[child_index];d->index[child_index]=temp;root=child_index;}}
void coh_wr_lod_dictionary_release(CohWrLodDictionary**out){if(out&&*out){CohWrLodDictionary*d=*out;coh_wr_lod_cache_release(&d->source);free(d);*out=NULL;}}
CohStatus coh_wr_lod_dictionary_stage(CohWrLodCache**source,CohWrLodWritablePath resolve,void*context,const CohWrLodDictionaryLimits*limits,CohCancel cancel,CohWrLodDictionary**out){
 if(!source||!*source||!resolve||!limits||!out||!apart(source,sizeof(*source),out,sizeof(*out))||!apart(limits,sizeof(*limits),source,sizeof(*source))||!apart(limits,sizeof(*limits),out,sizeof(*out))||!cache_output(*source,out,sizeof(*out))||!cache_output(*source,source,sizeof(*source)))return COH_INVALID;
 if(*out)return COH_STATE;
 CohWrLodCache*c=*source;size_t minimum=c->report.owned_bytes,aggregate=limits->external_bytes;
 if(!add(&minimum,c->report.loader_reservation)||!add(&minimum,CACHE_RESERVE)||limits->external_bytes<minimum||sizeof(CohWrLodDictionary)>limits->owned_limit||!limits->aggregate_limit||limits->aggregate_limit>96u*1024u*1024u||!add(&aggregate,sizeof(CohWrLodDictionary))||!add(&aggregate,DICTIONARY_RESERVE)||aggregate>limits->aggregate_limit)return COH_LIMIT;
 if(cancelled(cancel))return COH_CANCELLED;
 CohWrLodDictionary*d=calloc(1,sizeof(*d));if(!d)return COH_LIMIT;d->source=c;CohStatus status=COH_INVALID;CohBytes bytes=raw(c);
 for(uint32_t i=0;i<ROWS;i++){
  if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}Row r=c->rows[i];char filename[260],resolved[260];memcpy(filename,bytes.data+r.file,r.file_size);filename[r.file_size]=0;memset(resolved,0,sizeof(resolved));status=resolve(context,filename,resolved);if(status!=COH_OK)goto fail;size_t n;if(!ascii(resolved,&n)){status=COH_INVALID;goto fail;}
  const uint8_t*name=bytes.data+r.name;size_t m=r.size;for(size_t k=0;k+1<m;k++)if(name[k]=='_'&&name[k+1]=='_'){m=k;break;}
  if(n+1+m>=260){status=COH_LIMIT;goto fail;}Key*key=&d->rows[i];memcpy(key->key,resolved,n);key->key[n]='/';memcpy(key->key+n+1,name,m);key->key[n+1+m]=0;key->path_length=(uint16_t)n;key->model_length=(uint16_t)m;key->ordinal=i;d->index[i]=i;
 }
 for(uint32_t i=ROWS/2;i>0;i--)sift(d,i-1,ROWS);
 for(uint32_t i=ROWS;i>1;i--){if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}uint32_t temp=d->index[0];d->index[0]=d->index[i-1];d->index[i-1]=temp;sift(d,0,i-1);}
 uint32_t unique=0,duplicates=0;
 for(uint32_t start=0;start<ROWS;){if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}uint32_t end=start+1,first=d->index[start];while(end<ROWS&&!order(d,d->index[start],d->index[end])){if(d->index[end]<first)first=d->index[end];end++;}for(uint32_t i=start;i<end;i++)d->rows[d->index[i]].winner=first;unique++;duplicates+=end-start-1;start=end;}
 d->report=(CohWrLodDictionaryReport){c->report,ROWS,unique,duplicates,sizeof(*d),aggregate};if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}*source=NULL;*out=d;return COH_OK;
fail:free(d);return status;
}
CohStatus coh_wr_lod_dictionary_report(const CohWrLodDictionary*d,CohWrLodDictionaryReport*out){if(!d||!out||!dictionary_output(d,out,sizeof(*out)))return COH_INVALID;*out=d->report;return COH_OK;}
CohStatus coh_wr_lod_dictionary_row(const CohWrLodDictionary*d,uint32_t i,CohWrLodDictionaryRow*out){if(!d||!out||!dictionary_output(d,out,sizeof(*out)))return COH_INVALID;if(i>=ROWS)return COH_NOT_FOUND;const Key*k=&d->rows[i];Row r=d->source->rows[i];CohBytes b=raw(d->source);*out=(CohWrLodDictionaryRow){{(const uint8_t*)k->key,k->path_length},{b.data+r.name,k->model_length},i,k->winner,r.force,r.count};return COH_OK;}
CohStatus coh_wr_lod_dictionary_child(const CohWrLodDictionary*d,uint32_t i,uint32_t j,CohWrLodCacheChild*out){if(!d||!out||!dictionary_output(d,out,sizeof(*out)))return COH_INVALID;return coh_wr_lod_cache_child(d->source,i,j,out);}
static const char*contains(const char*s,const char*q){size_t n=strlen(q);for(;*s;s++){size_t i=0;while(i<n&&s[i]&&fold((unsigned char)s[i])==fold((unsigned char)q[i]))i++;if(i==n)return s;}return NULL;}
CohStatus coh_wr_lod_source_filename(const char*geo,char out[260]){size_t n;if(!out||!ascii(geo,&n)||!apart(geo,n+1,out,260))return COH_INVALID;const char*start=contains(geo,"/data/");start=start?start+6:geo;const char*end=contains(start,".geo");if(!end)return COH_NOT_FOUND;size_t size=(size_t)(end-start);if(size+10>260)return COH_LIMIT;char result[260];memcpy(result,"lods/",5);memcpy(result+5,start,size);memcpy(result+5+size,".txt",5);memcpy(out,result,size+10);return COH_OK;}
CohStatus coh_wr_lod_dictionary_lookup(const CohWrLodDictionary*d,const char*geo,const char*model,CohWrLodWritablePath resolve,void*context,CohWrLodDictionaryLookup*out){
 size_t gn,mn;if(!d||!out||!resolve||!ascii(geo,&gn)||!ascii(model,&mn)||!dictionary_output(d,out,sizeof(*out))||!apart(geo,gn+1,out,sizeof(*out))||!apart(model,mn+1,out,sizeof(*out)))return COH_INVALID;
 char file[260],resolved[260],key[1024];CohStatus status=coh_wr_lod_source_filename(geo,file);if(status!=COH_OK)return status;memset(resolved,0,sizeof(resolved));status=resolve(context,file,resolved);if(status!=COH_OK)return status;size_t n;if(!ascii(resolved,&n))return COH_INVALID;
 memcpy(key,resolved,n);key[n]='/';memcpy(key+n+1,model,mn+1);char*s=strstr(key,"__");if(s)*s=0;
 uint32_t lo=0,hi=ROWS,found=UINT32_MAX;while(lo<hi){uint32_t mid=lo+(hi-lo)/2;int cmp=compare(key,d->rows[d->index[mid]].key);if(cmp<0)hi=mid;else if(cmp>0)lo=mid+1;else{found=d->rows[d->index[mid]].winner;break;}}
 CohWrLodDictionaryLookup result={COH_WR_LOD_DICTIONARY_ABSENT,UINT32_MAX,1};if(found!=UINT32_MAX){Row r=d->source->rows[found];result.ordinal=found;result.branch=r.force&&!r.count?COH_WR_LOD_DICTIONARY_CONSTRUCT_FORCE_AUTO:COH_WR_LOD_DICTIONARY_RETURN_EXISTING;}*out=result;return COH_OK;
}
