"""Strict scalar-only public schemas emitted by the existing initial probes.

These are observation contracts, never character/catalog admission. Names and
decoded text are absent. Source formatters are coh_initial_*_probe_json plus the
bounded reward progress projection selected by interop_network.c.
"""

PROBE_KEYS = ('first_create', 'first_record_pose', 'first_record_sequence',
              'first_record_triggered_moves', 'first_record_ai_animation',
              'first_record_netfx', 'first_record_costume_prefix', 'first_reward_string')
REFUSED = ('selected_owner_bound', 'source_generation_admitted', 'complete_initial_character',
           'actor_publication', 'ack_permitted', 'world_authority')
SPECS = {
    'first_create': ('coh-initial-first-create-v1',
        'header_validated create_validated is_self self_dbid_matches_handoff',
        'header_end_bit create_end_bit failure_bit entity_index entity_type',
        ('NONE', 'INPUT', 'HEADER', 'INDEX', 'CREATE', 'FIRST_RECORD_BODY_REQUIRED', 'EMPTY_INITIAL_LIST'), True),
    'first_record_pose': ('coh-initial-first-pose-v1',
        'flags_validated mode_validated position_validated orientation_validated pose_validated',
        'begin_bit flags_end_bit mode_end_bit position_end_bit pose_end_bit failure_bit',
        ('NONE', 'INPUT', 'RARE_FLAGS', 'MODE', 'POSITION', 'ORIENTATION', 'FIRST_SEQUENCE_BODY_REQUIRED'), True),
    'first_record_sequence': ('coh-initial-first-sequence-v1',
        'update_seen index_present ticks_present movement_bits_present sequence_validated',
        'begin_bit index_end_bit ticks_end_bit sequence_end_bit failure_bit',
        ('NONE', 'INPUT', 'UPDATE', 'INDEX', 'TICKS', 'MOVEMENT_BITS', 'FIRST_TRIGGERED_MOVES_REQUIRED'), False),
    'first_record_triggered_moves': ('coh-initial-first-triggered-v1',
        'count_validated triggered_moves_validated',
        'begin_bit count_end_bit triggered_end_bit failure_bit local_trigger_limit count entries_validated current_entry fx_entries',
        ('NONE', 'INPUT', 'COUNT', 'INDEX', 'TICKS', 'FX', 'FIRST_AI_ANIMATION_REQUIRED'), False),
    'first_record_ai_animation': ('coh-initial-first-aianim-v1',
        'update_seen string_present ai_animation_validated',
        'begin_bit ai_end_bit failure_bit string_bytes text_limit_including_nul',
        ('NONE', 'INPUT', 'UPDATE', 'STRING_FLAG', 'STRING', 'FIRST_NETFX_REQUIRED'), False),
    'first_record_netfx': ('coh-initial-first-netfx-v1',
        'pchar_things in_phase body_present netfx_validated cross_prefix_in_phase_verified',
        'begin_bit flags_end_bit netfx_end_bit failure_bit effect_count',
        ('NONE', 'INPUT', 'FLAGS', 'BODY', 'FIRST_COSTUME_BODY_REQUIRED'), True),
}
COSTUME_STAGES = ('NONE', 'INPUT', 'SELECTOR_FLAG', 'SELECTOR', 'SELF', 'REWARD_COUNT',
    'REWARD_FLAG', 'SLOTS', 'MULTIPLE', 'STORED_COUNT', 'FIRST_COSTUME_REWARD_STRING_REQUIRED',
    'FIRST_COSTUME_DICTIONARY_REQUIRED', 'FIRST_NPC_COSTUME_BODY_REQUIRED', 'FIRST_SEQUENCE_COSTUME_BODY_REQUIRED')
REWARD_STAGES = ('NONE', 'INPUT', 'PRESENCE', 'STORAGE', 'TEXT',
                 'FIRST_REWARD_DICTIONARY_REQUIRED', 'FIRST_REWARD_CONTINUATION_REQUIRED')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def integer(value, maximum, label):
    need(type(value) is int and 0 <= value <= maximum, 'invalid probe integer: ' + label)


def entity_failure(value, bit_limit):
    need(isinstance(value, dict) and set(value) == {'status', 'stage', 'bit'}, 'invalid probe entity failure keys')
    integer(value['status'], 7, 'entity failure status')
    integer(value['stage'], 32, 'entity failure stage')
    integer(value['bit'], bit_limit, 'entity failure bit')


