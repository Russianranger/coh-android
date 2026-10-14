

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdarg.h>
#ifdef _WIN32
#include <windows.h>
#define native_stricmp _stricmp
#define COH_CLIENT_METADATA_CENSUS_PROTOTYPE 1
#else
#include <strings.h>
#define native_stricmp strcasecmp
#define MAX_PATH 260
#define COH_CLIENT_METADATA_CENSUS_PROTOTYPE 1
#define FALSE 0
#define FILE_ATTRIBUTE_READONLY 1u
#define FILE_ATTRIBUTE_HIDDEN 2u
#define FILE_ATTRIBUTE_SYSTEM 4u
#define FILE_ATTRIBUTE_DIRECTORY 16u
typedef struct { uint32_t dwLowDateTime, dwHighDateTime; } FILETIME;
typedef struct {
 uint32_t dwFileAttributes; FILETIME ftCreationTime,ftLastAccessTime,ftLastWriteTime;
 uint32_t nFileSizeHigh,nFileSizeLow,dwReserved0,dwReserved1;
 char cFileName[260],cAlternateFileName[14];
} WIN32_FIND_DATAA;
#endif
typedef uint32_t U32;
typedef int32_t S32;
#ifndef _WIN32
typedef int32_t __time32_t;
#endif
typedef struct FolderNode FolderNode;
typedef struct FolderCache FolderCache;

typedef struct FolderNode {
    // next and prev must be first because our standard link lists are used.
    FolderNode*    next;
    FolderNode*    prev;
    
    S32            virtual_location:16;    // <0 -> Piggs, >=0 -> a game data dir // larger ABS is higher virtual_location
    U32            is_dir:1;                // Is a folder/directory.
    U32            writeable:1;            // Is writeable (i.e. not read-only).
    U32            hidden:1;                // Is hidden.
    U32            system:1;                // System flag is set.
    
    U32            seen_in_fs:1;            // Used for development_dynamic hack to add all pigs and verify they're in the FS later
    U32            in_hash_table:1;        // Set when the node is added to htAllFiles.
    U32            delete_if_absent:1;        // Set when scanning for nonexistent nodes.
    int         file_index;             // index to the file in the pigfile specified by the virtual_location
    FolderNode*    contents;                // NULL if !is_dir;  linked list of all of the children nodes
    FolderNode*    contents_tail;            // NULL if !is_dir;  tail end of the linked list of children
    FolderNode*    parent;                    // NULL if root
    char*        name;                    // name, relative to parent node
    size_t        size;
    __time32_t    timestamp;
} FolderNode;


