"""Strict public projection for the bounded 0.1.11 native report extension."""
import functools
import json
from pathlib import Path
import re


@functools.lru_cache(maxsize=1)
def outer_field_names():
    """Use the linked source adapter's fixed names as its enum grows."""
    source = Path(__file__).resolve().parents[2] / 'engine/entities/coh_original_ent_costume.c'
    text = source.read_text()
    found = re.search(r'coh_original_ent_costume_field_name\(uint32_t \w+\).*?names\[\]\s*=\s*\{(.*?)\};', text, re.S)
    if found is None:
        raise ValueError('original source field-name table unavailable')
    names = json.loads('[' + ','.join(re.findall(r'"(?:\\.|[^"\\])*"', found[1])) + ']')
    if not names or len(names) > 128:
        raise ValueError('original source field-name table unbounded')
    return names

OMISSION_FIELDS = ('first_create', 'first_record_pose', 'first_record_sequence',
    'first_record_triggered_moves', 'first_record_ai_animation', 'first_record_netfx',
    'first_record_costume_prefix', 'first_reward_string', 'first_reward_progress')
REPORT_KEYS = {'owner_present', 'owner_terminal', 'initial_observation_known',
    'initial_observed', 'groups_present_files', 'groups_roots', 'report_limit_bytes',
    'report_truncated', 'report_omitted_mask', 'report_invalid_mask', 'report_omitted_fields'}
JAVA_REPORT_KEYS = {'last_observed_phase', 'control_observation', 'report_serialization_unknown'}
JAVA_PHASES = {'UNKNOWN', 'IDLE', 'DB_CONNECTING', 'CHARACTERS_READY', 'MAP_CONNECTING',
    'SCENE_INCOMPLETE', 'WAIT_GROUPS', 'WAIT_ALLENTS', 'INITIAL_OBSERVED', 'TIMED_OUT', 'SUSPENDED',
    'CANCELLED', 'CLOSED', 'FAILED', 'UNSUPPORTED', 'OWNER_BUSY', 'POLICY_UNAVAILABLE'}


def separate_java_extension(value):
    present = JAVA_REPORT_KEYS.intersection(value)
    need(not present or present == JAVA_REPORT_KEYS, 'partial Java report extension')
    if not present:
        return dict(value)
    need(type(value['last_observed_phase']) is str and value['last_observed_phase'] in JAVA_PHASES,
         'invalid retained Java protocol phase')
    need(type(value['report_serialization_unknown']) is bool
         and value['report_serialization_unknown'] == (value['phase'] in ('REPORT_LIMIT', 'REPORT_UNAVAILABLE')),
         'invalid Java report serialization status')
    control = value['control_observation']
    need(isinstance(control, dict) and set(control) == {'source', 'owner_present', 'known', 'owner_terminal', 'initial_observed'},
         'unexpected Java control observation keys')
    need(control['source'] == 'native_scalar_control_state', 'invalid Java control source')
    need(all(type(control[key]) is bool for key in ('owner_present', 'known', 'owner_terminal')),
         'invalid Java control Boolean')
    need(control['initial_observed'] is None or type(control['initial_observed']) is bool,
         'invalid Java initial observation')
    need(control['known'] or control['initial_observed'] is not False,
         'unknown Java scalar control fabricated a negative initial observation')
    if control['initial_observed'] is True:
        need(control['owner_terminal'], 'positive Java initial observation lost terminal state')
    return {key: item for key, item in value.items() if key not in JAVA_REPORT_KEYS}



def need(ok, message):
    if not ok:
        raise ValueError(message)


def separate_catalog_boundary(value):
    """Recognize only validated additive source framing, never a dictionary owner."""
    if 'catalog_boundary' not in value:
        return dict(value)
    boundary = value['catalog_boundary']
    if boundary is not None:
        need(value.get('schema') == 'coh-native-initial-interop-numeric-v1', 'catalog boundary schema')
        need(isinstance(boundary, list) and len(boundary) == 7
             and all(type(item) is int and item >= 0 for item in boundary), 'catalog boundary numeric shape')
        status, stage, done0, done1, end, delta, metadata = boundary
        need(status == 2 and stage in (41, 43) and done0 <= 256 and done1 <= 256
             and end <= 33554432 and delta <= 33554432 - end and metadata <= 0x1fffffff,
             'catalog boundary source domains')
        count, width = (metadata >> 21) & 31, (metadata >> 26) & 7
        compressed = bool(metadata & (1 << 18))
        need(delta >= (3272 if compressed else 3265) and metadata & 63 <= 54
             and (not compressed or (metadata >> 19) & 3 == 0), 'catalog boundary prefix/framing metadata')
        need((count == width == 0) if stage == 41 else
             (count <= 30 and width == (5 if compressed else 1 if count < 15 else 2)),
             'catalog boundary flag/count framing')
        # Retained Java diagnostics may survive partial serialization. A current
        # complete native report must still have its genuine positive observation.
        if value.get('phase') not in ('REPORT_LIMIT', 'REPORT_UNAVAILABLE'):
            need(value.get('raw_allents_observed') is True, 'catalog boundary without initial observation')
        reward = value.get('first_reward_string')
        if isinstance(reward, dict) and 'progress' in reward:
            need(reward['progress'] == boundary, 'essential/optional source progress mismatch')
    return {key: item for key, item in value.items() if key != 'catalog_boundary'}


