#!/usr/bin/env python3
"""Closed successor native promotion boundary; historical consumers remain exact.

This scaffold can inspect additive research evidence, but cannot promote a new
Game or Map executable. Actual admission is a separately reviewed integration.
"""
from __future__ import annotations
import copy
import hashlib
import json
import re

PROMOTIONS_IMPLEMENTED = False
RETAINED_MAP = {'bytes': 7475200,
    'sha256': 'fea96d0a20f5e245930abd0a97e8cc1da7c4ef4c83ff8a7d5a5c283ba8071363'}
MAP_CANDIDATE = {'bytes': 7480832,
    'sha256': '5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6'}
MAP_SOURCE = '47e40d4d586d29e273e31ed4d0d51d160832b89d'
MAP_BUILD_RUN = 38350813669
MAP_BUILD_ARTIFACT = {'id': 11790609618, 'bytes': 3307410,
    'sha256': '69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab'}


def require(value, message):
    if not value: raise ValueError(message)


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        allow_nan=False, ensure_ascii=False).encode()).hexdigest()


def pin(value):
    require(type(value) is dict and set(value) == {'bytes', 'sha256'}
        and type(value['bytes']) is int and 0 < value['bytes'] <= 256*1024**2
        and type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
        'Exact bounded native evidence pin required')
    return value


def validate_disabled_promotions(value):
    require(type(value) is dict and set(value) == {'game', 'mapserver'}
        and all(type(value[name]) is dict and set(value[name]) == {'enabled'}
            and value[name]['enabled'] is False for name in value),
        'Native Game/Map promotions are closed until exact reviewed component gates are integrated')
    require(PROMOTIONS_IMPLEMENTED is False, 'This scaffold has no implemented native promotion path')
    return copy.deepcopy(value)


def retain_native_component(donor, actual_server_archives, actual_component):
    require(actual_server_archives == donor['package_preflight']['server_archives']
        and actual_component == donor['map_startup_component'],
        'Closed native promotion must preserve exact .36 Game/Db/Map/schema/component bytes and producers')
    require(actual_component.get('files', {}).get('MapServer.exe') == RETAINED_MAP,
        'Unknown consumer cannot use the retained cache/texture projection compatibility')
    return {'format': 1, 'policy': 'retain_exact_audited_036_native_consumers',
        'native_promotions_implemented': False, 'new_native_consumer_admitted': False,
        'unknown_consumer_allowed': False, 'old_producer_facts_relabelled': False,
        'mapserver': RETAINED_MAP, 'original_component': copy.deepcopy(actual_component),
        'server_archives': copy.deepcopy(actual_server_archives)}


def inspect_map_research_wrapper(wrapper, previous_component):
    """Check additive evidence structure without granting runtime authority.

    Caller must authenticate the source/build/qualification artifact bytes
    independently. This function does not convert receipt assertions to tests.
    """
    require(type(wrapper) is dict and set(wrapper) == {'receipt', 'receipt_sha256'},
        'Exact additive native research wrapper required')
    receipt = wrapper['receipt']
    require(type(receipt) is dict and wrapper['receipt_sha256'] == canonical_sha(receipt),
        'Native research wrapper digest differs')
    require(receipt.get('format') == 1 and type(receipt.get('format')) is int
        and receipt.get('role') == 'nonshipping_map_metadata_research'
        and receipt.get('previous_component') == previous_component
        and receipt.get('previous_component_sha256') == canonical_sha(previous_component)
        and receipt.get('native_producer_relabelled') is False
        and receipt.get('shipping_allowed') is False
        and receipt.get('behavioral_collision_validated') is False
        and receipt.get('physical_timing_validated') is False,
        'Research evidence must preserve the original component and truthful nonshipping scope')
    require(receipt.get('mapserver') == MAP_CANDIDATE
        and receipt.get('build_repository_commit') == MAP_SOURCE
        and receipt.get('build_run_id') == MAP_BUILD_RUN
        and receipt.get('build_artifact') == MAP_BUILD_ARTIFACT,
        'Exact completed native candidate producer required')
    for name in ('build_manifest', 'native_fixture', 'paired_preload', 'native_world'):
        pin(receipt.get(name))
    return {'status': 'research_structure_checked_only', 'shipping_allowed': False,
        'runtime_admission_granted': False, 'mapserver': MAP_CANDIDATE,
        'receipt_sha256': wrapper['receipt_sha256'],
        'behavioral_collision_validated': False, 'physical_timing_validated': False}
