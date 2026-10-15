#!/usr/bin/env python3
"""Optional, read-only initiation evidence for authored Atlas contacts.

Call once with the owned server's bounded log snapshots at report collection.
These native logs precede dialogue generation and cannot prove visible dialogue,
NPC pathfinding, mission acceptance or combat. Absence never fails a session.
"""
import re
import time

import local_character_server as server

RECORD_LIMIT = 16
SCOPE = 'owned_atlas_stationary_contact_native_initiation_only'
NATIVE_CONTRACT_FILES = (
    'MapServer/src/dbcomm/logcomm.c',
    'MapServer/src/storyarc/contactInteraction.c',
    'MapServer/src/storyarc/pnpc.c',
    'MapServer/src/player/parseClientInput.c',
    'Game/src/UI/uiCursor.c',
    'Common/gameComm/dooranimcommon.h',
)
DATA_CONTRACT_FILES = (
    'data/maps/city_zones/city_01_01/city_01_01_layer_persistentnpc.txt',
    'data/scripts.loc/supergroupcontacts/msliberty.npc',
    'data/scripts.loc/contacts/level_1/city_representative.npc',
    'data/menu/defaultkey/defaultkeybindings.kb',
    'data/scripts.loc/contacts/kheldian/sunstorm.npc',
    'data/scripts.loc/spawndefs/infonpcs/meritinfo_npc_atlas_d0_v0.spawndef',
    'data/texts/english/contacts/kheldian/kheldiancontacts.def.ms',
    'data/texts/english/spawndefs/infonpcs/merit_reward_info_npcs.xls.ms',
)
CONTACTS = {
    'Ms. Liberty': {'npc_definition': 'SuperGroupContacts/MsLiberty.npc',
                    'contact_definition': 'SuperGroupContacts/MsLiberty.contact'},
    'City Representative': {'npc_definition': 'Contacts/Level_1/City_Representative.npc',
                           'contact_definition': 'Contacts/Level_1/City_Representative.contact'},
    'Sunstorm': {'npc_definition': 'Contacts/Kheldian/Sunstorm.npc',
                'contact_definition': 'Contacts/Kheldian/Sunstorm.contact'},
    'Merit Reward Informant': {
        'spawn_definition': 'Spawndefs/InfoNPCs/MeritInfo_NPC_Atlas_D0_V0.spawndef',
        'script_name': 'InfoNPC', 'dialog_definition': 'MeritReward',
        'dialog_start_page': 'MeritRewardsIntro', 'script_response_route_qualified': False},
}
SUFFIX = (r' ExpLevel:(?P<level>[1-9][0-9]{0,2}), AlignmentNum:(?P<alignment>[0-9]{1,2}), '
          r'Archetype:(?P<archetype>Class_[A-Za-z0-9_]{1,80}), Incarnate:(?P<incarnate>[01])'
          # The stock logger appends this bounded diagnostic field. Its values
          # do not prove a date/build identity and never enter contact proof.
          r'(?: BuildNumber: (?:dev: )?[0-9]{1,5}-[0-9]{1,5}-[0-9]{1,5}'
          r' [0-9]{1,5}:[0-9]{1,5}:[0-9]{1,5})?')
PREFIX = r'^"THORHERO:COHLOCAL" (?P<teamup>-?[0-9]{1,10}) '
OPEN = re.compile(PREFIX + r'ContactInteract:GenericOpen Initiating interaction with contact '
    r'(?P<handle>[1-9][0-9]{0,9}) \((?P<name>[^\r\n()]{1,80})\)' + SUFFIX + '$')
RESPONSE = re.compile(PREFIX + r'ContactInteract:Response Received response '
    r'(?P<link>[0-9]{1,10}) to contact (?P<handle>[1-9][0-9]{0,9})' + SUFFIX + '$')


def positive_int(value):
    return type(value) is int and 0 < value <= 0xffffffff


