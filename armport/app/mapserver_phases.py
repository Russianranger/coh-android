#!/usr/bin/env python3
"""Bounded MapServer console phase summary (diagnostic only; never gates).

MapServer prints self-timed phases ("Loading story arcs.. ... (53.58)") and
timestamped DEBUG/INFO lines. Untimed work (animation loading between the
sequencer parse and "Caching relevant folders") shows up only as a gap
between consecutive timestamps, so both views are reported.

Usage: mapserver_phases.py CONSOLE.txt  (prints the JSON summary)
"""
import datetime
import json
import re
import sys

STAMP = re.compile(r'\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{3})\]')
SELF_TIMED = re.compile(r'\((\d{1,5}\.\d\d)\)\s*$')
ANIMATION = re.compile(r'^COH_ANIM_CERT_V1 .*?\bopened=(\d+)')
# Native patch 0119 (instrumented CI MapServer) checkpoints, when present.
STARTUP = re.compile(r'ARMPORT_SERVER_STARTUP_V1 status=ok .*?\bphase=([a-z_]{1,40}) '
                     r'elapsed_ms=(\d+(?:\.\d+)?) phase_ms=(\d+(?:\.\d+)?)')
SESSION = re.compile(r'[0-9a-f]{32}')
# The last startup line before the map serves; later gaps are client waits.
READY = 'Verifying SG permission tables'
TRUSTED = 'ARMPORT_TRUSTED_BINS_V1 status=trusted'
LINE_LIMIT = 200000
LABEL_BYTES = 72


def _label(text):
    text = SESSION.sub('<session>', STAMP.sub('', text)).strip().strip('.').strip()
    return text[:LABEL_BYTES]


def _seconds(match):
    return datetime.datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S.%f').timestamp()


def summary(text, top=8):
    """Return the slowest self-timed phases and timestamp gaps up to map ready."""
    opener, previous = '', None
    timed, gaps = [], []
    first = last = None
    animations = None
    checkpoints, ready, trusted = {}, False, 0
    for index, line in enumerate(text.splitlines()):
        if index >= LINE_LIMIT:
            break
        if line.startswith(TRUSTED):
            trusted += 1
            continue
        match = STARTUP.search(line)
        if match and len(checkpoints) < 32:
            checkpoints.setdefault(match.group(1), round(float(match.group(3)) / 1000, 2))
            if match.group(1) == 'main_loop_begin':
                checkpoints.setdefault('elapsed_to_main_loop', round(float(match.group(2)) / 1000, 2))
            continue
        if READY in line or (line.startswith('COH_') and 'kind=ready' in line):
            ready = True
        if ready:
            continue
        match = ANIMATION.match(line)
        if match:
            animations = int(match.group(1))
            continue
        stamp = STAMP.search(line)
        head = line[:stamp.start()] if stamp else line
        if head.strip().endswith('..'):
            opener = _label(head.split('..', 1)[0])
        if stamp:
            moment = _seconds(stamp)
            first = moment if first is None else first
            last = moment
            if previous is not None and moment - previous[0] >= 1.0:
                gaps.append([round(moment - previous[0], 2), previous[1], _label(line[stamp.end():])])
            previous = (moment, _label(line[stamp.end():]))
        match = SELF_TIMED.search(line)
        if match and not stamp:
            text_before = line[:match.start()].strip()
            if re.fullmatch(r'(done|success)?', text_before) or text_before[:1].isdigit():
                label = opener
            elif '..' in text_before:
                label = _label(text_before.split('..', 1)[0])
            else:
                label = _label(text_before)
            timed.append([label, float(match.group(1))])
    timed.sort(key=lambda row: -row[1])
    gaps.sort(key=lambda row: -row[0])
    return {'format': 1,
            'stamped_span_seconds': round(last - first, 2) if first is not None else None,
            'self_timed_total_seconds': round(sum(row[1] for row in timed), 2),
            'slowest_self_timed': timed[:top],
            'slowest_untimed_gaps': gaps[:top],
            'animation_files_opened': animations,
            'native_checkpoint_seconds': checkpoints or None,
            'trusted_bins_reported': trusted}


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8', errors='replace') as handle:
        print(json.dumps(summary(handle.read(), top=12), indent=1))
