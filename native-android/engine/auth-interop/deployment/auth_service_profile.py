"""Exact disposable auth-only profile, never a DB/Map deployment profile."""
import hashlib
import json
import re
from pathlib import Path
import password_fixture
from hosted_auth_stage import ORIGINAL_TREE

HERE = Path(__file__).resolve().parent
PROTOCOL = 191021
SOURCE_PATHS = [
    'AuthServer/src/GlobalAuth.cpp', 'AuthServer/src/Config.cpp', 'AuthServer/src/Parser.cpp',
    'AuthServer/src/SocketServerEx.cpp', 'AuthServer/src/Account.cpp', 'AuthServer/src/AccountDB.cpp',
    'AuthServer/src/Protocol.h', 'AuthServer/src/ServerList.cpp', 'AuthServer/src/Thread.cpp',
    'AuthServer/src/IOServer.cpp', 'AuthServer/src/DBConn.cpp', 'AuthServer/src/util.cpp',
    'Assets/DBSchemas/cohauth.sql']


def configuration(instance, driver, ports, log_directory):
    if not re.fullmatch(r'cohauth-ci-[0-9a-f]{24}', instance):
        raise ValueError('owned_instance_name_invalid')
    if driver != 'ODBC Driver 17 for SQL Server':
        raise ValueError('qualified_x86_odbc_driver_required')
    if (len(ports) != 3 or len(set(ports)) != 3 or
            any(type(port) is not int or not 20000 <= port <= 59999 for port in ports)):
        raise ValueError('three_distinct_disposable_ports_required')
    log = str(log_directory)
    connection = 'Driver={' + driver + '};Server=(localdb)\\' + instance + ';Database=cohauth;Trusted_Connection=Yes;Encrypt=No;'
    # Original GetToken limits a quoted value to256 bytes, with no escaping.
    for value in (log, connection):
        if not value or len(value.encode('ascii')) > 240 or any(c in value for c in ('"', '\r', '\n', '\0')):
            raise ValueError('original_config_token_unrepresentable')
    values = {
        'serverPort': ports[0], 'serverExPort': ports[1], 'serverIntPort': ports[2],
        'WorldPort': 7000, 'DBConnectionNum': 2, 'numServerThread': 2, 'numServerIntThread': 1,
        'GameID': 8, 'SocketTimeOut': 20, 'SocketLimit': 32, 'AcceptCallNum': 2, 'WaitingUserLimit': 8,
        'Encrypt': True, 'DesApply': True, 'ProtocolVersion': PROTOCOL, 'CountryCode': 2,
        'logDirectory': log, 'connectionString': connection, 'useQueue': False, 'sendQueueLevel': False,
        'PayStatOverride': -1, 'FreeServer': False, 'HybridServer': False, 'Reactivation': 0,
        'UserData': False, 'UseIPServer': False, 'uselogd': False,
        'UseWantedSystem': False, 'useForbiddenIPList': False, 'PCCafeFirst': False,
        'GMCheckMode': False, 'RestrictGMIP': True, 'GMIP': '127.0.0.1',
        'allowUnknownServers': False, 'gameServerSpecifiesId': False, 'DBHasClientPorts': False,
        'ReadLocalServerList': False, 'OneTimeLogOut': False, 'supportReconnect': False,
        'DumpPacket': False, 'enableVerboseLogging': False, 'enableDebugLogging': False,
    }
    def text(value):
        if type(value) is bool:
            return 'true' if value else 'false'
        if type(value) is int:
            return str(value)
        return '"' + value + '"'
    return ''.join(key + ' = ' + text(value) + ';\n' for key, value in values.items())


def account_sql():
    # A normal nonblocked paid disposable row, not FreeServer/PayStatOverride.
    # Password fixture user_auth row is written separately by its qualified tool.
    return ("USE cohauth;\nSET NOCOUNT ON;\n"
            "INSERT INTO dbo.user_account(account,uid,pay_stat,login_flag,warn_flag,block_flag,block_flag2,subscription_flag,last_world,block_end_date,queue_level,loyalty_points,loyalty_legacy_points) VALUES('"
            + password_fixture.ACCOUNT + "',900001,1,0,0,0,0,0,0,'2020-01-01T00:00:00',0,0,0);\n"
            "IF (SELECT COUNT(*) FROM dbo.server)<>0 THROW 51000,'auth-only server table must remain empty',1;\n"
            "IF (SELECT COUNT(*) FROM dbo.user_auth)<>1 OR (SELECT COUNT(*) FROM dbo.user_account)<>1 THROW 51000,'auth-only fixture cardinality',1;\n")


def fixture_header():
    return ('/* Deliberately known disposable fixture, never a user credential. */\n'
            '#define COH_FIXTURE_ACCOUNT ' + json.dumps(password_fixture.ACCOUNT) + '\n'
            '#define COH_FIXTURE_PASSWORD ' + json.dumps(password_fixture.PASSWORD) + '\n')


def audit(root, original):
    return {'original_source_tree': ORIGINAL_TREE,
            'source_files_sha256': {path: hashlib.sha256((original / path).read_bytes()).hexdigest() for path in SOURCE_PATHS},
            'native_source_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in native_inputs(root)},
            'protocol': PROTOCOL, 'normal_empty_shard_list': True, 'queue_profile_enabled': False,
            'auth_encryption_required': True, 'password_hash_type': 1,
            'fixture_is_known_disposable': True, 'nondev_db_profile_admitted': False,
            'db_checksum_policy_modified': False}


def native_inputs(root):
    native = root / 'native-android'
    names = ['engine/login/coh_login.c', 'engine/login/coh_login.h', 'engine/auth/coh_auth.c',
             'engine/auth/coh_auth.h', 'engine/auth/coh_auth_openssl.c', 'engine/network/coh_net_udp.h',
             'engine/network/coh_net.h', 'engine/coh_contracts.h', 'include/coh_native_core.h',
             'src/coh_blowfish.c', 'src/byte_reader.h', 'protocol/coh_protocol.c',
             'protocol/coh_protocol.h', 'engine/auth/android/openssl-source.json']
    return [native / name for name in names]
