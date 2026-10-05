"""Compile the actual stock/candidate BIN freshness bodies and dependency guard."""
import argparse
import copy
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(Path(__file__).parent), str(ROOT/'tools')]
import package_client_startup_followup_native as native


def harness():
    original, current = native.patched_text()
    old = native.function(original, 'SimpleBufHandle ParserIsPersistNewer(').replace('ParserIsPersistNewer(', 'stock_freshness(', 1)
    new = native.function(current, 'SimpleBufHandle ParserIsPersistNewer(').replace('ParserIsPersistNewer(', 'candidate_freshness(', 1)
    helper = native.function(current, 'static void cohClientPreloadDependencies(')
    prefix = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <assert.h>
#include <stdint.h>
#define true 1
#ifdef _WIN32
#include <windows.h>
#ifdef _WIN64
#error Real Win32 native qualification required
#endif
#else
typedef uint32_t DWORD;
static DWORD GetTickCount(void) { return 0; }
#endif
typedef int SimpleBufHandle;
typedef int ParseTable;
typedef int DefineContext;
#ifndef _WIN32
typedef int32_t __time32_t;
#endif
typedef struct FileEntry { char path[260]; __time32_t date; int seen; } FileEntry;
typedef FileEntry **FileList;
typedef struct FolderCache { int marker; } FolderCache;
static FolderCache owned_cache;
FolderCache *folder_cache = &owned_cache;
static FileList lf_filedates;
static FileEntry entries[4541], scanned[2];
static FileEntry *entry_ptrs[4541], *scan_ptrs[2];
static int count, scan_count, production, open_ok, read_ok, bad_disk, removed_disk;
static unsigned int queries, menu_tree, animation_tree, request_count, checks, seeks, closes;
static const char * const g_StdAdditionalFilePrefixes[] = {"v_", "d_", ""};
#define PARSE_SIG "Parse6"
#define SEEK_SET 0
#define verbose_printf(...) ((void)0)
static int cohClientLoadingFlags(void) { return 0; }
static void cohClientBinProfile(const char*a,const char*b,DWORD c,int d,unsigned int e) {(void)a;(void)b;(void)c;(void)d;(void)e;}
static int ParseTableCRC(ParseTable*p,DefineContext*d) {(void)p;(void)d;return 7;}
static int isProductionMode(void) { return production; }
static int SerializeReadOpen(const char*p,const char*s,int c,int prod) {(void)p;(void)s;assert(c==7);(void)prod;return open_ok;}
static int SimpleBufTell(int f) {(void)f;return 12;}
static int FileListRead(FileList*p,int f) {(void)f;*p=entry_ptrs;return read_ok;}
static void FileListCreate(FileList*p) {*p=scan_ptrs;}
static int eaSize(FileList*p) {return *p==entry_ptrs?count:*p==scan_ptrs?scan_count:0;}
static int DateCheckCallback(void) {return 1;}
static void fileScanAllDataDirs(const char*p,int(*callback)(void)) {(void)p;assert(callback==DateCheckCallback);}
static void FileListInsert(FileList*p,const char*path,int date) {(void)p;(void)path;(void)date;}
static char *addFilePrefix(const char*p,const char*prefix) {(void)prefix;return (char*)p;}
static FileEntry *FileListFind(FileList*p,char*path) {
    int i,n=eaSize(p); for(i=0;i<n;i++)if(!strcmp((*p)[i]->path,path))return (*p)[i];return NULL;
}
static int fileDatesEqual(int a,int b,int dst) {checks++;return a==b||(dst&&(a-b==3600||b-a==3600));}
static __time32_t fileLastChanged(const char*p) {
    if(!menu_tree)queries++;
    if(removed_disk&&!strcmp(p,entries[count-1].path))return 0;
    if(bad_disk&&!strcmp(p,entries[count-1].path))return 1767225610;
    return 1767225600;
}
static int fileExists(const char*p) {(void)p;return 1;}
static void FileListDestroy(FileList*p) {*p=NULL;}
static void SimpleBufSeek(int f,int p,int whence) {(void)f;assert(p==12&&whence==SEEK_SET);seeks++;}
static void SerializeClose(int f) {(void)f;closes++;}
static void FolderCacheRequestTree(FolderCache*fc,const char*path) {
    assert(fc==&owned_cache);request_count++;
    if(!strcmp(path,"Menu"))menu_tree=1;
    else {assert(!strcmp(path,"player_library/animations"));animation_tree=1;}
}
'''
    tail = r'''
