#!/usr/bin/env python3
"""Parse bounded native PIG index observations without granting cache authority."""
from __future__ import annotations
import json
import re

MARKER = 'COH_NATIVE_PIG_INDEX_CAPTURE_V1'
MAX_CAPTURE_BYTES = 8 * 1024**2 + 4096
MAX_PROVIDERS = 64
MAX_ROWS = 200000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unsigned(value):
    return type(value) is int and 0 <= value <= 0xffffffff


def path(value):
    return type(value) is str and 0 < len(value) <= 259 and all(0 < ord(c) <= 255 for c in value)


def parse(console, generation, windows_pid):
    require(type(console) is str and len(console.encode('utf-8')) <= 48 * 1024**2, 'Bounded original native console required')
    require(type(generation) is str and re.fullmatch(r'[0-9a-f]{64}', generation), 'Exact current generation binding required')
    require(unsigned(windows_pid) and windows_pid > 0, 'Exact owned current Windows PID required')
    events, capture_bytes = [], 0
    for line in console.splitlines():
        if MARKER not in line:
            continue
        require(line.startswith(MARKER + ' ') and line.count(MARKER) == 1, 'Complete marker-leading native row required')
        payload = line.split(MARKER + ' ', 1)
        require(len(payload) == 2 and len(payload[1].encode('utf-8')) < 2048, 'Bounded complete native capture row required')
        capture_bytes += len(line.encode('utf-8')) + 1
        require(capture_bytes <= MAX_CAPTURE_BYTES, 'Native index capture exceeds limit')
        value = json.loads(payload[1], object_pairs_hook=unique_object)
        require(type(value) is dict and type(value.get('event')) is str, 'Typed native capture event required')
        events.append(value)
        require(len(events) <= MAX_ROWS + MAX_PROVIDERS + 2, 'Native capture event count exceeds limit')
    require(len(events) >= 2, 'Complete current native index capture missing')
    begin, end = events[0], events[-1]
    require(set(begin) == {'event', 'generation', 'providers', 'mode', 'gdd_root', 'windows_pid', 'windows_thread', 'native_registration_allowed'}
            and begin['event'] == 'begin' and begin['generation'] == generation
            and unsigned(begin['windows_pid']) and begin['windows_pid'] == windows_pid and unsigned(begin['windows_thread']) and begin['windows_thread'] > 0
            and type(begin['providers']) is int and 0 <= begin['providers'] <= MAX_PROVIDERS
            and type(begin['mode']) is int and begin['mode'] == 1 and path(begin['gdd_root'])
            and begin['native_registration_allowed'] is False, 'Native generation/owner/mode header differs')
    require(set(end) == {'event', 'complete', 'providers', 'rows', 'native_registration_allowed'}
            and end['event'] == 'end' and end['complete'] is True
            and end['native_registration_allowed'] is False and type(end['providers']) is int and end['providers'] == begin['providers']
            and type(end['rows']) is int and 0 <= end['rows'] <= MAX_ROWS, 'Native index capture incomplete')
    providers, rows, current = [], 0, None
    for event in events[1:-1]:
        if event['event'] == 'provider':
            if current is not None:
                require(len(current['members_observed']) == current['members'], 'Prior native provider incomplete')
            require(set(event) == {'event', 'ordinal', 'virtual_location', 'archive', 'folder_cache_mount', 'members'}
                    and type(event['ordinal']) is int and event['ordinal'] == len(providers)
                    and type(event['virtual_location']) is int and event['virtual_location'] == -len(providers) - 1
                    and path(event['archive']) and path(event['folder_cache_mount'])
                    and event['folder_cache_mount'] == event['archive'] + ':'
                    and type(event['members']) is int and 0 <= event['members'] <= MAX_ROWS - rows,
                    'Native provider order/mount/index bounds differ')
            current = dict(event, members_observed=[])
            providers.append(current)
        elif event['event'] == 'member':
            require(current is not None and set(event) == {'event', 'provider', 'file_index', 'name', 'name_present', 'special', 'timestamp', 'size', 'metadata_available'}
                    and type(event['provider']) is int and event['provider'] == current['ordinal']
                    and type(event['file_index']) is int and event['file_index'] == len(current['members_observed'])
                    and event['file_index'] < current['members'] and type(event['special']) is bool,
                    'Native member order/index/state differs')
            if event['name_present'] is True:
                require(path(event['name']) and event['metadata_available'] is True
                        and unsigned(event['timestamp']) and unsigned(event['size']), 'Native member metadata differs')
            else:
                require(event['name_present'] is False and event['name'] is None
                        and event['metadata_available'] is False and event['timestamp'] is None and event['size'] is None,
                        'Empty native slot must retain explicit unavailable metadata')
            current['members_observed'].append(dict(event))
            rows += 1
        else:
            raise ValueError('Unexpected native capture event')
    require(len(providers) == begin['providers'] and rows == end['rows']
            and (current is None or len(current['members_observed']) == current['members']), 'Full native index membership missing')
    return {'format': 1, 'role': 'observed_current_native_pig_index_capture', 'status': 'complete_index_observation',
            'begin': begin, 'end': end, 'providers': providers, 'native_pig_index_observed_complete': True,
            'archive_bytes_authenticated_by_this_parser': False, 'current_provider_generation_qualified': False,
            'native_registration_allowed': False, 'publication_allowed': False}


def unique_object(pairs):
    value = {}
    for name, item in pairs:
        require(name not in value, 'Duplicate native capture JSON key')
        value[name] = item
    return value
