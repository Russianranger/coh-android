#include "coh_wr_surface_states.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef struct{char name[100];uint32_t bit,flags;}Core;
#include "coh_wr_surface_core.inc"
struct CohWrSurfaceStates{CohWrSurfaceReport report;Core rows[COH_WR_SURFACE_MAX];};
typedef struct{CohBytes b;size_t pos,end;}Reader;
static int disjoint(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int take(Reader*r,size_t n,const uint8_t**p){if(n>r->end-r->pos)return 0;*p=r->b.data+r->pos;r->pos+=n;return 1;}
static int word(Reader*r,uint32_t*v){const uint8_t*p;if(!take(r,4,&p))return 0;*v=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;return 1;}
static int string(Reader*r,char*out,size_t cap){const uint8_t*p;if(!take(r,2,&p))return 0;size_t n=(size_t)p[0]|(size_t)p[1]<<8;if(n>=cap||!take(r,n,&p))return 0;for(size_t i=0;i<n;i++){if(p[i]<32||p[i]>126)return 0;out[i]=(char)p[i];}out[n]=0;return take(r,(4-(n+2)%4)%4,&p);}
static void upper(char*s){for(;*s;s++)if(*s>='a'&&*s<='z')*s=(char)(*s-32);}
static int stop(CohCancel c){return c.poll&&c.poll(c.context);}
void coh_wr_surface_release(CohWrSurfaceStates**p){if(p&&*p){free(*p);*p=NULL;}}
CohStatus coh_wr_surface_prepare(CohBytes b,uint32_t generation,CohWrSurfaceDigest digest,void*context,const CohWrSurfaceLimits*limit,CohCancel cancel,CohWrSurfaceStates**out){
 if(!b.data||!generation||!digest||!limit||!out)return COH_INVALID;
 if(!disjoint(b.data,b.size,out,sizeof(*out))||!disjoint(limit,sizeof(*limit),out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 size_t own=sizeof(CohWrSurfaceStates),total=own;if(b.size>SIZE_MAX-total)return COH_LIMIT;total+=b.size;if(32768>SIZE_MAX-total)return COH_LIMIT;total+=32768;if(limit->external_bytes>SIZE_MAX-total)return COH_LIMIT;total+=limit->external_bytes;
 if(b.size!=15380||own>limit->owned_limit||total>limit->aggregate_limit)return COH_LIMIT;
 if(stop(cancel))return COH_CANCELLED;
 static const uint8_t expected[32]={0x9c,0x4a,0x5a,0xab,0x4c,0x2b,0xff,0xb9,0x9e,0xb2,0x41,0x6e,0x76,0xa6,0x92,0x44,0x9e,0xe2,0x69,0x27,0xbe,0xed,0x3c,0xdd,0x86,0xde,0xce,0x02,0xaf,0x2b,0x2a,0xac};uint8_t hash[32];CohStatus status=digest(context,b,hash);if(status!=COH_OK)return status;if(memcmp(hash,expected,32))return COH_INVALID;
 Reader r={b,8,b.size};uint32_t crc,size,count;char text[260];if(memcmp(b.data,"CrypticS",8)||!word(&r,&crc)||crc!=0x6b0e7f06u||!string(&r,text,sizeof(text))||strcmp(text,"Parse6")||!string(&r,text,sizeof(text))||strcmp(text,"Files1")||!word(&r,&size)||size>r.end-r.pos)return COH_INVALID;
 size_t end=r.pos+size;Reader files={b,r.pos,end};uint32_t filecount;if(!word(&files,&filecount)||filecount>64)return COH_LIMIT;for(uint32_t i=0;i<filecount;i++)if(!string(&files,text,sizeof(text))||!word(&files,&crc))return COH_INVALID;if(files.pos!=end)return COH_INVALID;r.pos=end;
 if(!word(&r,&size)||size!=r.end-r.pos||!word(&r,&count)||count>764)return COH_INVALID;
 CohWrSurfaceStates*s=calloc(1,own);if(!s)return COH_LIMIT;s->report=(CohWrSurfaceReport){generation,111,own,total};memcpy(s->rows,core,sizeof(core));
 for(uint32_t i=0;i<count;i++){
  if(stop(cancel)){status=COH_CANCELLED;goto fail;}if(!word(&r,&size)||size>r.end-r.pos){status=COH_INVALID;goto fail;}end=r.pos+size;Reader row={b,r.pos,end};Core v;memset(&v,0,sizeof(v));if(!string(&row,v.name,sizeof(v.name))||!v.name[0]||!word(&row,&v.flags)||row.pos!=end){status=COH_INVALID;goto fail;}r.pos=end;upper(v.name);uint32_t j;for(j=0;j<s->report.count;j++)if(!strcmp(v.name,s->rows[j].name))break;if(j<s->report.count)continue;if(s->report.count+1>=COH_WR_SURFACE_MAX){status=COH_LIMIT;goto fail;}v.bit=s->report.count;s->rows[s->report.count++]=v;
 }
 if(r.pos!=r.end){status=COH_INVALID;goto fail;}if(stop(cancel)){status=COH_CANCELLED;goto fail;}*out=s;return COH_OK;
fail:coh_wr_surface_release(&s);return status;
}
CohStatus coh_wr_surface_report(const CohWrSurfaceStates*s,CohWrSurfaceReport*out){if(!s||!out||!disjoint(s,sizeof(*s),out,sizeof(*out)))return COH_INVALID;*out=s->report;return COH_OK;}
CohStatus coh_wr_surface_lookup(const CohWrSurfaceStates*s,const char*name,uint32_t*out){if(!s||!name||!out||!disjoint(s,sizeof(*s),out,sizeof(*out)))return COH_INVALID;char key[100];size_t n;for(n=0;n<sizeof(key);n++){unsigned c=(unsigned char)name[n];if(!c)break;if(c<32||c>126)return COH_UNSUPPORTED;key[n]=(char)c;}if(n==sizeof(key))return COH_LIMIT;if(!n||!disjoint(name,n+1,out,sizeof(*out)))return COH_INVALID;key[n]=0;upper(key);for(uint32_t i=0;i<s->report.count;i++)if(!strcmp(key,s->rows[i].name)){*out=s->rows[i].bit;return COH_OK;}return COH_NOT_FOUND;}