def probe_snapshot(name, value, bit_limit):
    if value is None:
        return
    need(isinstance(value, dict), 'probe must be null or scalar object: ' + name)
    if name in SPECS:
        schema, booleans, numbers, stages, failure = SPECS[name]
        booleans, numbers = booleans.split(), numbers.split()
        keys = set(booleans + numbers + list(REFUSED) + ['schema', 'diagnostic_only', 'status', 'stage', 'stage_id'])
        if failure:
            keys.add('entity_failure')
        need(set(value) == keys, 'unexpected probe public keys: ' + name)
        need(value['schema'] == schema and value['diagnostic_only'] is True, 'invalid probe scope: ' + name)
        need(all(type(value[k]) is bool for k in booleans), 'invalid probe boolean: ' + name)
        need(all(value[k] is False for k in REFUSED), 'probe granted authority: ' + name)
        integer(value['status'], 7, 'status')
        integer(value['stage_id'], len(stages) - 1, 'stage id')
        need(value['stage_id'] > 0 and value['stage'] == stages[value['stage_id']], 'probe stage enum mismatch: ' + name)
        for key in numbers:
            integer(value[key], bit_limit if key.endswith('_bit') else 0xffffffff, key)
        if failure:
            entity_failure(value['entity_failure'], bit_limit)
        if name == 'first_record_triggered_moves':
            need(value['local_trigger_limit'] == 16, 'trigger limit differs')
            need(not value['count_validated'] or value['count'] <= 16, 'validated trigger count exceeds policy')
            need(value['entries_validated'] <= 16 and value['current_entry'] <= 16 and value['fx_entries'] <= value['entries_validated'], 'trigger progress bounds')
        if name == 'first_record_ai_animation':
            need(value['text_limit_including_nul'] == 1000 and value['string_bytes'] <= 1000, 'AI text bounds')
            need(not value['ai_animation_validated'] or value['string_bytes'] < 1000, 'validated AI string lacks NUL room')
        if name == 'first_record_netfx':
            need(value['cross_prefix_in_phase_verified'] is False and value['effect_count'] <= 32, 'netfx authority/count differs')
        return
    if name == 'first_record_costume_prefix':
        bools = 'selector_validated self_wire_consistent framing_validated source_generation_admitted ack_permitted world_authority'.split()
        numbers = 'status begin_bit prefix_end_bit failure_bit type reward_list reward_index body_count'.split()
        need(set(value) == set(bools + numbers + ['schema', 'stage', 'reward_counts', 'absent_rewards']), 'unexpected costume public keys')
        need(value['schema'] == 'coh-initial-costume-prefix-v1' and value['stage'] in COSTUME_STAGES[1:], 'costume schema/stage differs')
        need(all(type(value[k]) is bool for k in bools), 'costume boolean differs')
        need(all(value[k] is False for k in ('source_generation_admitted', 'ack_permitted', 'world_authority')), 'costume probe granted authority')
        for key in numbers:
            integer(value[key], 7 if key == 'status' else bit_limit if key.endswith('_bit') else 0xffffffff, key)
        for key in ('reward_counts', 'absent_rewards'):
            need(isinstance(value[key], list) and len(value[key]) == 2, 'costume array shape differs')
            for item in value[key]:
                integer(item, 0xffffffff, key)
        need(not value['selector_validated'] or 1 <= value['type'] <= 4, 'validated costume selector differs')
        return
    need(name == 'first_reward_string', 'unknown probe name')
    keys = {'status', 'stage', 'bit', 'bytes', 'literal_validated'}
    need(set(value) in (keys, keys | {'progress'}), 'unexpected reward public keys')
    integer(value['status'], 7, 'reward status')
    integer(value['bit'], bit_limit, 'reward bit')
    integer(value['bytes'], 260, 'reward literal bytes')
    need(value['stage'] in REWARD_STAGES[1:] and type(value['literal_validated']) is bool, 'reward stage/boolean differs')
    need(not value['literal_validated'] or value['bytes'] < 260, 'validated reward lacks NUL room')
    if 'progress' in value:
        progress = value['progress']
        need(isinstance(progress, list) and len(progress) in (7, 9), 'reward progress shape differs')
        maxima = (7, 43, 256, 256, bit_limit, bit_limit, 0xffffffff) if len(progress) == 7 else (7, 6, 2, 256, 256, 256, bit_limit, 1, 6)
        for item, maximum in zip(progress, maxima):
            integer(item, maximum, 'reward progress')
        need(progress[1] > 0, 'reward progress stage absent')


def separate_current_probes(value, required=False):
    """Remove only a complete validated extension before legacy-core validation."""
    present = set(value).intersection(PROBE_KEYS)
    need(not present or present == set(PROBE_KEYS), 'partial initial probe schema')
    need(not required or present == set(PROBE_KEYS), 'current initial probe schema absent')
    core = dict(value)
    if present:
        integer(value.get('initial_bits'), 4194304 * 8, 'complete observed initial bits')
    for name in present:
        probe_snapshot(name, core.pop(name), value.get('initial_bits', 0))
    return core