def binding(proof, session, client_pid, now_utc_ms):
    """Use the existing validated reopen proof; never create a new connection."""
    if not (type(session) is str and re.fullmatch(r'[0-9a-f]{32}', session)
            and positive_int(client_pid) and type(now_utc_ms) is int and now_utc_ms > 0
            and type(proof) is dict and proof.get('session_id') == session
            and proof.get('client_pid') == client_pid and type(proof.get('client_pid')) is int
            and type(proof.get('character_id')) is int and proof['character_id'] == 1
            and type(proof.get('map_id')) is int and proof['map_id'] == 1
            and positive_int(proof.get('auth_id'))
            and proof.get('name') == 'THORHERO' and proof.get('account') == 'COHLOCAL'
            and all(proof.get(key) is True for key in ('connected_on_atlas',
                'existing_character_verified', 'preserved_existing_identity',
                'reopen_verified', 'native_client_ready_observed'))
            and type(proof.get('client_ready_observed_utc_ms')) is int
            and 0 < proof['client_ready_observed_utc_ms'] <= now_utc_ms):
        return None
    ready = proof.get('client_ready_evidence')
    if not (type(ready) is dict and ready.get('loaded_world_assets') is True
            and ready.get('name') == 'THORHERO' and ready.get('account') == 'COHLOCAL'):
        return None
    if ready.get('source') == 'current_owned_mapserver_immediate_ready':
        if not (ready.get('kind') == 'ready' and ready.get('session_id') == session
                and type(ready.get('db_id')) is int and ready['db_id'] == 1
                and ready.get('auth_id') == proof['auth_id'] and type(ready.get('auth_id')) is int
                and type(ready.get('map_id')) is int and ready['map_id'] == 1
                and positive_int(ready.get('windows_pid')) and positive_int(ready.get('main_thread_id'))
                and type(ready.get('utc_ms')) is int
                and 0 < ready['utc_ms'] <= proof['client_ready_observed_utc_ms']):
            return None
    elif not (ready.get('source') == 'current_owned_mapserver_CLIENT_READY_resumeCharacter_success'
            and ready.get('log_route') in ('local_mapserver', 'embedded_dbserver_logserver')
            and type(ready.get('log_timestamp')) is str):
        return None
    else:
        try:
            native_ms = int(time.mktime(time.strptime(ready['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
        except (ValueError, OverflowError):
            return None
        if not 0 < native_ms <= proof['client_ready_observed_utc_ms']:
            return None
    return {'session_id': session, 'client_pid': client_pid, 'character_id': 1,
            'auth_id': proof['auth_id'], 'map_id': 1, 'name': 'THORHERO', 'account': 'COHLOCAL',
            'client_ready_observed_utc_ms': proof['client_ready_observed_utc_ms'],
            'scope': 'previously_validated_current_session_reopen_connection',
            'native_log_contains_character_db_id': False,
            'native_log_contains_session_or_client_pid': False}


def collect(logs, proof, *, session, client_pid, now_utc_ms):
    """Return at most 16 distinct records; responses need a prior same-file open.

The native message's leading integer is teamup ID, and its contact handle is
runtime-local. They are not persistent player/contact identifiers. Timestamp
precision is one second; records must start at or after the observed ready
watermark and no later than collection. Duplicate local/embedded routes do not
count as separate interactions. Invalid optional inputs are unavailable evidence.
"""
    result = {'format': 1, 'scope': SCOPE, 'status': 'unavailable', 'optional': True,
        'native_initiation_observed': False, 'native_response_observed': False,
        'dialogue_visual_verified': False, 'npc_pathing_verified': False,
        'mission_acceptance_verified': False, 'combat_verified': False,
        'sql_game_mutations_performed': False, 'record_limit': RECORD_LIMIT, 'records': []}
    identity = binding(proof, session, client_pid, now_utc_ms)
    if identity is None:
        result['reason'] = 'Current validated reopen connection binding is unavailable'
        return result
    result.update(status='not_observed', connection=identity)
    if not (type(logs) in (list, tuple) and len(logs) <= server.SERVER_LOG_COUNT_LIMIT):
        result.update(status='unavailable', reason='Owned logger inventory is missing or exceeds bounds')
        return result
    total = 0
    for item in logs:
        if not (type(item) in (list, tuple) and len(item) == 2
                and type(item[0]) is str and type(item[1]) is str):
            result.update(status='unavailable', reason='Owned logger snapshot differs from the expected form')
            return result
        size = len(item[1].encode())
        total += size
        if size > server.SERVER_LOG_FILE_LIMIT or total > server.SERVER_LOG_TOTAL_LIMIT:
            result.update(status='unavailable', reason='Owned logger snapshot exceeds existing byte bounds')
            return result
    observations, seen, truncated = [], set(), False
    for path, text in logs:
        active = None
        for message, route in server.entity_records([(path, text)]):
            if len(message) > 2048 or 'ContactInteract:' not in message:
                continue
            try:
                utc_ms = int(time.mktime(time.strptime(route['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
            except (ValueError, OverflowError):
                continue
            if not identity['client_ready_observed_utc_ms'] <= utc_ms <= now_utc_ms:
                continue
            match, kind = OPEN.fullmatch(message), 'initiation'
            if match is None:
                match, kind = RESPONSE.fullmatch(message), 'response'
            if match is None:
                # Another opening path or malformed own-player message cannot
                # bridge an earlier click to a later response.
                if message.startswith('"THORHERO:COHLOCAL"') and 'ContactInteract:' in message:
                    active = None
                continue
            handle, teamup = int(match['handle']), int(match['teamup'])
            if not 0 < handle <= 0x7fffffff or not -0x80000000 <= teamup <= 0x7fffffff:
                active = None
                continue
            if kind == 'initiation':
                name = match['name']
                if name not in CONTACTS:
                    active = None
                    continue
                active = (handle, name, utc_ms)
            else:
                link = int(match['link'])
                if active is None or handle != active[0] or utc_ms < active[2] or link > 0x7fffffff:
                    continue
                name = active[1]
                # Scripted InfoNPC responses use contact zero; the positive
                # same-handle proof here cannot bind that route. Preserve its
                # genuine GenericOpen only, with no invented response chain.
                if CONTACTS[name].get('script_response_route_qualified') is False:
                    continue
            key = (utc_ms, message)
            if key in seen:
                continue
            if len(observations) >= RECORD_LIMIT:
                truncated = True
                continue
            seen.add(key)
            observation = dict(route, kind=kind, utc_ms=utc_ms, npc_name=name,
                contact_runtime_handle=handle, native_teamup_id=teamup,
                source='owned_native_ContactInteract_' + kind,
                proves_visible_dialogue=False, **CONTACTS[name])
            if kind == 'response':
                observation['response_link'] = link
                observation['matching_initiation_utc_ms'] = active[2]
            observations.append(observation)
    observations.sort(key=lambda item: item['utc_ms'])
    # Keep the first bounded segment, ensuring any retained response has its
    # preceding initiation in that segment. Return no unbounded identifiers.
    result.update(records=observations, records_truncated=truncated,
        native_initiation_observed=any(item['kind'] == 'initiation' for item in observations),
        native_response_observed=any(item['kind'] == 'response' for item in observations))
    if observations:
        result['status'] = 'native_initiation_observed'
    return result
