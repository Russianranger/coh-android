#!/usr/bin/env python3
"""Qualify auth-only staging without claiming a Windows service or real login."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile

import auth_service_profile as profile
import hosted_auth_stage as prior
import qualify_windows_adapter
from source_audit import decoded, extract

HERE = Path(__file__).resolve().parent


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, timeout=120, **kwargs)
    if result.returncode:
        raise ValueError('auth_only_host_command_failed:' + result.stderr.decode(errors='replace')[:4000])
    return result.stdout


def original_sources(root):
    tree = run(['git', '-C', root, 'rev-parse', 'HEAD:upstream/ouroboros']).decode().strip()
    if tree != prior.ORIGINAL_TREE:
        raise ValueError('auth_only_original_source_tree_mismatch')
    paths = ('Config.cpp', 'Parser.cpp', 'Parser.h')
    return {name: decoded(run(['git', '-C', root, 'show', 'HEAD:upstream/ouroboros/AuthServer/src/' + name])) for name in paths}


def const_method(source, name):
    match = re.search(r'(?m)^[^\n;{}]*\b' + re.escape(name) + r'\([^;{}]*\) const\s*\{', source)
    if not match:
        raise ValueError('original_const_method_missing')
    cursor = source.index('{', match.start()) + 1
    depth = 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[match.start():cursor]


def qualify_profile(root, directory, sanitize):
    source = original_sources(root)
    functions = {name: extract(source['Parser.cpp'], name) for name in ('IsDigit', 'IsSpace', 'IsWhiteSpace', 'IsAlpha', 'GetToken')}
    functions.update({name: const_method(source['Config.cpp'], 'Config::' + name) for name in ('Get', 'GetInt', 'GetBool')})
    load = extract(source['Config.cpp'], 'Config::Load')
    begin, end = load.index('        std::istrstream inp('), load.index('        delete pBuf;')
    block = load[begin:end]
    text = profile.configuration('cohauth-ci-' + 'a'*24, 'ODBC Driver 17 for SQL Server', [21000,21001,21002], 'C:\\private dir\\logs')
    expected = {}
    for line in text.splitlines():
        key, value = line.removesuffix(';').split(' = ', 1)
        expected[key] = value[1:-1] if value.startswith('"') else value
    code = '''#include <map>
#include <string>
#include <strstream>
#include <cstring>
#include <strings.h>
#include <cstdlib>
#include <cstdio>
#define LOG_ERROR 1
#define _stricmp strcasecmp
struct QuietLog {unsigned errors=0;template<class... A>void AddLog(int,const char*,A...){errors++;}} logger;
struct iless {bool operator()(const std::string&a,const std::string&b)const{return strcasecmp(a.c_str(),b.c_str())<0;}};
typedef std::map<std::string,std::string,iless> StringMap;
class Config{public:StringMap map; const char*Get(const char*)const;int GetInt(const char*,int=0)const;bool GetBool(const char*,bool=false)const;};
''' + source['Parser.h'] + '\n' + '\n'.join(functions.values()) + '''
static Config parse(char*pBuf,int size){Config c;StringMap &map=c.map; const char *filename="known-public-profile";
''' + block + '''return c;}
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x))return 1;}while(0)
int main(){std::string text=''' + json.dumps(text) + ''';Config c=parse(text.data(),(int)text.size());
CHECK(logger.errors==0); CHECK(c.map.size()==''' + str(len(expected)) + ''');
''' + '\n'.join('CHECK(c.Get(' + json.dumps(key) + ') && !strcmp(c.Get(' + json.dumps(key) + '),' + json.dumps(value) + '));' for key,value in expected.items()) + '''
CHECK(c.GetBool("Encrypt"));CHECK(c.GetBool("DesApply"));CHECK(c.GetInt("ProtocolVersion")==191021);
CHECK(c.GetInt("PayStatOverride")==-1);CHECK(!c.GetBool("FreeServer"));CHECK(!c.GetBool("useQueue"));
CHECK(!c.GetBool("DumpPacket"));CHECK(!c.GetBool("enableVerboseLogging"));CHECK(!c.GetBool("enableDebugLogging"));
CHECK(c.GetInt("serverPort")==21000);CHECK(c.GetInt("serverExPort")==21001);CHECK(c.GetInt("serverIntPort")==21002);
printf("{\\"passed\\":true,\\"checks\\":%u,\\"full_config_load_executed\\":false,\\"real_account_login_verified\\":false}\\n",checks);return 0;}
'''
    generated = directory / 'original-config-parser.cpp'
    generated.write_text(code)
    results = {}
    for mode in (('release','asan_ubsan') if sanitize else ('release',)):
        flags = ['-O2'] if mode == 'release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        binary = directory / ('original-config-' + mode)
        run(['c++','-std=c++17',*flags,generated,'-o',binary])
        result = json.loads(run([binary], env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
        if result != {'passed': True, 'checks': len(expected)+14, 'full_config_load_executed': False, 'real_account_login_verified': False}:
            raise ValueError('original_config_parser_result_mismatch')
        results[mode] = {'binary_sha256': prior.sha(binary), 'result': result}
    return {'passed': True, 'scope': 'Unchanged original GetToken/helpers, Config::Load token/map block and three getters; file IO/platform/date assignments are not executed.',
            'original_source_tree': prior.ORIGINAL_TREE,
            'original_source_sha256_utf8_lf': {key:hashlib.sha256(value.encode()).hexdigest() for key,value in source.items()},
            'function_sha256': {key:hashlib.sha256(value.encode()).hexdigest() for key,value in functions.items()},
            'original_load_parser_block_sha256':hashlib.sha256(block.encode()).hexdigest(),
            'generated_oracle_sha256':prior.sha(generated), 'profile_keys': len(expected), 'executions':results}


def qualify_probe(root, directory, sanitize):
    native = root / 'native-android'
    windows = HERE / 'windows'
    (directory / 'fixture_constants.h').write_text(profile.fixture_header())
    sources = [windows/'auth_only_probe.c',native/'engine/login/coh_login.c',native/'engine/auth/coh_auth.c',
               native/'engine/auth/coh_auth_openssl.c',native/'src/coh_blowfish.c',native/'protocol/coh_protocol.c']
    results = {}
    for mode in (('release','asan_ubsan') if sanitize else ('release',)):
        binary = directory / ('auth-only-probe-' + mode)
        flags = ['-O2'] if mode=='release' else ['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        run(['cc','-std=c11',*flags,'-I'+str(directory),'-I'+str(native/'include'),*sources,'-lcrypto','-o',binary])
        environment = dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
        checks = 0
        for args in ([],['0','valid'],['60000','valid'],['21000','secret'],['127.0.0.1','valid'],['21000','corrupt-frame'],['21000','valid','extra']):
            result = subprocess.run([str(binary),*args],capture_output=True,timeout=15,env=environment)
            if result.returncode != 2 or result.stdout or result.stderr:
                raise ValueError('host_probe_invalid_arguments_not_refused')
            checks += 1
        # Reserve an owned local port without listen(). No external endpoint is
        # probed, and no mock peer is mislabeled as an original AuthServer.
        with socket.socket() as reservation:
            for attempt in range(64):
                port=20000+secrets.randbelow(40000)
                try:
                    reservation.bind(('127.0.0.1',port))
                    break
                except OSError:
                    if attempt==63: raise ValueError('host_probe_port_reservation_failed')
            result = subprocess.run([str(binary),str(port),'valid'],capture_output=True,timeout=15,env=environment)
            if result.returncode != 1 or result.stderr:
                raise ValueError('host_probe_connection_refusal_not_observed')
            value = json.loads(result.stdout)
            if (value.get('passed') is not False or value.get('socket_cleanup_complete') is not True
                    or value.get('password_retained_after_close') is not False or value.get('protocol') != 0
                    or value.get('state') != 12 or not value.get('system_error')
                    or value.get('db_handoff_attempted') is not False):
                raise ValueError('host_probe_failure_cleanup_failed')
            checks += 1
        results[mode]={'binary_sha256':prior.sha(binary),'checks':checks,'connection_refusal_receipt':value,
                       'real_windows_execution':False,'real_account_login_verified':False}
    return {'passed':True,'scope':'POSIX build of exact probe/core; invalid-argument and owned loopback refused-connection cleanup only.',
            'source_sha256':{str(path.relative_to(root)):prior.sha(path) for path in sources},'executions':results}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args()
    root=args.source_root.resolve()
    suite=subprocess.run(['python3','-m','unittest','-v','test_auth_login_stage'],cwd=HERE,capture_output=True,timeout=90)
    if suite.returncode: raise ValueError('auth_only_unit_suite_failed:'+suite.stderr.decode()[:4000])
    with tempfile.TemporaryDirectory(prefix='coh-auth-only-controls-') as name:
        directory=Path(name)
        result={'schema':'coh-auth-only-host-qualification-v1','passed':True,
                'repository_base':run(['git','-C',root,'rev-parse','HEAD']).decode().strip(),
                'unit_test_log':suite.stderr.decode(),
                'winsock_adapter':qualify_windows_adapter.qualify(args.sanitize),
                'original_profile_parser':qualify_profile(root,directory,args.sanitize),
                'native_probe':qualify_probe(root,directory,args.sanitize),
                'driver_sha256':prior.sha(HERE/'hosted_auth_login.py'),
                'profile_sha256':prior.sha(HERE/'auth_service_profile.py'),
                'real_windows_execution':False,'real_account_login_verified':False,
                'authenticated_db_map_handoff_verified':False,'physical_thor_accepted':False,
                'leak_sanitizer_enabled':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'unit_suites':20,'windows_syscall_controls_per_mode':46,
                      'original_parser_controls_per_mode':result['original_profile_parser']['executions']['release']['result']['checks'],
                      'native_probe_controls_per_mode':8,'real_account_login_verified':False}))


if __name__=='__main__':
    main()
