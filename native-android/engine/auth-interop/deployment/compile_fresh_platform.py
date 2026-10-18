#!/usr/bin/env python3
"""Compile exactly two production Windows x64 objects; never execute the probe.

Reuses the retained immutable OpenSSL headers/library inventory. A syntax-only
MSVC pass discovers actual headers; all are pinned before the sole codegen pass.
No original services, crypto algorithms, controllers, zlib or CLI are compiled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess

PREFIX = 'native-android/engine/auth-interop/'
OWNER = PREFIX+'fresh-character-owner/'
SOURCES = (OWNER+'probe/windows/fresh_probe_windows.c', OWNER+'probe/fresh_probe_policy.c')
PROJECT_INPUTS = (*SOURCES, OWNER+'fresh_character_owner.h', OWNER+'probe/fresh_probe_platform.h',
    OWNER+'probe/fresh_probe_policy.h', PREFIX+'deployment/windows/winsock_compat.h',
    PREFIX+'deployment/windows/db_udp_winsock.h', 'native-android/engine/auth/coh_auth.h',
    'native-android/engine/coh_contracts.h', 'native-android/engine/dbclient/coh_db_session.h',
    'native-android/engine/dbclient/coh_dbclient.h', 'native-android/engine/login/coh_login.h',
    'native-android/engine/network/coh_net.h', 'native-android/engine/network/coh_net_udp.h',
    'native-android/include/coh_native_core.h', 'native-android/protocol/coh_protocol.h',
    PREFIX+'deployment/compile_fresh_platform.py')
CRYPTO_MANIFEST_SHA = '1c1c05eb10132e4d1d172d29a04d36311981e6c7023c7ee388348339c460896b'
CRYPTO_LIBRARY_SHA = '95aec97b796992a58f8745e1bbbc6eac634931420f13b0763d2db57537543698'
CRYPTO_ARCHIVE_SHA = 'aa7a1badbeb8926cec15009f7f87ebb797aa2345c0c97a183cd1e23866a3499b'
DEFINES = ('_CRT_SECURE_NO_WARNINGS', 'WIN32_LEAN_AND_MEAN', '_WIN32_WINNT=0x0601', 'WINVER=0x0601')


def need(value, code):
    if not value:
        raise ValueError(code)


def identity(path, maximum=64*1024**2):
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'SYMLINK')
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        need(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, 'REGULAR_BOUNDED_FILE')
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
         (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns), 'FILE_CHANGED')
    return {'bytes': before.st_size, 'sha256': digest}


def safe_path(path):
    need(not any(c in str(path) for c in '\r\n\0%!^"&|<>()'), 'COMMAND_PATH')
    return str(path)


def batch_text(vcvars, command):
    safe_path(vcvars)
    for token in command:
        safe_path(token)
    return ('@echo off\r\ncall "'+str(vcvars)+'" x64 >nul\r\nif errorlevel 1 exit /b 1\r\n'
            + subprocess.list2cmdline(list(map(str, command)))+'\r\nexit /b %errorlevel%\r\n')


def source_state(root, revision):
    result = {}
    for name in PROJECT_INPUTS:
        path = root/name
        row = identity(path, 8*1024**2)
        blob = subprocess.check_output(['git','-C',str(root),'show',revision+':'+name], timeout=30)
        need(hashlib.sha256(blob).hexdigest() == row['sha256'], 'CURRENT_COMMITTED_SOURCE')
        result[name] = row
    return result


def admit_crypto(directory):
    manifest = directory/'manifest.json'
    need(identity(manifest) == {'bytes':58665,'sha256':CRYPTO_MANIFEST_SHA}, 'CRYPTO_MANIFEST')
    value = json.loads(manifest.read_bytes())
    need(value['schema'] == 'coh-intact-openssl-build-ownership-v1' and len(value['files']) == 384
         and value['total_bytes'] == 105629748, 'CRYPTO_INVENTORY')
    for name, row in value['files'].items():
        path = PurePosixPath(name)
        need(path.as_posix()==name and not path.is_absolute() and path.parts and
             all(p not in ('','.','..') for p in path.parts) and '\\' not in name and ':' not in name,
             'CRYPTO_MEMBER')
        need(set(row)=={'bytes','sha256'} and type(row['bytes']) is int and
             0<=row['bytes']<=64*1024**2 and re.fullmatch('[a-f0-9]{64}',row['sha256']), 'CRYPTO_MEMBER_PIN')
        need(identity(directory/name)==row, 'CRYPTO_FILE')
    need(sum(r['bytes'] for r in value['files'].values())==105629748 and
         value['files']['libcrypto.lib']['sha256']==CRYPTO_LIBRARY_SHA and
         {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}==set(value['files'])|{'manifest.json'},
         'CRYPTO_EXACT_FILES')
    return value['files']


def includes(raw):
    result = set()
    for line in raw.decode('utf-8', errors='strict').splitlines():
        match = re.match(r'^\s*Note: including file:\s*(.*?)\s*$', line)
        if match:
            result.add(Path(match.group(1)).resolve())
    need(result, 'COMPILER_HEADER_TRACE')
    return result


def coff(raw):
    need(20<=len(raw)<=16*1024**2, 'COFF_EXTENT')
    machine,sections,_,symbols,count,optional,_ = struct.unpack_from('<HHIIIHH',raw)
    need(machine==0x8664 and 0<sections<4096 and optional==0 and
         20+40*sections<=len(raw) and (not count or symbols+18*count<=len(raw)), 'COFF_X64_OBJECT')
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'machine':machine,'sections':sections}


def archive_objects(raw, objects):
    need(raw.startswith(b'!<arch>\n') and len(raw)<=32*1024**2, 'STATIC_ARCHIVE')
    at,members=8,[]
    while at<len(raw):
        need(at+60<=len(raw), 'ARCHIVE_HEADER')
        header=raw[at:at+60];need(header[58:]==b'`\n','ARCHIVE_TRAILER')
        size=int(header[48:58]);at+=60;need(0<=size<=len(raw)-at,'ARCHIVE_MEMBER_EXTENT')
        name=header[:16].decode('ascii').strip();body=raw[at:at+size]
        if name not in ('/','//'):
            members.append(coff(body)['sha256'])
        at+=size+(size&1)
    need(at==len(raw) and sorted(members)==sorted(row['sha256'] for row in objects.values()) and len(members)==2,
         'EXACT_TWO_ARCHIVE_OBJECTS')
    return len(members)


def compile_platform(root, crypto, output, revision):
    need(os.name=='nt' and re.fullmatch('[a-f0-9]{40}',revision), 'WINDOWS_COMPILE_ONLY')
    root,crypto,output = (p.absolute() for p in (root,crypto,output))
    for p in (root,crypto,output):
        safe_path(p);need(not any(x.is_symlink() for x in (p,*p.parents)), 'ROOT_SYMLINK')
    need(not output.exists() and root!=output and crypto!=output and crypto not in output.parents
         and output not in crypto.parents, 'FRESH_OUTPUT')
    current = subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],timeout=30).decode().strip()
    need(current==revision, 'EXACT_REVISION')
    before=source_state(root,revision);crypto_before=admit_crypto(crypto)
    output.mkdir(parents=True)
    stage='TOOLS'
    try:
        program_files=Path(os.environ['ProgramFiles(x86)'])
        vswhere=program_files/'Microsoft Visual Studio/Installer/vswhere.exe'
        query=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires',
            'Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],timeout=30)
        paths=query.decode('utf-8').strip().splitlines();need(len(paths)==1, 'ONE_MSVC_INSTALLATION')
        installation=Path(paths[0]);safe_path(installation)
        marker=installation/'VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt'
        version=marker.read_text().strip();need(re.fullmatch(r'14\.\d+\.\d+',version), 'MSVC_TOOLSET')
        toolset=installation/'VC/Tools/MSVC'/version
        tools=toolset/'bin/Hostx64/x64';cl,lib=tools/'cl.exe',tools/'lib.exe'
        vcvars=installation/'VC/Auxiliary/Build/vcvarsall.bat'
        command_processor=Path(os.environ['SystemRoot'])/'System32/cmd.exe'
        tool_paths=[vswhere,marker,vcvars,command_processor,cl,lib,tools/'c1.dll',tools/'c2.dll',tools/'1033/clui.dll']
        tool_before={str(p):identity(p,256*1024**2) for p in tool_paths}
        sdk=program_files/'Windows Kits/10/Include'
        allowed_system=(toolset/'include',sdk)
        environment=dict(os.environ,VSLANG='1033',CL='',_CL_='')
        commands=[]

        def run(label, command):
            script=output/(label+'.cmd');script.write_bytes(batch_text(vcvars,command).encode('ascii'))
            child=subprocess.run([str(command_processor),'/d','/c',str(script)],cwd=output,
                                 env=environment,capture_output=True,timeout=180)
            raw=child.stdout+child.stderr
            (output/(label+'.log')).write_bytes(raw)
            need(len(raw)<=2*1024**2 and child.returncode==0, 'COMPILER_COMMAND_'+label.upper())
            commands.append({'label':label,'command':list(map(str,command)),'returncode':child.returncode})
            return raw

        flags=['/nologo','/TC','/std:c11','/W4','/WX','/MT','/showIncludes',
               *('/D'+d for d in DEFINES),'/I'+str(crypto/'include'),'/I'+str(root/'native-android/include')]
        headers=set();per_source={}
        stage='HEADER_DISCOVERY'
        for name in SOURCES:
            stem=Path(name).stem
            found=includes(run('syntax-'+stem,[cl,*flags,'/Zs',root/name]))
            per_source[name]=found;headers.update(found)
        project_headers={p.relative_to(root).as_posix() for p in headers if p.is_relative_to(root)}
        need(project_headers==set(PROJECT_INPUTS)-set(SOURCES)-{PREFIX+'deployment/compile_fresh_platform.py'}, 'EXACT_PROJECT_HEADER_CLOSURE')
        crypto_headers=set()
        for p in headers:
            if p.is_relative_to(root):
                continue
            if p.is_relative_to(crypto):
                relative=p.relative_to(crypto).as_posix();need(relative in crypto_before,'ADMITTED_CRYPTO_HEADER');crypto_headers.add(relative)
            else:
                need(any(p.is_relative_to(directory) for directory in allowed_system), 'SDK_HEADER_OWNER')
        need(crypto_headers, 'REAL_OPENSSL_HEADERS')
        header_before={str(p):identity(p,16*1024**2) for p in sorted(headers)}
        stage='CODE_GENERATION';objects={}
        for name in SOURCES:
            stem=Path(name).stem;object_file=output/(stem+'.obj')
            found=includes(run('compile-'+stem,[cl,*flags,'/O2','/c','/Fo'+str(object_file),root/name]))
            need(found==per_source[name], 'COMPILE_HEADER_CLOSURE_CHANGED')
            objects[object_file.name]=coff(object_file.read_bytes())
        stage='ARCHIVE'
        library=output/'coh-fresh-platform.lib'
        run('archive',[lib,'/nologo','/OUT:'+str(library),*(output/name for name in objects)])
        archive_objects(library.read_bytes(),objects)
        stage='FINAL_INPUT_ADMISSION'
        need(source_state(root,revision)==before and admit_crypto(crypto)==crypto_before, 'PROJECT_OR_CRYPTO_CHANGED')
        need(tool_before=={str(p):identity(p,256*1024**2) for p in tool_paths}, 'COMPILER_CHANGED')
        need(header_before=={str(p):identity(p,16*1024**2) for p in sorted(headers)}, 'HEADERS_CHANGED')
        need(subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],timeout=30).decode().strip()==revision,'REVISION_CHANGED')
        receipt={'schema':'coh-fresh-platform-msvc-x64-compile-v1','passed':True,'revision':revision,
            'project_source_inputs':before,'actual_compiler_tools':tool_before,'actual_included_headers':header_before,
            'production_defines':list(DEFINES),'commands':commands,'objects':objects,'static_library':identity(library),
            'retained_crypto':{'artifact_id':12078663003,'archive_sha256_reference':CRYPTO_ARCHIVE_SHA,
                'manifest_sha256':CRYPTO_MANIFEST_SHA,'library_sha256':CRYPTO_LIBRARY_SHA,'files_revalidated':384,'bytes_revalidated':105629748},
            'production_Windows_headers_compiled':True,'exact_two_x64_objects_archived':True,
            'inputs_unchanged_after_compile':True,'syntax_only_header_discovery_pass':True,
            'crypto_or_server_or_zlib_or_model_rebuilt':False,'CLI_linked':False,'probe_executed':False,
            'Windows_backend_APIs_executed':False,'original_services_executed':False,'world_authority':False}
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        return receipt
    except Exception:
        (output/'failure.json').write_text(json.dumps({'schema':'coh-fresh-platform-compile-refusal-v1','passed':False,
            'stage':stage,'probe_executed':False,'original_services_executed':False,'world_authority':False})+'\n')
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',required=True,type=Path)
    parser.add_argument('--crypto-dir',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--expected-commit',required=True)
    args=parser.parse_args()
    try:
        result=compile_platform(args.source_root,args.crypto_dir,args.output,args.expected_commit)
    except Exception:
        print(json.dumps({'passed':False,'compile_refused':True,'probe_executed':False,'world_authority':False}))
        return 1
    print(json.dumps({'passed':True,'objects':len(result['objects']),'CLI_linked':False,'probe_executed':False}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
