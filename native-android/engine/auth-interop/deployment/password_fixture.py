#!/usr/bin/env python3
"""Qualify a disposable credential fixture against unchanged original hashing.

No network, SQL, AuthServer, account lookup or real login occurs here. The native
request oracle uses its existing RSA-capture shell; it does not encrypt a frame.
"""
import argparse
import ctypes as C
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import tempfile
import zlib

from source_audit import decoded, digest, extract

HERE = Path(__file__).resolve().parent
AUTH = HERE.parent.parent / 'auth'
NATIVE = HERE.parents[2]
ACCOUNT = 'cohstage01'
PASSWORD = 'NativeStage2610!'


def run(command, **kwargs):
    result = subprocess.run([str(v) for v in command], capture_output=True, timeout=90, **kwargs)
    if result.returncode:
        # Original source/compiler diagnostics contain no private fixture rows.
        raise RuntimeError('password_control_failed: ' + result.stderr.decode(errors='replace')[:4096])
    return result.stdout


def sources(root):
    pins = json.loads((HERE / 'password-source-pins.json').read_text())['sha256_utf8_lf']
    values = {}
    for name, expected in pins.items():
        path = root / name
        value = decoded(path.read_bytes() if path.exists() else run(['git', '-C', root, 'show', 'HEAD:' + name]))
        if digest(value.encode()) != expected:
            raise ValueError('password_original_source_identity_mismatch')
        values[name] = value
    return values, pins


def salt(account):
    return int.from_bytes(zlib.adler32(account.encode()).to_bytes(4, 'big'), 'little')


