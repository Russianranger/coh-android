#!/usr/bin/env python3
"""Pinned-source ODBC contract and generated checksum object investigation.

The object experiment compiles the unchanged original checksum function under
32- and 64-bit x86 ABIs. It does not inspect a deployed DbServer executable.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from source_oracle import extract
from admit_schema import PARAMETERS

HERE = Path(__file__).resolve().parent
AUTH = 'upstream/ouroboros/AuthServer/src/'
CHECKSUM = 'upstream/ouroboros/Common/ClientLogin/clientcommLogin.c'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def decoded(data):
    # Auth_DB_objects.sql is UTF-16 LE with BOM; do not silently skip it as
    # binary or grep only the UTF-8 patch scripts.
    encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    return data.decode(encoding).replace('\r\n', '\n')


def pinned_sources(root):
    pins = json.loads((HERE / 'source-pins.json').read_text())
    values, identities = {}, {}
    commit = None
    git_root = subprocess.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'],
                              capture_output=True, text=True, timeout=15)
    if git_root.returncode == 0 and Path(git_root.stdout.strip()).resolve() == root.resolve():
        commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                check=True, capture_output=True, text=True, timeout=15).stdout.strip()
    for name, expected in pins['sha256_utf8_lf'].items():
        path = root / name
        if path.exists():
            data = path.read_bytes()
            provenance = 'source_file'
        elif commit:
            # A sparse working tree is not a missing source archive. Read the
            # exact pinned HEAD blob without expanding or modifying checkout.
            data = subprocess.run(['git', '-C', str(root), 'show', f'{commit}:{name}'],
                                  check=True, capture_output=True, timeout=15).stdout
            provenance = 'git_blob_at_' + commit
        else:
            raise ValueError('source_input_unavailable')
        content = decoded(data)
        if digest(content.encode()) != expected:
            raise ValueError('source_identity_changed')
        values[name] = content
        identities[name] = {'sha256': digest(data), 'sha256_utf8_lf': expected, 'read_from': provenance}
    return values, identities


def procedure_parameters(text, name):
    text = re.sub(r'/\*.*?\*/|--[^\n]*', '', text, flags=re.S)
    pattern = r'\bCREATE\s+PROCEDURE\s+(?:\[?dbo\]?\.)?\[?' + re.escape(name) + r'\]?\s+(.*?)\bAS\b'
    definitions = []
    for match in re.finditer(pattern, text, re.I | re.S):
        parsed = []
        for field in match.group(1).split(','):
            item = re.fullmatch(r'\s*@\w+\s+\[?(\w+)\]?\s*(?:\(\s*(\d+)\s*\))?\s*(OUTPUT)?\s*', field, re.I)
            if not item:
                raise ValueError('unsupported_pinned_sql_parameter')
            kind = item[1].lower()
            width = int(item[2]) if item[2] else {'tinyint': 1, 'int': 4, 'datetime': 8}.get(kind)
            if width is None:
                raise ValueError('unsupported_pinned_sql_type')
            parsed.append((kind, width, bool(item[3])))
        definitions.append(parsed)
    return definitions


def contracts(values):
    account = values[AUTH + 'Account.cpp']
    sources = {'ap_GPwd': extract(account, 'CAccount::LoadPassword'),
               'ap_GStat': extract(account, 'CAccount::Load'),
               'get_server_groups': extract(account, 'CAccount::Load')}
    results = {}
    for name, expected in PARAMETERS.items():
        text = sources[name]
        calls = re.findall(r'\{CALL\s+(?:dbo\.)?' + name + r'\s*\(([^)]*)\)', text)
        if len(calls) != 1 or calls[0].count('?') != len(expected):
            raise ValueError('source_call_contract_changed')
        # Independently count the actual SQLBindParameter ordinals of each call.
        prefix = text[:text.index('{CALL ' + ('dbo.' if name != 'get_server_groups' else '') + name)]
        if name == 'get_server_groups':
            prefix = prefix[prefix.index('int region(0)'):]
        bindings = re.findall(r'SQLBindParameter\(\s*conn\.m_stmt,\s*(\d+)\s*,\s*(SQL_PARAM_\w+)\s*,\s*(\w+)\s*,\s*(\w+)', prefix)
        if [int(row[0]) for row in bindings] != list(range(1, len(expected) + 1)):
            raise ValueError('source_parameter_order_changed')
        for binding, item in zip(bindings, expected):
            direction = 'SQL_PARAM_OUTPUT' if item[2] else 'SQL_PARAM_INPUT'
            sql_type = {'varchar': 'SQL_VARCHAR', 'binary': 'SQL_BINARY', 'tinyint': 'SQL_TINYINT',
                        'int': 'SQL_INTEGER', 'datetime': 'SQL_TYPE_TIMESTAMP'}[item[0]]
            if binding[1] != direction or binding[3] != sql_type:
                raise ValueError('source_parameter_type_changed')
        declarations = []
        for path, sql in values.items():
            if not path.endswith('.sql'):
                continue
            for params in procedure_parameters(sql, name):
                declarations.append({'source': path, 'parameter_count': len(params),
                                     'matches_source_binding_without_type_conversion': params == expected,
                                     'types': [p[0] for p in params],
                                     'datetime2_scales': [p[1] for p in params if p[0] == 'datetime2']})
        results[name] = {'source_call_parameters': len(expected), 'bound_parameter_ordinals': [int(row[0]) for row in bindings],
                         'checked_in_declarations': declarations}
    return results


def checksum_objects(values, directory):
    original = extract(values[CHECKSUM], 'clientCommLoginVerifyChecksum')
    records = {}
    for bits in (32, 64):
        # No OS headers or libraries required. Static assertions pin ABI and U32.
        # The function body itself is copied unchanged from the pinned source.
        code = ('typedef unsigned int U32;\nextern int memcmp(const void*,const void*,__SIZE_TYPE__);\n'
                'static U32 correct_game_checksum[4],ignore_checksum;\n'
                f'_Static_assert(sizeof(void*)=={bits // 8},"pointer ABI");\n'
                '_Static_assert(sizeof(correct_game_checksum)==16,"checksum width");\n' + original + '\n')
        source, obj = directory / f'checksum-{bits}.c', directory / f'checksum-{bits}.o'
        section = directory / f'checksum-{bits}.text'
        source.write_text(code)
        command = ['cc', f'-m{bits}', '-std=c11', '-O2', '-fno-pie', '-fno-pic', '-fno-stack-protector',
                   '-fno-asynchronous-unwind-tables', '-Wno-sizeof-array-argument', '-c', str(source), '-o', str(obj)]
        subprocess.run(command, check=True, capture_output=True, timeout=60)
        undefined = subprocess.run(['nm', '-u', str(obj)], check=True, capture_output=True, text=True, timeout=15).stdout
        subprocess.run(['objcopy', '-O', 'binary', '--only-section=.text', str(obj), str(section)],
                       check=True, capture_output=True, timeout=15)
        machine = section.read_bytes()
        # Exact generated function is xor eax,eax; ret, optionally preceded by
        # the compiler's x86-64 ENDBR64 control-flow landing pad. No referenced
        # memcmp exists. Other forms fail closed; do not infer equivalence.
        allowed = [b'\x31\xc0\xc3']
        if bits == 64:
            allowed.append(b'\xf3\x0f\x1e\xfa\x31\xc0\xc3')
        if machine not in allowed or undefined.strip():
            raise ValueError('checksum_codegen_not_admitted')
        records[str(bits)] = {'pointer_bytes': bits // 8, 'checksum_array_bytes': 16,
                              'source_sha256': digest(source.read_bytes()), 'object_sha256': digest(obj.read_bytes()),
                              'text_hex': machine.hex(), 'undefined_symbols': 0,
                              'generated_function_always_returns_zero': True,
                              'executed': False, 'deployed_binary_inspected': False}
    return records


def qualify(root, directory):
    values, identities = pinned_sources(root)
    calls = contracts(values)
    caller = values['upstream/ouroboros/DBServer/src/clientcomm.c']
    if not re.search(r'if\s*\(\s*clientCommLoginVerifyChecksum\(game_checksum\)\s*\)', caller):
        raise ValueError('checksum_caller_changed')
    schema = '\n'.join(text for name, text in values.items() if name.endswith('.sql'))
    return {'schema': 'coh-auth-deployment-source-audit-v1', 'source_pins_verified': True,
            'source_identities': identities, 'odbc_contracts': calls,
            'checked_in_gstat_has_full_parameter_count': any(d['parameter_count'] == 13 for d in calls['ap_GStat']['checked_in_declarations']),
            'checked_in_gstat_matches_binding_without_conversion': any(d['matches_source_binding_without_type_conversion'] for d in calls['ap_GStat']['checked_in_declarations']),
            'loyalty_referenced_in_checked_in_schema': bool(re.search(r'\bloyalty\w*\b', schema, re.I)),
            'checksum_generated_objects': checksum_objects(values, directory),
            'checksum_original_function_sha256': digest(extract(values[CHECKSUM], 'clientCommLoginVerifyChecksum').encode()),
            'checksum_source_repaired': False, 'deployed_binary_inspected': False,
            'real_account_login_verified': False, 'native_live_world': False}