typedef void (*NodeCallback)(FolderCache *,FolderNode *);
struct FolderCache { FolderNode *root,*root_tail; NodeCallback nodeCreateCallback,nodeDeleteCallback; };
static FolderCache *folder_cache;
static int folder_cache_update_enable,fixture_gdd_count=1,fixture_pig_count;
static uint32_t fixture_thread=1;
static uint32_t GetCurrentThreadId(void) {return fixture_thread;}
static int callback_clears;
static int fixture_dynamic=1;
static int FolderCacheGetMode(void) {return fixture_dynamic?1:0;}
#define FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC 1
static int FolderCache_GetNumGDDs(FolderCache *fc) {(void)fc;return fixture_gdd_count;}
static int FolderCache_GetNumPiggs(FolderCache *fc) {(void)fc;return fixture_pig_count;}
static char *FolderCache_GetFromVirtualLocation(FolderCache *fc,int i) {(void)fc;assert(i==0);return "fixture";}
static int use_global_owner=1;
typedef enum {FOLDER_CACHE_EXCLUDE_FOLDER,FOLDER_CACHE_ONLY_FOLDER,FOLDER_CACHE_ALL_FOLDERS} FolderCacheExclusion;
static int folder_cache_debug,discard_count,update_count,count_file,count_folder;
static FolderCacheExclusion folder_cache_exclusion=FOLDER_CACHE_ALL_FOLDERS;
static char *folder_cache_exclusion_folder;
static bool ban_all_overrides;
static char *banned_overrides[]={"/scenes","/ent_types","/object_library","/geobin"};
static int banned_overrides_len[4];
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define xcase break;case
#define xdefault break;default
#define STR_COMBINE_SS(out,a,b) snprintf((out),sizeof(out),"%s%s",(a),(b))
#define STR_COMBINE_SSS(out,a,b,c) snprintf((out),sizeof(out),"%s%s%s",(a),(b),(c))
static unsigned long long stock_comparisons,sorted_comparisons,current_comparisons;
static int count_comparisons;
static int compare_names(const char *a,const char *b) {
 if(count_comparisons) ++current_comparisons;
 return native_stricmp(a,b);
}
#define stricmp compare_names
static char *allocAddString(const char *value) {
 size_t n=strlen(value)+1;char *ret=(char*)malloc(n);assert(ret);memcpy(ret,value,n);return ret;
}
static FolderNode *FolderNodeCreate(void) {FolderNode *ret=(FolderNode*)calloc(1,sizeof(*ret));assert(ret);return ret;}
static void _FileTimeToUnixTime(const FILETIME *time,__time32_t *ret,int unused) {(void)unused;*ret=(__time32_t)time->dwLowDateTime;}
static int using_dev_data=1;
static int fileIsUsingDevData(void) {return using_dev_data;}
typedef struct FixtureDirectory {char path[1024];const unsigned char *rows;unsigned int count;} FixtureDirectory;
typedef struct FixtureHandle {FixtureDirectory *directory;unsigned int index;int open;} FixtureHandle;
static FixtureDirectory fixture_dirs[16384];
static FixtureHandle fixture_handles[8];
static int directory_count,find_first_calls,find_next_calls,find_close_calls,fixture_aliases;
static unsigned long long root_constructor_order;
static unsigned long long first_stock_comparisons,first_candidate_comparisons,last_stock_comparisons,last_candidate_comparisons;
static char callback_trace[65536];
static size_t callback_used;
static int callback_calls;
#include "coh_live_directory_batch.h"

