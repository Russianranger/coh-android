"""Actual extracted decoder parity and bounded active profiler source tests."""
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import map_startup_namespace_certificate as namespace
import prepare_native_startup_profile_source as profile
from test_map_startup_observer_source import WINDOWS_ADAPTER


def harness(active=True):
    original = namespace.function(profile.source_bytes(profile.PARSER).decode(), 'int ParserReadBinaryFile(')
    candidate = namespace.function(profile.parser_source(profile.source_bytes(profile.PARSER)).decode(), 'int ParserReadBinaryFile(')
    prefix = r'''
#include <assert.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include "windows.h"
typedef int SimpleBufHandle;
typedef int ParseTable;
typedef int FileList;
typedef int DefineContext;
#define PARSE_SIG "Parse6"
static int scenario, calls[32], call_count, rows;
static char last_row[1024];
static const char *parser_relpath;
static void trace(int n) { assert(call_count<32); calls[call_count++]=n; }
static int ParseTableCRC(ParseTable *p, DefineContext *d) { (void)p;(void)d;trace(1);return 42; }
static int isProductionMode(void) {trace(2);return 0;}
static int SerializeReadOpen(const char *name, const char *sig, int crc, int prod) {
 (void)name;assert(!strcmp(sig,"Parse6")&&crc==42&&!prod);trace(3);return scenario==1?0:7;
}
static int FileListRead(FileList *list, int file) { (void)list;assert(file==7);trace(4);return scenario!=2; }
static void SerializeClose(int file) {assert(file==7);trace(5);}
static int at_end;
static long SimpleBufTell(int file) {assert(file==7);trace(6);return at_end?(scenario==4?101:100):20;}
static const char *allocAddString(const char *value) {trace(7);return value;}
static int ParserReadBinaryTable(int file, ParseTable *p, void *s, int *size) {
 (void)p;(void)s;assert(file==7);trace(8);*size=80;return scenario!=3;
}
static void SimpleBufSeek(int file, int offset, int origin) {assert(file==7&&offset==0&&origin==SEEK_END);trace(9);at_end=1;}
static int profilePrintf(const char *format,...) {
 va_list args;int size;va_start(args,format);size=vsnprintf(last_row,sizeof(last_row),format,args);va_end(args);
 assert(size>=0&&(size_t)size<sizeof(last_row));
 if(!strncmp(last_row,"COH_NATIVE_STARTUP_PROFILE_V1 ",30)) ++rows;
 return size;
}
#define printf profilePrintf
'''
    if active:
        prefix += '#define COH_NATIVE_STARTUP_PROFILE 1\n'
    prefix += '#include "' + profile.HEADER + '"\n'
    tail = r'''
static void reset(int n) {scenario=n;at_end=0;call_count=0;parser_relpath=NULL;memset(calls,0,sizeof(calls));}
int main(void) {
 int n,result,expected,old_calls[32],old_count;
 for(n=0;n<6;n++) {
  reset(n);expected=stockDecoder(n==5?7:0,"bin/sequencers.bin",NULL,NULL,NULL,NULL);
  old_count=call_count;memcpy(old_calls,calls,sizeof(calls));
  reset(n);result=ParserReadBinaryFile(n==5?7:0,"bin/sequencers.bin",NULL,NULL,NULL,NULL);
  assert(result==expected&&old_count==call_count&&!memcmp(old_calls,calls,sizeof(calls))&&!parser_relpath);
 }
#ifdef COH_NATIVE_STARTUP_PROFILE
 assert(rows==6&&cohNativeProfileRows==6);
 fixture_clock_fail=1;reset(0);assert(ParserReadBinaryFile(7,NULL,NULL,NULL,NULL,NULL)==1);
 assert(strstr(last_row,"clock_valid=0 elapsed_us=0"));fixture_clock_fail=0;
 fixture_clock_regress_at=fixture_clock_calls+2;reset(0);assert(ParserReadBinaryFile(7,NULL,NULL,NULL,NULL,NULL)==1);
 assert(strstr(last_row,"clock_valid=0 elapsed_us=0"));fixture_clock_regress_at=0;
 fixture_frequency=0;reset(0);assert(ParserReadBinaryFile(7,NULL,NULL,NULL,NULL,NULL)==1);
 assert(strstr(last_row,"clock_valid=0 elapsed_us=0"));fixture_frequency=1000000;
 fixture_clock=-100000;reset(0);assert(ParserReadBinaryFile(7,NULL,NULL,NULL,NULL,NULL)==1);
 assert(strstr(last_row,"clock_valid=0 elapsed_us=0"));fixture_clock=100000;
 while(cohNativeProfileRows<256u) {reset(0);assert(ParserReadBinaryFile(7,NULL,NULL,NULL,NULL,NULL)==1);}
 {int clock_calls=fixture_clock_calls;for(n=0;n<300;n++) {reset(0);assert(ParserReadBinaryFile(7,NULL,NULL,NULL,NULL,NULL)==1);}
  assert(rows==256&&fixture_clock_calls==clock_calls);}
 {CohNativeProfile inactive;memset(&inactive,0,sizeof(inactive));cohNativeProfileEnd(&inactive,1);assert(rows==256);}
#else
 assert(rows==0&&fixture_clock_calls==0);
#endif
 puts("COH_NATIVE_STARTUP_PROFILE_PARITY_PASS decoder_cases=6");return 0;
}
'''
    return prefix + original.replace('ParserReadBinaryFile(', 'stockDecoder(', 1) + '\n' + candidate + tail


