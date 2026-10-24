"""Inventory complete multiline game error traces without accepting them."""
from collections import Counter
import json
import re


def inventory(path, output):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('Missing or oversized game stdio evidence')
    counts = Counter()
    pending = []
    start = re.compile(r'client\.(?:error|fatal)|Assertion failed|assertion failure', re.I)

    def finish():
        if pending:
            text = ''.join(pending).rstrip()
            text = re.sub(r'^ArmPort zone: \d+ ', '', text)
            text = re.sub(r' tid=\d+$', '', text)
            counts[text] += 1
            pending.clear()

    with path.open(errors='replace') as stream:
        for line in stream:
            if start.search(line):
                finish()
                pending.append(line)
            elif pending:
                if line.startswith('ArmPort '):
                    finish()
                else:
                    pending.append(line)
            if pending and re.search(r' tid=\d+\s*$', line):
                finish()
        finish()
    result = dict(count=sum(counts.values()), unique=len(counts),
                  errors=[dict(text=text, count=count) for text, count in sorted(counts.items())])
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result
