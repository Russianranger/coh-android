
#include "file-list-compare-provider.h"
#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef int32_t __time32_t;
#define MAX_PATH 260
typedef char host32[(sizeof(int)==4&&sizeof(__time32_t)==4)?1:-1];

#include <stdarg.h>
#define false 0
#define true 1
typedef struct FileEntry {
    char path[MAX_PATH];
    __time32_t date;
    int seen;            // just used for compare ops
} FileEntry;
typedef FileEntry** FileList;

typedef struct{uint32_t allocated,count;FileEntry nodes[FLC_NODE_MAX];FileEntry*pointers[FLC_NODE_MAX];FileEntry snapshot_nodes[FLC_NODE_MAX];FileEntry*snapshot_pointers[FLC_NODE_MAX];}OwnedList;
typedef struct{int active,comparing;uint32_t selected,last_index,last_found;FileCompareRequest request;OwnedList lists[2];FileCompareReceipt receipt;uint32_t diagnostic,diagnostic_index;}FileCompareOwner;
static FileCompareOwner owner;
static void wipe(void*p,size_t n){volatile unsigned char*b=p;while(n--)*b++=0;}
static int zero(const void*p,size_t n){const unsigned char*b=p;for(size_t i=0;i<n;i++)if(b[i])return 0;return 1;}
int filecompare_is_idle(void){return zero(&owner,sizeof(owner));}
size_t filecompare_owned_bytes(void){return sizeof(owner);}
static unsigned lower(unsigned c){return c>='A'&&c<='Z'?c+('a'-'A'):c;}
static int ascii_ncompare(const char*a,const char*b,size_t n){for(size_t i=0;i<n;i++){unsigned x=lower((unsigned char)a[i]),y=lower((unsigned char)b[i]);if(x!=y)return x<y?-1:1;if(!x)return 0;}return 0;}
static int ascii_compare(const char*a,const char*b){for(;;a++,b++){unsigned x=lower((unsigned char)*a),y=lower((unsigned char)*b);if(x!=y)return x<y?-1:1;if(!x)return 0;}}
#define stricmp ascii_compare
#define strnicmp ascii_ncompare
/* Explicit accepted shell: implementation absent from pinned snapshot. */
static char*forwardSlashes(char*path){assert(owner.active);owner.receipt.normalization_calls++;for(char*p=path;*p;p++)if(*p=='\\')*p='/';return path;}
static char*fileDataDir(void){assert(owner.active&&!owner.comparing&&owner.selected<2);owner.receipt.directory_calls++;return owner.request.lists[owner.selected].directory;}
static __time32_t fileLastChanged(const char*path){(void)path;assert(!"filesystem timestamp branch excluded");return 0;}
static OwnedList*owned_list(FileList*list){assert(owner.active&&list);for(unsigned i=0;i<2;i++)if(*list==owner.lists[i].pointers)return &owner.lists[i];assert(!"foreign or borrowed list");return NULL;}
static void owned_create(FileList*list){assert(owner.active&&!owner.comparing&&owner.selected<2&&list&&!*list);OwnedList*l=&owner.lists[owner.selected];assert(!l->count);*list=l->pointers;owner.receipt.create_calls++;}
static int owned_size(FileList*list){OwnedList*l=owned_list(list);owner.receipt.size_calls++;return(int)l->count;}
static void*owned_calloc(size_t n,size_t width){assert(owner.active&&!owner.comparing&&n==sizeof(FileEntry)&&width==1);OwnedList*l=&owner.lists[owner.selected];assert(l->allocated<owner.request.lists[owner.selected].count&&l->allocated<FLC_NODE_MAX);owner.receipt.allocation_calls++;return &l->nodes[l->allocated++];}
static void owned_insert(FileList*list,FileEntry*node,int index){OwnedList*l=owned_list(list);assert(!owner.comparing&&l==&owner.lists[owner.selected]&&l->count<FLC_NODE_MAX&&index>=0&&(unsigned)index<=l->count&&node==&l->nodes[l->allocated-1]);for(uint32_t i=l->count;i>(unsigned)index;i--)l->pointers[i]=l->pointers[i-1];l->pointers[index]=node;l->count++;owner.receipt.earray_insert_calls++;}
static void verbose_printf(const char*format,...){
 assert(owner.active&&owner.comparing&&!owner.receipt.diagnostic_calls);
 unsigned kind=!strcmp(format,"%s in bin file no longer exists on disk\n")?1u:!strcmp(format,"%s in bin file has different date than one on disk\n")?2u:0u;assert(kind);
 va_list args;va_start(args,format);char*path=va_arg(args,char*);va_end(args);
 unsigned i=0;while(i<owner.lists[0].count&&path!=owner.lists[0].pointers[i]->path)i++;assert(i<owner.lists[0].count);
 owner.diagnostic=kind;owner.diagnostic_index=i;owner.receipt.diagnostic_calls++;
}
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