static void enable(const char *value) {
#ifdef _WIN32
    _putenv_s("COH_CLIENT_DEPENDENCY_PRELOAD",value?value:"");
#else
    if(value)setenv("COH_CLIENT_DEPENDENCY_PRELOAD",value,1);else unsetenv("COH_CLIENT_DEPENDENCY_PRELOAD");
#endif
}
static void reset(int scenario) {
    int i;count=4540;scan_count=1;queries=menu_tree=animation_tree=request_count=checks=seeks=closes=0;
    open_ok=read_ok=1;production=bad_disk=removed_disk=0;folder_cache=&owned_cache;
    memset(entries,0,sizeof(entries));memset(scanned,0,sizeof(scanned));
    strcpy(entries[0].path,"defs/powers/ordinary.powers");entries[0].date=1767225600;
    scanned[0]=entries[0];scan_ptrs[0]=&scanned[0];scan_ptrs[1]=&scanned[1];
    for(i=1;i<count;i++) {sprintf(entries[i].path,"Menu/Powers/AnimFX/p%04d.pfx",i);entries[i].date=1767225600;}
    for(i=0;i<count;i++)entry_ptrs[i]=&entries[i];
    if(scenario==1)open_ok=0;
    if(scenario==2)read_ok=0;
    if(scenario==3)production=1;
    if(scenario==4)scanned[0].date++;
    if(scenario==5)bad_disk=1;
    if(scenario==6)removed_disk=1;
    if(scenario==7){scan_count=2;strcpy(scanned[1].path,"defs/powers/added.powers");scanned[1].date=1767225600;}
    if(scenario==8)entries[count-1].date=1767229200;
    if(scenario==9)folder_cache=NULL;
}
int main(void) {
#ifdef _WIN32
    assert(sizeof(void*) == 4);
#endif
    int scenario,flag;const char *values[]={NULL,"0","01","1"};
    for(scenario=0;scenario<10;scenario++)for(flag=0;flag<4;flag++) {
        int stock,candidate,stock_checks,stock_seek,stock_close;
        reset(scenario);enable(values[flag]);stock=stock_freshness("defs/powers/",".powers","bin/powers.bin",NULL,NULL);
        stock_checks=checks;stock_seek=seeks;stock_close=closes;
        if(!scenario)assert(queries==4539);
        reset(scenario);enable(values[flag]);candidate=candidate_freshness("defs/powers/",".powers","bin/powers.bin",NULL,NULL);
        assert(stock==candidate&&stock_checks==checks&&stock_seek==seeks&&stock_close==closes);
        if(flag==3&&scenario!=1&&scenario!=2&&scenario!=3&&scenario!=9)assert(menu_tree==1&&request_count==1);
        else assert(request_count==0);
        if(!scenario&&flag==3)assert(queries==0&&checks==4540);
    }
    {
        const char *dirs[]={NULL,"Defs","defs/","sequencers","defs/powers/"};
        const char *masks[]={NULL,".Powers",".powersets",".txt",".powers"};
        const char *bins[]={NULL,"bin/Powers.bin","server/bin/powers.bin","bin/sequencers.bin","bin/powers.bin"};
        int i,j,k;enable("1");
        for(i=0;i<5;i++)for(j=0;j<5;j++)for(k=0;k<5;k++) {
            reset(0);cohClientPreloadDependencies(dirs[i],masks[j],bins[k]);
            assert(request_count==((i==4&&j==4&&k==4)||(i==3&&j==3&&k==3)));
        }
    }
    enable(NULL);
    puts("COH_PRELOAD_NATIVE_EQUIVALENCE_PASS individual_fallback_queries=4539 candidate_tree_requests=1");
    return 0;
}
'''
    return prefix+helper+'\n'+old+'\n'+new+'\n'+tail


def execute(require_windows=False, output=None):
    if require_windows:
        if os.name!='nt':raise ValueError('Real Windows native qualification required')
        compiler=shutil.which('cl');native.require(compiler,'Win32 cl compiler required')
    else:
        compiler=shutil.which('cc');native.require(compiler,'Native C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-preload-native-') as temporary:
        root=Path(temporary); source=root/'harness.c';exe=root/('harness.exe' if require_windows else 'harness')
        source.write_text(harness())
        command=([compiler,*native.COMPILER_OPTIONS,str(source),'/Fe:'+str(exe)] if require_windows
                 else [compiler,'-std=c11','-D_POSIX_C_SOURCE=200809L','-O2',str(source),'-o',str(exe)])
        subprocess.run(command,cwd=root,check=True,capture_output=True)
        run=subprocess.run([str(exe)],cwd=root,check=True,capture_output=True,text=True)
        native.require('COH_PRELOAD_NATIVE_EQUIVALENCE_PASS individual_fallback_queries=4539 candidate_tree_requests=1' in run.stdout,
                       'Actual freshness/preload harness did not pass')
    if require_windows:
        receipt={'format':1,'status':'passed','platform':'windows','architecture':'Win32','configuration':'OptDebug',
            'compiler_options':native.COMPILER_OPTIONS,'build_input':native.expected_receipt(),
            'harness_sha256':hashlib.sha256(harness().encode()).hexdigest(),
            'equivalence_verified':True,'opt_in_and_fallback_verified':True,'exact_scope_verified':True,
            'freshness_failure_branches_verified':True,'metadata_lookup_reduction_verified':True,
            'ordinary_source_mutation_detection_verified':True,'physical_startup_savings_validated':False,
            'individual_fallback_queries':4539,'candidate_tree_requests':1}
        native.validate_checks(receipt)
        Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(receipt,indent=2)+'\n')
        return receipt
    return run.stdout


class ClientStartupFollowupNativeTests(unittest.TestCase):
    def test_exact_freshness_crc_and_decoder_preserved(self):
        receipt=native.expected_receipt()
        self.assertTrue(receipt['freshness_body_exact_except_preload_call'])
        self.assertTrue(receipt['reverse_patch_exact_base_verified'])
        self.assertEqual(receipt['source_sha256'],native.base.expected_receipt()['patched_sha256'])
        self.assertFalse(receipt['dependency_preload']['full_asset_bytes_preloaded'])

    def test_guards_match_actual_native_callsite_paths(self):
        receipt = native.expected_receipt()
        self.assertEqual(set(receipt['native_callsite_sources_sha256']), {
            'Common/entity/load_def.c', 'Common/entity/powers_load.c', 'Common/seq/seqload.c',
            'libs/UtilitiesLib/src/utils/FolderCache.c', 'libs/UtilitiesLib/src/utils/FolderCacheNode.c',
            'libs/UtilitiesLib/src/utils/file.c'})
        self.assertEqual(receipt['dependency_preload']['requests'][0]['directory'], 'defs/powers/')
        _, current = native.patched_text()
        helper = native.function(current, 'static void cohClientPreloadDependencies(')
        self.assertIn('strcmp(dir, "defs/powers/")', helper)
        node = (native.ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCacheNode.c').read_text()
        self.assertIn('update= !((timestamp == node->timestamp) || (timestamp - node->timestamp)==3600);', node)
        self.assertIn('node2->seen_in_fs = 1;', node)

    def test_actual_freshness_body_matches_and_mutations_fail(self):
        self.assertIn('COH_PRELOAD_NATIVE_EQUIVALENCE_PASS',execute())

    def test_real_source_layer_rejects_repeated_or_changed_input(self):
        import test_startup_bundle_client as fixtures
        with tempfile.TemporaryDirectory() as temporary:
            fixture = fixtures.StartupBundleClientTests(); fixture.root = Path(temporary)
            source = fixture.frozen_source()
            native.base.base.apply_overlay(source)
            native.base.apply_overlay(source)
            for name in native.expected_receipt()['native_callsite_sources_sha256']:
                if not (source/name).exists():
                    (source/name).parent.mkdir(parents=True,exist_ok=True)
                    (source/name).write_bytes((native.ROOT/'upstream/ouroboros'/name).read_bytes().replace(b'\r\n',b'\n'))
            import prepare_wine_dbserver_source as wine
            section = next(part for part in re.split(r'(?=^--- a/)',wine.patch_bytes(native.ROOT).decode(),flags=re.M)
                           if part.startswith('--- a/libs/UtilitiesLib/src/utils/FolderCache.c'))
            native.base.apply_patch(source,section.encode())
            before = {name:(source/name).read_bytes() for name in native.base.base.baseline.SCHEMA_FILES if name!=native.FILE}
            receipt = native.apply_overlay(source)
            self.assertEqual(native.validate_source(source)[0],receipt)
            self.assertEqual(before,{name:(source/name).read_bytes() for name in before})
            with self.assertRaisesRegex(ValueError,'receipt exists'):native.apply_overlay(source)
            for name in receipt['native_callsite_sources_sha256']:
                old=(source/name).read_bytes();(source/name).write_bytes(old+b'foreign')
                with self.subTest(name=name),self.assertRaisesRegex(ValueError,'dependency callsite differs'):
                    native.validate_source(source)
                (source/name).write_bytes(old)
            (source/native.FILE).write_bytes((source/native.FILE).read_bytes()+b'foreign')
            with self.assertRaisesRegex(ValueError,'parser source changed'):native.validate_source(source)

    def test_windows_qualification_required(self):
        if os.name!='nt':
            with self.assertRaisesRegex(ValueError,'Windows'):execute(True,'unused')

    def test_preload_does_not_replace_any_loader_or_source(self):
        old,new=native.patched_text()
        oldbody=native.function(old,'SimpleBufHandle ParserIsPersistNewer(')
        newbody=native.function(new,'SimpleBufHandle ParserIsPersistNewer(')
        self.assertEqual(newbody.replace('    cohClientPreloadDependencies(dir, filemask, persistfile);\n\n',''),oldbody)
        helper=native.function(new,'static void cohClientPreloadDependencies(')
        self.assertNotIn('fileOpen',helper)
        self.assertNotIn('malloc',helper)
        self.assertEqual(helper.count('FolderCacheRequestTree('),1)
        self.assertEqual(native.BASE_GAME['sha256'],'ec1a6c01b07d7c189bde743a7255c860b8dd96879225b4ffa50fd42eabbb721b')


if __name__=='__main__':
    if '--windows-qualify' in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument('--windows-qualify',action='store_true');parser.add_argument('--output',required=True)
        args=parser.parse_args();execute(True,args.output)
    else:unittest.main()
