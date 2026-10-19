
#include "file-list-lifecycle-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef int32_t __time32_t;
#define MAX_PATH 260
typedef char host32[(sizeof(int)==4&&sizeof(__time32_t)==4)?1:-1];

#include <stdlib.h>
typedef uint32_t U32;
#define cpp_reinterpret_cast(type) (type)
#define _NORMAL_BLOCK 1
#define devassertmsg(condition,message) assert(condition)
typedef struct FileEntry {
    char path[MAX_PATH];
    __time32_t date;
    int seen;            // just used for compare ops
} FileEntry;
typedef FileEntry** FileList;
typedef struct EArray
{
    int count;
    int size;
    U32 flags;
    void* structptrs[1];
} EArray;
#define PRIVATE_EARRAY_HEAP    0
#define EARRAY_FLAG_CUSTOMALLOC            (1 << 0)
#define EARRAY_FLAG_SHAREDMEMORY        (1 << 1) // currently only set for FULLDEBUG
#define EARRAY_HEADER_SIZE            (offsetof(EArray,structptrs))
#define HandleFromEArray(array) ((mEArrayHandle)(((uintptr_t)array) + EARRAY_HEADER_SIZE))
#define mEACast(handle) (cpp_reinterpret_cast(mEArrayHandle*)(handle))
#define eaSize(handle)                            (EAPtrTest(handle), eaSizeUnsafe(handle))
#define eaSizeUnsafe(handle)                    (*(handle) ? EArrayFromHandle(*(handle))->count : 0) // should only be used for void***
#define eaClearEx(handle, destructor)            eaClearExDbg(mEACast(handle), destructor)
#define eaDestroyEx(handle, destructor)            eaDestroyExDbg(mEACast(handle), destructor)
#    define EArrayFromHandle(handle) ((EArray*)(((uintptr_t)handle) - EARRAY_HEADER_SIZE))
#define EAPtrTest(ptr) ((void)sizeof(char[ \
	__builtin_classify_type(**(ptr)) == 5 ? 1 : -1])
typedef void** mEArrayHandle;                                // non-const pointer to a list of pointers
typedef void (*EArrayItemDestructor)(void*);

typedef struct{int active;uint32_t allocated,count,last_index,last_found;FileLifecycleRequest request;FileEntry*nodes[FLL_NODE_MAX];FileEntry*order[FLL_NODE_MAX];EArray*storage;uint32_t storage_live;FileLifecycleReceipt receipt;}FileLifecycleOwner;
static FileLifecycleOwner owner;
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static int zero(const void*p,size_t n){const unsigned char*b=p;for(size_t i=0;i<n;i++)if(b[i])return 0;return 1;}
int filelifecycle_is_idle(void){return zero(&owner,sizeof(owner));}
size_t filelifecycle_owned_bytes(void){return sizeof(owner)+EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*)+FLL_NODE_MAX*sizeof(FileEntry);}
/* Explicit ASCII CRT shell, not original platform stricmp implementation. */
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+('a'-'A'):c;}
static int ascii_ncompare(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){unsigned x=lower((unsigned char)a[i]),y=lower((unsigned char)b[i]);if(x!=y)return x<y?-1:1;if(!x)return 0;}return 0;}
static int ascii_compare(const char*a,const char*b){for(;;a++,b++){unsigned x=lower((unsigned char)*a),y=lower((unsigned char)*b);if(x!=y)return x<y?-1:1;if(!x)return 0;}}
#define stricmp ascii_compare
#define strnicmp ascii_ncompare
/* Snapshot has forwardSlashes declaration/calls only. This explicit adapter
 * replaces backslashes only, preserving repeated separators, dots and case. */
static char*forwardSlashes(char*path){assert(owner.active);owner.receipt.normalization_calls++;for(char*p=path;*p;p++)if(*p=='\\')*p='/';return path;}
static char*fileDataDir(void){assert(owner.active);owner.receipt.directory_calls++;return owner.request.directory;}
static __time32_t fileLastChanged(const char*path){(void)path;assert(!"filesystem timestamp branch excluded");return 0;}

