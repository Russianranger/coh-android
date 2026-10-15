"""Source-bound readiness gate and actual native provider/freshness algorithms."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import map_startup_namespace_certificate as audit


def harness():
    source = (audit.ROOT / audit.NODE).read_text()
    node = audit.function(source, 'FolderNode *FolderNodeAdd(')
    parser = audit.function((audit.ROOT / audit.PARSER).read_text(),
                            'SimpleBufHandle ParserIsPersistNewer(')
    prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdbool.h>
#define MAX_PATH 260
#define stricmp strcasecmp
typedef struct FolderNode {
    struct FolderNode *next, *prev, *parent, *contents, *contents_tail;
    int virtual_location, file_index, is_dir, seen_in_fs;
    size_t size; int32_t timestamp; char *name;
} FolderNode;
static int folder_cache_debug, update_count, discard_count;
static FolderNode *FolderNodeCreate(void) {return calloc(1, sizeof(FolderNode));}
static char *allocAddString(const char *text) {return strdup(text);}
static char *firstSlash(char *text) {
    while (*text) {if (*text == '/' || *text == '\\') return text; ++text;} return NULL;
}
typedef int SimpleBufHandle;
typedef int ParseTable;
typedef int DefineContext;
typedef int32_t __time32_t;
typedef struct FileEntry {char path[260]; int32_t date; int seen;} FileEntry;
typedef FileEntry **FileList;
static FileList lf_filedates;
static FileEntry bins[4], scanned[4];
static FileEntry *bin_ptrs[4], *scan_ptrs[4];
static int count, scanned_count, scan_count, production, open_ok, read_ok, scenario;
static int checks, scans, closes, seeks;
static const char *g_StdAdditionalFilePrefixes[] = {"v_", "d_", ""};
#define PARSE_SIG "Parse6"
#define verbose_printf(...) ((void)0)
static int ParseTableCRC(ParseTable *p, DefineContext *d) {(void)p;(void)d;return 7;}
static int isProductionMode(void) {return production;}
/* Bounded IO adapters: actual provider/freshness C bodies below are unchanged. */
static int SerializeReadOpen(const char *p,const char *s,int crc,int prod) {
    (void)p;(void)prod;assert(!strcmp(s, "Parse6") && crc == 7);return open_ok;
}
static int SimpleBufTell(int file) {(void)file;return 12;}
static int FileListRead(FileList *list,int file) {(void)file;*list=bin_ptrs;return read_ok;}
static void FileListCreate(FileList *list) {*list=scan_ptrs;scan_count=0;}
static int eaSize(FileList *list) {return *list==bin_ptrs?count:*list==scan_ptrs?scan_count:0;}
static int DateCheckCallback(void) {return 1;}
static void fileScanAllDataDirs(const char *dir,int (*callback)(void)) {
    (void)dir;assert(callback==DateCheckCallback);scans++;scan_count=scanned_count;
}
static int fileLastChanged(const char *path);
static void FileListInsert(FileList *list,const char *path,int date) {
    assert(*list==scan_ptrs && scan_count<4);
    strcpy(scanned[scan_count].path,path);
    scanned[scan_count].date=date?date:fileLastChanged(path);
    scanned[scan_count].seen=0;scan_count++;
}
static char *addFilePrefix(const char *path,const char *prefix) {
    static char out[260]; const char *slash=strrchr(path,'/'); size_t offset=slash?slash-path+1:0;
    assert(strlen(path)+strlen(prefix)<sizeof(out));memcpy(out,path,offset);out[offset]=0;
    strcat(out,prefix);strcat(out,path+offset);return out;
}
static FileEntry *FileListFind(FileList *list,char *path) {
    int i;for(i=0;i<eaSize(list);i++)if(!strcasecmp((*list)[i]->path,path))return (*list)[i];return NULL;
}
static int fileDatesEqual(int a,int b,int dst) {checks++;return a==b||(dst&&(a-b==3600||b-a==3600));}
static int fileLastChanged(const char *path) {
    if(strstr(path,"/v_")||strstr(path,"/d_"))return scenario==11?1767225600:0;
    if(scenario==7&&!strcmp(path,"defs/fx/base.fx"))return 0;
    if(!strcmp(path,"defs/shared.txt")) {
        if(scenario==4)return 1767225610;
        if(scenario==5)return 0;
        if(scenario==8)return 1767229200;
    }
    return 1767225600;
}
static int fileExists(const char *path) {
    if(strstr(path,"/v_")||strstr(path,"/d_"))return scenario==11;
    return 1;
}
static void FileListDestroy(FileList *list) {*list=NULL;}
static void SimpleBufSeek(int file,int at,int whence) {(void)file;assert(at==12&&whence==SEEK_SET);seeks++;}
static void SerializeClose(int file) {(void)file;closes++;}
'''
    tail = r'''
static void provider_tests(void) {
    FolderNode *head=NULL,*tail=NULL,*node;int made;
    node=FolderNodeAdd(&head,&tail,NULL,"Fx/Test.FX",1767225600,100,0,-1,&made);
    assert(node&&made&&node->virtual_location==0);
    /* Case-insensitive same name; matching Pig date wins over loose. */
    node=FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767225600,100,-1,4,&made);
    assert(node&&!made&&node->virtual_location==-1&&node->file_index==4);
    node=FolderNodeAdd(&head,&tail,NULL,"FX/TEST.FX",1767225600,100,-2,5,&made);
    assert(node&&node->virtual_location==-2&&node->file_index==5);
    assert(!FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767225600,100,-1,4,&made));
    /* Matching loose date preserves Pig; changed loose date selects override. */
    assert(!FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767225600,100,0,-1,&made));
    node=FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767225610,101,0,-1,&made);
    assert(node&&node->virtual_location==0&&node->size==101);
    node=FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767225610,101,2,-1,&made);
    assert(node&&node->virtual_location==2);
    assert(!FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767225610,101,1,-1,&made));
    /* The stock Pig-vs-loose one-hour rule is directional, not arbitrary tolerance. */
    node=FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767229210,101,-3,9,&made);
    assert(node&&node->virtual_location==-3);
    assert(!FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767232810,101,3,-1,&made));
    node=FolderNodeAdd(&head,&tail,NULL,"fx/test.fx",1767232811,102,3,-1,&made);
    assert(node&&node->virtual_location==3);
}
static void reset(int test) {
    int i;scenario=test;count=2;scanned_count=1;scan_count=production=checks=scans=closes=seeks=0;
    open_ok=read_ok=1;memset(bins,0,sizeof(bins));memset(scanned,0,sizeof(scanned));
    strcpy(bins[0].path,"defs/fx/base.fx");strcpy(bins[1].path,"defs/shared.txt");
    bins[0].date=bins[1].date=1767225600;scanned[0]=bins[0];
    for(i=0;i<4;i++){bin_ptrs[i]=&bins[i];scan_ptrs[i]=&scanned[i];}
    if(test==1)open_ok=0;
    if(test==2)read_ok=0;
    if(test==3)scanned[0].date++;
    if(test==6){scanned_count=2;strcpy(scanned[1].path,"defs/fx/added.fx");scanned[1].date=1767225600;}
    if(test==7)scanned_count=0;
    if(test==9)production=1;
}
int main(void) {
    int test;
    provider_tests();
    for(test=0;test<12;test++) {
        int value;reset(test);
        value=ParserIsPersistNewer(test>=10?NULL:"defs/fx",test>=10?"defs/fx/base.fx":".fx",
                                  "bin/fxinfo.bin",NULL,NULL);
        assert(value==(test==0||test==8||test==9||test==10));
        if(test==0)assert(checks==2&&scans==1&&seeks==1&&!closes);
        if(test==9)assert(!checks&&!scans&&!closes&&!seeks);
        if(!value&&test!=1)assert(closes==1&&!seeks);
    }
    puts("COH_NAMESPACE_STOCK_ALGORITHMS_PASS provider_cases=11 freshness_cases=12 shipping_bypass=0");
    return 0;
}
'''
    return prefix + '\n' + node + '\n' + parser + '\n' + tail


def execute():
    compiler = shutil.which('cc')
    audit.require(compiler, 'Host C compiler required for stock native algorithm fixture')
    with tempfile.TemporaryDirectory(prefix='coh-namespace-stock-') as temporary:
        path = Path(temporary)
        (path / 'fixture.c').write_text(harness())
        build = subprocess.run([compiler, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-O2',
                                str(path / 'fixture.c'), '-o', str(path / 'fixture')],
                               capture_output=True, text=True)
        audit.require(build.returncode == 0, 'Stock fixture compile failed: ' + build.stderr)
        result = subprocess.run([str(path / 'fixture')], capture_output=True, text=True)
        audit.require(result.returncode == 0, 'Stock fixture failed: ' + result.stderr)
        audit.require('COH_NAMESPACE_STOCK_ALGORITHMS_PASS' in result.stdout, 'Stock fixture receipt missing')
        return {'status': 'passed', 'scope': 'extracted_actual_native_C_algorithms_with_bounded_IO_adapters',
                'provider_cases': 11, 'freshness_cases': 12,
                'harness_sha256': hashlib.sha256(harness().encode()).hexdigest(),
                'full_mapserver_wine_execution': False, 'shipping_bypass_enabled': False}


class NamespaceCertificateGateTests(unittest.TestCase):
    def test_current_source_receipt_blocks_bypass(self):
        value = audit.audit()
        self.assertEqual(value['status'], 'blocked_exact_native_provider_generation_missing')
        self.assertFalse(value['production_freshness_bypass_enabled'])
        self.assertFalse(value['global_production_mode_enabled'])
        self.assertFalse(value['native_loader_changed'])
        self.assertEqual(len(value['source_sha256']), 10)
        self.assertTrue(all(value['source_semantics_verified'].values()))

    def test_actual_native_provider_and_freshness_failure_branches(self):
        result = execute()
        self.assertEqual((result['provider_cases'], result['freshness_cases']), (11, 12))
        self.assertFalse(result['full_mapserver_wine_execution'])

    def test_in_place_leaf_change_does_not_require_parent_mtime_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary); leaf = parent / 'original.fx'
            leaf.write_bytes(b'original'); leaf.chmod(0o400)
            before = parent.stat().st_mtime_ns
            original = hashlib.sha256(leaf.read_bytes()).hexdigest()
            leaf.chmod(0o600); leaf.write_bytes(b'modified'); leaf.chmod(0o400)
            self.assertEqual(parent.stat().st_mtime_ns, before)
            self.assertNotEqual(hashlib.sha256(leaf.read_bytes()).hexdigest(), original)
            # Directory ownership/mtime alone therefore cannot issue a leaf certificate.

    def test_source_semantics_mutation_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in audit.SOURCES:
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((audit.ROOT / name).read_bytes())
            path = root / audit.PARSER
            path.write_text(path.read_text().replace('if (!scanfile->seen)', 'if (0)', 1))
            with self.assertRaisesRegex(ValueError, 'semantics changed'): audit.audit(root)

    def test_source_link_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); path = root / audit.PARSER
            path.parent.mkdir(parents=True); path.symlink_to(audit.ROOT / audit.PARSER)
            with self.assertRaisesRegex(ValueError, 'linked audit source'): audit.audit(root)

    def test_extractor_preserves_actual_function_without_comment_braces(self):
        text = 'int x() { /* } */ const char *s="{"; // }\n if (s) {return 1;} return 0;}\n'
        self.assertEqual(audit.function(text, 'int x()'), text.rstrip())


if __name__ == '__main__': unittest.main()