static int observed_search(FileList*list,char*path,int*found){owner.receipt.search_calls++;int index=FileListSearch(list,path,found);assert(index>=0&&(unsigned)index<=owned_list(list)->count);owner.last_index=(uint32_t)index;owner.last_found=(uint32_t)*found;return index;}
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

/* Verify that the exact original reader returns an owned disk node or NULL. */
static FileEntry*observed_find(FileList*list,char*path){
 assert(owner.comparing&&owned_list(list)==&owner.lists[1]);owner.receipt.find_calls++;
 FileEntry*answer=FileListFind(list,path);
 if(answer){unsigned i=0;while(i<owner.lists[1].count&&answer!=owner.lists[1].pointers[i])i++;assert(i<owner.lists[1].count&&owner.last_found&&owner.last_index==i);}
 else assert(!owner.last_found);
 owner.receipt.selected_reader_results_checked++;return answer;
}
#define FileListFind observed_find
int FileListIsBinUpToDate(FileList* binlist, FileList *disklist)
{
    int bin_len, disk_len;
    FileEntry *bin_file, *disk_file;
    int i;

    bin_len = eaSize(binlist);
    disk_len = eaSize(disklist);

    if (bin_len != disk_len)
        return false;

    for (i = 0; i < bin_len; i++)
    {
        bin_file = (*binlist)[i];
        disk_file = FileListFind(disklist, bin_file->path);
        if (!disk_file)
        {
            verbose_printf("%s in bin file no longer exists on disk\n", bin_file->path);
            return false;
        }
        if (bin_file->date != disk_file->date)
        {
            verbose_printf("%s in bin file has different date than one on disk\n", bin_file->path);
            return false;
        }
    }

    return true;
}