static void owned_create(FileList*list){assert(owner.active&&list&&!*list&&!owner.count&&owner.storage_live);*list=(FileList)HandleFromEArray(owner.storage);owner.receipt.create_calls++;}
static void*owned_calloc(size_t n,size_t width){assert(owner.active&&n==sizeof(FileEntry)&&width==1&&owner.allocated<owner.receipt.reserved_nodes&&owner.allocated<FLL_NODE_MAX);owner.receipt.allocation_calls++;return owner.nodes[owner.allocated++];}
static void owned_insert(FileList*list,FileEntry*node,int index){assert(owner.active&&list&&*list==(FileList)HandleFromEArray(owner.storage)&&owner.count<FLL_NODE_MAX&&index>=0&&(unsigned)index<=owner.count&&node==owner.nodes[owner.allocated-1]);EArray*a=EArrayFromHandle(*list);assert(a->count==(int)owner.count);for(uint32_t i=owner.count;i>(unsigned)index;i--)a->structptrs[i]=a->structptrs[i-1];a->structptrs[index]=node;a->count++;owner.count++;owner.receipt.earray_insert_calls++;}
/* Original free(NULL-destructor) call is checked against independently owned
 * reservations and source traversal order, then invokes real host free. */
static void owned_node_free(void*ptr){
 assert(owner.active&&owner.storage_live&&ptr);uint32_t at=owner.receipt.node_free_calls;assert(at<owner.allocated&&ptr==owner.order[at]);
 for(uint32_t i=0;i<at;i++)assert(owner.storage->structptrs[i]==NULL);
 uint32_t i=0;while(i<owner.allocated&&owner.nodes[i]!=ptr)i++;assert(i<owner.allocated);
 wipe(ptr,sizeof(FileEntry));free(ptr);owner.nodes[i]=NULL;owner.order[at]=NULL;owner.receipt.node_free_calls++;owner.receipt.release_order_checked++;
}
static void owned_storage_free(void*ptr,int block){
 assert(owner.active&&block==_NORMAL_BLOCK&&owner.storage_live&&ptr==owner.storage&&owner.storage->flags==0&&owner.storage->count==0&&owner.receipt.node_free_calls==owner.allocated);
 for(uint32_t i=0;i<owner.count;i++)assert(owner.storage->structptrs[i]==NULL);
 owner.receipt.slots_cleared=owner.count;wipe(ptr,EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));free(ptr);owner.storage=NULL;owner.storage_live=0;owner.receipt.storage_free_calls++;
}
static void reservation_cleanup(void){for(uint32_t i=0;i<FLL_NODE_MAX;i++)if(owner.nodes[i]){wipe(owner.nodes[i],sizeof(FileEntry));free(owner.nodes[i]);owner.nodes[i]=NULL;owner.receipt.reservation_releases++;}if(owner.storage_live){wipe(owner.storage,EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));free(owner.storage);owner.storage=NULL;owner.storage_live=0;owner.receipt.reservation_releases++;}}
#define eaCreate owned_create
#define eaInsert owned_insert
#define calloc owned_calloc
#define free owned_node_free
#define _free_dbg owned_storage_free
void eaClearExDbg(mEArrayHandle* handle, EArrayItemDestructor destructor)
{
    int i;
    EArray* pArray = EArrayFromHandle(*handle);
    if(!*handle)
        return;

    for (i = 0; i < pArray->count; i++)
    {
        if (pArray->structptrs[i])
        {
            if(destructor)
                destructor(pArray->structptrs[i]);
            else
                free(pArray->structptrs[i]);    

            pArray->structptrs[i] = NULL;
        }
    }

    pArray->count = 0;
}
void eaDestroyDbg(mEArrayHandle* handle) // free list
{
    EArray* pArray = EArrayFromHandle(*handle);
    if(!*handle)
        return;
    devassertmsg(!(pArray->flags & EARRAY_FLAG_CUSTOMALLOC), "trying to perform a heap operation on a compressed EArray");
#if PRIVATE_EARRAY_HEAP
    memMonitorTrackUserMemory(EARRAY_MEMMONITOR_NAME, 1, MOT_FREE, HeapSize(g_earrayheap, heap_flags, pArray));
    HeapFree(g_earrayheap, 0, pArray);
#else
    _free_dbg(pArray, _NORMAL_BLOCK);
#endif
    *handle = NULL;
}
void eaDestroyExDbg(mEArrayHandle *handle,EArrayItemDestructor destructor)
{
    eaClearEx(handle,destructor);
    eaDestroyDbg(handle);
}
void FileListCreate(FileList* list)
{
    eaCreate(list);
}
static int FileListSearch(FileList* list, char* path, int* found)
{
    int front = 0;
    int back = eaSize(list) - 1;
    int cmp;
    *found = 0;

    if (back == -1) // no items in list
        return 0;

    // binary search to narrow front and back
    while (back - front > 1)
    {
        int mid = (front + back) / 2;
        cmp = stricmp(path, (*list)[mid]->path);
        if (cmp < 0)
            back = mid;
        else if (cmp > 0)
            front = mid;
        else
        {
            *found = 1;
            return mid;
        }
    }

    // compare to front
    cmp = stricmp(path, (*list)[front]->path);
    if (cmp < 0) // if less than front
        return 0;
    if (cmp == 0) // is front
    {
        *found = 1;
        return 0;
    }

    // compare to back
    cmp = stricmp(path, (*list)[back]->path);
    if (cmp > 0) // greater than back
        return back+1;
    if (cmp == 0) // is back
    {
        *found = 1;
        return back;
    }
    // otherwise, less than back
    return back;
}

