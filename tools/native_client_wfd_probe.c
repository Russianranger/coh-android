/* Read-only, qualification-only Win32 ANSI metadata observations.
 * Build: cl /nologo /O2 /MT /TC native_client_wfd_probe.c /Fe:probe.exe
 * Usage: probe.exe DATA_ROOT NEW_OUTPUT GENERATION64 OPERATION32 CI_SECONDS
 * No payloads, PIG indexes, player data, cache nodes or reuse authority.
 * The qualifier owns the output directory and authenticates every identity.
 */
#define WIN32_LEAN_AND_MEAN
#define _WIN32_WINNT 0x0601
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>

#define PROBE_MAX_BYTES (64u * 1024u * 1024u)
#define PROBE_MAX_DIRS 16384u
#define PROBE_MAX_ROWS 200000u
#define PROBE_HEADER_BYTES 160u
#define PROBE_PATH_BYTES 1024u
#define PROBE_RELATIVE_BYTES 260u
#define PROBE_STAT_BYTES 80u
#define PROBE_ROOT 1u
#define PROBE_DIRECTORY 2u
#define PROBE_ENTRY 3u
#define PROBE_DIRECTORY_END 4u
#define PROBE_FOOTER 5u
#define PROBE_NO_PARENT 0xffffffffu

typedef struct ProbeDirectory {
    char relative[PROBE_RELATIVE_BYTES];
    uint32_t parent, branch;
    DWORD volume, index_high, index_low;
    int identity_valid;
} ProbeDirectory;
typedef struct ProbeState {
    HANDLE output;
    char root[PROBE_RELATIVE_BYTES], destination[PROBE_RELATIVE_BYTES];
    char generation[65], operation[33];
    ProbeDirectory *directories;
    uint32_t queued, observed, rows, issues, sequence, written, seconds;
    uint32_t enumeration_complete, readability_complete;
    ULONGLONG started, deadline;
    int assembly_failed, output_created;
} ProbeState;

static const char *probe_branches[5] =
    {"texture_library", "object_library", "fx", "scripts", "scripts.loc"};

