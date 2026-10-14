"""Strict capture parser and controlled fixtures; no provider authorization.

Native Windows: compile native_client_wfd_probe.c once via vcvars32, then:
  python test_native_client_wfd_probe.py --windows-qualify --probe probe.exe --output checks.json
Portable tests use encoded binary fixtures. They never claim SDK/Wine execution.
"""
from __future__ import annotations
import argparse
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('native_client_wfd_probe.c')
MAGIC = b'COHWFD1\0'
BRANCHES = ('texture_library', 'object_library', 'fx', 'scripts', 'scripts.loc')
MAX_BYTES, MAX_DIRS, MAX_ROWS = 64*1024**2, 16384, 200000
HEADER_BYTES, WFD_BYTES, INFO_BYTES, STAT_BYTES = 160, 320, 52, 80
MARKER = 'COH_NATIVE_WFD_PROBE_V1 '
GENERATION, OPERATION = '1'*64, '2'*32
UINT32_MAX = 0xffffffff


def require(value, message):
    if not value:
        raise ValueError(message)


def root_path(value):
    require(type(value) is str and 4 <= len(value) < 260 and value.isascii(),
            'Bounded ASCII native root required')
    value = value.replace('\\', '/')
    if value.endswith('/'):
        value = value[:-1]
    require(re.fullmatch(r'[A-Za-z]:/[^:*?"<>|\x00-\x1f]+', value), 'Drive-qualified native root required')
    require(all(part and part not in ('.', '..') and not part.endswith(('.', ' '))
                for part in value[3:].split('/')), 'Ambiguous native root components')
    return value


def u32(data, offset=0):
    return struct.unpack_from('<I', data, offset)[0]


def parse_stat(data):
    require(len(data) == STAT_BYTES, 'Exact by-handle packet required')
    attempted, created, create_error, informed, info_error, closed, close_error = struct.unpack_from('<7I', data)
    require(all(flag in (0, 1) for flag in (attempted, created, informed, closed)), 'Boolean native API status required')
    if not attempted:
        require(not any(data), 'Not-attempted metadata must be unavailable')
    elif not created:
        require(not informed and not closed and not info_error and not close_error and not any(data[28:]),
                'Failed CreateFile cannot provide handle metadata')
    else:
        require(create_error == 0 and (not informed or info_error == 0) and (not closed or close_error == 0),
                'Native successful API errors must be canonical zero')
        if not informed:
            require(not any(data[28:]), 'Failed GetFileInformation metadata must be unavailable')
    return {'attempted': bool(attempted), 'create_ok': bool(created), 'create_error': create_error,
            'information_ok': bool(informed), 'information_error': info_error,
            'close_ok': bool(closed), 'close_error': close_error,
            'information': data[28:].hex(), 'readable': bool(attempted and created and informed and closed)}


def projected_string(data, malformed=False):
    at = data.find(b'\0')
    if at < 0:
        require(malformed, 'Canonical ANSI name terminator missing')
        return None
    require(not any(data[at:]), 'Canonical ANSI string tail differs')
    return data[:at].decode('latin1')


def parse_wfd(data, flags):
    require(len(data) == WFD_BYTES and flags <= 31, 'Canonical WFD projection or flags differ')
    require(not any(data[36:44]) and not any(data[318:]), 'Reserved WFD/padding is nonauthoritative zero')
    name = projected_string(data[44:304], bool(flags & 16))
    alternate = projected_string(data[304:318], bool(flags & 16))
    require(name or flags & 16, 'Native long name unavailable')
    attributes = u32(data)
    require(bool(flags & 2) == (name in ('.', '..')), 'Traversal-alias flag differs')
    require(bool(flags & 4) == ((attributes & (16 | 1024)) == (16 | 1024)), 'Directory-reparse flag differs')
    require(bool(flags & 8) == (not attributes & 16 and not attributes & 1), 'Readonly observation flag differs')
    if flags & 1:
        require(name and name.isascii() and not re.search(r'[\\/:*?"<>|\x00-\x1f]', name),
                'Supported filename projection differs')
    return {'name': name, 'alternate': alternate, 'attributes': attributes,
            'projection': data.hex(), 'mapping_supported': bool(flags & 1),
            'traversal_alias': bool(flags & 2), 'directory_reparse': bool(flags & 4),
            'readonly_required_failed': bool(flags & 8), 'malformed': bool(flags & 16)}