static int observed_search(FileList*list,char*path,int*found){owner.receipt.search_calls++;int index=FileListSearch(list,path,found);assert(index>=0&&(unsigned)index<=owner.count);owner.last_index=(uint32_t)index;owner.last_found=(uint32_t)*found;return index;}
#define FileListSearch observed_search
FileEntry* FileListFind(FileList* list, char* path)
{
    char cleanpath[MAX_PATH];
    int found;
    int result;
    strcpy(cleanpath, path);
    forwardSlashes(cleanpath);
    result = FileListSearch(list, cleanpath, &found);
    if (!found)
        return NULL;
    return (*list)[result];
}
void FileListInsert(FileList* list, const char* path, __time32_t date)
{
    char *s,cleanpath[MAX_PATH];
    int index;
    int found;
    FileEntry* node;

    // look for an existing element or a good index
    s = fileDataDir();
    if (strnicmp(path,s,strlen(s))==0)
    {
        path += strlen(s);
        if (path[0] == '/' || path[0] == '\\')
            path++;
    }
    strcpy(cleanpath, path);
    forwardSlashes(cleanpath);
    index = FileListSearch(list, cleanpath, &found);
    if (found) return;

    // otherwise, create a node and insert
    node = calloc(sizeof(FileEntry), 1);
    strcpy(node->path, cleanpath);
    if (!date) date = fileLastChanged(path);
    // Date can be 0 at this point, signifying that the file doesn't exist but needs to be checked when
    //  verifying the validity of the .bin file
    node->date = date;
    eaInsert(list, node, index);
}
int FileListLength(FileList *list)
{
    return eaSize(list);
}
void FileListDestroy(FileList* list)
{
    eaDestroyEx(list, NULL);
}

