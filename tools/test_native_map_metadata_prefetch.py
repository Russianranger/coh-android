#!/usr/bin/env python3
"""Compile extracted retained/candidate Map BIN freshness functions for parity.

The native fixture models ordinary FolderCache metadata and file-list inputs.
It does not execute a world, read animation payloads, or measure startup savings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import map_startup_namespace_certificate as namespace
import prepare_native_map_metadata_prefetch_source as native
import prepare_native_startup_profile_source as profile

SIGNATURE = 'SimpleBufHandle ParserIsPersistNewer('
HELPER_SIGNATURE = 'static void cohMapPreloadSequencerDependencies('
CALL = '    cohMapPreloadSequencerDependencies(dir, filemask, persistfile);\n'
PASS = 'COH_MAP_METADATA_PREFETCH_EQUIVALENCE_PASS'
COMPILER_OPTIONS = ['/O2', '/Oy-', '/MT', '/TC']
HOST_COMPILER_OPTIONS = ['-std=c11', '-D_POSIX_C_SOURCE=200809L', '-O2']
SCENARIO_COUNT = 16
FLAG_COUNT = 8
TUPLE_COUNT = 252


def source_pair():
    original = profile.parser_source(profile.source_bytes(profile.PARSER))
    return original.decode(), native.patch_source(original).decode()


def harness(candidate_source=None):
    """Extract real source bodies; only their external dependencies are doubles."""
    original, candidate = source_pair()
    if candidate_source is not None:
        candidate = candidate_source
    old = namespace.function(original, SIGNATURE).replace(
        'ParserIsPersistNewer(', 'stock_freshness(', 1)
    new = namespace.function(candidate, SIGNATURE).replace(
        'ParserIsPersistNewer(', 'candidate_freshness(', 1)
    helper = namespace.function(candidate, HELPER_SIGNATURE)
    prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#ifdef _WIN64
#error This fixture requires the real Win32 compiler target
#endif
#else
typedef uint32_t DWORD;
typedef int32_t __time32_t;
static DWORD GetTickCount(void) { return 0; }
#endif
#define true 1
#define PARSE_SIG "Parse6"
#define verbose_printf(...) ((void)0)
#define COH_MAP_BIN_DECLARE() ((void)0)
#define COH_MAP_BIN_BEGIN(...) ((void)0)
#define COH_MAP_BIN_PHASE(...) ((void)0)
#define COH_MAP_BIN_FINISH(...) ((void)0)
typedef int SimpleBufHandle;
typedef int ParseTable;
typedef int DefineContext;
typedef struct FileEntry { char path[260]; __time32_t date; int seen; } FileEntry;
typedef FileEntry **FileList;
typedef struct FolderCache { int marker; } FolderCache;
static FolderCache owned_cache;
FolderCache *folder_cache = &owned_cache;
static FileList lf_filedates;
static FileEntry entries[7], scanned[3];
static FileEntry *entry_ptrs[7], *scan_ptrs[3];
static const char * const g_StdAdditionalFilePrefixes[] = {"v_", "d_", ""};
static const __time32_t base_date = 1767225600;
enum Scenario {
    VALID, OPEN_MISSING, BAD_CRC, BAD_HEADER, PRODUCTION,
    SCANNED_CHANGED, DEPENDENCY_CHANGED, DEPENDENCY_REMOVED,
    SCANNED_ADDED, SCANNED_REMOVED, DST_DEPENDENCY, NULL_CACHE,
    PRODUCTION_OPEN_MISSING, PRODUCTION_BAD_CRC, PRODUCTION_BAD_HEADER,
    PRODUCTION_CHANGED, SCENARIO_COUNT
};
enum Operation {
    CRC, PRODUCTION_CHECK, OPEN, TELL, HEADER, CREATE, SCAN, SIZE, FIND,
    DATE_CHECK, DISK_DATE, EXISTS, INSERT, DESTROY, SEEK, CLOSE
};
typedef struct Operations {
    unsigned int crc, production_checks, opens, tells, headers, creates, scans;
    unsigned int sizes, finds, checks, dates, exists, inserts, destroys, seeks, closes;
} Operations;
static Operations operations;
static int scenario, scan_count, production, open_ok, stored_crc, read_ok;
static int header_succeeded, tree_requested, direct_helper;
static unsigned int request_count, uncached_metadata_lookups;
static int trace[512], trace_count;
static void operation(int event) { assert(trace_count<512); trace[trace_count++]=event; }
static int ParseTableCRC(ParseTable *p, DefineContext *d) {
    assert(!p&&!d);operation(CRC);operations.crc++;return 7;
}
static int isProductionMode(void) {
    operation(PRODUCTION_CHECK);operations.production_checks++;return production;
}
static int SerializeReadOpen(const char *path,const char *signature,int crc,int prod) {
    assert(!strcmp(path,"bin/sequencers.bin")&&!strcmp(signature,PARSE_SIG));
    assert(crc==7&&prod==production);operation(OPEN);operations.opens++;
    return open_ok&&stored_crc==crc?37:0;
}
static int SimpleBufTell(int file) { assert(file==37);operation(TELL);operations.tells++;return 12; }
static int FileListRead(FileList *list,int file) {
    assert(file==37);operation(HEADER);operations.headers++;
    *list=entry_ptrs;header_succeeded=read_ok;return read_ok;
}
static void FileListCreate(FileList *list) {
    assert(header_succeeded);operation(CREATE);operations.creates++;*list=scan_ptrs;
}
static int eaSize(FileList *list) {
    operation(SIZE);operations.sizes++;
    return *list==entry_ptrs?7:*list==scan_ptrs?scan_count:0;
}
static int DateCheckCallback(void) { return 1; }
static void fileScanAllDataDirs(const char *path,int (*callback)(void)) {
    assert(!strcmp(path,"sequencers")&&callback==DateCheckCallback);
    operation(SCAN);operations.scans++;
}
static void FileListInsert(FileList *list,const char *path,int date) {
    (void)list;(void)path;(void)date;operation(INSERT);operations.inserts++;
}
static char *addFilePrefix(const char *path,const char *prefix) { (void)prefix;return (char *)path; }
static FileEntry *FileListFind(FileList *list,char *path) {
    int i,n;operation(FIND);operations.finds++;n=eaSize(list);
    for(i=0;i<n;i++)if(!strcmp((*list)[i]->path,path))return (*list)[i];
    return NULL;
}
static int fileDatesEqual(int left,int right,int dst) {
    assert(dst==true);operation(DATE_CHECK);operations.checks++;
    return left==right||(dst&&(left-right==3600||right-left==3600));
}
static __time32_t fileLastChanged(const char *path) {
    operation(DISK_DATE);operations.dates++;
    if(!tree_requested&&!strncmp(path,"player_library/animations/",26))uncached_metadata_lookups++;
    if(scenario==SCANNED_REMOVED&&!strcmp(path,"sequencers/human.txt"))return 0;
    if(scenario==DEPENDENCY_REMOVED&&!strcmp(path,entries[6].path))return 0;
    if((scenario==DEPENDENCY_CHANGED||scenario==PRODUCTION_CHANGED)&&!strcmp(path,entries[6].path))
        return base_date+10;
    return base_date;
}
static int fileExists(const char *path) { (void)path;operation(EXISTS);operations.exists++;return 1; }
static void FileListDestroy(FileList *list) { operation(DESTROY);operations.destroys++;*list=NULL; }
static void SimpleBufSeek(int file,int position,int origin) {
    assert(file==37&&position==12&&origin==SEEK_SET);operation(SEEK);operations.seeks++;
}
static void SerializeClose(int file) { assert(file==37);operation(CLOSE);operations.closes++; }
static void FolderCacheRequestTree(FolderCache *cache,const char *path) {
    assert(cache==&owned_cache&&!strcmp(path,"player_library/animations"));
    if(!direct_helper) {
        assert(open_ok&&stored_crc==7&&header_succeeded&&!production);
        assert(operations.headers==1&&!operations.checks&&!operations.dates&&!operations.finds);
        assert(!operations.seeks&&!operations.closes);
    }
    assert(!request_count);request_count++;tree_requested=1;
}
'''
    tail = r'''
static void enable(const char *value) {
#ifdef _WIN32
    assert(_putenv_s("COH_MAP_ANIMATION_METADATA_PREFETCH",value?value:"")==0);
#else
    assert((value?setenv("COH_MAP_ANIMATION_METADATA_PREFETCH",value,1):
        unsetenv("COH_MAP_ANIMATION_METADATA_PREFETCH"))==0);
#endif
}
static void reset(int value) {
    int i;scenario=value;scan_count=2;production=0;open_ok=read_ok=1;stored_crc=7;
    header_succeeded=tree_requested=direct_helper=trace_count=0;
    request_count=uncached_metadata_lookups=0;folder_cache=&owned_cache;lf_filedates=NULL;
    memset(&operations,0,sizeof(operations));memset(trace,0,sizeof(trace));
    memset(entries,0,sizeof(entries));memset(scanned,0,sizeof(scanned));
    strcpy(entries[0].path,"sequencers/human.txt");strcpy(entries[1].path,"sequencers/critter.txt");
    for(i=2;i<7;i++)sprintf(entries[i].path,"player_library/animations/a%04d.anim",i);
    for(i=0;i<7;i++){entries[i].date=base_date;entry_ptrs[i]=&entries[i];}
    for(i=0;i<2;i++)scanned[i]=entries[i];
    for(i=0;i<3;i++)scan_ptrs[i]=&scanned[i];
    if(value==OPEN_MISSING||value==PRODUCTION_OPEN_MISSING)open_ok=0;
    if(value==BAD_CRC||value==PRODUCTION_BAD_CRC)stored_crc=8;
    if(value==BAD_HEADER||value==PRODUCTION_BAD_HEADER)read_ok=0;
    if(value==PRODUCTION||value>=PRODUCTION_OPEN_MISSING)production=1;
    if(value==SCANNED_CHANGED)scanned[0].date++;
    if(value==SCANNED_ADDED){scan_count=3;strcpy(scanned[2].path,"sequencers/added.txt");scanned[2].date=base_date;}
    if(value==SCANNED_REMOVED){scan_count=1;scanned[0]=entries[1];}
    if(value==DST_DEPENDENCY)entries[6].date+=3600;
    if(value==NULL_CACHE)folder_cache=NULL;
}
static int accepted(int value) {
    return value==VALID||value==PRODUCTION||value==DST_DEPENDENCY||value==NULL_CACHE||
        value==PRODUCTION_BAD_HEADER||value==PRODUCTION_CHANGED;
}
int main(void) {
    int value,flag;unsigned int cases=0,tuple_cases=0;
    const char *values[]={NULL,"0","01","1","10","true"," 1","1 "};
#ifdef _WIN32
    assert(sizeof(void*)==4);
#endif
    for(value=0;value<SCENARIO_COUNT;value++)for(flag=0;flag<8;flag++) {
        int stock,candidate,stock_trace[512],stock_count,want_request;
        Operations stock_operations;
        reset(value);enable(values[flag]);
        stock=stock_freshness("sequencers",".txt","bin/sequencers.bin",NULL,NULL);
        assert(stock==(accepted(value)?37:0));assert(!request_count);
        assert(operations.crc==1&&operations.opens==1);
        if(!open_ok||stored_crc!=7)assert(!operations.headers&&!operations.closes&&!operations.seeks);
        else if(production)assert(!operations.headers&&!operations.checks&&!operations.closes&&!operations.seeks);
        else assert(operations.headers==1&&operations.seeks==(unsigned int)accepted(value)&&
            operations.closes==(unsigned int)!accepted(value));
        if(value==VALID)assert(operations.checks==7&&operations.dates==5&&uncached_metadata_lookups==5);
        stock_operations=operations;stock_count=trace_count;memcpy(stock_trace,trace,sizeof(trace));
        reset(value);enable(values[flag]);
        candidate=candidate_freshness("sequencers",".txt","bin/sequencers.bin",NULL,NULL);
        assert(stock==candidate&&!memcmp(&stock_operations,&operations,sizeof(operations)));
        assert(stock_count==trace_count&&!memcmp(stock_trace,trace,sizeof(trace)));
        want_request=flag==3&&open_ok&&stored_crc==7&&read_ok&&!production&&folder_cache!=NULL;
        assert(request_count==(unsigned int)want_request);
        if(value==VALID)assert(operations.checks==7&&operations.dates==5&&
            uncached_metadata_lookups==(unsigned int)(flag==3?0:5));
        cases++;
    }
    {
        const char *dirs[]={NULL,"sequencers","sequencers/","Sequencers","server/sequencers","defs/powers/"};
        const char *masks[]={NULL,".txt",".TXT","txt",".txtx",".powers"};
        const char *bins[]={NULL,"bin/sequencers.bin","bin/Sequencers.bin","sequencers.bin",
            "server/bin/sequencers.bin","bin/sequencers.BIN","bin/powers.bin"};
        int i,j,k;enable("1");
        for(i=0;i<6;i++)for(j=0;j<6;j++)for(k=0;k<7;k++) {
            reset(VALID);direct_helper=1;
            cohMapPreloadSequencerDependencies(dirs[i],masks[j],bins[k]);
            assert(request_count==(unsigned int)(i==1&&j==1&&k==1));tuple_cases++;
        }
    }
    enable(NULL);
    printf("COH_MAP_METADATA_PREFETCH_EQUIVALENCE_PASS scenarios=%d flags=8 cases=%u tuple_cases=%u pointer_bits=%u\n",
        SCENARIO_COUNT,cases,tuple_cases,(unsigned int)(8*sizeof(void*)));
    return 0;
}
'''
    return prefix + helper + '\n' + old + '\n' + new + '\n' + tail


def compile_and_run(code, directory, windows=False):
    compiler = shutil.which('cl' if windows else 'cc')
    namespace.require(compiler, 'Win32 cl compiler required' if windows else 'Native C compiler required')
    root = Path(directory)
    source, executable = root/'fixture.c', root/('fixture.exe' if windows else 'fixture')
    source.write_text(code, encoding='utf-8', newline='\n')
    options = COMPILER_OPTIONS if windows else HOST_COMPILER_OPTIONS
    command = ([compiler, *options, str(source), '/Fe:'+str(executable)] if windows else
               [compiler, *options, str(source), '-o', str(executable)])
    build = subprocess.run(command, cwd=root, capture_output=True, text=True)
    namespace.require(build.returncode == 0, 'Metadata prefetch fixture compile failed: '+build.stdout+build.stderr)
    run = subprocess.run([str(executable)], cwd=root, capture_output=True, text=True)
    return compiler, source, executable, build, run


def execute(require_windows=False, output=None):
    """Return source-bound fixture evidence; Windows runs retain the executable."""
    windows = os.name == 'nt'
    namespace.require(not require_windows or windows, 'Real Windows native qualification required')
    namespace.require(not windows or output is not None, 'Windows fixture evidence output path required')
    code = harness()
    recipe = native.expected_receipt()
    with tempfile.TemporaryDirectory(prefix='coh-map-metadata-prefetch-') as temporary:
        compiler, source, executable, build, run = compile_and_run(code, temporary, windows)
        pattern = (rf'{PASS} scenarios={SCENARIO_COUNT} flags={FLAG_COUNT} '
                   rf'cases={SCENARIO_COUNT*FLAG_COUNT} tuple_cases={TUPLE_COUNT} pointer_bits=(32|64)')
        match = re.search(pattern, run.stdout)
        namespace.require(run.returncode == 0 and match is not None,
                          'Actual Map metadata prefetch fixture failed: '+run.stdout+run.stderr)
        pointer_bits = int(match.group(1))
        namespace.require(not windows or pointer_bits == 32, 'Win32 fixture pointer width required')
        receipt = {
            'format': 1, 'status': 'passed', 'platform': 'windows' if windows else sys.platform,
            'architecture': 'Win32' if windows else str(pointer_bits)+'-bit-host',
            'configuration': 'OptDebug' if windows else 'portable_C_fixture',
            'compiler': Path(compiler).name,
            'compiler_options': COMPILER_OPTIONS if windows else HOST_COMPILER_OPTIONS,
            'build_input': recipe, 'harness_sha256': hashlib.sha256(code.encode()).hexdigest(),
            'fixture_binary_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
            'scope': 'extracted_actual_freshness_and_prefetch_with_external_IO_test_doubles',
            'scenario_count': SCENARIO_COUNT, 'flag_count': FLAG_COUNT,
            'cases': SCENARIO_COUNT*FLAG_COUNT,
            'equivalence_cases': SCENARIO_COUNT*FLAG_COUNT, 'exact_tuple_cases': TUPLE_COUNT,
            'equivalence_verified': True, 'operation_order_and_counts_verified': True,
            'after_header_before_checks_verified': True, 'opt_in_and_fallback_verified': True,
            'exact_scope_verified': True, 'freshness_failure_branches_verified': True,
            'ordinary_source_mutation_detection_verified': True,
            'existing_production_behavior_preserved': True, 'observer_macros_are_noops': True,
            'metadata_lookup_model_only': True, 'animation_payload_reads_exercised': False,
            'native_windows_executed': windows, 'native_wine_executed': False,
            'world_startup_executed': False, 'physical_device_executed': False,
            'physical_startup_savings_validated': False, 'publication_allowed': False,
        }
        if output is not None:
            target = Path(output)
            target.parent.mkdir(parents=True, exist_ok=True)
            stem = target.stem
            evidence = {
                stem+'.fixture.c': source.read_bytes(),
                stem+('.fixture.exe' if windows else '.fixture'): executable.read_bytes(),
                stem+'.build.log': (build.stdout+build.stderr).encode(),
                stem+'.stdout.txt': run.stdout.encode(),
                stem+'.stderr.txt': run.stderr.encode(),
            }
            receipt['evidence'] = {}
            for name, data in evidence.items():
                (target.parent/name).write_bytes(data)
                receipt['evidence'][name] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
            target.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        return receipt


class NativeMapMetadataPrefetchTests(unittest.TestCase):
    def test_actual_freshness_decisions_operation_order_and_opt_in_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = execute(output=Path(temporary)/'checks.json')
            self.assertEqual(receipt['equivalence_cases'], 128)
            self.assertEqual(receipt['exact_tuple_cases'], 252)
            self.assertTrue(receipt['after_header_before_checks_verified'])
            self.assertFalse(receipt['physical_startup_savings_validated'])
            self.assertEqual(receipt['build_input'], native.expected_receipt())
            self.assertEqual(receipt['harness_sha256'], hashlib.sha256(harness().encode()).hexdigest())
            for name, pin in receipt['evidence'].items():
                data = (Path(temporary)/name).read_bytes()
                self.assertEqual(pin, {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})

    def test_retained_freshness_function_and_source_are_exact_except_additions(self):
        original, candidate = source_pair()
        self.assertEqual(native.SOURCE, profile.PARSER)
        old = namespace.function(original, SIGNATURE)
        new = namespace.function(candidate, SIGNATURE)
        self.assertEqual(new.count(CALL), 1)
        self.assertEqual(new.replace(CALL, '', 1), old)
        helper = namespace.function(candidate, HELPER_SIGNATURE)
        # An exact full-source reverse comparison also covers includes and callers.
        self.assertEqual(candidate.replace(native.HELPER, '', 1).replace(CALL, '', 1), original)
        for signature in ('int ParseTableCRC(', 'int ParserReadBinaryTable(',
                          'int ParserReadBinaryFile(', 'static FileScanAction DateCheckCallback('):
            self.assertEqual(namespace.function(original, signature), namespace.function(candidate, signature))
        ordered = ['crc = ParseTableCRC(', 'binfile = SerializeReadOpen(',
                   'if(isProductionMode())', 'if (!FileListRead(', 'goto IsPersist_Fail;',
                   CALL.strip(), 'FileListCreate(', 'fileDatesEqual(', 'fileLastChanged(',
                   '// check that top-level files', 'SimpleBufSeek(', 'SerializeClose(']
        positions = [new.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(helper.count('FolderCacheRequestTree('), 1)
        for forbidden in ('fileOpen(', 'SerializeReadOpen(', 'malloc(', 'ParserReadBinary',
                          'isProductionMode(', 'COH_CLIENT_DEPENDENCY_PRELOAD'):
            self.assertNotIn(forbidden, helper)

    def test_recipe_binds_exact_source_and_keeps_runtime_claims_unverified(self):
        original, candidate = source_pair()
        receipt = native.expected_receipt()
        self.assertEqual(receipt['source_sha256'][native.SOURCE], hashlib.sha256(original.encode()).hexdigest())
        self.assertEqual(receipt['patched_sha256'][native.SOURCE], hashlib.sha256(candidate.encode()).hexdigest())
        self.assertEqual(receipt['environment'], {'name': 'COH_MAP_ANIMATION_METADATA_PREFETCH',
                         'enabled_value': '1', 'disabled_by_default': True})
        self.assertEqual(receipt['exact_request'], {'directory': 'sequencers', 'filemask': '.txt',
                         'persistfile': 'bin/sequencers.bin', 'tree': 'player_library/animations'})
        self.assertEqual(receipt['build_targets'], ['MapServer'])
        for key in ('publication_allowed', 'shipping_allowed', 'native_execution_validated',
                    'physical_savings_validated', 'new_asset_bytes_preloaded', 'persistent_cache_authority_added'):
            self.assertFalse(receipt[key])
        for name, pin in receipt['retained_callsites_sha256'].items():
            self.assertEqual(pin, hashlib.sha256(profile.source_bytes(name)).hexdigest())
        self.assertIn('ParserLoadFiles("sequencers", ".txt", "sequencers.bin",',
                      profile.source_bytes(profile.SEQUENCER).decode())

    def test_changed_or_repeated_source_rejected(self):
        original, candidate = source_pair()
        mutations = [original+'\n', candidate,
                     original.replace('crc = ParseTableCRC(pti, defines);', 'crc = 0;', 1),
                     original.replace('fileDatesEqual(scanfile->date, binfile->date, true)', '1', 1),
                     original.replace('SimpleBufSeek(binfile, savedpos, SEEK_SET);', '(void)binfile;', 1)]
        for changed in mutations:
            with self.subTest(sha256=hashlib.sha256(changed.encode()).hexdigest()):
                self.assertNotEqual(changed, original)
                with self.assertRaisesRegex(ValueError, 'Exact observed retained Map parser'):
                    native.patch_source(changed.encode())

    def test_fixture_rejects_missing_request_early_request_and_skipped_checks(self):
        _, candidate = source_pair()
        without_call = candidate.replace(CALL, '', 1)
        early = without_call.replace('    if (!FileListRead(&binlist, binfile))\n',
                                     CALL+'    if (!FileListRead(&binlist, binfile))\n', 1)
        skip_check = candidate.replace('if (!fileDatesEqual(scanfile->date, binfile->date, true))',
                                       'if (0)', 1)
        for name, changed in [('missing_request', without_call), ('before_header', early),
                              ('skipped_date_check', skip_check)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                self.assertNotEqual(changed, candidate)
                _, _, _, _, run = compile_and_run(harness(changed), temporary, os.name == 'nt')
                self.assertNotEqual(run.returncode, 0)
                self.assertNotIn(PASS, run.stdout)

    def test_real_windows_requirement_is_not_satisfied_by_host_fixture(self):
        if os.name != 'nt':
            with self.assertRaisesRegex(ValueError, 'Real Windows'):
                execute(require_windows=True, output='unused.json')


if __name__ == '__main__':
    if '--windows-qualify' in sys.argv or '--output' in sys.argv:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--windows-qualify', action='store_true')
        parser.add_argument('--output', type=Path, required=True)
        args = parser.parse_args()
        print(json.dumps(execute(args.windows_qualify, args.output), sort_keys=True))
    else:
        unittest.main()