def separate_report_extension(value, required=False):
    value = separate_catalog_boundary(separate_java_extension(value))
    if 'rare_suffix' in value or 'initial_suffix_next' in value:
        rare = value.get('rare_suffix')
        need('costume_outer' in value and isinstance(rare, list) and len(rare) == 7
             and all(type(item) is int and item >= 0 for item in rare), 'rare suffix source shape')
        status, stage, begin, end, failure, exact, complete = rare
        names = ('not observed', 'very-rare prefix', 'very-rare tail', 'teammate buffs', 'entity list sentinel')
        need(status <= 7 and stage < len(names) and begin <= end <= 33554432
             and failure <= 33554432 and exact <= 1 and complete <= 1
             and (not complete or status == 0 and stage == 4 and exact == 1), 'rare suffix source domains')
        need(value.get('initial_suffix_next') == names[stage], 'rare suffix source next field')
        value = {key: item for key, item in value.items() if key not in ('rare_suffix', 'initial_suffix_next')}
    if 'inventory_words' in value:
        inventory = value['inventory_words']
        need('costume_outer' in value and isinstance(inventory, list) and len(inventory) == 5
             and all(type(item) is int and item >= 0 for item in inventory), 'inventory source shape')
        begin, end, count, words, negative = inventory
        need(begin <= end <= 33554432 and count <= 0x7fffffff and words <= 33554432
             and negative <= words, 'inventory source domains')
        value = {key: item for key, item in value.items() if key != 'inventory_words'}
    if 'power_unresolved' in value:
        unresolved = value['power_unresolved']
        need('power_customization' in value and isinstance(unresolved, list) and len(unresolved) == 5
             and all(type(item) is int and item >= 0 for item in unresolved), 'unresolved power source shape')
        entries, count, first, last, scratch = unresolved
        need(count <= entries <= 0x7fffffff and first <= 0xffffffff and last <= 0xffffffff
             and scratch <= 65536 and (count or first == last == 0), 'unresolved power source domains')
        value = {key: item for key, item in value.items() if key != 'power_unresolved'}
    if 'initial_replay' in value:
        replay = value['initial_replay']
        need(isinstance(replay, list) and len(replay) == 2
             and all(type(item) is int and item >= 0 for item in replay)
             and replay[0] <= 65536 and replay[1] <= 3
             and (not replay[0] or not replay[1]), 'INITIAL replay retention shape')
        value = {key: item for key, item in value.items() if key != 'initial_replay'}
    outer_keys = {'costume_outer', 'selected_costume', 'costume_next', 'costume_next_kind', 'power_customization', 'initial_tail'}
    outer_present = outer_keys.intersection(value)
    need(not outer_present or outer_present == outer_keys, 'partial original outer costume extension')
    if outer_present:
        outer, selected = value['costume_outer'], value['selected_costume']
        need(isinstance(outer, list) and len(outer) == 10
             and all(type(item) is int and item >= 0 for item in outer), 'outer costume numeric shape')
        names = outer_field_names()
        need(outer[0] <= 7 and outer[1] < len(names)
             and all(item <= 33554432 for item in outer[2:6])
             and all(item in (0, 1) for item in outer[6:])
             and outer[8:] == [0, 0], 'outer costume source domains/transaction scope')
        need(isinstance(selected, list) and len(selected) == 5
             and all(type(item) is int and item >= 0 for item in selected)
             and selected[0] <= 1 and selected[1] < 10 and selected[2] < 9
             and selected[3] <= 30 and selected[4] <= 33554432, 'selected decoded costume shape')
        need(selected[0] or selected[2:] == [0, 0, 0], 'absent selected costume fabricated values')
        power, tail = value['power_customization'], value['initial_tail']
        need(isinstance(power, list) and len(power) == 8
             and all(type(item) is int and item >= 0 for item in power)
             and power[0] <= 0x7fffffff and power[1] <= 1 and power[2] <= 10
             and power[3] <= 0x7fffffff and power[4] <= 1 and power[5] <= 0xffffffff
             and all(item <= 33554432 for item in power[6:]), 'power customization source domains')
        need(isinstance(tail, list) and len(tail) == 3
             and all(type(item) is int and item in (0, 1) for item in tail), 'initial tail source domains')
        need(value['costume_next'] == names[outer[1]], 'outer source field name mismatch')
        next_kind = value['costume_next_kind']
        need(next_kind in ('not observed', 'required table', 'implementation remaining', 'source field'), 'outer source boundary kind')
        if power[4]:
            need(next_kind == 'required table', 'actual BasePower dependency mislabeled')
        elif value['costume_next'] == 'later very-rare entity fields':
            need(next_kind == 'implementation remaining', 'known source implementation mislabeled as table')
        elif not outer[1]:
            need(next_kind == 'not observed', 'absent source observation fabricated')
        value = {key: item for key, item in value.items() if key not in outer_keys}
    if 'costume_bodies' in value:
        bodies = value['costume_bodies']
        need(isinstance(bodies, list) and len(bodies) == 2
             and all(type(item) is int and item >= 0 for item in bodies)
             and bodies[1] <= bodies[0] <= 10, 'original costume body count shape')
        value = {key: item for key, item in value.items() if key != 'costume_bodies'}
    if 'client_slots' in value:
        slots = value['client_slots']
        need(isinstance(slots, list) and len(slots) == 4
             and all(type(item) is int and item >= 0 for item in slots), 'CLIENT slot resource shape')
        status, raw, index, mapped = slots
        need(status <= 7 and raw in (0, 641477) and index in (0, 134144)
             and mapped <= 8388608, 'CLIENT slot resource domains')
        need((raw == index == mapped == 0) or
             (status == 0 and raw == 641477 and index == 134144 and mapped >= raw),
             'CLIENT slot ownership mismatch')
        value = {key: item for key, item in value.items() if key != 'client_slots'}
    present = REPORT_KEYS.intersection(value)
    need(not present or present == REPORT_KEYS, 'partial bounded report extension')
    need(not required or present == REPORT_KEYS, 'bounded report extension absent')
    if not present:
        return dict(value)
    for key in ('owner_present', 'owner_terminal', 'initial_observation_known', 'report_truncated'):
        need(type(value[key]) is bool, 'invalid report boolean: ' + key)
    if value['initial_observation_known']:
        need(type(value['initial_observed']) is bool, 'known initial observation is not Boolean')
        need(value['initial_observed'] == value['raw_allents_observed'], 'initial observation differs from producer')
    else:
        need(value['initial_observed'] is None, 'unknown initial observation exposed as Boolean')
    for key in ('groups_present_files', 'groups_roots'):
        need(type(value[key]) is int and 0 <= value[key] <= 0xffffffff, 'invalid GROUPS numeric projection')
    need(value['report_limit_bytes'] == 7168, 'native report resource limit changed')
    for key in ('report_omitted_mask', 'report_invalid_mask'):
        need(type(value[key]) is int and 0 <= value[key] <= 511, 'invalid report omission mask')
    omitted, invalid = value['report_omitted_mask'], value['report_invalid_mask']
    need(invalid & ~omitted == 0, 'invalid fragment not explicitly omitted')
    need(value['report_truncated'] == bool(omitted), 'report truncation differs from omitted fields')
    need(value['report_omitted_fields'] == [name for bit, name in enumerate(OMISSION_FIELDS) if omitted & (1 << bit)], 'report omission list differs from fixed mask')
    for bit, name in enumerate(OMISSION_FIELDS[:8]):
        if omitted & (1 << bit):
            need(value.get(name) is None, 'omitted diagnostic still exposes a value')
    if omitted & 256 and isinstance(value.get('first_reward_string'), dict):
        need('progress' not in value['first_reward_string'], 'omitted reward progress retained')
    if value['phase'] in ('INITIAL_OBSERVED', 'TIMED_OUT', 'SUSPENDED', 'CANCELLED', 'CLOSED', 'FAILED', 'UNSUPPORTED'):
        need(value['owner_terminal'], 'terminal protocol phase lost terminal owner state')
    if value['phase'] == 'INITIAL_OBSERVED':
        need(value['owner_present'] and value['owner_terminal'] and value['initial_observed'] is True,
             'observed capture lost independent terminal owner state')
    return {key: item for key, item in value.items() if key not in REPORT_KEYS}
