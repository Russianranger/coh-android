"""Strict public projection for the bounded 0.1.11 native report extension."""

OMISSION_FIELDS = ('first_create', 'first_record_pose', 'first_record_sequence',
    'first_record_triggered_moves', 'first_record_ai_animation', 'first_record_netfx',
    'first_record_costume_prefix', 'first_reward_string', 'first_reward_progress')
REPORT_KEYS = {'owner_present', 'owner_terminal', 'initial_observation_known',
    'initial_observed', 'groups_present_files', 'groups_roots', 'report_limit_bytes',
    'report_truncated', 'report_omitted_mask', 'report_invalid_mask', 'report_omitted_fields'}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def separate_report_extension(value, required=False):
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
