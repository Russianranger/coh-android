#define _GNU_SOURCE
#include "coh_live_directory_core.h"
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/xattr.h>
#include <unistd.h>

#ifndef O_PATH
#error O_PATH is required for a body-free Linux/Bionic backend
#endif
#define ATTR_READONLY 1u
#define ATTR_HIDDEN 2u
#define ATTR_SYSTEM 4u
#define ATTR_DIRECTORY 16u
#define ATTR_ARCHIVE 32u
#define ATTR_REPARSE 1024u
#define ROW_BYTES 328u
#define HEADER_BYTES 64u
#define MAX_ROWS 85u
#define NT_BYTES 8192u
#define TIME_EPOCH UINT64_C(11644473600)
_Static_assert(sizeof(long)==8&&sizeof(int)==4,"Exact reviewed Linux/Bionic ARM64 DOS-xattr widths required");

struct Root {
    char guest[COH_LIVE_PATH_MAX], host[COH_LIVE_PATH_MAX];
    int fd; uint64_t dev, ino; uint32_t uid;
};
struct CohLiveNamespace {
    struct Root roots[COH_LIVE_ROOT_MAX]; size_t count;
    uint32_t uid, guest_uid; uint64_t device; int show_dot_files, case_sensitive;
    CohLiveDirectory *cursors[COH_LIVE_CURSOR_MAX];
    CohLiveStats stats;
};
struct CohLiveDirectory {
    CohLiveNamespace *space; int fd, failed, finished;
    char guest[COH_LIVE_PATH_MAX], requested_guest[COH_LIVE_PATH_MAX];
    char *arena, **names; size_t arena_capacity, arena_used, names_capacity;
    uint32_t count, position, sequence, emitted;
    unsigned char operation[16], directory[16], wire[COH_LIVE_WIRE_MAX];
};

static void error_set(CohLiveError *error, int number, uint64_t rows) {
    if (error) { error->error_number = number ? number : EIO;
        error->rows_emitted = rows; error->fallback_allowed = rows == 0; }
}
static int fail(CohLiveError *error, int number, uint64_t rows) {
    error_set(error, number, rows); return 0;
}
static int ascii_name(const char *name) {
    size_t n = strlen(name), i;
    if (!n || n > COH_LIVE_NAME_MAX || strstr(name, ".l2s")) return 0;
    for (i = 0; i < n; ++i) {
        unsigned char c = (unsigned char)name[i];
        if (c < 32 || c >= 127 || strchr("/\\:*?\"<>|", c)) return 0;
    }
    return 1;
}
static int canonical_path(const char *path) {
    const char *p; size_t n;
    if (!path || path[0] != '/' || (n = strlen(path)) >= COH_LIVE_PATH_MAX ||
        (n > 1 && path[n-1] == '/') || strstr(path, ".l2s")) return 0;
    for (p = path + 1; *p;) {
        const char *start = p;
        while (*p && *p != '/') { unsigned char c = (unsigned char)*p;
            if (c < 32 || c >= 127 || c == '\\') return 0;
            ++p; }
        if (p == start || (p-start == 1 && start[0] == '.') ||
            (p-start == 2 && start[0] == '.' && start[1] == '.')) return 0;
        if (*p) ++p;
    }
    return 1;
}
static int prefix(const char *path, const char *root) {
    size_t n = strlen(root);
    return !strncmp(path, root, n) && (n == 1 || path[n] == 0 || path[n] == '/');
}
static struct Root *choose_root(CohLiveNamespace *space, const char *guest) {
    struct Root *best = NULL; size_t i;
    for (i = 0; i < space->count; ++i)
        if (prefix(guest, space->roots[i].guest) && (!best ||
            strlen(space->roots[i].guest) > strlen(best->guest))) best = &space->roots[i];
    return best;
}
/* Walk native absolute roots without following an ancestor symlink. System
 * ancestors need not be app-owned; the exact final root must match all pins. */