def parse(data, generation, operation, root, windows_pid=None):
    require(type(data) is bytes and HEADER_BYTES <= len(data) <= MAX_BYTES, 'Bounded binary probe sidecar required')
    require(re.fullmatch(r'[0-9a-f]{64}', generation) and re.fullmatch(r'[0-9a-f]{32}', operation),
            'Exact current operation/generation required')
    root = root_path(root)
    require(data[:8] == MAGIC and struct.unpack_from('<10I', data, 8)[:4] == (1, 160, 320, 52),
            'Versioned native SDK probe ABI differs')
    pid, thread, flags, branches, seconds, maximum = struct.unpack_from('<6I', data, 24)
    require(pid > 0 and thread > 0 and flags == 3 and branches == 5 and 1 <= seconds <= 900
            and maximum == MAX_BYTES and not any(data[144:160]), 'Native header identity/bounds differ')
    if windows_pid is not None:
        require(type(windows_pid) is int and windows_pid > 0 and windows_pid == pid, 'Current owned native PID differs')
    require(data[48:112] == generation.encode() and data[112:144] == operation.encode(),
            'Current native token/operation differs')
    offset, sequence, root_record, active, footer = HEADER_BYTES, 0, None, None, None
    directories, entries, directory_ends = [], [], []
    while offset < len(data):
        require(footer is None and len(data)-offset >= 12, 'Interrupted/trailing native probe record')
        kind, size, observed_sequence = struct.unpack_from('<III', data, offset)
        offset += 12
        require(observed_sequence == sequence and size <= len(data)-offset, 'Native record sequence/bounds differ')
        body = data[offset:offset+size]
        offset += size
        sequence += 1
        if kind == 1:
            require(sequence == 1 and root_record is None and size >= 84, 'Single first partial root anchor required')
            n = u32(body)
            require(n == size-84 and body[84:] == root.encode('ascii'), 'Current native root differs')
            root_record = {'root': root, 'partial_anchor': True, 'enumeration_authority': False,
                           'by_handle': parse_stat(body[4:84])}
        elif kind == 2:
            require(root_record and active is None and size >= 96 and len(directories) < MAX_DIRS,
                    'Bounded native directory boundary required')
            ordinal, parent, branch, n = struct.unpack_from('<4I', body)
            require(ordinal == len(directories) and n == size-96 and 0 < n < 260 and branch < 5,
                    'Native directory index/path differs')
            relative = body[96:].decode('ascii')
            require(all(part and part not in ('.', '..') for part in relative.split('/')) and
                    not re.search(r'[\\:*?"<>|\x00-\x1f]', relative), 'Unsupported directory projection')
            if parent == UINT32_MAX:
                require(ordinal < 5 and ordinal == branch and relative == BRANCHES[branch],
                        'Exact five native branch roots required')
            else:
                require(parent < ordinal and directories[parent]['branch'] == branch and
                        relative.startswith(directories[parent]['relative'] + '/') and
                        '/' not in relative[len(directories[parent]['relative'])+1:],
                        'Native directory parent membership differs')
            require(relative.lower() not in {d['relative'].lower() for d in directories},
                    'Ambiguous native directory case aliases')
            active = {'ordinal': ordinal, 'parent': parent, 'branch': branch, 'relative': relative,
                      'by_handle': parse_stat(body[16:96]), 'entries': []}
            directories.append(active)
        elif kind == 3:
            require(active is not None and size == 412 and len(entries) < MAX_ROWS, 'Exact bounded native entry packet required')
            ordinal, arrival, row_flags = struct.unpack_from('<3I', body)
            require(ordinal == active['ordinal'] and arrival == len(active['entries']), 'Original native arrival differs')
            row = {'directory': ordinal, 'arrival': arrival, 'flags': row_flags,
                   'wfd': parse_wfd(body[12:332], row_flags), 'by_handle': parse_stat(body[332:])}
            active['entries'].append(row)
            entries.append(row)
        elif kind == 4:
            require(active is not None and size == 24, 'Exact native directory footer required')
            ordinal, count, first_error, next_error, closed, close_error = struct.unpack('<6I', body)
            require(ordinal == active['ordinal'] and count == len(active['entries']) and closed in (0, 1)
                    and (not closed or close_error == 0), 'Native enumeration/footer counts differ')
            if first_error:
                require(count == 0 and next_error == 0 and closed == 0 and close_error == 0,
                        'Failed initial enumeration cannot supply rows')
            directory_ends.append({'directory': ordinal, 'rows': count, 'first_error': first_error,
                                   'next_error': next_error, 'find_closed': bool(closed), 'close_error': close_error})
            active = None
        elif kind == 5:
            require(root_record and active is None and size == 36, 'Complete native capture footer required')
            queued, observed, count, issues, enum_complete, readable_complete, low, high, authority = struct.unpack('<9I', body)
            require(queued == observed == len(directories) and count == len(entries)
                    and enum_complete in (0, 1) and readable_complete in (0, 1) and authority == 0,
                    'Native overall counts/authority differ')
            footer = {'directories': observed, 'rows': count, 'issues': issues,
                      'enumeration_complete': bool(enum_complete), 'readability_complete': bool(readable_complete),
                      'elapsed_ms': low + (high << 32)}
        else:
            raise ValueError('Unknown native probe record')
    require(root_record and footer and active is None and len(directory_ends) == len(directories),
            'Interrupted native sidecar is diagnostic only')
    if footer['enumeration_complete']:
        require(len(directories) >= 5 and root_record['by_handle']['readable'] and
                u32(bytes.fromhex(root_record['by_handle']['information'])) & 16,
                'Complete enumeration requires readable root/five branches')
        require(all(end['first_error'] == 2 or end['first_error'] == 0 and end['next_error'] == 18
                    and end['find_closed'] for end in directory_ends),
                'Unexpected native enumeration completion')
        require(all(directory['by_handle']['readable'] and
                    u32(bytes.fromhex(directory['by_handle']['information'])) & 16 and
                    not u32(bytes.fromhex(directory['by_handle']['information'])) & 1024
                    for directory in directories),
                'Complete enumeration lacks directory readability')
        observed_paths = {directory['relative'] for directory in directories}
        expected_paths = set(BRANCHES)
        for directory in directories:
            for row in directory['entries']:
                wfd = row['wfd']
                if wfd['attributes'] & 16 and not wfd['traversal_alias']:
                    require(wfd['mapping_supported'] and not wfd['directory_reparse'],
                            'Complete enumeration cannot skip an unknown child')
                    expected_paths.add(directory['relative'] + '/' + wfd['name'])
        require(observed_paths == expected_paths, 'Complete native directory membership differs')
    if footer['readability_complete']:
        require(root_record['by_handle']['readable'] and
                all(directory['by_handle']['readable'] for directory in directories) and
                all(row['by_handle']['readable']
                and row['wfd']['mapping_supported'] and not row['wfd']['malformed']
                and not row['wfd']['readonly_required_failed'] for row in entries),
                'Complete readability contradicts native API evidence')
    require((footer['enumeration_complete'] and footer['readability_complete']) or footer['issues'] > 0,
            'Unknown native observation requires explicit issues')
    complete = footer['enumeration_complete'] and footer['readability_complete'] and footer['issues'] == 0
    return {'format': 1, 'role': 'bounded_native_ANSI_WFD_and_by_handle_observation', 'status':
            'complete_observation' if complete else 'incomplete_observation',
            'windows_pid': pid, 'windows_thread': thread, 'operation': operation, 'generation': generation,
            'ABI': {'pointer_bits': 32, 'WFD_bytes': 320, 'by_handle_bytes': 52, 'header_bytes': 160},
            'ci_deadline_seconds': seconds, 'root': root_record, 'directories': directories,
            'directory_ends': directory_ends, 'footer': footer,
            'provider_authority': False, 'native_registration_allowed': False, 'publication_allowed': False}


