"""Controlled native-call boundaries for the capture-only PIG index bridge."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import native_client_pig_index_capture as parser
import prepare_native_client_metadata_census_source as source
import map_startup_namespace_certificate as namespace

GENERATION = '0' * 64


def harness():
    original = source.source_bytes().decode()
    before = namespace.function(original, 'int FolderCacheAddAllPigs(')
    after = namespace.function(source.patch_source(original.encode()).decode(), 'int FolderCacheAddAllPigs(')
    prefix = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
typedef struct FolderCache {void *nodeCreateCallback,*nodeDeleteCallback;} FolderCache;
typedef struct PigFile {int ordinal,locked;unsigned int count;} PigFile;
static FolderCache owner,*folder_cache=&owner;
static PigFile pigs[2]={{0,0,3},{1,0,2}};
static int mode=1,pig_count=2,gdd_count=1,folder_cache_update_enable,dev_data=1;
static int folder_cache_exclusion,folder_cache_exclusion_folder;
static int adds,locks,unlocks,metadata_calls,scenario,count_queries;
static const char *enable="1",*generation="0000000000000000000000000000000000000000000000000000000000000000";
#define FOLDER_CACHE_MODE_FILESYSTEM_ONLY 4
#define FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC 1
#define FOLDER_CACHE_ALL_FOLDERS 0
#define PIG_INDEX_TO_VIRTUAL_LOCATION(p) (-(p)-1)
static const char *env(const char *name) {
 if(!strcmp(name,"COH_CLIENT_CENSUS_CAPTURE"))return enable;
 assert(!strcmp(name,"COH_CLIENT_CENSUS_CAPTURE_GENERATION"));return generation;
}
#define COH_CAPTURE_ENV env
struct _stat32 {int placeholder;};
static unsigned long fixture_last_error;
static unsigned long GetLastError(void) {return fixture_last_error;}
static void SetLastError(unsigned long value) {fixture_last_error=value;}
void cohClientCensusObserveStatStage(int stage,int succeeded);
static int fake_stat_failure;
static int _AltStat(const char *name,struct _stat32 *value) {(void)name;(void)value;
 cohClientCensusObserveStatStage(1,!fake_stat_failure);
 if(!fake_stat_failure)cohClientCensusObserveStatStage(2,1);
 errno=611;fixture_last_error=612;return fake_stat_failure?-1:0;}
static unsigned long GetCurrentProcessId(void) {return 312;}
static unsigned long fixture_current_thread=77;
static unsigned long GetCurrentThreadId(void) {return fixture_current_thread;}
static int FolderCacheGetMode(void) {return mode;}
static int FolderCache_GetNumGDDs(FolderCache *fc) {(void)fc;return gdd_count;}
static int FolderCache_GetNumPiggs(FolderCache *fc) {(void)fc;return pig_count;}
static const char *FolderCache_GetFromVirtualLocation(FolderCache *fc,int index) {
 (void)fc;return index==0?"c:/qualified/data":index==-1?"c:/qualified/piggs/animations.pigg:":"c:/qualified/piggs/supplement.pigg:";
}
static int fileIsUsingDevData(void) {return dev_data;}
static int PigSetGetNumPigs(void) {return pig_count;}
static PigFile *PigSetGetPigFile(int p) {assert(p>=0&&p<pig_count);return &pigs[p];}
static void FolderCacheAddPig(FolderCache *fc,PigFile *pig,int location) {(void)fc;assert(location==-pig->ordinal-1&&!pig->locked);++adds;}
static void PigFileLock(PigFile *pig) {assert(!pig->locked);pig->locked=1;++locks;}
static void PigFileUnlock(PigFile *pig) {assert(pig->locked);pig->locked=0;++unlocks;}
static unsigned int PigFileGetNumFiles(PigFile *pig) {assert(pig->locked);++count_queries;return pig->count;}
static const char *PigFileGetArchiveFileName(PigFile *pig) {assert(pig->locked);return pig->ordinal?"c:/qualified/piggs/supplement.pigg":"c:/qualified/piggs/animations.pigg";}
static const char *PigFileGetFileName(PigFile *pig,int i) {
 static char long_name[261];assert(pig->locked&&i>=0&&(unsigned int)i<pig->count);
 if(scenario==10){memset(long_name,'x',260);long_name[260]=0;return long_name;}
 if(!pig->ordinal)return i==0?"sequencers/test.anim":i==1?NULL:"?DataList";
 return i==0?"fx/a\"b\\c.fx":"scripts.loc/example.npc";
}
static int PigFileIsSpecialFile(PigFile *pig,int i) {assert(pig->locked);return !pig->ordinal&&i==2;}
static unsigned int PigFileGetFileTimestamp(PigFile *pig,int i) {assert(pig->locked&&PigFileGetFileName(pig,i));++metadata_calls;return 1000u+(unsigned int)i;}
static unsigned int PigFileGetFileSize(PigFile *pig,int i) {assert(pig->locked&&PigFileGetFileName(pig,i));++metadata_calls;return 2000u+(unsigned int)i;}
#include "coh_folder_census_capture.h"
'''
    tail = r'''
int main(int argc,char **argv) {
 int before_adds;
 assert(argc==2);scenario=atoi(argv[1]);
 if(scenario==1)enable="0";
 if(scenario==2)generation="bad";
 if(scenario==3)gdd_count=2;
 if(scenario==4)folder_cache_update_enable=1;
 if(scenario==5)owner.nodeCreateCallback=&owner;
 if(scenario==6)folder_cache=&owner+1;
 if(scenario==7)mode=4;
 if(scenario==8)dev_data=0;
 if(scenario==9)folder_cache_exclusion=1;
 if(scenario==11)pig_count=0;
 if(scenario==12){pig_count=1;pigs[0].count=COH_CAPTURE_MAX_ROWS+1;}
 before_adds=stockAddAllPigs(&owner);assert(before_adds==0);before_adds=adds;adds=0;errno=51;fixture_last_error=52;
 assert(FolderCacheAddAllPigs(&owner)==0);assert(adds==before_adds);
 assert(errno==51&&fixture_last_error==52);
 assert(locks==unlocks&&!pigs[0].locked&&!pigs[1].locked);
 if(scenario==0) {
  struct _stat32 stat_value;int prior;assert(locks==2&&metadata_calls==8&&count_queries==4);
  prior=coh_client_census_stat_scope=3;errno=21;fixture_last_error=22;
  assert(cohFolderCensusObservedAltStat(&owner,"native",&stat_value,"SCRIPTS.LOC/test.npc")==0);
  assert(errno==611&&fixture_last_error==612&&coh_client_census_stat_scope==prior);
  assert(coh_client_census_stat_counts[5].calls==1&&coh_client_census_stat_counts[5].create_calls==1&&coh_client_census_stat_counts[5].info_ok==1);
  assert(cohFolderCensusObservedAltStat(&owner,"native",&stat_value,"scripts.local/test.npc")==0);
  assert(coh_client_census_stat_counts[3].calls==0&&coh_client_census_stat_counts[3].create_calls==0);
  fake_stat_failure=1;assert(cohFolderCensusObservedAltStat(&owner,"native",&stat_value,"fx/failure.fx")==-1);
  assert(errno==611&&fixture_last_error==612&&coh_client_census_stat_scope==prior);
  assert(coh_client_census_stat_counts[3].calls==1&&coh_client_census_stat_counts[3].returns_failed==1);
  errno=31;fixture_last_error=32;cohFolderCensusFlushStatObservations();assert(errno==31&&fixture_last_error==32);
  assert(coh_client_census_flushes==1);
  fixture_current_thread=78;cohFolderCensusFlushStatObservations();assert(coh_client_census_flushes==1);
  fixture_current_thread=77;
 }
 if(scenario>0&&scenario<10)assert(locks==0&&metadata_calls==0);
 fprintf(stderr,"CONTROLLED_CAPTURE_PASS scenario=%d adds=%d locks=%d unlocks=%d metadata_calls=%d\n",scenario,adds,locks,unlocks,metadata_calls);
 return 0;
}
'''
    return prefix + before.replace('FolderCacheAddAllPigs(', 'stockAddAllPigs(') + '\n#define COH_CLIENT_METADATA_CENSUS_CAPTURE 1\n' + after + tail


def execute():
    compiler = shutil.which('cc')
    if not compiler:
        raise ValueError('C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-census-pig-capture-') as temporary:
        root = Path(temporary)
        (root / 'fixture.c').write_text(harness())
        for name in ('coh_folder_census_capture.h', 'coh_folder_census_observation.h'):
            (root / name).write_bytes((source.ROOT / 'database/client-metadata-census/overlay' / name).read_bytes())
        binary = root / 'fixture'
        build = subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-I', str(root), 'fixture.c', '-o', str(binary)], cwd=root, text=True, capture_output=True)
        if build.returncode:
            raise ValueError('Capture fixture compilation failed: ' + build.stdout + build.stderr)
        values = []
        for scenario in range(13):
            run = subprocess.run([str(binary), str(scenario)], text=True, capture_output=True, timeout=5)
            if run.returncode or 'CONTROLLED_CAPTURE_PASS' not in run.stderr:
                raise ValueError('Capture fixture failed: ' + run.stdout + run.stderr)
            values.append({'scenario': scenario, 'stdout': run.stdout, 'stderr': run.stderr})
        return values


class CaptureSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = execute()

    def test_actual_source_hook_retains_stock_initialization_and_disabled_paths(self):
        original = namespace.function(source.source_bytes().decode(), 'int FolderCacheAddAllPigs(')
        patched = namespace.function(source.patch_source(source.source_bytes()).decode(), 'int FolderCacheAddAllPigs(')
        self.assertEqual(patched.replace('#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)\n    cohFolderCensusCapturePigIndex(fc);\n#endif\n', ''), original)
        for row in self.values[1:10]:
            self.assertNotIn(parser.MARKER, row['stdout'])

    def test_complete_native_call_fixture_retains_every_index_and_empty_special_state(self):
        value = parser.parse(self.values[0]['stdout'], GENERATION, 312)
        self.assertEqual(value['end']['rows'], 5)
        self.assertEqual(value['providers'][0]['members_observed'][1]['name'], None)
        self.assertEqual(value['providers'][0]['members_observed'][1]['size'], None)
        self.assertTrue(value['providers'][0]['members_observed'][2]['special'])
        self.assertEqual(value['providers'][1]['members_observed'][0]['name'], 'fx/a"b\\c.fx')
        self.assertFalse(value['native_registration_allowed'])

    def test_zero_provider_index_is_observation_without_authority(self):
        value = parser.parse(self.values[11]['stdout'], GENERATION, 312)
        self.assertEqual(value['providers'], [])
        self.assertFalse(value['archive_bytes_authenticated_by_this_parser'])

    def test_unsupported_name_or_count_preserves_stock_and_rejects_partial_index(self):
        for scenario in (10, 12):
            with self.assertRaises(ValueError):
                parser.parse(self.values[scenario]['stdout'], GENERATION, 312)

    def test_wrong_owner_generation_or_truncated_duplicated_trace_rejected(self):
        console = '\n'.join(line for line in self.values[0]['stdout'].splitlines() if parser.MARKER in line) + '\n'
        for data, generation, pid in ((console, '1' * 64, 312), (console, GENERATION, 313),
                ('\n'.join(console.splitlines()[:-1]), GENERATION, 312), (console + console, GENERATION, 312)):
            with self.assertRaises(ValueError):
                parser.parse(data, generation, pid)

    def test_mutated_member_index_mount_and_field_types_rejected(self):
        events = [json.loads(line.split(parser.MARKER + ' ', 1)[1]) for line in self.values[0]['stdout'].splitlines() if parser.MARKER in line]
        mutations = [(0, 'windows_pid', 312.0), (0, 'gdd_root', 'data\0bad'), (1, 'ordinal', True), (1, 'folder_cache_mount', 'other'), (2, 'file_index', 1),
                     (2, 'size', True), (2, 'special', 1), (-1, 'rows', 4), (-1, 'native_registration_allowed', True)]
        for index, key, changed in mutations:
            values = copy.deepcopy(events); values[index][key] = changed
            console = '\n'.join(parser.MARKER + ' ' + json.dumps(value) for value in values)
            with self.assertRaises(ValueError):
                parser.parse(console, GENERATION, 312)

    def test_embedded_or_wrapped_native_marker_refused(self):
        source_console = '\n'.join(line for line in self.values[0]['stdout'].splitlines() if parser.MARKER in line)
        for prefix in ('unrelated ', 'Game says ', '  '):
            with self.assertRaises(ValueError):
                parser.parse('\n'.join(prefix + line for line in source_console.splitlines()), GENERATION, 312)

    def test_partial_header_has_no_authority_and_native_build_not_inferred(self):
        recipe = source.expected_receipt()
        self.assertFalse(recipe['native_pig_capture_registers_provider_authority'])
        self.assertFalse(recipe['native_windows_executed'])
        self.assertFalse(recipe['native_game_executed'])
        self.assertFalse(recipe['publication_allowed'])
        self.assertIn('scripts.loc', recipe['admitted_branches'])


if __name__ == '__main__':
    unittest.main()
