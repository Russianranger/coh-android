#include "coh_wr_tex_namespace.h"
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
#include <math.h>

#define NS_PATH 260u
#define NS_PREPARATION 65536u
#define NS_MEMORY_MAX (256u*1024u*1024u)
#define NONE UINT32_MAX
enum {SOURCE_TEX_ALPHA=1u<<0,SOURCE_TEX_TGA=1u<<5,SOURCE_TEX_DDS=1u<<6,SOURCE_TEX_CUBEMAPFACE=1u<<9,SOURCE_TEX_BUMPMAP=1u<<11,SOURCE_TEX_JPEG=1u<<13};
enum {SOURCE_TEXOPT_FADE=1u<<0,SOURCE_TEXOPT_BUMPMAP=1u<<12,SOURCE_TEXOPT_CUBEMAP=1u<<15,SOURCE_TEXOPT_JPEG=1u<<17};
typedef struct {
 char path[NS_PATH];
 CohAssetSource source;
 int32_t timestamp,location,file_index;
 uint32_t directory,root;
} Record;
typedef struct {
 char name[NS_PATH];
 uint32_t parent,first,next,record,directory,seen_fs;
} Node;
typedef struct {
 char original[1024],directory[1000],key[128];
 uint8_t hash[32],mips[1024];
 uint32_t record,first,width,height,flags,basic_flags,offset,bytes,mip_bytes;
 float fade[2];
 uint8_t alpha;
} Basic;
struct CohWrTexNamespaceBody {
 const CohAssetBlob *blob;
 struct CohWrTexNamespace *owner;
};
struct CohWrTexNamespace {
 CohWrTexNamespaceReport report;
 CohWrTexNamespaceLimits limits;
 CohWrTexNamespaceRequest policy;
 CohAssetLoader *loader;
 Record *records;
 Node *nodes;
 Basic *basics;
 uint32_t *order,*node_hash,*basic_hash;
 CohWrTexNamespaceBody *bodies;
 CohAssetSource *piggs;
 uint32_t *root_generations,*root_counts;
 char (*root_paths)[1024];
 char exclusion_folder[NS_PATH];
 char prefixes[50][NS_PATH];
 size_t borrowed;
 uint32_t record_count,node_count,basic_count,basic_capacity,node_capacity,node_hash_count,basic_hash_count;
 uint32_t held,busy;
};
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static unsigned upper(unsigned c){return c>='a'&&c<='z'?c-32:c;}
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint16_t u16(const uint8_t*p){return (uint16_t)((uint16_t)p[0]|(uint16_t)p[1]<<8);}
static int compare(const char*a,const char*b){while(*a&&*b){int d=(int)fold((unsigned char)*a++)-(int)fold((unsigned char)*b++);if(d)return d;}return(unsigned char)*a-(unsigned char)*b;}
static int disjoint(const void*a,size_t n,const void*b,size_t m){uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;return x<=UINTPTR_MAX-n&&y<=UINTPTR_MAX-m&&(x+n<=y||y+m<=x);}
static int plus(size_t*n,size_t v){if(v>SIZE_MAX-*n)return 0;*n+=v;return 1;}
static int cancelled(CohCancel c){return c.poll&&c.poll(c.context);}
static CohStatus text(const char*s,size_t max,size_t*n){if(!s)return COH_INVALID;for(size_t k=0;k<=max;k++){unsigned c=(unsigned char)s[k];if(!c){*n=k;return COH_OK;}if(c<32||c>126)return COH_UNSUPPORTED;}return COH_LIMIT;}
static CohStatus path(const char*s,char out[NS_PATH]){
 size_t n;CohStatus status=text(s,NS_PATH-1,&n);if(status!=COH_OK)return status;
 if(!n||s[0]=='/'||s[0]=='\\')return COH_INVALID;
 size_t start=0;
 for(size_t i=0;i<=n;i++){
  char c=s[i]=='\\'?'/':s[i];out[i]=c;
  if(c==':')return COH_INVALID;
  if(c=='/'||!c){size_t length=i-start;if(!length||(length==1&&s[start]=='.')||(length==2&&s[start]=='.'&&s[start+1]=='.'))return COH_INVALID;start=i+1;}
 }
 return COH_OK;
}
static uint32_t hash(const char*s,uint32_t seed){uint32_t h=seed;for(;*s;s++)h=(h^fold((unsigned char)*s))*16777619u;return h;}
static uint32_t capacity(uint32_t count){uint32_t n=1;while(n<count*2u)n*=2u;return n;}
static int room(CohWrTexNamespace*r,size_t extra){
 size_t n=r->limits.external_bytes;
 return plus(&n,NS_PREPARATION)&&plus(&n,r->limits.loader.total_bytes)&&plus(&n,r->borrowed)&&plus(&n,r->report.owned_bytes)&&plus(&n,extra)&&n<=r->limits.aggregate_limit;
}
static void *take(CohWrTexNamespace*r,size_t bytes){
 if(!bytes)bytes=1;
 if(bytes>r->limits.owned_limit-r->report.owned_bytes||!room(r,bytes))return NULL;
 void*p=calloc(1,bytes?bytes:1);if(!p)return NULL;r->report.owned_bytes+=bytes?bytes:1;
 if(r->report.owned_bytes>r->report.peak_owned_bytes)r->report.peak_owned_bytes=r->report.owned_bytes;
 return p;
}
static int output_ok(const CohWrTexNamespace*r,const void*out,size_t size){
 if(!disjoint(r,sizeof(*r),out,size)||!disjoint(r->records,(size_t)r->record_count*sizeof(Record),out,size)||!disjoint(r->nodes,(size_t)r->node_capacity*sizeof(Node),out,size)||!disjoint(r->basics,(size_t)r->basic_capacity*sizeof(Basic),out,size)||!disjoint(r->order,(size_t)r->record_count*sizeof(uint32_t),out,size)||!disjoint(r->node_hash,(size_t)r->node_hash_count*sizeof(uint32_t),out,size)||!disjoint(r->basic_hash,(size_t)r->basic_hash_count*sizeof(uint32_t),out,size)||!disjoint(r->bodies,(size_t)r->limits.body_lease_limit*sizeof(*r->bodies),out,size)||!disjoint(r->piggs,(size_t)r->policy.pigg_count*sizeof(CohAssetSource),out,size)||!disjoint(r->root_generations,(size_t)r->policy.root_count*sizeof(uint32_t),out,size)||!disjoint(r->root_counts,(size_t)r->policy.root_count*sizeof(uint32_t),out,size)||!disjoint(r->root_paths,(size_t)r->policy.root_count*sizeof(*r->root_paths),out,size))return 0;
 for(uint32_t i=0;i<r->limits.body_lease_limit;i++)if(r->bodies[i].blob){CohBytes b=coh_asset_bytes(r->bodies[i].blob);if(!disjoint(b.data,b.size,out,size))return 0;}
 return 1;
}
static CohStatus read_source(CohAssetSource s,uint64_t at,void*out,size_t size){if(!s.read_at||at>s.size||size>s.size-at)return COH_INVALID;return size?s.read_at(s.context,at,out,size):COH_OK;}
static int source_equal(CohAssetSource a,CohAssetSource b){return a.read_at==b.read_at&&a.context==b.context&&a.size==b.size&&a.generation==b.generation;}
static int prefix(const char*s,const char*key){for(;*key;s++,key++)if(fold((unsigned char)*s)!=fold((unsigned char)*key))return 0;return 1;}
static int ignored(const CohWrTexNamespace*r,const char*s){
 for(uint32_t i=0;i<r->policy.ignore_prefix_count;i++){
  const char*p=r->prefixes[i];size_t n=strlen(p);if(!n)continue;if(prefix(s,p))return 1;
  /* Preserve original's two exact slash searches, including its mixed-case
   * behavior; replacing this with a general case-insensitive search differs. */
  char lower[NS_PATH+1],higher[NS_PATH+1];lower[0]=higher[0]='/';
  for(size_t j=0;j<n;j++){lower[j+1]=(char)fold((unsigned char)p[j]);higher[j+1]=(char)upper((unsigned char)p[j]);}lower[n+1]=higher[n+1]=0;
  if(strstr(s,lower)||strstr(s,higher))return 1;
 }
 return 0;
}
/* Path-component order, not plain full-path lexical order: a/b precedes
 * a.texture because sibling a precedes sibling a.texture in FolderNodeAdd. */