#undef FileListFind
#undef FileListSearch
#undef eaCreate
#undef eaSize
#undef eaInsert
#undef calloc
typedef struct{const void*p;size_t n;}Span;
static int valid(Span s){return s.p?(uintptr_t)s.p<=UINTPTR_MAX-s.n:!s.n;}
static int apart(Span a,Span b){return !a.n||!b.n||(uintptr_t)a.p+a.n<=(uintptr_t)b.p||(uintptr_t)b.p+b.n<=(uintptr_t)a.p;}
static int ascii_path(const char*p,size_t n,size_t cap){if(n>=cap||p[n])return 0;for(size_t i=0;i<n;i++)if(!p[i]||(unsigned char)p[i]>127)return 0;return 1;}
CohStatus filecompare_apply(const FileCompareRequest*request,const FileCompareIdentity*observed,const FileCompareIdentity*expected,const CohCostumeImportDigest*digest,FileCompareResult*out,FileCompareReceipt*receipt,size_t budget,size_t retained){
 if(!request||!observed||!expected||!digest||!out||!receipt)return COH_INVALID;
 Span spans[7]={{request,sizeof(*request)},{observed,sizeof(*observed)},{expected,sizeof(*expected)},{digest,sizeof(*digest)},{out,sizeof(*out)},{receipt,sizeof(*receipt)},{NULL,0}};
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(!apart(spans[i],spans[j]))return COH_INVALID;}
 spans[6]=(Span){digest->context,digest->context_bytes};if(!valid(spans[6]))return COH_INVALID;for(unsigned i=0;i<6;i++)if(!apart(spans[6],spans[i]))return COH_INVALID;
 FileCompareReceipt r;memset(&r,0,sizeof(r));r.stage=FLC_INPUT;r.cleanup_complete=(uint32_t)filecompare_is_idle();CohStatus status=COH_OK;uint32_t inserts=0;
 if(!r.cleanup_complete)status=COH_STATE;else if(!budget||budget>FLC_BUDGET_MAX)status=COH_LIMIT;else if(!digest->sha256)status=COH_STATE;
 size_t charge=sizeof(owner)+FLC_STACK_RESERVE;
 if(status==COH_OK)for(unsigned i=0;i<7;i++){if(spans[i].n>budget||charge>budget-spans[i].n){status=COH_LIMIT;break;}charge+=spans[i].n;}
 if(status==COH_OK){if(digest->scratch_reserve>budget||charge>budget-digest->scratch_reserve)status=COH_LIMIT;else charge+=digest->scratch_reserve;}
 if(status==COH_OK&&(retained>budget||charge>budget-retained))status=COH_LIMIT;
 if(status!=COH_OK)goto refused;
 r.stage=FLC_IDENTITY;for(unsigned i=0;i<5;i++)if(zero((const unsigned char*)expected+i*32u,32))status=COH_STATE;
 if(memcmp(observed,expected,sizeof(*expected)))status=COH_STATE;
 if(status!=COH_OK)goto refused;
 r.identity_matched=1;
 for(uint32_t side=0;side<2;side++){
  const FileCompareList*l=&request->lists[side];r.failed_list=side;r.failed_entry=0;r.stage=FLC_PROFILE;if(l->count>FLC_NODE_MAX){status=COH_LIMIT;goto refused;}
  r.stage=FLC_PATH;if(!ascii_path(l->directory,l->directory_length,FLC_PATH_MAX)){status=COH_INVALID;goto refused;}
  for(uint32_t i=0;i<l->count;i++){
   const FileCompareEntry*entry=&l->entries[i];r.failed_entry=i;r.stage=FLC_PATH;
   if(!ascii_path(entry->path,entry->length,FLC_RAW_MAX)){status=COH_INVALID;goto refused;}
   size_t skip=0;if(!ascii_ncompare(entry->path,l->directory,l->directory_length)){skip=l->directory_length;if(entry->path[skip]=='/'||entry->path[skip]=='\\')skip++;}
   if(entry->length-skip>=FLC_PATH_MAX){status=COH_LIMIT;goto refused;}
   r.stage=FLC_DATE;if(!entry->date_bits){status=COH_UNSUPPORTED;goto refused;}inserts++;
  }
 }
 r.stage=FLC_PROFILE;if(request->reserve_fault>inserts+2u){status=COH_UNSUPPORTED;goto refused;}
 r.stage=FLC_DIGEST;uint8_t sum[32];memset(sum,0,sizeof(sum));status=digest->sha256(digest->context,(CohBytes){(const uint8_t*)request,sizeof(*request)},sum);if(status==COH_OK&&memcmp(sum,expected->input_sha256,32))status=COH_STATE;wipe(sum,sizeof(sum));if(status!=COH_OK)goto refused;
 r.stage=FLC_RESERVE;for(uint32_t i=1;i<=inserts+2;i++){r.reservation_calls++;if(request->reserve_fault==i){status=COH_LIMIT;goto refused;}}r.reserved_nodes=inserts;
 owner.active=1;owner.request=*request;owner.receipt=r;owner.receipt.cleanup_complete=0;owner.diagnostic_index=UINT32_MAX;FileList lists[2]={NULL,NULL};
 for(uint32_t side=0;side<2;side++){
  owner.selected=side;FileListCreate(&lists[side]);
  for(uint32_t i=0;i<owner.request.lists[side].count;i++){FileCompareEntry*entry=&owner.request.lists[side].entries[i];__time32_t date;memcpy(&date,&entry->date_bits,4);owner.receipt.insert_calls++;FileListInsert(&lists[side],entry->path,date);}
  memcpy(owner.lists[side].snapshot_nodes,owner.lists[side].nodes,sizeof(owner.lists[side].nodes));memcpy(owner.lists[side].snapshot_pointers,owner.lists[side].pointers,sizeof(owner.lists[side].pointers));
 }
 assert(lists[0]!=lists[1]);owner.receipt.compare_calls++;owner.comparing=1;
 int equal=FileListIsBinUpToDate(&lists[0],&lists[1]);
 owner.comparing=0;assert(equal==0||equal==1);FileCompareResult candidate;memset(&candidate,0,sizeof(candidate));candidate.equal=(uint32_t)equal;candidate.bin_count=owner.lists[0].count;candidate.disk_count=owner.lists[1].count;candidate.diagnostic=owner.diagnostic;candidate.diagnostic_index=owner.diagnostic_index;
 for(uint32_t side=0;side<2;side++){
  OwnedList*l=&owner.lists[side];assert(lists[side]==l->pointers&&!memcmp(l->nodes,l->snapshot_nodes,sizeof(l->nodes))&&!memcmp(l->pointers,l->snapshot_pointers,sizeof(l->pointers)));
  for(uint32_t i=0;i<l->count;i++){FileEntry*node=l->pointers[i];uintptr_t at=(uintptr_t)node,start=(uintptr_t)l->nodes;assert(at>=start&&at-start<sizeof(l->nodes)&&(at-start)%sizeof(FileEntry)==0);memcpy(candidate.entries[side][i].path,node->path,MAX_PATH);memcpy(&candidate.entries[side][i].date_bits,&node->date,4);}
 }
 owner.receipt.lists_unchanged=1;owner.receipt.node_count=owner.lists[0].count+owner.lists[1].count;owner.receipt.stage=FLC_COMPLETE;owner.receipt.failed_list=owner.receipt.failed_entry=0;owner.receipt.status=COH_OK;r=owner.receipt;lists[0]=lists[1]=NULL;wipe(&owner,sizeof(owner));r.cleanup_complete=(uint32_t)filecompare_is_idle();assert(r.cleanup_complete);*out=candidate;*receipt=r;wipe(&candidate,sizeof(candidate));wipe(&r,sizeof(r));return COH_OK;
refused:r.status=(uint32_t)status;*receipt=r;wipe(&r,sizeof(r));return status;
}
