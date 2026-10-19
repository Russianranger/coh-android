
#include "file-list-ops-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef int32_t __time32_t;
#define MAX_PATH 260
typedef char host32[(sizeof(int)==4&&sizeof(__time32_t)==4)?1:-1];
typedef struct FileEntry {
    char path[MAX_PATH];
    __time32_t date;
    int seen;            // just used for compare ops
} FileEntry;
typedef FileEntry** FileList;

typedef struct{int active;uint32_t allocated,count,last_index,last_found;FileOpsRequest request;FileEntry nodes[FLO_NODE_MAX];FileEntry*pointers[FLO_NODE_MAX];FileOpsReceipt receipt;}FileOpsOwner;
static FileOpsOwner owner;
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static int zero(const void*p,size_t n){const unsigned char*b=p;for(size_t i=0;i<n;i++)if(b[i])return 0;return 1;}
int fileops_is_idle(void){return zero(&owner,sizeof(owner));}
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
static void owned_create(FileList*list){assert(owner.active&&list&&!*list&&!owner.count);*list=owner.pointers;owner.receipt.create_calls++;}
static int owned_size(FileList*list){assert(owner.active&&list&&*list==owner.pointers);return(int)owner.count;}
static void*owned_calloc(size_t n,size_t width){assert(owner.active&&n==sizeof(FileEntry)&&width==1&&owner.allocated<owner.receipt.reserved_nodes&&owner.allocated<FLO_NODE_MAX);owner.receipt.allocation_calls++;return &owner.nodes[owner.allocated++];}
static void owned_insert(FileList*list,FileEntry*node,int index){assert(owner.active&&list&&*list==owner.pointers&&owner.count<FLO_NODE_MAX&&index>=0&&(unsigned)index<=owner.count&&node==&owner.nodes[owner.allocated-1]);for(uint32_t i=owner.count;i>(unsigned)index;i--)owner.pointers[i]=owner.pointers[i-1];owner.pointers[index]=node;owner.count++;owner.receipt.earray_insert_calls++;}
#define eaCreate owned_create
#define eaSize owned_size
#define eaInsert owned_insert
#define calloc owned_calloc
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

