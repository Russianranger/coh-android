"""Nonshipping observer staging and extracted actual stock-C equivalence."""
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import map_startup_namespace_certificate as namespace
import prepare_map_startup_observer_source as observer
import test_map_startup_namespace_certificate as stock_fixture


WINDOWS_ADAPTER = r'''
#ifndef COH_FIXTURE_WINDOWS_H
#define COH_FIXTURE_WINDOWS_H
typedef struct { long long QuadPart; } LARGE_INTEGER;
static long long fixture_clock;
static long long fixture_frequency=1000000;
static int fixture_clock_fail, fixture_clock_calls, fixture_clock_regress_at;
static int QueryPerformanceFrequency(LARGE_INTEGER *out) {
    out->QuadPart=fixture_frequency; return !fixture_clock_fail;
}
static int QueryPerformanceCounter(LARGE_INTEGER *out) {
    ++fixture_clock_calls;
    fixture_clock += fixture_clock_calls==fixture_clock_regress_at ? -10000 : 1000;
    out->QuadPart=fixture_clock; return !fixture_clock_fail;
}
#endif
'''


def harness(server=True):
    inherited = stock_fixture.harness()
    stock = namespace.function((observer.ROOT / 'upstream/ouroboros' / observer.SOURCE).read_text(),
                               observer.SIGNATURE)
    prefix = inherited[:inherited.index('FolderNode *FolderNodeAdd(')]
    reset = namespace.function(inherited, 'static void reset(')
    reset = reset.replace('    int i;scenario=test;',
                          '    int i;fixture_trace_length=0;fixture_trace[0]=0;scenario=test;', 1)
    tracing = r'''
static char fixture_trace[16384];
static size_t fixture_trace_length;
static void fixtureTrace(const char *label,const char *path,int a,int b) {
    int length=snprintf(fixture_trace+fixture_trace_length,
                       sizeof(fixture_trace)-fixture_trace_length,"%s:%s:%d:%d;",
                       label,path?path:"-",a,b);
    assert(length>=0&&(size_t)length<sizeof(fixture_trace)-fixture_trace_length);
    fixture_trace_length+=(size_t)length;
}
'''
    insertion = 'static int ParseTableCRC('
    prefix = prefix[:prefix.index(insertion)] + tracing + prefix[prefix.index(insertion):]
    # The bounded IO adapters are traced, not replaced by an imitation loader.
    replacements = (
        ('(void)p;(void)d;return 7;', 'fixtureTrace("crc",NULL,7,0);(void)p;(void)d;return 7;'),
        ('static int isProductionMode(void) {return production;}',
         'static int isProductionMode(void) {fixtureTrace("production",NULL,production,0);return production;}'),
        ('(void)p;(void)prod;assert', 'fixtureTrace("open",p,crc,prod);(void)p;(void)prod;assert'),
        ('(void)file;return 12;', 'fixtureTrace("tell",NULL,file,12);(void)file;return 12;'),
        ('(void)file;*list=bin_ptrs;return read_ok;',
         'fixtureTrace("readlist",NULL,file,read_ok);(void)file;*list=bin_ptrs;return read_ok;'),
        ('*list=scan_ptrs;scan_count=0;', 'fixtureTrace("createlist",NULL,0,0);*list=scan_ptrs;scan_count=0;'),
        ('(void)dir;assert(callback==DateCheckCallback);scans++;',
         'fixtureTrace("scan",dir,0,0);(void)dir;assert(callback==DateCheckCallback);scans++;'),
        ('assert(*list==scan_ptrs && scan_count<4);',
         'fixtureTrace("insert",path,date,scan_count);assert(*list==scan_ptrs && scan_count<4);'),
        ('int i;for(i=0;i<eaSize(list);i++)',
         'int i;fixtureTrace("find",path,*list==bin_ptrs?1:2,0);for(i=0;i<eaSize(list);i++)'),
        ('{checks++;return a==b', '{fixtureTrace("dates",NULL,a,b);checks++;return a==b'),
        ('static int fileLastChanged(const char *path) {\n',
         'static int fileLastChanged(const char *path) {\n    fixtureTrace("lastchanged",path,0,0);\n'),
        ('static int fileExists(const char *path) {\n',
         'static int fileExists(const char *path) {\n    fixtureTrace("exists",path,0,0);\n'),
        ('static void FileListDestroy(FileList *list) {*list=NULL;}',
         'static void FileListDestroy(FileList *list) {fixtureTrace("destroy",NULL,*list==bin_ptrs?1:*list==scan_ptrs?2:0,0);*list=NULL;}'),
        ('(void)file;assert(at==12&&whence==SEEK_SET);seeks++;',
         'fixtureTrace("seek",NULL,file,at);(void)file;assert(at==12&&whence==SEEK_SET);seeks++;'),
        ('(void)file;closes++;', 'fixtureTrace("close",NULL,file,0);(void)file;closes++;'),
    )
    for old, new in replacements:
        namespace.require(prefix.count(old) == 1, 'Observer trace adapter anchor differs: ' + old)
        prefix = prefix.replace(old, new, 1)
    logging = r'''
#include <stdarg.h>
static unsigned int fixture_rows;
static char fixture_last_row[1024];
static int fixturePrintf(const char *format,...) {
    va_list args;int length;va_start(args,format);
    length=vsnprintf(fixture_last_row,sizeof(fixture_last_row),format,args);va_end(args);
    assert(length>0&&(size_t)length<sizeof(fixture_last_row));
    assert(!strncmp(fixture_last_row,"COH_MAP_BIN_FRESHNESS_V1 ",25));
    ++fixture_rows;return length;
}
#define printf fixturePrintf
#include "coh_map_bin_observer.h"
'''
    tail = r'''
static void run_equivalence(void) {
    int test;
    for(test=0;test<14;++test) {
        int first,second,a_checks,a_scans,a_closes,a_seeks;
        char original_trace[16384];FileEntry original_bins[4],original_scanned[4];
        const char *dir=test>=10?NULL:"defs/fx";
        const char *mask=test>=10?"defs/fx/base.fx":".fx";
        if(test>=12)dir=mask=NULL;
        reset(test);if(test==13)count=scanned_count=0;
        fixture_trace_length=0;fixture_trace[0]=0;
        first=StockParserIsPersistNewer(dir,mask,"bin/fxinfo.bin",NULL,NULL);
        strcpy(original_trace,fixture_trace);
        memcpy(original_bins,bins,sizeof(bins));memcpy(original_scanned,scanned,sizeof(scanned));
        a_checks=checks;a_scans=scans;a_closes=closes;a_seeks=seeks;
        reset(test);if(test==13)count=scanned_count=0;
        fixture_trace_length=0;fixture_trace[0]=0;
        second=ParserIsPersistNewer(dir,mask,"bin/fxinfo.bin",NULL,NULL);
        assert(first==second&&!strcmp(original_trace,fixture_trace));
        assert(!memcmp(original_bins,bins,sizeof(bins))&&!memcmp(original_scanned,scanned,sizeof(scanned)));
        assert(a_checks==checks&&a_scans==scans&&a_closes==closes&&a_seeks==seeks);
#ifdef SERVER
        assert(strstr(fixture_last_row,"clock_valid=1 "));
        assert(strstr(fixture_last_row,test==9?"outcome=production_assumed":
                      test==1?"outcome=open_rejected":second?"outcome=freshness_accepted":"outcome=freshness_rejected"));
#endif
    }
}
int main(void) {
    unsigned int before;int clocks;
    run_equivalence();
#ifdef SERVER
    assert(fixture_rows==14&&cohMapBinObservationCount==14);
    fixture_clock_fail=1;reset(0);
    assert(ParserIsPersistNewer("defs/fx",".fx","bin/fxinfo.bin",NULL,NULL)==1);
    assert(strstr(fixture_last_row,"clock_valid=0 open_us=0 dependencies_us=0 scan_us=0 dates_us=0 membership_us=0 cleanup_us=0"));
    fixture_clock_fail=0;fixture_clock_regress_at=fixture_clock_calls+3;reset(0);
    assert(ParserIsPersistNewer("defs/fx",".fx","bin/fxinfo.bin",NULL,NULL)==1);
    assert(strstr(fixture_last_row,"clock_valid=0 open_us=0 dependencies_us=0 scan_us=0 dates_us=0 membership_us=0 cleanup_us=0"));
    fixture_clock_regress_at=0;
    fixture_frequency=0;reset(0);
    assert(ParserIsPersistNewer("defs/fx",".fx","bin/fxinfo.bin",NULL,NULL)==1);
    assert(strstr(fixture_last_row,"clock_valid=0 open_us=0 dependencies_us=0 scan_us=0 dates_us=0 membership_us=0 cleanup_us=0"));
    fixture_frequency=1000000;fixture_clock=-100000;reset(0);
    assert(ParserIsPersistNewer("defs/fx",".fx","bin/fxinfo.bin",NULL,NULL)==1);
    assert(strstr(fixture_last_row,"clock_valid=0 open_us=0 dependencies_us=0 scan_us=0 dates_us=0 membership_us=0 cleanup_us=0"));
    fixture_frequency=1;fixture_clock=9223372036854700000LL;reset(0);
    assert(ParserIsPersistNewer("defs/fx",".fx","bin/fxinfo.bin",NULL,NULL)==1);
    assert(strstr(fixture_last_row,"clock_valid=0 open_us=0 dependencies_us=0 scan_us=0 dates_us=0 membership_us=0 cleanup_us=0"));
    fixture_frequency=1000000;fixture_clock=100000;
    while(cohMapBinObservationCount<COH_MAP_BIN_OBSERVER_LIMIT) {
        reset(0);assert(ParserIsPersistNewer("defs/fx",".fx","bin/fxinfo.bin",NULL,NULL)==1);
    }
    before=fixture_rows;clocks=fixture_clock_calls;
    {int i;for(i=0;i<300;++i) {reset(0);assert(ParserIsPersistNewer("defs/fx",".fx","bin/fxinfo.bin",NULL,NULL)==1);}}
    assert(fixture_rows==before&&before==256&&fixture_clock_calls==clocks);
    /* Finishing a record twice cannot duplicate a row. */
    {CohMapBinObservation value;memset(&value,0,sizeof(value));cohMapBinFinish(&value,"inactive");assert(fixture_rows==before);}
#else
    (void)before;(void)clocks;assert(fixture_rows==0);
#endif
    puts("COH_MAP_BIN_OBSERVER_EQUIVALENCE_PASS freshness_cases=14 shipping_bypass=0");
    return 0;
}
'''
    return prefix + '\n' + logging + '\n' + stock.replace('ParserIsPersistNewer(', 'StockParserIsPersistNewer(', 1) \
        + '\n' + observer.patch_function(stock) + '\n' + reset + '\n' + tail


