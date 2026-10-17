/* NONSHIPPING diagnostic overlay. Caller freezes original initialized tables.
 * Read-only source stash getters; no insertion, resizing, loading or mutation.
 * Scratch bytes may change on refusal; *written commits only on full success.
 * Return0=success,1=invalid/schema,2=capacity. Not actor or origin authority. */
#include <stddef.h>
#include <string.h>
#include "coh_costume_export_source_id.inc"
typedef char coh_costume_export_int_must_be_32_bits[(sizeof(int)==4)?1:-1];
typedef struct CohCostumeExportWriter {unsigned char *p;size_t cap,at;int error;} CohCostumeExportWriter;
static void coh_costume_export_bytes(CohCostumeExportWriter*w,const void*p,size_t n){
 if(w->error)return;
 if(n>w->cap-w->at){w->error=2;return;}
 if(n)memcpy(w->p+w->at,p,n);
 w->at+=n;
}
static void coh_costume_export_u8(CohCostumeExportWriter*w,unsigned v){unsigned char b=(unsigned char)v;coh_costume_export_bytes(w,&b,1);}
static void coh_costume_export_u16(CohCostumeExportWriter*w,unsigned v){coh_costume_export_u8(w,v);coh_costume_export_u8(w,v>>8);}
static void coh_costume_export_u32(CohCostumeExportWriter*w,U32 v){unsigned i;for(i=0;i<4;i++)coh_costume_export_u8(w,v>>(i*8));}
static int coh_costume_export_nonzero(const unsigned char*p){unsigned i;unsigned char v=0;for(i=0;i<32;i++)v|=p[i];return v!=0;}
static int coh_costume_export_size(U32 v){return v>=2&&v<=65536&&!(v&(v-1));}
static int coh_source_costume_export(unsigned char*out,size_t capacity,U32 generation,
 const unsigned char inventory[32],const unsigned char profile[32],const unsigned char run[32],size_t*written){
 CohCostumeExportWriter w;U32 sizes[3],valid[3],seen[3]={0,0,0};int parts,types;unsigned i,t;
 cStashTable tables[3];
 if(!out||!written||!inventory||!profile||!run||!generation||!capacity||capacity>4u*1024u*1024u)return 1;
 if(!coh_costume_export_nonzero(inventory)||!coh_costume_export_nonzero(profile)||!coh_costume_export_nonzero(run))return 1;
 tables[0]=costume_HashTable;tables[1]=costume_HashTableExtraInfo;tables[2]=costume_PaletteTable;
 for(t=0;t<3;t++){
  if(!tables[t])return 1;
  sizes[t]=stashGetMaxSize(tables[t]);valid[t]=stashGetValidElementCount(tables[t]);
  if(!coh_costume_export_size(sizes[t])||valid[t]>sizes[t])return 1;
 }
 parts=GetBodyPartCount();types=getBodyTypeCount();if(parts<1||parts>=30||types!=9)return 1;
 w.p=out;w.cap=capacity;w.at=0;w.error=0;
 coh_costume_export_bytes(&w,"COHCDI1\0",8);coh_costume_export_u32(&w,1);coh_costume_export_u32(&w,generation);
 coh_costume_export_u32(&w,(U32)parts);coh_costume_export_u32(&w,(U32)types);
 for(t=0;t<3;t++)coh_costume_export_u32(&w,sizes[t]);
 for(t=0;t<3;t++)coh_costume_export_u32(&w,valid[t]);
 coh_costume_export_bytes(&w,coh_costume_export_source_id,32);coh_costume_export_bytes(&w,inventory,32);coh_costume_export_bytes(&w,profile,32);coh_costume_export_bytes(&w,run,32);
 for(t=0;t<2&&!w.error;t++)for(i=0;i<sizes[t]&&!w.error;i++){
  const void*key=NULL;
  if(stashFindKeyByIndex(tables[t],i,&key)){
   const char*str=(const char*)key;size_t len=0;if(!str){w.error=1;break;}
   while(len<=259&&str[len])len++;
   if(len>259){w.error=1;break;}
   coh_costume_export_u16(&w,(unsigned)len);coh_costume_export_bytes(&w,str,len);seen[t]++;
  }else coh_costume_export_u16(&w,65535);
 }
 for(i=0;i<sizes[2]&&!w.error;i++){
  int key=0;U32 value=0;int present=stashIntFindKeyByIndex(tables[2],i,&key);
  if(present){memcpy(&value,&key,4);if(!value){w.error=1;break;}seen[2]++;}
  coh_costume_export_u8(&w,present?1:0);coh_costume_export_u32(&w,present?value:0);
 }
 if(w.error)return w.error;
 for(t=0;t<3;t++)if(seen[t]!=valid[t]||sizes[t]!=stashGetMaxSize(tables[t])||valid[t]!=stashGetValidElementCount(tables[t]))return 1;
 *written=w.at;return 0;
}