static int use_bridge=0,bridge_failed=0;
static uint32_t batch_sequence, batch_first, batch_cursor;
static unsigned char batch_data[COH_LIVE_MAX_BYTES], operation[16]={1},directory_token[16]={2};
static CohLiveBatch batch;static CohLiveCursor cursor;
static unsigned long long batches, rows_checked, max_batch;
static int current_directory=-1;
static void p32(unsigned char *p,uint32_t v) {p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
static void load_batch(FixtureHandle *h) {
 unsigned int first=h->index,n=0,nt=0,bytes;const unsigned char *at;
 memset(batch_data,0,sizeof(batch_data));memcpy(batch_data,"COHLIVE1",8);
 memcpy(batch_data+8,operation,16);memcpy(batch_data+24,directory_token,16);
 while(first+n<h->directory->count&&n<COH_LIVE_MAX_ROWS) {
  unsigned int length;at=h->directory->rows+(first+n)*328u+8;
  length=(unsigned int)strlen((const char*)at+44);
  unsigned int next=((nt+7u)&~7u)+94u+length*2u;
  if(next>8192)break;nt=next;
  p32(batch_data+64+n*328u,first+n);memcpy(batch_data+64+n*328u+8,at,320);n++;
 }
 assert(n||first==h->directory->count);bytes=64+n*328u;
 p32(batch_data+40,batch_sequence);p32(batch_data+44,first);p32(batch_data+48,n);
 p32(batch_data+52,first+n==h->directory->count);p32(batch_data+60,bytes);
 assert(cohLiveSubmit(&cursor,batch_data,bytes));batch=cursor.batch;
 batches++;rows_checked+=n;if(bytes>max_batch)max_batch=bytes;batch_cursor=0;batch_first=first;batch_sequence++;
}
static void row_for(FixtureHandle *h,WIN32_FIND_DATAA *row) {
 if(!use_bridge){memcpy(row,h->directory->rows+h->index*328u+8,320);return;}
 assert(!bridge_failed);
 if(h->index<batch_first||h->index>=batch_first+batch.count)load_batch(h);
 batch_cursor=h->index-batch_first;
 const unsigned char *projection=cohLiveTake(&cursor);assert(projection);memcpy(row,projection,320);
 assert(!memcmp(row,h->directory->rows+h->index*328u+8,320));
}
static int fwFindFirstFile(U32 *handle,const char *search,WIN32_FIND_DATAA *row) {
 int i,j;char path[1024];size_t n=strlen(search);++find_first_calls;
 assert(n>2&&!strcmp(search+n-2,"/*"));memcpy(path,search,n-2);path[n-2]=0;
 for(i=0;i<directory_count;i++)if(!strcmp(path,fixture_dirs[i].path)&&fixture_dirs[i].count) {
  for(j=0;j<8;j++)if(!fixture_handles[j].open) {
   FixtureHandle *h=&fixture_handles[j];h->directory=&fixture_dirs[i];h->index=0;h->open=1;
   *handle=(U32)(j+1);batch_sequence=0;batch_first=UINT32_MAX;memset(&batch,0,sizeof(batch));
   current_directory=i;cohLiveInit(&cursor,operation,directory_token);row_for(h,row);return 1;
  }assert(0);
 }return 0;
}
static int fwFindNextFile(U32 handle,WIN32_FIND_DATAA *row) {
 FixtureHandle *h;assert(handle>0&&handle<=8);h=&fixture_handles[handle-1];assert(h->open);++find_next_calls;
 if(++h->index>=h->directory->count)return 0;row_for(h,row);return 1;
}
static void fwFindClose(U32 handle) {assert(handle>0&&handle<=8&&fixture_handles[handle-1].open);fixture_handles[handle-1].open=0;++find_close_calls;}
static void decoder_refusals(void) {
 unsigned char bad[COH_LIVE_MAX_BYTES];CohLiveBatch out;unsigned int bytes;
 FixtureHandle h={&fixture_dirs[0],0,1};cohLiveInit(&cursor,operation,directory_token);load_batch(&h);bytes=cohLiveU32(batch_data+60);
 assert(cohLiveBatchDecode(batch_data,bytes,operation,directory_token,0,0,&out));
 #define REFUSE(expression) do {memcpy(bad,batch_data,bytes);expression;memset(&out,0xff,sizeof(out));assert(!cohLiveBatchDecode(bad,bytes,operation,directory_token,0,0,&out));assert(!out.rows&&!out.count);} while(0)
 REFUSE(bad[0]^=1);REFUSE(bad[8]^=1);REFUSE(bad[24]^=1);REFUSE(p32(bad+40,1));
 REFUSE(p32(bad+44,1));REFUSE(p32(bad+48,86));REFUSE(p32(bad+52,2));REFUSE(p32(bad+56,1));
 REFUSE(p32(bad+60,bytes+1));REFUSE(p32(bad+64,1));REFUSE(p32(bad+68,1));
 REFUSE(bad[64+8+36]=1);REFUSE(bad[64+8+44]=1);
 assert(!cohLiveBatchDecode(batch_data,bytes-1,operation,directory_token,0,0,&out));
 #undef REFUSE
 /* Fail before first returned row allows stock; after one row never restarts. */
 {CohLiveCursor early,late;unsigned char first_row[320];
  cohLiveInit(&early,operation,directory_token);bad[0]='?';
  assert(!cohLiveSubmit(&early,bad,bytes)&&early.terminal_failure&&early.fallback_allowed);
  assert(!cohLiveSubmit(&early,batch_data,bytes)&&!cohLiveTake(&early));
  cohLiveInit(&late,operation,directory_token);assert(cohLiveSubmit(&late,batch_data,bytes));
  memcpy(first_row,cohLiveTake(&late),320);memset(bad,0,bytes);
  assert(!memcmp(first_row,batch_data+72,320));
  assert(!cohLiveSubmit(&late,bad,bytes)&&late.terminal_failure&&!late.fallback_allowed);
  assert(late.rows_returned==1&&!cohLiveTake(&late));
  assert(!cohLiveSubmit(&late,batch_data,bytes)&&late.rows_returned==1);
  /* Mutating caller's transport buffer cannot alter the owned current batch. */
  cohLiveInit(&late,operation,directory_token);memcpy(bad,batch_data,bytes);
  assert(cohLiveSubmit(&late,bad,bytes));memset(bad,0,bytes);
  assert(!memcmp(cohLiveTake(&late),batch_data+72,320));
  while(cohLiveTake(&late)) {}
  assert(late.finished);assert(!cohLiveSubmit(&late,batch_data,bytes)&&late.terminal_failure&&!late.fallback_allowed);
 }
}
static char *firstSlash(char *s) {
    char *c;
    for (c=s; *c; c++) {
        if (*c=='/' || *c=='\\') return c;
    }
    return NULL;
}
FolderNode *FolderNodeAdd(FolderNode **head, FolderNode **tail, FolderNode *parent, const char *_fn, __time32_t timestamp, size_t size, int virtual_location, int file_index, int* createdOut)
{
    char *s;
    FolderNode *node = *head, *lastnode=NULL;
    FolderNode *node2, *node_ret=NULL;
    int is_folder=0;
    bool is_new=false;
    char fn_temp[MAX_PATH], *fn;
    int stricmpres;

    if(createdOut){
        *createdOut = 0;
    }

    assert(tail);

    strcpy(fn_temp, _fn);
    fn = fn_temp;

    //printf("Adding %s - %d\n", fn, timestamp);
    while (fn[0]=='/' || fn[0]=='\\') fn++;
    if (fn[0]=='.' && (fn[1]=='/' || fn[1]=='\\')) fn+=2;
    if (fn[0]==0) {
        // zero length name, we only get this when adding a folder without a file as well, the caller wants the folder's parent back
        return parent;
    }
    s = firstSlash(fn);
    if (!s) {
        is_folder=0;
    } else {
        *s=0;
        is_folder=1;
        s++;
    }
    if (tail && *tail) {
        stricmpres = stricmp(fn, (*tail)->name);
        if (stricmpres>0) {
            // This new node is supposed to be right past the tail
            lastnode = *tail;
            node = NULL;
            is_new = true;
        } else if (stricmpres==0) {
            // This node *is* the tail
            node = *tail;
            is_new = false;
            lastnode = (void*)-1; // Not valid
        }
    }
    while (node) {
        stricmpres = stricmp(fn, node->name);
        if (stricmpres==0) {
            // Found the folder or file
            if (!node->is_dir) {
                if (is_folder) { // this *is* a folder
                    if (folder_cache_debug)
                        printf("File system inconsistency:  A file in one location is named the same as a folder in another : %s\n", fn);
                    // Assume the old one was actually a folder
                    node->is_dir = 1;
                    return FolderNodeAdd(&node->contents, &node->contents_tail, node, s, timestamp, size, virtual_location, file_index, createdOut);
                } else { // They're both files, treat this as an Update command
                    break;
                }
            } else {
                if (is_folder) {
                    return FolderNodeAdd(&node->contents, &node->contents_tail, node, s, timestamp, size, virtual_location, file_index, createdOut);
                } else {
                    // We don't think this is a folder, but a folder exists under this name already, must be a folder
                    // This call will just return node->contents back down the tree for us
                    s = "";
                    return FolderNodeAdd(&node->contents, &node->contents_tail, node, s, timestamp, size, virtual_location, file_index, createdOut);
                }
            }
            assert(0);
            return NULL;
        } else if (stricmpres<0) {
            // We want to insert the new one *before* this one
            is_new=true;
            break;
        }
        lastnode = node;
        node = node->next;
    }
    if (node!=NULL && !is_new) { // We're doing an update
        bool update;
        node2 = node;
        // check timestamps and virtual location to see which one should be used
        if (is_folder) {
            // All folder nodes must link to the base GameDataDir (priority 0)
            if (virtual_location == 0) {
                update = true;
            } else {
                if (node->virtual_location==0) {
                    update = false;
                } else {
                    update = virtual_location > node->virtual_location; // Take GDDs over pigs
                }
            }
        } else if (virtual_location < 0 && node->virtual_location < 0) {
            // Both pigs
            update = virtual_location <= node->virtual_location;
        } else if (virtual_location < 0) {
            // Just the new one is a pig
            // Use the pig if it has the same timestamp // *and* this is not an "override" data dir
            update= (timestamp == node->timestamp) || (timestamp - node->timestamp)==3600; // && (node->virtual_location==0);
            node2->seen_in_fs = 1;
        } else if (node->virtual_location < 0) {
            // Just the old one is a pig
            // Use the pig if it has the same timestamp // *and* this is not an "override" data dir
            update= !((timestamp == node->timestamp) || (timestamp - node->timestamp)==3600); // && (virtual_location==0));
            node2->seen_in_fs = 1;
        } else {
            // Both are file system
            // Update if this is a higher priority one, or if it's the same, then this has to be an update call
            update = virtual_location >= node->virtual_location;
            node2->seen_in_fs = 1;
        }
        //printf("file %s: %s\n", fn, update?"overridden":"did not override");
        assert(node2->parent == parent);
        assert(!is_folder);
        if (update) {
            update_count++;
            // Update the data
            node2->timestamp = timestamp;
            node2->size = size;
            node2->virtual_location = virtual_location;
            node2->file_index = file_index;
        } else {
            discard_count++;
            return NULL;
        }
    } else {
        is_new = true;
        // Was not found in the list, it's a new node
        node2 = FolderNodeCreate();
        node2->parent = parent;
        node2->name = (char*)allocAddString(fn);
        // These three not specifically needed if it is a folder
        node2->timestamp = timestamp;
        node2->size = size;
        node2->virtual_location = virtual_location;
        node2->file_index = file_index;
        if (virtual_location >=0)
            node2->seen_in_fs = 1;
    }
    node2->is_dir = is_folder;
    node_ret = node2;
    if (is_folder) {
        node_ret = FolderNodeAdd(&node2->contents, &node2->contents_tail, node2, s, timestamp, size, virtual_location, file_index, createdOut);
    }
    if(is_new && createdOut){
        *createdOut = 1;
    }
    if (node!=NULL && !is_new) { // We are doing an update
        return node_ret;
    }
    if (lastnode) { // There was a list to begin with, add to it/insert in the middle
        FolderNode *next = lastnode->next;
        node2->prev = lastnode;
        lastnode->next = node2;
        node2->next = next;
    } else {  // node==NULL -> there was no list to begin with, or we want this to be the new first element
        node2->next = *head;
        *head = node2;
    }
    if (node2->next) {
        node2->next->prev = node2;
    }
    if (node2->next==NULL && tail) {
        // This is the new tail
        *tail = node2;
    }
    return node_ret;
}
static void stockConstructor(    FolderCache* fc,
                                        FolderNode **node,
                                        FolderNode **tail,
                                        FolderNode *parent,
                                        const char *basepath,
                                        int virtual_location)
{
    char                        buffer[1024];
    FolderNode*                    node2;
    int                            i;
    int                            strLength;
    WIN32_FIND_DATAA             wfd;
    U32                            handle;

    if (!fileIsUsingDevData()) {
        static bool banned_overrides_inited=false;
        
        if (ban_all_overrides)
            return;
        if (!banned_overrides_inited) {
            for (i=0; i<ARRAY_SIZE(banned_overrides); i++) 
                banned_overrides_len[i] = (int)strlen(banned_overrides[i]);
            banned_overrides_inited=true;
        }

        strLength = (int)strlen(basepath);
        for (i=0; i<ARRAY_SIZE(banned_overrides); i++) {
            if(banned_overrides_len[i] > strLength)
                continue;
            if(stricmp(basepath + strLength - banned_overrides_len[i], banned_overrides[i]) == 0)
                return;
        }
    }

    strcpy(buffer, basepath);
    strcat(buffer, "/*");

    if (!fwFindFirstFile(&handle, buffer, &wfd)) {
        // no files found (this is not a valid filespec/path)
        // do nothing
        return;
    }
    do {
        const char* fileName = wfd.cFileName;
        U32            fileSize;
        __time32_t        utc_time;
        int            created;
        
        if(fileName[0] == '.')
            continue;
            
        fileSize = wfd.nFileSizeLow;
        
        _FileTimeToUnixTime(&wfd.ftLastWriteTime, &utc_time, FALSE);
        
        if(wfd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY){
            // folder
            switch (folder_cache_exclusion) {
                xcase FOLDER_CACHE_EXCLUDE_FOLDER:
                    if (folder_cache_exclusion_folder && stricmp(fileName, folder_cache_exclusion_folder)==0) {
                        continue; // skip it!
                    }
                xcase FOLDER_CACHE_ONLY_FOLDER:
                    if (parent==NULL && folder_cache_exclusion_folder && stricmp(fileName, folder_cache_exclusion_folder)!=0) {
                        continue; // skip it if it doesn't match and this is in the root
                    }
                xcase FOLDER_CACHE_ALL_FOLDERS:
                    // Everything is good
                xdefault:
                    assert(false);
            }
            // add the folder
            STR_COMBINE_SS(buffer, fileName, "/");
            node2 = FolderNodeAdd(node, tail, parent, buffer, utc_time, fileSize, virtual_location, -1, &created);
            node2->is_dir = true; // in case it has no contents
            assert(node2->parent == parent);
            // Callback if created.
            if(created && fc->nodeCreateCallback){
                fc->nodeCreateCallback(fc, node2);
            }
            count_folder++;
        } else {
            // normal file
            node2 = FolderNodeAdd(node, tail, parent, fileName, utc_time, fileSize, virtual_location, -1, &created);
            
            if(node2){
                node2->writeable = !(wfd.dwFileAttributes & FILE_ATTRIBUTE_READONLY);
                node2->hidden = wfd.dwFileAttributes & FILE_ATTRIBUTE_HIDDEN ? 1 : 0;
                node2->system = wfd.dwFileAttributes & FILE_ATTRIBUTE_SYSTEM ? 1 : 0;
            
                // Callback if created.
                if(created && fc->nodeCreateCallback){
                    fc->nodeCreateCallback(fc, node2);
                }
            }
            
            count_file++;
        }

    } while (fwFindNextFile(handle, &wfd)!=0);
    
    fwFindClose(handle);

    for(node2 = *node; node2; node2 = node2->next){
        if(node2->is_dir){
            // Add the contents of the folder.
            STR_COMBINE_SSS(buffer, basepath, "/", node2->name);
            stockConstructor(fc, &node2->contents, &node2->contents_tail, node2, buffer, virtual_location);
        }
    }
}
static void destroy_nodes(FolderNode *node) {
 while(node) {FolderNode *next=node->next;destroy_nodes(node->contents);free(node->name);free(node);node=next;}
}
static void assert_equal_nodes(FolderNode *a,FolderNode *b,FolderNode *ap,FolderNode *bp,FolderNode *at,FolderNode *bt) {
 FolderNode *last_a=NULL,*last_b=NULL;
 while(a&&b) {
  assert(a->parent==ap&&b->parent==bp&&a->prev==last_a&&b->prev==last_b);
  assert(!strcmp(a->name,b->name));assert(a->virtual_location==b->virtual_location&&a->is_dir==b->is_dir);
  assert(a->writeable==b->writeable&&a->hidden==b->hidden&&a->system==b->system&&a->seen_in_fs==b->seen_in_fs);
  assert(a->in_hash_table==b->in_hash_table&&a->delete_if_absent==b->delete_if_absent);
  assert(a->timestamp==b->timestamp&&a->size==b->size&&a->file_index==b->file_index);
  assert_equal_nodes(a->contents,b->contents,a,b,a->contents_tail,b->contents_tail);
  last_a=a;last_b=b;a=a->next;b=b->next;
 }
 assert(!a&&!b&&last_a==at&&last_b==bt);
}
/* Traversal simulates the unchanged stock final hash-table membership, recording
 * each exact relative path and metadata; pointer values are not compared. */
static unsigned long long provider_digest(FolderNode *node,const char *prefix) {
 unsigned long long hash=1469598103934665603ull;char path[1024];
 for(;node;node=node->next) {
  const unsigned char *p;snprintf(path,sizeof(path),"%s/%s",prefix,node->name);
  for(p=(const unsigned char*)path;*p;p++)hash=(hash^*p)*1099511628211ull;
  hash=(hash^(unsigned long long)(unsigned int)node->timestamp)*1099511628211ull;
  hash=(hash^(unsigned long long)node->size)*1099511628211ull;
  hash^=provider_digest(node->contents,path);
 }
 return hash;
}

int main(int argc,char **argv) {
 unsigned char *packet;FILE *f;long length;unsigned int offset,count,i,record;static const char *branches[]={"texture_library","object_library","fx","scripts","scripts.loc"};
 assert(argc==2);f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);length=ftell(f);rewind(f);assert(length>64&&length<=64*1024*1024);
 packet=(unsigned char*)malloc((size_t)length);assert(packet&&fread(packet,1,(size_t)length,f)==(size_t)length);fclose(f);
 count=cohLiveU32(packet+16);record=cohLiveU32(packet+24);assert(count<=16384);offset=64;
 for(i=0;i<count;i++) {
  unsigned int name_length=packet[offset]|((unsigned int)packet[offset+1]<<8),first=cohLiveU32(packet+offset+4),rows=cohLiveU32(packet+offset+8);
  assert(name_length<260&&offset+16+name_length<=record&&record+(size_t)(first+rows)*328u<=(size_t)length);
  memcpy(fixture_dirs[i].path,"fixture/",8);memcpy(fixture_dirs[i].path+8,packet+offset+16,name_length);fixture_dirs[i].path[8+name_length]=0;
  fixture_dirs[i].count=rows;fixture_dirs[i].rows=packet+record+(size_t)first*328u;offset=(offset+16+name_length+3)&~3;
 }directory_count=count;decoder_refusals();batches=rows_checked=max_batch=0;
 for(i=0;i<5;i++) {
  FolderCache baseline={0},changed={0};char path[1024];int files,folders;
  snprintf(path,sizeof(path),"fixture/%s",branches[i]);count_file=count_folder=0;use_bridge=0;
  stockConstructor(&baseline,&baseline.root,&baseline.root_tail,NULL,path,0);files=count_file;folders=count_folder;
  count_file=count_folder=0;use_bridge=1;
  stockConstructor(&changed,&changed.root,&changed.root_tail,NULL,path,0);
  assert(files==count_file&&folders==count_folder);
  assert_equal_nodes(baseline.root,changed.root,NULL,NULL,baseline.root_tail,changed.root_tail);
  assert(provider_digest(baseline.root,"")==provider_digest(changed.root,""));
  destroy_nodes(baseline.root);destroy_nodes(changed.root);
 }
 printf("COH_LIVE_SOURCE_PARITY_PASS branches=5 refusal_controls=14 terminal_custody_controls=4 rows=%llu buffers=%llu max_packet_bytes=%llu packet_limit=%u cursor_owned_bytes=%lu actual_native_API=0 provider_authority=0\n",rows_checked,batches,max_batch,(unsigned int)COH_LIVE_MAX_BYTES,(unsigned long)sizeof(CohLiveCursor));
 free(packet);return 0;
}