def fixture_projection(name, attributes=1):
    data = bytearray(320)
    struct.pack_into('<IQQQIIII', data, 0, attributes, 11, 12, 13, 0, 99, 0, 0)
    raw = name.encode()
    data[44:44+len(raw)] = raw
    return bytes(data)


def fixture_stat(attributes=16, failed=False):
    if failed:
        return struct.pack('<7I', 1, 0, 32, 0, 0, 0, 0) + bytes(52)
    info = struct.pack('<IQQQIIIIII', attributes, 11, 12, 13, 7, 0, 99, 1, 0, 77)
    return struct.pack('<7I', 1, 1, 0, 1, 0, 1, 0) + info


def fixture(root='C:/controlled/data', failed=False):
    header = bytearray(160)
    header[:8] = MAGIC
    struct.pack_into('<10I', header, 8, 1, 160, 320, 52, 312, 77, 3, 5, 60, MAX_BYTES)
    header[48:112], header[112:144] = GENERATION.encode(), OPERATION.encode()
    records, sequence = [], 0
    def emit(kind, body):
        nonlocal sequence
        records.append(struct.pack('<III', kind, len(body), sequence) + body)
        sequence += 1
    emit(1, struct.pack('<I', len(root)) + fixture_stat() + root.encode())
    rows = 0
    for ordinal, branch in enumerate(BRANCHES):
        emit(2, struct.pack('<4I', ordinal, UINT32_MAX, ordinal, len(branch)) + fixture_stat() + branch.encode())
        # Deliberately retain an unsorted arrival order, including traversal aliases.
        for arrival, name in enumerate(('z.texture', '.', 'a.texture', '..')):
            alias = name in ('.', '..')
            flags = 3 if alias else 1
            stat_packet = fixture_stat(16 if alias else 1, failed=failed and ordinal == 0 and arrival == 0)
            emit(3, struct.pack('<3I', ordinal, arrival, flags) +
                 fixture_projection(name, 16 if alias else 1) + stat_packet)
            rows += 1
        emit(4, struct.pack('<6I', ordinal, 4, 0, 18, 1, 0))
    emit(5, struct.pack('<9I', 5, 5, rows, 1 if failed else 0, 1, 0 if failed else 1, 17, 0, 0))
    return bytes(header) + b''.join(records)


