"""Strict private v2 receipt admission; fixed received-header-only projection."""
DB_PHASES=('IDLE','CONNECTING','WAIT_PLAYERS','QUEUED','CHARACTERS','WAIT_MAP','HANDOFF_READY',
    'DISCONNECTING','SUSPENDED','CLOSED','FAILED','CANCELLED','TIMED_OUT')
COMMANDS=('SEND_PLAYERS','MSG','MAP_CONNECT','DELETE_OK','SEND_COSTUME','SEND_POWERSET_NAMES',
    'ACCOUNTSERVER_CHARCOUNT','ACCOUNTSERVER_CATALOG','ACCOUNTSERVER_CLIENTAUTH',
    'ACCOUNTSERVER_PLAYNC_AUTH_KEY','ACCOUNTSERVER_NOTIFYREQUEST','ACCOUNTSERVER_INVENTORY',
    'ACCOUNTSERVER_UNAVAILABLE','CONPRINT','RENAME_RESPONSE','UNLOCK_CHARACTER_RESPONSE',
    'CHECK_NAME_RESPONSE','LOGIN_DIALOG_RESPONSE','QUEUE_POSITION','CAN_START_STATIC_MAP_RESPONSE')
NAMES={'NONE','UNKNOWN'}|{'DBGAMESERVER_'+name for name in COMMANDS}
FLAGS={'available','context_verified','retired','truncated','first_unsupported_attributed','body_acceptance_observed'}
COUNTERS={'instances':2,'service_calls':65535,'total_seen':65535}
KEYS=FLAGS|set(COUNTERS)|{'schema','entries'}
ENTRY_KEYS={'command','header_decoded','phase','legacy','compressed'}

SOURCE_PINS={
    'upstream/ouroboros/Common/comm_backend.h':'9af3a17854cc0c9a7e32e545bc563158b6a8538afd9e215f490f55574397f24c',
    'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h':'116b3c4a4d4319893ddc0cd75a60722ec58c96a3dc066a74b1b92e12d925aea9',
    'native-android/engine/dbclient/coh_db_session.c':'ca8ee6130ebdccb3072f0ec0c279e4c044fac88f463144db7ef1caa7202f36b9',
    'native-android/engine/auth-interop/deployment/windows/db_development_probe.c':'fab9f9bbf4d79d6fdf00982d8f516e40d8b0ed85fe30190bca2879ed8dbd4354',
}


def admit(value,preflight=False):
    """No raw opcode/body/identity input is projected, even on a valid header."""
    if (type(preflight) is not bool or type(value) is not dict or set(value)!=KEYS
            or value['schema']!='coh-db-received-header-prefix-v1'
            or any(type(value[key]) is not bool for key in FLAGS)
            or any(type(value[key]) is not int or not 0<=value[key]<=limit for key,limit in COUNTERS.items())
            or value['first_unsupported_attributed'] is not False or value['body_acceptance_observed'] is not False
            or type(value['entries']) is not list or len(value['entries'])>16):
        raise ValueError('development_received_header_scope')
    entries=value['entries'];total=value['total_seen'];instances=value['instances']
    if (len(entries)!=min(total,16) or value['truncated'] is not (total>16)
            or (value['context_verified'] and (not value['available'] or instances!=1 or not value['service_calls']))
            or (value['retired'] and not instances)
            or (total and (not instances or not value['service_calls']))
            or (not value['available'] and (instances or value['service_calls'] or total or value['context_verified'] or value['retired']))
            or (preflight and (instances or value['service_calls'] or total or value['context_verified'] or value['retired']))):
        raise ValueError('development_received_header_cardinality')
    rows=[]
    for row in entries:
        if (type(row) is not dict or set(row)!=ENTRY_KEYS or type(row['command']) is not str or row['command'] not in NAMES
                or type(row['phase']) is not int or not 0<=row['phase']<len(DB_PHASES)
                or any(type(row[key]) is not bool for key in ('header_decoded','legacy','compressed'))
                or (row['command']=='NONE') is row['header_decoded']):
            raise ValueError('development_received_header_entry')
        rows.append(dict(row,phase=DB_PHASES[row['phase']]))
    return dict(value,entries=rows)


def native(value,preflight=False):
    """Return unchanged v1-policy inputs plus a separately labeled projection."""
    expected='coh-auth-db-development-'+('platform-preflight' if preflight else 'list-probe')+'-v2'
    if type(value) is not dict or value.get('schema')!=expected or 'db_received_prefix' not in value:
        raise ValueError('development_received_native_schema')
    projection=admit(value['db_received_prefix'],preflight)
    base={key:item for key,item in value.items() if key!='db_received_prefix'}
    base['schema']=expected[:-1]+'1'
    return base,projection


def completion(value,preflight=False):
    """The new observation must be available; original list policy is separate."""
    if (value['available'] is not True or (not preflight and
            (value['context_verified'] is not True or value['retired'] is not True or not value['total_seen']))):
        raise ValueError('development_received_context_unverified')
    return value
