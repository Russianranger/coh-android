/* Adapter boundary: primary table constructor/insertion uses whole original
 * functions. Non-primary reward, tags, geometry, account/UI are not admitted. */
#define SERVER 1
#define CLIENT 0
#define CASE(s,ret) if(stricmp(gender,s)==0)return ret;
#define cpp_const_cast(t) (t)
#define cpp_reinterpret_cast(t) (t)
static unsigned callback_mode,callback_policy,callback_sku_calls,callback_errors;
static const char*skuIdFromString(const char*s){assert(s);return s;}
static bool accountCatalogIsSkuPublished(const char*s){assert(s);callback_sku_calls++;return callback_policy==1||(callback_policy==3&&(callback_sku_calls&1));}
#define S32_TO_PTR(v) ((void*)(uintptr_t)(uint32_t)(v))
#define onlyfulldebugdevassert(v) assert(v)
static int isSharedMemory(const void*p){(void)p;assert(0);return 0;}
typedef StashTableImp*StashTable;typedef const StashTableImp*cStashTable;
#define Indexable 0
#define WideString 1
static void*createStringTable(void){assert(0);return NULL;}
static void initStringTable(void*p,int n){(void)p;(void)n;assert(0);}
static void strTableSetMode(void*p,int n){(void)p;(void)n;assert(0);}
static CostumeMasterList gCostumeMaster;static ColorPalette gSuperPalette;
static cStashTable costume_HashTable,costume_HashTableExtraInfo,costume_PaletteTable,costumeReward_HashTable,costume_GeoDataTable;
static StashTable costume_TaggedPartTable;
static StashTableImp ancillary[3];
static unsigned ancillary_adds[3],tag_calls,geo_calls;
static unsigned char*trace;static unsigned trace_size,trace_cap;
static void trace_word(U32 v){assert(trace_size<=trace_cap&&trace_cap-trace_size>=4);for(unsigned i=0;i<4;i++)trace[trace_size++]=(unsigned char)(v>>(8*i));}
static void trace_string(unsigned kind,const char*s){unsigned n=(unsigned)strlen(s);trace_word(kind);trace_word(n);assert(trace_size<=trace_cap&&n<=trace_cap-trace_size);memcpy(trace+trace_size,s,n);trace_size+=n;}
static void trace_integer(U32 v){trace_word(2);trace_word(v);}
static unsigned trace_mode;
static char*estrTemp(void){static char temp[16];return temp;}
static void estrDestroy(char**p){(void)p;}
static int vec3IsZero(const Vec3 v){return v[0]==0&&v[1]==0&&v[2]==0;}
static void ErrorFilenamef(const char*p,const char*f,...){(void)p;(void)f;callback_errors++;if(!callback_mode)assert(0);}
static void rewardAddCostumePartToHashTable(const char*s){assert(s);}
static int s_costume_getGloveName(char**p,const char*a,const char*b){(void)p;(void)a;(void)b;geo_calls++;return 0;}
typedef struct{const char*displayName,*bodySetName,*regionName,*pchName,*pchGeom,*pchTex1,*pchFxName,*pchTex2;}AncillaryPart;
typedef struct{int maskIdx;AncillaryPart part;}CostumeTaggedPart;
static CostumeTaggedPart*s_getTaggedPart(const char*s,BodyType body,int required){static CostumeTaggedPart dummy;assert(s&&required&&body>=0&&body<=8);tag_calls++;return &dummy;}
/* WHOLE_SOURCE_INSERTION */
static StashTable stashTableCreateWithStringKeys(unsigned size,StashTableMode mode){if(!callback_mode&&(size==20||size==50||size==1024)){unsigned n=size==20?0:size==50?1:2;memset(&ancillary[n],0,sizeof(ancillary[n]));return &ancillary[n];}assert((size==4096||size==256)&&mode==StashDefault);return stashTableCreateWithStringKeysEx(size,mode,"offline-source",0);}
static StashTable stashTableCreateInt(unsigned size){assert(size==128);return stashTableCreateIntEx(size,"offline-source",0);}
static void stashTableClearConst(cStashTable p){assert(p==&ancillary[2]);}
static bool stashAddPointer(StashTable p,const void*key,void*value,bool overwrite){if(p==costume_HashTable||p==costume_HashTableExtraInfo){assert(key&&!value&&!overwrite);if(trace_mode)trace_string(p==costume_HashTable?0:1,key);return source_stashAddPointer(p,key,value,overwrite);}if(callback_mode)return source_stashAddPointer(p,key,value,overwrite);for(unsigned i=0;i<3;i++)if(p==&ancillary[i]){ancillary_adds[i]++;return true;}assert(0);return false;}

static bool stashFindElement(StashTable p,const void*key,void*out){assert(callback_mode&&!out);StashKey k;k.pKey=(void*)key;unsigned index;return stashFindIndexByKeyInternal(p,k,getKeyLength(p,key),&index,NULL);}
static void stashTableDestroy(StashTable p){assert(callback_mode&&p);free(p->pStorage);free(p);}