def qualify(root, temporary, sanitize):
    values, pins = sources(root)
    crypt = temporary / 'cryptLib'
    for name, value in values.items():
        if '/libs/cryptLib/' in name:
            path = crypt / name.split('/libs/cryptLib/')[1]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
    original = extract(values['upstream/ouroboros/AuthServer/src/util.cpp'], 'EncPwdSha512')
    check = extract(values['upstream/ouroboros/AuthServer/src/Account.cpp'], 'CAccount::CheckPassword')
    fragment = re.search(r'cryptLib::digest512 hash;.*?passwd = \(char\*\)passwdSHA512;', check, re.S)
    if not fragment:
        raise ValueError('password_original_consumer_fragment_missing')
    # Existing qualified native request builder and public OpenSSL provider;
    # the existing shim captures the 94-byte RSA input without encryption.
    native_inputs = [AUTH / 'coh_auth.c', AUTH / 'coh_auth_openssl.c',
                     NATIVE / 'src/coh_blowfish.c', NATIVE / 'protocol/coh_protocol.c',
                     AUTH / 'tests/oracle_shim.c']
    native_headers = [AUTH / 'coh_auth.h', NATIVE / 'engine/coh_contracts.h',
                      NATIVE / 'include/coh_native_core.h', NATIVE / 'src/byte_reader.h',
                      NATIVE / 'protocol/coh_protocol.h']
    qualification_inputs = [Path(__file__).resolve(), HERE / 'password-source-pins.json',
                            HERE / 'source_audit.py', HERE / 'admit_schema.py', HERE.parent / 'source_oracle.py']
    library = temporary / 'native.so'
    run(['cc', '-std=c99', '-O2', '-fPIC', '-shared', '-I' + str(NATIVE / 'include'),
         *native_inputs, '-lcrypto', '-o', library])
    native = C.CDLL(str(library))
    native.auth_test_plain.argtypes = [C.c_char_p, C.c_char_p, C.c_uint32, C.c_void_p]
    rng = random.Random(261016)
    cases = [(ACCOUNT, PASSWORD)] + [('cohstage01' if i % 2 else 'saltprobe',
             ''.join(chr(rng.randrange(33, 127)) for _ in range(i % 17))) for i in range(68)]
    rows = []
    for account, password in cases:
        number = salt(account)
        expected = hashlib.sha512((password + f'{number:08x}').encode()).hexdigest()
        output = C.create_string_buffer(94)
        if native.auth_test_plain(account.encode(), password.encode(), 0x81234567, output) != 0:
            raise ValueError('native_password_request_failed')
        wire = output.raw[30:94]
        swapped = b''.join(bytes.fromhex(expected)[i:i+8][::-1] for i in range(0, 64, 8))
        if output.raw[:14].rstrip(b'\0') != account.encode() or wire != swapped:
            raise ValueError('native_password_derivation_mismatch')
        rows.append('{' + json.dumps(password) + ',' + str(number) + 'u,' + json.dumps(expected)
                    + ',{' + ','.join(str(b) for b in wire) + '}}')
    code = '''#include <cstring>
#include <cstdio>
#include <string>
#include "cryptlib/sha512.h"
using namespace std;
#define ENC_PWD_LEN 128
''' + original + '''
static void original_consumer(const char *dbpwdSHA512, char *output){
 unsigned char passwdSHA512[128]; char *passwd=0;
''' + fragment[0] + '''
 memcpy(output,passwd,128);
}
struct Row {const char *password; unsigned salt; const char *expected; unsigned char wire[64];};
static Row rows[]={''' + ',\n'.join(rows) + '''};
int main(){unsigned checks=0;for(const Row &row:rows){
 char password[129]={0},received[128];memcpy(password,row.password,strlen(row.password));
 EncPwdSha512(password,row.salt);if(memcmp(password,row.expected,128))return 1;checks++;
 original_consumer((const char*)row.wire,received);if(memcmp(received,row.expected,128))return 2;checks++;
 for(unsigned i=0;i<64;i++){unsigned char changed[64];memcpy(changed,row.wire,64);changed[i]^=1;
 original_consumer((const char*)changed,received);if(!memcmp(received,row.expected,128))return 3;checks++;}
 memset(password,0,sizeof(password));memset(received,0,sizeof(received));
 }printf("{\\"passed\\":true,\\"checks\\":%u,\\"real_account_login_verified\\":false}\\n",checks);return 0;}
'''
    source = temporary / 'password-original.cpp'
    source.write_text(code)
    executions = {}
    for mode in (('release', 'asan_ubsan') if sanitize else ('release',)):
        binary = temporary / ('password-' + mode)
        flags = ['-O2'] if mode == 'release' else ['-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
        run(['c++', '-std=c++17', *flags, '-I' + str(crypt / 'include'), source,
             crypt / 'src/sha512.cpp', crypt / 'src/sha512Impl.cpp', '-o', binary])
        result = json.loads(run([binary], env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',
                                                  UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')))
        if result != {'passed': True, 'checks': len(cases) * 66, 'real_account_login_verified': False}:
            raise ValueError('password_control_result_mismatch')
        executions[mode] = {'binary_sha256': digest(binary.read_bytes()), 'result': result}
    return {'schema': 'coh-auth-password-fixture-qualification-v1', 'passed': True,
            'original_source_sha256_utf8_lf': pins,
            'original_function_sha256': digest(original.encode()),
            'original_checkpassword_fragment_sha256': digest(fragment[0].encode()),
            'repository_head_at_qualification': run(['git', '-C', root, 'rev-parse', 'HEAD']).decode().strip(),
            'native_source_sha256': {str(p.relative_to(root)): digest(p.read_bytes()) for p in native_inputs + native_headers},
            'qualification_input_sha256': {str(p.relative_to(root)): digest(p.read_bytes()) for p in qualification_inputs},
            'generated_control_sha256': digest(code.encode()), 'native_request_cases': len(cases), 'executions': executions,
            'scope': 'Unchanged EncPwdSha512, cryptLib and CheckPassword digest fragment; native RSA-input capture only.',
            'full_checkpassword_executed': False, 'rsa_encryption_executed': False, 'sql_executed': False,
            'service_started': False, 'real_account_login_verified': False,
            'leak_sanitizer_enabled': False, 'physical_thor_accepted': False}


def write_private_fixture(directory):
    # Deliberately known disposable fixture. Never accept production credentials.
    directory.mkdir(mode=0o700)
    number = salt(ACCOUNT)
    signed = number if number < 2**31 else number - 2**32
    hashed = hashlib.sha512((PASSWORD + f'{number:08x}').encode()).hexdigest()
    files = {'credential.json': json.dumps({'account': ACCOUNT, 'password': PASSWORD,
              'disposable_known_fixture': True}) + '\n',
             'credential.sql': "USE cohauth;\nSET NOCOUNT ON;\nINSERT INTO dbo.user_auth(account,password,salt,hash_type) VALUES('"
              + ACCOUNT + "',0x" + hashed.encode().hex() + ',' + str(signed) + ',1);\n'}
    for name, content in files.items():
        with os.fdopen(os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as out:
            out.write(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--private-fixture-dir', type=Path, help='New private directory; known disposable credential only, no SQL execution')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-password-source-') as name:
        proof = qualify(args.source_root.resolve(), Path(name), args.sanitize)
    if args.private_fixture_dir:
        write_private_fixture(args.private_fixture_dir)
    proof['private_fixture_generated'] = args.private_fixture_dir is not None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': True, 'native_request_cases': proof['native_request_cases'],
                      'real_account_login_verified': False}))


if __name__ == '__main__':
    main()
