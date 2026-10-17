/* Bounded host memory/earray backing; actual TokenStore string policy below is
 * original, including NULL indirect-empty vs PRESENT array-empty distinction. */
typedef void*(*CustomMemoryAllocator)(void*,size_t);
typedef const void*const* cccEArrayHandle;
#define TOK_STORAGE_INDIRECT_FIXEDARRAY 16
#define TOK_STORAGE_INDIRECT_EARRAY 32
#define TS_REQUIRE(mask) assert(TokenStoreGetStorageType(tpi[column].type)&(mask))
#define parser_relpath "authenticated-costume-bin"
static int g_parseerr;
static size_t memory_live,memory_peak;static unsigned allocation_count,total_allocations;
static void*allocations[1000000];static size_t allocation_sizes[1000000];
static void*alloc(size_t n){assert(allocation_count<1000000&&n<=128u*1024u*1024u&&memory_live<=128u*1024u*1024u-n);void*p=calloc(1,n?n:1);assert(p);allocations[allocation_count]=p;allocation_sizes[allocation_count++]=n;memory_live+=n;if(memory_live>memory_peak)memory_peak=memory_live;total_allocations++;return p;}
static void reset(void){while(allocation_count){allocation_count--;if(allocations[allocation_count]){free(allocations[allocation_count]);memory_live-=allocation_sizes[allocation_count];}}assert(!memory_live);memory_peak=0;total_allocations=0;}
static void StructFreeString(void*p){for(unsigned i=0;i<allocation_count;i++)if(allocations[i]==p){free(p);allocations[i]=NULL;memory_live-=allocation_sizes[i];return;}assert(0);}
static void*StructAllocRawDbg(size_t n,const char*a,int line){(void)a;(void)line;return alloc(n);}
static char*StructAllocStringLenDbg(const char*s,int n,const char*a,int line){(void)n;(void)a;(void)line;size_t z=strlen(s);char*d=alloc(z+1);memcpy(d,s,z+1);return d;}
static const char*allocAddString(const char*s){return StructAllocStringLenDbg(s,-1,NULL,0);}
#define strcpy_s(d,n,s) (assert(strlen(s)<(size_t)(n)),strcpy(d,s))
#define Errorf(...) (assert(0),(void)0)
int TokenStoreGetStorageType(StructTypeField);
const char*TokenStoreGetStringConst(ParseTable*,int,const void*,int);
char*TokenStoreGetString(ParseTable*,int,void*,int);
char*TokenStoreSetString(ParseTable*,int,void*,int,const char*,CustomMemoryAllocator,void*);
void TokenStoreSetCapacity(ParseTable*,int,void*,int);
void*TokenStoreAlloc(ParseTable*,int,void*,int,U32,CustomMemoryAllocator,void*);
void*TokenStoreGetPointer(ParseTable*,int,void*,int);
const void*TokenStoreGetPointerConst(ParseTable*,int,const void*,int);
int TokenStoreGetNumElems(ParseTable*,int,const void*);
typedef struct{size_t capacity,count;void*items[];}HostArray;
static HostArray*coh_host_array(const void*p){return (HostArray*)((char*)p-sizeof(HostArray));}
#define eaSize(h) (*(h)?(int)coh_host_array(*(h))->count:0)
#define eaSizeUnsafe(h) eaSize(h)
static size_t eaMemUsage(const void*p){void*const*const*h=p;return *h?sizeof(HostArray)+coh_host_array(*h)->capacity*sizeof(void*):0;}
static void eaCreateWithCapacity(void***h,int n){assert(!*h&&n>0&&n<=65536);HostArray*a=alloc(sizeof(*a)+(size_t)n*sizeof(void*));a->capacity=n;*h=a->items;}
static void eaSetCapacity(void***h,int n){assert(!*h);eaCreateWithCapacity(h,n);}
static int eaPush(void***h,void*p){assert(*h);HostArray*a=coh_host_array(*h);assert(a->count<a->capacity);a->items[a->count]=p;return (int)a->count++;}
static void eaSet(void***h,void*p,int i){assert(i>=0&&(size_t)i<coh_host_array(*h)->count);(*h)[i]=p;}
static int ea32Size(const void*p){(void)p;assert(0);return 0;}
static void*field(ParseTable*t,int c,const void*p){return (char*)p+t[c].storeoffset;}
static void TokenStoreSetInt(ParseTable*t,int c,void*p,int i,int v){((int*)field(t,c,p))[i]=v;}
static int TokenStoreGetInt(ParseTable*t,int c,const void*p,int i){return ((int*)field(t,c,p))[i];}
static void TokenStoreSetU8(ParseTable*t,int c,void*p,int i,U8 v){((U8*)field(t,c,p))[i]=v;}
static int TokenStoreGetU8(ParseTable*t,int c,const void*p,int i){return ((U8*)field(t,c,p))[i];}
static void TokenStoreSetF32(ParseTable*t,int c,void*p,int i,F32 v){((F32*)field(t,c,p))[i]=v;}
static F32 TokenStoreGetF32(ParseTable*t,int c,const void*p,int i){return ((F32*)field(t,c,p))[i];}