static int path_compare(const char*a,const char*b){
 for(;;){unsigned x=fold((unsigned char)*a),y=fold((unsigned char)*b);unsigned ax=(x=='/')?0:x,by=(y=='/')?0:y;if(ax!=by)return ax<by?-1:1;if(!ax){if(!x||!y)return x==y?0:(!x?-1:1);}a++;b++;}
}
static int record_less(const CohWrTexNamespace*r,uint32_t a,uint32_t b){int d=path_compare(r->records[a].path,r->records[b].path);return d<0||(d==0&&a<b);}
static void sift(CohWrTexNamespace*r,uint32_t count,uint32_t root){for(;;){uint32_t child=root*2u+1u;if(child>=count)return;if(child+1<count&&record_less(r,r->order[child],r->order[child+1]))child++;if(!record_less(r,r->order[root],r->order[child]))return;uint32_t t=r->order[root];r->order[root]=r->order[child];r->order[child]=t;root=child;}}
static uint32_t component_count(const char*p){uint32_t n=1;for(;*p;p++)if(*p=='/')n++;return n;}
static uint32_t common_components(const char*a,const char*b){uint32_t n=0;for(;;){const char*x=a,*y=b;while(*a&&*a!='/'&&*b&&*b!='/'&&fold((unsigned char)*a)==fold((unsigned char)*b)){a++;b++;}if((!*a||*a=='/')&&(!*b||*b=='/')){n++;if(!*a||!*b)return n;a++;b++;}else{(void)x;(void)y;return n;}}}
static CohStatus prepare_tree(CohWrTexNamespace*r,CohCancel cancel){
 r->order=take(r,(size_t)r->record_count*sizeof(uint32_t));if(!r->order)return COH_LIMIT;
 for(uint32_t i=0;i<r->record_count;i++)r->order[i]=i;
 for(uint32_t i=r->record_count/2;i;i--){if(cancelled(cancel))return COH_CANCELLED;sift(r,r->record_count,i-1);}
 for(uint32_t n=r->record_count;n>1;n--){if(cancelled(cancel))return COH_CANCELLED;uint32_t t=r->order[0];r->order[0]=r->order[n-1];r->order[n-1]=t;sift(r,n-1,0);}
 uint32_t count=1; /* synthetic root */
 for(uint32_t i=0;i<r->record_count;i++){
  const char*p=r->records[r->order[i]].path;uint32_t common=i?common_components(p,r->records[r->order[i-1]].path):0;
  uint32_t extra=component_count(p)-common;if(extra>r->limits.node_limit-count)return COH_LIMIT;count+=extra;
 }
 /* Dynamic RequestTree may synthesize texture_library even if all inputs are
  * elsewhere. Reserve it independently rather than inventing a file record. */
 if(count==r->limits.node_limit)return COH_LIMIT;
 count++;
 r->node_capacity=count;r->node_hash_count=capacity(count);
 r->nodes=take(r,(size_t)count*sizeof(Node));r->node_hash=take(r,(size_t)r->node_hash_count*sizeof(uint32_t));if(!r->nodes||!r->node_hash)return COH_LIMIT;
 r->node_count=1;r->nodes[0].first=NONE;return COH_OK;
}
static uint32_t *node_slot(CohWrTexNamespace*r,uint32_t parent,const char*name){uint32_t pos=hash(name,2166136261u^parent)&(r->node_hash_count-1);while(r->node_hash[pos]){Node*n=r->nodes+r->node_hash[pos];if(n->parent==parent&&!compare(n->name,name))break;pos=(pos+1)&(r->node_hash_count-1);}return r->node_hash+pos;}
static int replace(const Record*old,const Record*next){
 if(next->location<0&&old->location<0)return next->location<=old->location;
 if(next->location<0)return next->timestamp==old->timestamp||(int64_t)next->timestamp-old->timestamp==3600;
 if(old->location<0)return !(next->timestamp==old->timestamp||(int64_t)next->timestamp-old->timestamp==3600);
 return next->location>=old->location;
}
static CohStatus insert(CohWrTexNamespace*r,uint32_t row){
 Record*record=r->records+row;uint32_t parent=0;const char*cursor=record->path;
 for(;;){char name[NS_PATH];size_t n=0;while(cursor[n]&&cursor[n]!='/')n++;memcpy(name,cursor,n);name[n]=0;int directory=cursor[n]=='/'||record->directory;
  uint32_t*slot=node_slot(r,parent,name);Node*node;
  if(!*slot){if(r->node_count==r->node_capacity)return COH_LIMIT;uint32_t index=r->node_count++;*slot=index;node=r->nodes+index;strcpy(node->name,name);node->parent=parent;node->record=row;node->directory=(uint32_t)directory;node->seen_fs=record->location>=0;node->first=NONE;node->next=r->nodes[parent].first;r->nodes[parent].first=index;}
  else{node=r->nodes+*slot;if(directory){node->directory=1;}else if(!node->directory){Record*old=r->records+node->record;if(record->location>=0||old->location>=0)node->seen_fs=1;if(replace(old,record))node->record=row;}}
  parent=*slot;if(!cursor[n])return COH_OK;cursor+=n+1;
 }
}
static uint32_t find_node(CohWrTexNamespace*r,const char*path_name){uint32_t parent=0;const char*p=path_name;for(;;){char name[NS_PATH];size_t n=0;while(p[n]&&p[n]!='/')n++;memcpy(name,p,n);name[n]=0;uint32_t*slot=node_slot(r,parent,name);if(!*slot)return NONE;parent=*slot;if(!p[n])return parent;p+=n+1;}}
static int allowed_fs(const CohWrTexNamespace*r,const Record*x){
 const char*s=x->path;for(;;){if(*s=='.')return 0;const char*end=strchr(s,'/');if(!end)break;s=end+1;}
 if(!r->policy.development_data&&r->policy.disallow_overrides)return 0;
 if(!r->policy.development_data){const char*bad[]={"scenes","ent_types","object_library","geobin"};const char*root=r->root_paths[x->root];size_t size=strlen(root);for(unsigned i=0;i<4;i++){size_t n=strlen(bad[i]);if(size>n&&(root[size-n-1]=='/'||root[size-n-1]=='\\')&&!compare(root+size-n,bad[i]))return 0;}s=x->path;for(;;){const char*end=strchr(s,'/');size_t n=end?(size_t)(end-s):strlen(s);if(end||x->directory)for(unsigned i=0;i<4;i++)if(strlen(bad[i])==n){char temp[NS_PATH];memcpy(temp,s,n);temp[n]=0;if(!compare(temp,bad[i]))return 0;}if(!end)break;s=end+1;}}
 s=x->path;
 for(uint32_t depth=0;;depth++){
  const char*end=strchr(s,'/');size_t n=end?(size_t)(end-s):strlen(s);
  if(end||x->directory){char name[NS_PATH];memcpy(name,s,n);name[n]=0;
   if(r->policy.folder_exclusion==1&&!(r->policy.mode==COH_WR_TEX_NS_DEVELOPMENT_DYNAMIC&&depth==0)&&!compare(name,r->exclusion_folder))return 0;
   if(r->policy.folder_exclusion==2&&r->policy.mode!=COH_WR_TEX_NS_DEVELOPMENT_DYNAMIC&&depth==0&&compare(name,r->exclusion_folder))return 0;
  }
  if(!end)break;
  s=end+1;
 }
 return 1;
}
static int texture_path(const char*p){return prefix(p,"texture_library/");}
static CohStatus merge(CohWrTexNamespace*r,CohCancel cancel){
 for(unsigned phase=0;phase<2;phase++){
 if(phase==1&&r->policy.mode==COH_WR_TEX_NS_DEVELOPMENT_DYNAMIC){
  /* fileScanAllDataDirs falls back to the legacy OS scanner before RequestTree
   * when the initial FolderCache is empty. That route is unsupported here. */
  if(r->node_count==1)return COH_UNSUPPORTED;
  if(!r->policy.quickload&&find_node(r,"texture_library")==NONE){
   uint32_t*slot=node_slot(r,0,"texture_library");if(r->node_count==r->node_capacity)return COH_LIMIT;*slot=r->node_count++;Node*n=r->nodes+*slot;strcpy(n->name,"texture_library");n->parent=0;n->directory=1;n->record=NONE;n->first=NONE;n->next=r->nodes[0].first;r->nodes[0].first=*slot;
  }
 }
 for(uint32_t i=0;i<r->record_count;i++){
  Record*x=r->records+i;int fs=x->location>=0;int want_fs=(r->policy.mode==COH_WR_TEX_NS_DEVELOPMENT_DYNAMIC)?phase==1:phase==0;
  if(fs!=want_fs)continue;
 if(cancelled(cancel))return COH_CANCELLED;
  if(fs){if(r->policy.mode==COH_WR_TEX_NS_PIGS_ONLY||(r->policy.mode==COH_WR_TEX_NS_DEVELOPMENT_DYNAMIC&&(r->policy.quickload||(!texture_path(x->path)&&compare(x->path,"texture_library"))))||!allowed_fs(r,x))continue;}
  else if(r->policy.mode==COH_WR_TEX_NS_DEVELOPMENT&&(ignored(r,x->path)||find_node(r,x->path)==NONE))continue;
  CohStatus status=insert(r,i);if(status!=COH_OK)return status;
 }
 }
 if(r->node_count==1)return COH_UNSUPPORTED;
 /* FolderNodeAdd sorts siblings while inserting. Sort the completed sibling
  * lists here; this changes no creation spelling, winner or seen_in_fs state. */
 for(uint32_t parent=0;parent<r->node_count;parent++){
  uint32_t head=r->nodes[parent].first;
  for(uint32_t width=1;head!=NONE;width*=2){
   if(cancelled(cancel))return COH_CANCELLED;
   uint32_t at=head,next_head=NONE,tail=NONE,merges=0;
   while(at!=NONE){
    merges++;uint32_t other=at,left=0,right=width;for(uint32_t k=0;k<width&&other!=NONE;k++){left++;other=r->nodes[other].next;}
    while(left||(right&&other!=NONE)){
     uint32_t selected;
     if(!left){selected=other;other=r->nodes[other].next;right--;}
     else if(!right||other==NONE){selected=at;at=r->nodes[at].next;left--;}
     else if(compare(r->nodes[at].name,r->nodes[other].name)<=0){selected=at;at=r->nodes[at].next;left--;}
     else{selected=other;other=r->nodes[other].next;right--;}
     if(tail!=NONE)r->nodes[tail].next=selected;else next_head=selected;tail=selected;
    }
    at=other;
   }
   r->nodes[tail].next=NONE;head=next_head;if(merges<=1)break;
  }
  r->nodes[parent].first=head;
 }
 return COH_OK;
}
static uint32_t *basic_slot(CohWrTexNamespace*r,const char*key){uint32_t pos=hash(key,2166136261u)&(r->basic_hash_count-1);while(r->basic_hash[pos]&&compare(r->basics[r->basic_hash[pos]-1].key,key))pos=(pos+1)&(r->basic_hash_count-1);return r->basic_hash+pos;}
static uint32_t basic_type(char*name,CohStatus*status){
 size_t n=strlen(name);if(n<4)return SOURCE_TEX_TGA;
 if(name[n-4]=='.'){uint32_t flags=!strcmp(name+n-3,"tga")?SOURCE_TEX_TGA:!strcmp(name+n-3,"jpg")?SOURCE_TEX_JPEG:!strcmp(name+n-3,"dds")?SOURCE_TEX_DDS:0;name[n-4]=0;return flags;}
 if(n<8){*status=COH_UNSUPPORTED;return 0;}
 if(name[n-8]=='.'){uint32_t flags=!strcmp(name+n-7,"texture")?SOURCE_TEX_DDS:0;name[n-8]=0;return flags;}return 0;
}
static CohStatus parse_header(CohBytes bytes,Basic*b,const char*filename){
 if(bytes.size<33)return COH_INVALID;
 uint32_t header=u32(bytes.data),payload=u32(bytes.data+4);
 if(header<=32||header>1056||header>bytes.size||payload>INT32_MAX)return COH_INVALID;
 const char*original=(const char*)bytes.data+32;const char*end=memchr(original,0,header-32);if(!end)return COH_INVALID;
 size_t n=(size_t)(end-original);if(n>=sizeof(b->original))return COH_LIMIT;memcpy(b->original,original,n+1);
 size_t checked;CohStatus status=text(b->original,1023,&checked);if(status!=COH_OK)return status;
 if(!prefix(b->original,"texture_library/"))return COH_UNSUPPORTED;
 const char*directory=b->original+15;while(*directory=='/')directory++;
 if(strlen(directory)>=sizeof(b->directory))return COH_LIMIT;
 strcpy(b->directory,directory);char*slash=strrchr(b->directory,'/');if(slash)*slash=0;
 const char*base=strrchr(b->original,'/');if(!base||!base[1])return COH_INVALID;base++;if(strlen(base)>=sizeof(b->key))return COH_LIMIT;strcpy(b->key,base);b->basic_flags=basic_type(b->key,&status);if(status!=COH_OK)return status;
 const char*file=strrchr(filename,'/');file=file?file+1:filename;size_t length=strlen(file);if(length<8||length-8>=128)return COH_LIMIT;char stem[128];memcpy(stem,file,length-8);stem[length-8]=0;if(b->key[0]&&compare(stem,b->key))return COH_INVALID;
 b->width=u32(bytes.data+8);b->height=u32(bytes.data+12);b->flags=u32(bytes.data+16);b->alpha=bytes.data[28];
 if(!b->width||!b->height||b->width>INT32_MAX||b->height>INT32_MAX||b->alpha>1)return COH_INVALID;
 if((b->basic_flags&SOURCE_TEX_JPEG)&&!(b->flags&SOURCE_TEXOPT_JPEG))return COH_INVALID;
 uint32_t fade=u32(bytes.data+20);memcpy(b->fade,&fade,4);fade=u32(bytes.data+24);memcpy(b->fade+1,&fade,4);
 if(!isfinite(b->fade[0])||!isfinite(b->fade[1]))return COH_UNSUPPORTED;
 if(b->alpha&&!(b->flags&SOURCE_TEXOPT_FADE))b->basic_flags|=SOURCE_TEX_ALPHA;
 if(b->flags&SOURCE_TEXOPT_BUMPMAP)b->basic_flags|=SOURCE_TEX_BUMPMAP;
 if(b->flags&SOURCE_TEXOPT_CUBEMAP)for(const char*s=b->key;*s;s++)if(prefix(s,"cubemap")){b->basic_flags|=SOURCE_TEX_CUBEMAPFACE;break;}
 b->offset=header;b->bytes=payload;
 if(bytes.data[29]=='T'&&bytes.data[30]=='X'&&bytes.data[31]=='2'){b->mip_bytes=header-32-(uint32_t)n-1;if(b->mip_bytes>sizeof(b->mips))return COH_LIMIT;memcpy(b->mips,end+1,b->mip_bytes);}
 return COH_OK;
}
static CohStatus scan_node(CohWrTexNamespace*r,uint32_t index,char path_name[NS_PATH],size_t parent_bytes,CohCancel cancel){
 typedef struct{uint32_t next;size_t prefix_bytes;}Frame;
 Frame frames[130];uint32_t depth=1;frames[0]=(Frame){index,parent_bytes};
 while(depth){
  Frame*frame=frames+depth-1;index=frame->next;if(index==NONE){depth--;continue;}if(cancelled(cancel))return COH_CANCELLED;
  Node*n=r->nodes+index;frame->next=n->next;parent_bytes=frame->prefix_bytes;size_t count=strlen(n->name);if(parent_bytes+count>=NS_PATH)return COH_LIMIT;memcpy(path_name+parent_bytes,n->name,count+1);
  if(ignored(r,path_name)||n->name[0]=='_'){r->report.ignored++;continue;}
  if(n->directory){
   if(n->first!=NONE){if(depth==130)return COH_LIMIT;path_name[parent_bytes+count]='/';frames[depth++]=(Frame){n->first,parent_bytes+count+1};}
   continue;
  }
  if(!(r->policy.mode==COH_WR_TEX_NS_DEVELOPMENT_DYNAMIC&&!r->policy.quickload&&!n->seen_fs)&&count>=8&&!compare(n->name+count-8,".texture")){
   char key[128];if(count-8>=sizeof(key))return COH_LIMIT;memcpy(key,n->name,count-8);key[count-8]=0;
   if(r->policy.lwc_active&&r->policy.lwc_last_completed_stage>1&&*basic_slot(r,key)){r->report.lwc_skipped++;continue;}
   if(r->basic_count==r->limits.basic_limit)return COH_LIMIT;
 Basic*b=r->basics+r->basic_count;Record*x=r->records+n->record;
   const CohAssetBlob*blob=NULL;CohStatus status=coh_asset_acquire(r->loader,(CohAssetId){x->path,x->source.generation},cancel,&blob);if(status!=COH_OK)return status;CohBytes bytes=coh_asset_bytes(blob);
   status=parse_header(bytes,b,n->name);if(status==COH_OK)status=r->policy.digest(r->policy.digest_context,bytes,b->hash);coh_asset_release(r->loader,blob);if(status!=COH_OK)return status;b->record=n->record;
   uint32_t*slot=basic_slot(r,b->key);b->first=*slot?*slot-1:r->basic_count;if(!*slot){*slot=r->basic_count+1;r->report.first_keys++;}else{strcpy(b->key,r->basics[b->first].key);r->report.duplicates_retained++;}r->basic_count++;
  }
 }
 return COH_OK;
}
static void untake(CohWrTexNamespace*r,void*p,size_t bytes){if(p){free(p);r->report.owned_bytes-=bytes?bytes:1;}}
static CohStatus collect_pig(CohWrTexNamespace*r,CohAssetSource source,uint32_t pig_index,CohCancel cancel){
 CohStatus status=coh_asset_mount_pigg(r->loader,source,cancel);if(status!=COH_OK)return status;
 uint8_t header[16],pool_header[12];status=read_source(source,0,header,sizeof(header));if(status!=COH_OK)return status;
 uint32_t count=u32(header+12);uint16_t archive_header=u16(header+8),file_header=u16(header+10);
 uint64_t pool_at=(uint64_t)archive_header+(uint64_t)file_header*count;
 status=read_source(source,pool_at,pool_header,sizeof(pool_header));if(status!=COH_OK)return status;
 uint32_t name_count=u32(pool_header+4),name_bytes=u32(pool_header+8);
 if(u32(pool_header)!=0x6789||name_count!=count||name_bytes>(uint64_t)count*(NS_PATH+4u))return COH_INVALID;
 uint8_t*names=take(r,name_bytes);uint32_t*offsets=take(r,(size_t)count*sizeof(uint32_t));
 if(!names||!offsets){untake(r,names,name_bytes);untake(r,offsets,(size_t)count*sizeof(uint32_t));return COH_LIMIT;}
 status=read_source(source,pool_at+12,names,name_bytes);if(status!=COH_OK)goto done;
 size_t cursor=0;
 for(uint32_t i=0;i<count;i++){
  if(cursor>name_bytes||name_bytes-cursor<4){status=COH_INVALID;goto done;}uint32_t n=u32(names+cursor);cursor+=4;
  if(!n||n>NS_PATH||n>name_bytes-cursor||names[cursor+n-1]||memchr(names+cursor,0,n-1)){status=COH_INVALID;goto done;}offsets[i]=(uint32_t)cursor;cursor+=n;
 }
 if(cursor!=name_bytes){status=COH_INVALID;goto done;}
 for(uint32_t i=0;i<count;i++){
  if(cancelled(cancel)){status=COH_CANCELLED;goto done;}uint8_t file[48];status=read_source(source,(uint64_t)archive_header+(uint64_t)i*file_header,file,sizeof(file));if(status!=COH_OK)goto done;
  uint32_t name=u32(file+4);if(name!=i){status=COH_UNSUPPORTED;goto done;}if(name>=count||r->record_count==r->limits.record_limit){status=COH_LIMIT;goto done;}
  Record*x=r->records+r->record_count;status=path((const char*)names+offsets[name],x->path);if(status!=COH_OK)goto done;
  CohAssetInfo info;status=coh_asset_lookup(r->loader,(CohAssetId){x->path,source.generation},&info);if(status!=COH_OK)goto done;
  if(info.timestamp>INT32_MAX){status=COH_UNSUPPORTED;goto done;}x->timestamp=(int32_t)info.timestamp;x->source=source;x->location=-(int32_t)pig_index-1;x->file_index=(int32_t)i;x->root=NONE;r->record_count++;
 }
done:
 untake(r,names,name_bytes);untake(r,offsets,(size_t)count*sizeof(uint32_t));return status;
}
static CohStatus validate(const CohWrTexNamespaceRequest*q,const CohWrTexNamespaceLimits*b,CohWrTexNamespace**out,size_t*borrowed){
 if(!q||!b||!out||!q->input_generation||!q->digest||!q->provider_hold||!q->provider_drop||(q->root_count&&!q->roots)||(q->pigg_count&&!q->piggs)||(q->ignore_prefix_count&&!q->ignore_prefixes))return COH_INVALID;
 if(!disjoint(q,sizeof(*q),out,sizeof(*out))||!disjoint(b,sizeof(*b),out,sizeof(*out))||!disjoint(q->roots,(size_t)q->root_count*sizeof(*q->roots),out,sizeof(*out))||!disjoint(q->piggs,(size_t)q->pigg_count*sizeof(*q->piggs),out,sizeof(*out))||!disjoint(q->ignore_prefixes,(size_t)q->ignore_prefix_count*sizeof(char*),out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 if(q->root_count>32768||q->pigg_count>32768||q->mode>3||q->ignore_prefix_count>50)return COH_UNSUPPORTED;
 if(q->quickload>1||q->development_data>1||q->disallow_overrides>1||q->lwc_active>1||q->folder_exclusion>2)return COH_INVALID;
 if(!b->owned_limit||!b->aggregate_limit||b->aggregate_limit>NS_MEMORY_MAX||!b->record_limit||b->record_limit>262144||!b->node_limit||b->node_limit>262144||!b->basic_limit||b->basic_limit>65536||!b->body_lease_limit||b->body_lease_limit>256)return COH_LIMIT;
 if(q->predecessor&&q->predecessor->busy)return COH_STATE;
 if(q->predecessor&&(!q->lwc_active||q->lwc_last_completed_stage<=1||!output_ok(q->predecessor,out,sizeof(*out))))return COH_INVALID;
 if(q->predecessor){size_t minimum=q->predecessor->report.owned_bytes;if(q->predecessor->busy)return COH_STATE;if(!plus(&minimum,q->predecessor->limits.loader.total_bytes)||b->external_bytes<minimum)return COH_LIMIT;}
 size_t n=sizeof(*q)+sizeof(*b);
 if(!plus(&n,(size_t)q->root_count*sizeof(*q->roots))||!plus(&n,(size_t)q->pigg_count*sizeof(*q->piggs))||!plus(&n,(size_t)q->ignore_prefix_count*sizeof(char*)))return COH_LIMIT;
 if(q->folder_exclusion){size_t size;CohStatus status=text(q->exclusion_folder,NS_PATH-1,&size);if(status!=COH_OK)return status;if(!disjoint(q->exclusion_folder,size+1,out,sizeof(*out)))return COH_INVALID;if(!plus(&n,size+1))return COH_LIMIT;}
 uint32_t records=0;
 for(uint32_t i=0;i<q->ignore_prefix_count;i++){size_t size;CohStatus status=text(q->ignore_prefixes[i],NS_PATH-1,&size);if(status!=COH_OK)return status;if(!disjoint(q->ignore_prefixes[i],size+1,out,sizeof(*out)))return COH_INVALID;if(!plus(&n,size+1))return COH_LIMIT;}
 for(uint32_t i=0;i<q->root_count;i++){
  const CohWrTexNamespaceRoot*root=q->roots+i;if(!root->generation||(root->count&&!root->files))return COH_INVALID;
  size_t root_size;CohStatus root_status=text(root->root_path,1023,&root_size);if(root_status!=COH_OK)return root_status;if(!root_size||!disjoint(root->root_path,root_size+1,out,sizeof(*out)))return COH_INVALID;if(!plus(&n,root_size+1))return COH_LIMIT;
  if(root->count>b->record_limit-records)return COH_LIMIT;
 records+=root->count;
  if(!disjoint(root->files,(size_t)root->count*sizeof(*root->files),out,sizeof(*out)))return COH_INVALID;
  if(!plus(&n,(size_t)root->count*sizeof(*root->files)))return COH_LIMIT;
  for(uint32_t j=0;j<i;j++)if(q->roots[j].generation==root->generation)return COH_INVALID;
  for(uint32_t j=0;j<root->count;j++){
   const CohWrTexNamespaceFile*file=root->files+j;char normalized[NS_PATH];CohStatus status=path(file->path,normalized);if(status!=COH_OK)return status;size_t size=strlen(file->path)+1;
   if(!disjoint(file->path,size,out,sizeof(*out)))return COH_INVALID;
 if(!plus(&n,size))return COH_LIMIT;
   if(file->timestamp<0||file->is_directory>1)return COH_UNSUPPORTED;
   if(file->is_directory){if(file->bytes.read_at||file->bytes.context||file->bytes.size||file->bytes.generation)return COH_INVALID;}
   else if(!file->bytes.read_at||file->bytes.generation!=root->generation||file->bytes.size>UINT32_MAX)return COH_INVALID;
  }
 }
 for(uint32_t i=0;i<q->pigg_count;i++){
  CohAssetSource source=q->piggs[i];if(!source.read_at||!source.generation)return COH_INVALID;
  for(uint32_t j=0;j<q->root_count;j++)if(q->roots[j].generation==source.generation)return COH_INVALID;
  for(uint32_t j=0;j<i;j++)if(q->piggs[j].generation==source.generation)return COH_INVALID;
 }
 *borrowed=n;return COH_OK;
}
static CohStatus predecessor(CohWrTexNamespace*r,const CohWrTexNamespace*old){
 if(!old)return COH_OK;
 if(old->policy.root_count!=r->policy.root_count||old->policy.pigg_count>r->policy.pigg_count||old->policy.mode!=r->policy.mode||old->policy.quickload!=r->policy.quickload||old->policy.development_data!=r->policy.development_data||old->policy.disallow_overrides!=r->policy.disallow_overrides||old->policy.folder_exclusion!=r->policy.folder_exclusion||strcmp(old->exclusion_folder,r->exclusion_folder)||old->policy.ignore_prefix_count!=r->policy.ignore_prefix_count||old->policy.lwc_last_completed_stage>r->policy.lwc_last_completed_stage)return COH_STATE;
 for(uint32_t i=0;i<old->policy.ignore_prefix_count;i++)if(strcmp(old->prefixes[i],r->prefixes[i]))return COH_STATE;
 for(uint32_t i=0;i<old->policy.root_count;i++)if(old->root_generations[i]!=r->root_generations[i]||old->root_counts[i]!=r->root_counts[i]||strcmp(old->root_paths[i],r->root_paths[i]))return COH_STATE;
 for(uint32_t i=0;i<old->policy.pigg_count;i++)if(!source_equal(old->piggs[i],r->piggs[i]))return COH_STATE;
 if(old->record_count>r->record_count)return COH_STATE;
 for(uint32_t i=0;i<old->record_count;i++){
  const Record*a=old->records+i,*b=r->records+i;
  if(strcmp(a->path,b->path)||a->timestamp!=b->timestamp||a->location!=b->location||a->file_index!=b->file_index||a->directory!=b->directory||a->root!=b->root||!source_equal(a->source,b->source))return COH_STATE;
 }
 return COH_OK;
}
static void dispose(CohWrTexNamespace*r){
 if(!r)return;
 if(r->loader)(void)coh_asset_destroy(&r->loader);
 free(r->records);free(r->nodes);free(r->basics);free(r->order);free(r->node_hash);free(r->basic_hash);free(r->bodies);free(r->piggs);free(r->root_generations);free(r->root_counts);free(r->root_paths);
 if(r->held)r->policy.provider_drop(r->policy.provider_context);
 free(r);
}
CohStatus coh_wr_tex_namespace_build(const CohWrTexNamespaceRequest*q,const CohWrTexNamespaceLimits*b,CohCancel cancel,CohWrTexNamespace**out){
 size_t borrowed=0;CohStatus status=validate(q,b,out,&borrowed);if(status!=COH_OK)return status;
 CohWrTexNamespace initial;memset(&initial,0,sizeof(initial));initial.limits=*b;initial.borrowed=borrowed;initial.report.owned_bytes=sizeof(initial);
 if(sizeof(initial)>b->owned_limit||!room(&initial,0))return COH_LIMIT;
 CohWrTexNamespace*previous=(CohWrTexNamespace*)q->predecessor;if(previous)previous->busy=1;
 if(cancelled(cancel)){if(previous)previous->busy=0;return COH_CANCELLED;}
 CohWrTexNamespace*r=calloc(1,sizeof(*r));if(!r){if(previous)previous->busy=0;return COH_LIMIT;}*r=initial;r->policy=*q;r->report.peak_owned_bytes=sizeof(*r);
 for(uint32_t i=0;i<q->ignore_prefix_count;i++)strcpy(r->prefixes[i],q->ignore_prefixes[i]);
 if(q->folder_exclusion)strcpy(r->exclusion_folder,q->exclusion_folder);
 status=q->provider_hold(q->provider_context);if(status!=COH_OK)goto fail;r->held=1;
 uint32_t count=0,files=0;
 for(uint32_t i=0;i<q->root_count;i++)for(uint32_t j=0;j<q->roots[i].count;j++){count++;if(!q->roots[i].files[j].is_directory)files++;}
 for(uint32_t i=0;i<q->pigg_count;i++){
  if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}uint8_t header[16];status=read_source(q->piggs[i],0,header,sizeof(header));if(status!=COH_OK)goto fail;
  if(u32(header)!=0x123||u16(header+6)>2){status=COH_UNSUPPORTED;goto fail;}uint32_t entries=u32(header+12);if(entries>b->record_limit-count){status=COH_LIMIT;goto fail;}count+=entries;if(entries>UINT32_MAX-files){status=COH_LIMIT;goto fail;}files+=entries;
 }
 if(!count||count>b->record_limit||b->loader.entries<files){status=COH_LIMIT;goto fail;}
 /* The configured source bound is checked precisely after counting loose files;
  * one archive is one source, not one source for each internal PIGG record. */
 uint32_t loose=0;for(uint32_t i=0;i<q->root_count;i++)for(uint32_t j=0;j<q->roots[i].count;j++)if(!q->roots[i].files[j].is_directory)loose++;
 if(q->pigg_count>UINT32_MAX-loose||b->loader.sources<loose+q->pigg_count){status=COH_LIMIT;goto fail;}
 r->records=take(r,(size_t)count*sizeof(Record));r->piggs=take(r,(size_t)q->pigg_count*sizeof(CohAssetSource));r->root_generations=take(r,(size_t)q->root_count*sizeof(uint32_t));r->root_counts=take(r,(size_t)q->root_count*sizeof(uint32_t));r->root_paths=take(r,(size_t)q->root_count*sizeof(*r->root_paths));r->bodies=take(r,(size_t)b->body_lease_limit*sizeof(*r->bodies));
 if(!r->records||!r->piggs||!r->root_generations||!r->root_counts||!r->root_paths||!r->bodies){status=COH_LIMIT;goto fail;}
 if(q->pigg_count)memcpy(r->piggs,q->piggs,(size_t)q->pigg_count*sizeof(CohAssetSource));
 status=coh_asset_create(&b->loader,&r->loader);if(status!=COH_OK)goto fail;
 for(uint32_t reverse=q->root_count;reverse;reverse--){
  uint32_t root_index=reverse-1;const CohWrTexNamespaceRoot*root=q->roots+root_index;r->root_generations[root_index]=root->generation;r->root_counts[root_index]=root->count;strcpy(r->root_paths[root_index],root->root_path);
  for(uint32_t j=0;j<root->count;j++){
   if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}const CohWrTexNamespaceFile*file=root->files+j;Record*x=r->records+r->record_count;
   status=path(file->path,x->path);if(status!=COH_OK)goto fail;x->source=file->bytes;x->timestamp=file->timestamp;x->directory=file->is_directory;x->location=(int32_t)(q->root_count-1-root_index);x->file_index=-1;x->root=root_index;
   if(!x->directory){status=coh_asset_mount_file(r->loader,x->path,x->source);if(status!=COH_OK)goto fail;}r->record_count++;
  }
 }
 for(uint32_t i=0;i<q->pigg_count;i++){status=collect_pig(r,q->piggs[i],i,cancel);if(status!=COH_OK)goto fail;}
 status=predecessor(r,q->predecessor);if(status!=COH_OK)goto fail;
 status=prepare_tree(r,cancel);if(status!=COH_OK)goto fail;status=merge(r,cancel);if(status!=COH_OK)goto fail;
 uint32_t possible=q->predecessor?q->predecessor->basic_count:0;
 for(uint32_t i=1;i<r->node_count;i++){Node*n=r->nodes+i;size_t size=strlen(n->name);if(!n->directory&&size>=8&&!compare(n->name+size-8,".texture")){if(possible==b->basic_limit){status=COH_LIMIT;goto fail;}possible++;}}
 r->basic_capacity=possible?possible:1;r->basic_hash_count=capacity(r->basic_capacity);r->basics=take(r,(size_t)r->basic_capacity*sizeof(Basic));r->basic_hash=take(r,(size_t)r->basic_hash_count*sizeof(uint32_t));if(!r->basics||!r->basic_hash){status=COH_LIMIT;goto fail;}
 if(q->predecessor){
  const CohWrTexNamespace*old=q->predecessor;r->basic_count=old->basic_count;memcpy(r->basics,old->basics,(size_t)old->basic_count*sizeof(Basic));
  for(uint32_t i=0;i<r->basic_count;i++){uint32_t*slot=basic_slot(r,r->basics[i].key);if(!*slot){*slot=i+1;r->report.first_keys++;}else r->report.duplicates_retained++;}
 }
 uint32_t start=find_node(r,"texture_library");if(start!=NONE&&r->nodes[start].first!=NONE){char scan_path[NS_PATH]="texture_library/";status=scan_node(r,r->nodes[start].first,scan_path,16,cancel);if(status!=COH_OK)goto fail;}
 if(cancelled(cancel)){status=COH_CANCELLED;goto fail;}
 r->report.roots=q->root_count;r->report.piggs=q->pigg_count;r->report.source_records=r->record_count;r->report.tree_nodes=r->node_count-1;r->report.basic_rows=r->basic_count;r->report.source_input_generation=q->input_generation;r->report.unresolved_client_semantics=1;
 r->report.aggregate_reserved_bytes=b->external_bytes+NS_PREPARATION+b->loader.total_bytes+borrowed+r->report.peak_owned_bytes;
 r->policy.roots=NULL;r->policy.piggs=NULL;r->policy.ignore_prefixes=NULL;r->policy.predecessor=NULL;r->policy.exclusion_folder=NULL;if(previous)previous->busy=0;*out=r;return COH_OK;
fail:
 dispose(r);if(previous)previous->busy=0;return status;
}
CohStatus coh_wr_tex_namespace_destroy(CohWrTexNamespace**p){
 if(!p||!*p)return COH_OK;
 CohWrTexNamespace*r=*p;if(r->busy)return COH_STATE;
 if(!output_ok(r,p,sizeof(*p)))return COH_INVALID;
 for(uint32_t i=0;i<r->limits.body_lease_limit;i++)if(r->bodies[i].blob)return COH_STATE;
 r->busy=1;CohStatus status=coh_asset_destroy(&r->loader);if(status!=COH_OK){r->busy=0;return status;}dispose(r);*p=NULL;return COH_OK;
}
CohStatus coh_wr_tex_namespace_report(const CohWrTexNamespace*r,CohWrTexNamespaceReport*out){if(!r||!out)return COH_INVALID;
 if(r->busy)return COH_STATE;
 if(!output_ok(r,out,sizeof(*out)))return COH_INVALID;
 *out=r->report;return COH_OK;}