def execute(server=True):
    compiler = shutil.which('cc')
    namespace.require(compiler, 'Host C compiler required for observer equivalence fixture')
    with tempfile.TemporaryDirectory(prefix='coh-map-bin-observer-') as temporary:
        root = Path(temporary)
        source = harness(server)
        (root / 'fixture.c').write_text(source)
        (root / 'windows.h').write_text(WINDOWS_ADAPTER)
        (root / 'coh_map_bin_observer.h').write_bytes(observer.bytes_lf(observer.ROOT / observer.OVERLAY))
        command = [compiler, '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-O2', '-I', str(root),
                   str(root / 'fixture.c'), '-o', str(root / 'fixture')]
        if server: command.insert(1, '-DSERVER')
        build = subprocess.run(command, capture_output=True, text=True)
        namespace.require(build.returncode == 0, 'Observer fixture compile failed: ' + build.stderr)
        result = subprocess.run([str(root / 'fixture')], capture_output=True, text=True)
        namespace.require(result.returncode == 0, 'Observer fixture failed: ' + result.stderr)
        namespace.require('COH_MAP_BIN_OBSERVER_EQUIVALENCE_PASS' in result.stdout, 'Observer fixture marker absent')
        return {'status': 'passed', 'scope': 'actual_extracted_stock_C_and_observer_with_bounded_IO_and_QPC_adapters',
                'server_observer_enabled': server, 'freshness_cases': 14,
                'exact_loader_IO_call_sequence_compared': True, 'decoder_observed': False,
                'maximum_rows_verified': 256 if server else 0,
                'harness_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'full_mapserver_wine_execution': False, 'physical_device_qualified': False}


class MapStartupObserverSourceTests(unittest.TestCase):
    def staging(self, root):
        for name in (observer.SOURCE, *observer.RETAINED):
            path = root / name;path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(observer.bytes_lf(observer.ROOT / 'upstream/ouroboros' / name))

    def test_server_actual_native_function_IO_and_decisions_match(self):
        self.assertEqual(execute()['freshness_cases'], 14)

    def test_nonserver_actual_native_function_has_no_observations(self):
        self.assertEqual(execute(False)['maximum_rows_verified'], 0)

    def test_contract_explicitly_refuses_publication_certificates_and_speed_claim(self):
        value = observer.expected_receipt()
        self.assertFalse(value['publication_allowed'])
        for name in ('freshness_bypass_enabled', 'effective_provider_generation_created',
                     'per_bin_certificate_created', 'native_windows_wine_qualified',
                     'physical_device_qualified', 'startup_savings_measured'):
            self.assertFalse(value['contract'][name])
        self.assertEqual(value['contract']['additional_filesystem_reads'], 0)

    def test_isolated_staging_and_exact_decoder_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary);self.staging(root)
            decoder = namespace.function((root / observer.SOURCE).read_text(), 'int ParserReadBinaryFile(')
            retained = {name: (root / name).read_bytes() for name in observer.RETAINED}
            value = observer.apply_observer_overlay(root)
            self.assertEqual(value, observer.expected_receipt())
            self.assertEqual(namespace.function((root / observer.SOURCE).read_text(), 'int ParserReadBinaryFile('), decoder)
            for name, data in retained.items(): self.assertEqual((root / name).read_bytes(), data)
            self.assertEqual(hashlib.sha256((root / observer.TARGET).read_bytes()).hexdigest(), value['overlay_sha256'][observer.TARGET])
            with self.assertRaisesRegex(ValueError, 'already staged'): observer.apply_observer_overlay(root)

    def test_changed_staging_source_is_refused_before_any_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary);self.staging(root)
            path = root / observer.SOURCE;path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'exact staging source differs'): observer.apply_observer_overlay(root)
            self.assertFalse((root / observer.TARGET).exists())
            self.assertFalse((root / observer.RECEIPT).exists())

    def test_linked_staging_source_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary);self.staging(root)
            path = root / observer.SOURCE;path.unlink()
            path.symlink_to(observer.ROOT / 'upstream/ouroboros' / observer.SOURCE)
            with self.assertRaisesRegex(ValueError, 'linked staging'): observer.apply_observer_overlay(root)

    def test_immutable_and_repository_roots_are_refused(self):
        for path in (observer.ROOT, observer.ROOT / 'upstream/ouroboros', observer.ROOT.parent):
            with self.assertRaisesRegex(ValueError, 'immutable or repository ancestor'): observer.apply_observer_overlay(path)

    def test_patch_anchor_mutation_is_refused(self):
        original = observer.bytes_lf(observer.ROOT / 'upstream/ouroboros' / observer.SOURCE)
        with self.assertRaisesRegex(ValueError, 'anchor differs'):
            observer.patch_source(original.replace(b'    // open the bin file\n', b'    // changed\n'))

    def test_all_original_stock_C_tokens_remain_in_exact_order(self):
        original = namespace.function((observer.ROOT / 'upstream/ouroboros' / observer.SOURCE).read_text(),
                                      observer.SIGNATURE)
        patched = observer.patch_function(original)
        stripped = re.sub(r'(?m)^[ \t]*COH_MAP_BIN_[A-Z]+\([^;\n]*\);[ \t]*\n', '', patched)
        stripped = stripped.replace('if(isProductionMode()) {\n        return binfile;\n    }',
                                    'if(isProductionMode())\n        return binfile;', 1)
        def tokens(text):
            return [token for token in re.findall(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s]', text)
                    if not token.startswith(('//', '/*'))]
        self.assertEqual(tokens(stripped), tokens(original))


if __name__ == '__main__': unittest.main()