static void put32(unsigned char *p, uint32_t value)
{
    p[0]=(unsigned char)value; p[1]=(unsigned char)(value>>8);
    p[2]=(unsigned char)(value>>16); p[3]=(unsigned char)(value>>24);
}
static void put_time(unsigned char *p, FILETIME value)
{
    put32(p,value.dwLowDateTime); put32(p+4,value.dwHighDateTime);
}
static int deadline_ok(ProbeState *state)
{
    if (GetTickCount64() >= state->deadline) {
        state->assembly_failed=1;
        return 0;
    }
    return 1;
}
static int write_bytes(ProbeState *state, const void *data, uint32_t bytes)
{
    const unsigned char *at=(const unsigned char *)data;
    uint32_t left=bytes;
    if (state->assembly_failed || bytes>PROBE_MAX_BYTES-state->written) {
        state->assembly_failed=1; return 0;
    }
    while (left) {
        DWORD done=0;
        if (!deadline_ok(state) || !WriteFile(state->output,at,left,&done,NULL) ||
            !done || done>left) {
            state->assembly_failed=1; return 0;
        }
        state->written+=done; at+=done; left-=done;
    }
    return 1;
}
static int record(ProbeState *state, uint32_t kind, const void *data, uint32_t bytes)
{
    unsigned char header[12];
    if (bytes>PROBE_MAX_BYTES-12u || state->written>PROBE_MAX_BYTES-12u-bytes) {
        state->assembly_failed=1; return 0;
    }
    put32(header,kind); put32(header+4,bytes); put32(header+8,state->sequence++);
    return write_bytes(state,header,12) && write_bytes(state,data,bytes);
}
static int token(const char *value, size_t length, char *output)
{
    size_t i;
    if (!value) return 0;
    for (i=0;i<length;i++) {
        if (!value[i] || !((value[i]>='0'&&value[i]<='9') ||
                           (value[i]>='a'&&value[i]<='f'))) return 0;
        output[i]=value[i];
    }
    if (value[length]) return 0;
    output[length]=0; return 1;
}
static int absolute_path(const char *input, char output[PROBE_RELATIVE_BYTES])
{
    size_t i, n=0, component;
    if (!input) return 0;
    while (n<PROBE_RELATIVE_BYTES && input[n]) ++n;
    if (n<4 || n>=PROBE_RELATIVE_BYTES ||
        !((input[0]>='A'&&input[0]<='Z')||(input[0]>='a'&&input[0]<='z')) ||
        input[1]!=':' || (input[2]!='/'&&input[2]!='\\')) return 0;
    for (i=0;i<n;i++) {
        unsigned char c=(unsigned char)input[i];
        if (c<32 || c>=127 || c=='*'||c=='?'||c=='"'||c=='<'||c=='>'||c=='|' ||
            (c==':'&&i!=1)) return 0;
        output[i]=c=='\\'?'/':(char)c;
    }
    if (n>3 && output[n-1]=='/') --n;
    output[n]=0; component=3;
    for (i=3;i<=n;i++) {
        if (!output[i] || output[i]=='/') {
            size_t count=i-component;
            if (!count || (count==1&&output[component]=='.') ||
                (count==2&&output[component]=='.'&&output[component+1]=='.') ||
                output[i-1]=='.'||output[i-1]==' ') return 0;
            component=i+1;
        }
    }
    return 1;
}
static int below(const char *path, const char *root)
{
    size_t n=strlen(root);
    return !_strnicmp(path,root,n) && (!path[n] || path[n]=='/');
}
static int native_path(ProbeState *state, const char *relative,
                       const char *name, char output[PROBE_PATH_BYTES])
{
    size_t a=strlen(state->root), b=strlen(relative), c=name?strlen(name):0;
    if (a+1+b+(name?1+c:0)>=PROBE_PATH_BYTES) return 0;
    memcpy(output,state->root,a); output[a++]='/';
    memcpy(output+a,relative,b); a+=b;
    if (name) { output[a++]='/'; memcpy(output+a,name,c); a+=c; }
    output[a]=0; return 1;
}
static size_t bounded_string(const char *text, size_t capacity)
{
    size_t i;
    for (i=0;i<capacity&&text[i];i++) {}
    return i;
}
/* Actual names remain raw ANSI bytes. Unsupported path names are observations,
 * never an absent entry; they prevent a complete qualified mapping. */
