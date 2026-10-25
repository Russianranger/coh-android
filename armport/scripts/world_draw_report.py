"""Summarize 0077 observations without changing rendering acceptance."""
import re

FIELDS = ('frame refs roots root_models vis outside zocc fog visits editor_skip '
          'distance_skip frustum_skip model_calls not_loaded alpha_zero sort_requests tid').split()
PATTERN = re.compile(r'^ArmPort zone: [0-9]+ world\.draw ' +
                     ' '.join(rf'{key}=(-?[0-9]+)' for key in FIELDS) + r'$')


def summarize(lines):
    """Consume raw lines including terminators; an unterminated record is unknown."""
    samples, failures = [], []
    seen = 0
    previous = -1
    for line in lines:
        if not line.startswith('ArmPort zone: ') or ' world.draw' not in line:
            continue
        seen += 1
        if seen > 8:
            continue
        terminated = line.endswith('\n')
        record = line[:-1].removesuffix('\r') if terminated else line
        match = PATTERN.fullmatch(record) if terminated and len(record) <= 1024 else None
        if not match:
            failures.append('malformed sample ' + str(seen))
            continue
        values = dict(zip(FIELDS, map(int, match.groups())))
        rejected = sum(values[k] for k in ('editor_skip', 'distance_skip', 'frustum_skip'))
        if (any(values[k] < 0 for k in FIELDS if k != 'vis') or
                values['frame'] <= previous or rejected > values['visits']):
            failures.append('inconsistent sample ' + str(seen))
            continue
        previous = values['frame']
        values['visited_after_first_three_checks'] = values['visits'] - rejected
        samples.append(values)
    if seen > 8:
        failures.append('sample bound exceeded')
    complete = seen > 0 and not failures and len(samples) == seen
    return {'scope': 'sampled_world_traversal_only', 'observations_valid': complete,
            'sample_count': seen, 'failures': failures, 'samples': samples,
            'all_sampled_model_calls_zero': all(s['model_calls'] == 0 for s in samples) if complete else None,
            'all_sampled_sort_requests_zero': all(s['sort_requests'] == 0 for s in samples) if complete else None,
            'cause_established': False, 'rendering_acceptance_changed': False}
