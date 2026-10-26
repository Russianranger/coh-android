"""Summarize 0083 model counters; never changes rendering acceptance."""
import json
import re

import world_draw_report

FIELDS = 'frame visits editor_skip distance_skip frustum_skip postchecks'.split()
MODEL = re.compile(' '.join(rf'{key}=([0-9]+)' for key in FIELDS))
DRAW_FIELDS = world_draw_report.FIELDS[:-1]  # tid is a separate JSONL field
DRAW = re.compile(' '.join(rf'{key}=(-?[0-9]+)' for key in DRAW_FIELDS))


def summarize(lines):
    """Use complete isolated records; reject missing, torn or inconsistent pairs."""
    models, draws, failures = [], [], []
    model_count = draw_count = 0
    for index, line in enumerate(lines, 1):
        if not line.endswith('\n'):
            failures.append(f'unterminated trace record {index}')
            continue
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError('object required')
        except (ValueError, TypeError):
            failures.append(f'invalid trace record {index}')
            continue
        stage = record.get('stage')
        if stage not in ('world.models', 'world.draw'):
            continue
        is_model = stage == 'world.models'
        if is_model:
            model_count += 1
            count = model_count
        else:
            draw_count += 1
            count = draw_count
        if count > 8:
            continue
        text = record.get('text')
        pattern, fields = (MODEL, FIELDS) if is_model else (DRAW, DRAW_FIELDS)
        match = pattern.fullmatch(text) if isinstance(text, str) and len(text) <= 1024 else None
        if not match or type(record.get('tid')) is not int or record['tid'] < 0:
            failures.append(f'invalid {stage} record {index}')
            continue
        sample = dict(zip(fields, map(int, match.groups())))
        sample['tid'] = record['tid']
        destination = models if is_model else draws
        if (any(value < 0 for key, value in sample.items() if key != 'vis') or
                destination and sample['frame'] <= destination[-1]['frame']):
            failures.append(f'inconsistent {stage} record {index}')
            continue
        rejected = sum(sample[key] for key in ('editor_skip','distance_skip','frustum_skip'))
        if rejected > sample['visits'] or (is_model and rejected + sample['postchecks'] != sample['visits']):
            failures.append(f'inconsistent {stage} counts {index}')
            continue
        destination.append(sample)
    if model_count > 8 or draw_count > 8:
        failures.append('sample bound exceeded')
    if not models or len(models) != len(draws):
        failures.append('missing matching draw/model samples')
    for model, draw in zip(models, draws):
        if (model['frame'] != draw['frame'] or model['tid'] != draw['tid'] or
                any(model[key] > draw[key] for key in ('visits','editor_skip','distance_skip','frustum_skip')) or
                model['postchecks'] > draw['visits'] - sum(draw[key] for key in ('editor_skip','distance_skip','frustum_skip'))):
            failures.append('draw/model counters disagree at frame ' + str(model['frame']))
    valid = not failures and len(models) == model_count and len(draws) == draw_count
    return dict(scope='sampled_model_counters_only', observations_valid=valid,
                model_sample_count=model_count, draw_sample_count=draw_count,
                failure_count=len(failures), failures=failures[:16], samples=models,
                all_sampled_model_visits_zero=all(sample['visits']==0 for sample in models) if valid else None,
                all_sampled_postchecks_zero=all(sample['postchecks']==0 for sample in models) if valid else None,
                cause_established=False, rendering_acceptance_changed=False)