static int supported_name(const char *name, size_t length)
{
    size_t i;
    if (!length || length>=260) return 0;
    for (i=0;i<length;i++) {
        unsigned char c=(unsigned char)name[i];
        if (c<32||c>=127||c=='/'||c=='\\'||c==':'||c=='*'||c=='?'||
            c=='"'||c=='<'||c=='>'||c=='|') return 0;
    }
    return 1;
}
static int canonical_wfd(const WIN32_FIND_DATAA *value, unsigned char out[320])
{
    size_t name=bounded_string(value->cFileName,260);
    size_t alternate=bounded_string(value->cAlternateFileName,14);
    memset(out,0,320);
    put32(out,value->dwFileAttributes);
    put_time(out+4,value->ftCreationTime); put_time(out+12,value->ftLastAccessTime);
    put_time(out+20,value->ftLastWriteTime);
    put32(out+28,value->nFileSizeHigh); put32(out+32,value->nFileSizeLow);
    memcpy(out+44,value->cFileName,name);
    memcpy(out+304,value->cAlternateFileName,alternate);
    /* Reserved fields, string tails and ABI padding are nonauthoritative zero. */
    return name>0&&name<260&&alternate<14;
}
static void canonical_info(const BY_HANDLE_FILE_INFORMATION *value, unsigned char out[52])
{
    memset(out,0,52); put32(out,value->dwFileAttributes);
    put_time(out+4,value->ftCreationTime); put_time(out+12,value->ftLastAccessTime);
    put_time(out+20,value->ftLastWriteTime); put32(out+28,value->dwVolumeSerialNumber);
    put32(out+32,value->nFileSizeHigh); put32(out+36,value->nFileSizeLow);
    put32(out+40,value->nNumberOfLinks); put32(out+44,value->nFileIndexHigh);
    put32(out+48,value->nFileIndexLow);
}
static int readable(ProbeState *state, const char *path, unsigned char out[PROBE_STAT_BYTES],
                    BY_HANDLE_FILE_INFORMATION *information)
{
    HANDLE input;
    BOOL success, closed;
    DWORD error;
    memset(out,0,PROBE_STAT_BYTES); memset(information,0,sizeof(*information));
    if (!deadline_ok(state)) return 0;
    put32(out,1); /* Attempted. A zero packet is explicit not-attempted. */
    input=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,
                     NULL,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS,NULL);
    if (input==INVALID_HANDLE_VALUE) {
        error=GetLastError(); put32(out+8,error);
        state->readability_complete=0; ++state->issues; return 0;
    }
    put32(out+4,1);
    success=GetFileInformationByHandle(input,information);
    error=success?0:GetLastError();
    put32(out+12,success?1:0); put32(out+16,error);
    if (success) canonical_info(information,out+28);
    closed=CloseHandle(input); error=closed?0:GetLastError();
    put32(out+20,closed?1:0); put32(out+24,error);
    if (!success || !closed) {
        state->readability_complete=0; ++state->issues;
    }
    return success&&closed;
}
static int queue_child(ProbeState *state, uint32_t parent, const char *name)
{
    ProbeDirectory *source=state->directories+parent, *target;
    size_t a=strlen(source->relative), b=strlen(name);
    uint32_t i;
    if (state->queued>=PROBE_MAX_DIRS || a+1+b>=PROBE_RELATIVE_BYTES) {
        state->assembly_failed=1; return 0;
    }
    target=state->directories+state->queued;
    memcpy(target->relative,source->relative,a); target->relative[a++]='/';
    memcpy(target->relative+a,name,b+1); target->parent=parent; target->branch=source->branch;
    for (i=0;i<state->queued;i++) {
        if (!_stricmp(state->directories[i].relative,target->relative)) {
            state->enumeration_complete=0; ++state->issues;
            memset(target,0,sizeof(*target)); return 0;
        }
    }
    ++state->queued; return 1;
}
static void enumerate_directory(ProbeState *state, uint32_t ordinal)
{
    ProbeDirectory *directory=state->directories+ordinal;
    char path[PROBE_PATH_BYTES], search[PROBE_PATH_BYTES];
    unsigned char begin[96+PROBE_RELATIVE_BYTES], packet[412], end[24];
    BY_HANDLE_FILE_INFORMATION info;
    WIN32_FIND_DATAA native;
    HANDLE finder=INVALID_HANDLE_VALUE;
    DWORD first_error=0,next_error=0,close_error=0;
    uint32_t arrival=0,i;
    int closed=0, good;
    size_t length=strlen(directory->relative), path_length;
    if (!native_path(state,directory->relative,NULL,path)) {state->assembly_failed=1;return;}
    memset(begin,0,sizeof(begin)); put32(begin,ordinal); put32(begin+4,directory->parent);
    put32(begin+8,directory->branch); put32(begin+12,(uint32_t)length);
    good=readable(state,path,begin+16,&info);
    memcpy(begin+96,directory->relative,length);
    if (!record(state,PROBE_DIRECTORY,begin,(uint32_t)(96+length))) return;
    ++state->observed;
    if (!good || !(info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY) ||
        (info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT)) {
        state->enumeration_complete=0; ++state->issues;
        first_error=ERROR_NOT_SUPPORTED; goto finish;
    }
    directory->volume=info.dwVolumeSerialNumber;
    directory->index_high=info.nFileIndexHigh; directory->index_low=info.nFileIndexLow;
    directory->identity_valid=1;
    for (i=0;i<ordinal;i++) {
        ProbeDirectory *previous=state->directories+i;
        if (previous->identity_valid&&previous->volume==directory->volume&&
            previous->index_high==directory->index_high&&previous->index_low==directory->index_low) {
            state->enumeration_complete=0; ++state->issues;
            first_error=ERROR_NOT_SUPPORTED; goto finish;
        }
    }
    path_length=strlen(path);
    if (path_length+2>=sizeof(search)) {state->assembly_failed=1;return;}
    memcpy(search,path,path_length); memcpy(search+path_length,"/*",3);
    memset(&native,0,sizeof(native));
    finder=FindFirstFileA(search,&native);
    if (finder==INVALID_HANDLE_VALUE) {
        first_error=GetLastError();
        if (first_error!=ERROR_FILE_NOT_FOUND) {state->enumeration_complete=0;++state->issues;}
        goto finish;
    }
    for (;;) {
        uint32_t flags=0;
        size_t name_length;
        int canonical, alias, supported;
        BY_HANDLE_FILE_INFORMATION entry_info;
        if (!deadline_ok(state) || state->rows>=PROBE_MAX_ROWS) {state->assembly_failed=1;break;}
        memset(packet,0,sizeof(packet)); put32(packet,ordinal); put32(packet+4,arrival);
        canonical=canonical_wfd(&native,packet+12);
        name_length=bounded_string(native.cFileName,260);
        supported=canonical&&supported_name(native.cFileName,name_length);
        alias=canonical&&(!strcmp(native.cFileName,".")||!strcmp(native.cFileName,".."));
        if (supported) flags|=1;
        if (alias) flags|=2;
        if ((native.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))==
            (FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)) flags|=4;
        if (!(native.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)&&
            !(native.dwFileAttributes&FILE_ATTRIBUTE_READONLY)) flags|=8;
        if (!canonical) flags|=16;
        put32(packet+8,flags);
        if (supported&&native_path(state,directory->relative,native.cFileName,path))
            readable(state,path,packet+332,&entry_info);
        else {state->readability_complete=0;++state->issues;}
        if (!record(state,PROBE_ENTRY,packet,sizeof(packet))) break;
        ++state->rows; ++arrival;
        if (flags&8) {state->readability_complete=0;++state->issues;}
        if (native.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY) {
            if (!alias) {
                if (!supported||(flags&4)) {state->enumeration_complete=0;++state->issues;}
                else queue_child(state,ordinal,native.cFileName);
            }
        }
        if (state->assembly_failed) break;
        memset(&native,0,sizeof(native));
        if (!FindNextFileA(finder,&native)) {
            next_error=GetLastError();
            if (next_error!=ERROR_NO_MORE_FILES) {state->enumeration_complete=0;++state->issues;}
            break;
        }
    }
    closed=FindClose(finder)?1:0; close_error=closed?0:GetLastError();
    if (!closed) {state->enumeration_complete=0;++state->issues;}