CohStatus coh_wr_tex_namespace_basic(const CohWrTexNamespace*r,uint32_t row,CohWrTexNamespaceBasic*out){
 if(!r||!out)return COH_INVALID;
 if(r->busy)return COH_STATE;
 if(!output_ok(r,out,sizeof(*out)))return COH_INVALID;
 if(row>=r->basic_count)return COH_NOT_FOUND;
 const Basic*b=r->basics+row;const Record*x=r->records+b->record;CohWrTexNamespaceBasic value;memset(&value,0,sizeof(value));value.asset=(CohAssetId){x->path,x->source.generation};memcpy(value.sha256,b->hash,32);value.row=row;value.first_owner_row=b->first;value.virtual_location=x->location;value.timestamp=x->timestamp;value.file_index=x->file_index;value.original_name=b->original;value.directory=b->directory;value.basic_key=b->key;value.cached_mips=(CohBytes){b->mips,b->mip_bytes};value.width=b->width;value.height=b->height;value.cached_flags=b->flags;value.initial_basic_flags=b->basic_flags;value.file_offset=b->offset;value.file_bytes=b->bytes;memcpy(value.cached_fade,b->fade,sizeof(value.cached_fade));value.cached_alpha=b->alpha;*out=value;return COH_OK;
}
CohStatus coh_wr_tex_namespace_find(const CohWrTexNamespace*r,const char*key,CohWrTexNamespaceBasic*out){
 if(!r||!out)return COH_INVALID;
 if(r->busy)return COH_STATE;
 if(!output_ok(r,out,sizeof(*out)))return COH_INVALID;
 size_t size;CohStatus status=text(key,127,&size);if(status!=COH_OK)return status;if(!disjoint(key,size+1,out,sizeof(*out)))return COH_INVALID;
 uint32_t pos=hash(key,2166136261u)&(r->basic_hash_count-1);while(r->basic_hash[pos]){uint32_t row=r->basic_hash[pos]-1;if(!compare(r->basics[row].key,key))return coh_wr_tex_namespace_basic(r,row,out);pos=(pos+1)&(r->basic_hash_count-1);}return COH_NOT_FOUND;
}
CohStatus coh_wr_tex_namespace_acquire(CohWrTexNamespace*r,uint32_t row,CohCancel cancel,const CohWrTexNamespaceBody**out){
 if(!r||!out)return COH_INVALID;
 if(r->busy)return COH_STATE;
 if(!output_ok(r,out,sizeof(*out)))return COH_INVALID;
 if(*out)return COH_STATE;
 if(row>=r->basic_count)return COH_NOT_FOUND;
 uint32_t slot=0;while(slot<r->limits.body_lease_limit&&r->bodies[slot].blob)slot++;if(slot==r->limits.body_lease_limit)return COH_LIMIT;
 r->busy=1;const Basic*b=r->basics+row;const Record*x=r->records+b->record;const CohAssetBlob*blob=NULL;CohStatus status=coh_asset_acquire(r->loader,(CohAssetId){x->path,x->source.generation},cancel,&blob);if(status!=COH_OK){r->busy=0;return status;}
 uint8_t digest[32];status=r->policy.digest(r->policy.digest_context,coh_asset_bytes(blob),digest);if(status==COH_OK&&memcmp(digest,b->hash,32))status=COH_INVALID;
 if(status==COH_OK&&cancelled(cancel))status=COH_CANCELLED;
 if(status!=COH_OK){coh_asset_release(r->loader,blob);r->busy=0;return status;}
 r->bodies[slot].owner=r;r->bodies[slot].blob=blob;*out=r->bodies+slot;r->busy=0;return COH_OK;
}
CohStatus coh_wr_tex_namespace_body(const CohWrTexNamespaceBody*body,CohBytes*out){if(!body||!body->blob||!body->owner||!out)return COH_INVALID;if(body->owner->busy)return COH_STATE;if(!output_ok(body->owner,out,sizeof(*out)))return COH_INVALID;*out=coh_asset_bytes(body->blob);return COH_OK;}
CohStatus coh_wr_tex_namespace_release(CohWrTexNamespace*r,const CohWrTexNamespaceBody**p){
 if(!r||!p)return COH_INVALID;
 if(r->busy)return COH_STATE;
 if(!output_ok(r,p,sizeof(*p)))return COH_INVALID;
 if(!*p)return COH_OK;
 for(uint32_t i=0;i<r->limits.body_lease_limit;i++)if(*p==r->bodies+i&&r->bodies[i].blob){coh_asset_release(r->loader,r->bodies[i].blob);r->bodies[i].blob=NULL;r->bodies[i].owner=NULL;*p=NULL;return COH_OK;}
 return COH_INVALID;
}
