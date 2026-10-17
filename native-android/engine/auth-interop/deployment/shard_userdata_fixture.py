"""Generate a bounded real-driver prerequisite from unchanged original bodies.

The shell owns one ODBC statement at a time and captures sends in memory. It is
not an AuthServer or DbServer, and never creates an authentication grant.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from hosted_auth_stage import ORIGINAL_TREE
from source_audit import decoded, extract

HERE = Path(__file__).resolve().parent
AUTH = 'upstream/ouroboros/AuthServer/src/'
PATHS = tuple(AUTH + name for name in (
    'AccountDB.cpp', 'CSocketServer.cpp', 'ServerList.cpp', 'DBConn.cpp',
    'AuthType.h', 'ServerId.h', 'Protocol.h', 'util.cpp')) + (
    'upstream/ouroboros/Assets/DBSchemas/cohauth.sql',)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_function(source, name):
    # The shared extractor predates const-qualified C++ methods. Preserve the
    # complete signature as well as the body for these three methods.
    if name not in ('CServerList::IsServerUp', 'CServerList::GetInternalAddress',
                    'CServerList::GetFreeServerId'):
        return extract(source, name)
    pattern = r'(?m)^[^\n;{}]*\b' + re.escape(name) + r'\([^;{}]*\)\s+const\s*\{'
    matches = list(re.finditer(pattern, source))
    if len(matches) != 1:
        raise ValueError('userdata_const_source_function_missing')
    start = matches[0].start()
    cursor, depth = source.index('{', start) + 1, 1
    while depth:
        depth += (source[cursor] == '{') - (source[cursor] == '}')
        cursor += 1
    return source[start:cursor]


def inputs(root):
    def git(*args):
        return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root), *args], timeout=30)
    if git('rev-parse', 'HEAD:upstream/ouroboros').decode().strip() != ORIGINAL_TREE:
        raise ValueError('userdata_original_tree_changed')
    raw = {name: git('show', 'HEAD:' + name) for name in PATHS}
    return {name: decoded(value) for name, value in raw.items()}, {name: sha(value) for name, value in raw.items()}


def fixture_sql(port=23000):
    # SQL smallint is signed; the original ServerList binding is SQL_C_SHORT.
    if type(port) is not int or not 20000 <= port <= 32767:
        raise ValueError('userdata_source_smallint_port_required')
    auth = bytes(range(128))
    game = bytes(255 - i for i in range(128))
    return (
        'USE cohauth;\nSET NOCOUNT ON;\n'
        "IF EXISTS(SELECT 1 FROM dbo.server) OR EXISTS(SELECT 1 FROM dbo.user_data) THROW 51000,'fresh fixture required',1;\n"
        "INSERT dbo.server(id,name,ip,inner_ip,ageLimit,pk_flag,server_group_id,client_port) VALUES(1,'Disposable SQL fixture','127.0.0.1','127.0.0.1',0,0,1," + str(port) + ');\n'
        'INSERT dbo.worldstatus(idx,status) VALUES(1,0);\n'
        'INSERT dbo.user_data(uid,user_data,user_data_new,user_game_data,user_game_data_new) VALUES(900001,0x'
        + auth[:16].hex() + ',0x' + auth[16:].hex() + ',0x' + game[:16].hex() + ',0x' + game[16:].hex() + ');\n'
        "IF (SELECT COUNT(*) FROM dbo.server)<>1 OR (SELECT COUNT(*) FROM dbo.user_data)<>1 THROW 51000,'fixture cardinality',1;\n"
        "IF EXISTS(SELECT 1 FROM dbo.user_data WHERE uid<>900001 OR DATALENGTH(user_data)<>16 OR DATALENGTH(user_data_new)<>112 OR DATALENGTH(user_game_data)<>16 OR DATALENGTH(user_game_data_new)<>112) THROW 51000,'userdata widths',1;\n")


def prepare(root, directory):
    values, identities = inputs(root)
    functions = {}
    for filename, names in (
            ('ServerList.cpp', ('CServerList::Load', 'CServerList::SetServerSocketByAddress',
                                'CServerList::SetServerStatus', 'CServerList::IsServerUp',
                                'CServerList::GetInternalAddress', 'CServerList::GetFreeServerId')),
            ('DBConn.cpp', ('CDBConn::Execute', 'CDBConn::Fetch', 'CDBConn::ResetHtmt')),
            ('AccountDB.cpp', ('AccountDB::AboutToPlay',)),
            ('CSocketServer.cpp', ('ServerReadGameData',)),
            ('util.cpp', ('Assemble',))):
        for name in names:
            functions[name] = exact_function(values[AUTH + filename], name)
    # All six overloads are copied together, preserving their original ODBC C ABI.
    db = values[AUTH + 'DBConn.cpp']
    begin, end = db.index('void CDBConn::Bind(char *n)'), db.index('void CDBConn::SetParamNumber')
    functions['CDBConn::Bind overloads'] = db[begin:end].rstrip()
    world = re.search(r'struct WorldServer\s*\{.*?\};', values[AUTH + 'AuthType.h'], re.S)
    if not world:
        raise ValueError('userdata_original_world_struct_missing')
    # Protocol.h's enum blocks have no transitive GlobalAuth/logging declarations.
    protocol = values[AUTH + 'Protocol.h']
    enums = re.findall(r'enum\s*\{.*?\};', protocol, re.S)
    if len(enums) != 12:
        raise ValueError('userdata_original_protocol_enums_changed')
    template = (HERE / 'shard_userdata_fixture.cpp').read_text()
    substitutions = {
        '/* ORIGINAL_SERVER_ID */': values[AUTH + 'ServerId.h'],
        '/* ORIGINAL_PROTOCOL */': '\n'.join(enums),
        '/* ORIGINAL_WORLD_SERVER */': world[0],
        '/* ORIGINAL_FUNCTIONS */': '\n\n'.join(functions.values()),
    }
    for marker, replacement in substitutions.items():
        if template.count(marker) != 1:
            raise ValueError('userdata_template_marker_changed')
        template = template.replace(marker, replacement)
    generated, fixture = directory / 'original-shard-userdata.cpp', directory / 'shard-userdata.sql'
    generated.write_text(template, encoding='utf-8', newline='\n')
    fixture.write_text(fixture_sql(), encoding='ascii', newline='\n')
    return {'schema': 'coh-original-shard-userdata-source-v1', 'original_source_tree': ORIGINAL_TREE,
            'source_sha256': identities, 'function_sha256': {name: sha(body.encode()) for name, body in functions.items()},
            'generated_source_sha256': sha(generated.read_bytes()), 'fixture_sql_sha256': sha(fixture.read_bytes()),
            'source_struct_sha256': sha(world[0].encode()), 'protocol_enums_sha256': sha('\n'.join(enums).encode()),
            'no_authentication_grant_generated': True, 'network_registration_verified': False,
            'authenticated_db_map_handoff_verified': False}


def admit_result(value):
    expected = {'schema', 'passed', 'pointer_bytes', 'sql_connected', 'shard_sql_loaded',
                'source_address_lookup', 'unknown_address_refused', 'full_auth_sql_to_wire',
                'full_game_sql_to_wire', 'missing_userdata_guard', 'null_userdata_guard',
                'source_missing_userdata_zero_filled', 'source_game_missing_zero_filled',
                'source_queue_disabled', 'source_sql_errors', 'network_registration_verified',
                'authentication_grant_generated', 'authenticated_db_map_handoff_verified'}
    if (not isinstance(value, dict) or set(value) != expected
            or value['schema'] != 'coh-original-shard-userdata-odbc-v1'
            or type(value['pointer_bytes']) is not int or value['pointer_bytes'] != 4
            or type(value['source_sql_errors']) is not int or value['source_sql_errors'] != 0
            or any(value[name] is not True for name in expected - {
                'schema', 'pointer_bytes', 'source_sql_errors', 'network_registration_verified',
                'authentication_grant_generated', 'authenticated_db_map_handoff_verified'})
            or any(value[name] is not False for name in ('network_registration_verified',
                'authentication_grant_generated', 'authenticated_db_map_handoff_verified'))):
        raise ValueError('userdata_runtime_result_scope')
    return value