def controlled_c_checks():
    """Actual C functions with manually declared controlled Win32 API types.

    This is neither SDK layout qualification nor a real filesystem observation.
    """
    compiler = shutil.which('cc')
    require(compiler is not None, 'Portable C compiler required')
    fake = r'''
#ifndef CONTROLLED_WINDOWS_H
#define CONTROLLED_WINDOWS_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <strings.h>
typedef uint32_t DWORD;
typedef unsigned long long ULONGLONG;
typedef int BOOL;
typedef void *HANDLE;
typedef struct {DWORD dwLowDateTime,dwHighDateTime;} FILETIME;
typedef struct {
 DWORD dwFileAttributes;FILETIME ftCreationTime,ftLastAccessTime,ftLastWriteTime;
 DWORD nFileSizeHigh,nFileSizeLow,dwReserved0,dwReserved1;char cFileName[260],cAlternateFileName[14];
} WIN32_FIND_DATAA;
typedef struct {
 DWORD dwFileAttributes;FILETIME ftCreationTime,ftLastAccessTime,ftLastWriteTime;
 DWORD dwVolumeSerialNumber,nFileSizeHigh,nFileSizeLow,nNumberOfLinks,nFileIndexHigh,nFileIndexLow;
} BY_HANDLE_FILE_INFORMATION;
typedef struct {unsigned char DeleteFile;} FILE_DISPOSITION_INFO;
#define TRUE 1
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define GENERIC_READ 1u
#define GENERIC_WRITE 2u
#define DELETE 4u
#define FILE_READ_ATTRIBUTES 8u
#define FILE_SHARE_READ 1u
#define FILE_SHARE_WRITE 2u
#define OPEN_EXISTING 3u
#define CREATE_NEW 4u
#define FILE_FLAG_BACKUP_SEMANTICS 8u
#define FILE_ATTRIBUTE_NORMAL 128u
#define FILE_ATTRIBUTE_DIRECTORY 16u
#define FILE_ATTRIBUTE_READONLY 1u
#define FILE_ATTRIBUTE_REPARSE_POINT 1024u
#define ERROR_NOT_SUPPORTED 50u
#define ERROR_FILE_NOT_FOUND 2u
#define ERROR_NO_MORE_FILES 18u
#define FileDispositionInfo 4
#define _stricmp strcasecmp
#define _strnicmp strncasecmp
static int scenario,creates,informs,closes;
static DWORD native_error;
static ULONGLONG GetTickCount64(void) {return 100;}
static DWORD GetCurrentProcessId(void) {return 312;}
static DWORD GetCurrentThreadId(void) {return 77;}
static DWORD GetLastError(void) {return native_error;}
static HANDLE CreateFileA(const char *path,DWORD access,DWORD share,void *security,DWORD disposition,DWORD flags,void *unused) {
 (void)path;(void)security;(void)unused;
 if(disposition==OPEN_EXISTING) {
  if(access!=GENERIC_READ||share!=(FILE_SHARE_READ|FILE_SHARE_WRITE)||flags!=FILE_FLAG_BACKUP_SEMANTICS)return INVALID_HANDLE_VALUE;
  ++creates;if(scenario==1){native_error=32;return INVALID_HANDLE_VALUE;}
  return (HANDLE)(intptr_t)1;
 }
 return INVALID_HANDLE_VALUE;
}
static BOOL GetFileInformationByHandle(HANDLE handle,BY_HANDLE_FILE_INFORMATION *value) {
 (void)handle;++informs;
 if(scenario==2){native_error=5;return 0;}
 memset(value,0,sizeof(*value));value->dwFileAttributes=1;value->nFileSizeHigh=123;value->nFileSizeLow=456;
 value->nNumberOfLinks=7;value->nFileIndexHigh=89;value->nFileIndexLow=90;return 1;
}
static BOOL CloseHandle(HANDLE handle) {(void)handle;++closes;if(scenario==3){native_error=6;return 0;}return 1;}
static BOOL WriteFile(HANDLE h,const void *p,DWORD n,DWORD *done,void *o){(void)h;(void)p;(void)o;*done=n;return 1;}
static HANDLE FindFirstFileA(const char *p,WIN32_FIND_DATAA *d){(void)p;(void)d;return INVALID_HANDLE_VALUE;}
static BOOL FindNextFileA(HANDLE h,WIN32_FIND_DATAA *d){(void)h;(void)d;return 0;}
static BOOL FindClose(HANDLE h){(void)h;return 1;}
static BOOL FlushFileBuffers(HANDLE h){(void)h;return 1;}
static BOOL SetFileInformationByHandle(HANDLE h,int k,const void *p,DWORD n){(void)h;(void)k;(void)p;(void)n;return 1;}
#endif
'''
    driver = r'''
#include <assert.h>
#define main controlled_unexecuted_native_main
#include "native_client_wfd_probe.c"
#undef main
static uint32_t take32(const unsigned char *p) {return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
int main(void) {
 WIN32_FIND_DATAA native;unsigned char projection[320],packet[80];BY_HANDLE_FILE_INFORMATION information;
 ProbeState state;char path[260];unsigned int i;
 assert(sizeof(native)==320&&sizeof(information)==52); /* Controlled types, not SDK. */
 memset(&native,0xA5,sizeof(native));native.dwFileAttributes=0x103;
 native.ftLastWriteTime.dwLowDateTime=0x11223344;native.ftLastWriteTime.dwHighDateTime=0x55667788;
 native.nFileSizeHigh=0x99AABBCC;native.nFileSizeLow=0xDDEEFF00;
 strcpy(native.cFileName,".named-file");strcpy(native.cAlternateFileName,"NAMED~1.TXT");
 assert(canonical_wfd(&native,projection));
 assert(take32(projection)==0x103&&take32(projection+20)==0x11223344&&take32(projection+24)==0x55667788);
 assert(take32(projection+28)==0x99AABBCC&&take32(projection+32)==0xDDEEFF00);
 for(i=36;i<44;i++)assert(!projection[i]);for(i=318;i<320;i++)assert(!projection[i]);
 for(i=44+strlen(".named-file");i<304;i++)assert(!projection[i]);
 assert(absolute_path("Z:\\owned\\data",path)&&!strcmp(path,"Z:/owned/data"));
 assert(!absolute_path("Z:/owned/data.",path)&&!absolute_path("Z:/owned/data /outside",path));
 assert(!absolute_path("Z:/owned/../data",path)&&!absolute_path("Z:/owned//data",path));
 for(scenario=0;scenario<4;scenario++) {
  int result;memset(&state,0,sizeof(state));state.deadline=1000;state.readability_complete=1;
  creates=informs=closes=0;result=readable(&state,"controlled",packet,&information);
  assert(creates==1&&informs==(scenario!=1)&&closes==(scenario!=1));
  assert(result==(scenario==0));
  if(scenario==1)assert(take32(packet+8)==32&&!take32(packet+4));
  if(scenario==2){assert(take32(packet+16)==5&&!take32(packet+12));for(i=28;i<80;i++)assert(!packet[i]);}
  if(scenario==3)assert(take32(packet+24)==6&&!take32(packet+20));
  if(!scenario)assert(take32(packet+28+32)==123&&take32(packet+28+36)==456&&take32(packet+28+48)==90);
 }
 puts("CONTROLLED_WFD_C_PASS cases=4 canonical_projection=1 path_alias_refusal=1 SDK=0 authority=0");return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='coh-wfd-controlled-c-') as temporary:
        root = Path(temporary)
        (root/'windows.h').write_text(fake)
        (root/'fixture.c').write_text(driver)
        (root/'native_client_wfd_probe.c').write_bytes(SOURCE.read_bytes())
        built = subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-I',str(root),
                                'fixture.c','-o','fixture'],cwd=root,capture_output=True,text=True)
        require(built.returncode == 0, 'Controlled C probe compile failed: '+built.stdout+built.stderr)
        run = subprocess.run([str(root/'fixture')],capture_output=True,text=True,timeout=5)
        require(run.returncode == 0 and 'CONTROLLED_WFD_C_PASS' in run.stdout,
                'Controlled C probe API fixture failed: '+run.stdout+run.stderr)
        return run.stdout


def native_windows_checks(probe, output):
    require(os.name == 'nt', 'Actual Windows host required')
    probe, output = Path(probe).resolve(), Path(output)
    require(probe.is_file() and not probe.is_symlink(), 'Actual built Win32 probe required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                                  ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    cases = []
    with tempfile.TemporaryDirectory(prefix='coh-wfd-native-') as temporary:
        base = Path(temporary)
        data = base / 'data'
        created = []
        for branch in BRANCHES:
            directory = data / branch
            for relative in ('empty', '.named-dir', '_excluded'):
                (directory / relative).mkdir(parents=True)
            for relative in ('ordinary.txt', '.named-file', '.named-dir/readonly.txt', '_excluded/nontexture.geo'):
                path = directory / relative
                path.write_bytes(b'controlled metadata only\n')
                path.chmod(0o444)
                created.append(path)
        def invoke(label, destination):
            run = subprocess.run([str(probe), str(data), str(destination), GENERATION, OPERATION, '60'],
                                 capture_output=True, timeout=90)
            lines = [line for line in run.stdout.decode('ascii', 'strict').splitlines() if line.startswith(MARKER)]
            require(len(lines) == 1, 'Current native helper cleanup receipt missing')
            receipt = json.loads(lines[0][len(MARKER):])
            require(receipt['operation'] == OPERATION and receipt['generation'] == GENERATION
                    and receipt['provider_authority'] is False and receipt['publication_allowed'] is False,
                    'Native helper cannot grant authority')
            result, packet = None, b''
            if destination.exists():
                packet = destination.read_bytes()
                if receipt['output_created']:
                    result = parse(packet, GENERATION, OPERATION, str(data), receipt['windows_pid'])
            cases.append({'label': label, 'returncode': run.returncode, 'receipt': receipt,
                          'status': result['status'] if result else None,
                          'stdout_base64': base64.b64encode(run.stdout).decode(),
                          'stderr_base64': base64.b64encode(run.stderr).decode(),
                          'packet_base64': base64.b64encode(packet).decode(),
                          'packet_bytes': len(packet),
                          'packet_sha256': hashlib.sha256(packet).hexdigest() if packet else None})
            return run, receipt, result
        held = None
        try:
            destination = base / 'complete.bin'
            run, receipt, result = invoke('complete_readonly_named_dot_empty_branches', destination)
            require(run.returncode == 0 and result['status'] == 'complete_observation'
                    and receipt['output_handle_closed'] is True, 'Actual Win32 complete fixture failed')
            paths = {d['relative'] for d in result['directories']}
            require(all(branch + '/.named-dir' in paths and branch + '/empty' in paths and
                        branch + '/_excluded' in paths for branch in BRANCHES),
                    'Native named-dot/empty/excluded directory graph lost')
            expected_rows = result['footer']['rows']
            original = hashlib.sha256(destination.read_bytes()).hexdigest()
            run, receipt, _ = invoke('existing_output_refused', destination)
            require(run.returncode != 0 and receipt['output_created'] is False
                    and hashlib.sha256(destination.read_bytes()).hexdigest() == original,
                    'Existing output bytes were modified')
            held = kernel.CreateFileW(str(created[0]), 0x80000000, 0, None, 3, 0, None)
            require(held not in (None, ctypes.c_void_p(-1).value), 'Exclusive readability fixture handle failed')
            run, receipt, result = invoke('sharing_denial_explicit_incomplete', base / 'denied.bin')
            require(run.returncode != 0 and result['status'] == 'incomplete_observation'
                    and not result['footer']['readability_complete']
                    and any(row['by_handle']['create_error'] == 32 for d in result['directories']
                            for row in d['entries']), 'Native sharing denial became absence/success')
            kernel.CloseHandle(held)
            held = None
            run, receipt, _ = invoke('output_inside_readonly_inputs_refused', data / 'forbidden.bin')
            require(run.returncode == 64 and not (data / 'forbidden.bin').exists(), 'Probe wrote into readonly inputs')
        finally:
            if held not in (None, ctypes.c_void_p(-1).value):
                kernel.CloseHandle(held)
            for path in created:
                path.chmod(0o666)
    receipt = {'format': 1, 'role': 'Windows_SDK_readonly_ANSI_metadata_probe_fixture', 'status': 'passed',
               'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
               'probe': {'bytes': probe.stat().st_size, 'sha256': hashlib.sha256(probe.read_bytes()).hexdigest()},
               'observed_ABI': {'pointer_bits': 32, 'WFD_bytes': 320, 'by_handle_bytes': 52, 'header_bytes': 160},
               'actual_windows_sdk_executed': True, 'native_Wine_executed': False, 'native_Game_executed': False,
               'physical_device_executed': False, 'current_provider_generation_qualified': False,
               'provider_authority': False, 'publication_allowed': False, 'cases': cases, 'observed_rows': expected_rows}
    require(not output.exists() and not output.is_symlink(), 'Fresh native SDK fixture receipt required')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


class ProbeParserTests(unittest.TestCase):
    def test_actual_c_projection_and_readability_faults_are_controlled_only(self):
        self.assertIn('SDK=0 authority=0', controlled_c_checks())

    def test_original_native_arrival_and_partial_root_without_authority(self):
        value = parse(fixture(), GENERATION, OPERATION, 'C:/controlled/data', 312)
        self.assertEqual(value['status'], 'complete_observation')
        self.assertEqual([r['wfd']['name'] for r in value['directories'][0]['entries']],
                         ['z.texture', '.', 'a.texture', '..'])
        self.assertTrue(value['root']['partial_anchor'])
        self.assertFalse(value['provider_authority'])

    def test_failed_readability_is_explicit_incomplete(self):
        value = parse(fixture(failed=True), GENERATION, OPERATION, 'C:/controlled/data')
        self.assertEqual(value['status'], 'incomplete_observation')
        self.assertEqual(value['directories'][0]['entries'][0]['by_handle']['create_error'], 32)

    def test_complete_readability_cannot_include_unknown_or_malformed_names(self):
        for flags in (0, 17):
            packet = bytearray(fixture())
            offset = HEADER_BYTES
            while u32(packet, offset) != 3:
                offset += 12 + u32(packet, offset + 4)
            struct.pack_into('<I', packet, offset + 20, flags)
            with self.subTest(flags=flags), self.assertRaisesRegex(ValueError, 'Complete readability'):
                parse(bytes(packet), GENERATION, OPERATION, 'C:/controlled/data')

    def test_wrong_binding_or_pid_refused(self):
        for generation, operation, root, pid in [
            ('3'*64, OPERATION, 'C:/controlled/data', 312),
            (GENERATION, '3'*32, 'C:/controlled/data', 312),
            (GENERATION, OPERATION, 'C:/other/data', 312),
            (GENERATION, OPERATION, 'C:/controlled/data//', 312),
            (GENERATION, OPERATION, 'C:/controlled//data', 312),
            (GENERATION, OPERATION, 'C:/controlled/./data', 312),
            (GENERATION, OPERATION, 'C:/controlled/data./', 312),
            (GENERATION, OPERATION, 'C:/controlled/data', 313),
            (GENERATION, OPERATION, 'C:/controlled/data', 312.0)]:
            with self.assertRaises(ValueError):
                parse(fixture(), generation, operation, root, pid)

    def test_header_padding_version_and_bounds_refused(self):
        for offset, raw in [(0, b'X'), (8, struct.pack('<I', 2)), (12, struct.pack('<I', 96)),
                            (16, struct.pack('<I', 319)), (20, struct.pack('<I', 51)),
                            (144, b'X'), (44, struct.pack('<I', MAX_BYTES + 1))]:
            data = bytearray(fixture())
            data[offset:offset+len(raw)] = raw
            with self.assertRaises(ValueError):
                parse(bytes(data), GENERATION, OPERATION, 'C:/controlled/data')

    def test_truncation_sequence_unknown_record_and_extra_bytes_refused(self):
        good = fixture()
        for value in (good[:159], good[:-1], good + b'\0', bytes(MAX_BYTES + 1)):
            with self.assertRaises(ValueError):
                parse(value, GENERATION, OPERATION, 'C:/controlled/data')
        for offset, number in [(160, 88), (168, 3), (164, UINT32_MAX)]:
            data = bytearray(good)
            struct.pack_into('<I', data, offset, number)
            with self.assertRaises(ValueError):
                parse(bytes(data), GENERATION, OPERATION, 'C:/controlled/data')

    def test_unknown_by_handle_fields_are_not_filled(self):
        packet = bytearray(fixture_stat(failed=True))
        packet[28] = 1
        with self.assertRaises(ValueError):
            parse_stat(bytes(packet))

    def test_native_source_has_exact_read_only_apis_and_handle_cleanup(self):
        text = SOURCE.read_text()
        for expected in ('FindFirstFileA(', 'FindNextFileA(', 'FindClose(', 'GetFileInformationByHandle(',
                         'GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE', 'CREATE_NEW',
                         'SetFileInformationByHandle(state.output,FileDispositionInfo', 'PROBE_HEADER_BYTES 160u'):
            self.assertIn(expected, text)
        self.assertNotIn('DeleteFileA(', text)
        self.assertNotIn('ReadFile(', text)
        self.assertNotIn('PigFile', text)

    def test_windows_fixture_cannot_be_claimed_on_portable_host(self):
        if os.name != 'nt':
            with self.assertRaisesRegex(ValueError, 'Actual Windows'):
                native_windows_checks(Path('absent.exe'), Path('absent.json'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--windows-qualify', action='store_true')
    parser.add_argument('--probe', type=Path)
    parser.add_argument('--output', type=Path)
    args, remaining = parser.parse_known_args()
    if args.windows_qualify:
        require(args.probe is not None and args.output is not None, 'Actual probe/output required')
        print(json.dumps(native_windows_checks(args.probe, args.output)))
    else:
        unittest.main(argv=[__file__, *remaining])
