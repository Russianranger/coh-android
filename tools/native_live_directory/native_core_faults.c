/* Test-only linker interposition. This file is never linked into JNI delivery. */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

enum { F_MALLOC=1,F_CALLOC,F_OPENAT,F_FDOPENDIR,F_READDIR,F_FSTAT,F_READLINKAT,F_GETXATTR,F_CLOSEDIR };
static int fault_kind, fault_remaining;
void coh_live_test_fault(int kind,int calls_before_failure) {
    fault_kind=kind;fault_remaining=calls_before_failure;
}
static int fires(int kind) {
    if(fault_kind!=kind)return 0;
    if(fault_remaining>0){fault_remaining--;return 0;}
    fault_kind=0;errno=EIO;return 1;
}
void *__real_malloc(size_t);
void *__real_calloc(size_t,size_t);
int __real_openat(int,const char *,int,...);
DIR *__real_fdopendir(int);
struct dirent *__real_readdir(DIR *);
int __real_fstat(int,struct stat *);
ssize_t __real_readlinkat(int,const char *,char *,size_t);
ssize_t __real_getxattr(const char *,const char *,void *,size_t);
int __real_closedir(DIR *);
void *__wrap_malloc(size_t n){return fires(F_MALLOC)?NULL:__real_malloc(n);}
void *__wrap_calloc(size_t n,size_t size){return fires(F_CALLOC)?NULL:__real_calloc(n,size);}
int __wrap_openat(int fd,const char *name,int flags,...){
    mode_t mode=0;if(flags&O_CREAT){va_list args;va_start(args,flags);mode=(mode_t)va_arg(args,int);va_end(args);}
    return fires(F_OPENAT)?-1:__real_openat(fd,name,flags,mode);
}
DIR *__wrap_fdopendir(int fd){return fires(F_FDOPENDIR)?NULL:__real_fdopendir(fd);}
struct dirent *__wrap_readdir(DIR *dir){return fires(F_READDIR)?NULL:__real_readdir(dir);}
int __wrap_fstat(int fd,struct stat *out){return fires(F_FSTAT)?-1:__real_fstat(fd,out);}
ssize_t __wrap_readlinkat(int fd,const char *name,char *out,size_t size){return fires(F_READLINKAT)?-1:__real_readlinkat(fd,name,out,size);}
ssize_t __wrap_getxattr(const char *name,const char *attr,void *out,size_t size){return fires(F_GETXATTR)?-1:__real_getxattr(name,attr,out,size);}
int __wrap_closedir(DIR *dir){int force=fires(F_CLOSEDIR);int result=__real_closedir(dir);if(force){errno=EIO;return -1;}return result;}