static int host_root_open(const char *path) {
    char copy[COH_LIVE_PATH_MAX], *part, *following, *save = NULL; int current, next, saved;
    if (!canonical_path(path)) { errno = EINVAL; return -1; }
    /* Ancestors authorize search, not enumeration. The returned final root
     * remains a readable directory; "/" itself is final for that spelling. */
    current = open("/", (path[1] ? O_PATH : O_RDONLY)|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (current < 0) return -1;
    strcpy(copy, path);
    for (part = strtok_r(copy+1, "/", &save); part; part = following) {
        following = strtok_r(NULL, "/", &save);
        next = openat(current, part, (following ? O_PATH : O_RDONLY)|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        saved = errno; close(current); errno = saved;
        if (next < 0) return -1;
        current = next;
    }
    return current;
}
static int root_matches(struct Root *root, int fd) {
    struct stat st;
    return !fstat(fd, &st) && S_ISDIR(st.st_mode) &&
        (uint64_t)st.st_dev == root->dev && (uint64_t)st.st_ino == root->ino &&
        (uint32_t)st.st_uid == root->uid;
}
int coh_live_namespace_validate(CohLiveNamespace *space, CohLiveError *error) {
    size_t i; int fd, saved;
    if (!space || (uint32_t)getuid() != space->uid) return fail(error, EPERM, 0);
    for (i = 0; i < space->count; ++i) {
        if (!root_matches(&space->roots[i], space->roots[i].fd)) return fail(error, ESTALE, 0);
        fd = host_root_open(space->roots[i].host);
        if (fd < 0) return fail(error, errno, 0);
        saved = root_matches(&space->roots[i], fd) ? 0 : ESTALE;
        close(fd); if (saved) return fail(error, saved, 0);
    }
    return 1;
}
static int owned_uid(CohLiveNamespace *space, const struct stat *st) {
    if ((uint32_t)st->st_uid != space->uid) { errno = EPERM; return 0; }
    if ((uint64_t)st->st_dev != space->device) { errno = EXDEV; return 0; }
    return 1;
}
static int guest_append(char *path, const char *part) {
    size_t n = strlen(path), p = strlen(part), slash = n != 1;
    if (n + slash + p >= COH_LIVE_PATH_MAX) { errno = ENAMETOOLONG; return 0; }
    if (slash) path[n++] = '/';
    memcpy(path+n, part, p+1); return 1;
}
static void guest_parent(char *path) {
    char *slash = strrchr(path, '/'); if (slash == path) path[1] = 0; else *slash = 0;
}
/* Current held-FD resolution. Absolute links re-enter the admitted GUEST bind
 * table. Relative links start at the held directory, including after rename.
 * Every opened leaf is O_PATH|O_NOFOLLOW: a racing link cannot escape to a host
 * absolute path. readlinkat(fd, "") reads that exact owned link inode. */
static int resolve(CohLiveNamespace *space, int base_fd, const char *base_guest,
    const char *path, struct stat *result, uint32_t *extra, int want_directory,
    char canonical_guest[COH_LIVE_PATH_MAX]) {
    char pending[COH_LIVE_PATH_MAX], guest[COH_LIVE_PATH_MAX], component[260];
    char target[COH_LIVE_PATH_MAX], rest[COH_LIVE_PATH_MAX];
    struct Root *root, *selected; struct stat st; int current = -1, leaf = -1;
    unsigned links = 0; int final_link = 0, saved; ssize_t bytes;
    if (!path || strlen(path) >= sizeof(pending) || strstr(path, ".l2s")) { errno=EINVAL; return -1; }
    if (path[0] == '/') {
        root = choose_root(space, path); if (!root) { errno=EXDEV; return -1; }
        strcpy(guest, root->guest);
        strcpy(pending, path + strlen(root->guest));
        current = openat(root->fd, ".", O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    } else {
        if (base_fd < 0 || !base_guest || !canonical_path(base_guest)) { errno=EINVAL; return -1; }
        root = choose_root(space, base_guest); if (!root) { errno=EXDEV; return -1; }
        strcpy(guest, base_guest); strcpy(pending, path);
        current = openat(base_fd, ".", O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    }
    if (current < 0) return -1;
    for (;;) {
        char *start = pending, *slash; size_t length;
        while (*start == '/') ++start;
        if (!*start) { leaf=current; current=-1; break; }
        slash = strchr(start, '/'); length = slash ? (size_t)(slash-start) : strlen(start);
        if (!length || length >= sizeof(component)) { errno=ENAMETOOLONG; goto bad; }
        memcpy(component,start,length); component[length]=0;
        strcpy(rest,slash ? slash+1 : "");
        if (!strcmp(component,".")) { strcpy(pending,rest); continue; }
        if (!strcmp(component,"..")) {
            if (!strcmp(guest,"/")) { errno=EXDEV; goto bad; }
            guest_parent(guest); selected=choose_root(space,guest);
            if (!selected) { errno=EXDEV; goto bad; }
            if (selected != root) {
                /* A binding parent cannot be reconstructed through a raw host
                 * .. view. Re-resolve its admitted absolute guest spelling. */
                char absolute[COH_LIVE_PATH_MAX];
                if (snprintf(absolute,sizeof(absolute),"%s%s%s",guest,*rest?"/":"",rest) >= (int)sizeof(absolute)) { errno=ENAMETOOLONG; goto bad; }
                strcpy(pending,absolute+strlen(selected->guest)); strcpy(guest,selected->guest);
                leaf=openat(selected->fd,".",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
                root=selected;
            } else {
                leaf=openat(current,"..",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
                strcpy(pending,rest);
            }
            if (leaf<0) goto bad;
            if (fstat(leaf,&st) || !owned_uid(space,&st)) goto bad;
            close(current); current=leaf; leaf=-1;
            continue;
        }
        if (!ascii_name(component)) { errno=EOPNOTSUPP; goto bad; }
        {
            char next_guest[COH_LIVE_PATH_MAX]; strcpy(next_guest,guest);
            if (!guest_append(next_guest,component)) goto bad;
            selected=choose_root(space,next_guest);
            if (!selected) { errno=EXDEV; goto bad; }
            if (selected!=root) {
                if (strcmp(next_guest,selected->guest)) { errno=EXDEV; goto bad; }
                leaf=openat(selected->fd,".",O_PATH|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
                root=selected;
            } else leaf=openat(current,component,O_PATH|O_NOFOLLOW|O_CLOEXEC);
            if (leaf<0) goto bad;
            if (fstat(leaf,&st) || !owned_uid(space,&st)) goto bad;
            if (S_ISLNK(st.st_mode)) {
                if (++links>COH_LIVE_SYMLINK_MAX) { errno=ELOOP; goto bad; }
                bytes=readlinkat(leaf,"",target,sizeof(target)-1);
                if (bytes<0) goto bad;
                target[bytes]=0;
                if (!bytes || (size_t)bytes==sizeof(target)-1 || strstr(target,".l2s")) { errno=EOPNOTSUPP; goto bad; }
                if (snprintf(pending,sizeof(pending),"%s%s%s",target,*rest?"/":"",rest) >= (int)sizeof(pending)) { errno=ENAMETOOLONG; goto bad; }
                close(leaf); leaf=-1;
                if (!*rest) final_link=1;
                if (target[0]=='/') {
                    root=choose_root(space,pending); if (!root) { errno=EXDEV; goto bad; }
                    strcpy(rest,pending+strlen(root->guest)); strcpy(guest,root->guest); strcpy(pending,rest);
                    close(current); current=openat(root->fd,".",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
                    if (current<0) goto bad;
                }
                continue;
            }
            strcpy(guest,next_guest);
            if (!*rest) break;
            if (!S_ISDIR(st.st_mode)) { errno=ENOTDIR; goto bad; }
            close(current); current=leaf; leaf=-1; strcpy(pending,rest);
        }
    }
    if (fstat(leaf,&st) || !owned_uid(space,&st)) goto bad;
    if ((!S_ISDIR(st.st_mode) && !S_ISREG(st.st_mode)) || (want_directory && !S_ISDIR(st.st_mode))) { errno=EOPNOTSUPP; goto bad; }
    if (extra) *extra=final_link && S_ISDIR(st.st_mode) ? ATTR_REPARSE : 0;
    if (result) *result=st;
    if (canonical_guest) strcpy(canonical_guest,guest);
    if (current>=0) close(current);
    return leaf;
bad:
    saved=errno ? errno : EIO; if (leaf>=0) close(leaf); if (current>=0) close(current); errno=saved; return -1;
}
static int directory_validate(CohLiveDirectory *c,CohLiveError *error) {
    struct stat held,current;char guest[COH_LIVE_PATH_MAX];int fd,saved;
    if (!coh_live_namespace_validate(c->space,error)) return 0;
    fd=resolve(c->space,-1,NULL,c->requested_guest,&current,NULL,1,guest);
    if (fd<0) return fail(error,errno,c->emitted);
    saved=fstat(c->fd,&held) ? errno : 0;
    close(fd);
    if (saved) return fail(error,saved,c->emitted);
    if (held.st_dev!=current.st_dev||held.st_ino!=current.st_ino||strcmp(guest,c->guest))
        return fail(error,ESTALE,c->emitted);
    return 1;
}

static void *allocate(CohLiveNamespace *space, size_t size) {
    void *out;
    if (size > COH_LIVE_HEAP_MAX-space->stats.owned_heap_bytes) { errno=ENOMEM; return NULL; }
    out=malloc(size); if (!out) return NULL;
    space->stats.owned_heap_bytes+=size;
    if (space->stats.owned_heap_bytes>space->stats.peak_heap_bytes) space->stats.peak_heap_bytes=space->stats.owned_heap_bytes;
    return out;
}
static void release(CohLiveNamespace *space, void *pointer, size_t bytes) {
    if (pointer) { free(pointer); space->stats.owned_heap_bytes-=bytes; }
}
static int ascii_compare(const void *left, const void *right) {
    const unsigned char *a=(const unsigned char *)*(const char *const *)left;
    const unsigned char *b=(const unsigned char *)*(const char *const *)right;
    const unsigned char *first=a,*second=b;
    while (*a && *b) { int x=*a, y=*b;
        if (x>='a'&&x<='z') x-=32;
        if (y>='a'&&y<='z') y-=32;
        if (x!=y) return x-y;
        ++a; ++b; }
    if (*a!=*b) return (int)*a-(int)*b;
    return strcmp((const char *)first,(const char *)second);
}
static int append_name(CohLiveDirectory *c, const char *name) {
    size_t bytes=strlen(name)+1;
    if (c->count>=COH_LIVE_NAMES_MAX) { errno=EOVERFLOW; return 0; }
    if (bytes>c->arena_capacity-c->arena_used) {
        size_t capacity=c->arena_capacity ? c->arena_capacity*2 : 4096;
        char *next;
        if (capacity > COH_LIVE_NAMES_MAX*(COH_LIVE_NAME_MAX+1u)) capacity=COH_LIVE_NAMES_MAX*(COH_LIVE_NAME_MAX+1u);
        next=allocate(c->space,capacity); if (!next) return 0;
        if (c->arena) memcpy(next,c->arena,c->arena_used);
        release(c->space,c->arena,c->arena_capacity); c->arena=next; c->arena_capacity=capacity;
    }
    memcpy(c->arena+c->arena_used,name,bytes); c->arena_used+=bytes; c->count++; return 1;
}
int coh_live_namespace_open(CohLiveNamespace **out,const CohLiveRootSpec *roots,
    size_t count,uint32_t uid,uint32_t guest_uid,int show_dot_files,int case_sensitive,CohLiveError *error) {
    CohLiveNamespace *space; size_t i,j; int saved;
    if (out) *out=NULL;
    if (!out || !roots || !count || count>COH_LIVE_ROOT_MAX || uid!=(uint32_t)getuid() || guest_uid!=1000 ||
        (show_dot_files!=0&&show_dot_files!=1) || (case_sensitive!=0&&case_sensitive!=1)) return fail(error,EINVAL,0);
    space=calloc(1,sizeof(*space)); if (!space) return fail(error,ENOMEM,0);
    space->count=count; space->uid=uid; space->guest_uid=guest_uid;
    space->device=roots[0].device;
    space->show_dot_files=show_dot_files; space->case_sensitive=case_sensitive;
    space->stats.owned_heap_bytes=space->stats.peak_heap_bytes=sizeof(*space);
    for (i=0;i<count;i++) space->roots[i].fd=-1;
    for (i=0;i<count;i++) {
        struct Root *r=&space->roots[i];
        if (!canonical_path(roots[i].guest_prefix)||!canonical_path(roots[i].host_root)||roots[i].uid!=uid) { errno=EINVAL; goto bad; }
        if (roots[i].device!=space->device) { errno=EXDEV; goto bad; }
        for (j=0;j<i;j++) if (!strcmp(roots[j].guest_prefix,roots[i].guest_prefix)) { errno=EINVAL; goto bad; }
        strcpy(r->guest,roots[i].guest_prefix); strcpy(r->host,roots[i].host_root);
        r->dev=roots[i].device; r->ino=roots[i].inode; r->uid=roots[i].uid;
        r->fd=host_root_open(r->host);
        if (r->fd<0) goto bad;
        if (!root_matches(r,r->fd)) { errno=ESTALE; goto bad; }
    }
    *out=space; return 1;
bad:
    saved=errno; coh_live_namespace_close(space); return fail(error,saved,0);
}
int coh_live_directory_open(CohLiveNamespace *space,CohLiveDirectory **out,
    const char *guest,const unsigned char operation[16],const unsigned char directory[16],CohLiveError *error) {
    CohLiveDirectory *c=NULL; DIR *stream=NULL; struct dirent *entry;
    struct stat st; size_t slot,i,offset; int listfd=-1,saved;
    if (out) *out=NULL;
    if (!space||!out||!canonical_path(guest)||!operation||!directory) return fail(error,EINVAL,0);
    if (!coh_live_namespace_validate(space,error)) return 0;
    for (slot=0;slot<COH_LIVE_CURSOR_MAX&&space->cursors[slot];slot++);
    if (slot==COH_LIVE_CURSOR_MAX) return fail(error,EMFILE,0);
    c=allocate(space,sizeof(*c)); if (!c) return fail(error,errno,0);
    memset(c,0,sizeof(*c)); c->fd=-1; c->space=space; strcpy(c->guest,guest);strcpy(c->requested_guest,guest);
    memcpy(c->operation,operation,16); memcpy(c->directory,directory,16);
    c->fd=resolve(space,-1,NULL,guest,&st,NULL,1,c->guest); if (c->fd<0) goto bad;
    /* Fresh file description prevents readdir from modifying any authorization
     * or root descriptor's directory position. */
    listfd=openat(c->fd,".",O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if (listfd<0) goto bad;
    stream=fdopendir(listfd); if (!stream) goto bad; listfd=-1;
    if (!append_name(c,".")||!append_name(c,"..")) goto bad;
    errno=0;
    while ((entry=readdir(stream))) {
        if (!strcmp(entry->d_name,".")||!strcmp(entry->d_name,"..")) continue;
        if (!ascii_name(entry->d_name)) { errno=EOPNOTSUPP; goto bad; }
        if (!append_name(c,entry->d_name)) goto bad;
        errno=0;
    }
    if (errno) goto bad;
    if (closedir(stream)) { stream=NULL; goto bad; } stream=NULL;
    c->names_capacity=(size_t)c->count*sizeof(*c->names);
    c->names=allocate(space,c->names_capacity); if (!c->names) goto bad;
    for (i=0,offset=0;i<c->count;i++) { c->names[i]=c->arena+offset; offset+=strlen(c->arena+offset)+1; }
    qsort(c->names+2,c->count-2,sizeof(*c->names),ascii_compare);
    if (!directory_validate(c,error)) { errno=error?error->error_number:ESTALE; goto bad; }
    space->cursors[slot]=c; space->stats.names_opened+=c->count; *out=c; return 1;
bad:
    saved=errno?errno:EIO; if (stream) closedir(stream); if (listfd>=0) close(listfd);
    if (c) coh_live_directory_close(c);
    return fail(error,saved,0);
}
static void u32(unsigned char *out,uint32_t n) { out[0]=(unsigned char)n;out[1]=(unsigned char)(n>>8);out[2]=(unsigned char)(n>>16);out[3]=(unsigned char)(n>>24); }
static void u64(unsigned char *out,uint64_t n) { u32(out,(uint32_t)n);u32(out+4,(uint32_t)(n>>32)); }
static int metadata(CohLiveDirectory *c,const char *name,struct stat *st,uint32_t *attrs) {
    char path[64], data[65],*end; uint32_t extra=0; ssize_t bytes; int fd,saved;
    c->space->stats.metadata_requests++;
    fd=resolve(c->space,c->fd,c->guest,name,st,&extra,0,NULL);
    if (fd<0) return -1;
    *attrs=(S_ISDIR(st->st_mode)?ATTR_DIRECTORY:ATTR_ARCHIVE)|extra;
    if (!(st->st_mode&0222)) *attrs|=ATTR_READONLY;
    snprintf(path,sizeof(path),"/proc/self/fd/%d",fd);
    bytes=getxattr(path,"user.DOSATTRIB",data,64);
    saved=errno; close(fd);
    if (bytes>=0) {
        data[bytes]=0;
        if (bytes>2&&data[0]=='0'&&data[1]=='x') {
            int value=(int)strtol(data,&end,16);
            if (!*end) *attrs|=(uint32_t)value&(ATTR_HIDDEN|ATTR_SYSTEM);
            else { errno=EOPNOTSUPP; return -1; }
        } else { errno=EOPNOTSUPP; return -1; }
    } else {
        if (saved!=ENODATA&&saved!=ENOTSUP&&saved!=EOPNOTSUPP) { errno=saved; return -1; }
        if (!c->space->show_dot_files&&name[0]=='.'&&strcmp(name,".")&&strcmp(name,"..")) *attrs|=ATTR_HIDDEN;
    }
    return 0;
}
int coh_live_directory_next(CohLiveDirectory *c,const unsigned char **wire,size_t *length,CohLiveError *error) {
    uint32_t rows=0,used=0,start; int saved; CohLiveError check;
    if (wire) *wire=NULL;
    if (length) *length=0;
    if (!c||!wire||!length) return fail(error,EINVAL,0);
    if (c->failed||c->finished) return fail(error,EPIPE,c->emitted);
    if (!directory_validate(c,&check)) { saved=check.error_number; goto bad; }
    memset(c->wire,0,sizeof(c->wire)); start=c->emitted;
    while (c->position<c->count) {
        const char *name=c->names[c->position]; struct stat st; uint32_t attrs,nt; uint64_t seconds;
        unsigned char *row,*wfd;
        if (metadata(c,name,&st,&attrs)) {
            if (errno==ENOENT||errno==ENOTDIR) { c->position++;c->space->stats.skipped_missing++;continue; }
            saved=errno; goto bad;
        }
        nt=((used+7u)&~7u)+94u+(uint32_t)strlen(name)*2u;
        if (nt>NT_BYTES) break; /* Wine retries overflow metadata next query. */
        if (rows>=MAX_ROWS) { saved=EOVERFLOW;goto bad; }
        row=c->wire+HEADER_BYTES+(size_t)rows*ROW_BYTES;wfd=row+8;
        used=nt;
        u32(row,start+rows); u32(wfd,attrs);
        if (st.st_mtim.tv_sec < -(int64_t)TIME_EPOCH || st.st_mtim.tv_nsec<0||st.st_mtim.tv_nsec>=1000000000) { saved=EOVERFLOW;goto bad; }
        seconds=st.st_mtim.tv_sec>=0 ? (uint64_t)st.st_mtim.tv_sec+TIME_EPOCH :
            TIME_EPOCH-(uint64_t)(-(st.st_mtim.tv_sec+1))-1;
        if (seconds > (UINT64_MAX-UINT64_C(9999999))/UINT64_C(10000000)) { saved=EOVERFLOW;goto bad; }
        u64(wfd+20,seconds*UINT64_C(10000000)+(uint64_t)st.st_mtim.tv_nsec/100);
        if (!S_ISDIR(st.st_mode)) { if (st.st_size<0) { saved=EOVERFLOW;goto bad; }
            u32(wfd+28,(uint32_t)((uint64_t)st.st_size>>32));u32(wfd+32,(uint32_t)st.st_size); }
        memcpy(wfd+44,name,strlen(name)+1); c->position++;rows++;
    }
    if (!rows&&c->position<c->count) { saved=EOVERFLOW; goto bad; }
    if (!directory_validate(c,&check)) { saved=check.error_number;goto bad; }
    memcpy(c->wire,"COHLIVE1",8);memcpy(c->wire+8,c->operation,16);memcpy(c->wire+24,c->directory,16);
    u32(c->wire+40,c->sequence++);u32(c->wire+44,start);u32(c->wire+48,rows);
    c->finished=c->position==c->count;u32(c->wire+52,(uint32_t)c->finished);
    *length=HEADER_BYTES+(size_t)rows*ROW_BYTES;u32(c->wire+60,(uint32_t)*length);
    c->emitted+=rows;c->space->stats.batches++;*wire=c->wire;return 1;
bad:
    c->failed=1; memset(c->wire,0,sizeof(c->wire));return fail(error,saved,c->emitted);
}
void coh_live_directory_close(CohLiveDirectory *c) {
    CohLiveNamespace *space; size_t i;
    if (!c) return;
    space=c->space;
    if (c->fd>=0) close(c->fd);
    for (i=0;i<COH_LIVE_CURSOR_MAX;i++) if (space->cursors[i]==c) space->cursors[i]=NULL;
    release(space,c->names,c->names_capacity);release(space,c->arena,c->arena_capacity);
    release(space,c,sizeof(*c));
}
void coh_live_namespace_close(CohLiveNamespace *space) {
    size_t i; if (!space) return;
    for (i=0;i<COH_LIVE_CURSOR_MAX;i++) coh_live_directory_close(space->cursors[i]);
    for (i=0;i<space->count;i++) if (space->roots[i].fd>=0) close(space->roots[i].fd);
    free(space);
}
void coh_live_namespace_stats(const CohLiveNamespace *space,CohLiveStats *out) {
    if (space&&out) *out=space->stats;
}
int coh_live_directory_identity(CohLiveDirectory *c,uint64_t *device,
    uint64_t *inode,uint32_t *uid,CohLiveError *error) {
    struct stat st;
    if (!c||!device||!inode||!uid) return fail(error,EINVAL,0);
    if (c->failed||fstat(c->fd,&st)||!S_ISDIR(st.st_mode)||!owned_uid(c->space,&st))
        return fail(error,errno?errno:ESTALE,c->emitted);
    *device=(uint64_t)st.st_dev;*inode=(uint64_t)st.st_ino;*uid=(uint32_t)st.st_uid;
    return 1;
}
const char *coh_live_directory_guest_path(const CohLiveDirectory *cursor) {
    return cursor ? cursor->guest : NULL;
}
