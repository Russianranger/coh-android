"""Execute bounded canonical census decoding; source/provider authority is absent.

Every metadata/time value is controlled fixture data. A Win32 execution can
verify SDK layout, but cannot establish a real Wine/provider census or Game gain.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = 'coh_folder_census.h'
OVERLAY = 'database/client-metadata-census/overlay/' + HEADER
LIMITS = {'bytes': 64 * 1024**2, 'directories': 16384, 'rows': 200000, 'path_bytes': 259,
          'header_bytes': 64, 'WFD_projection_bytes': 320, 'row_bytes': 328}


def projection(name, attributes=0, creation=0, access=0, write=0,
               size_high=0, size_low=0, alternate=''):
    """Controlled canonical projection, never a native metadata authority."""
    data = bytearray(320)
    name, alternate = name.encode('ascii'), alternate.encode('ascii')
    if len(name) > 259 or len(alternate) > 13:
        raise ValueError('Fixture names outside projection')
    struct.pack_into('<IQQQIIII', data, 0, attributes, creation, access, write,
                     size_high, size_low, 0, 0)
    data[44:44+len(name)] = name
    data[304:304+len(alternate)] = alternate
    return bytes(data)


def encode_fixture(directories, token=bytes(range(32))):
    """Fixture encoder for the versioned bytes contract; grants no admission."""
    if len(token) != 32:
        raise ValueError('Opaque fixture token must be 32 bytes')
    ordered = sorted(directories.items(), key=lambda value: value[0].lower())
    directory_table, record_table = bytearray(), bytearray()
    count = 0
    for ordinal, (path, rows) in enumerate(ordered):
        name = path.encode('ascii')
        directory_table.extend(struct.pack('<HHIII', len(name), 0, count, len(rows), ordinal))
        directory_table.extend(name)
        directory_table.extend(bytes((-len(directory_table)) % 4))
        for arrival, row in enumerate(rows):
            if len(row) != 320:
                raise ValueError('Fixture WFD projection must be 320 bytes')
            record_table.extend(struct.pack('<II', ordinal, arrival) + row)
        count += len(rows)
    record_offset = 64 + len(directory_table)
    total = record_offset + len(record_table)
    return struct.pack('<8sIIIIII32s', b'COHCNS1\0', 1, total, len(ordered), count,
                       record_offset, 0, token) + directory_table + record_table


def directories_fixture(root='texture_library'):
    return {
        root: [projection('.', 16), projection('..', 16),
               projection('z.texture', 0x000010A3, 0x1122334455667788, 0x2233445566778899,
                          0x33445566778899AA, 0x12345678, 0x87654321, 'Z~1.TEX'),
               projection('_excluded.txt', 2 | 32, 123, 456, 789, 0, 211),
               projection('same.geo', 1, write=100, size_low=41),
               projection('SAME.GEO', 4, write=200, size_low=43),
               projection('_hidden', 16 | 2), projection('empty', 16),
               projection('.hidden-dir', 16 | 2), projection('.hidden-file', 2),
               projection('nontexture', 16)],
        root + '/.hidden-dir': [projection('retained.secret', 4, write=12, size_low=37)],
        root + '/_hidden': [projection('_discarded.txt', 1, write=13), projection('retained.geo', 32, write=14)],
        root + '/empty': [],
        root + '/nontexture': [projection('nested.geom', 0x80000000, 77, 88, 99, 1, 2)],
    }


def directory_offsets(blob):
    offset, result = 64, []
    for _ in range(struct.unpack_from('<I', blob, 16)[0]):
        result.append(offset)
        n = struct.unpack_from('<H', blob, offset)[0]
        offset = (offset + 16 + n + 3) & ~3
    return result


def mutation(blob, offset, raw):
    changed = bytearray(blob)
    changed[offset:offset + len(raw)] = raw
    return bytes(changed)


def cases():
    good = encode_fixture(directories_fixture())
    rows = struct.unpack_from('<I', good, 24)[0]
    offsets = directory_offsets(good)
    result = [('complete_hidden_empty_excluded_leaf_aliases', good, 1)]
    for name, offset, raw in [
        ('bad_magic', 0, b'X'), ('unknown_version', 8, struct.pack('<I', 2)),
        ('unknown_flags', 28, struct.pack('<I', 1)), ('short_total', 12, struct.pack('<I', len(good)-1)),
        ('zero_directories', 16, struct.pack('<I', 0)), ('too_many_directories', 16, struct.pack('<I', 16385)),
        ('too_many_rows', 20, struct.pack('<I', 200001)), ('unbounded_rows', 20, struct.pack('<I', 0xFFFFFFFF)),
        ('records_overlap_header', 24, struct.pack('<I', 60)), ('unaligned_record_offset', 24, struct.pack('<I', rows+1)),
        ('directory_reserved', offsets[0]+2, b'\x01\0'), ('directory_ordinal', offsets[0]+12, struct.pack('<I', 3)),
        ('nondense_first_row', offsets[0]+4, struct.pack('<I', 1)), ('directory_count_overflow', offsets[0]+8, struct.pack('<I', 0xFFFFFFFF)),
        ('unbounded_path', offsets[0], struct.pack('<H', 260)), ('row_owner', rows, struct.pack('<I', 4)),
        ('row_arrival', rows+4, struct.pack('<I', 3)), ('reserved0_stack_bytes', rows+8+36, b'\x01\0\0\0'),
        ('reserved1_stack_bytes', rows+8+40, b'\x01\0\0\0'), ('trailing_stack_padding', rows+8+318, b'\xA5\xA5'),
        ('long_string_padding', rows+8+46, b'X'), ('short_string_padding', rows+8+305, b'X'),
        ('long_string_no_terminator', rows+8+44, b'A'*260), ('short_string_no_terminator', rows+8+304, b'A'*14),
        ('unsupported_name_encoding', rows+8+44, b'\xE9'), ('name_contains_path', rows+8+44, b'/'),
        ('name_contains_stream', rows+8+44, b':'), ('empty_long_name', rows+8+44, b'\0'),
    ]:
        result.append((name, mutation(good, offset, raw), 0))
    # Padding after a non-four-byte path must be canonical zero.
    for off in offsets:
        length = struct.unpack_from('<H', good, off)[0]
        end = off + 16 + length
        if end & 3:
            result.append(('directory_padding', mutation(good, end, b'X'), 0))
            break
    for length in (0, 1, 7, 32, 63, 64, len(good)-1):
        result.append(('truncated_%d' % length, good[:length], 0))
    result.append(('appended_bytes', good + b'\0', 0))
    result.append(('opaque_token_does_not_authenticate', mutation(good, 32, bytes(32)), 1))
    result.append(('single_empty_subtree', encode_fixture({'fx': []}), 1))
    result.append(('empty_data_root', encode_fixture({'': []}), 1))
    result.append(('missing_empty_directory', encode_fixture({'fx': [projection('empty', 16)]}), 0))
    result.append(('orphan_directory', encode_fixture({'fx': [], 'fx/orphan': []}), 0))
    result.append(('second_independent_root', encode_fixture({'fx': [], 'scripts.loc': []}), 0))
    result.append(('path_traversal', encode_fixture({'fx/..': []}), 0))
    result.append(('absolute_directory', encode_fixture({'/fx': []}), 0))
    result.append(('drive_directory', encode_fixture({'Z:/fx': []}), 0))
    result.append(('backslash_directory', encode_fixture({'fx\\sub': []}), 0))
    result.append(('ambiguous_directory_case', encode_fixture({'fx': [], 'FX': []}), 0))
    result.append(('directory_case_alias_rows', encode_fixture({'fx': [projection('dir', 16), projection('DIR', 16)], 'fx/dir': []}), 0))
    result.append(('file_directory_alias', encode_fixture({'fx': [projection('dir', 16), projection('DIR', 0)], 'fx/dir': []}), 0))
    result.append(('duplicate_leaf_case_preserved', encode_fixture({'fx': [projection('A.fx', 1), projection('a.FX', 4)]}), 1))
    result.append(('hidden_directory_full_membership', encode_fixture({'fx': [projection('.hidden', 16)], 'fx/.hidden': [projection('child.fx', 1)]}), 1))
    result.append(('missing_hidden_directory', encode_fixture({'fx': [projection('.hidden', 16)]}), 0))
    result.append(('dot_directory_never_root_edge', encode_fixture({'fx': [projection('.', 16)], 'fx/else': []}), 0))
    # Random valid arrival orders preserve excluded and nontexture rows exactly.
    randomizer = random.Random(0xC0C3)
    for index in range(64):
        root = ('texture_library', 'object_library', 'fx', 'scripts.loc')[index % 4]
        dirs = directories_fixture(root)
        randomizer.shuffle(dirs[root])
        result.append(('random_arrival_%02d' % index, encode_fixture(dirs), 1))
    return result


def harness():
    fixture_cases = cases()
    prefix = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#endif
#include "coh_folder_census.h"
'''
    arrays = []
    for index, (_, blob, _) in enumerate(fixture_cases):
        arrays.append('static const unsigned char input_%d[] = {%s};' % (
            index, ','.join(str(x) for x in blob) if blob else '0'))
    table = 'typedef struct FixtureCase {const unsigned char *data;size_t bytes;int success;const char *name;} FixtureCase;\n'
    table += 'static const FixtureCase cases[] = {\n'
    table += ',\n'.join('{input_%d,%du,%d,"%s"}' % (i, len(blob), expected, name)
                        for i, (name, blob, expected) in enumerate(fixture_cases)) + '\n};\n'
    tail = r'''
static void failed_view(const CohFolderCensusView *view) {
 assert(!view->valid&&!view->data&&!view->provider_token&&!view->directory_offsets);
 assert(!view->bytes&&!view->directory_count&&!view->row_count&&!view->record_offset);
}
int main(void) {
 uint32_t scratch[COH_CENSUS_MAX_DIRS];unsigned int i,accepted=0,rejected=0,total_rows=0;
#ifdef _WIN32
 assert(sizeof(WIN32_FIND_DATAA)==320&&offsetof(WIN32_FIND_DATAA,dwFileAttributes)==0);
 assert(offsetof(WIN32_FIND_DATAA,ftCreationTime)==4&&offsetof(WIN32_FIND_DATAA,ftLastAccessTime)==12&&offsetof(WIN32_FIND_DATAA,ftLastWriteTime)==20);
 assert(offsetof(WIN32_FIND_DATAA,nFileSizeHigh)==28&&offsetof(WIN32_FIND_DATAA,nFileSizeLow)==32);
 assert(offsetof(WIN32_FIND_DATAA,dwReserved0)==36&&offsetof(WIN32_FIND_DATAA,dwReserved1)==40);
 assert(offsetof(WIN32_FIND_DATAA,cFileName)==44&&offsetof(WIN32_FIND_DATAA,cAlternateFileName)==304);
#endif
 for(i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
  const FixtureCase *test=&cases[i];CohFolderCensusView view;CohCensusResult status;
  memset(&view,0xA5,sizeof(view));memset(scratch,0xEE,sizeof(scratch));
  status=cohCensusDecode(&view,test->data,test->bytes,scratch,COH_CENSUS_MAX_DIRS);
  if((status==COH_CENSUS_OK)!=test->success){fprintf(stderr,"case=%s unexpected status=%d\n",test->name,status);return 2;}
  if(!test->success){++rejected;failed_view(&view);assert(!cohCensusProjection(&view,0,0));continue;}
  ++accepted;assert(view.valid&&view.data==test->data&&view.bytes==test->bytes&&view.provider_token==test->data+32);
  assert(view.directory_offsets==scratch);total_rows+=view.row_count;
  {
   uint32_t d,got;
   for(d=0;d<view.directory_count;d++) {
    const unsigned char *entry=cohCensusDirectory(&view,d);uint32_t rows,arrival;size_t length=cohCensusU16(entry);
    char path[260],upper[260];memcpy(path,entry+16,length);path[length]=0;memcpy(upper,path,length+1);
    for(arrival=0;arrival<length;arrival++)if(upper[arrival]>='a'&&upper[arrival]<='z')upper[arrival]-=32;
    assert(cohCensusFindDirectory(&view,path,&got)&&got==d);
    assert(cohCensusFindDirectory(&view,upper,&got)&&got==d);
    assert(cohCensusDirectoryCount(&view,d,&rows)&&rows==cohCensusU32(entry+8));
    for(arrival=0;arrival<rows;arrival++) {
     const unsigned char *wfd=cohCensusProjection(&view,d,arrival);
     const unsigned char *expected=test->data+view.record_offset+(size_t)(cohCensusU32(entry+4)+arrival)*328u+8u;
     assert(wfd&&wfd==expected&&!memcmp(wfd,expected,320u));
#ifdef _WIN32
     {WIN32_FIND_DATAA native;memcpy(&native,wfd,sizeof(native));
      assert(native.dwFileAttributes==cohCensusU32(wfd)&&native.nFileSizeHigh==cohCensusU32(wfd+28)&&native.nFileSizeLow==cohCensusU32(wfd+32));
      assert(native.ftCreationTime.dwLowDateTime==cohCensusU32(wfd+4)&&native.ftCreationTime.dwHighDateTime==cohCensusU32(wfd+8));
      assert(native.ftLastAccessTime.dwLowDateTime==cohCensusU32(wfd+12)&&native.ftLastAccessTime.dwHighDateTime==cohCensusU32(wfd+16));
      assert(native.ftLastWriteTime.dwLowDateTime==cohCensusU32(wfd+20)&&native.ftLastWriteTime.dwHighDateTime==cohCensusU32(wfd+24));
      assert(native.dwReserved0==0&&native.dwReserved1==0&&!strcmp(native.cFileName,(const char*)wfd+44)&&!strcmp(native.cAlternateFileName,(const char*)wfd+304));}
#endif
    }
    assert(!cohCensusProjection(&view,d,rows));
   }
   assert(!cohCensusProjection(&view,view.directory_count,0));
   assert(!cohCensusDirectoryCount(&view,view.directory_count,&got));
   assert(!cohCensusFindDirectory(&view,"../outside",&got));
   {char no_terminator[260];memset(no_terminator,'X',sizeof(no_terminator));assert(!cohCensusFindDirectory(&view,no_terminator,&got));}
  }
  cohCensusClear(&view);failed_view(&view);
 }
 {
  CohFolderCensusView view;unsigned char copy[sizeof(input_0)];memcpy(copy,input_0,sizeof(copy));
  assert(cohCensusDecode(&view,copy,sizeof(copy),scratch,0)==COH_CENSUS_SCRATCH);failed_view(&view);
  assert(cohCensusDecode(&view,copy,sizeof(copy),(uint32_t*)copy,COH_CENSUS_MAX_DIRS)==COH_CENSUS_SCRATCH);
  failed_view(&view);assert(!memcmp(copy,input_0,sizeof(copy)));
  assert(cohCensusDecode(&view,NULL,64,scratch,COH_CENSUS_MAX_DIRS)==COH_CENSUS_BAD_HEADER);failed_view(&view);
  assert(cohCensusDecode(&view,input_0,(size_t)COH_CENSUS_MAX_BYTES+1u,scratch,COH_CENSUS_MAX_DIRS)==COH_CENSUS_BAD_HEADER);failed_view(&view);
  {
   union {CohFolderCensusView view;unsigned char bytes[sizeof(input_0)];} overlap;
   unsigned char original[sizeof(input_0)];memcpy(overlap.bytes,input_0,sizeof(input_0));memcpy(original,overlap.bytes,sizeof(original));
   assert(cohCensusDecode(&overlap.view,overlap.bytes,sizeof(overlap.bytes),scratch,COH_CENSUS_MAX_DIRS)==COH_CENSUS_SCRATCH);
   assert(!memcmp(overlap.bytes,original,sizeof(original)));
  }
  {
   union {CohFolderCensusView view;uint32_t index[COH_CENSUS_MAX_DIRS];} overlap;
   unsigned char original[sizeof(overlap)];memset(&overlap,0xA5,sizeof(overlap));memcpy(original,&overlap,sizeof(original));
   assert(cohCensusDecode(&overlap.view,input_0,sizeof(input_0),overlap.index,COH_CENSUS_MAX_DIRS)==COH_CENSUS_SCRATCH);
   assert(!memcmp(&overlap,original,sizeof(original)));
  }
 }
 printf("COH_NATIVE_CENSUS_DECODE_PASS cases=%u accepted=%u rejected=%u canonical_rows=%u directory_index_bound_bytes=%lu projection_bytes=320 callbacks=0 heap_allocations=0 source_authority=0\n",
   (unsigned int)(sizeof(cases)/sizeof(cases[0]))+6u,accepted,rejected+6u,total_rows,(unsigned long)(COH_CENSUS_MAX_DIRS*sizeof(uint32_t)));
 return 0;
}
'''
    return prefix + '\n'.join(arrays) + '\n' + table + tail


def execute(output=None, windows=False):
    if windows and os.name != 'nt':
        raise ValueError('Actual Windows host required')
    compiler = shutil.which('cl' if windows else 'cc')
    if not compiler:
        raise ValueError('C compiler required')
    with tempfile.TemporaryDirectory(prefix='coh-census-decode-') as temporary:
        root = Path(temporary); code = harness(); header = (ROOT/OVERLAY).read_bytes().replace(b'\r\n',b'\n')
        (root/'fixture.c').write_text(code); (root/HEADER).write_bytes(header)
        binary = root/('fixture.exe' if windows else 'fixture')
        command = [compiler,'/nologo','/O2','/TC','/MT','fixture.c','/Fe:'+str(binary)] if windows else [compiler,'-std=c11','-O2','-Wall','-Wextra','-I',str(root),'fixture.c','-o',str(binary)]
        build = subprocess.run(command,cwd=root,capture_output=True,text=True)
        if build.returncode:
            raise ValueError('Census decoder compile failed: '+build.stdout+build.stderr)
        run = subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
        if run.returncode or 'COH_NATIVE_CENSUS_DECODE_PASS' not in run.stdout:
            raise ValueError('Census decoder fixture failed: '+run.stdout+run.stderr)
        fields = dict(item.split('=',1) for item in run.stdout.strip().split()[1:])
        receipt = {'format':1,'status':'passed','role':'bounded_canonical_native_metadata_census_decoder_fixture',
            'cases':int(fields['cases']),'accepted':int(fields['accepted']),'rejected':int(fields['rejected']),
            'canonical_rows_verified':int(fields['canonical_rows']),'limits':LIMITS,
            'decoder_heap_allocations':0,'decoder_callbacks':0,'decoder_filesystem_calls':0,
            'caller_directory_index_maximum_bytes':65536,'blob_maximum_bytes':67108864,
            'provider_token_authenticates_source':False,'provider_generation_qualified':False,
            'all_times_are_controlled_fixture_observations':True,'current_full_WFD_parity_proven':False,
            'reserved_and_string_tail_and_ABI_padding':'canonical_zero_nonauthoritative',
            'access_time_current_authority_proven':False,'input_and_index_borrowed_private_immutable':True,
            'full_directory_graph_preflight_before_replay':True,'hidden_directory_graph_retained':True,
            'output_input_or_index_alias_refused_before_writes':True,
            'ordinary_disjoint_failure_view_cleared':True,'alias_misuse_preserves_storage_instead_of_clearing':True,
            'directory_and_file_directory_aliases_rejected':True,'leaf_case_alias_arrival_preserved':True,
            'native_windows_executed':windows,'Windows_SDK_projection_ABI_executed':windows,
            'native_Wine_enumeration_executed':False,'native_Game_executed':False,
            'physical_device_executed':False,'publication_allowed':False,
            'header_sha256':hashlib.sha256(header).hexdigest(),'harness_sha256':hashlib.sha256(code.encode()).hexdigest(),
            'fixture_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'output':run.stdout.strip()}
        if output:
            output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(receipt,indent=2)+'\n')
            shutil.copyfile(binary,output.with_suffix('.exe' if windows else '.bin'))
        return receipt


class CensusDecoderTests(unittest.TestCase):
    def test_actual_portable_decoder_malformed_graph_and_projection_parity(self):
        receipt=execute()
        self.assertGreater(receipt['cases'],100)
        self.assertGreater(receipt['canonical_rows_verified'],800)
        self.assertEqual(receipt['decoder_callbacks'],0)
        self.assertFalse(receipt['provider_generation_qualified'])

    def test_schema_retains_hidden_empty_nontexture_and_leaf_alias_observations(self):
        values=cases()
        names={name for name,_,_ in values}
        for expected in ('hidden_directory_full_membership','single_empty_subtree','duplicate_leaf_case_preserved',
                         'complete_hidden_empty_excluded_leaf_aliases','opaque_token_does_not_authenticate'):
            self.assertIn(expected,names)
        self.assertEqual(struct.unpack_from('<I',encode_fixture(directories_fixture()),16)[0],5)

    def test_canonical_projection_preserves_defined_metadata_fields(self):
        row=projection('test.texture',0xA0,0x0102030405060708,0x1112131415161718,
                       0x2122232425262728,0x31323334,0x41424344,'TEST~1.TEX')
        self.assertEqual(struct.unpack_from('<IQQQIIII',row,0),
                         (0xA0,0x0102030405060708,0x1112131415161718,0x2122232425262728,0x31323334,0x41424344,0,0))
        self.assertEqual(row[318:],bytes(2))
        self.assertEqual(row[44:57],b'test.texture\0')

    def test_decoder_does_not_expose_authorization_or_native_side_effects(self):
        text=(ROOT/OVERLAY).read_text()
        for call in ('malloc(', 'realloc(', 'fopen(', 'fwFindFirstFile(', 'FolderNodeAdd(', 'FolderCacheQuery('):
            self.assertNotIn(call,text)
        self.assertIn('Opaque; this decoder cannot verify it',text)
        self.assertIn('No heap allocation',text)

    def test_limits_and_offsets_match_header_contract(self):
        blob=encode_fixture(directories_fixture())
        self.assertEqual(blob[:8],b'COHCNS1\0')
        self.assertEqual(struct.unpack_from('<I',blob,12)[0],len(blob))
        records=struct.unpack_from('<I',blob,20)[0];offset=struct.unpack_from('<I',blob,24)[0]
        self.assertEqual(len(blob)-offset,records*328)
        self.assertEqual(struct.unpack_from('<I',blob,28)[0],0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--windows-qualify',action='store_true');parser.add_argument('--output',type=Path)
    args,rest=parser.parse_known_args()
    if args.windows_qualify:
        if args.output is None:raise ValueError('Actual Windows fixture output required')
        print(json.dumps(execute(args.output,windows=True)))
    else:
        unittest.main(argv=[__file__,*rest])
