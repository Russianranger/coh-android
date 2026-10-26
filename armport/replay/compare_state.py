#!/usr/bin/env python3
"""Compare explicitly partial snapshots; never declares the M3 exit test met."""
import argparse
import copy
import json
from pathlib import Path
import tempfile

import run_ci



# Review 5646841168: these additions apply only to snapshot 0 of the
# ID1/31 comparison. Saved data, same-ID pairs and later snapshots stay literal.
INITIAL_CHANNEL_IDS = (
    'pkt_id_friendslist', 'pkt_id_seq_move', 'pkt_id_seq_triggermove',
    'pkt_id_logout', 'pkt_id_supergroup', 'pkt_id_costume', 'pkt_id_powerCust',
    'pkt_id_xlucency', 'pkt_id_titles', 'pkt_id_character_stats',
    'pkt_id_targetting', 'pkt_id_status_effects', 'pkt_id_buffs',
    'pkt_id_debug_info', 'pkt_id_rare_bits', 'pkt_id_state_mode')
_LOW = ('HitPoints', 'Absorb', 'Endurance', 'Meter', 'StealthRadiusPlayer')
_HIGH = ('HitPoints', 'Absorb', 'Endurance', 'Meter', 'PerceptionRadius',
         'StealthRadiusPlayer', 'Confused')
_LEVELS = ('Level', 'CombatLevel')
ATTRIBUTE_ID_SCHEMAS = {
    'basic': (('CurrentAttribs', _LOW), ('MaxAttribs', _LOW), ('SendLevels', _LEVELS)),
    'self': (('CurrentAttribs', _HIGH + ('ToHit',)), ('MaxAttribs', _HIGH),
             ('SendLevels', _LEVELS), ('ExperiencePoints', None),
             ('ExperienceDebt', None), ('ExperienceRest', None), ('InfluencePoints', None))}


def canonical_attribute_ids(rows, schema, initial_id):
    # Match both the original schema position and name. Unknown or malformed
    # shapes are left literal, never recursively normalized by key spelling.
    if not isinstance(rows, list) or len(rows) != len(schema):
        return
    if any(not isinstance(row, dict) or set(row) != {'field', 'ids'}
           or row['field'] != name for row, (name, _) in zip(rows, schema)):
        return
    for row, (_, children) in zip(rows, schema):
        if children is not None:
            canonical_attribute_ids(row['ids'], tuple((name, None) for name in children), initial_id)
        elif type(row['ids']) is int and row['ids'] == initial_id:
            row['ids'] = 'synthetic_INITIAL'


def canonical_initial_ids(document, initial_id, snapshot_index=None):
    result = copy.deepcopy(document)
    for entity in result['entities']:
        if entity['pkt_id_create'] == initial_id:
            entity['pkt_id_create'] = 'synthetic_INITIAL'
        for field in ('pkt_id_pos', 'pkt_id_qrot'):
            entity[field] = ['synthetic_INITIAL' if value == initial_id else value
                             for value in entity[field]]
        if type(snapshot_index) is int and snapshot_index == 0:
            channels = entity.get('packet_order', {})
            for name in INITIAL_CHANNEL_IDS:
                if type(channels.get(name)) is int and channels[name] == initial_id:
                    channels[name] = 'synthetic_INITIAL'
            attributes = entity.get('attribute_packet_order', {})
            for name, schema in ATTRIBUTE_ID_SCHEMAS.items():
                canonical_attribute_ids(attributes.get(name), schema, initial_id)
        player = entity['player']
        if player and player['lastClientStatePktId'] == initial_id:
            player['lastClientStatePktId'] = 'synthetic_INITIAL'
    for deletion in result['delete_history']:
        if deletion['pkt_id'] == initial_id:
            deletion['pkt_id'] = 'synthetic_INITIAL'
    if type(snapshot_index) is int and snapshot_index == 0 and type(result.get('friend_receive_id')) is int and result['friend_receive_id'] == initial_id:
        result['friend_receive_id'] = 'synthetic_INITIAL'
    return result


def differences(a, b, path='$'):
    """Bound diagnostic output while retaining exact equality as the verdict."""
    if type(a) is not type(b):
        yield path
    elif isinstance(a, dict):
        if a.keys() != b.keys():
            yield path + '.keys'
        for key in sorted(a.keys() & b.keys()):
            yield from differences(a[key], b[key], path + '.' + key)
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path + '.length'
        for i, (left, right) in enumerate(zip(a, b)):
            yield from differences(left, right, f'{path}[{i}]')
    elif a != b:
        yield path


