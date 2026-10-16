/*
 * NTDLL directory and file functions
 *
 * Copyright 1993 Erik Bos
 * Copyright 2003 Eric Pouech
 * Copyright 1996, 2004 Alexandre Julliard
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA
 */

/* Disposable independent execution of unchanged Wine10 get_file_info body.
 * Linux stat/lstat are real. Xattr-only and logging helpers are deterministic
 * shells, so this is directory reparse classification, not Wine WinAPI execution.
 */
#include <sys/stat.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdio.h>
typedef unsigned long ULONG;
#define FILE_ATTRIBUTE_REPARSE_POINT 1024u
#define FILE_ATTRIBUTE_HIDDEN 2u
#define SAMBA_XATTR_DOS_ATTRIB "user.DOSATTRIB"
#define WARN(...) ((void)0)
static ULONG get_file_attributes(const struct stat *s){return S_ISDIR(s->st_mode)?16u:128u;}
static int xattr_get(const char *p,const char *n,char *v,size_t size){(void)p;(void)n;(void)v;(void)size;errno=ENODATA;return -1;}
static ULONG parse_samba_dos_attrib_data(const char *v,int n){(void)v;(void)n;abort();}
static int is_hidden_file(const char *p){(void)p;return 0;}
static int get_file_info( const char *path, struct stat *st, ULONG *attr )
{
    char *parent_path;
    char attr_data[65];
    int attr_len, ret;

    *attr = 0;
    ret = lstat( path, st );
    if (ret == -1) return ret;
    if (S_ISLNK( st->st_mode ))
    {
        ret = stat( path, st );
        if (ret == -1) return ret;
        /* is a symbolic link and a directory, consider these "reparse points" */
        if (S_ISDIR( st->st_mode )) *attr |= FILE_ATTRIBUTE_REPARSE_POINT;
    }
    else if (S_ISDIR( st->st_mode ) && (parent_path = malloc( strlen(path) + 4 )))
    {
        struct stat parent_st;

        /* consider mount points to be reparse points (IO_REPARSE_TAG_MOUNT_POINT) */
        strcpy( parent_path, path );
        strcat( parent_path, "/.." );
        if (!stat( parent_path, &parent_st )
                && (st->st_dev != parent_st.st_dev || st->st_ino == parent_st.st_ino))
            *attr |= FILE_ATTRIBUTE_REPARSE_POINT;

        free( parent_path );
    }
    *attr |= get_file_attributes( st );

    attr_len = xattr_get( path, SAMBA_XATTR_DOS_ATTRIB, attr_data, sizeof(attr_data)-1 );
    if (attr_len != -1)
        *attr |= parse_samba_dos_attrib_data( attr_data, attr_len );
    else
    {
        if (is_hidden_file( path ))
            *attr |= FILE_ATTRIBUTE_HIDDEN;
        if (errno == ENOTSUP) return ret;
#ifdef ENODATA
        if (errno == ENODATA) return ret;
#endif
#ifdef ENOATTR
        if (errno == ENOATTR) return ret;
#endif
        WARN( "Failed to get extended attribute " SAMBA_XATTR_DOS_ATTRIB " from %s. errno %d (%s)\n",
              debugstr_a(path), errno, strerror( errno ) );
    }
    return ret;
}

int main(int argc,char **argv){for(int i=1;i<argc;i++){struct stat st;ULONG attrs;int status=get_file_info(argv[i],&st,&attrs);printf("case=%d status=%d attrs=%lu reparse=%u\n",i,status,attrs,(unsigned)!!(attrs&FILE_ATTRIBUTE_REPARSE_POINT));}return 0;}