#undef FileListSearch
#undef eaCreate
#undef eaInsert
#undef calloc
#undef free
#undef _free_dbg
typedef struct{const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int ascii_path(const char*p,size_t n,size_t cap){if(n>=cap||p[n])return 0;for(size_t i=0;i<n;i++)if(!p[i]||(unsigned char)p[i]>127)return 0;return 1;}
CohStatus filelifecycle_apply(const FileLifecycleRequest*request,const FileLifecycleIdentity*observed,const FileLifecycleIdentity*expected,const CohCostumeImportDigest*digest,FileLifecycleResult*out,FileLifecycleReceipt*receipt,size_t budget,size_t retained){
 if(!request||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 Span spans[7]={{request,sizeof(*request)},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(Span){digest->context,digest->context_bytes};if(!valid(spans[6]))return COH_INVALID;for(unsigned i=0;i<6;i++)if(!apart(spans[6],spans[i]))return COH_INVALID;
 FileLifecycleReceipt r;memset(&r,0,sizeof(r));r.stage=FLL_INPUT;r.cleanup_complete=(uint32_t)filelifecycle_is_idle();CohStatus status=COH_OK;uint32_t inserts=0,unique=0;
 char keys[FLL_NODE_MAX][FLL_PATH_MAX];memset(keys,0,sizeof(keys));
 if(!r.cleanup_complete)status=COH_STATE;else if(!budget||budget>FLL_BUDGET_MAX)status=COH_LIMIT;else if(!digest->sha256)status=COH_STATE;
 size_t charge=filelifecycle_owned_bytes()+FLL_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK)goto refused;
 r.stage=FLL_IDENTITY;for(unsigned i=0;i<5;i++)if(zero((const unsigned char*)expected+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK)goto refused;
 r.identity_matched=1;
 r.stage=FLL_PROFILE;if(request->count>FLL_OP_MAX){status=COH_LIMIT;goto refused;}
 r.stage=FLL_PATH;if(!ascii_path(request->directory,request->directory_length,FLL_PATH_MAX)){status=COH_INVALID;goto refused;}
 for(uint32_t i=0;i<request->count;i++){
  const FileLifecycleOperation*op=&request->operations[i];r.failed_operation=i;r.stage=FLL_PROFILE;
  if(op->kind<FLL_INSERT||op->kind>FLL_SEARCH){status=COH_UNSUPPORTED;goto refused;}
  r.stage=FLL_PATH;if(!ascii_path(op->path,op->length,FLL_RAW_MAX)){status=COH_INVALID;goto refused;}
  size_t skip=0;if(op->kind==FLL_INSERT&&!ascii_ncompare(op->path,request->directory,request->directory_length)){skip=request->directory_length;if(op->path[skip]=='/'||op->path[skip]=='\\')skip++;}
  if(op->length-skip>=FLL_PATH_MAX){status=COH_LIMIT;goto refused;}
  if(op->kind==FLL_INSERT){
   r.stage=FLL_DATE;if(!op->date_bits){status=COH_UNSUPPORTED;goto refused;}if(++inserts>FLL_NODE_MAX){status=COH_LIMIT;goto refused;}
   /* Independent bounded capacity admission only, never a replacement source
    * list: linear equality of literal-prefix/slash prepared ASCII keys. */
   char prepared[FLL_PATH_MAX];memset(prepared,0,sizeof(prepared));
   for(size_t j=skip;j<op->length;j++)prepared[j-skip]=op->path[j]=='\\'?'/':op->path[j];
   uint32_t j=0;while(j<unique&&ascii_compare(prepared,keys[j]))j++;
   if(j==unique){memcpy(keys[unique],prepared,sizeof(prepared));unique++;}
   wipe(prepared,sizeof(prepared));
  }
 }
 r.stage=FLL_PROFILE;if(request->reserve_fault>inserts+1u){status=COH_UNSUPPORTED;goto refused;}
 r.stage=FLL_CAPACITY;r.fixture_mode=request->fixture_mode;
 if(request->fixture_mode>2){status=COH_UNSUPPORTED;goto refused;}
 if((request->fixture_mode==1&&request->count)||(request->fixture_mode==2&&unique==FLL_NODE_MAX)){status=COH_LIMIT;goto refused;}
 r.stage=FLL_DIGEST;uint8_t sum[32];memset(sum,0,sizeof(sum));status=digest->sha256(digest->context,(CohBytes){(const uint8_t*)request,sizeof(*request)},sum);if(status==COH_OK&&memcmp(sum,expected->input_sha256,32))status=COH_STATE;wipe(sum,sizeof(sum));if(status!=COH_OK)goto refused;
 r.stage=FLL_RESERVE;owner.active=1;owner.request=*request;owner.receipt=r;owner.receipt.cleanup_complete=0;
 for(uint32_t i=1;i<=inserts+1;i++){
  owner.receipt.reservation_calls++;
  if(request->reserve_fault==i){status=COH_LIMIT;goto reservation_refused;}
  if(request->fixture_mode==1)continue;
  if(i==1){owner.storage=malloc(EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));if(!owner.storage){status=COH_LIMIT;goto reservation_refused;}owner.storage_live=1;memset(owner.storage,0,EARRAY_HEADER_SIZE+FLL_NODE_MAX*sizeof(void*));owner.storage->size=FLL_NODE_MAX;}
  else{owner.nodes[i-2]=malloc(sizeof(FileEntry));if(!owner.nodes[i-2]){status=COH_LIMIT;goto reservation_refused;}memset(owner.nodes[i-2],0,sizeof(FileEntry));}
 }
 owner.receipt.reserved_nodes=inserts;wipe(keys,sizeof(keys));FileList list=NULL;if(request->fixture_mode!=1)FileListCreate(&list);
 for(uint32_t i=0;i<request->count;i++){
  FileLifecycleOperation*op=&owner.request.operations[i];
  if(op->kind==FLL_INSERT){__time32_t date;memcpy(&date,&op->date_bits,4);owner.receipt.insert_calls++;FileListInsert(&list,op->path,date);}
  else if(op->kind==FLL_FIND){owner.receipt.find_calls++;(void)FileListFind(&list,op->path);}
  else{int present;(void)observed_search(&list,op->path,&present);}
 }
 assert(owner.count==unique&&owner.allocated==unique);
 FileLifecycleResult candidate;memset(&candidate,0,sizeof(candidate));
 if(request->fixture_mode==2){assert(owner.storage&&owner.count<FLL_NODE_MAX);owner.storage->structptrs[owner.count]=NULL;owner.storage->count++;owner.count++;}
 owner.receipt.length_calls++;candidate.count=(uint32_t)FileListLength(&list);assert(candidate.count==owner.count);
 for(uint32_t i=0;i<unique;i++){FileEntry*node=list[i];owner.order[i]=node;memcpy(candidate.entries[i].path,node->path,MAX_PATH);memcpy(&candidate.entries[i].date_bits,&node->date,4);}
 owner.receipt.node_count=unique;owner.receipt.destroy_calls++;FileListDestroy(&list);assert(!list&&!owner.storage_live);owner.receipt.handle_null=1;
 owner.receipt.length_calls++;assert(FileListLength(&list)==0);owner.receipt.destroy_calls++;FileListDestroy(&list);assert(!list);
 assert(owner.receipt.node_free_calls==unique&&owner.receipt.release_order_checked==unique&&owner.receipt.storage_free_calls==(request->fixture_mode!=1));
 reservation_cleanup();owner.receipt.stage=FLL_COMPLETE;owner.receipt.failed_operation=0;owner.receipt.status=COH_OK;r=owner.receipt;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)filelifecycle_is_idle();assert(r.cleanup_complete);*out=candidate;*receipt=r;wipe(&candidate,sizeof(candidate));wipe(&r,sizeof(r));return COH_OK;
reservation_refused:reservation_cleanup();r=owner.receipt;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)filelifecycle_is_idle();assert(r.cleanup_complete);
refused:wipe(keys,sizeof(keys));r.status=(uint32_t)status;*receipt=r;wipe(&r,sizeof(r));return status;
}
