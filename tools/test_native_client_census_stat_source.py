"""Execute extracted legacy _AltStat with controlled Win32 API behavior."""
from __future__ import annotations
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import map_startup_namespace_certificate as namespace
import prepare_native_client_metadata_census_source as source


def harness(enabled=True):
    raw = source.bytes_lf(source.ROOT / 'upstream/ouroboros' / source.STAT_SOURCE).decode()
    original = namespace.function(raw, 'int _AltStat(')
    patched = namespace.function(source.patch_stat_source(raw.encode()).decode(), 'int _AltStat(')
    prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
typedef uint32_t DWORD;
typedef int BOOL;
typedef int _dev_t;
typedef int32_t __time32_t;
typedef void *HANDLE;
typedef struct FILETIME {uint32_t low,high;} FILETIME;
typedef struct BY_HANDLE_FILE_INFORMATION {DWORD dwFileAttributes,nNumberOfLinks,nFileSizeLow;FILETIME ftLastAccessTime,ftLastWriteTime,ftCreationTime;} BY_HANDLE_FILE_INFORMATION;
struct _stat32 {int32_t st_mtime;int st_mode;short st_nlink;uint32_t st_size;int st_dev,st_rdev,st_ino,st_uid,st_gid;};
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define GENERIC_READ 1
#define FILE_SHARE_READ 2
#define FILE_SHARE_WRITE 4
#define OPEN_EXISTING 8
#define FILE_FLAG_BACKUP_SEMANTICS 16
#define FILE_ATTRIBUTE_DIRECTORY 16
#define PERFINFO_AUTO_START(name,depth) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define ZeroStruct(p) memset((p),0,sizeof(*(p)))
#define warn(...) ((void)0)
#define COH_CENSUS_STAT_CREATE 1
#define COH_CENSUS_STAT_FILE_INFORMATION 2
static int scenario,create_calls,info_calls,close_calls,attribute_calls,observer_create,observer_info;
static DWORD last_error;
static int coh_client_census_stat_scope=1;
static DWORD GetLastError(void) {return last_error;}
static void SetLastError(DWORD value) {last_error=value;}
static void cohClientCensusObserveStatStage(int stage,int succeeded) {
 if(stage==1){++observer_create;assert(succeeded==(scenario!=1&&scenario!=2));}
 else {assert(stage==2);++observer_info;assert(succeeded==(scenario!=3));}
 errno=900;last_error=901; /* Deliberately hostile observer proves restoration. */
}
static HANDLE CreateFileA(const char *name,int access,int sharing,void *security,int disposition,int flags,void *template_file) {
 assert(!strcmp(name,"c:/data/test")&&access==GENERIC_READ&&sharing==(FILE_SHARE_READ|FILE_SHARE_WRITE));
 assert(!security&&disposition==OPEN_EXISTING&&flags==FILE_FLAG_BACKUP_SEMANTICS&&!template_file);
 ++create_calls;errno=101;last_error=102;return scenario==1||scenario==2?INVALID_HANDLE_VALUE:(HANDLE)(intptr_t)1;
}
static DWORD GetFileAttributesA(const char *name) {(void)name;++attribute_calls;errno=201;last_error=202;return scenario==2?16:0xffffffffu;}
static BOOL GetFileInformationByHandle(HANDLE h,BY_HANDLE_FILE_INFORMATION *info) {
 assert(h==(HANDLE)(intptr_t)1);++info_calls;errno=301;last_error=302;
 if(scenario==3)return 0;
 info->dwFileAttributes=32;info->nNumberOfLinks=2;info->nFileSizeLow=99;return 1;
}
static BOOL CloseHandle(HANDLE h) {assert(h==(HANDLE)(intptr_t)1);++close_calls;errno=401;last_error=402;return scenario!=5;}
static int _FileAttributesToUnixMode(DWORD value,const char *name) {(void)name;return (int)value+7;}
static int _FileTimesToUnixTimes(const char *name,const FILETIME *access,const FILETIME *write,const FILETIME *creation,void *a,__time32_t *mtime,void *c) {
 (void)name;(void)access;(void)write;(void)creation;assert(!a&&!c);*mtime=777;return scenario!=4;
}
static int _getdrive(void) {return 1;}
'''
    if enabled:
        prefix += '#define COH_CLIENT_METADATA_CENSUS_CAPTURE 1\n'
    tail = r'''
int main(void) {
 for(scenario=0;scenario<6;scenario++) {
  struct _stat32 before,after;int rc,old_errno,old_create,old_info,old_close,old_attrs;DWORD old_error;
  memset(&before,0xA5,sizeof(before));memset(&after,0xA5,sizeof(after));
  create_calls=info_calls=close_calls=attribute_calls=0;errno=31;last_error=32;
  rc=stock_AltStat("c:/data/test",&before);old_errno=errno;old_error=last_error;
  old_create=create_calls;old_info=info_calls;old_close=close_calls;old_attrs=attribute_calls;
  create_calls=info_calls=close_calls=attribute_calls=observer_create=observer_info=0;errno=31;last_error=32;
  assert(_AltStat("c:/data/test",&after)==rc&&!memcmp(&before,&after,sizeof(before)));
  assert(errno==old_errno&&last_error==old_error);
  assert(create_calls==old_create&&info_calls==old_info&&close_calls==old_close&&attribute_calls==old_attrs);
#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)
  assert(observer_create==1&&observer_info==old_info);
#else
  assert(!observer_create&&!observer_info);
#endif
 }
 puts("CONTROLLED_STAT_SOURCE_PASS cases=6 errno_preserved=1 last_error_preserved=1 legacy_info_failure_unchanged=1");return 0;
}
'''
    return prefix + original.replace('int _AltStat(', 'int stock_AltStat(', 1) + '\n' + patched + tail


def execute(enabled=True):
    compiler = shutil.which('cc')
    if not compiler:
        raise ValueError('C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-native-census-stat-') as temporary:
        root = Path(temporary)
        (root / 'fixture.c').write_text(harness(enabled))
        build = subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', 'fixture.c', '-o', 'fixture'], cwd=root, capture_output=True, text=True)
        if build.returncode:
            raise ValueError('Stat observer compile failed: ' + build.stdout + build.stderr)
        result = subprocess.run([str(root / 'fixture')], text=True, capture_output=True, timeout=5)
        if result.returncode or 'CONTROLLED_STAT_SOURCE_PASS' not in result.stdout:
            raise ValueError('Stat observer fixture failed: ' + result.stdout + result.stderr)
        return result.stdout


class StatSourceTests(unittest.TestCase):
    def test_extracted_legacy_native_stat_and_error_state_with_observers(self):
        self.assertIn('cases=6', execute())

    def test_extracted_legacy_stat_unchanged_when_compile_gate_absent(self):
        self.assertIn('cases=6', execute(False))

    def test_native_api_calls_not_doubled_or_failed_getinfo_behavior_fixed(self):
        raw = source.bytes_lf(source.ROOT / 'upstream/ouroboros' / source.STAT_SOURCE).decode()
        patched = namespace.function(source.patch_stat_source(raw.encode()).decode(), 'int _AltStat(')
        self.assertIn('BOOL coh_info_result = GetFileInformationByHandle(hndl, &bhfi);', patched)
        self.assertNotIn('if (!coh_info_result)', patched)
        self.assertIn('errno = coh_saved_errno;', patched)


if __name__ == '__main__':
    unittest.main()