#undef FileListSearch
#undef eaCreate
#undef eaSize
#undef eaInsert
#undef calloc
typedef struct{const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int ascii_path(const char*p,size_t n,size_t cap){if(n>=cap||p[n])return 0;for(size_t i=0;i<n;i++)if(!p[i]||(unsigned char)p[i]>127)return 0;return 1;}
CohStatus fileops_apply(const FileOpsRequest*request,const FileOpsIdentity*observed,const FileOpsIdentity*expected,const CohCostumeImportDigest*digest,FileOpsResult*out,FileOpsReceipt*receipt,size_t budget,size_t retained){
 if(!request||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 Span spans[7]={{request,sizeof(*request)},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(Span){digest->context,digest->context_bytes};if(!valid(spans[6]))return COH_INVALID;for(unsigned i=0;i<6;i++)if(!apart(spans[6],spans[i]))return COH_INVALID;
 FileOpsReceipt r;memset(&r,0,sizeof(r));r.stage=FLO_INPUT;r.cleanup_complete=(uint32_t)fileops_is_idle();CohStatus status=COH_OK;uint32_t inserts=0;
 if(!r.cleanup_complete)status=COH_STATE;else if(!budget||budget>FLO_BUDGET_MAX)status=COH_LIMIT;else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+FLO_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK)goto refused;
 r.stage=FLO_IDENTITY;for(unsigned i=0;i<5;i++)if(zero((const unsigned char*)expected+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK)goto refused;
 r.identity_matched=1;
 r.stage=FLO_PROFILE;if(request->count>FLO_OP_MAX){status=COH_LIMIT;goto refused;}
 r.stage=FLO_PATH;if(!ascii_path(request->directory,request->directory_length,FLO_PATH_MAX)){status=COH_INVALID;goto refused;}
 for(uint32_t i=0;i<request->count;i++){
  const FileOpsOperation*op=&request->operations[i];r.failed_operation=i;r.stage=FLO_PROFILE;
  if(op->kind<FLO_INSERT||op->kind>FLO_SEARCH){status=COH_UNSUPPORTED;goto refused;}
  r.stage=FLO_PATH;if(!ascii_path(op->path,op->length,FLO_RAW_MAX)){status=COH_INVALID;goto refused;}
  size_t skip=0;if(op->kind==FLO_INSERT&&!ascii_ncompare(op->path,request->directory,request->directory_length)){skip=request->directory_length;if(op->path[skip]=='/'||op->path[skip]=='\\')skip++;}
  if(op->length-skip>=FLO_PATH_MAX){status=COH_LIMIT;goto refused;}
  if(op->kind==FLO_INSERT){r.stage=FLO_DATE;if(!op->date_bits){status=COH_UNSUPPORTED;goto refused;}if(++inserts>FLO_NODE_MAX){status=COH_LIMIT;goto refused;}}
 }
 r.stage=FLO_PROFILE;if(request->reserve_fault>inserts+1u){status=COH_UNSUPPORTED;goto refused;}
 r.stage=FLO_DIGEST;uint8_t sum[32];memset(sum,0,sizeof(sum));status=digest->sha256(digest->context,(CohBytes){(const uint8_t*)request,sizeof(*request)},sum);if(status==COH_OK&&memcmp(sum,expected->input_sha256,32))status=COH_STATE;wipe(sum,sizeof(sum));if(status!=COH_OK)goto refused;
 r.stage=FLO_RESERVE;for(uint32_t i=1;i<=inserts+1;i++){r.reservation_calls++;if(request->reserve_fault==i){status=COH_LIMIT;goto refused;}}r.reserved_nodes=inserts;
 owner.active=1;owner.request=*request;owner.receipt=r;owner.receipt.cleanup_complete=0;FileList list=NULL;FileListCreate(&list);FileOpsResult candidate;memset(&candidate,0,sizeof(candidate));
 for(uint32_t i=0;i<request->count;i++){
  FileOpsOperation*op=&owner.request.operations[i];FileOpsOperationResult*answer=&candidate.operations[i];FileEntry*found=NULL;answer->index=UINT32_MAX;
  if(op->kind==FLO_INSERT){__time32_t date;memcpy(&date,&op->date_bits,4);uint32_t before=owner.count;owner.receipt.insert_calls++;FileListInsert(&list,op->path,date);answer->found=owner.last_found;answer->index=owner.last_index;answer->inserted=owner.count-before;found=list[answer->index];}
  else if(op->kind==FLO_FIND){owner.receipt.find_calls++;found=FileListFind(&list,op->path);answer->found=(uint32_t)(found!=NULL);if(found)for(uint32_t j=0;j<owner.count;j++)if(list[j]==found)answer->index=j;}
  else{int present;answer->index=(uint32_t)observed_search(&list,op->path,&present);answer->found=(uint32_t)present;if(present)found=list[answer->index];}
  answer->count_after=owner.count;if(found)memcpy(&answer->date_bits,&found->date,4);
 }
 candidate.count=owner.count;for(uint32_t i=0;i<owner.count;i++){assert(list[i]>=owner.nodes&&list[i]<owner.nodes+FLO_NODE_MAX);memcpy(candidate.entries[i].path,list[i]->path,MAX_PATH);memcpy(&candidate.entries[i].date_bits,&list[i]->date,4);memcpy(&candidate.entries[i].seen,&list[i]->seen,4);}
 owner.receipt.node_count=owner.count;owner.receipt.stage=FLO_COMPLETE;owner.receipt.failed_operation=0;owner.receipt.status=COH_OK;r=owner.receipt;list=NULL;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)fileops_is_idle();*out=candidate;*receipt=r;wipe(&candidate,sizeof(candidate));wipe(&r,sizeof(r));return COH_OK;
refused:r.status=(uint32_t)status;*receipt=r;wipe(&r,sizeof(r));return status;
}
