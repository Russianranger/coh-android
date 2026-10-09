#!/usr/bin/env python3
"""Read-only evidence for one manually accepted authored local Atlas task.

The input sender's receipts establish delivery, never task success. Native
Task:Add, admin ForceComplete, entity Success, current SQL and the existing
ordinary logout/save proof remain separate requirements. Completing this
bounded diagnostic task proves no combat, mission map, visual NPC or reward
turn-in. Stock /completetask 0 leaves a completed task pending contact return.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

import stationary_contact_evidence as contact

server = contact.server
CONTACT_PATH = 'Contacts/Atlas_Park/Matthew_Habashy.contact'
TASK_FILE = 'scripts.loc/contacts/atlas_park/tasks/sl1_matthewhabashy.storyarc'
CONTEXT_PATH = TASK_FILE
TASKS = {
    'Mission1': {'subhandle': 1, 'type': 'taskKillX',
                 'task_success_experience': 25, 'task_success_contact_points': 10},
}
SELECTED = {
    'tasks': ('containerid', 'subid', 'id', 'subhandle', 'compoundpos', 'state',
              'assigneddbid', 'assignedtime', 'seed', 'subtasksuccess', 'playercreated'),
    'contacts': ('containerid', 'subid', 'id', 'contactpoints', 'taskissued',
                 'storyarcissued', 'contactrelationship', 'notifyplayer'),
    'ents': ('containerid', 'experiencepoints', 'influencepoints'),
    'storyarcs': ('containerid', 'subid', 'id', 'contact', 'episode'),
}
NATIVE_CONTRACT_FILES = (
    'MapServer/src/storyarc/task.c', 'MapServer/src/storyarc/taskdef.c',
    'MapServer/src/storyarc/contactDialog.c', 'MapServer/src/storyarc/contactInteraction.c',
    'MapServer/src/storyarc/contactdef.c', 'MapServer/src/container/containerloadsave.c',
    'MapServer/src/storyarc/storyarcprivate.h', 'MapServer/src/cmdparse/cmdserver.c',
    'MapServer/src/dbcomm/logcomm.c', 'MapServer/src/dbcomm/logcomm.h',
    'MapServer/src/storyarc/storyarc.c',
)
DATA_CONTRACT_FILES = (
    'data/scripts.loc/contacts/atlas_park/matthew_habashy.contact',
    'data/scripts.loc/contacts/atlas_park/tasks/sl1_matthewhabashy.storyarc',
)
SCOPE = 'owned_atlas_manual_authored_task_stock_command_completion_and_ordinary_save'
RECORD_LIMIT = 128
ROW_LIMIT = 128
RECEIPT_LIMIT = 4096
COMMAND_MAX_AGE_MS = 180000
TASK_KEYS = {'name', 'context', 'subhandle', 'task_index'}
PREFIX = contact.PREFIX
SUFFIX = contact.SUFFIX
PATTERNS = {
    'contact': re.compile(PREFIX + r'ContactInteract:Debug Initiating interaction with contact (?P<context>[1-9][0-9]{0,9})' + SUFFIX + '$'),
    'add': re.compile(PREFIX + r'Task:Add (?P<name>[A-Za-z0-9_]{1,256})' + SUFFIX + '$'),
    'arc': re.compile(PREFIX + r'Storyarc:Add Handle (?P<context>-[1-9][0-9]{0,9})' + SUFFIX + '$'),
    'success': re.compile(PREFIX + r'Task:Success Name: (?P<name>[A-Za-z0-9_]{1,256}), Type: (?P<type>[A-Za-z0-9_]{1,64})' + SUFFIX + '$'),
    'force_auth': re.compile(PREFIX + r'Task:ForceComplete Auth: COHLOCAL Task: (?P<filename>[^\r\n]{1,256}?)' + SUFFIX + '$'),
    'force_context': re.compile(PREFIX + r'Task:ForceComplete Context: (?P<context>-?[0-9]{1,10}) Subhandle: (?P<subhandle>[0-9]{1,10})' + SUFFIX + '$'),
    'force_name': re.compile(PREFIX + r'Task:ForceComplete Task Name: (?P<name>[A-Za-z0-9_]{1,256}), File: (?P<filename>[^\r\n]{1,256}?)' + SUFFIX + '$'),
    'reward': re.compile(PREFIX + r'\[Tbl\]:Rcv:Points XP: (?P<xp>[0-9]{1,10}), Debt: (?P<debt>[0-9]{1,10}), '
        r'Inf: (?P<influence>[0-9]{1,10}), Pres: (?P<prestige>[0-9]{1,10}) \(SGMode off \((?P<supergroup>[0-9]{1,10})\)\)' + SUFFIX + '$'),
}


def _result(status='unavailable', reason=None):
    result = {'format': 1, 'scope': SCOPE, 'status': status, 'verified': False,
        'task_accepted_verified': False, 'task_completed_verified': False,
        'task_save_verified': False, 'native_task_verified': False,
        'sql_task_verified': False, 'reward_turn_in_verified': False,
        'combat_verified': False, 'mission_map_verified': False,
        'dialog_semantics_verified': False, 'sql_game_mutations_performed': False,
        'record_limit': RECORD_LIMIT}
    if reason is not None:
        result['reason'] = reason
    return result


def _int(value, lo=0, hi=0x7fffffff, *, null_zero=False):
    if value is None and null_zero:
        return 0
    return value if type(value) is int and lo <= value <= hi else None


def _path(value):
    if not (type(value) is str and len(value) <= 256 and value.isascii()
            and re.fullmatch(r'[A-Za-z0-9_./\\-]+', value)):
        return None
    normalized = value.replace('\\', '/').casefold()
    return normalized if all(part not in ('', '.', '..') for part in normalized.split('/')) else None


def _task(value):
    return (type(value) is dict and set(value) == TASK_KEYS and value.get('name') in TASKS
        and _int(value.get('context'), -0x80000000, -1) is not None
        and type(value.get('subhandle')) is int
        and value['subhandle'] == TASKS[value['name']]['subhandle']
        and type(value.get('task_index')) is int and value['task_index'] == 0)


def _receipt(value, identity, ready_ms, now_ms, *, task=None):
    completion = task is not None
    keys = {'format', 'session_id', 'client_pid', 'character_id', 'action', 'sent_utc_ms'}
    keys |= {'task_index', 'task'} if completion else {'contact_path', 'commands', 'native_effect_verified'}
    if not (type(value) is dict and set(value) == keys and type(value.get('format')) is int
            and value['format'] == 1 and value.get('session_id') == identity['session_id']
            and type(value.get('client_pid')) is int and value['client_pid'] == identity['client_pid']
            and type(value.get('character_id')) is int and value['character_id'] == 1
            and type(value.get('sent_utc_ms')) is int
            and ready_ms <= value['sent_utc_ms'] <= now_ms):
        return False
    if completion:
        return (value['action'] == 'completetask' and type(value['task_index']) is int
            and value['task_index'] == 0 and _task(value['task']) and value['task'] == task
            and now_ms - value['sent_utc_ms'] <= COMMAND_MAX_AGE_MS)
    return (value['action'] == 'contactdialog' and value['contact_path'] == CONTACT_PATH
        and value['commands'] == ['/contactdialog ' + CONTACT_PATH]
        and value['native_effect_verified'] is False)


def _read_private(path):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        server.require(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
            and info.st_nlink == 1 and 0 < info.st_size <= RECEIPT_LIMIT,
            'Invalid private task delivery file')
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            raw = source.read(RECEIPT_LIMIT + 1)
        after = os.fstat(descriptor)
        server.require(len(raw) == info.st_size and len(raw) <= RECEIPT_LIMIT
            and (after.st_size, after.st_mtime_ns, after.st_nlink)
                == (info.st_size, info.st_mtime_ns, info.st_nlink),
            'Task delivery changed during read or exceeded bound')
    finally:
        os.close(descriptor)
    return json.loads(raw.decode())


def read_delivery(path, proof, *, session, client_pid, now_utc_ms, accepted=None):
    """Read bounded private sender receipt; transport is not server success."""
    value = _read_private(path)
    if value is None:
        return None
    identity = contact.binding(proof, session, client_pid, now_utc_ms)
    server.require(identity is not None and _receipt(value, identity,
        proof['client_ready_observed_utc_ms'], now_utc_ms,
        task=None if accepted is None else accepted.get('task')),
        'Task delivery does not match this current ready character/task')
    return value


def records(logs, ready_ms, now_ms):
    """Read complete bounded entity/admin records only from owned Atlas routes."""
    if not (type(logs) in (list, tuple) and len(logs) <= server.SERVER_LOG_COUNT_LIMIT):
        return None
    total, found, seen = 0, [], set()
    for item in logs:
        if not (type(item) in (list, tuple) and len(item) == 2
                and type(item[0]) is str and type(item[1]) is str):
            return None
        name, text = item
        size = len(text.encode())
        total += size
        if size > server.SERVER_LOG_FILE_LIMIT or total > server.SERVER_LOG_TOTAL_LIMIT:
            return None
        path = Path(name)
        if path.parent == Path('logs/mapserver') and path.name in ('entity.log', 'admin.log', 'rewards.log'):
            category, route_name = path.stem, 'local_mapserver'
        elif path.parent == Path('logs/dbserver'):
            category_match = re.fullmatch(r'(entity|admin|rewards)_[0-9][0-9_-]*\.log', path.name)
            if category_match is None:
                continue
            category, route_name = category_match[1], 'embedded_dbserver_logserver'
        else:
            continue
        route_pattern = re.compile(r'^(?P<timestamp>\d{6} \d{2}:\d{2}:\d{2}) '
            r'(?:(?P<local_level>[02])|(?P<map_instance>(?i:City_01_01)_1):127\.0\.0\.1:127\.0\.0\.1) +'
            r'(?P<message>[^\r\n]+)$')
        for line_index, line in enumerate(text[:text.rfind('\n') + 1].splitlines()):
            parsed = route_pattern.fullmatch(line)
            if parsed is None or (parsed['local_level'] is not None) != (route_name == 'local_mapserver'):
                continue
            message = parsed['message']
            route = {'path': name, 'line_sha256': hashlib.sha256(line.encode()).hexdigest(),
                'log_timestamp': parsed['timestamp'], 'log_route': route_name,
                'map_instance': parsed['map_instance'], 'log_category': category,
                'line_index': line_index}
            if len(message) > 2048:
                continue
            try:
                utc_ms = int(time.mktime(time.strptime(route['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
            except (ValueError, OverflowError):
                continue
            if not ready_ms <= utc_ms <= now_ms:
                continue
            for kind, pattern in PATTERNS.items():
                match = pattern.fullmatch(message)
                expected_category = 'admin' if kind.startswith('force_') else ('rewards' if kind == 'reward' else 'entity')
                if (match is None or category != expected_category
                        or (parsed['local_level'] == '2' and kind != 'arc')
                        or (parsed['local_level'] == '0' and kind == 'arc')):
                    continue
                if _int(int(match['teamup']), -0x80000000) is None:
                    continue
                key = (kind, utc_ms, message)
                if key in seen:
                    break
                seen.add(key)
                if len(found) >= RECORD_LIMIT:
                    return None  # Never accept a potentially ambiguous truncated inventory.
                found.append(dict(route, path=name, kind=kind, utc_ms=utc_ms,
                    fields={key: value for key, value in match.groupdict().items() if value is not None},
                    native_log_contains_session_or_client_pid=False,
                    native_log_contains_character_db_id=False))
                break
    return sorted(found, key=lambda item: (item['utc_ms'], item['path']))


def _rows(rows):
    if not (type(rows) is dict and set(rows) == set(SELECTED)):
        return None
    result = {}
    for table, fields in SELECTED.items():
        values = rows[table]
        if not (type(values) is list and len(values) <= ROW_LIMIT):
            return None
        selected, seen = [], set()
        for row in values:
            if not (type(row) is dict and set(row) == set(fields)
                    and type(row.get('containerid')) is int and row['containerid'] == 1):
                return None
            normalized = {}
            for field in fields:
                value = row[field]
                if field in ('taskissued', 'storyarcissued'):
                    if value is not None and not (type(value) is str and len(value) <= 1024
                            and value.isascii() and re.fullmatch(r'[A-Za-z0-9+/=\\x]*', value)):
                        return None
                    normalized[field] = value
                else:
                    # PACKTYPE_INT writes through int*, including the U32
                    # task seed. Preserve its signed SQL representation.
                    parsed = _int(value, -0x80000000 if field == 'seed' else 0,
                                  0x7fffffff,
                                  null_zero=field not in ('containerid', 'subid', 'id', 'assigneddbid'))
                    if parsed is None:
                        return None
                    normalized[field] = parsed
            key = normalized.get('subid', 0)
            if key in seen:
                return None
            seen.add(key)
            selected.append(normalized)
        result[table] = selected
    if len(result['ents']) != 1:
        return None
    return result


def _attribute(attributes, identifier):
    if not (type(attributes) is list and len(attributes) <= 100000):
        return None
    values = [row.get('name') for row in attributes if type(row) is dict
        and type(row.get('id')) is int and row['id'] == identifier]
    return values[0] if len(values) == 1 else None


def _same_task(row, accepted):
    original = accepted['sql_at_acceptance']['tasks'][0]
    protected = ('containerid', 'subid', 'id', 'subhandle', 'compoundpos',
                 'assigneddbid', 'assignedtime', 'seed', 'playercreated')
    return all(row[key] == original[key] for key in protected)


def _story_rows_match(current, accepted, contact_points):
    """Preserve selected contact/arc progress around the one pending task.

    TaskComplete sets its own contact notification. Showing UI can clear that
    boolean; no issue bit, relationship or other contact/arc row may change.
    """
    original = accepted['sql_at_acceptance']
    if current['storyarcs'] != original['storyarcs'] or len(current['contacts']) != len(original['contacts']):
        return False
    expected = copy.deepcopy(original['contacts'])
    indices = [index for index, row in enumerate(expected) if row['id'] == accepted['sql_contact_attribute_id']]
    if len(indices) != 1:
        return False
    index = indices[0]
    if current['contacts'][index]['id'] != expected[index]['id'] or current['contacts'][index]['notifyplayer'] not in (0, 1):
        return False
    expected[index]['contactpoints'] = contact_points
    expected[index]['notifyplayer'] = current['contacts'][index]['notifyplayer']
    return current['contacts'] == expected


def _accepted(accepted, identity):
    return (type(accepted) is dict and accepted.get('task_accepted_verified') is True
        and accepted.get('native_task_verified') is True and accepted.get('sql_task_verified') is True
        and accepted.get('session_id') == identity['session_id']
        and type(accepted.get('client_pid')) is int and accepted['client_pid'] == identity['client_pid']
        and type(accepted.get('character_id')) is int and accepted['character_id'] == 1
        and _task(accepted.get('task')) and _rows(accepted.get('sql_at_acceptance')) is not None
        and len(accepted['sql_at_acceptance']['tasks']) == 1
        and accepted['sql_at_acceptance']['tasks'][0]['state'] == 1
        and accepted['sql_at_acceptance']['tasks'][0]['subhandle'] == accepted['task']['subhandle']
        and accepted['sql_at_acceptance']['tasks'][0]['compoundpos'] in (None, 0)
        and accepted.get('contact_path') == CONTACT_PATH and accepted.get('task_file') == TASK_FILE
        and type(accepted.get('observed_utc_ms')) is int
        and identity['client_ready_observed_utc_ms'] <= accepted['observed_utc_ms'])


def observe_acceptance(logs, proof, rows, *, session, client_pid, now_utc_ms,
                       baseline_rows, attributes, setup_receipt):
    result = _result()
    identity = contact.binding(proof, session, client_pid, now_utc_ms)
    if identity is None:
        result['reason'] = 'Current validated reopen connection is unavailable'
        return result
    current, baseline = _rows(rows), _rows(baseline_rows)
    if current is None or baseline is None:
        result['reason'] = 'Malformed, foreign or duplicate task SQL inventory'
        return result
    if baseline['tasks'] or len(current['tasks']) != 1:
        result.update(status='not_observed', reason='Require no baseline tasks and exactly one current accepted task')
        return result
    if current['ents'] != baseline['ents']:
        result['reason'] = 'Experience or influence changed before the bounded authored task acceptance'
        return result
    task = current['tasks'][0]
    if not (task['subid'] == 0 and task['state'] == 1 and task['assigneddbid'] == 1
            and task['compoundpos'] == 0 and task['playercreated'] == 0
            and task['subtasksuccess'] == 0
            and _path(_attribute(attributes, task['id'])) == _path(CONTEXT_PATH)):
        result.update(status='not_observed', reason='Current task is outside the finite authored simple task contract')
        return result
    names = [name for name, contract in TASKS.items() if task['subhandle'] == contract['subhandle']]
    if len(names) != 1 or not _receipt(setup_receipt, identity,
            identity['client_ready_observed_utc_ms'], now_utc_ms):
        result['reason'] = 'Authored contact setup delivery or task binding is unavailable'
        return result
    values = records(logs, identity['client_ready_observed_utc_ms'], now_utc_ms)
    if values is None:
        result['reason'] = 'Owned native task logger inventory exceeds bounds or differs'
        return result
    adds = [item for item in values if item['kind'] == 'add'
        and item['fields']['name'] == names[0] and item['utc_ms'] >= setup_receipt['sent_utc_ms'] - 999]
    if len(adds) != 1:
        result.update(status='not_observed', reason='Require one fresh native task acceptance')
        return result
    added = adds[0]
    opens = [item for item in values if item['kind'] == 'contact' and item['path'] == added['path']
        and item['fields']['teamup'] == added['fields']['teamup']
        and setup_receipt['sent_utc_ms'] - 999 <= item['utc_ms'] <= added['utc_ms']]
    if len(opens) != 1 or _int(int(opens[0]['fields']['context']), 1) is None:
        result.update(status='not_observed', reason='Authored task acceptance lacks one same-route contact delivery')
        return result
    arcs = [row for row in current['storyarcs'] if row['id'] == task['id'] and row['episode'] == 0]
    if len(arcs) != 1 or _path(_attribute(attributes, arcs[0]['contact'])) != _path(CONTACT_PATH):
        result['reason'] = 'Accepted task lacks its one authored first-episode contact/arc SQL binding'
        return result
    selected_contacts = [row for row in current['contacts'] if row['id'] == arcs[0]['contact']]
    if len(selected_contacts) != 1:
        result['reason'] = 'Accepted task contact is missing or ambiguous in current SQL'
        return result
    native_arcs = [item for item in values if item['kind'] == 'arc' and item['path'] == added['path']
        and item['fields']['teamup'] == added['fields']['teamup']
        and opens[0]['utc_ms'] <= item['utc_ms'] <= added['utc_ms']]
    contexts = {int(item['fields']['context']) for item in native_arcs}
    if len(contexts) != 1 or _int(next(iter(contexts), None), -0x80000000, -1) is None:
        result.update(status='not_observed', reason='Accepted story task lacks one fresh native arc context')
        return result
    result.update(status='accepted_verified', task_accepted_verified=True,
        native_task_verified=True, sql_task_verified=True, active_task_count=1,
        session_id=session, client_pid=client_pid, character_id=1, connection=identity,
        observed_utc_ms=now_utc_ms,
        task={'name': names[0], 'context': next(iter(contexts)),
              'subhandle': task['subhandle'], 'task_index': 0},
        context_kind='native_runtime_storyarc_handle_not_sql_attribute_id',
        native_contact_runtime_handle=int(opens[0]['fields']['context']),
        sql_context_attribute_id=task['id'], contact_path=CONTACT_PATH, task_file=TASK_FILE,
        native_task_evidence=added, native_contact_evidence=opens[0], native_arc_evidence=native_arcs[-1],
        sql_contact_attribute_id=arcs[0]['contact'],
        setup_delivery=copy.deepcopy(setup_receipt), sql_at_acceptance=current,
        baseline_sql=baseline, sql_at_acceptance_sha256=server.digest_json(current))
    return result


def observe_completion(logs, proof, accepted, receipt, rows, *, session, client_pid, now_utc_ms):
    result = _result()
    identity = contact.binding(proof, session, client_pid, now_utc_ms)
    if identity is None or not _accepted(accepted, identity):
        result['reason'] = 'Current accepted authored task binding is unavailable'
        return result
    task = accepted['task']
    if not (_receipt(receipt, identity, accepted['observed_utc_ms'], now_utc_ms, task=task)):
        result['reason'] = 'Completion delivery differs from the current accepted task or is stale'
        return result
    current = _rows(rows)
    if current is None or len(current['tasks']) != 1:
        result['reason'] = 'Completed task SQL inventory is missing, malformed or ambiguous'
        return result
    row = current['tasks'][0]
    if not (_same_task(row, accepted) and row['state'] == 4 and row['subtasksuccess'] == 1):
        result.update(status='not_observed', reason='SQL has not reached this simple task succeeded state')
        return result
    values = records(logs, identity['client_ready_observed_utc_ms'], now_utc_ms)
    if values is None:
        result['reason'] = 'Owned native completion inventory exceeds bounds or differs'
        return result
    values = [item for item in values if -999 <= item['utc_ms'] - receipt['sent_utc_ms'] <= COMMAND_MAX_AGE_MS]
    force_auth = [item for item in values if item['kind'] == 'force_auth'
        and _path(item['fields']['filename']) == _path(TASK_FILE)]
    if len(force_auth) != 1:
        result.update(status='not_observed', reason='Require one delivery-bound native ForceComplete block')
        return result
    auth = force_auth[0]
    block = [item for item in values if item['path'] == auth['path']
        and item['utc_ms'] == auth['utc_ms'] and item['fields']['teamup'] == auth['fields']['teamup']]
    contexts = [item for item in block if item['kind'] == 'force_context']
    names = [item for item in block if item['kind'] == 'force_name']
    if not (len(contexts) == len(names) == 1
            and auth['line_index'] < contexts[0]['line_index'] < names[0]['line_index']
            and int(contexts[0]['fields']['context']) == task['context']
            and int(contexts[0]['fields']['subhandle']) == task['subhandle']
            and names[0]['fields']['name'] == task['name']
            and _path(names[0]['fields']['filename']) == _path(TASK_FILE)):
        result.update(status='not_observed', reason='Native ForceComplete block differs from accepted task')
        return result
    successes = [item for item in values if item['kind'] == 'success'
        and item['fields']['name'] == task['name'] and item['fields']['type'] == TASKS[task['name']]['type']
        and item['fields']['teamup'] == auth['fields']['teamup']
        and 0 <= item['utc_ms'] - auth['utc_ms'] <= COMMAND_MAX_AGE_MS]
    if len(successes) != 1:
        result.update(status='not_observed', reason='Require one matching native succeeded event after completion delivery')
        return result
    rewards = [item for item in values if item['kind'] == 'reward'
        and item['fields']['teamup'] == auth['fields']['teamup']
        and 0 <= item['utc_ms'] - successes[0]['utc_ms'] <= 5000]
    if len(rewards) != 1:
        result.update(status='not_observed', reason='Require one bounded native reward credit in this singleton task completion interval')
        return result
    reward = rewards[0]
    xp, debt, influence, prestige, supergroup = [int(reward['fields'][key])
        for key in ('xp', 'debt', 'influence', 'prestige', 'supergroup')]
    if not (0 <= xp <= 1000 and 0 <= debt <= 1000 and influence == prestige == supergroup == 0):
        result.update(status='not_observed', reason='Native reward credit is outside the finite local task reward policy')
        return result
    prior_ent = accepted['sql_at_acceptance']['ents'][0]
    expected_ent = dict(prior_ent, experiencepoints=prior_ent['experiencepoints'] + xp)
    prior_contact = next(row for row in accepted['sql_at_acceptance']['contacts']
        if row['id'] == accepted['sql_contact_attribute_id'])
    current_contacts = [row for row in current['contacts'] if row['id'] == prior_contact['id']]
    expected_points = prior_contact['contactpoints'] + TASKS[task['name']]['task_success_contact_points']
    if (current['ents'][0] != expected_ent or len(current_contacts) != 1
            or current_contacts[0]['contactpoints'] != expected_points
            or not _story_rows_match(current, accepted, expected_points)):
        result.update(status='not_observed', reason='Current SQL reward values do not match the bounded native credited experience and authored contact points')
        return result
    result.update(status='completed_verified', task_accepted_verified=True, task_completed_verified=True,
        native_task_verified=True, sql_task_verified=True, active_task_count=1,
        session_id=session, client_pid=client_pid, character_id=1, connection=identity,
        task=copy.deepcopy(task), observed_utc_ms=now_utc_ms,
        completion_delivery=copy.deepcopy(receipt), native_force_evidence=[auth, contexts[0], names[0]],
        native_success_evidence=successes[0], sql_at_completion=current,
        native_reward_evidence=reward, expected_saved_reward_values=expected_ent,
        expected_saved_contact_points={'id': prior_contact['id'], 'contactpoints': expected_points},
        reward_credit_verified=True, credited_experience=xp, credited_influence=influence,
        native_reward_binding_scope='same_owned_character_single_authored_task_force_success_interval',
        native_reward_log_contains_task_name=False,
        sql_at_completion_sha256=server.digest_json(current),
        completed_task_pending_contact_return=True, reward_turn_in_verified=False,
        evidence_scope='stock_command_completed_authored_task_retained_succeeded_in_current_sql')
    return result


def verify_saved(logs, proof, accepted, completed, rows, *, session, client_pid,
                 now_utc_ms, ordinary_save_verified):
    result = _result()
    identity = contact.binding(proof, session, client_pid, now_utc_ms)
    if identity is None or not _accepted(accepted, identity):
        result['reason'] = 'Accepted task identity differs from this current session'
        return result
    if not (type(completed) is dict and completed.get('task_completed_verified') is True
            and completed.get('task') == accepted['task'] and completed.get('session_id') == session
            and type(completed.get('client_pid')) is int and completed['client_pid'] == client_pid
            and type(completed.get('character_id')) is int and completed['character_id'] == 1
            and type(completed.get('observed_utc_ms')) is int
            and accepted['observed_utc_ms'] <= completed['observed_utc_ms'] <= now_utc_ms):
        result['reason'] = 'Current completed task evidence is unavailable'
        return result
    # Re-evaluate the native/receipt/SQL completion proof at its original bounded
    # observation time. A later ordinary logout must not refresh an old command.
    checked = observe_completion(logs, proof, accepted, completed.get('completion_delivery'),
        completed.get('sql_at_completion'), session=session, client_pid=client_pid,
        now_utc_ms=completed['observed_utc_ms'])
    if checked.get('task_completed_verified') is not True:
        result['reason'] = 'Retained completion proof no longer matches owned native records'
        return result
    current = _rows(rows)
    if current is None or len(current['tasks']) != 1:
        result['reason'] = 'Committed task SQL inventory is missing, malformed or ambiguous'
        return result
    row = current['tasks'][0]
    if not (_same_task(row, accepted) and row['state'] == 4 and row['subtasksuccess'] == 1):
        result['reason'] = 'Committed SQL does not retain this completed task'
        return result
    expected_points = checked['expected_saved_contact_points']
    contacts = [row for row in current['contacts'] if row['id'] == expected_points['id']]
    if (current['ents'][0] != checked['expected_saved_reward_values'] or len(contacts) != 1
            or contacts[0]['contactpoints'] != expected_points['contactpoints']
            or not _story_rows_match(current, accepted, expected_points['contactpoints'])):
        result['reason'] = 'Committed SQL reward values differ from the verified native task credit'
        return result
    if ordinary_save_verified is not True:
        result.update(status='save_pending', reason='Existing ordinary logout and full character save proof is required')
        return result
    result.update(status='saved_verified', verified=True, task_accepted_verified=True,
        task_completed_verified=True, task_save_verified=True, native_task_verified=True,
        sql_task_verified=True, active_task_count=1, session_id=session, client_pid=client_pid,
        character_id=1, task=copy.deepcopy(accepted['task']), observed_utc_ms=now_utc_ms,
        ordinary_character_save_verified=True, committed_task_sql_sha256=server.digest_json(current),
        expected_saved_reward_values=checked['expected_saved_reward_values'],
        expected_saved_contact_points=checked['expected_saved_contact_points'],
        reward_credit_verified=True, credited_experience=checked['credited_experience'],
        credited_influence=checked['credited_influence'],
        committed_sql=current, completed_task_pending_contact_return=True,
        reward_turn_in_verified=False,
        evidence_scope='manual_authored_acceptance_stock_command_success_and_ordinary_save_of_completed_task')
    return result