def compare(root, commit, *, original_texture_exception=False):
    import itertools
    reports = {}
    with tempfile.TemporaryDirectory() as temporary:
        expected = run_ci.fixtures(Path(temporary))
    for target in ('arm64', 'i686'):
        folder = root / target
        report = json.loads((folder / 'report.json').read_text())
        if (report.get('target') != target or report.get('source_commit') != commit
                or report.get('cursor_stage_passed') is not True
                or report.get('original_texture_exception', False) is not original_texture_exception):
            raise ValueError('Reference identity or execution differs: ' + target)
        for label, initial_id in (('id1-a', 1), ('id1-b', 1), ('id31', 31)):
            run = folder / label
            process = json.loads((run / 'process-observation.json').read_text())
            if (type(process.get('returncode')) is not int or process['returncode'] != 2
                    or process.get('host_timeout_kill', False) is not False):
                raise ValueError('Reference process exit or timeout differs: ' + str(run))
            run_ci.check_output(run / 'receiver.jsonl', expected, initial_id, run / 'wine-output.txt',
                                original_texture_exception=original_texture_exception)
            reports[target, label] = run
    # All six runs must have identical literal startup/load inventories and counts,
    # including the ID-sensitivity run. No message normalization is permitted.
    outside = {key: json.loads((run / 'client-errors.json').read_text())['outside_errors']
               for key, run in reports.items()}
    if any(value != outside['arm64', 'id1-a'] for value in outside.values()):
        raise ValueError('Startup/map-load error inventories or counts differ')
    comparisons = []
    pairs = [(('arm64', label), ('i686', label), False) for label in ('id1-a', 'id1-b', 'id31')]
    for target in ('arm64', 'i686'):
        pairs += [((target, 'id1-a'), (target, 'id1-b'), False),
                  ((target, 'id1-a'), (target, 'id31'), True)]
    for left, right, sensitivity in pairs:
        mismatches = []
        for i in range(117):
            # Keep only a single pair in memory, not six complete histories.
            a_raw = (reports[left] / f'state-{i:03d}.json').read_bytes()
            b_raw = (reports[right] / f'state-{i:03d}.json').read_bytes()
            a, b = json.loads(a_raw), json.loads(b_raw)
            if sensitivity:
                a, b = canonical_initial_ids(a, 1, i), canonical_initial_ids(b, 31, i)
                equal = json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
            else:
                equal = a_raw == b_raw
            if not equal:
                mismatches.append({'index': i, 'fields': list(itertools.islice(differences(a, b), 20))})
        comparisons.append({'left': left, 'right': right, 'id_sensitivity': sensitivity,
                            'canonicalized_fields': [
                                'entities[].pkt_id_create',
                                'entities[].player.lastClientStatePktId',
                                'delete_history[].pkt_id',
                                'entities[].pkt_id_pos[]', 'entities[].pkt_id_qrot[]'] if sensitivity else [],
                            'canonicalization_condition': 'equals this runs synthetic INITIAL ID' if sensitivity else None,
                            'snapshot0_additional_canonicalization': {
                                'scalar_channels': list(INITIAL_CHANNEL_IDS),
                                'attribute_schemas': ATTRIBUTE_ID_SCHEMAS,
                                'friend_receive_id': True,
                                'condition': 'snapshot index 0; exact integer equals this runs synthetic INITIAL ID',
                                'review': 5646841168} if sensitivity else None,
                            'equal': not mismatches, 'mismatches': mismatches})
    return {'outside_error_inventories_equal': True, 'source_commit': commit, 'scope': 'partial_receiver_state_comparison',
            'original_texture_exception': original_texture_exception,
            'accepted_original_data_errors': run_ci.original_data_errors.load_policy()['occurrences'] if original_texture_exception else [],
            'comparisons': comparisons, 'partial_state_equal': all(c['equal'] for c in comparisons),
            'state_schema_complete': False, 'state_comparison_complete': False, 'm3_replay_complete': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--original-texture-exception', action='store_true')
    args = parser.parse_args()
    result = compare(args.root, args.commit, original_texture_exception=args.original_texture_exception)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    summary = {k: v for k, v in result.items() if k != 'comparisons'}
    print(json.dumps(summary))
    run_ci.notice('ArmPort partial state comparison', summary)
    return 0 if result['partial_state_equal'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
