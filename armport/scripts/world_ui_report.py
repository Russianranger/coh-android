"""Summarize world-phase UI inputs; never infer rendered text or acceptance."""
import json
import re

import world_model_report

FIELDS = 'frame compass_mode map_mode mission_map selected_task selected_type name_present map_present'.split()
PATTERN = re.compile(' '.join(rf'{key}=(-?[0-9]+)' for key in FIELDS))


def summarize(lines):
    lines = list(lines)
    models = world_model_report.summarize(lines)
    failures = [] if models['observations_valid'] else ['matching model/draw observations invalid']
    samples = []
    count = 0
    for index, line in enumerate(lines, 1):
        if not line.endswith('\n'):
            continue  # matching model report rejects torn records
        try:
            record = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(record, dict) or record.get('stage') != 'world.ui':
            continue
        count += 1
        if count > 8:
            continue
        text = record.get('text')
        match = PATTERN.fullmatch(text) if isinstance(text, str) and len(text) < 256 else None
        if not match or type(record.get('tid')) is not int or record['tid'] < 0:
            failures.append(f'invalid UI record {index}')
            continue
        sample = dict(zip(FIELDS, map(int, match.groups())))
        sample['tid'] = record['tid']
        if (any(not -(2**31) <= sample[k] < 2**31 for k in FIELDS[1:])
                or any(sample[k] not in (0, 1) for k in ('selected_task', 'name_present', 'map_present'))
                or sample['frame'] not in (1, 600, 1200, 1800, 2400, 3000, 3600, 4200)
                or samples and sample['frame'] <= samples[-1]['frame']):
            failures.append(f'inconsistent UI record {index}')
            continue
        samples.append(sample)
    if count > 8:
        failures.append('UI sample bound exceeded')
    if not samples or count != len(samples) or len(samples) != len(models['samples']):
        failures.append('missing matching UI/model samples')
    for ui, model in zip(samples, models['samples']):
        if (ui['frame'], ui['tid']) != (model['frame'], model['tid']):
            failures.append('UI/model frame or thread mismatch')
    valid = not failures
    return dict(scope='sampled_world_phase_ui_inputs_only', observations_valid=valid,
                sample_count=count, failure_count=len(failures), failures=failures[:16], samples=samples,
                samples_without_destination_name=sum(s['name_present'] == 0 for s in samples) if valid else None,
                cause_established=False, rendering_acceptance_changed=False)