def execute(active=True):
    compiler = shutil.which('cc')
    namespace.require(compiler, 'C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-native-startup-profile-') as temporary:
        root = Path(temporary)
        code = harness(active)
        (root / 'fixture.c').write_text(code)
        (root / 'windows.h').write_text(WINDOWS_ADAPTER)
        (root / profile.HEADER).write_bytes((profile.ROOT / profile.OVERLAY).read_bytes())
        build = subprocess.run([compiler, '-std=c11', '-O2', '-I', str(root), str(root/'fixture.c'),
                                '-o', str(root/'fixture')], capture_output=True, text=True)
        namespace.require(build.returncode == 0, 'Native profile fixture compile failed: ' + build.stderr)
        run = subprocess.run([str(root/'fixture')], capture_output=True, text=True)
        namespace.require(run.returncode == 0 and 'COH_NATIVE_STARTUP_PROFILE_PARITY_PASS' in run.stdout,
                          'Native profile fixture failed: ' + run.stdout + run.stderr)
        return {'status': 'passed', 'decoder_cases': 6, 'active_without_SERVER_definition': active,
                'windows_clock_is_adapter': True, 'native_windows_executed': False,
                'native_wine_executed': False, 'physical_device_executed': False,
                'harness_sha256': hashlib.sha256(code.encode()).hexdigest()}


class NativeStartupProfileSourceTests(unittest.TestCase):
    def staging(self, path):
        for name in (profile.PARSER, profile.SEQUENCER):
            target = path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(profile.source_bytes(name))
        (path / 'map-startup-build-input.json').write_text('{}\n')

    def test_actual_decoder_IO_and_results_match_when_active_without_SERVER(self):
        self.assertTrue(execute()['active_without_SERVER_definition'])

    def test_disabled_profiler_performs_no_clocks_and_preserves_decoder(self):
        self.assertFalse(execute(False)['active_without_SERVER_definition'])

    def test_sequencer_callbacks_retain_each_original_statement_in_order(self):
        original = profile.source_bytes(profile.SEQUENCER).decode()
        patched = profile.sequencer_source(original.encode()).decode()
        for signature in ('static bool seqPreloadSeqInfoPostProcessor(',
                          'static bool seqPreloadSeqInfoFinalProcessor(', 'void seqPreloadSeqInfos('):
            before = namespace.function(original, signature)
            after = namespace.function(patched, signature)
            after = re.sub(r'^[ \t]*COH_NATIVE_PROFILE_(?:DECLARE|BEGIN|END)\([^\n]*\);\n', '', after, flags=re.M)
            self.assertEqual(before, after)
        self.assertIn('#ifdef SERVER\n#define COH_NATIVE_STARTUP_PROFILE 1\n#endif', patched)

    def test_isolated_staging_activates_real_parser_TU_and_binds_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.staging(root)
            receipt = profile.stage(root)
            self.assertFalse(receipt['publication_allowed'])
            for name, pin in receipt['patched_sha256'].items():
                self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), pin)
            parser = (root/profile.PARSER).read_text()
            self.assertIn('#define COH_NATIVE_STARTUP_PROFILE 1\n#include "coh_map_bin_observer.h"', parser)
            header = (root/profile.freshness.TARGET).read_text()
            self.assertIn('#ifdef COH_NATIVE_STARTUP_PROFILE', header)
            self.assertNotIn('#ifdef SERVER', header)
            with self.assertRaisesRegex(ValueError, 'exact source differs'): profile.stage(root)

    def test_changed_sequencer_refused_before_parser_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.staging(root)
            before = (root/profile.PARSER).read_bytes()
            (root/profile.SEQUENCER).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'exact source differs'): profile.stage(root)
            self.assertEqual((root/profile.PARSER).read_bytes(), before)
            self.assertFalse((root/profile.RECEIPT).exists())

    def test_linked_output_refused_before_any_source_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.staging(root)
            before = (root/profile.PARSER).read_bytes()
            (root/profile.freshness.TARGET).symlink_to(root/'elsewhere')
            with self.assertRaisesRegex(ValueError, 'linked staging path'): profile.stage(root)
            self.assertEqual((root/profile.PARSER).read_bytes(), before)

    def test_staging_requires_existing_animation_monorail_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.staging(root)
            (root/'map-startup-build-input.json').unlink()
            with self.assertRaisesRegex(ValueError, 'retained animation'): profile.stage(root)

    def test_receipt_does_not_claim_native_execution_or_integrity_authority(self):
        receipt = profile.expected_receipt()
        for name in ('publication_allowed','native_windows_executed','native_wine_executed',
                     'physical_device_executed','provider_authority_created','freshness_bypass_enabled',
                     'animation_payload_or_validation_changed','persistent_cache_payload_added'):
            self.assertFalse(receipt[name])


if __name__ == '__main__': unittest.main()
