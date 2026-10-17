#!/usr/bin/env python3
"""One-shot, bounded, read-only Linux owned-process memory diagnostic.

Explicit PID/start-tick admission is mandatory. No signal, launch, background
thread, command line, path inventory, account or environment capture occurs.
This is a sequential observation, never an atomic process-tree peak.
"""
import argparse
import json
import os
from pathlib import Path
import re
import time

MAX_PIDS = 8192
MAX_OWNED = 64
MAX_FILE = 16384


def require(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE + 1)
    require(len(raw) <= MAX_FILE, 'PROC_FILE_BOUND')
    return raw.decode('ascii')


def identity(proc, pid):
    raw = read(proc / str(pid) / 'stat')
    # comm may contain spaces and parentheses. Fields after its final ')' begin
    # at Linux field 3; starttime is field 22. Never export comm.
    end = raw.rfind(')')
    require(end > 0 and raw[:raw.find(' ')].isdigit(), 'STAT_FORMAT')
    require(int(raw[:raw.find(' ')]) == pid, 'STAT_PID')
    fields = raw[end + 1:].split()
    require(len(fields) >= 20 and fields[1].isdigit() and fields[19].isdigit(), 'STAT_FIELDS')
    return int(fields[1]), int(fields[19])


def metrics(proc, pid, uid):
    status = read(proc / str(pid) / 'status')
    uids = re.findall(r'^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$', status, re.M)
    require(len(uids) == 1 and all(int(value) == uid for value in uids[0]), 'UID_OWNERSHIP')
    rows = re.findall(r'^VmRSS:\s+(\d+) kB\s*$', status, re.M)
    require(len(rows) == 1, 'RSS_UNAVAILABLE')
    rss = int(rows[0])
    try:
        rollup = read(proc / str(pid) / 'smaps_rollup')
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        rollup = ''
    rows = re.findall(r'^Pss:\s+(\d+) kB\s*$', rollup, re.M)
    require(len(rows) <= 1, 'PSS_FORMAT')
    pss = int(rows[0]) if rows else None
    require(rss <= 2**50 and (pss is None or pss <= 2**50), 'METRIC_BOUND')
    return rss, pss


def sample(proc, root_pid, root_start_ticks, *, uid=None):
    require(type(root_pid) is int and root_pid > 0 and type(root_start_ticks) is int
            and root_start_ticks > 0, 'ROOT_IDENTITY_REQUIRED')
    uid = os.getuid() if uid is None else uid
    started = time.monotonic_ns()
    root = identity(proc, root_pid)
    require(root[1] == root_start_ticks, 'ROOT_REUSED')
    observed = {}
    count = 0
    with os.scandir(proc) as entries:
        for entry in entries:
            if not entry.name.isascii() or not entry.name.isdigit():
                continue
            count += 1
            require(count <= MAX_PIDS, 'PROCESS_SCAN_BOUND')
            pid = int(entry.name)
            try:
                observed[pid] = identity(proc, pid)
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue  # Unselected process exits do not establish ownership.
    require(observed.get(root_pid) == root, 'ROOT_CHANGED')
    selected = {root_pid}
    # Fixed point over bounded records handles arbitrary directory ordering.
    for _ in range(MAX_OWNED):
        added = {pid for pid, (parent, _) in observed.items() if parent in selected} - selected
        if not added:
            break
        selected.update(added)
        require(len(selected) <= MAX_OWNED, 'OWNED_PROCESS_BOUND')
    else:
        raise ValueError('ANCESTRY_DEPTH_BOUND')
    rss_sum = pss_sum = 0
    pss_count = 0
    # Every selected identity, including intermediate parents, is rechecked
    # before and after reads. Any observed exit/reparent/reuse refuses the sample.
    for pid in sorted(selected):
        require(identity(proc, pid) == observed[pid], 'SELECTED_IDENTITY_CHANGED')
        rss, pss = metrics(proc, pid, uid)
        require(identity(proc, pid) == observed[pid], 'SELECTED_IDENTITY_CHANGED')
        rss_sum += rss
        if pss is not None:
            pss_sum += pss
            pss_count += 1
    for pid in selected:
        require(identity(proc, pid) == observed[pid], 'SELECTED_IDENTITY_CHANGED')
    return {'schema': 'coh-owned-memory-observation-v1', 'observed_processes': len(selected),
            'observation_duration_ns': time.monotonic_ns() - started,
            'rss_sum_kib': rss_sum, 'rss_sum_counts_shared_pages_multiple_times': True,
            'pss_available_processes': pss_count,
            'enumerated_process_pss_sum_kib': pss_sum if pss_count == len(selected) else None,
            'process_tree_membership_atomic': False, 'whole_process_tree_peak_measured': False,
            'android_server_overlap_measured': False, 'enumeration_may_miss_short_lived_processes': True,
            'scope': 'same_uid_descendants_of_explicit_pid_starttime_at_sequential_read_boundaries'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', required=True, type=int)
    parser.add_argument('--start-ticks', required=True, type=int)
    args = parser.parse_args()
    try:
        result = sample(Path('/proc'), args.pid, args.start_ticks)
    except (OSError, ValueError, UnicodeError):
        # Never publish path-bearing OS error text.
        print(json.dumps({'schema': 'coh-owned-memory-observation-v1', 'passed': False,
                          'refusal_code': 'OWNED_SAMPLE_UNAVAILABLE'}))
        return 1
    print(json.dumps({'passed': True, **result}, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