finish:
    memset(end,0,sizeof(end)); put32(end,ordinal); put32(end+4,arrival);
    put32(end+8,first_error); put32(end+12,next_error);
    put32(end+16,(uint32_t)closed); put32(end+20,close_error);
    record(state,PROBE_DIRECTORY_END,end,sizeof(end));
}
static void receipt(ProbeState *state, const char *status, int cleanup_marked, int closed)
{
    printf("COH_NATIVE_WFD_PROBE_V1 {\"format\":1,\"status\":\"%s\",\"operation\":\"%s\",\"generation\":\"%s\",\"windows_pid\":%lu,\"rows\":%lu,\"directories\":%lu,\"bytes\":%lu,\"issues\":%lu,\"output_created\":%s,\"exact_handle_cleanup_marked\":%s,\"output_handle_closed\":%s,\"provider_authority\":false,\"publication_allowed\":false}\n",
        status,state->operation,state->generation,(unsigned long)GetCurrentProcessId(),
        (unsigned long)state->rows,(unsigned long)state->observed,(unsigned long)state->written,
        (unsigned long)state->issues,state->output_created?"true":"false",
        cleanup_marked?"true":"false",closed?"true":"false");
}
int main(int argc, char **argv)
{
    ProbeState state;
    unsigned char header[PROBE_HEADER_BYTES], root[4+PROBE_STAT_BYTES+PROBE_RELATIVE_BYTES], footer[36];
    BY_HANDLE_FILE_INFORMATION info;
    uint32_t i;
    unsigned long seconds;
    char *end;
    int marked=0,closed=0,code=2,root_ok;
    FILE_DISPOSITION_INFO disposition;
    memset(&state,0,sizeof(state)); state.output=INVALID_HANDLE_VALUE;
    if (argc!=6 || sizeof(void *)!=4 || sizeof(WIN32_FIND_DATAA)!=320 ||
        sizeof(BY_HANDLE_FILE_INFORMATION)!=52 ||
        offsetof(WIN32_FIND_DATAA,cFileName)!=44 ||
        offsetof(WIN32_FIND_DATAA,cAlternateFileName)!=304 ||
        !token(argv[3],64,state.generation)||!token(argv[4],32,state.operation) ||
        !absolute_path(argv[1],state.root)||!absolute_path(argv[2],state.destination) ||
        below(state.destination,state.root)) {
        receipt(&state,"arguments_or_abi_refused",0,0); return 64;
    }
    seconds=strtoul(argv[5],&end,10);
    if (!*argv[5]||*end||seconds<1||seconds>900) {
        receipt(&state,"ci_deadline_refused",0,0); return 64;
    }
    state.seconds=(uint32_t)seconds; state.started=GetTickCount64();
    state.deadline=state.started+seconds*1000ull;
    state.enumeration_complete=state.readability_complete=1;
    state.directories=(ProbeDirectory *)calloc(PROBE_MAX_DIRS,sizeof(*state.directories));
    if (!state.directories) {receipt(&state,"allocation_failed",0,0);return 2;}
    state.output=CreateFileA(state.destination,GENERIC_WRITE|DELETE|FILE_READ_ATTRIBUTES,
        0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
    if (state.output==INVALID_HANDLE_VALUE) {
        free(state.directories); receipt(&state,"exclusive_output_refused",0,0); return 2;
    }
    state.output_created=1;
    memset(header,0,sizeof(header)); memcpy(header,"COHWFD1\0",8);
    put32(header+8,1); put32(header+12,PROBE_HEADER_BYTES);
    put32(header+16,320); put32(header+20,52);
    put32(header+24,GetCurrentProcessId()); put32(header+28,GetCurrentThreadId());
    put32(header+32,3); /* Partial root anchor and capture-only/no authority. */
    put32(header+36,5); put32(header+40,state.seconds); put32(header+44,PROBE_MAX_BYTES);
    memcpy(header+48,state.generation,64); memcpy(header+112,state.operation,32);
    write_bytes(&state,header,sizeof(header));
    memset(root,0,sizeof(root)); put32(root,(uint32_t)strlen(state.root));
    root_ok=readable(&state,state.root,root+4,&info);
    memcpy(root+4+PROBE_STAT_BYTES,state.root,strlen(state.root));
    record(&state,PROBE_ROOT,root,(uint32_t)(4+PROBE_STAT_BYTES+strlen(state.root)));
    if (!root_ok||!(info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)) {
        state.enumeration_complete=0; ++state.issues;
    } else {
        for (i=0;i<5;i++) {
            strcpy(state.directories[i].relative,probe_branches[i]);
            state.directories[i].parent=PROBE_NO_PARENT; state.directories[i].branch=i;
        }
        state.queued=5;
        for (i=0;i<state.queued&&!state.assembly_failed;i++) enumerate_directory(&state,i);
    }
    memset(footer,0,sizeof(footer)); put32(footer,state.queued); put32(footer+4,state.observed);
    put32(footer+8,state.rows); put32(footer+12,state.issues);
    put32(footer+16,state.enumeration_complete); put32(footer+20,state.readability_complete);
    {
        ULONGLONG elapsed=GetTickCount64()-state.started;
        put32(footer+24,(uint32_t)elapsed); put32(footer+28,(uint32_t)(elapsed>>32));
    }
    put32(footer+32,0); /* Cannot authorize a cache or provider. */
    record(&state,PROBE_FOOTER,footer,sizeof(footer));
    if (!state.assembly_failed&&!FlushFileBuffers(state.output)) state.assembly_failed=1;
    if (state.assembly_failed) {
        disposition.DeleteFile=TRUE;
        marked=SetFileInformationByHandle(state.output,FileDispositionInfo,&disposition,sizeof(disposition))?1:0;
        code=2;
    } else code=state.issues?2:0;
    closed=CloseHandle(state.output)?1:0;
    if (!closed) code=2;
    free(state.directories);
    receipt(&state,state.assembly_failed?"assembly_failed":code?"incomplete_observation":"complete_observation",marked,closed);
    return code;
}
